import os
import pytest
import pandas as pd
from ml.features import extract_features, FEATURE_COLUMNS
from ml.fraud_detector import FraudDetector
from data.synthetic_generator import generate_synthetic_dataset


def test_feature_extraction():
    sample_records = [
        {
            "amount": 150.0,
            "historical_avg_spending": 50.0,
            "category": "Electronics",
            "payment_method": "CREDIT_CARD",
            "timestamp": "2026-03-01 14:30:00",
        },
        {
            "amount": 5000.0,
            "historical_avg_spending": 40.0,
            "category": "Crypto Exchange",
            "payment_method": "CRYPTO",
            "timestamp": "2026-03-01 03:15:00",
        },
    ]
    df_feat = extract_features(sample_records)
    assert list(df_feat.columns) == FEATURE_COLUMNS
    assert len(df_feat) == 2
    assert df_feat.iloc[0]["amount_to_avg_ratio"] == 3.0
    assert df_feat.iloc[1]["amount_to_avg_ratio"] == 125.0
    assert df_feat.iloc[1]["is_night_txn"] == 1.0


def test_fraud_detector_fit_and_score():
    _, _, df_txns = generate_synthetic_dataset(num_transactions=500, seed=123)
    detector = FraudDetector(contamination=0.04)
    detector.fit(df_txns)
    assert detector.is_fitted is True

    # Test scoring normal txn
    normal_txn = {
        "amount": 45.0,
        "historical_avg_spending": 50.0,
        "category": "Groceries",
        "payment_method": "DEBIT_CARD",
        "timestamp": "2026-03-01 12:00:00",
    }
    res_normal = detector.score_single(normal_txn)
    assert "anomaly_score" in res_normal
    assert "risk_level" in res_normal
    assert res_normal["risk_level"] in ("LOW", "MEDIUM")

    # Test scoring extreme fraud txn
    fraud_txn = {
        "amount": 9500.0,
        "historical_avg_spending": 40.0,
        "category": "Crypto Exchange",
        "payment_method": "CRYPTO",
        "timestamp": "2026-03-01 03:00:00",
    }
    res_fraud = detector.score_single(fraud_txn)
    assert res_fraud["risk_level"] == "HIGH"
    assert res_fraud["anomaly_score"] >= 0.70
    assert "Crypto Exchange" in res_fraud["flagged_reason"] or "higher than historical baseline" in res_fraud["flagged_reason"]


def test_model_persistence(tmp_path):
    _, _, df_txns = generate_synthetic_dataset(num_transactions=300, seed=99)
    model_file = str(tmp_path / "test_model.joblib")

    detector = FraudDetector(model_path=model_file)
    detector.fit(df_txns)
    detector.save()
    assert os.path.exists(model_file)

    loaded_detector = FraudDetector(model_path=model_file)
    loaded = loaded_detector.load()
    assert loaded is True
    assert loaded_detector.is_fitted is True
