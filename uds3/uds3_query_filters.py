"""
UDS3 Query Filters Module
==========================

Base filter classes and operators for querying across all databases.

Provides:
- Abstract BaseFilter with fluent API
- FilterOperator enum for common operations
- Query builders for Vector, Graph, Relational, File Storage
- PolyglotQuery coordinator for cross-database queries

Author: UDS3 Team
Date: 1. Oktober 2025
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Filter Operators
# ============================================================================

class FilterOperator(Enum):
    """Common filter operators for all database types"""
    
    # Equality
    EQ = "=="          # Equal
    NE = "!="          # Not equal
    
    # Comparison
    GT = ">"           # Greater than
    LT = "<"           # Less than
    GTE = ">="         # Greater than or equal
    LTE = "<="         # Less than or equal
    
    # Membership
    IN = "in"          # Value in list
    NOT_IN = "not_in"  # Value not in list
    
    # String operations
    CONTAINS = "contains"           # String contains substring
    NOT_CONTAINS = "not_contains"   # String doesn't contain substring
    STARTS_WITH = "starts_with"     # String starts with prefix
    ENDS_WITH = "ends_with"         # String ends with suffix
    REGEX = "regex"                 # Regex match
    
    # Null checks
    IS_NULL = "is_null"         # Value is null/None
    IS_NOT_NULL = "is_not_null" # Value is not null/None
    
    # Range
    BETWEEN = "between"  # Value between min and max


class LogicalOperator(Enum):
    """Logical operators for combining filters"""
    AND = "and"
    OR = "or"
    NOT = "not"


class SortOrder(Enum):
    """Sort order for results"""
    ASC = "asc"     # Ascending
    DESC = "desc"   # Descending


# ============================================================================
# Filter Condition
# ============================================================================

@dataclass
class FilterCondition:
    """Represents a single filter condition"""
    field: str
    operator: FilterOperator
    value: Any
    logical_op: LogicalOperator = LogicalOperator.AND
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "logical_op": self.logical_op.value
        }
    
    def __repr__(self) -> str:
        return f"FilterCondition({self.field} {self.operator.value} {self.value})"


@dataclass
class SortField:
    """Represents a sort field"""
    field: str
    order: SortOrder = SortOrder.ASC
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "field": self.field,
            "order": self.order.value
        }


# ============================================================================
# Query Result
# ============================================================================

@dataclass
class QueryResult:
    """Result of a query operation"""
    success: bool
    results: List[Dict[str, Any]]
    total_count: Optional[int] = None
    has_more: bool = False
    query_time_ms: Optional[float] = None
    database: Optional[str] = None
    errors: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "results": self.results,
            "count": len(self.results)
        }
        if self.total_count is not None:
            result["total_count"] = self.total_count
        if self.has_more:
            result["has_more"] = self.has_more
        if self.query_time_ms is not None:
            result["query_time_ms"] = self.query_time_ms
        if self.database:
            result["database"] = self.database
        if self.errors:
            result["errors"] = self.errors
        return result


# ============================================================================
# Base Filter (Abstract)
# ============================================================================

class BaseFilter(ABC):
    """
    Abstract base class for all database filters.
    
    Provides fluent API for building queries:
        filter = SomeFilter(backend)
            .where("field", FilterOperator.EQ, "value")
            .and_where("other", FilterOperator.GT, 10)
            .order_by("created_at", SortOrder.DESC)
            .limit(50)
            .offset(0)
            .execute()
    
    Subclasses must implement:
    - execute(): Execute the query and return results
    - count(): Count matching documents
    - to_query(): Convert filter to database-specific query
    """
    
    def __init__(self, backend=None):
        """
        Initialize filter with backend.
        
        Args:
            backend: Database backend instance (optional)
        """
        self.backend = backend
        self.conditions: List[FilterCondition] = []
        self.sort_fields: List[SortField] = []
        self.limit_value: Optional[int] = None
        self.offset_value: int = 0
        self._negated: bool = False
        
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    # ========================================================================
    # Condition Methods (Fluent API)
    # ========================================================================
    
    def where(
        self, 
        field: str, 
        operator: Union[FilterOperator, str], 
        value: Any
    ) -> 'BaseFilter':
        """
        Add WHERE condition (starts new condition chain).
        
        Args:
            field: Field name
            operator: Filter operator
            value: Comparison value
        
        Returns:
            Self for chaining
        
        Example:
            filter.where("status", FilterOperator.EQ, "active")
        """
        if isinstance(operator, str):
            operator = FilterOperator(operator)
        
        condition = FilterCondition(
            field=field,
            operator=operator,
            value=value,
            logical_op=LogicalOperator.AND
        )
        self.conditions.append(condition)
        
        return self
    
    def and_where(
        self, 
        field: str, 
        operator: Union[FilterOperator, str], 
        value: Any
    ) -> 'BaseFilter':
        """
        Add AND WHERE condition.
        
        Args:
            field: Field name
            operator: Filter operator
            value: Comparison value
        
        Returns:
            Self for chaining
        """
        if isinstance(operator, str):
            operator = FilterOperator(operator)
        
        condition = FilterCondition(
            field=field,
            operator=operator,
            value=value,
            logical_op=LogicalOperator.AND
        )
        self.conditions.append(condition)
        
        return self
    
    def or_where(
        self, 
        field: str, 
        operator: Union[FilterOperator, str], 
        value: Any
    ) -> 'BaseFilter':
        """
        Add OR WHERE condition.
        
        Args:
            field: Field name
            operator: Filter operator
            value: Comparison value
        
        Returns:
            Self for chaining
        """
        if isinstance(operator, str):
            operator = FilterOperator(operator)
        
        condition = FilterCondition(
            field=field,
            operator=operator,
            value=value,
            logical_op=LogicalOperator.OR
        )
        self.conditions.append(condition)
        
        return self
    
    def where_in(self, field: str, values: List[Any]) -> 'BaseFilter':
        """
        Add WHERE IN condition.
        
        Args:
            field: Field name
            values: List of values
        
        Returns:
            Self for chaining
        """
        return self.where(field, FilterOperator.IN, values)
    
    def where_not_in(self, field: str, values: List[Any]) -> 'BaseFilter':
        """Add WHERE NOT IN condition"""
        return self.where(field, FilterOperator.NOT_IN, values)
    
    def where_between(
        self, 
        field: str, 
        min_value: Any, 
        max_value: Any
    ) -> 'BaseFilter':
        """
        Add WHERE BETWEEN condition.
        
        Args:
            field: Field name
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
        
        Returns:
            Self for chaining
        """
        return self.where(field, FilterOperator.BETWEEN, (min_value, max_value))
    
    def where_null(self, field: str) -> 'BaseFilter':
        """Add WHERE IS NULL condition"""
        return self.where(field, FilterOperator.IS_NULL, None)
    
    def where_not_null(self, field: str) -> 'BaseFilter':
        """Add WHERE IS NOT NULL condition"""
        return self.where(field, FilterOperator.IS_NOT_NULL, None)
    
    def where_contains(self, field: str, substring: str) -> 'BaseFilter':
        """Add WHERE CONTAINS condition (string contains substring)"""
        return self.where(field, FilterOperator.CONTAINS, substring)
    
    def where_starts_with(self, field: str, prefix: str) -> 'BaseFilter':
        """Add WHERE STARTS WITH condition"""
        return self.where(field, FilterOperator.STARTS_WITH, prefix)
    
    def where_ends_with(self, field: str, suffix: str) -> 'BaseFilter':
        """Add WHERE ENDS WITH condition"""
        return self.where(field, FilterOperator.ENDS_WITH, suffix)
    
    def where_regex(self, field: str, pattern: str) -> 'BaseFilter':
        """Add WHERE REGEX condition"""
        return self.where(field, FilterOperator.REGEX, pattern)
    
    # ========================================================================
    # Sorting & Pagination
    # ========================================================================
    
    def order_by(
        self, 
        field: str, 
        order: Union[SortOrder, str] = SortOrder.ASC
    ) -> 'BaseFilter':
        """
        Add ORDER BY clause.
        
        Args:
            field: Field to sort by
            order: Sort order (ASC or DESC)
        
        Returns:
            Self for chaining
        """
        if isinstance(order, str):
            order = SortOrder(order.lower())
        
        sort_field = SortField(field=field, order=order)
        self.sort_fields.append(sort_field)
        
        return self
    
    def limit(self, n: int) -> 'BaseFilter':
        """
        Set LIMIT (maximum number of results).
        
        Args:
            n: Maximum results
        
        Returns:
            Self for chaining
        """
        if n < 0:
            raise ValueError("Limit must be non-negative")
        
        self.limit_value = n
        return self
    
    def offset(self, n: int) -> 'BaseFilter':
        """
        Set OFFSET (skip first N results).
        
        Args:
            n: Number of results to skip
        
        Returns:
            Self for chaining
        """
        if n < 0:
            raise ValueError("Offset must be non-negative")
        
        self.offset_value = n
        return self
    
    def paginate(self, page: int, per_page: int = 50) -> 'BaseFilter':
        """
        Set pagination (convenience method).
        
        Args:
            page: Page number (1-indexed)
            per_page: Results per page
        
        Returns:
            Self for chaining
        """
        if page < 1:
            raise ValueError("Page must be >= 1")
        
        self.limit_value = per_page
        self.offset_value = (page - 1) * per_page
        
        return self
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def reset(self) -> 'BaseFilter':
        """Reset all conditions and settings"""
        self.conditions.clear()
        self.sort_fields.clear()
        self.limit_value = None
        self.offset_value = 0
        self._negated = False
        
        return self
    
    def has_conditions(self) -> bool:
        """Check if filter has any conditions"""
        return len(self.conditions) > 0
    
    def get_conditions(self) -> List[FilterCondition]:
        """Get all conditions"""
        return self.conditions.copy()
    
    def get_sort_fields(self) -> List[SortField]:
        """Get all sort fields"""
        return self.sort_fields.copy()
    
    # ========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # ========================================================================
    
    @abstractmethod
    def execute(self) -> QueryResult:
        """
        Execute the query and return results.
        
        Returns:
            QueryResult with matching documents
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Count matching documents without fetching them.
        
        Returns:
            Number of matching documents
        """
        pass
    
    @abstractmethod
    def to_query(self) -> Any:
        """
        Convert filter to database-specific query format.
        
        Returns:
            Database-specific query object
        """
        pass
    
    # ========================================================================
    # Optional Methods (can be overridden)
    # ========================================================================
    
    def first(self) -> Optional[Dict[str, Any]]:
        """
        Get first matching document.
        
        Returns:
            First document or None
        """
        original_limit = self.limit_value
        self.limit_value = 1
        
        result = self.execute()
        
        self.limit_value = original_limit
        
        return result.results[0] if result.results else None
    
    def exists(self) -> bool:
        """
        Check if any documents match the filter.
        
        Returns:
            True if at least one document matches
        """
        return self.count() > 0
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"{self.__class__.__name__}("
            f"conditions={len(self.conditions)}, "
            f"sort={len(self.sort_fields)}, "
            f"limit={self.limit_value}, "
            f"offset={self.offset_value})"
        )


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Enums
    'FilterOperator',
    'LogicalOperator',
    'SortOrder',
    
    # Data Classes
    'FilterCondition',
    'SortField',
    'QueryResult',
    
    # Base Classes
    'BaseFilter',
]
