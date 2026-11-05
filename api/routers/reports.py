from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from agents.financial_reporting_agent import FinancialReportingAgent
from agents.transaction_analysis_agent import TransactionAnalysisAgent
from agents.fraud_investigation_agent import FraudInvestigationAgent
from database.queries import get_customer_spending_summary, get_top_merchants_by_volume
from database.models import Transaction
from api.schemas import FinancialReportResponse
import uuid

router = APIRouter(prefix="/reports", tags=["Financial Reporting"])


@router.get("/financial", response_model=FinancialReportResponse)
def get_financial_report(
    customer_id: Optional[str] = Query(None, description="Generate customer-specific report"),
    merchant_id: Optional[str] = Query(None, description="Generate merchant-specific report"),
    db: Session = Depends(get_db),
):
    """
    Generate an executive-level structured financial operations report with
    findings, risk breakdowns, anomaly detections, and recommendations.
    """
    reporting_agent = FinancialReportingAgent()
    analysis_agent = TransactionAnalysisAgent()
    fraud_agent = FraudInvestigationAgent()

    # Query matching transactions
    query = db.query(Transaction)
    if customer_id:
        query = query.filter(Transaction.customer_id == customer_id)
    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)

    records = [
        {
            "transaction_id": t.transaction_id,
            "customer_id": t.customer_id,
            "merchant_id": t.merchant_id,
            "amount": t.amount,
            "category": t.category,
            "payment_method": t.payment_method,
            "status": t.status,
            "historical_avg_spending": t.historical_avg_spending,
            "anomaly_score": t.anomaly_score,
            "risk_level": t.risk_level,
            "flagged_reason": t.flagged_reason,
            "timestamp": t.timestamp.isoformat() if t.timestamp else "",
        }
        for t in query.limit(200).all()
    ]

    # Synthesize state for reporting
    mock_state = {
        "session_id": f"report-{uuid.uuid4().hex[:8]}",
        "user_query": f"Generate report for customer {customer_id}" if customer_id else "Generate operational report",
        "extracted_entities": {"customer_id": customer_id, "merchant_id": merchant_id},
        "sql_results": records,
        "supporting_transactions": [],
        "agent_logs": [],
        "routed_agents": [],
    }

    # Run analysis and fraud agents
    analysis_res = analysis_agent.run(mock_state)
    mock_state.update(analysis_res)

    fraud_res = fraud_agent.run(mock_state)
    mock_state.update(fraud_res)

    report_res = reporting_agent.run(mock_state)
    report_output = report_res["report_output"]

    return report_output
