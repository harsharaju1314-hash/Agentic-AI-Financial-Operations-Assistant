import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from database.connection import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    risk_profile = Column(String(20), default="LOW")  # LOW, MEDIUM, HIGH
    avg_monthly_spend = Column(Float, default=0.0)
    home_country = Column(String(50), default="US")
    home_city = Column(String(50), default="New York")
    account_status = Column(String(20), default="ACTIVE")  # ACTIVE, FROZEN, UNDER_REVIEW
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    alerts = relationship("FraudAlert", back_populates="customer")


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # Electronics, Groceries, Luxury, Travel, Crypto, Gaming
    base_risk_score = Column(Float, default=0.05)  # 0.0 to 1.0
    city = Column(String(50), default="New York")
    country = Column(String(50), default="US")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="merchant")


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(60), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False, index=True)
    merchant_id = Column(String(50), ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    timestamp = Column(DateTime, nullable=False, index=True)
    category = Column(String(50), nullable=False)
    payment_method = Column(String(30), nullable=False)  # CREDIT_CARD, DEBIT_CARD, WIRE_TRANSFER, CRYPTO, ACH
    status = Column(String(30), default="COMPLETED")  # COMPLETED, FLAGGED, BLOCKED, REFUNDED
    location = Column(String(100), nullable=False)
    historical_avg_spending = Column(Float, default=0.0)
    anomaly_score = Column(Float, default=0.0, index=True)
    risk_level = Column(String(20), default="LOW", index=True)  # LOW, MEDIUM, HIGH
    is_flagged = Column(Boolean, default=False, index=True)
    flagged_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    alert = relationship("FraudAlert", back_populates="transaction", uselist=False)

    __table_args__ = (
        Index("idx_txn_cust_time", "customer_id", "timestamp"),
        Index("idx_txn_merch_time", "merchant_id", "timestamp"),
        Index("idx_txn_risk_flag", "risk_level", "is_flagged"),
    )


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    alert_id = Column(String(60), primary_key=True, index=True)
    transaction_id = Column(String(60), ForeignKey("transactions.transaction_id"), nullable=False, unique=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False, index=True)
    risk_level = Column(String(20), nullable=False)  # MEDIUM, HIGH
    anomaly_score = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="PENDING_REVIEW")  # PENDING_REVIEW, APPROVED_ACTION, DISMISSED, ESCALATED
    reviewed_by = Column(String(50), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    action_taken = Column(String(50), nullable=True)  # ACCOUNT_FROZEN, TRANSACTION_REVERSED, FALSE_POSITIVE
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="alert")
    customer = relationship("Customer", back_populates="alerts")


class InvestigationResult(Base):
    __tablename__ = "investigation_results"

    investigation_id = Column(String(60), primary_key=True, index=True)
    alert_id = Column(String(60), ForeignKey("fraud_alerts.alert_id"), nullable=True)
    customer_id = Column(String(50), nullable=True)
    agent_findings = Column(Text, nullable=False)
    recommended_action = Column(String(100), nullable=False)
    human_approval_required = Column(Boolean, default=True)
    status = Column(String(30), default="OPEN")  # OPEN, ACTION_APPROVED, REJECTED, CLOSED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(60), nullable=False, index=True)
    user_query = Column(Text, nullable=False)
    agent_name = Column(String(50), nullable=False, index=True)
    action_taken = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    sql_query = Column(Text, nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
