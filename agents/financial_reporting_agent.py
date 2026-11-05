import time
from typing import Dict, Any, List
from agents.state import FinancialAgentState
from database.connection import SessionLocal
from database.queries import log_agent_execution


class FinancialReportingAgent:
    """
    Financial Reporting Agent:
    - Synthesizes transaction summaries, ML anomaly detections, and merchant/customer trends.
    - Produces executive summaries, risk assessment breakdowns, and action items.
    """

    def run(self, state: FinancialAgentState) -> Dict[str, Any]:
        start_time = time.time()
        user_query = state.get("user_query", "")
        session_id = state.get("session_id", "default_session")
        analysis = state.get("analysis_summary") or {}
        fraud = state.get("fraud_findings") or {}
        sql_results = state.get("sql_results") or []
        entities = state.get("extracted_entities", {})

        metrics = analysis.get("metrics", {})
        customer_id = entities.get("customer_id")
        merchant_id = entities.get("merchant_id")

        # Compile Executive Report
        report_title = "Financial Operations Operational Report"
        if customer_id:
            report_title = f"Customer Financial & Risk Assessment: {customer_id}"
        elif merchant_id:
            report_title = f"Merchant Volume & Risk Profile: {merchant_id}"
        elif "top" in user_query.lower() and "merchant" in user_query.lower():
            report_title = "Top Merchants by Transaction Volume & Ticket Size"

        key_findings = []
        if metrics:
            key_findings.append(
                f"Processed {metrics.get('count', 0)} transactions totaling ${metrics.get('total_volume_usd', 0.0):,.2f} USD "
                f"(average ticket: ${metrics.get('mean_amount_usd', 0.0):,.2f})."
            )

        if fraud:
            flagged = fraud.get("flagged_count", 0)
            highest_risk = fraud.get("highest_risk_level", "LOW")
            if flagged > 0:
                key_findings.append(
                    f"Machine Learning Anomaly Engine detected {flagged} elevated risk transactions "
                    f"with peak anomaly severity of {fraud.get('max_anomaly_score', 0.0):.4f} (Risk Tier: {highest_risk})."
                )
            else:
                key_findings.append("No anomalous transactions exceeding risk thresholds were detected in this inquiry window.")

        recommendations = []
        if state.get("human_approval_required"):
            recommendations.append("Human-in-the-loop analyst approval recommended before applying account freeze or transaction reversal.")
        if state.get("recommended_action"):
            recommendations.append(f"Recommended operational action: {state.get('recommended_action')}.")

        report_output = {
            "title": report_title,
            "executive_summary": " ".join(key_findings),
            "key_findings": key_findings,
            "recommendations": recommendations,
            "metrics": metrics,
            "flagged_transactions": fraud.get("flagged_transactions", []),
            "customer_summary": analysis.get("customer_summary"),
        }

        db = SessionLocal()
        try:
            exec_time = round((time.time() - start_time) * 1000, 2)
            log_agent_execution(
                db=db,
                session_id=session_id,
                user_query=user_query,
                agent_name="FinancialReportingAgent",
                action_taken="GENERATE_STRUCTURED_REPORT",
                details=f"Report generated: {report_title}",
                execution_time_ms=exec_time,
            )
        finally:
            db.close()

        agent_logs = list(state.get("agent_logs", []))
        agent_logs.append({
            "agent": "FinancialReportingAgent",
            "action": "REPORT_SYNTHESIS",
            "report_title": report_title,
            "duration_ms": exec_time,
        })

        routed = list(state.get("routed_agents", []))
        if "FinancialReportingAgent" not in routed:
            routed.append("FinancialReportingAgent")

        return {
            "report_output": report_output,
            "agent_logs": agent_logs,
            "routed_agents": routed,
            "current_agent": "FinancialReportingAgent",
        }
