"""
Themis Relational Backend

Implements UDS3-like relational operations on top of Themis HTTP API.

Author: VCC Covina Team
Created: 2025-11-07
Version: 0.1.0
"""

from __future__ import annotations

import json
import uuid
import re
from typing import Optional, List, Dict, Any

from .themis_adapter import ThemisAdapter
from .themis_exceptions import (
    ThemisNotFoundError,
    ThemisValidationError,
    create_query_error,
)


class ThemisRelationalBackend:
    """
    Relational Backend for Themis (PostgreSQL → Themis Entities + AQL)

    Maps UDS3 relational operations to Themis HTTP API:
    - CRUD → /entities/{key} (PUT/GET/DELETE)
    - Queries → /query/aql (AQL syntax)
    - Aggregations → COLLECT clause
    """

    def __init__(self, adapter: ThemisAdapter):
        self.adapter = adapter
        self.client = adapter  # use adapter's retry-enabled methods
        self.logger = adapter.logger

    # -------------------------------------------------------------------------
    # UDS3-compatible CRUD operations
    # -------------------------------------------------------------------------
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute SQL-like query (basic translation to AQL).

        Supports minimal subset:
        - SELECT * FROM table [WHERE expr] [ORDER BY col [ASC|DESC]] [LIMIT n]
        - SELECT col1, col2 FROM table ...
        
        Note: For complex queries, pass AQL directly using the same method.
        If `query` looks like AQL (starts with FOR/LET/RETURN), it's sent as-is.
        """
        aql_query = query if self._looks_like_aql(query) else self._translate_sql_to_aql(query, params)
        try:
            response = await self.client.post(
                "/query/aql",
                json={
                    "query": aql_query,
                    "allow_full_scan": True
                }
            )
            data = response.json()
            # Themis returns entities as JSON strings in a list under key "entities"
            entities = [json.loads(entity_str) for entity_str in data.get("entities", [])]
            return entities
        except ThemisValidationError as e:
            raise create_query_error(str(e), query=aql_query)

    async def insert(self, table: str, data: Dict[str, Any]) -> str:
        """
        Insert entity into table.

        Args:
            table: Table/collection name (prefix for entity key)
            data: Entity document (JSON)
        Returns:
            Entity key (format: "{table}:{pk}")
        """
        pk = self._extract_or_create_pk(data)
        key = f"{table}:{pk}"
        await self._put_entity(key, data)
        return key

    async def update(self, table: str, pk: str, data: Dict[str, Any]) -> bool:
        """Update entity (upsert semantics in Themis)."""
        key = f"{table}:{pk}"
        await self._put_entity(key, data)
        return True

    async def delete(self, table: str, pk: str) -> bool:
        """Delete entity by primary key."""
        key = f"{table}:{pk}"
        response = await self.client.delete(f"/entities/{key}")
        return response.status_code == 200

    async def get(self, table: str, pk: str) -> Optional[Dict[str, Any]]:
        """Get entity by primary key."""
        key = f"{table}:{pk}"
        response = await self.client.get(f"/entities/{key}")
        if response.status_code == 404:
            return None
        data = response.json()
        return json.loads(data.get("blob", "{}"))

    # -------------------------------------------------------------------------
    # Aggregations (AQL COLLECT)
    # -------------------------------------------------------------------------
    async def aggregate(self, table: str, group_by: str, aggregations: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Execute aggregation query via AQL COLLECT.

        Example:
            group_by = "city"
            aggregations = [
                {"func": "COUNT", "as": "total"},
                {"func": "AVG", "field": "salary", "as": "avg_sal"}
            ]
        """
        agg_clauses: List[str] = []
        return_names: List[str] = [group_by]
        for agg in aggregations:
            func = agg["func"].upper()
            field = agg.get("field")
            as_name = agg["as"]
            return_names.append(as_name)
            if func == "COUNT":
                agg_clauses.append(f"{as_name} = COUNT()")
            elif field:
                agg_clauses.append(f"{as_name} = {func}(doc.{field})")
            else:
                raise ThemisValidationError(f"Aggregation '{func}' requires 'field'", status_code=400)

        aql = (
            f"FOR doc IN {table}\n"
            f"COLLECT {group_by}_val = doc.{group_by}\n"
            f"AGGREGATE {', '.join(agg_clauses)}\n"
            f"RETURN {{{group_by}: {group_by}_val, {', '.join(n + ': ' + n for n in return_names if n != group_by)}}}"
        )
        try:
            response = await self.client.post("/query/aql", json={"query": aql})
            entities = [json.loads(e) for e in response.json().get("entities", [])]
            return entities
        except ThemisValidationError as e:
            raise create_query_error(str(e), query=aql)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    async def _put_entity(self, key: str, doc: Dict[str, Any]) -> None:
        payload = {
            "key": key,
            "blob": json.dumps(doc, ensure_ascii=False)
        }
        await self.client.put(f"/entities/{key}", json=payload)

    def _extract_or_create_pk(self, data: Dict[str, Any]) -> str:
        for k in ("_key", "id", "pk", "_id"):
            if k in data and data[k]:
                return str(data[k])
        new_pk = str(uuid.uuid4())
        data.setdefault("_key", new_pk)
        return new_pk

    def _looks_like_aql(self, text: str) -> bool:
        head = text.strip().upper()
        return head.startswith("FOR ") or head.startswith("LET ") or head.startswith("RETURN ")

    def _translate_sql_to_aql(self, sql: str, params: Optional[Dict[str, Any]]) -> str:
        """
        Translate a minimal subset of SQL to AQL.

        Supports:
        - SELECT fields FROM table [WHERE expr] [ORDER BY col [ASC|DESC]] [LIMIT n]

        Limitations:
        - WHERE clause is passed through with '=' replaced by '=='
        - Field references are not qualified automatically (expects 'doc.field') if complex
        - Intended as pragmatic MVP; complex SQL should be provided as AQL directly
        """
        select_match = re.search(r"SELECT\s+(.+?)\s+FROM\s+(\w+)", sql, re.IGNORECASE)
        if not select_match:
            raise ThemisValidationError(f"Unsupported SQL: {sql}", status_code=400)
        fields, table = select_match.groups()

        where_match = re.search(r"WHERE\s+(.+?)(?:\s+ORDER BY|\s+LIMIT|$)", sql, re.IGNORECASE)
        order_match = re.search(r"ORDER BY\s+(\w+)(?:\s+(ASC|DESC))?", sql, re.IGNORECASE)
        limit_match = re.search(r"LIMIT\s+(\d+)", sql, re.IGNORECASE)

        parts: List[str] = [f"FOR doc IN {table}"]

        if where_match:
            where_clause = where_match.group(1)
            # naive operator cleanup
            where_clause = re.sub(r"\s=\s", " == ", where_clause)
            parts.append(f"FILTER {where_clause}")

        if order_match:
            col, direction = order_match.groups()
            direction = (direction or "ASC").upper()
            parts.append(f"SORT doc.{col} {direction}")

        if limit_match:
            parts.append(f"LIMIT {limit_match.group(1)}")

        if fields.strip() == "*":
            parts.append("RETURN doc")
        else:
            field_list = [f.strip() for f in fields.split(",")]
            returned = "{" + ", ".join(f"{f}: doc.{f}" for f in field_list) + "}"
            parts.append(f"RETURN {returned}")

        return "\n".join(parts)
