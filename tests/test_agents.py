import pytest
from agents.sql_retrieval_agent import SQLDataRetrievalAgent
from agents.transaction_analysis_agent import TransactionAnalysisAgent
from agents.fraud_investigation_agent import FraudInvestigationAgent
from agents.financial_reporting_agent import FinancialReportingAgent
from agents.orchestrator import FinancialOperationsOrchestrator


def test_sql_retrieval_agent(db_session):
    agent = SQLDataRetrievalAgent()
    state = {
        "user_query": "Select all transactions for customer C1001",
        "extracted_entities": {"customer_id": "C1001", "limit": 10},
        "session_id": "test_sql_agent_session",
        "routed_agents": [],
        "agent_logs": [],
    }
    result = agent.run(state)
    assert result["sql_query"] is not None
    assert "C1001" in result["sql_query"]
    assert result["current_agent"] == "SQLDataRetrievalAgent"
    assert "SQLDataRetrievalAgent" in result["routed_agents"]


def test_transaction_analysis_agent(db_session):
    agent = TransactionAnalysisAgent()
    sample_records = [
        {"transaction_id": "TXN-1", "amount": 100.0, "category": "Retail"},
        {"transaction_id": "TXN-2", "amount": 200.0, "category": "Dining"},
        {"transaction_id": "TXN-3", "amount": 300.0, "category": "Retail"},
    ]
    state = {
        "user_query": "Analyze spending for customer C1001",
        "extracted_entities": {"customer_id": "C1001"},
        "sql_results": sample_records,
        "session_id": "test_analysis_agent_session",
        "routed_agents": [],
        "agent_logs": [],
    }
    result = agent.run(state)
    metrics = result["analysis_summary"]["metrics"]
    assert metrics["count"] == 3
    assert metrics["total_volume_usd"] == 600.0
    assert metrics["mean_amount_usd"] == 200.0
    assert result["analysis_summary"]["category_breakdown"]["Retail"] == 2


def test_fraud_investigation_agent():
    agent = FraudInvestigationAgent()
    sample_records = [
        {
            "transaction_id": "TXN-F1",
            "amount": 7500.0,
            "historical_avg_spending": 50.0,
            "category": "Crypto Exchange",
            "payment_method": "CRYPTO",
            "customer_id": "C1002",
        }
    ]
    state = {
        "user_query": "Investigate fraud for customer C1002",
        "sql_results": sample_records,
        "session_id": "test_fraud_session",
        "routed_agents": [],
        "agent_logs": [],
    }
    result = agent.run(state)
    findings = result["fraud_findings"]
    assert findings["flagged_count"] == 1
    assert findings["highest_risk_level"] in ("HIGH", "MEDIUM")
    assert result["human_approval_required"] is True


def test_financial_reporting_agent():
    agent = FinancialReportingAgent()
    state = {
        "user_query": "Generate report for customer C1001",
        "extracted_entities": {"customer_id": "C1001"},
        "analysis_summary": {
            "metrics": {"count": 10, "total_volume_usd": 1500.0, "mean_amount_usd": 150.0}
        },
        "fraud_findings": {
            "flagged_count": 0,
            "highest_risk_level": "LOW",
            "max_anomaly_score": 0.15,
        },
        "human_approval_required": False,
        "session_id": "test_report_session",
        "routed_agents": [],
        "agent_logs": [],
    }
    result = agent.run(state)
    report = result["report_output"]
    assert "C1001" in report["title"]
    assert len(report["key_findings"]) >= 1


def test_orchestrator_fraud_flow():
    orch = FinancialOperationsOrchestrator()
    res = orch.execute_query("Find unusual transactions for customer C1002.")
    assert "SQLDataRetrievalAgent" in res["routed_agents"]
    assert "FraudInvestigationAgent" in res["routed_agents"]
    assert "FinancialReportingAgent" in res["routed_agents"]
    assert res["final_response"] is not None


def test_orchestrator_top_merchants_flow():
    orch = FinancialOperationsOrchestrator()
    res = orch.execute_query("Summarize the top five merchants by transaction volume.")
    assert "SQLDataRetrievalAgent" in res["routed_agents"]
    assert "TransactionAnalysisAgent" in res["routed_agents"]
    assert "FinancialReportingAgent" in res["routed_agents"]
    assert "Top Merchants" in res["final_response"]
