import os
from typing import Dict, Any, List, Union, Tuple, Optional
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from config.settings import settings
from ml.features import extract_features, FEATURE_COLUMNS


class FraudDetector:
    def __init__(
        self,
        contamination: float = 0.035,
        model_path: str = settings.MODEL_PATH,
        random_state: int = 42,
    ):
        self.contamination = contamination
        self.model_path = model_path
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=150,
            contamination=self.contamination,
            max_samples="auto",
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.is_fitted = False

    def fit(self, df_transactions: pd.DataFrame) -> "FraudDetector":
        """Fits StandardScaler and Isolation Forest on transaction features."""
        X = extract_features(df_transactions)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        return self

    def score_single(self, txn_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates anomaly score and risk classification for a single transaction.
        Returns score (0.0 to 1.0), risk_level, and human-readable explanation.
        """
        res = self.score_batch([txn_dict])
        return res[0]

    def score_batch(self, transactions: Union[pd.DataFrame, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Scores a batch of transactions:
        Computes anomaly score, assigns risk level, and generates reason explanations.
        """
        if isinstance(transactions, list):
            df_input = pd.DataFrame(transactions)
        else:
            df_input = transactions.copy()

        if not self.is_fitted:
            # Fallback heuristic scoring if model not yet trained
            return self._heuristic_scoring(df_input)

        X = extract_features(df_input)
        X_scaled = self.scaler.transform(X)

        # Isolation Forest decision_function: higher is normal, lower is anomalous
        # Typical range ~ [-0.4, 0.2]
        raw_scores = self.model.decision_function(X_scaled)

        # Normalize score into [0, 1] where 1.0 is highest anomaly
        # Map raw_score: 0.2 -> 0.0, -0.35 -> 1.0
        normalized_scores = 1.0 / (1.0 + np.exp(raw_scores * 10.0))

        results = []
        for i, norm_score in enumerate(normalized_scores):
            score = round(float(norm_score), 4)
            row = df_input.iloc[i].to_dict()

            # Risk classification thresholds
            if score >= settings.HIGH_RISK_THRESHOLD:
                risk_level = "HIGH"
            elif score >= settings.MEDIUM_RISK_THRESHOLD:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            reasons = self._generate_explanation(row, score, risk_level)
            results.append({
                "transaction_id": row.get("transaction_id", f"TXN-PREVIEW-{i}"),
                "anomaly_score": score,
                "risk_level": risk_level,
                "is_flagged": risk_level in ("HIGH", "MEDIUM"),
                "flagged_reason": "; ".join(reasons) if reasons else "Transaction patterns within normal operational bounds",
            })

        return results

    def _generate_explanation(self, row: Dict[str, Any], score: float, risk_level: str) -> List[str]:
        """Generates analytical, human-readable explanations of risk factors."""
        reasons = []
        amount = float(row.get("amount", 0.0))
        hist_avg = max(10.0, float(row.get("historical_avg_spending", 50.0)))
        ratio = amount / hist_avg
        category = str(row.get("category", "Retail"))
        payment_method = str(row.get("payment_method", "CREDIT_CARD"))

        if ratio >= 4.0:
            reasons.append(
                f"Amount (${amount:.2f}) is {ratio:.1f}x higher than historical baseline (${hist_avg:.2f})"
            )
        elif amount > 5000.0:
            reasons.append(f"High absolute transaction amount (${amount:.2f})")

        if category in ["Crypto Exchange", "Wire Transfer"]:
            reasons.append(f"Elevated risk sector: {category}")

        if payment_method in ["CRYPTO", "WIRE_TRANSFER"]:
            reasons.append(f"Irreversible payment rail: {payment_method}")

        ts = row.get("timestamp")
        if ts is not None:
            dt = pd.to_datetime(ts)
            if 0 <= dt.hour <= 5:
                reasons.append(f"Unusual transaction timestamp: {dt.strftime('%H:%M')} (Late Night Window)")

        if not reasons and risk_level != "LOW":
            reasons.append(f"Multivariate anomaly detected by Isolation Forest (score: {score:.4f})")

        return reasons

    def _heuristic_scoring(self, df_input: pd.DataFrame) -> List[Dict[str, Any]]:
        """Reliable heuristic fallback when model weights are loading."""
        results = []
        for i in range(len(df_input)):
            row = df_input.iloc[i].to_dict()
            amount = float(row.get("amount", 0.0))
            hist_avg = max(10.0, float(row.get("historical_avg_spending", 50.0)))
            ratio = amount / hist_avg
            cat = str(row.get("category", "Retail"))

            score = 0.10
            if ratio > 6.0:
                score += 0.55
            elif ratio > 3.0:
                score += 0.30

            if cat in ["Crypto Exchange", "Wire Transfer"]:
                score += 0.25

            score = min(0.99, max(0.01, round(score, 4)))
            risk_level = "HIGH" if score >= 0.75 else ("MEDIUM" if score >= 0.40 else "LOW")
            reasons = self._generate_explanation(row, score, risk_level)

            results.append({
                "transaction_id": row.get("transaction_id", f"TXN-{i}"),
                "anomaly_score": score,
                "risk_level": risk_level,
                "is_flagged": risk_level in ("HIGH", "MEDIUM"),
                "flagged_reason": "; ".join(reasons) if reasons else "Transaction within normal limits",
            })
        return results

    def save(self, filepath: Optional[str] = None):
        """Persists trained model and scaler to disk."""
        target = filepath or self.model_path
        os.makedirs(os.path.dirname(target), exist_ok=True)
        joblib.dump({"model": self.model, "scaler": self.scaler, "is_fitted": self.is_fitted}, target)

    def load(self, filepath: Optional[str] = None) -> bool:
        """Loads model weights from disk if available."""
        target = filepath or self.model_path
        if os.path.exists(target):
            data = joblib.load(target)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.is_fitted = data.get("is_fitted", True)
            return True
        return False
