import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, text, case
from database.models import Customer, Merchant, Transaction, FraudAlert, InvestigationResult, AgentExecutionLog
from database.sql_validator import validate_read_only_sql, SQLSecurityError


def execute_validated_sql(db: Session, query: str) -> List[Dict[str, Any]]:
    """Validates and executes a raw read-only SQL query against the database."""
    is_valid, safe_query, error_msg = validate_read_only_sql(query)
    if not is_valid:
        raise SQLSecurityError(error_msg)

    result = db.execute(text(safe_query))
    columns = result.keys()
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows


def get_financial_summary_metrics(db: Session) -> Dict[str, Any]:
    """Calculates top-level operational KPIs."""
    total_txns = db.query(func.count(Transaction.transaction_id)).scalar() or 0
    total_val = db.query(func.sum(Transaction.amount)).scalar() or 0.0
    avg_txn = db.query(func.avg(Transaction.amount)).scalar() or 0.0
    high_risk_count = db.query(func.count(Transaction.transaction_id)).filter(
        Transaction.risk_level == "HIGH"
    ).scalar() or 0
    pending_alerts = db.query(func.count(FraudAlert.alert_id)).filter(
        FraudAlert.status == "PENDING_REVIEW"
    ).scalar() or 0

    return {
        "total_transactions": total_txns,
        "total_volume_usd": round(float(total_val), 2),
        "average_transaction_usd": round(float(avg_txn), 2),
        "high_risk_transactions": high_risk_count,
        "pending_fraud_alerts": pending_alerts,
        "flagged_ratio_pct": round((high_risk_count / total_txns * 100), 2) if total_txns > 0 else 0.0
    }


def get_top_merchants_by_volume(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves top merchants ranked by total transaction volume."""
    results = (
        db.query(
            Merchant.merchant_id,
            Merchant.name,
            Merchant.category,
            func.count(Transaction.transaction_id).label("transaction_count"),
            func.sum(Transaction.amount).label("total_volume_usd"),
            func.avg(Transaction.amount).label("average_ticket_usd"),
            func.sum(case((Transaction.risk_level == "HIGH", 1), else_=0)).label("high_risk_count")
        )
        .join(Transaction, Transaction.merchant_id == Merchant.merchant_id)
        .group_by(Merchant.merchant_id, Merchant.name, Merchant.category)
        .order_by(desc("total_volume_usd"))
        .limit(limit)
        .all()
    )

    return [
        {
            "merchant_id": r.merchant_id,
            "merchant_name": r.name,
            "category": r.category,
            "transaction_count": r.transaction_count,
            "total_volume_usd": round(float(r.total_volume_usd or 0.0), 2),
            "average_ticket_usd": round(float(r.average_ticket_usd or 0.0), 2),
            "high_risk_count": int(r.high_risk_count or 0),
        }
        for r in results
    ]


def get_customer_spending_summary(db: Session, customer_id: str) -> Optional[Dict[str, Any]]:
    """Calculates granular historical spending aggregates for a customer."""
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        return None

    stats = (
        db.query(
            func.count(Transaction.transaction_id).label("txn_count"),
            func.sum(Transaction.amount).label("total_spent"),
            func.avg(Transaction.amount).label("avg_spent"),
            func.max(Transaction.amount).label("max_spent"),
            func.sum(case((Transaction.risk_level == "HIGH", 1), else_=0)).label("flagged_count")
        )
        .filter(Transaction.customer_id == customer_id)
        .first()
    )

    recent_txns = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(desc(Transaction.timestamp))
        .limit(10)
        .all()
    )

    return {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "email": customer.email,
        "risk_profile": customer.risk_profile,
        "account_status": customer.account_status,
        "home_country": customer.home_country,
        "home_city": customer.home_city,
        "total_transactions": stats.txn_count if stats else 0,
        "total_spent_usd": round(float(stats.total_spent or 0.0), 2) if stats else 0.0,
        "average_transaction_usd": round(float(stats.avg_spent or 0.0), 2) if stats else 0.0,
        "max_transaction_usd": round(float(stats.max_spent or 0.0), 2) if stats else 0.0,
        "flagged_transactions_count": int(stats.flagged_count or 0) if stats else 0,
        "recent_transactions": [
            {
                "transaction_id": t.transaction_id,
                "amount": t.amount,
                "merchant_id": t.merchant_id,
                "timestamp": t.timestamp.isoformat(),
                "category": t.category,
                "status": t.status,
                "risk_level": t.risk_level,
                "anomaly_score": t.anomaly_score,
                "flagged_reason": t.flagged_reason,
            }
            for t in recent_txns
        ]
    }


def log_agent_execution(
    db: Session,
    session_id: str,
    user_query: str,
    agent_name: str,
    action_taken: str,
    details: str = "",
    sql_query: Optional[str] = None,
    execution_time_ms: float = 0.0,
) -> AgentExecutionLog:
    """Records an immutable audit trail entry of an AI agent action."""
    log_entry = AgentExecutionLog(
        session_id=session_id,
        user_query=user_query,
        agent_name=agent_name,
        action_taken=action_taken,
        details=details,
        sql_query=sql_query,
        execution_time_ms=execution_time_ms,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
