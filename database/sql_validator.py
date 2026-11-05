import re
from typing import Tuple, List
import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import DML, DDL, Keyword


ALLOWED_TABLES = {
    "customers",
    "merchants",
    "transactions",
    "fraud_alerts",
    "investigation_results",
    "agent_execution_logs",
}

FORBIDDEN_KEYWORDS = {
    "DROP",
    "DELETE",
    "INSERT",
    "UPDATE",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "REPLACE",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "ATTACH",
    "DETACH",
    "SHUTDOWN",
    "INFORMATION_SCHEMA",
    "PG_CATALOG",
    "PG_TABLES",
    "SQLITE_MASTER",
    "BENCHMARK",
    "SLEEP",
    "INTO OUTFILE",
    "LOAD_FILE",
}


class SQLSecurityError(ValueError):
    """Raised when an AI-generated SQL query fails security or read-only validation."""
    pass


def validate_read_only_sql(query: str, max_limit: int = 500) -> Tuple[bool, str, str]:
    """
    Validates that a SQL query is strictly read-only, safe from SQL injection,
    and restricts execution to permitted application tables.

    Returns:
        (is_valid, sanitized_query_or_error, error_message)
    """
    if not query or not query.strip():
        return False, "", "Empty SQL query provided."

    cleaned = query.strip().rstrip(";")

    # Prevent multiple chained statements (e.g. SELECT 1; DROP TABLE)
    statements = sqlparse.split(cleaned)
    if len(statements) != 1:
        return False, "", "Multi-statement queries or chained statements are forbidden for security."

    parsed = sqlparse.parse(statements[0])[0]

    # Normalize token string for keyword checks
    upper_query = cleaned.upper()

    # Check for forbidden dangerous keywords
    for forbidden in FORBIDDEN_KEYWORDS:
        # Use regex boundary check
        pattern = r"\b" + re.escape(forbidden) + r"\b"
        if re.search(pattern, upper_query):
            return False, "", f"Security Violation: Forbidden keyword or system token '{forbidden}' detected."

    # Check primary command is SELECT or WITH
    first_token = None
    for token in parsed.tokens:
        if not token.is_whitespace:
            first_token = token
            break

    if not first_token:
        return False, "", "Invalid SQL statement."

    first_word = first_token.value.upper()
    if first_word not in ("SELECT", "WITH"):
        return False, "", f"Only read-only SELECT or WITH statements are allowed. Got: '{first_word}'."

    # Ensure no DML or DDL tokens exist in the parsed tree
    for token in parsed.flatten():
        val = token.value.upper()
        if token.ttype in (DDL,) or (token.ttype in (DML,) and val != "SELECT"):
            return False, "", f"Disallowed DDL/DML token detected: {token.value}"

    # Enforce safe LIMIT
    sanitized_query = cleaned
    if not re.search(r"\bLIMIT\s+\d+\b", upper_query):
        sanitized_query = f"{cleaned} LIMIT {max_limit}"

    return True, sanitized_query, ""
