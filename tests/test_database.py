import pytest
from database.models import Customer, Merchant, Transaction, FraudAlert, AgentExecutionLog
from database.queries import (
    get_financial_summary_metrics,
    get_top_merchants_by_volume,
    get_customer_spending_summary,
    execute_validated_sql,
    log_agent_execution,
)


def test_database_entities_seeded(db_session):
    cust_count = db_session.query(Customer).count()
    merch_count = db_session.query(Merchant).count()
    txn_count = db_session.query(Transaction).count()
    assert cust_count == 2
    assert merch_count == 2
    assert txn_count == 2


def test_get_financial_summary_metrics(db_session):
    metrics = get_financial_summary_metrics(db_session)
    assert metrics["total_transactions"] == 2
    assert metrics["total_volume_usd"] == 4555.00
    assert metrics["high_risk_transactions"] == 1
    assert metrics["pending_fraud_alerts"] == 1
    assert metrics["flagged_ratio_pct"] == 50.0


def test_get_top_merchants_by_volume(db_session):
    top = get_top_merchants_by_volume(db_session, limit=5)
    assert len(top) == 2
    assert top[0]["merchant_id"] == "M2002"
    assert top[0]["total_volume_usd"] == 4500.00
    assert top[1]["merchant_id"] == "M2001"
    assert top[1]["total_volume_usd"] == 55.00


def test_get_customer_spending_summary(db_session):
    summary = get_customer_spending_summary(db_session, "C1001")
    assert summary is not None
    assert summary["customer_id"] == "C1001"
    assert summary["total_transactions"] == 1
    assert summary["total_spent_usd"] == 55.00

    unknown = get_customer_spending_summary(db_session, "C_NONEXISTENT")
    assert unknown is None


def test_execute_validated_sql(db_session):
    rows = execute_validated_sql(db_session, "SELECT customer_id, amount FROM transactions WHERE amount > 100")
    assert len(rows) == 1
    assert rows[0]["customer_id"] == "C1002"
    assert rows[0]["amount"] == 4500.00


def test_log_agent_execution(db_session):
    entry = log_agent_execution(
        db=db_session,
        session_id="sess-test-123",
        user_query="Check fraud for C1002",
        agent_name="FraudInvestigationAgent",
        action_taken="EVALUATE_ANOMALIES",
        details="Found 1 high risk transaction",
        sql_query="SELECT * FROM transactions",
        execution_time_ms=12.5,
    )
    assert entry.log_id is not None
    assert entry.agent_name == "FraudInvestigationAgent"
    assert entry.session_id == "sess-test-123"

    saved = db_session.query(AgentExecutionLog).filter_by(session_id="sess-test-123").first()
    assert saved is not None
    assert saved.action_taken == "EVALUATE_ANOMALIES"
