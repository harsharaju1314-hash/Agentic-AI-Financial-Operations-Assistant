from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database.connection import get_db
from database.queries import get_financial_summary_metrics, get_top_merchants_by_volume
from database.models import Transaction
from sqlalchemy import func, desc, case
from api.schemas import AnalyticsSummaryResponse, TopMerchantResponse

router = APIRouter(prefix="/analytics", tags=["Analytics & Insights"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(db: Session = Depends(get_db)):
    """Retrieve operational financial metrics, transaction totals, and fraud risk ratios."""
    metrics = get_financial_summary_metrics(db)
    return metrics


@router.get("/merchants/top", response_model=List[TopMerchantResponse])
def get_top_merchants(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Retrieve top merchants ranked by total dollar transaction volume."""
    results = get_top_merchants_by_volume(db, limit=limit)
    return results


@router.get("/categories")
def get_category_breakdown(db: Session = Depends(get_db)):
    """Retrieve transaction volume and count rollups aggregated by merchant category."""
    results = (
        db.query(
            Transaction.category,
            func.count(Transaction.transaction_id).label("count"),
            func.sum(Transaction.amount).label("total_volume_usd"),
            func.sum(case((Transaction.risk_level == "HIGH", 1), else_=0)).label("high_risk_count"),
        )
        .group_by(Transaction.category)
        .order_by(desc("total_volume_usd"))
        .all()
    )

    return [
        {
            "category": r.category,
            "transaction_count": r.count,
            "total_volume_usd": round(float(r.total_volume_usd or 0.0), 2),
            "high_risk_count": int(r.high_risk_count or 0),
        }
        for r in results
    ]
