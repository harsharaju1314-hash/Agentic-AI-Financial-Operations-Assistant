import time
from typing import Dict, Any
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.sql_validator import validate_read_only_sql, SQLSecurityError
from database.queries import execute_validated_sql, log_agent_execution
from agents.state import FinancialAgentState
from agents.llm_factory import get_llm, DeterministicFinancialIntelligence


class SQLDataRetrievalAgent:
    """
    SQL Data Retrieval Agent:
    - Converts natural language financial inquiries into syntactically valid SQL queries.
    - Strictly validates queries against SQL injection, DDL/DML mutation, and unapproved tables.
    - Executes read-only queries against PostgreSQL/SQLite and returns tabular records.
    """

    def __init__(self):
        self.llm = get_llm()

    def run(self, state: FinancialAgentState) -> Dict[str, Any]:
        start_time = time.time()
        user_query = state.get("user_query", "")
        entities = state.get("extracted_entities", {})
        session_id = state.get("session_id", "default_session")

        # 1. Generate SQL query
        sql_query = None
        if self.llm:
            try:
                system_prompt = (
                    "You are a strict read-only PostgreSQL expert for a financial operations database.\n"
                    "Tables available:\n"
                    "- customers (customer_id, name, email, risk_profile, avg_monthly_spend, home_country, home_city, account_status)\n"
                    "- merchants (merchant_id, name, category, base_risk_score, city, country)\n"
                    "- transactions (transaction_id, customer_id, merchant_id, amount, currency, timestamp, category, payment_method, status, location, historical_avg_spending, anomaly_score, risk_level, is_flagged, flagged_reason)\n"
                    "- fraud_alerts (alert_id, transaction_id, customer_id, risk_level, anomaly_score, reason, status)\n"
                    "Output ONLY the raw SQL query. Do not use markdown blocks, quotes, or conversational explanations."
                )
                response = self.llm.invoke(f"{system_prompt}\nUser Request: {user_query}")
                raw_sql = response.content.strip().replace("```sql", "").replace("```", "").strip()
                sql_query = raw_sql
            except Exception:
                sql_query = DeterministicFinancialIntelligence.generate_sql_for_query(user_query, entities)
        else:
            sql_query = DeterministicFinancialIntelligence.generate_sql_for_query(user_query, entities)

        # 2. Validate and Execute Query
        db: Session = SessionLocal()
        results = []
        error_msg = None
        safe_query = sql_query

        try:
            is_valid, validated_sql, err = validate_read_only_sql(sql_query)
            if not is_valid:
                error_msg = f"SQL Security Validation Failed: {err}"
            else:
                safe_query = validated_sql
                results = execute_validated_sql(db, safe_query)
        except Exception as e:
            error_msg = f"Execution Error: {str(e)}"
        finally:
            exec_time = round((time.time() - start_time) * 1000, 2)
            log_agent_execution(
                db=db,
                session_id=session_id,
                user_query=user_query,
                agent_name="SQLDataRetrievalAgent",
                action_taken="EXECUTE_SQL_QUERY" if not error_msg else "SQL_VALIDATION_ERROR",
                details=f"Returned {len(results)} records" if not error_msg else error_msg,
                sql_query=safe_query,
                execution_time_ms=exec_time,
            )
            db.close()

        log_entry = {
            "agent": "SQLDataRetrievalAgent",
            "action": "QUERY_EXECUTION",
            "query": safe_query,
            "record_count": len(results),
            "error": error_msg,
            "duration_ms": exec_time,
        }

        agent_logs = list(state.get("agent_logs", []))
        agent_logs.append(log_entry)

        routed = list(state.get("routed_agents", []))
        if "SQLDataRetrievalAgent" not in routed:
            routed.append("SQLDataRetrievalAgent")

        return {
            "sql_query": safe_query,
            "sql_results": results,
            "sql_error": error_msg,
            "agent_logs": agent_logs,
            "routed_agents": routed,
            "current_agent": "SQLDataRetrievalAgent",
        }
