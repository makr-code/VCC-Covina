"""
Themis Adapter
Phase 2: VCC Ecosystem Integration

Adapter for Themis Unified Database Service.
Provides cross-VCC data access and synchronization.

On-premise deployment - connects to self-hosted Themis service.
"""

import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from .base_adapter import VCCServiceAdapter, VCCServiceError

logger = logging.getLogger(__name__)


# Themis Data Models

class SyncDirection(str, Enum):
    """Data synchronization direction"""
    COVINA_TO_THEMIS = "covina_to_themis"
    THEMIS_TO_COVINA = "themis_to_covina"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(str, Enum):
    """Conflict resolution strategy"""
    LATEST_WINS = "latest_wins"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    MANUAL = "manual"


class ThemisRecord(BaseModel):
    """Record from Themis database"""
    record_id: str
    table_name: str
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int = 1
    source_service: str = "themis"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    """Result of synchronization operation"""
    sync_id: str
    direction: SyncDirection
    records_processed: int
    records_created: int
    records_updated: int
    records_skipped: int
    conflicts_resolved: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    duration_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QueryResult(BaseModel):
    """Result of Themis query"""
    query_id: str
    records: List[ThemisRecord]
    total_count: int
    page: int = 1
    page_size: int = 100
    has_more: bool = False
    execution_time_ms: int = 0


class ThemisAdapter(VCCServiceAdapter):
    """
    Adapter for Themis Unified Database Service
    
    Themis provides:
    - Unified query interface across VCC databases
    - Smart query routing
    - Cross-database transactions
    - Data synchronization between services
    
    Usage:
        async with ThemisAdapter(
            base_url="http://themis.local:8080"
        ) as themis:
            records = await themis.query("documents", {"status": "active"})
    """
    
    SERVICE_NAME = "themis"
    
    def __init__(
        self,
        base_url: str = "http://themis-service.covina.svc.cluster.local:8080",
        sync_enabled: bool = True,
        conflict_resolution: ConflictResolution = ConflictResolution.LATEST_WINS,
        **kwargs
    ):
        """
        Initialize Themis adapter
        
        Args:
            base_url: Themis service URL (on-premise)
            sync_enabled: Enable automatic synchronization
            conflict_resolution: Default conflict resolution strategy
            **kwargs: Additional adapter configuration
        """
        super().__init__(base_url=base_url, **kwargs)
        self.sync_enabled = sync_enabled
        self.conflict_resolution = conflict_resolution
        self._available_tables: List[str] = []
    
    async def connect(self) -> bool:
        """Connect to Themis service"""
        try:
            healthy = await self.health_check()
            if healthy:
                # Load available tables
                schema = await self._request("GET", "/api/v1/schema")
                self._available_tables = schema.get("tables", [])
                logger.info(f"Connected to Themis: {self.base_url}")
            return healthy
        except Exception as e:
            logger.error(f"Failed to connect to Themis: {e}")
            return False
    
    async def query(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        order_dir: str = "asc",
        page: int = 1,
        page_size: int = 100
    ) -> QueryResult:
        """
        Query records from Themis
        
        Args:
            table: Table name
            filters: Query filters
            fields: Fields to return (None = all)
            order_by: Field to order by
            order_dir: Order direction (asc/desc)
            page: Page number
            page_size: Records per page
            
        Returns:
            QueryResult with matching records
        """
        data = {
            "table": table,
            "filters": filters or {},
            "fields": fields,
            "order_by": order_by,
            "order_dir": order_dir,
            "page": page,
            "page_size": page_size
        }
        
        result = await self._request("POST", "/api/v1/query", data=data)
        
        return QueryResult(
            query_id=result.get("query_id", ""),
            records=[
                ThemisRecord(**r) for r in result.get("records", [])
            ],
            total_count=result.get("total_count", 0),
            page=page,
            page_size=page_size,
            has_more=result.get("has_more", False),
            execution_time_ms=result.get("execution_time_ms", 0)
        )
    
    async def get_record(
        self,
        table: str,
        record_id: str
    ) -> Optional[ThemisRecord]:
        """
        Get a specific record by ID
        
        Args:
            table: Table name
            record_id: Record identifier
            
        Returns:
            ThemisRecord or None if not found
        """
        try:
            result = await self._request(
                "GET", 
                f"/api/v1/tables/{table}/records/{record_id}"
            )
            if result:
                return ThemisRecord(**result)
        except VCCServiceError as e:
            if e.status_code == 404:
                return None
            raise
        
        return None
    
    async def insert_record(
        self,
        table: str,
        data: Dict[str, Any],
        sync_to_themis: bool = True
    ) -> ThemisRecord:
        """
        Insert a new record
        
        Args:
            table: Table name
            data: Record data
            sync_to_themis: Sync to Themis database
            
        Returns:
            Created record
        """
        payload = {
            "table": table,
            "data": data,
            "source_service": "covina",
            "sync": sync_to_themis
        }
        
        result = await self._request("POST", "/api/v1/records", data=payload)
        
        return ThemisRecord(**result)
    
    async def update_record(
        self,
        table: str,
        record_id: str,
        data: Dict[str, Any],
        sync_to_themis: bool = True
    ) -> ThemisRecord:
        """
        Update an existing record
        
        Args:
            table: Table name
            record_id: Record identifier
            data: Updated data
            sync_to_themis: Sync to Themis database
            
        Returns:
            Updated record
        """
        payload = {
            "data": data,
            "source_service": "covina",
            "sync": sync_to_themis
        }
        
        result = await self._request(
            "PUT",
            f"/api/v1/tables/{table}/records/{record_id}",
            data=payload
        )
        
        return ThemisRecord(**result)
    
    async def delete_record(
        self,
        table: str,
        record_id: str,
        sync_to_themis: bool = True
    ) -> bool:
        """
        Delete a record
        
        Args:
            table: Table name
            record_id: Record identifier
            sync_to_themis: Sync deletion to Themis
            
        Returns:
            True if deleted
        """
        params = {"sync": sync_to_themis}
        
        await self._request(
            "DELETE",
            f"/api/v1/tables/{table}/records/{record_id}",
            params=params
        )
        
        return True
    
    async def sync_data(
        self,
        table: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        since: Optional[datetime] = None,
        conflict_resolution: Optional[ConflictResolution] = None
    ) -> SyncResult:
        """
        Synchronize data between Covina and Themis
        
        Args:
            table: Table to synchronize
            direction: Sync direction
            since: Only sync records modified since this time
            conflict_resolution: Conflict resolution strategy
            
        Returns:
            SyncResult with statistics
        """
        data = {
            "table": table,
            "direction": direction.value,
            "since": since.isoformat() if since else None,
            "conflict_resolution": (
                conflict_resolution or self.conflict_resolution
            ).value
        }
        
        result = await self._request("POST", "/api/v1/sync", data=data)
        
        return SyncResult(
            sync_id=result.get("sync_id", ""),
            direction=direction,
            records_processed=result.get("records_processed", 0),
            records_created=result.get("records_created", 0),
            records_updated=result.get("records_updated", 0),
            records_skipped=result.get("records_skipped", 0),
            conflicts_resolved=result.get("conflicts_resolved", 0),
            errors=result.get("errors", []),
            duration_ms=result.get("duration_ms", 0)
        )
    
    async def get_sync_status(
        self,
        table: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get synchronization status
        
        Args:
            table: Specific table (None = all tables)
            
        Returns:
            Sync status information
        """
        params = {"table": table} if table else {}
        return await self._request("GET", "/api/v1/sync/status", params=params)
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute raw query (read-only)
        
        Args:
            query: Query string (Themis Query Language)
            params: Query parameters
            
        Returns:
            Query results
        """
        data = {
            "query": query,
            "params": params or {},
            "read_only": True
        }
        
        result = await self._request("POST", "/api/v1/execute", data=data)
        
        return result.get("results", [])
    
    async def bulk_insert(
        self,
        table: str,
        records: List[Dict[str, Any]],
        sync_to_themis: bool = True
    ) -> Dict[str, Any]:
        """
        Bulk insert multiple records
        
        Args:
            table: Table name
            records: List of record data
            sync_to_themis: Sync to Themis database
            
        Returns:
            Bulk operation result
        """
        data = {
            "table": table,
            "records": records,
            "source_service": "covina",
            "sync": sync_to_themis
        }
        
        return await self._request("POST", "/api/v1/bulk/insert", data=data)
    
    async def get_schema(
        self,
        table: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get table schema
        
        Args:
            table: Specific table (None = all tables)
            
        Returns:
            Schema information
        """
        if table:
            return await self._request("GET", f"/api/v1/schema/tables/{table}")
        return await self._request("GET", "/api/v1/schema")
    
    @property
    def available_tables(self) -> List[str]:
        """Get available tables"""
        return self._available_tables
