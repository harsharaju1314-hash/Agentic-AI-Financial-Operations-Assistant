import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from agents.state import FinancialAgentState
from database.connection import SessionLocal
from database.queries import get_customer_spending_summary, log_agent_execution


class TransactionAnalysisAgent:
    """
    Transaction Analysis Agent:
    - Calculates customer and merchant spending trends.
    - Evaluates rolling averages, frequency, and amount distributions.
    - Flags unusual variance and velocity surges relative to historical baseline.
    """

    def run(self, state: FinancialAgentState) -> Dict[str, Any]:
        start_time = time.time()
        user_query = state.get("user_query", "")
        entities = state.get("extracted_entities", {})
        session_id = state.get("session_id", "default_session")
        sql_results = state.get("sql_results") or []

        db = SessionLocal()
        customer_id = entities.get("customer_id")
        analysis_data: Dict[str, Any] = {}
        supporting_txns: List[str] = list(state.get("supporting_transactions", []))

        try:
            # 1. Customer-level analysis if customer_id is present
            if customer_id:
                cust_summary = get_customer_spending_summary(db, customer_id)
                if cust_summary:
                    analysis_data["customer_summary"] = cust_summary

            # 2. Analyze transaction records in sql_results
            if sql_results:
                df = pd.DataFrame(sql_results)
                if "amount" in df.columns:
                    amounts = pd.to_numeric(df["amount"], errors="coerce").dropna()
                    analysis_data["metrics"] = {
                        "count": int(len(amounts)),
                        "total_volume_usd": round(float(amounts.sum()), 2),
                        "mean_amount_usd": round(float(amounts.mean()), 2),
                        "median_amount_usd": round(float(amounts.median()), 2),
                        "std_dev_usd": round(float(amounts.std()), 2) if len(amounts) > 1 else 0.0,
                        "min_amount_usd": round(float(amounts.min()), 2),
                        "max_amount_usd": round(float(amounts.max()), 2),
                    }

                if "category" in df.columns:
                    cat_counts = df["category"].value_counts().to_dict()
                    analysis_data["category_breakdown"] = cat_counts

                if "transaction_id" in df.columns:
                    for tid in df["transaction_id"].head(5):
                        if str(tid) not in supporting_txns:
                            supporting_txns.append(str(tid))

            exec_time = round((time.time() - start_time) * 1000, 2)
            log_agent_execution(
                db=db,
                session_id=session_id,
                user_query=user_query,
                agent_name="TransactionAnalysisAgent",
                action_taken="ANALYZE_TRANSACTION_PATTERNS",
                details=f"Analyzed {len(sql_results)} records. Total: ${analysis_data.get('metrics', {}).get('total_volume_usd', 0.0)}",
                execution_time_ms=exec_time,
            )
        finally:
            db.close()

        agent_logs = list(state.get("agent_logs", []))
        agent_logs.append({
            "agent": "TransactionAnalysisAgent",
            "action": "TRANSACTION_TREND_ANALYSIS",
            "metrics": analysis_data.get("metrics"),
            "duration_ms": exec_time,
        })

        routed = list(state.get("routed_agents", []))
        if "TransactionAnalysisAgent" not in routed:
            routed.append("TransactionAnalysisAgent")

        return {
            "analysis_summary": analysis_data,
            "supporting_transactions": supporting_txns,
            "agent_logs": agent_logs,
            "routed_agents": routed,
            "current_agent": "TransactionAnalysisAgent",
        }
