-- PostgreSQL Schema: Agentic AI Financial Operations Assistant

-- Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    risk_profile VARCHAR(20) DEFAULT 'LOW',
    avg_monthly_spend NUMERIC(12, 2) DEFAULT 0.00,
    home_country VARCHAR(50) DEFAULT 'US',
    home_city VARCHAR(50) DEFAULT 'New York',
    account_status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Merchants Table
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    base_risk_score NUMERIC(5, 4) DEFAULT 0.05,
    city VARCHAR(50) DEFAULT 'New York',
    country VARCHAR(50) DEFAULT 'US',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Financial Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(60) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    merchant_id VARCHAR(50) NOT NULL REFERENCES merchants(merchant_id),
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    category VARCHAR(50) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    status VARCHAR(30) DEFAULT 'COMPLETED',
    location VARCHAR(100) NOT NULL,
    historical_avg_spending NUMERIC(12, 2) DEFAULT 0.00,
    anomaly_score NUMERIC(5, 4) DEFAULT 0.00,
    risk_level VARCHAR(20) DEFAULT 'LOW',
    is_flagged BOOLEAN DEFAULT FALSE,
    flagged_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Fraud Alerts Table
CREATE TABLE IF NOT EXISTS fraud_alerts (
    alert_id VARCHAR(60) PRIMARY KEY,
    transaction_id VARCHAR(60) NOT NULL UNIQUE REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    risk_level VARCHAR(20) NOT NULL,
    anomaly_score NUMERIC(5, 4) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'PENDING_REVIEW',
    reviewed_by VARCHAR(50),
    resolution_notes TEXT,
    action_taken VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Investigation Results Table
CREATE TABLE IF NOT EXISTS investigation_results (
    investigation_id VARCHAR(60) PRIMARY KEY,
    alert_id VARCHAR(60) REFERENCES fraud_alerts(alert_id),
    customer_id VARCHAR(50),
    agent_findings TEXT NOT NULL,
    recommended_action VARCHAR(100) NOT NULL,
    human_approval_required BOOLEAN DEFAULT TRUE,
    status VARCHAR(30) DEFAULT 'OPEN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Execution Audit Logs Table
CREATE TABLE IF NOT EXISTS agent_execution_logs (
    log_id SERIAL PRIMARY KEY,
    session_id VARCHAR(60) NOT NULL,
    user_query TEXT NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    action_taken VARCHAR(100) NOT NULL,
    details TEXT,
    sql_query TEXT,
    execution_time_ms NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optimized Performance Indexes
CREATE INDEX IF NOT EXISTS idx_txn_cust ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_txn_merch ON transactions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_txn_timestamp ON transactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_txn_risk ON transactions(risk_level);
CREATE INDEX IF NOT EXISTS idx_txn_score ON transactions(anomaly_score DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON fraud_alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_customer ON fraud_alerts(customer_id);
CREATE INDEX IF NOT EXISTS idx_logs_session ON agent_execution_logs(session_id);
