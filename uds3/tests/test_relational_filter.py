"""
Tests for UDS3 Relational Filter Module
========================================

Comprehensive test suite for RelationalFilter with SQL query building.

Test Coverage:
- SELECT clause (fields, aggregates, DISTINCT)
- FROM clause
- JOIN operations (INNER, LEFT, RIGHT, FULL)
- WHERE conditions with parameter binding
- GROUP BY and HAVING
- ORDER BY, LIMIT, OFFSET
- SQL generation and parameter binding
- Edge cases and error handling

Author: UDS3 Team
Date: 2. Oktober 2025
"""

import pytest
from typing import List, Tuple
from unittest.mock import Mock, MagicMock

from uds3_relational_filter import (
    RelationalFilter,
    create_relational_filter,
    SelectField,
    JoinClause,
    JoinType,
    SQLDialect,
    AggregateFunction,
    GroupByClause,
    RelationalQueryResult
)

from uds3_query_filters import (
    FilterOperator,
    FilterCondition,
    SortOrder,
    LogicalOperator
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_sqlite_backend():
    """Mock SQLite database backend"""
    backend = Mock()
    
    # Mock execute method that returns a cursor-like object
    mock_cursor = Mock()
    mock_cursor.fetchall = MagicMock(return_value=[
        {"id": 1, "name": "Test"}
    ])
    mock_cursor.fetchone = MagicMock(return_value=[10])  # For COUNT
    
    backend.execute = MagicMock(return_value=mock_cursor)
    return backend


@pytest.fixture
def mock_postgresql_backend():
    """Mock PostgreSQL database backend"""
    backend = Mock()
    backend.execute_query = MagicMock(return_value=[
        {"id": 1, "name": "Test User", "email": "test@example.com"}
    ])
    return backend


@pytest.fixture
def relational_filter():
    """Basic RelationalFilter instance"""
    return RelationalFilter(dialect=SQLDialect.SQLITE)


@pytest.fixture
def relational_filter_with_backend(mock_sqlite_backend):
    """RelationalFilter with mock backend"""
    return RelationalFilter(
        backend=mock_sqlite_backend,
        dialect=SQLDialect.SQLITE
    )


# ============================================================================
# Test SelectField
# ============================================================================

class TestSelectField:
    """Test SelectField dataclass"""
    
    def test_select_field_simple(self):
        """Test simple SELECT field"""
        field = SelectField(expression="name")
        assert field.to_sql() == "name"
    
    def test_select_field_with_alias(self):
        """Test SELECT field with alias"""
        field = SelectField(expression="user_name", alias="name")
        assert field.to_sql() == "user_name AS name"
    
    def test_select_field_with_aggregate(self):
        """Test SELECT field with aggregate function"""
        field = SelectField(
            expression="id",
            aggregate=AggregateFunction.COUNT,
            alias="total"
        )
        assert field.to_sql() == "COUNT(id) AS total"
    
    def test_select_field_aggregate_no_alias(self):
        """Test aggregate without alias"""
        field = SelectField(
            expression="amount",
            aggregate=AggregateFunction.SUM
        )
        assert field.to_sql() == "SUM(amount)"


# ============================================================================
# Test JoinClause
# ============================================================================

class TestJoinClause:
    """Test JoinClause dataclass"""
    
    def test_inner_join_clause(self):
        """Test INNER JOIN clause"""
        join = JoinClause(
            join_type=JoinType.INNER,
            table="orders",
            on_left="users.id",
            on_right="orders.user_id"
        )
        assert join.to_sql() == "INNER JOIN orders ON users.id = orders.user_id"
    
    def test_left_join_clause(self):
        """Test LEFT JOIN clause"""
        join = JoinClause(
            join_type=JoinType.LEFT,
            table="orders",
            on_left="users.id",
            on_right="orders.user_id"
        )
        assert join.to_sql() == "LEFT JOIN orders ON users.id = orders.user_id"
    
    def test_join_clause_with_alias(self):
        """Test JOIN with table alias"""
        join = JoinClause(
            join_type=JoinType.LEFT,
            table="orders",
            on_left="users.id",
            on_right="o.user_id",
            alias="o"
        )
        assert join.to_sql() == "LEFT JOIN orders AS o ON users.id = o.user_id"


# ============================================================================
# Test RelationalFilter - Basics
# ============================================================================

class TestRelationalFilterBasics:
    """Test basic RelationalFilter functionality"""
    
    def test_initialization_default(self):
        """Test default initialization"""
        filter = RelationalFilter()
        assert filter.dialect == SQLDialect.SQLITE
        assert filter.select_fields == []
        assert filter.from_table_name is None
        assert filter.join_clauses == []
        assert filter.distinct is False
    
    def test_initialization_with_dialect(self):
        """Test initialization with PostgreSQL dialect"""
        filter = RelationalFilter(dialect=SQLDialect.POSTGRESQL)
        assert filter.dialect == SQLDialect.POSTGRESQL
    
    def test_initialization_with_backend(self, mock_sqlite_backend):
        """Test initialization with backend"""
        filter = RelationalFilter(backend=mock_sqlite_backend)
        assert filter.backend == mock_sqlite_backend
    
    def test_factory_function(self):
        """Test create_relational_filter factory"""
        filter = create_relational_filter(dialect=SQLDialect.SQLITE)
        assert isinstance(filter, RelationalFilter)
        assert filter.dialect == SQLDialect.SQLITE


# ============================================================================
# Test SELECT Clause
# ============================================================================

class TestSelectClause:
    """Test SELECT clause methods"""
    
    def test_select_single_field(self, relational_filter):
        """Test SELECT with single field"""
        filter = relational_filter.select("name")
        assert len(filter.select_fields) == 1
        assert filter.select_fields[0].expression == "name"
    
    def test_select_multiple_fields(self, relational_filter):
        """Test SELECT with multiple fields"""
        filter = relational_filter.select("id", "name", "email")
        assert len(filter.select_fields) == 3
        assert filter.select_fields[0].expression == "id"
        assert filter.select_fields[1].expression == "name"
        assert filter.select_fields[2].expression == "email"
    
    def test_select_aggregate_count(self, relational_filter):
        """Test SELECT with COUNT aggregate"""
        filter = relational_filter.select_aggregate(
            AggregateFunction.COUNT, "*", "total"
        )
        assert len(filter.select_fields) == 1
        field = filter.select_fields[0]
        assert field.aggregate == AggregateFunction.COUNT
        assert field.expression == "*"
        assert field.alias == "total"
    
    def test_select_aggregate_sum(self, relational_filter):
        """Test SELECT with SUM aggregate"""
        filter = relational_filter.select_aggregate(
            AggregateFunction.SUM, "amount", "total_amount"
        )
        field = filter.select_fields[0]
        assert field.aggregate == AggregateFunction.SUM
        assert field.to_sql() == "SUM(amount) AS total_amount"
    
    def test_select_distinct(self, relational_filter):
        """Test SELECT DISTINCT"""
        filter = relational_filter.select("country").select_distinct()
        assert filter.distinct is True
    
    def test_select_count_convenience(self, relational_filter):
        """Test select_count convenience method"""
        filter = relational_filter.select_count("total_users")
        assert len(filter.select_fields) == 1
        field = filter.select_fields[0]
        assert field.aggregate == AggregateFunction.COUNT
        assert field.expression == "*"
        assert field.alias == "total_users"
    
    def test_select_chaining(self, relational_filter):
        """Test SELECT method chaining"""
        filter = relational_filter \
            .select("id", "name") \
            .select_aggregate(AggregateFunction.COUNT, "orders.id", "order_count")
        
        assert len(filter.select_fields) == 3


# ============================================================================
# Test FROM Clause
# ============================================================================

class TestFromClause:
    """Test FROM clause methods"""
    
    def test_from_table_simple(self, relational_filter):
        """Test simple FROM table"""
        filter = relational_filter.from_table("users")
        assert filter.from_table_name == "users"
        assert filter.from_table_alias is None
    
    def test_from_table_with_alias(self, relational_filter):
        """Test FROM table with alias"""
        filter = relational_filter.from_table("users", "u")
        assert filter.from_table_name == "users"
        assert filter.from_table_alias == "u"


# ============================================================================
# Test JOIN Operations
# ============================================================================

class TestJoinOperations:
    """Test JOIN operations"""
    
    def test_inner_join(self, relational_filter):
        """Test INNER JOIN"""
        filter = relational_filter.inner_join(
            "orders", "users.id", "orders.user_id"
        )
        assert len(filter.join_clauses) == 1
        join = filter.join_clauses[0]
        assert join.join_type == JoinType.INNER
        assert join.table == "orders"
        assert join.on_left == "users.id"
        assert join.on_right == "orders.user_id"
    
    def test_left_join(self, relational_filter):
        """Test LEFT JOIN"""
        filter = relational_filter.left_join(
            "orders", "users.id", "orders.user_id"
        )
        join = filter.join_clauses[0]
        assert join.join_type == JoinType.LEFT
    
    def test_right_join(self, relational_filter):
        """Test RIGHT JOIN"""
        filter = relational_filter.right_join(
            "orders", "users.id", "orders.user_id"
        )
        join = filter.join_clauses[0]
        assert join.join_type == JoinType.RIGHT
    
    def test_full_join(self, relational_filter):
        """Test FULL OUTER JOIN"""
        filter = relational_filter.full_join(
            "orders", "users.id", "orders.user_id"
        )
        join = filter.join_clauses[0]
        assert join.join_type == JoinType.FULL
    
    def test_join_with_alias(self, relational_filter):
        """Test JOIN with table alias"""
        filter = relational_filter.left_join(
            "orders", "users.id", "o.user_id", alias="o"
        )
        join = filter.join_clauses[0]
        assert join.alias == "o"
    
    def test_multiple_joins(self, relational_filter):
        """Test multiple JOINs"""
        filter = relational_filter \
            .left_join("orders", "users.id", "orders.user_id") \
            .inner_join("products", "orders.product_id", "products.id")
        
        assert len(filter.join_clauses) == 2
        assert filter.join_clauses[0].table == "orders"
        assert filter.join_clauses[1].table == "products"


# ============================================================================
# Test WHERE Conditions
# ============================================================================

class TestWhereConditions:
    """Test WHERE clause conditions"""
    
    def test_where_equality(self, relational_filter):
        """Test WHERE with equality"""
        filter = relational_filter.where("active", FilterOperator.EQ, True)
        assert len(filter.conditions) == 1
        assert filter.conditions[0].field == "active"
        assert filter.conditions[0].operator == FilterOperator.EQ
        assert filter.conditions[0].value is True
    
    def test_where_comparison(self, relational_filter):
        """Test WHERE with comparison operators"""
        filter = relational_filter \
            .where("age", FilterOperator.GT, 18) \
            .and_where("age", FilterOperator.LT, 65)
        
        assert len(filter.conditions) == 2
        assert filter.conditions[0].operator == FilterOperator.GT
        assert filter.conditions[1].operator == FilterOperator.LT
    
    def test_where_in(self, relational_filter):
        """Test WHERE with IN operator"""
        filter = relational_filter.where("status", FilterOperator.IN, ["active", "pending"])
        assert filter.conditions[0].operator == FilterOperator.IN
        assert filter.conditions[0].value == ["active", "pending"]
    
    def test_where_null(self, relational_filter):
        """Test WHERE with IS NULL"""
        filter = relational_filter.where("deleted_at", FilterOperator.IS_NULL, None)
        assert filter.conditions[0].operator == FilterOperator.IS_NULL


# ============================================================================
# Test GROUP BY / HAVING
# ============================================================================

class TestGroupByHaving:
    """Test GROUP BY and HAVING clauses"""
    
    def test_group_by_single(self, relational_filter):
        """Test GROUP BY with single field"""
        filter = relational_filter.group_by("country")
        assert filter.group_by_clause is not None
        assert filter.group_by_clause.fields == ["country"]
    
    def test_group_by_multiple(self, relational_filter):
        """Test GROUP BY with multiple fields"""
        filter = relational_filter.group_by("country", "city")
        assert filter.group_by_clause.fields == ["country", "city"]
    
    def test_having_condition(self, relational_filter):
        """Test HAVING with condition"""
        filter = relational_filter \
            .group_by("user_id") \
            .having("COUNT(*)", FilterOperator.GT, 5)
        
        assert len(filter.group_by_clause.having_conditions) == 1
        having_cond = filter.group_by_clause.having_conditions[0]
        assert having_cond.field == "COUNT(*)"
        assert having_cond.operator == FilterOperator.GT
        assert having_cond.value == 5
    
    def test_having_without_group_by_raises_error(self, relational_filter):
        """Test HAVING without GROUP BY raises error"""
        with pytest.raises(ValueError, match="HAVING requires GROUP BY"):
            relational_filter.having("COUNT(*)", FilterOperator.GT, 5)


# ============================================================================
# Test SQL Generation
# ============================================================================

class TestSQLGeneration:
    """Test SQL query generation"""
    
    def test_simple_select(self, relational_filter):
        """Test simple SELECT query"""
        filter = relational_filter \
            .select("name", "email") \
            .from_table("users")
        
        sql, params = filter.to_sql()
        assert "SELECT name, email" in sql
        assert "FROM users" in sql
        assert params == []
    
    def test_select_with_where(self, relational_filter):
        """Test SELECT with WHERE"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .where("active", FilterOperator.EQ, True)
        
        sql, params = filter.to_sql()
        assert "SELECT *" in sql
        assert "FROM users" in sql
        assert "WHERE active = ?" in sql
        assert params == [True]
    
    def test_select_with_join(self, relational_filter):
        """Test SELECT with JOIN"""
        filter = relational_filter \
            .select("users.name", "orders.total") \
            .from_table("users") \
            .left_join("orders", "users.id", "orders.user_id")
        
        sql, params = filter.to_sql()
        assert "SELECT users.name, orders.total" in sql
        assert "LEFT JOIN orders ON users.id = orders.user_id" in sql
    
    def test_select_with_aggregate(self, relational_filter):
        """Test SELECT with aggregate function"""
        filter = relational_filter \
            .select("country") \
            .select_aggregate(AggregateFunction.COUNT, "*", "total") \
            .from_table("users") \
            .group_by("country")
        
        sql, params = filter.to_sql()
        assert "SELECT country, COUNT(*) AS total" in sql
        assert "GROUP BY country" in sql
    
    def test_select_with_order_by(self, relational_filter):
        """Test SELECT with ORDER BY"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .order_by("created_at", SortOrder.DESC)
        
        sql, params = filter.to_sql()
        assert "ORDER BY created_at DESC" in sql
    
    def test_select_with_limit_offset(self, relational_filter):
        """Test SELECT with LIMIT and OFFSET"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .limit(10) \
            .offset(20)
        
        sql, params = filter.to_sql()
        assert "LIMIT ?" in sql
        assert "OFFSET ?" in sql
        assert 10 in params
        assert 20 in params
    
    def test_complex_query(self, relational_filter):
        """Test complex query with all features"""
        filter = relational_filter \
            .select("users.id", "users.name") \
            .select_aggregate(AggregateFunction.COUNT, "orders.id", "order_count") \
            .from_table("users") \
            .left_join("orders", "users.id", "orders.user_id") \
            .where("users.active", FilterOperator.EQ, True) \
            .and_where("users.created_at", FilterOperator.GT, "2025-01-01") \
            .group_by("users.id", "users.name") \
            .having("order_count", FilterOperator.GT, 5) \
            .order_by("order_count", SortOrder.DESC) \
            .limit(10)
        
        sql, params = filter.to_sql()
        
        # Verify all components present
        assert "SELECT users.id, users.name, COUNT(orders.id) AS order_count" in sql
        assert "FROM users" in sql
        assert "LEFT JOIN orders ON users.id = orders.user_id" in sql
        assert "WHERE users.active = ?" in sql
        assert "AND users.created_at > ?" in sql
        assert "GROUP BY users.id, users.name" in sql
        assert "HAVING order_count > ?" in sql
        assert "ORDER BY order_count DESC" in sql
        assert "LIMIT ?" in sql
        
        # Verify parameters
        assert True in params
        assert "2025-01-01" in params
        assert 5 in params
        assert 10 in params
    
    def test_count_query_generation(self, relational_filter):
        """Test COUNT query generation"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .where("active", FilterOperator.EQ, True)
        
        sql, params = filter.to_sql(count_only=True)
        
        assert sql == "SELECT COUNT(*) FROM users WHERE active = ?"
        assert params == [True]
    
    def test_distinct_query(self, relational_filter):
        """Test DISTINCT query"""
        filter = relational_filter \
            .select("country") \
            .select_distinct() \
            .from_table("users")
        
        sql, params = filter.to_sql()
        assert "SELECT DISTINCT country" in sql
    
    def test_no_from_table_raises_error(self, relational_filter):
        """Test missing FROM table raises error"""
        filter = relational_filter.select("*")
        
        with pytest.raises(ValueError, match="FROM table must be specified"):
            filter.to_sql()


# ============================================================================
# Test Parameter Binding
# ============================================================================

class TestParameterBinding:
    """Test SQL parameter binding for security"""
    
    def test_parameter_binding_equality(self, relational_filter):
        """Test parameter binding with equality"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .where("name", FilterOperator.EQ, "Alice")
        
        sql, params = filter.to_sql()
        assert "name = ?" in sql
        assert params == ["Alice"]
    
    def test_parameter_binding_in(self, relational_filter):
        """Test parameter binding with IN operator"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .where("status", FilterOperator.IN, ["active", "pending", "review"])
        
        sql, params = filter.to_sql()
        assert "status IN (?, ?, ?)" in sql
        assert params == ["active", "pending", "review"]
    
    def test_parameter_binding_between(self, relational_filter):
        """Test parameter binding with BETWEEN"""
        filter = relational_filter \
            .select("*") \
            .from_table("orders") \
            .where("amount", FilterOperator.BETWEEN, [100, 1000])
        
        sql, params = filter.to_sql()
        assert "amount BETWEEN ? AND ?" in sql
        assert params == [100, 1000]
    
    def test_parameter_binding_multiple_conditions(self, relational_filter):
        """Test parameter binding with multiple conditions"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .where("age", FilterOperator.GT, 18) \
            .and_where("country", FilterOperator.EQ, "Germany") \
            .and_where("status", FilterOperator.IN, ["active", "premium"])
        
        sql, params = filter.to_sql()
        assert params == [18, "Germany", "active", "premium"]


# ============================================================================
# Test Query Execution
# ============================================================================

class TestQueryExecution:
    """Test query execution with mock backends"""
    
    def test_execute_with_backend_returns_result_structure(self):
        """Test execute() returns proper RelationalQueryResult structure"""
        backend = Mock()
        backend.execute = Mock(side_effect=Exception("Test exception"))
        
        filter = RelationalFilter(backend=backend)
        filter.select("*").from_table("users")
        
        result = filter.execute()
        
        # Even on error, should return proper structure
        assert isinstance(result, RelationalQueryResult)
        assert result.sql_query is not None
        assert isinstance(result.parameters, list)
    
    def test_execute_without_backend(self, relational_filter):
        """Test execute() without backend returns error"""
        filter = relational_filter \
            .select("*") \
            .from_table("users")
        
        result = filter.execute()
        
        assert result.success is False
        assert "No database backend" in result.errors[0]
    
    def test_count_without_backend_returns_zero(self, relational_filter):
        """Test count() without backend returns 0"""
        filter = relational_filter.select("*").from_table("users")
        
        count = filter.count()
        
        assert count == 0


# ============================================================================
# Test to_query() Method
# ============================================================================

class TestToQueryMethod:
    """Test to_query() dictionary conversion"""
    
    def test_to_query_simple(self, relational_filter):
        """Test to_query() with simple query"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .limit(10)
        
        query_dict = filter.to_query()
        
        assert query_dict["filter_type"] == "relational"
        assert query_dict["dialect"] == "sqlite"
        assert query_dict["from_table"] == "users"
        assert query_dict["limit"] == 10
        assert query_dict["offset"] == 0
    
    def test_to_query_with_joins(self, relational_filter):
        """Test to_query() with JOINs"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .left_join("orders", "users.id", "orders.user_id")
        
        query_dict = filter.to_query()
        assert query_dict["join_count"] == 1


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_select_defaults_to_star(self, relational_filter):
        """Test empty SELECT defaults to SELECT *"""
        filter = relational_filter.from_table("users")
        sql, _ = filter.to_sql()
        assert "SELECT *" in sql
    
    def test_multiple_order_by(self, relational_filter):
        """Test multiple ORDER BY fields"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .order_by("country", SortOrder.ASC) \
            .order_by("created_at", SortOrder.DESC)
        
        sql, _ = filter.to_sql()
        assert "ORDER BY country ASC, created_at DESC" in sql
    
    def test_table_alias_in_from(self, relational_filter):
        """Test table alias in FROM clause"""
        filter = relational_filter \
            .select("u.name") \
            .from_table("users", "u")
        
        sql, _ = filter.to_sql()
        assert "FROM users AS u" in sql
    
    def test_null_check_no_parameters(self, relational_filter):
        """Test IS NULL doesn't add parameters"""
        filter = relational_filter \
            .select("*") \
            .from_table("users") \
            .where("deleted_at", FilterOperator.IS_NULL, None)
        
        sql, params = filter.to_sql()
        assert "deleted_at IS NULL" in sql
        assert params == []
    
    def test_chaining_returns_self(self, relational_filter):
        """Test all methods return self for chaining"""
        filter = relational_filter \
            .select("id") \
            .from_table("users") \
            .where("active", FilterOperator.EQ, True) \
            .order_by("id") \
            .limit(10)
        
        assert isinstance(filter, RelationalFilter)


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("Running UDS3 RelationalFilter Tests...")
    print("=" * 80)
    
    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
