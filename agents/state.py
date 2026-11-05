from typing import TypedDict, List, Dict, Any, Optional


class FinancialAgentState(TypedDict):
    session_id: str
    user_query: str
    intent: str  # TRANSACTION_ANALYSIS, FRAUD_INVESTIGATION, SQL_RETRIEVAL, FINANCIAL_REPORTING, GENERAL
    routed_agents: List[str]
    current_agent: str
    extracted_entities: Dict[str, Any]  # e.g., customer_id, merchant_id, date, amount
    sql_query: Optional[str]
    sql_results: Optional[List[Dict[str, Any]]]
    sql_error: Optional[str]
    fraud_findings: Optional[Dict[str, Any]]
    analysis_summary: Optional[Dict[str, Any]]
    report_output: Optional[Dict[str, Any]]
    agent_logs: List[Dict[str, Any]]
    final_response: Optional[str]
    supporting_transactions: List[str]
    human_approval_required: bool
    recommended_action: Optional[str]
