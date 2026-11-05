import time
import uuid
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from agents.state import FinancialAgentState
from agents.llm_factory import DeterministicFinancialIntelligence, get_llm
from agents.sql_retrieval_agent import SQLDataRetrievalAgent
from agents.transaction_analysis_agent import TransactionAnalysisAgent
from agents.fraud_investigation_agent import FraudInvestigationAgent
from agents.financial_reporting_agent import FinancialReportingAgent
from database.connection import SessionLocal
from database.queries import log_agent_execution


class FinancialOperationsOrchestrator:
    """
    LangGraph-powered Financial Operations Orchestrator:
    - Analyzes natural language user inquiries.
    - Classifies intent and extracts financial entities.
    - Routes requests to specialized agents across the state graph.
    - Synthesizes consolidated multi-agent intelligence into executive answers.
    """

    def __init__(self):
        self.sql_agent = SQLDataRetrievalAgent()
        self.analysis_agent = TransactionAnalysisAgent()
        self.fraud_agent = FraudInvestigationAgent()
        self.reporting_agent = FinancialReportingAgent()
        self.llm = get_llm()
        self.workflow = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(FinancialAgentState)

        # Nodes
        builder.add_node("classify_intent", self._node_classify_intent)
        builder.add_node("sql_retrieval", self._node_sql_retrieval)
        builder.add_node("transaction_analysis", self._node_transaction_analysis)
        builder.add_node("fraud_investigation", self._node_fraud_investigation)
        builder.add_node("financial_reporting", self._node_financial_reporting)
        builder.add_node("consolidate_response", self._node_consolidate_response)

        # Graph Entrypoint
        builder.set_entry_point("classify_intent")

        # Edges from classifier
        builder.add_edge("classify_intent", "sql_retrieval")

        # Conditional routing after SQL retrieval based on intent
        builder.add_conditional_edges(
            "sql_retrieval",
            self._route_after_sql,
            {
                "fraud_branch": "fraud_investigation",
                "analysis_branch": "transaction_analysis",
                "reporting_branch": "transaction_analysis",
                "direct_consolidate": "consolidate_response",
            },
        )

        # Edges in fraud branch
        builder.add_edge("fraud_investigation", "financial_reporting")

        # Edges in analysis branch
        builder.add_edge("transaction_analysis", "financial_reporting")

        # Edges to consolidation
        builder.add_edge("financial_reporting", "consolidate_response")
        builder.add_edge("consolidate_response", END)

        return builder.compile()

    def _node_classify_intent(self, state: FinancialAgentState) -> Dict[str, Any]:
        user_query = state.get("user_query", "")
        session_id = state.get("session_id", str(uuid.uuid4()))
        entities = state.get("extracted_entities") or {}

        # Classify intent & entities
        parsed = DeterministicFinancialIntelligence.classify_intent_and_entities(user_query)
        entities.update(parsed.get("entities", {}))
        intent = parsed.get("intent", "TRANSACTION_ANALYSIS")

        routed = list(state.get("routed_agents", []))
        routed.append("Orchestrator:Classify")

        return {
            "session_id": session_id,
            "intent": intent,
            "extracted_entities": entities,
            "routed_agents": routed,
            "current_agent": "Orchestrator:Classify",
        }

    def _route_after_sql(self, state: FinancialAgentState) -> str:
        intent = state.get("intent", "TRANSACTION_ANALYSIS")
        if intent == "FRAUD_INVESTIGATION":
            return "fraud_branch"
        elif intent == "SQL_RETRIEVAL":
            return "direct_consolidate"
        elif intent == "FINANCIAL_REPORTING":
            return "reporting_branch"
        else:
            return "analysis_branch"

    def _node_sql_retrieval(self, state: FinancialAgentState) -> Dict[str, Any]:
        return self.sql_agent.run(state)

    def _node_transaction_analysis(self, state: FinancialAgentState) -> Dict[str, Any]:
        return self.analysis_agent.run(state)

    def _node_fraud_investigation(self, state: FinancialAgentState) -> Dict[str, Any]:
        return self.fraud_agent.run(state)

    def _node_financial_reporting(self, state: FinancialAgentState) -> Dict[str, Any]:
        return self.reporting_agent.run(state)

    def _node_consolidate_response(self, state: FinancialAgentState) -> Dict[str, Any]:
        start_time = time.time()
        user_query = state.get("user_query", "")
        session_id = state.get("session_id", "default_session")
        intent = state.get("intent", "GENERAL")
        sql_results = state.get("sql_results") or []
        sql_query = state.get("sql_query", "")
        fraud = state.get("fraud_findings") or {}
        analysis = state.get("analysis_summary") or {}
        report = state.get("report_output") or {}
        supporting = state.get("supporting_transactions") or []

        # Build comprehensive markdown response
        sections = []

        if intent == "FRAUD_INVESTIGATION":
            sections.append(f"### 🛡️ Fraud Investigation Findings\n")
            flagged = fraud.get("flagged_transactions", [])
            if flagged:
                sections.append(
                    f"**Summary:** Evaluated {len(sql_results)} transactions. "
                    f"Detected **{len(flagged)} anomalous transactions** requiring risk escalation.\n"
                )
                sections.append("| Transaction ID | Customer | Merchant | Amount | Anomaly Score | Risk Level | Reason |")
                sections.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
                for t in flagged[:5]:
                    tid = t.get("transaction_id")
                    cid = t.get("customer_id")
                    mid = t.get("merchant_id")
                    amt = f"${float(t.get('amount', 0)):,.2f}"
                    score = f"{float(t.get('anomaly_score', 0)):.4f}"
                    risk = t.get("risk_level", "HIGH")
                    reason = t.get("flagged_reason", "Statistical deviation")
                    sections.append(f"| `{tid}` | {cid} | {mid} | {amt} | {score} | **{risk}** | {reason} |")

                if state.get("human_approval_required"):
                    sections.append(
                        f"\n> ⚠️ **Analyst Notice:** Human-in-the-loop approval is required for containment. "
                        f"Recommended Action: `{state.get('recommended_action')}`."
                    )
            else:
                sections.append(f"No transactions breached anomaly thresholds for the given inquiry window.")

        elif "top" in user_query.lower() and "merchant" in user_query.lower():
            sections.append(f"### 📊 Top Merchants by Transaction Volume\n")
            if sql_results:
                sections.append("| Merchant ID | Merchant Name | Category | Total Volume (USD) | Txn Count |")
                sections.append("| :--- | :--- | :--- | :--- | :--- |")
                for r in sql_results[:10]:
                    mid = r.get("merchant_id", "N/A")
                    name = r.get("merchant_name", r.get("name", "N/A"))
                    cat = r.get("category", "N/A")
                    vol = f"${float(r.get('total_volume_usd', r.get('total_amount', 0.0))):,.2f}"
                    cnt = r.get("transaction_count", r.get("count", "N/A"))
                    sections.append(f"| `{mid}` | **{name}** | {cat} | {vol} | {cnt} |")
            else:
                sections.append("No merchant records found matching the query criteria.")

        elif intent == "TRANSACTION_ANALYSIS":
            sections.append(f"### 📈 Transaction Analysis Summary\n")
            cust_summary = analysis.get("customer_summary")
            metrics = analysis.get("metrics")

            if cust_summary:
                sections.append(
                    f"**Customer:** {cust_summary.get('name')} (`{cust_summary.get('customer_id')}`)\n"
                    f"- **Status:** {cust_summary.get('account_status')} | **Risk Tier:** {cust_summary.get('risk_profile')}\n"
                    f"- **Total Spend:** ${cust_summary.get('total_spent_usd', 0.0):,.2f} USD across {cust_summary.get('total_transactions')} transactions\n"
                    f"- **Historical Average:** ${cust_summary.get('average_transaction_usd', 0.0):,.2f} | **Max Ticket:** ${cust_summary.get('max_transaction_usd', 0.0):,.2f}\n"
                )

            if metrics:
                sections.append(
                    f"**Window Metrics:** {metrics.get('count')} transactions analyzed totaling "
                    f"${metrics.get('total_volume_usd', 0.0):,.2f} USD (mean: ${metrics.get('mean_amount_usd', 0.0):,.2f})."
                )

        else:
            sections.append(f"### 📋 Financial Operations Query Results\n")
            if sql_results:
                sections.append(f"Retrieved {len(sql_results)} records from the PostgreSQL database.")
                first_few = sql_results[:5]
                keys = [k for k in first_few[0].keys() if k != "created_at"][:6]
                header = "| " + " | ".join(keys) + " |"
                sep = "| " + " | ".join([":---"] * len(keys)) + " |"
                sections.append(header)
                sections.append(sep)
                for row in first_few:
                    vals = [str(row.get(k, "")) for k in keys]
                    sections.append("| " + " | ".join(vals) + " |")

        # Audit & provenance footer
        sections.append(f"\n---")
        sections.append(f"**Supporting Transaction References:** {', '.join(supporting[:8]) if supporting else 'None'}")
        sections.append(f"**Validated SQL Executed:** `{sql_query}`")

        final_response = "\n".join(sections)

        db = SessionLocal()
        try:
            exec_time = round((time.time() - start_time) * 1000, 2)
            log_agent_execution(
                db=db,
                session_id=session_id,
                user_query=user_query,
                agent_name="OrchestratorAgent",
                action_taken="CONSOLIDATE_AGENT_OUTPUTS",
                details=f"Consolidated multi-agent response for intent: {intent}",
                execution_time_ms=exec_time,
            )
        finally:
            db.close()

        routed = list(state.get("routed_agents", []))
        routed.append("Orchestrator:Consolidate")

        return {
            "final_response": final_response,
            "routed_agents": routed,
            "current_agent": "Orchestrator:Consolidate",
        }

    def execute_query(self, user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Entry point for handling a user inquiry through the full LangGraph multi-agent system."""
        initial_state: FinancialAgentState = {
            "session_id": session_id or str(uuid.uuid4()),
            "user_query": user_query,
            "intent": "TRANSACTION_ANALYSIS",
            "routed_agents": [],
            "current_agent": "START",
            "extracted_entities": {},
            "sql_query": None,
            "sql_results": None,
            "sql_error": None,
            "fraud_findings": None,
            "analysis_summary": None,
            "report_output": None,
            "agent_logs": [],
            "final_response": None,
            "supporting_transactions": [],
            "human_approval_required": False,
            "recommended_action": None,
        }

        final_state = self.workflow.invoke(initial_state)
        return final_state
