import os
import json
from typing import Dict, Any
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)
from config.settings import settings
from data.synthetic_generator import generate_synthetic_dataset
from ml.fraud_detector import FraudDetector


def train_and_evaluate_fraud_pipeline(
    num_samples: int = 12000,
    save_model: bool = True,
    output_metrics_file: str = "ml/models/model_metrics.json",
) -> Dict[str, Any]:
    """
    Trains the Isolation Forest fraud detection model on synthetic transactions
    and rigorously evaluates performance on a held-out 20% test dataset.
    """
    print(f"Generating {num_samples} transaction records for ML pipeline...")
    _, _, df_txns = generate_synthetic_dataset(num_transactions=num_samples, seed=42)

    # 80/20 train/test split
    df_train, df_test = train_test_split(
        df_txns, test_size=0.20, random_state=42, stratify=df_txns["is_fraud_ground_truth"]
    )

    print(f"Training dataset size: {len(df_train)} | Test dataset size: {len(df_test)}")
    y_test_true = df_test["is_fraud_ground_truth"].values

    # Initialize and train FraudDetector
    detector = FraudDetector(contamination=settings.FRAUD_CONTAMINATION)
    detector.fit(df_train)

    if save_model:
        detector.save()
        print(f"Model saved to {detector.model_path}")

    # Predict on held-out test set
    test_scores = detector.score_batch(df_test)
    y_test_pred = [1 if item["risk_level"] in ("HIGH", "MEDIUM") else 0 for item in test_scores]

    # Calculate actual empirical evaluation metrics
    prec = precision_score(y_test_true, y_test_pred, zero_division=0)
    rec = recall_score(y_test_true, y_test_pred, zero_division=0)
    f1 = f1_score(y_test_true, y_test_pred, zero_division=0)
    cm = confusion_matrix(y_test_true, y_test_pred).tolist()

    tn, fp, fn, tp = confusion_matrix(y_test_true, y_test_pred).ravel()

    metrics = {
        "train_samples": len(df_train),
        "test_samples": len(df_test),
        "ground_truth_frauds_in_test": int(y_test_true.sum()),
        "predicted_frauds_in_test": int(sum(y_test_pred)),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "model_hyperparameters": {
            "n_estimators": 150,
            "contamination": settings.FRAUD_CONTAMINATION,
            "high_risk_threshold": settings.HIGH_RISK_THRESHOLD,
            "medium_risk_threshold": settings.MEDIUM_RISK_THRESHOLD,
        },
    }

    print("\n--- Model Evaluation Results on Test Dataset ---")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1 Score:  {metrics['f1_score']:.4f}")
    print(f"Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")

    if save_model:
        os.makedirs(os.path.dirname(output_metrics_file), exist_ok=True)
        with open(output_metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)

    return metrics


if __name__ == "__main__":
    train_and_evaluate_fraud_pipeline()
