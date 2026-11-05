import os
import re
from typing import Dict, Any, List, Optional
from config.settings import settings


class DeterministicFinancialIntelligence:
    """
    High-fidelity built-in intelligence engine used for deterministic intent routing,
    entity extraction, text-to-SQL generation, and financial synthesis.
    Works independently of external network/API keys, ensuring 100% reliable execution.
    """

    @staticmethod
    def classify_intent_and_entities(query: str) -> Dict[str, Any]:
        q = query.lower()

        # Extract entities
        customer_match = re.search(r"\b(c\d{3,5})\b", q)
        merchant_match = re.search(r"\b(m\d{3,5})\b", q)
        txn_match = re.search(r"\b(txn-\d{4,7})\b", q)

        entities: Dict[str, Any] = {}
        if customer_match:
            entities["customer_id"] = customer_match.group(1).upper()
        if merchant_match:
            entities["merchant_id"] = merchant_match.group(1).upper()
        if txn_match:
            entities["transaction_id"] = txn_match.group(1).upper()

        # Extract limit or top-N
        limit_match = re.search(r"\b(top|limit|first)\s+(\d+)\b", q)
        if limit_match:
            entities["limit"] = int(limit_match.group(2))
        elif "top five" in q or "top 5" in q:
            entities["limit"] = 5
        elif "top ten" in q or "top 10" in q:
            entities["limit"] = 10

        # Classify intent
        if any(w in q for w in ["fraud", "suspicious", "unusual", "anomaly", "anomalies", "flagged", "risk", "investigate", "alert"]):
            intent = "FRAUD_INVESTIGATION"
        elif any(w in q for w in ["trend", "spending", "average", "pattern", "breakdown", "volume", "top", "merchant", "customer", "category"]):
            if any(w in q for w in ["report", "executive summary", "comprehensive report"]):
                intent = "FINANCIAL_REPORTING"
            else:
                intent = "TRANSACTION_ANALYSIS"
        elif any(w in q for w in ["select", "sql", "query", "database", "table", "rows", "show records"]):
            intent = "SQL_RETRIEVAL"
        elif any(w in q for w in ["report", "summary", "audit", "brief"]):
            intent = "FINANCIAL_REPORTING"
        else:
            intent = "GENERAL"

        return {
            "intent": intent,
            "entities": entities,
        }

    @staticmethod
    def generate_sql_for_query(query: str, entities: Dict[str, Any]) -> str:
        q = query.lower()
        limit = entities.get("limit", 10)
        customer_id = entities.get("customer_id")
        merchant_id = entities.get("merchant_id")
        txn_id = entities.get("transaction_id")

        if txn_id:
            return f"SELECT * FROM transactions WHERE transaction_id = '{txn_id}' LIMIT 1"

        if customer_id:
            if "unusual" in q or "fraud" in q or "flagged" in q or "suspicious" in q:
                return (
                    f"SELECT transaction_id, customer_id, merchant_id, amount, timestamp, "
                    f"category, payment_method, status, anomaly_score, risk_level, flagged_reason "
                    f"FROM transactions "
                    f"WHERE customer_id = '{customer_id}' "
                    f"ORDER BY anomaly_score DESC, timestamp DESC LIMIT {limit}"
                )
            return (
                f"SELECT transaction_id, customer_id, merchant_id, amount, timestamp, "
                f"category, payment_method, status, anomaly_score, risk_level "
                f"FROM transactions "
                f"WHERE customer_id = '{customer_id}' "
                f"ORDER BY timestamp DESC LIMIT {limit}"
            )

        if "top" in q and "merchant" in q:
            return (
                f"SELECT m.merchant_id, m.name AS merchant_name, m.category, "
                f"COUNT(t.transaction_id) AS transaction_count, "
                f"ROUND(SUM(t.amount), 2) AS total_volume_usd, "
                f"ROUND(AVG(t.amount), 2) AS average_ticket_usd "
                f"FROM merchants m "
                f"JOIN transactions t ON m.merchant_id = t.merchant_id "
                f"GROUP BY m.merchant_id, m.name, m.category "
                f"ORDER BY total_volume_usd DESC LIMIT {limit}"
            )

        if "high risk" in q or "fraud" in q or "suspicious" in q or "alert" in q:
            return (
                f"SELECT transaction_id, customer_id, merchant_id, amount, timestamp, "
                f"category, payment_method, status, anomaly_score, risk_level, flagged_reason "
                f"FROM transactions "
                f"WHERE risk_level = 'HIGH' "
                f"ORDER BY anomaly_score DESC, timestamp DESC LIMIT {limit}"
            )

        if "category" in q or "spending by category" in q:
            return (
                f"SELECT category, COUNT(transaction_id) AS transaction_count, "
                f"ROUND(SUM(amount), 2) AS total_volume_usd, "
                f"ROUND(AVG(amount), 2) AS average_amount_usd "
                f"FROM transactions "
                f"GROUP BY category "
                f"ORDER BY total_volume_usd DESC LIMIT {limit}"
            )

        # Default fallback transaction query
        return (
            f"SELECT transaction_id, customer_id, merchant_id, amount, timestamp, "
            f"category, payment_method, status, risk_level "
            f"FROM transactions "
            f"ORDER BY timestamp DESC LIMIT {limit}"
        )


def get_llm():
    """Returns ChatOpenAI if API key is provided, else returns None (triggers deterministic engine)."""
    if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 10:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
            )
        except Exception:
            return None
    return None
