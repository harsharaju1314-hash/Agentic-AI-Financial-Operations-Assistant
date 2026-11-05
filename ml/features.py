import numpy as np
import pandas as pd
from typing import List, Dict, Any, Union


CATEGORY_RISK_MAP = {
    "Crypto Exchange": 0.85,
    "Wire Transfer": 0.75,
    "Luxury": 0.50,
    "Electronics": 0.25,
    "Travel": 0.20,
    "Gaming": 0.20,
    "Entertainment": 0.10,
    "Dining": 0.08,
    "Healthcare": 0.06,
    "Groceries": 0.04,
    "Retail": 0.10,
}

PAYMENT_RISK_MAP = {
    "CRYPTO": 0.85,
    "WIRE_TRANSFER": 0.70,
    "ACH": 0.20,
    "CREDIT_CARD": 0.15,
    "DEBIT_CARD": 0.10,
}

FEATURE_COLUMNS = [
    "amount",
    "log_amount",
    "amount_to_avg_ratio",
    "amount_deviation",
    "hour_of_day",
    "is_night_txn",
    "day_of_week",
    "category_risk",
    "payment_method_risk",
]


def extract_features(df_or_dicts: Union[pd.DataFrame, List[Dict[str, Any]]]) -> pd.DataFrame:
    """
    Extracts numerical and behavioral features from transaction records
    for anomaly detection and fraud risk scoring.
    """
    if isinstance(df_or_dicts, list):
        df = pd.DataFrame(df_or_dicts)
    else:
        df = df_or_dicts.copy()

    # Amount features
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(10.0)
    df["log_amount"] = np.log1p(df["amount"])

    # Historical spending baseline
    if "historical_avg_spending" in df.columns:
        df["historical_avg_spending"] = pd.to_numeric(
            df["historical_avg_spending"], errors="coerce"
        ).fillna(50.0).apply(lambda x: max(5.0, float(x)))
    else:
        df["historical_avg_spending"] = 50.0

    # Ratio and deviation
    df["amount_to_avg_ratio"] = df["amount"] / df["historical_avg_spending"]
    df["amount_deviation"] = (df["amount"] - df["historical_avg_spending"]).abs()

    # Time-based features
    if "timestamp" in df.columns and df["timestamp"].notnull().any():
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        # Ensure datetimelike dtype
        if not pd.api.types.is_datetime64_any_dtype(ts):
            ts = pd.to_datetime(ts, errors="coerce")
        ts = ts.fillna(pd.Timestamp.utcnow())
        df["hour_of_day"] = ts.dt.hour
        df["day_of_week"] = ts.dt.dayofweek
    else:
        now = pd.Timestamp.utcnow()
        df["hour_of_day"] = now.hour
        df["day_of_week"] = now.dayofweek

    # Night transaction indicator (00:00 to 05:00)
    df["is_night_txn"] = df["hour_of_day"].apply(lambda h: 1.0 if (0 <= h <= 5) else 0.0)

    # Category and Payment risk indices
    if "category" in df.columns:
        df["category_risk"] = df["category"].map(CATEGORY_RISK_MAP).fillna(0.10)
    else:
        df["category_risk"] = 0.10

    if "payment_method" in df.columns:
        df["payment_method_risk"] = df["payment_method"].map(PAYMENT_RISK_MAP).fillna(0.15)
    else:
        df["payment_method_risk"] = 0.15

    return df[FEATURE_COLUMNS]
