import os
import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from database.connection import SessionLocal, init_db
from database.models import Customer, Merchant, Transaction, FraudAlert
from data.synthetic_generator import generate_synthetic_dataset, CATEGORIES


CATEGORY_CANONICAL_MAP = {
    c.lower(): c for c in CATEGORIES
}
CATEGORY_CANONICAL_MAP.update({
    "grocery": "Groceries",
    "food": "Dining",
    "restaurant": "Dining",
    "restaurants": "Dining",
    "tech": "Electronics",
    "computers": "Electronics",
    "flight": "Travel",
    "flights": "Travel",
    "hotel": "Travel",
    "crypto": "Crypto Exchange",
    "wire": "Wire Transfer",
    "medical": "Healthcare",
    "shopping": "Retail",
    "ecommerce": "Retail",
})


def clean_and_normalize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw transaction dataframe:
    - Drops duplicates based on transaction_id
    - Imputes or drops NaN critical fields
    - Normalizes category names
    - Parses and standardizes timestamps
    - Validates positive amounts
    """
    df = df.copy()

    # Deduplicate
    df = df.drop_duplicates(subset=["transaction_id"], keep="last")

    # Clean amounts
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df[df["amount"].notnull() & (df["amount"] > 0)]

    # Clean and parse timestamps
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["timestamp"] = df["timestamp"].fillna(pd.Timestamp.utcnow())
    else:
        df["timestamp"] = pd.Timestamp.utcnow()

    # Normalize category
    def normalize_cat(cat_val):
        if pd.isna(cat_val):
            return "Retail"
        s = str(cat_val).strip().lower()
        return CATEGORY_CANONICAL_MAP.get(s, "Retail")

    if "category" in df.columns:
        df["category"] = df["category"].apply(normalize_cat)
    else:
        df["category"] = "Retail"

    # Normalize payment method
    valid_payments = {"CREDIT_CARD", "DEBIT_CARD", "WIRE_TRANSFER", "ACH", "CRYPTO"}
    if "payment_method" in df.columns:
        df["payment_method"] = df["payment_method"].astype(str).str.upper().str.strip()
        df["payment_method"] = df["payment_method"].apply(
            lambda p: p if p in valid_payments else "CREDIT_CARD"
        )
    else:
        df["payment_method"] = "CREDIT_CARD"

    # Impute historical_avg_spending if missing or zero
    if "historical_avg_spending" in df.columns:
        df["historical_avg_spending"] = pd.to_numeric(df["historical_avg_spending"], errors="coerce").fillna(50.0)
        df["historical_avg_spending"] = df["historical_avg_spending"].apply(lambda v: max(10.0, float(v)))
    else:
        df["historical_avg_spending"] = 50.0

    # Ensure required text columns exist
    if "location" in df.columns:
        df["location"] = df["location"].fillna("New York, US").astype(str)
    else:
        df["location"] = "New York, US"

    if "status" in df.columns:
        df["status"] = df["status"].fillna("COMPLETED").astype(str)
    else:
        df["status"] = "COMPLETED"

    if "risk_level" in df.columns:
        df["risk_level"] = df["risk_level"].fillna("LOW").astype(str)
    else:
        df["risk_level"] = "LOW"

    if "anomaly_score" in df.columns:
        df["anomaly_score"] = pd.to_numeric(df["anomaly_score"], errors="coerce").fillna(0.0)
    else:
        df["anomaly_score"] = 0.0

    if "is_flagged" in df.columns:
        df["is_flagged"] = df["is_flagged"].fillna(False).astype(bool)
    else:
        df["is_flagged"] = False

    return df


def ingest_initial_seed_data(db: Optional[Session] = None, num_transactions: int = 12000) -> Dict[str, Any]:
    """
    Generates synthetic dataset, cleans and ingests Customers, Merchants,
    Transactions, and initial Fraud Alerts into the database.
    """
    close_db = False
    if db is None:
        init_db()
        db = SessionLocal()
        close_db = True

    try:
        # Check if data already exists
        existing_count = db.query(Transaction).count()
        if existing_count >= 1000:
            return {
                "status": "already_populated",
                "transactions_count": existing_count,
            }

        df_cust, df_merch, df_txns = generate_synthetic_dataset(num_transactions=num_transactions)

        # 1. Ingest Customers
        cust_records = [
            Customer(
                customer_id=row["customer_id"],
                name=row["name"],
                email=row["email"],
                risk_profile=row["risk_profile"],
                avg_monthly_spend=float(row["avg_monthly_spend"]),
                home_country=row["home_country"],
                home_city=row["home_city"],
                account_status=row["account_status"],
                created_at=row["created_at"].to_pydatetime() if isinstance(row["created_at"], pd.Timestamp) else row["created_at"],
            )
            for _, row in df_cust.iterrows()
        ]
        db.bulk_save_objects(cust_records)
        db.commit()

        # 2. Ingest Merchants
        merch_records = [
            Merchant(
                merchant_id=row["merchant_id"],
                name=row["name"],
                category=row["category"],
                base_risk_score=float(row["base_risk_score"]),
                city=row["city"],
                country=row["country"],
                created_at=row["created_at"].to_pydatetime() if isinstance(row["created_at"], pd.Timestamp) else row["created_at"],
            )
            for _, row in df_merch.iterrows()
        ]
        db.bulk_save_objects(merch_records)
        db.commit()

        # 3. Clean and Ingest Transactions
        df_txns_clean = clean_and_normalize_transactions(df_txns)
        txn_records = []
        alerts_records = []

        for idx, row in df_txns_clean.iterrows():
            ts = row["timestamp"].to_pydatetime() if isinstance(row["timestamp"], pd.Timestamp) else row["timestamp"]
            is_flagged = bool(row["is_flagged"])
            risk_lvl = str(row["risk_level"])
            score = float(row["anomaly_score"])

            txn = Transaction(
                transaction_id=str(row["transaction_id"]),
                customer_id=str(row["customer_id"]),
                merchant_id=str(row["merchant_id"]),
                amount=float(row["amount"]),
                currency=str(row.get("currency", "USD")),
                timestamp=ts,
                category=str(row["category"]),
                payment_method=str(row["payment_method"]),
                status=str(row["status"]),
                location=str(row["location"]),
                historical_avg_spending=float(row["historical_avg_spending"]),
                anomaly_score=score,
                risk_level=risk_lvl,
                is_flagged=is_flagged,
                flagged_reason=row.get("flagged_reason"),
                created_at=ts,
            )
            txn_records.append(txn)

            if is_flagged or risk_lvl == "HIGH":
                alert_id = f"ALT-{10000 + len(alerts_records)}"
                alert = FraudAlert(
                    alert_id=alert_id,
                    transaction_id=str(row["transaction_id"]),
                    customer_id=str(row["customer_id"]),
                    risk_level=risk_lvl,
                    anomaly_score=score,
                    reason=row.get("flagged_reason") or "High anomaly score detected by ML engine",
                    status="PENDING_REVIEW",
                    created_at=ts,
                )
                alerts_records.append(alert)

        # Bulk save in batches of 2000
        batch_size = 2000
        for i in range(0, len(txn_records), batch_size):
            db.bulk_save_objects(txn_records[i:i + batch_size])
            db.commit()

        for i in range(0, len(alerts_records), batch_size):
            db.bulk_save_objects(alerts_records[i:i + batch_size])
            db.commit()

        return {
            "status": "success",
            "customers_ingested": len(cust_records),
            "merchants_ingested": len(merch_records),
            "transactions_ingested": len(txn_records),
            "fraud_alerts_created": len(alerts_records),
        }

    finally:
        if close_db:
            db.close()


def ingest_incremental_transactions(
    records: List[Dict[str, Any]],
    db: Session,
) -> Dict[str, Any]:
    """Ingests an incremental batch of new incoming transactions."""
    df_new = pd.DataFrame(records)
    df_clean = clean_and_normalize_transactions(df_new)

    inserted_txns = []
    created_alerts = []

    for _, row in df_clean.iterrows():
        ts = row["timestamp"].to_pydatetime() if isinstance(row["timestamp"], pd.Timestamp) else row["timestamp"]
        txn = Transaction(
            transaction_id=str(row["transaction_id"]),
            customer_id=str(row["customer_id"]),
            merchant_id=str(row["merchant_id"]),
            amount=float(row["amount"]),
            currency=str(row.get("currency", "USD")),
            timestamp=ts,
            category=str(row["category"]),
            payment_method=str(row["payment_method"]),
            status=str(row["status"]),
            location=str(row["location"]),
            historical_avg_spending=float(row.get("historical_avg_spending", 50.0)),
            anomaly_score=float(row.get("anomaly_score", 0.0)),
            risk_level=str(row.get("risk_level", "LOW")),
            is_flagged=bool(row.get("is_flagged", False)),
            flagged_reason=row.get("flagged_reason"),
            created_at=datetime.datetime.utcnow(),
        )
        db.merge(txn)
        inserted_txns.append(txn.transaction_id)

        if txn.is_flagged or txn.risk_level == "HIGH":
            alert_id = f"ALT-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{txn.transaction_id[:8]}"
            alert = FraudAlert(
                alert_id=alert_id,
                transaction_id=txn.transaction_id,
                customer_id=txn.customer_id,
                risk_level=txn.risk_level,
                anomaly_score=txn.anomaly_score,
                reason=txn.flagged_reason or "Flagged by incremental fraud engine",
                status="PENDING_REVIEW",
                created_at=datetime.datetime.utcnow(),
            )
            db.merge(alert)
            created_alerts.append(alert_id)

    db.commit()
    return {
        "inserted_count": len(inserted_txns),
        "alerts_created": len(created_alerts),
        "transaction_ids": inserted_txns,
    }
