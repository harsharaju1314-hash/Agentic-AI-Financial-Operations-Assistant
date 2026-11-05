import time
from typing import Dict, Any, List
import pandas as pd
from agents.state import FinancialAgentState
from ml.fraud_detector import FraudDetector
from database.connection import SessionLocal
from database.queries import log_agent_execution


class FraudInvestigationAgent:
    """
    Fraud Investigation Agent:
    - Applies Isolation Forest anomaly detection to live transaction records.
    - Classifies transactions into LOW, MEDIUM, or HIGH risk.
    - Generates analytical explanations for flagged anomalies.
    - Determines containment recommendations and human approval requirements.
    """

    def __init__(self):
        self.detector = FraudDetector()
        self.detector.load()

    def run(self, state: FinancialAgentState) -> Dict[str, Any]:
        start_time = time.time()
        user_query = state.get("user_query", "")
        session_id = state.get("session_id", "default_session")
        sql_results = state.get("sql_results") or []
        supporting_txns: List[str] = list(state.get("supporting_transactions", []))

        flagged_transactions = []
        highest_risk = "LOW"
        max_score = 0.0
        human_approval_required = False
        recommended_action = "MONITOR_ACCOUNT"

        if sql_results:
            # Score transactions through the ML fraud engine
            scored_results = self.detector.score_batch(sql_results)

            for i, scored in enumerate(scored_results):
                orig_txn = sql_results[i]
                risk = scored["risk_level"]
                score = scored["anomaly_score"]
                tid = str(orig_txn.get("transaction_id", f"TXN-{i}"))

                if score > max_score:
                    max_score = score

                if risk == "HIGH":
                    highest_risk = "HIGH"
                    human_approval_required = True
                    flagged_transactions.append({
                        **orig_txn,
                        "anomaly_score": score,
                        "risk_level": risk,
                        "flagged_reason": scored["flagged_reason"],
                    })
                    if tid not in supporting_txns:
                        supporting_txns.append(tid)

                elif risk == "MEDIUM":
                    if highest_risk != "HIGH":
                        highest_risk = "MEDIUM"
                    flagged_transactions.append({
                        **orig_txn,
                        "anomaly_score": score,
                        "risk_level": risk,
                        "flagged_reason": scored["flagged_reason"],
                    })
                    if tid not in supporting_txns:
                        supporting_txns.append(tid)

        if highest_risk == "HIGH":
            recommended_action = "TEMPORARY_HOLD_AND_CUSTOMER_VERIFICATION"
        elif highest_risk == "MEDIUM":
            recommended_action = "ENHANCED_TRANSACTION_MONITORING"
        else:
            recommended_action = "STANDARD_PROCESSING"

        fraud_findings = {
            "evaluated_transactions_count": len(sql_results),
            "flagged_count": len(flagged_transactions),
            "highest_risk_level": highest_risk,
            "max_anomaly_score": round(max_score, 4),
            "flagged_transactions": flagged_transactions,
            "recommended_action": recommended_action,
        }

        db = SessionLocal()
        try:
            exec_time = round((time.time() - start_time) * 1000, 2)
            log_agent_execution(
                db=db,
                session_id=session_id,
                user_query=user_query,
                agent_name="FraudInvestigationAgent",
                action_taken="ANOMALY_DETECTION_EVALUATION",
                details=f"Evaluated {len(sql_results)} txns. Flagged: {len(flagged_transactions)}. Max Score: {max_score:.4f}",
                execution_time_ms=exec_time,
            )
        finally:
            db.close()

        agent_logs = list(state.get("agent_logs", []))
        agent_logs.append({
            "agent": "FraudInvestigationAgent",
            "action": "ML_FRAUD_EVALUATION",
            "flagged_count": len(flagged_transactions),
            "highest_risk": highest_risk,
            "duration_ms": exec_time,
        })

        routed = list(state.get("routed_agents", []))
        if "FraudInvestigationAgent" not in routed:
            routed.append("FraudInvestigationAgent")

        return {
            "fraud_findings": fraud_findings,
            "supporting_transactions": supporting_txns,
            "human_approval_required": human_approval_required,
            "recommended_action": recommended_action,
            "agent_logs": agent_logs,
            "routed_agents": routed,
            "current_agent": "FraudInvestigationAgent",
        }
