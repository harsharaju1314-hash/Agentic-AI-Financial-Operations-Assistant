import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.connection import get_db
from database.models import AgentExecutionLog
from agents.orchestrator import FinancialOperationsOrchestrator
from api.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    AgentExecutionLogResponse,
)
from api.dependencies import verify_api_key

router = APIRouter(prefix="/agents", tags=["Agentic AI Orchestration"])
orchestrator = FinancialOperationsOrchestrator()


@router.post("/query", response_model=AgentQueryResponse)
def execute_agent_query(
    payload: AgentQueryRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    Submits a natural language financial operations query to the multi-agent system.
    Orchestrated via LangGraph across specialized agents:
    - SQL Data Retrieval Agent
    - Transaction Analysis Agent
    - Fraud Investigation Agent
    - Financial Reporting Agent
    """
    session_id = payload.session_id or f"sess-{uuid.uuid4().hex[:10]}"
    state = orchestrator.execute_query(user_query=payload.query, session_id=session_id)

    return {
        "session_id": state.get("session_id", session_id),
        "user_query": payload.query,
        "intent": state.get("intent", "GENERAL"),
        "routed_agents": state.get("routed_agents", []),
        "sql_query": state.get("sql_query"),
        "supporting_transactions": state.get("supporting_transactions", []),
        "human_approval_required": state.get("human_approval_required", False),
        "recommended_action": state.get("recommended_action"),
        "final_response": state.get("final_response", "No response generated."),
        "execution_logs": state.get("agent_logs", []),
    }


@router.get("/executions", response_model=List[AgentExecutionLogResponse])
def get_agent_execution_logs(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve immutable audit trail records of AI agent operations and SQL queries."""
    query = db.query(AgentExecutionLog)
    if session_id:
        query = query.filter(AgentExecutionLog.session_id == session_id)
    if agent_name:
        query = query.filter(AgentExecutionLog.agent_name == agent_name)

    logs = query.order_by(desc(AgentExecutionLog.created_at)).offset(offset).limit(limit).all()
    return logs
