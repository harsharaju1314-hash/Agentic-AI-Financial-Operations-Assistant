import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# --- Transaction Schemas ---

class TransactionBase(BaseModel):
    customer_id: str = Field(..., example="C1001")
    merchant_id: str = Field(..., example="M2001")
    amount: float = Field(..., gt=0, example=149.99)
    currency: str = Field(default="USD", example="USD")
    timestamp: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    category: str = Field(default="Retail", example="Electronics")
    payment_method: str = Field(default="CREDIT_CARD", example="CREDIT_CARD")
    location: str = Field(default="New York, US", example="New York, US")
    historical_avg_spending: Optional[float] = Field(default=50.0, example=65.0)


class TransactionCreate(TransactionBase):
    transaction_id: Optional[str] = Field(default=None, example="TXN-99901")


class TransactionResponse(TransactionBase):
    transaction_id: str
    status: str
    anomaly_score: float
    risk_level: str
    is_flagged: bool
    flagged_reason: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class TransactionBatchCreate(BaseModel):
    transactions: List[TransactionCreate]


# --- Fraud Detection Schemas ---

class FraudAnalysisRequest(BaseModel):
    transaction_id: Optional[str] = "TXN-TEST-001"
    customer_id: str = "C1001"
    merchant_id: str = "M2001"
    amount: float = Field(..., gt=0)
    category: str = "Electronics"
    payment_method: str = "CREDIT_CARD"
    timestamp: Optional[datetime.datetime] = None
    location: str = "New York, US"
    historical_avg_spending: Optional[float] = 50.0


class FraudAnalysisResponse(BaseModel):
    transaction_id: str
    anomaly_score: float
    risk_level: str  # LOW, MEDIUM, HIGH
    is_flagged: bool
    flagged_reason: str


class AlertActionRequest(BaseModel):
    action: str = Field(..., example="ACCOUNT_FROZEN", description="ACCOUNT_FROZEN, TRANSACTION_REVERSED, or FALSE_POSITIVE")
    reviewed_by: str = Field(..., example="Analyst_John")
    resolution_notes: str = Field(..., example="Customer confirmed unauthorized charge.")


class FraudAlertResponse(BaseModel):
    alert_id: str
    transaction_id: str
    customer_id: str
    risk_level: str
    anomaly_score: float
    reason: str
    status: str
    reviewed_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    action_taken: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# --- Analytics & Reporting Schemas ---

class AnalyticsSummaryResponse(BaseModel):
    total_transactions: int
    total_volume_usd: float
    average_transaction_usd: float
    high_risk_transactions: int
    pending_fraud_alerts: int
    flagged_ratio_pct: float


class TopMerchantResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    category: str
    transaction_count: int
    total_volume_usd: float
    average_ticket_usd: float
    high_risk_count: int


# --- Agent Orchestration Schemas ---

class AgentQueryRequest(BaseModel):
    query: str = Field(..., example="Find unusual transactions for customer C1002.")
    session_id: Optional[str] = Field(default=None, example="session-abc-123")


class AgentQueryResponse(BaseModel):
    session_id: str
    user_query: str
    intent: str
    routed_agents: List[str]
    sql_query: Optional[str] = None
    supporting_transactions: List[str] = []
    human_approval_required: bool = False
    recommended_action: Optional[str] = None
    final_response: str
    execution_logs: List[Dict[str, Any]] = []


class AgentExecutionLogResponse(BaseModel):
    log_id: int
    session_id: str
    user_query: str
    agent_name: str
    action_taken: str
    details: Optional[str] = None
    sql_query: Optional[str] = None
    execution_time_ms: float
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class FinancialReportResponse(BaseModel):
    title: str
    executive_summary: str
    key_findings: List[str]
    recommendations: List[str]
    metrics: Dict[str, Any]
    flagged_transactions: List[Dict[str, Any]] = []
    customer_summary: Optional[Dict[str, Any]] = None
