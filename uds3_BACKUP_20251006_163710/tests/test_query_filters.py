"""
Unit Tests for Query Filters Module
====================================

Tests BaseFilter, FilterOperator, and fluent API.

Author: UDS3 Team
Date: 1. Oktober 2025
"""

import pytest
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock

from uds3_query_filters import (
    BaseFilter,
    FilterOperator,
    LogicalOperator,
    SortOrder,
    FilterCondition,
    SortField,
    QueryResult,
)


# ============================================================================
# Concrete Filter Implementation (for testing)
# ============================================================================

class MockFilter(BaseFilter):
    """Concrete implementation of BaseFilter for testing"""
    
    def __init__(self, backend=None):
        super().__init__(backend)
        self.mock_results = []
        self.mock_count = 0
    
    def execute(self) -> QueryResult:
        """Mock execute"""
        # Apply limit/offset to mock results
        start = self.offset_value
        end = start + self.limit_value if self.limit_value else None
        
        results = self.mock_results[start:end]
        
        return QueryResult(
            success=True,
            results=results,
            total_count=self.mock_count or len(self.mock_results),
            database="mock"
        )
    
    def count(self) -> int:
        """Mock count"""
        return self.mock_count or len(self.mock_results)
    
    def to_query(self) -> Dict:
        """Mock to_query"""
        return {
            "conditions": [c.to_dict() for c in self.conditions],
            "sort": [s.to_dict() for s in self.sort_fields],
            "limit": self.limit_value,
            "offset": self.offset_value
        }


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_filter():
    """Create MockFilter instance"""
    return MockFilter()


@pytest.fixture
def mock_backend():
    """Create mock backend"""
    return Mock()


@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        {"id": "doc1", "title": "First", "status": "active", "priority": 1},
        {"id": "doc2", "title": "Second", "status": "inactive", "priority": 2},
        {"id": "doc3", "title": "Third", "status": "active", "priority": 3},
        {"id": "doc4", "title": "Fourth", "status": "archived", "priority": 1},
        {"id": "doc5", "title": "Fifth", "status": "active", "priority": 2},
    ]


# ============================================================================
# FilterOperator Tests
# ============================================================================

class TestFilterOperator:
    """Test FilterOperator enum"""
    
    def test_equality_operators(self):
        """Test equality operators"""
        assert FilterOperator.EQ.value == "=="
        assert FilterOperator.NE.value == "!="
    
    def test_comparison_operators(self):
        """Test comparison operators"""
        assert FilterOperator.GT.value == ">"
        assert FilterOperator.LT.value == "<"
        assert FilterOperator.GTE.value == ">="
        assert FilterOperator.LTE.value == "<="
    
    def test_membership_operators(self):
        """Test membership operators"""
        assert FilterOperator.IN.value == "in"
        assert FilterOperator.NOT_IN.value == "not_in"
    
    def test_string_operators(self):
        """Test string operators"""
        assert FilterOperator.CONTAINS.value == "contains"
        assert FilterOperator.STARTS_WITH.value == "starts_with"
        assert FilterOperator.ENDS_WITH.value == "ends_with"
        assert FilterOperator.REGEX.value == "regex"


# ============================================================================
# FilterCondition Tests
# ============================================================================

class TestFilterCondition:
    """Test FilterCondition dataclass"""
    
    def test_create_condition(self):
        """Test creating a filter condition"""
        condition = FilterCondition(
            field="status",
            operator=FilterOperator.EQ,
            value="active"
        )
        
        assert condition.field == "status"
        assert condition.operator == FilterOperator.EQ
        assert condition.value == "active"
        assert condition.logical_op == LogicalOperator.AND
    
    def test_condition_to_dict(self):
        """Test condition to_dict()"""
        condition = FilterCondition(
            field="priority",
            operator=FilterOperator.GT,
            value=5
        )
        
        result = condition.to_dict()
        
        assert result["field"] == "priority"
        assert result["operator"] == ">"
        assert result["value"] == 5
        assert result["logical_op"] == "and"
    
    def test_condition_repr(self):
        """Test condition string representation"""
        condition = FilterCondition(
            field="name",
            operator=FilterOperator.CONTAINS,
            value="test"
        )
        
        repr_str = repr(condition)
        assert "name" in repr_str
        assert "contains" in repr_str


# ============================================================================
# QueryResult Tests
# ============================================================================

class TestQueryResult:
    """Test QueryResult dataclass"""
    
    def test_create_result(self):
        """Test creating a query result"""
        result = QueryResult(
            success=True,
            results=[{"id": "1"}, {"id": "2"}],
            total_count=10,
            query_time_ms=25.5
        )
        
        assert result.success is True
        assert len(result.results) == 2
        assert result.total_count == 10
        assert result.query_time_ms == 25.5
    
    def test_result_to_dict(self):
        """Test result to_dict()"""
        result = QueryResult(
            success=True,
            results=[{"id": "1"}],
            total_count=5,
            database="vector"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["count"] == 1
        assert result_dict["total_count"] == 5
        assert result_dict["database"] == "vector"


# ============================================================================
# BaseFilter Basic Tests
# ============================================================================

class TestBaseFilterBasics:
    """Test basic BaseFilter functionality"""
    
    def test_create_filter(self, mock_backend):
        """Test creating a filter"""
        filter = MockFilter(mock_backend)
        
        assert filter.backend == mock_backend
        assert len(filter.conditions) == 0
        assert len(filter.sort_fields) == 0
        assert filter.limit_value is None
        assert filter.offset_value == 0
    
    def test_has_conditions(self, mock_filter):
        """Test has_conditions()"""
        assert mock_filter.has_conditions() is False
        
        mock_filter.where("field", FilterOperator.EQ, "value")
        
        assert mock_filter.has_conditions() is True
    
    def test_reset(self, mock_filter):
        """Test reset()"""
        mock_filter.where("field", FilterOperator.EQ, "value")
        mock_filter.order_by("created_at")
        mock_filter.limit(10)
        
        assert mock_filter.has_conditions() is True
        
        mock_filter.reset()
        
        assert mock_filter.has_conditions() is False
        assert len(mock_filter.sort_fields) == 0
        assert mock_filter.limit_value is None


# ============================================================================
# Fluent API Tests - WHERE Conditions
# ============================================================================

class TestWhereConditions:
    """Test WHERE condition methods"""
    
    def test_where_basic(self, mock_filter):
        """Test basic where()"""
        result = mock_filter.where("status", FilterOperator.EQ, "active")
        
        assert result == mock_filter  # Fluent API
        assert len(mock_filter.conditions) == 1
        
        condition = mock_filter.conditions[0]
        assert condition.field == "status"
        assert condition.operator == FilterOperator.EQ
        assert condition.value == "active"
    
    def test_where_string_operator(self, mock_filter):
        """Test where() with string operator"""
        mock_filter.where("priority", ">", 5)
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.GT
    
    def test_and_where(self, mock_filter):
        """Test and_where()"""
        mock_filter.where("status", FilterOperator.EQ, "active")
        mock_filter.and_where("priority", FilterOperator.GT, 3)
        
        assert len(mock_filter.conditions) == 2
        assert mock_filter.conditions[1].logical_op == LogicalOperator.AND
    
    def test_or_where(self, mock_filter):
        """Test or_where()"""
        mock_filter.where("status", FilterOperator.EQ, "active")
        mock_filter.or_where("status", FilterOperator.EQ, "pending")
        
        assert len(mock_filter.conditions) == 2
        assert mock_filter.conditions[1].logical_op == LogicalOperator.OR
    
    def test_where_in(self, mock_filter):
        """Test where_in()"""
        mock_filter.where_in("status", ["active", "pending", "review"])
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.IN
        assert condition.value == ["active", "pending", "review"]
    
    def test_where_not_in(self, mock_filter):
        """Test where_not_in()"""
        mock_filter.where_not_in("status", ["archived", "deleted"])
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.NOT_IN
    
    def test_where_between(self, mock_filter):
        """Test where_between()"""
        mock_filter.where_between("priority", 1, 5)
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.BETWEEN
        assert condition.value == (1, 5)
    
    def test_where_null(self, mock_filter):
        """Test where_null()"""
        mock_filter.where_null("deleted_at")
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.IS_NULL
    
    def test_where_not_null(self, mock_filter):
        """Test where_not_null()"""
        mock_filter.where_not_null("created_at")
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.IS_NOT_NULL
    
    def test_where_contains(self, mock_filter):
        """Test where_contains()"""
        mock_filter.where_contains("title", "test")
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.CONTAINS
        assert condition.value == "test"
    
    def test_where_starts_with(self, mock_filter):
        """Test where_starts_with()"""
        mock_filter.where_starts_with("title", "Doc")
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.STARTS_WITH
    
    def test_where_ends_with(self, mock_filter):
        """Test where_ends_with()"""
        mock_filter.where_ends_with("filename", ".pdf")
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.ENDS_WITH
    
    def test_where_regex(self, mock_filter):
        """Test where_regex()"""
        mock_filter.where_regex("email", r".*@example\.com")
        
        condition = mock_filter.conditions[0]
        assert condition.operator == FilterOperator.REGEX


# ============================================================================
# Fluent API Tests - Sorting & Pagination
# ============================================================================

class TestSortingAndPagination:
    """Test sorting and pagination methods"""
    
    def test_order_by(self, mock_filter):
        """Test order_by()"""
        result = mock_filter.order_by("created_at", SortOrder.DESC)
        
        assert result == mock_filter  # Fluent API
        assert len(mock_filter.sort_fields) == 1
        
        sort = mock_filter.sort_fields[0]
        assert sort.field == "created_at"
        assert sort.order == SortOrder.DESC
    
    def test_order_by_string(self, mock_filter):
        """Test order_by() with string order"""
        mock_filter.order_by("priority", "asc")
        
        sort = mock_filter.sort_fields[0]
        assert sort.order == SortOrder.ASC
    
    def test_multiple_order_by(self, mock_filter):
        """Test multiple order_by()"""
        mock_filter.order_by("priority", SortOrder.DESC)
        mock_filter.order_by("created_at", SortOrder.ASC)
        
        assert len(mock_filter.sort_fields) == 2
    
    def test_limit(self, mock_filter):
        """Test limit()"""
        result = mock_filter.limit(50)
        
        assert result == mock_filter
        assert mock_filter.limit_value == 50
    
    def test_limit_invalid(self, mock_filter):
        """Test limit() with invalid value"""
        with pytest.raises(ValueError):
            mock_filter.limit(-1)
    
    def test_offset(self, mock_filter):
        """Test offset()"""
        result = mock_filter.offset(100)
        
        assert result == mock_filter
        assert mock_filter.offset_value == 100
    
    def test_offset_invalid(self, mock_filter):
        """Test offset() with invalid value"""
        with pytest.raises(ValueError):
            mock_filter.offset(-5)
    
    def test_paginate(self, mock_filter):
        """Test paginate()"""
        mock_filter.paginate(page=3, per_page=20)
        
        assert mock_filter.limit_value == 20
        assert mock_filter.offset_value == 40  # (3-1) * 20
    
    def test_paginate_first_page(self, mock_filter):
        """Test paginate() first page"""
        mock_filter.paginate(page=1, per_page=50)
        
        assert mock_filter.limit_value == 50
        assert mock_filter.offset_value == 0
    
    def test_paginate_invalid(self, mock_filter):
        """Test paginate() with invalid page"""
        with pytest.raises(ValueError):
            mock_filter.paginate(page=0, per_page=20)


# ============================================================================
# Query Execution Tests
# ============================================================================

class TestQueryExecution:
    """Test query execution methods"""
    
    def test_execute(self, mock_filter, sample_documents):
        """Test execute()"""
        mock_filter.mock_results = sample_documents
        
        result = mock_filter.execute()
        
        assert isinstance(result, QueryResult)
        assert result.success is True
        assert len(result.results) == 5
    
    def test_execute_with_limit(self, mock_filter, sample_documents):
        """Test execute() with limit"""
        mock_filter.mock_results = sample_documents
        mock_filter.limit(2)
        
        result = mock_filter.execute()
        
        assert len(result.results) == 2
    
    def test_execute_with_offset(self, mock_filter, sample_documents):
        """Test execute() with offset"""
        mock_filter.mock_results = sample_documents
        mock_filter.offset(2)
        
        result = mock_filter.execute()
        
        assert len(result.results) == 3
        assert result.results[0]["id"] == "doc3"
    
    def test_execute_with_limit_and_offset(self, mock_filter, sample_documents):
        """Test execute() with limit and offset"""
        mock_filter.mock_results = sample_documents
        mock_filter.limit(2).offset(1)
        
        result = mock_filter.execute()
        
        assert len(result.results) == 2
        assert result.results[0]["id"] == "doc2"
        assert result.results[1]["id"] == "doc3"
    
    def test_count(self, mock_filter):
        """Test count()"""
        mock_filter.mock_count = 42
        
        count = mock_filter.count()
        
        assert count == 42
    
    def test_first(self, mock_filter, sample_documents):
        """Test first()"""
        mock_filter.mock_results = sample_documents
        
        first_doc = mock_filter.first()
        
        assert first_doc is not None
        assert first_doc["id"] == "doc1"
    
    def test_first_empty(self, mock_filter):
        """Test first() with no results"""
        mock_filter.mock_results = []
        
        first_doc = mock_filter.first()
        
        assert first_doc is None
    
    def test_exists(self, mock_filter):
        """Test exists()"""
        mock_filter.mock_count = 5
        
        assert mock_filter.exists() is True
        
        mock_filter.mock_count = 0
        
        assert mock_filter.exists() is False
    
    def test_to_query(self, mock_filter):
        """Test to_query()"""
        mock_filter.where("status", FilterOperator.EQ, "active")
        mock_filter.order_by("created_at", SortOrder.DESC)
        mock_filter.limit(10)
        
        query = mock_filter.to_query()
        
        assert "conditions" in query
        assert "sort" in query
        assert query["limit"] == 10


# ============================================================================
# Fluent API Chaining Tests
# ============================================================================

class TestFluentAPIChaining:
    """Test fluent API method chaining"""
    
    def test_complex_chain(self, mock_filter):
        """Test complex method chain"""
        result = (mock_filter
            .where("status", FilterOperator.EQ, "active")
            .and_where("priority", FilterOperator.GT, 3)
            .or_where("urgent", FilterOperator.EQ, True)
            .order_by("created_at", SortOrder.DESC)
            .limit(50)
            .offset(10)
        )
        
        assert result == mock_filter
        assert len(mock_filter.conditions) == 3
        assert len(mock_filter.sort_fields) == 1
        assert mock_filter.limit_value == 50
        assert mock_filter.offset_value == 10
    
    def test_pagination_chain(self, mock_filter, sample_documents):
        """Test pagination chain"""
        mock_filter.mock_results = sample_documents
        
        result = (mock_filter
            .where("status", FilterOperator.EQ, "active")
            .order_by("priority")
            .paginate(page=2, per_page=2)
            .execute()
        )
        
        assert len(result.results) == 2
        assert mock_filter.offset_value == 2


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_filter(self, mock_filter):
        """Test filter with no conditions"""
        assert mock_filter.has_conditions() is False
        
        query = mock_filter.to_query()
        assert len(query["conditions"]) == 0
    
    def test_get_conditions_copy(self, mock_filter):
        """Test get_conditions() returns copy"""
        mock_filter.where("field", FilterOperator.EQ, "value")
        
        conditions = mock_filter.get_conditions()
        conditions.clear()
        
        # Original should still have condition
        assert len(mock_filter.conditions) == 1
    
    def test_repr(self, mock_filter):
        """Test __repr__()"""
        mock_filter.where("field", FilterOperator.EQ, "value")
        mock_filter.limit(10)
        
        repr_str = repr(mock_filter)
        
        assert "MockFilter" in repr_str
        assert "conditions=1" in repr_str
        assert "limit=10" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
