import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.connection import get_db
from database.models import Transaction, FraudAlert, Customer
from database.queries import get_customer_spending_summary
from ml.fraud_detector import FraudDetector
from api.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionBatchCreate,
)
from api.dependencies import verify_api_key

router = APIRouter(prefix="/transactions", tags=["Transactions"])
detector = FraudDetector()
detector.load()


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    Ingest a new transaction. Evaluates anomaly score in real time using the ML model.
    Automatically generates a Fraud Alert if high risk is detected.
    """
    txn_id = payload.transaction_id or f"TXN-{uuid.uuid4().hex[:8].upper()}"
    ts = payload.timestamp or datetime.datetime.utcnow()

    # Score with ML detector
    score_res = detector.score_single({
        "transaction_id": txn_id,
        "customer_id": payload.customer_id,
        "merchant_id": payload.merchant_id,
        "amount": payload.amount,
        "category": payload.category,
        "payment_method": payload.payment_method,
        "timestamp": ts,
        "location": payload.location,
        "historical_avg_spending": payload.historical_avg_spending,
    })

    risk_level = score_res["risk_level"]
    anomaly_score = score_res["anomaly_score"]
    is_flagged = score_res["is_flagged"]
    flagged_reason = score_res["flagged_reason"]

    txn = Transaction(
        transaction_id=txn_id,
        customer_id=payload.customer_id,
        merchant_id=payload.merchant_id,
        amount=payload.amount,
        currency=payload.currency,
        timestamp=ts,
        category=payload.category,
        payment_method=payload.payment_method,
        status="FLAGGED" if is_flagged else "COMPLETED",
        location=payload.location,
        historical_avg_spending=payload.historical_avg_spending or 50.0,
        anomaly_score=anomaly_score,
        risk_level=risk_level,
        is_flagged=is_flagged,
        flagged_reason=flagged_reason,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(txn)

    if is_flagged or risk_level == "HIGH":
        alert = FraudAlert(
            alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
            transaction_id=txn_id,
            customer_id=payload.customer_id,
            risk_level=risk_level,
            anomaly_score=anomaly_score,
            reason=flagged_reason or "High risk score detected",
            status="PENDING_REVIEW",
            created_at=datetime.datetime.utcnow(),
        )
        db.add(alert)

    db.commit()
    db.refresh(txn)
    return txn


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def create_transactions_batch(
    payload: TransactionBatchCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """Batch ingest transactions with bulk ML anomaly scoring."""
    txns_data = [t.model_dump() for t in payload.transactions]
    for idx, t in enumerate(txns_data):
        if not t.get("transaction_id"):
            t["transaction_id"] = f"TXN-{uuid.uuid4().hex[:8].upper()}"

    scored = detector.score_batch(txns_data)
    created_txns = []
    created_alerts = []

    for i, t in enumerate(txns_data):
        sc = scored[i]
        ts = t.get("timestamp") or datetime.datetime.utcnow()
        txn = Transaction(
            transaction_id=t["transaction_id"],
            customer_id=t["customer_id"],
            merchant_id=t["merchant_id"],
            amount=t["amount"],
            currency=t.get("currency", "USD"),
            timestamp=ts,
            category=t.get("category", "Retail"),
            payment_method=t.get("payment_method", "CREDIT_CARD"),
            status="FLAGGED" if sc["is_flagged"] else "COMPLETED",
            location=t.get("location", "New York, US"),
            historical_avg_spending=t.get("historical_avg_spending", 50.0),
            anomaly_score=sc["anomaly_score"],
            risk_level=sc["risk_level"],
            is_flagged=sc["is_flagged"],
            flagged_reason=sc["flagged_reason"],
            created_at=datetime.datetime.utcnow(),
        )
        created_txns.append(txn)

        if sc["is_flagged"] or sc["risk_level"] == "HIGH":
            alert = FraudAlert(
                alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                transaction_id=t["transaction_id"],
                customer_id=t["customer_id"],
                risk_level=sc["risk_level"],
                anomaly_score=sc["anomaly_score"],
                reason=sc["flagged_reason"],
                status="PENDING_REVIEW",
                created_at=datetime.datetime.utcnow(),
            )
            created_alerts.append(alert)

    db.bulk_save_objects(created_txns)
    if created_alerts:
        db.bulk_save_objects(created_alerts)
    db.commit()

    return {
        "status": "success",
        "ingested_count": len(created_txns),
        "alerts_generated": len(created_alerts),
    }


@router.get("", response_model=List[TransactionResponse])
def list_transactions(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    merchant_id: Optional[str] = Query(None, description="Filter by merchant ID"),
    risk_level: Optional[str] = Query(None, description="Filter by LOW, MEDIUM, HIGH"),
    is_flagged: Optional[bool] = Query(None, description="Filter flagged transactions"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve financial transactions with pagination and multi-criteria filters."""
    query = db.query(Transaction)
    if customer_id:
        query = query.filter(Transaction.customer_id == customer_id)
    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)
    if risk_level:
        query = query.filter(Transaction.risk_level == risk_level.upper())
    if is_flagged is not None:
        query = query.filter(Transaction.is_flagged == is_flagged)

    records = query.order_by(desc(Transaction.timestamp)).offset(offset).limit(limit).all()
    return records


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve detailed record for a specific transaction ID."""
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' was not found.",
        )
    return txn


@router.get("/customer/{customer_id}")
def get_customer_transactions(
    customer_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve customer financial profile, spending metrics, and recent transaction history."""
    summary = get_customer_spending_summary(db, customer_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' was not found.",
        )
    return summary
