import pytest
import pandas as pd
from data.synthetic_generator import generate_synthetic_dataset
from data.ingestion import clean_and_normalize_transactions, ingest_incremental_transactions
from database.models import Transaction


def test_synthetic_data_generation():
    df_cust, df_merch, df_txns = generate_synthetic_dataset(
        num_transactions=1000,
        num_customers=50,
        num_merchants=20,
    )
    assert len(df_cust) == 50
    assert len(df_merch) == 20
    assert len(df_txns) == 1000
    assert "is_fraud_ground_truth" in df_txns.columns
    assert "anomaly_score" in df_txns.columns
    assert "risk_level" in df_txns.columns


def test_clean_and_normalize_transactions():
    raw_data = pd.DataFrame([
        {
            "transaction_id": "TXN-001",
            "amount": "125.50",
            "category": "grocery",
            "payment_method": "credit_card",
            "timestamp": "2026-02-15 10:00:00",
        },
        {
            "transaction_id": "TXN-001",  # duplicate
            "amount": "125.50",
            "category": "grocery",
            "payment_method": "credit_card",
            "timestamp": "2026-02-15 10:00:00",
        },
        {
            "transaction_id": "TXN-002",
            "amount": "-50.00",  # invalid negative amount
            "category": "tech",
            "payment_method": "crypto",
            "timestamp": "invalid_date",
        },
    ])

    cleaned = clean_and_normalize_transactions(raw_data)
    assert len(cleaned) == 1  # Deduplicated and negative amount dropped
    assert cleaned.iloc[0]["category"] == "Groceries"
    assert cleaned.iloc[0]["payment_method"] == "CREDIT_CARD"


def test_ingest_incremental_transactions(db_session):
    new_records = [
        {
            "transaction_id": "TXN-INCR-1",
            "customer_id": "C1001",
            "merchant_id": "M2001",
            "amount": 250.00,
            "category": "Electronics",
            "payment_method": "CREDIT_CARD",
            "risk_level": "LOW",
            "anomaly_score": 0.15,
            "is_flagged": False,
        },
        {
            "transaction_id": "TXN-INCR-2",
            "customer_id": "C1002",
            "merchant_id": "M2002",
            "amount": 8500.00,
            "category": "Crypto Exchange",
            "payment_method": "CRYPTO",
            "risk_level": "HIGH",
            "anomaly_score": 0.92,
            "is_flagged": True,
            "flagged_reason": "High dollar crypto anomaly",
        },
    ]

    res = ingest_incremental_transactions(new_records, db_session)
    assert res["inserted_count"] == 2
    assert res["alerts_created"] == 1

    saved = db_session.query(Transaction).filter_by(transaction_id="TXN-INCR-2").first()
    assert saved is not None
    assert saved.risk_level == "HIGH"
