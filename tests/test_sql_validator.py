import pytest
from database.sql_validator import validate_read_only_sql, SQLSecurityError


def test_valid_select_query():
    query = "SELECT transaction_id, amount FROM transactions WHERE customer_id = 'C1001'"
    is_valid, safe_query, err = validate_read_only_sql(query)
    assert is_valid is True
    assert "LIMIT" in safe_query
    assert err == ""


def test_valid_with_cte_query():
    query = "WITH high_txns AS (SELECT * FROM transactions WHERE amount > 1000) SELECT * FROM high_txns"
    is_valid, safe_query, err = validate_read_only_sql(query)
    assert is_valid is True
    assert err == ""


def test_block_drop_table():
    query = "DROP TABLE customers"
    is_valid, safe_query, err = validate_read_only_sql(query)
    assert is_valid is False
    assert "Forbidden keyword" in err or "SELECT or WITH" in err


def test_block_delete_dml():
    query = "DELETE FROM transactions WHERE amount < 10"
    is_valid, safe_query, err = validate_read_only_sql(query)
    assert is_valid is False
    assert "Forbidden keyword" in err or "SELECT or WITH" in err


def test_block_insert_dml():
    query = "INSERT INTO customers (customer_id, name) VALUES ('C999', 'Hacker')"
    is_valid, safe_query, err = validate_read_only_sql(query)
    assert is_valid is False


def test_block_update_dml():
    query = "UPDATE customers SET account_status = 'ACTIVE' WHERE customer_id = 'C1002'"
    is_valid, safe_query, err = validate_read_only_sql(query)
    assert is_valid is False


def test_block_chained_multi_statements():
    query = "SELECT * FROM transactions; DROP TABLE customers;"
    is_valid, safe_query, err = validate_read_only_sql(query)
    assert is_valid is False
    assert "Multi-statement" in err or "Forbidden keyword" in err


def test_block_system_schema_access():
    query = "SELECT * FROM information_schema.tables"
    is_valid, safe_query, err = validate_read_only_sql(query)
    assert is_valid is False
    assert "Forbidden keyword" in err


def test_empty_query_rejected():
    is_valid, _, err = validate_read_only_sql("   ")
    assert is_valid is False
    assert "Empty SQL query" in err


def test_existing_limit_preserved():
    query = "SELECT * FROM transactions LIMIT 25"
    is_valid, safe_query, _ = validate_read_only_sql(query)
    assert is_valid is True
    assert safe_query.strip().endswith("LIMIT 25")
