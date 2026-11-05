from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.connection import get_db
from database.models import FraudAlert, Transaction, Customer
from ml.fraud_detector import FraudDetector
from api.schemas import (
    FraudAnalysisRequest,
    FraudAnalysisResponse,
    FraudAlertResponse,
    AlertActionRequest,
)
from api.dependencies import verify_api_key

router = APIRouter(prefix="/fraud", tags=["Fraud Detection & Investigation"])
detector = FraudDetector()
detector.load()


@router.post("/analyze", response_model=FraudAnalysisResponse)
def analyze_transaction_fraud(
    payload: FraudAnalysisRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    On-demand AI/ML fraud and anomaly detection for an ad-hoc transaction payload.
    Returns anomaly score, risk tier, and human-readable explanation factors.
    """
    data = payload.model_dump()
    result = detector.score_single(data)
    return result


@router.get("/alerts", response_model=List[FraudAlertResponse])
def get_fraud_alerts(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: PENDING_REVIEW, APPROVED_ACTION, DISMISSED, ESCALATED"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: HIGH, MEDIUM"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve fraud alerts queue for operational risk analyst investigation."""
    query = db.query(FraudAlert)
    if status_filter:
        query = query.filter(FraudAlert.status == status_filter.upper())
    if risk_level:
        query = query.filter(FraudAlert.risk_level == risk_level.upper())

    alerts = query.order_by(desc(FraudAlert.created_at)).offset(offset).limit(limit).all()
    return alerts


@router.post("/alerts/{alert_id}/action", response_model=FraudAlertResponse)
def take_alert_action(
    alert_id: str,
    action_data: AlertActionRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    Human-in-the-loop analyst action on a fraud alert:
    Enforces human review before sensitive actions (e.g. freezing account, reversing charge).
    """
    alert = db.query(FraudAlert).filter(FraudAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fraud alert '{alert_id}' was not found.",
        )

    valid_actions = {"ACCOUNT_FROZEN", "TRANSACTION_REVERSED", "FALSE_POSITIVE", "ESCALATED"}
    action_upper = action_data.action.upper()
    if action_upper not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{action_data.action}'. Permitted actions: {valid_actions}",
        )

    alert.status = "APPROVED_ACTION" if action_upper != "FALSE_POSITIVE" else "DISMISSED"
    alert.action_taken = action_upper
    alert.reviewed_by = action_data.reviewed_by
    alert.resolution_notes = action_data.resolution_notes

    # If action is freezing account, update customer account status
    if action_upper == "ACCOUNT_FROZEN":
        customer = db.query(Customer).filter(Customer.customer_id == alert.customer_id).first()
        if customer:
            customer.account_status = "FROZEN"

    # If action is reversing transaction, update transaction status
    if action_upper == "TRANSACTION_REVERSED":
        txn = db.query(Transaction).filter(Transaction.transaction_id == alert.transaction_id).first()
        if txn:
            txn.status = "REFUNDED"

    db.commit()
    db.refresh(alert)
    return alert
