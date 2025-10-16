"""
UDS3 Relational Filter Module
==============================

SQL Query Builder for SQLite and PostgreSQL with fluent API.

Features:
- SELECT clause with field selection and aggregates
- FROM clause with table specification
- JOIN support (INNER, LEFT, RIGHT, FULL)
- WHERE clause with parameter binding
- GROUP BY and HAVING
- ORDER BY and LIMIT/OFFSET
- SQL injection protection via parameter binding
- Multiple SQL dialect support

Author: UDS3 Team
Date: 2. Oktober 2025
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from uds3_query_filters import (
    BaseFilter,
    FilterOperator,
    FilterCondition,
    SortOrder,
    SortField,
    LogicalOperator,
    QueryResult
)

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class JoinType(Enum):
    """SQL JOIN types"""
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL OUTER JOIN"
    CROSS = "CROSS JOIN"


class SQLDialect(Enum):
    """SQL dialect support"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class AggregateFunction(Enum):
    """SQL aggregate functions"""
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    GROUP_CONCAT = "GROUP_CONCAT"  # SQLite
    STRING_AGG = "STRING_AGG"      # PostgreSQL


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SelectField:
    """Represents a SELECT field"""
    expression: str
    alias: Optional[str] = None
    aggregate: Optional[AggregateFunction] = None
    
    def to_sql(self, dialect: SQLDialect = SQLDialect.SQLITE) -> str:
        """Convert to SQL string"""
        if self.aggregate:
            sql = f"{self.aggregate.value}({self.expression})"
        else:
            sql = self.expression
        
        if self.alias:
            sql += f" AS {self.alias}"
        
        return sql
    
    def __repr__(self) -> str:
        if self.aggregate:
            return f"{self.aggregate.value}({self.expression})"
        return self.expression


@dataclass
class JoinClause:
    """Represents a SQL JOIN clause"""
    join_type: JoinType
    table: str
    on_left: str
    on_right: str
    alias: Optional[str] = None
    
    def to_sql(self) -> str:
        """Convert to SQL JOIN clause"""
        table_ref = f"{self.table} AS {self.alias}" if self.alias else self.table
        return f"{self.join_type.value} {table_ref} ON {self.on_left} = {self.on_right}"
    
    def __repr__(self) -> str:
        return f"JOIN {self.table} ON {self.on_left}={self.on_right}"


@dataclass
class GroupByClause:
    """Represents GROUP BY clause"""
    fields: List[str]
    having_conditions: List[FilterCondition] = field(default_factory=list)
    
    def to_sql(self) -> Tuple[str, Optional[str]]:
        """
        Convert to SQL GROUP BY and HAVING clauses.
        
        Returns:
            Tuple of (GROUP BY clause, HAVING clause or None)
        """
        group_by = f"GROUP BY {', '.join(self.fields)}"
        
        if self.having_conditions:
            having_parts = []
            for cond in self.having_conditions:
                having_parts.append(self._condition_to_sql(cond))
            having = "HAVING " + " AND ".join(having_parts)
            return group_by, having
        
        return group_by, None
    
    def _condition_to_sql(self, condition: FilterCondition) -> str:
        """Convert HAVING condition to SQL"""
        # Simple implementation - would need parameter binding in real usage
        op_map = {
            FilterOperator.EQ: "=",
            FilterOperator.NE: "!=",
            FilterOperator.GT: ">",
            FilterOperator.LT: "<",
            FilterOperator.GTE: ">=",
            FilterOperator.LTE: "<=",
        }
        
        operator = op_map.get(condition.operator, "=")
        return f"{condition.field} {operator} ?"


@dataclass
class RelationalQueryResult(QueryResult):
    """Extended QueryResult for relational queries"""
    sql_query: Optional[str] = None
    parameters: Optional[List[Any]] = None
    rows_affected: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.sql_query:
            result["sql_query"] = self.sql_query
        if self.parameters:
            result["parameters"] = self.parameters
        if self.rows_affected is not None:
            result["rows_affected"] = self.rows_affected
        return result


# ============================================================================
# Relational Filter
# ============================================================================

class RelationalFilter(BaseFilter):
    """
    SQL Query Builder for relational databases (SQLite, PostgreSQL).
    
    Features:
    - Fluent API for building SQL queries
    - SELECT with fields, aggregates, DISTINCT
    - JOIN support (INNER, LEFT, RIGHT, FULL)
    - WHERE with parameter binding
    - GROUP BY with HAVING
    - ORDER BY, LIMIT, OFFSET
    - SQL injection protection
    
    Example:
        filter = RelationalFilter(db_backend)
            .select("users.name", "users.email")
            .select_aggregate(AggregateFunction.COUNT, "orders.id", "order_count")
            .from_table("users")
            .left_join("orders", "users.id", "orders.user_id")
            .where("users.active", FilterOperator.EQ, True)
            .group_by("users.id", "users.name", "users.email")
            .having("order_count", FilterOperator.GT, 5)
            .order_by("order_count", SortOrder.DESC)
            .limit(10)
        
        result = filter.execute()
    """
    
    def __init__(
        self, 
        backend=None, 
        dialect: SQLDialect = SQLDialect.SQLITE
    ):
        """
        Initialize RelationalFilter.
        
        Args:
            backend: Database backend (SQLite or PostgreSQL connection)
            dialect: SQL dialect to use
        """
        super().__init__(backend)
        self.dialect = dialect
        self.select_fields: List[SelectField] = []
        self.from_table_name: Optional[str] = None
        self.from_table_alias: Optional[str] = None
        self.join_clauses: List[JoinClause] = []
        self.group_by_clause: Optional[GroupByClause] = None
        self.distinct: bool = False
        self.parameters: List[Any] = []
        
        logger.debug(f"Initialized RelationalFilter with {dialect.value} dialect")
    
    # ========================================================================
    # SELECT Clause Methods
    # ========================================================================
    
    def select(self, *fields: str) -> 'RelationalFilter':
        """
        Add fields to SELECT clause.
        
        Args:
            *fields: Field names or expressions (e.g., "users.name", "COUNT(*)")
        
        Returns:
            Self for method chaining
        
        Example:
            .select("id", "name", "email")
            .select("users.name", "orders.total")
        """
        for field_expr in fields:
            self.select_fields.append(SelectField(expression=field_expr))
        
        logger.debug(f"Added SELECT fields: {fields}")
        return self
    
    def select_aggregate(
        self, 
        func: AggregateFunction, 
        field: str, 
        alias: Optional[str] = None
    ) -> 'RelationalFilter':
        """
        Add aggregate function to SELECT clause.
        
        Args:
            func: Aggregate function (COUNT, SUM, AVG, MIN, MAX)
            field: Field name or expression
            alias: Optional alias for result
        
        Returns:
            Self for method chaining
        
        Example:
            .select_aggregate(AggregateFunction.COUNT, "*", "total_count")
            .select_aggregate(AggregateFunction.AVG, "orders.amount", "avg_amount")
        """
        self.select_fields.append(
            SelectField(expression=field, aggregate=func, alias=alias)
        )
        
        logger.debug(f"Added aggregate: {func.value}({field}) AS {alias}")
        return self
    
    def select_distinct(self) -> 'RelationalFilter':
        """
        Enable DISTINCT for SELECT clause.
        
        Returns:
            Self for method chaining
        
        Example:
            .select("country").select_distinct()
        """
        self.distinct = True
        logger.debug("Enabled DISTINCT")
        return self
    
    def select_count(self, alias: str = "count") -> 'RelationalFilter':
        """
        Convenience method for COUNT(*).
        
        Args:
            alias: Alias for count column (default: "count")
        
        Returns:
            Self for method chaining
        
        Example:
            .select_count("total_users")
        """
        return self.select_aggregate(AggregateFunction.COUNT, "*", alias)
    
    # ========================================================================
    # FROM Clause Methods
    # ========================================================================
    
    def from_table(self, table: str, alias: Optional[str] = None) -> 'RelationalFilter':
        """
        Specify FROM table.
        
        Args:
            table: Table name
            alias: Optional table alias
        
        Returns:
            Self for method chaining
        
        Example:
            .from_table("users")
            .from_table("users", "u")
        """
        self.from_table_name = table
        self.from_table_alias = alias
        
        logger.debug(f"Set FROM table: {table}" + (f" AS {alias}" if alias else ""))
        return self
    
    # ========================================================================
    # JOIN Methods
    # ========================================================================
    
    def join(
        self, 
        table: str, 
        on_left: str, 
        on_right: str,
        join_type: JoinType = JoinType.INNER,
        alias: Optional[str] = None
    ) -> 'RelationalFilter':
        """
        Add JOIN clause.
        
        Args:
            table: Table to join
            on_left: Left side of ON condition (e.g., "users.id")
            on_right: Right side of ON condition (e.g., "orders.user_id")
            join_type: Type of join (default: INNER)
            alias: Optional table alias
        
        Returns:
            Self for method chaining
        
        Example:
            .join("orders", "users.id", "orders.user_id")
            .join("products", "orders.product_id", "products.id", alias="p")
        """
        join_clause = JoinClause(
            join_type=join_type,
            table=table,
            on_left=on_left,
            on_right=on_right,
            alias=alias
        )
        self.join_clauses.append(join_clause)
        
        logger.debug(f"Added {join_type.value}: {table} ON {on_left}={on_right}")
        return self
    
    def inner_join(
        self, 
        table: str, 
        on_left: str, 
        on_right: str,
        alias: Optional[str] = None
    ) -> 'RelationalFilter':
        """
        Add INNER JOIN (convenience method).
        
        Example:
            .inner_join("orders", "users.id", "orders.user_id")
        """
        return self.join(table, on_left, on_right, JoinType.INNER, alias)
    
    def left_join(
        self, 
        table: str, 
        on_left: str, 
        on_right: str,
        alias: Optional[str] = None
    ) -> 'RelationalFilter':
        """
        Add LEFT JOIN (convenience method).
        
        Example:
            .left_join("orders", "users.id", "orders.user_id")
        """
        return self.join(table, on_left, on_right, JoinType.LEFT, alias)
    
    def right_join(
        self, 
        table: str, 
        on_left: str, 
        on_right: str,
        alias: Optional[str] = None
    ) -> 'RelationalFilter':
        """
        Add RIGHT JOIN (convenience method).
        
        Example:
            .right_join("orders", "users.id", "orders.user_id")
        """
        return self.join(table, on_left, on_right, JoinType.RIGHT, alias)
    
    def full_join(
        self, 
        table: str, 
        on_left: str, 
        on_right: str,
        alias: Optional[str] = None
    ) -> 'RelationalFilter':
        """
        Add FULL OUTER JOIN (convenience method).
        
        Example:
            .full_join("orders", "users.id", "orders.user_id")
        """
        return self.join(table, on_left, on_right, JoinType.FULL, alias)
    
    # ========================================================================
    # GROUP BY / HAVING Methods
    # ========================================================================
    
    def group_by(self, *fields: str) -> 'RelationalFilter':
        """
        Add GROUP BY clause.
        
        Args:
            *fields: Field names to group by
        
        Returns:
            Self for method chaining
        
        Example:
            .group_by("country", "city")
            .group_by("users.id", "users.name")
        """
        if not self.group_by_clause:
            self.group_by_clause = GroupByClause(fields=list(fields))
        else:
            self.group_by_clause.fields.extend(fields)
        
        logger.debug(f"Added GROUP BY: {fields}")
        return self
    
    def having(
        self, 
        field: str, 
        operator: FilterOperator, 
        value: Any
    ) -> 'RelationalFilter':
        """
        Add HAVING condition (for aggregate filtering).
        
        Args:
            field: Field or aggregate expression
            operator: Filter operator
            value: Comparison value
        
        Returns:
            Self for method chaining
        
        Example:
            .having("COUNT(*)", FilterOperator.GT, 5)
            .having("AVG(amount)", FilterOperator.GTE, 100.0)
        """
        if not self.group_by_clause:
            raise ValueError("HAVING requires GROUP BY to be set first")
        
        condition = FilterCondition(
            field=field,
            operator=operator,
            value=value
        )
        self.group_by_clause.having_conditions.append(condition)
        
        logger.debug(f"Added HAVING: {field} {operator.value} {value}")
        return self
    
    # ========================================================================
    # SQL Generation
    # ========================================================================
    
    def to_sql(self, count_only: bool = False) -> Tuple[str, List[Any]]:
        """
        Generate SQL query string with parameter placeholders.
        
        Args:
            count_only: If True, generate COUNT(*) query
        
        Returns:
            Tuple of (SQL string, parameter list)
        
        Example:
            sql, params = filter.to_sql()
            # sql: "SELECT name, email FROM users WHERE active = ? LIMIT ?"
            # params: [True, 10]
        """
        self.parameters = []
        parts = []
        
        # SELECT clause
        if count_only:
            parts.append("SELECT COUNT(*)")
        else:
            select_clause = self._build_select_clause()
            parts.append(select_clause)
        
        # FROM clause
        if not self.from_table_name:
            raise ValueError("FROM table must be specified")
        
        from_clause = self._build_from_clause()
        parts.append(from_clause)
        
        # JOIN clauses
        for join_clause in self.join_clauses:
            parts.append(join_clause.to_sql())
        
        # WHERE clause
        if self.conditions:
            where_clause = self._build_where_clause()
            parts.append(where_clause)
        
        # GROUP BY / HAVING
        if self.group_by_clause and not count_only:
            group_by_sql, having_sql = self.group_by_clause.to_sql()
            parts.append(group_by_sql)
            if having_sql:
                parts.append(having_sql)
                # Add HAVING parameters
                for cond in self.group_by_clause.having_conditions:
                    self.parameters.append(cond.value)
        
        # ORDER BY (skip for count queries)
        if self.sort_fields and not count_only:
            order_by_clause = self._build_order_by_clause()
            parts.append(order_by_clause)
        
        # LIMIT / OFFSET (skip for count queries)
        if not count_only:
            if self.limit_value is not None:
                parts.append(f"LIMIT ?")
                self.parameters.append(self.limit_value)
            
            if self.offset_value > 0:
                parts.append(f"OFFSET ?")
                self.parameters.append(self.offset_value)
        
        sql = " ".join(parts)
        logger.debug(f"Generated SQL: {sql}")
        logger.debug(f"Parameters: {self.parameters}")
        
        return sql, self.parameters.copy()
    
    def _build_select_clause(self) -> str:
        """Build SELECT clause"""
        if not self.select_fields:
            # Default: SELECT *
            select_expr = "*"
        else:
            field_strs = [f.to_sql(self.dialect) for f in self.select_fields]
            select_expr = ", ".join(field_strs)
        
        if self.distinct:
            return f"SELECT DISTINCT {select_expr}"
        else:
            return f"SELECT {select_expr}"
    
    def _build_from_clause(self) -> str:
        """Build FROM clause"""
        if self.from_table_alias:
            return f"FROM {self.from_table_name} AS {self.from_table_alias}"
        else:
            return f"FROM {self.from_table_name}"
    
    def _build_where_clause(self) -> str:
        """Build WHERE clause with parameter binding"""
        where_parts = []
        
        for condition in self.conditions:
            where_part = self._condition_to_sql(condition)
            
            # Add logical operator if not first condition
            if where_parts:
                logical_op = condition.logical_op.value.upper()
                where_parts.append(logical_op)
            
            where_parts.append(where_part)
            
            # Add value to parameters list
            if condition.operator not in [FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL]:
                if condition.operator == FilterOperator.IN:
                    # IN requires multiple parameters
                    if isinstance(condition.value, (list, tuple)):
                        for val in condition.value:
                            self.parameters.append(val)
                elif condition.operator == FilterOperator.BETWEEN:
                    # BETWEEN requires two parameters
                    if isinstance(condition.value, (list, tuple)) and len(condition.value) == 2:
                        self.parameters.append(condition.value[0])
                        self.parameters.append(condition.value[1])
                else:
                    self.parameters.append(condition.value)
        
        return "WHERE " + " ".join(where_parts)
    
    def _condition_to_sql(self, condition: FilterCondition) -> str:
        """Convert FilterCondition to SQL with parameter placeholder"""
        field = condition.field
        op = condition.operator
        
        # Operator mapping
        if op == FilterOperator.EQ:
            return f"{field} = ?"
        elif op == FilterOperator.NE:
            return f"{field} != ?"
        elif op == FilterOperator.GT:
            return f"{field} > ?"
        elif op == FilterOperator.LT:
            return f"{field} < ?"
        elif op == FilterOperator.GTE:
            return f"{field} >= ?"
        elif op == FilterOperator.LTE:
            return f"{field} <= ?"
        elif op == FilterOperator.IN:
            # Build placeholders for IN clause
            if isinstance(condition.value, (list, tuple)):
                placeholders = ", ".join(["?"] * len(condition.value))
                return f"{field} IN ({placeholders})"
            else:
                return f"{field} IN (?)"
        elif op == FilterOperator.NOT_IN:
            if isinstance(condition.value, (list, tuple)):
                placeholders = ", ".join(["?"] * len(condition.value))
                return f"{field} NOT IN ({placeholders})"
            else:
                return f"{field} NOT IN (?)"
        elif op == FilterOperator.CONTAINS:
            # Use LIKE for contains (will need % wrapping in parameter)
            return f"{field} LIKE ?"
        elif op == FilterOperator.NOT_CONTAINS:
            return f"{field} NOT LIKE ?"
        elif op == FilterOperator.STARTS_WITH:
            return f"{field} LIKE ?"
        elif op == FilterOperator.ENDS_WITH:
            return f"{field} LIKE ?"
        elif op == FilterOperator.IS_NULL:
            return f"{field} IS NULL"
        elif op == FilterOperator.IS_NOT_NULL:
            return f"{field} IS NOT NULL"
        elif op == FilterOperator.BETWEEN:
            return f"{field} BETWEEN ? AND ?"
        else:
            # Fallback
            return f"{field} = ?"
    
    def _build_order_by_clause(self) -> str:
        """Build ORDER BY clause"""
        if not self.sort_fields:
            return ""
        
        order_parts = []
        for sort_field in self.sort_fields:
            order_str = f"{sort_field.field} {sort_field.order.value.upper()}"
            order_parts.append(order_str)
        
        return "ORDER BY " + ", ".join(order_parts)
    
    # ========================================================================
    # Execution Methods
    # ========================================================================
    
    def execute(self) -> RelationalQueryResult:
        """
        Execute the SQL query and return results.
        
        Returns:
            RelationalQueryResult with query results
        
        Note:
            Requires a valid database backend to be set.
        """
        if not self.backend:
            logger.error("Cannot execute: no backend set")
            return RelationalQueryResult(
                success=False,
                results=[],
                errors=["No database backend configured"]
            )
        
        try:
            sql, params = self.to_sql()
            
            # Execute query through backend
            # This is a simplified version - real implementation depends on backend type
            results_list = []
            
            if hasattr(self.backend, 'execute_query'):
                results = self.backend.execute_query(sql, params)
                results_list = results if isinstance(results, list) else []
            elif hasattr(self.backend, 'execute'):
                cursor = self.backend.execute(sql, params)
                results = cursor.fetchall()
                # Convert to list
                if isinstance(results, list):
                    results_list = results
                elif results:
                    try:
                        results_list = list(results)
                    except:
                        results_list = [results]
                else:
                    results_list = []
            else:
                raise ValueError("Backend does not support query execution")
            
            return RelationalQueryResult(
                success=True,
                results=results_list,
                total_count=len(results_list),
                sql_query=sql,
                parameters=params,
                database=self.dialect.value
            )
        
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return RelationalQueryResult(
                success=False,
                results=[],
                errors=[str(e)],
                sql_query=sql if 'sql' in locals() else None,
                parameters=params if 'params' in locals() else None
            )
    
    def count(self) -> int:
        """
        Execute COUNT(*) query and return count.
        
        Returns:
            Number of matching rows
        """
        if not self.backend:
            logger.error("Cannot count: no backend set")
            return 0
        
        try:
            sql, params = self.to_sql(count_only=True)
            
            # Execute count query
            if hasattr(self.backend, 'execute_query'):
                result = self.backend.execute_query(sql, params)
                if result and len(result) > 0:
                    # Handle both dict and tuple results
                    if isinstance(result[0], dict):
                        return result[0].get('count', 0) or result[0].get('COUNT(*)', 0)
                    else:
                        return result[0][0] if result[0] else 0
                return 0
            elif hasattr(self.backend, 'execute'):
                cursor = self.backend.execute(sql, params)
                row = cursor.fetchone()
                if row:
                    # Handle both list and tuple
                    return row[0] if isinstance(row, (list, tuple)) else row
                return 0
            else:
                raise ValueError("Backend does not support query execution")
        
        except Exception as e:
            logger.error(f"Count query failed: {e}")
            return 0
    
    def to_query(self) -> Dict[str, Any]:
        """
        Convert filter to dictionary representation.
        
        Returns:
            Dictionary with query details
        """
        sql, params = self.to_sql()
        
        return {
            "filter_type": "relational",
            "dialect": self.dialect.value,
            "sql": sql,
            "parameters": params,
            "from_table": self.from_table_name,
            "select_fields": [str(f) for f in self.select_fields],
            "join_count": len(self.join_clauses),
            "conditions": [c.to_dict() for c in self.conditions],
            "limit": self.limit_value,
            "offset": self.offset_value
        }


# ============================================================================
# Factory Function
# ============================================================================

def create_relational_filter(
    backend=None, 
    dialect: SQLDialect = SQLDialect.SQLITE
) -> RelationalFilter:
    """
    Factory function to create RelationalFilter instance.
    
    Args:
        backend: Database backend (SQLite or PostgreSQL connection)
        dialect: SQL dialect to use (default: SQLite)
    
    Returns:
        RelationalFilter instance
    
    Example:
        filter = create_relational_filter(sqlite_conn, SQLDialect.SQLITE)
        filter = create_relational_filter(pg_conn, SQLDialect.POSTGRESQL)
    """
    return RelationalFilter(backend=backend, dialect=dialect)


# ============================================================================
# Main (Testing)
# ============================================================================

if __name__ == "__main__":
    print("UDS3 RelationalFilter Test")
    print("=" * 80)
    
    # Test SQL generation
    filter = RelationalFilter(dialect=SQLDialect.SQLITE)
    filter.select("users.id", "users.name", "users.email") \
          .select_aggregate(AggregateFunction.COUNT, "orders.id", "order_count") \
          .from_table("users") \
          .left_join("orders", "users.id", "orders.user_id") \
          .where("users.active", FilterOperator.EQ, True) \
          .and_where("users.created_at", FilterOperator.GT, "2025-01-01") \
          .group_by("users.id", "users.name", "users.email") \
          .having("order_count", FilterOperator.GT, 5) \
          .order_by("order_count", SortOrder.DESC) \
          .limit(10)
    
    sql, params = filter.to_sql()
    
    print("\n✅ Generated SQL:")
    print(sql)
    print("\n✅ Parameters:")
    print(params)
    
    print("\n✅ Query Dict:")
    import json
    print(json.dumps(filter.to_query(), indent=2))
    
    print("\n" + "=" * 80)
    print("✅ RelationalFilter module created successfully!")
