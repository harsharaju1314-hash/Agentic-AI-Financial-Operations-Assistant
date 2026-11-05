-- Sample Seed Data for PostgreSQL Database
-- Customers
INSERT INTO customers (customer_id, name, email, risk_profile, avg_monthly_spend, home_country, home_city, account_status)
VALUES 
('C1001', 'Alexander Wright', 'alex.wright@financialops-enterprise.com', 'LOW', 2500.00, 'US', 'New York', 'ACTIVE'),
('C1002', 'Sophia Chen', 'sophia.chen@financialops-enterprise.com', 'HIGH', 4200.00, 'US', 'San Francisco', 'ACTIVE'),
('C1003', 'Liam O''Connor', 'liam.oc@financialops-enterprise.com', 'MEDIUM', 1800.00, 'UK', 'London', 'ACTIVE'),
('C1004', 'Emma Watson', 'emma.w@financialops-enterprise.com', 'LOW', 3100.00, 'CA', 'Toronto', 'ACTIVE'),
('C1005', 'Dmitri Ivanov', 'dmitri.i@financialops-enterprise.com', 'HIGH', 5000.00, 'DE', 'Berlin', 'UNDER_REVIEW')
ON CONFLICT (customer_id) DO NOTHING;

-- Merchants
INSERT INTO merchants (merchant_id, name, category, base_risk_score, city, country)
VALUES
('M2001', 'Apple Store #402', 'Electronics', 0.10, 'New York', 'US'),
('M2002', 'Binance Pay Liquidity', 'Crypto Exchange', 0.75, 'London', 'UK'),
('M2003', 'Western Union Remit', 'Wire Transfer', 0.65, 'New York', 'US'),
('M2004', 'Rolex Boutique Fifth Ave', 'Luxury', 0.45, 'New York', 'US'),
('M2005', 'Whole Foods Market #102', 'Groceries', 0.05, 'San Francisco', 'US')
ON CONFLICT (merchant_id) DO NOTHING;

-- Transactions
INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, timestamp, category, payment_method, status, location, historical_avg_spending, anomaly_score, risk_level, is_flagged, flagged_reason)
VALUES
('TXN-SEED-001', 'C1001', 'M2001', 129.99, 'USD', '2026-03-01 14:15:00', 'Electronics', 'CREDIT_CARD', 'COMPLETED', 'New York, US', 85.00, 0.12, 'LOW', FALSE, NULL),
('TXN-SEED-002', 'C1001', 'M2005', 64.50, 'USD', '2026-03-02 18:30:00', 'Groceries', 'DEBIT_CARD', 'COMPLETED', 'New York, US', 85.00, 0.08, 'LOW', FALSE, NULL),
('TXN-SEED-003', 'C1002', 'M2002', 8500.00, 'USD', '2026-03-03 03:22:00', 'Crypto Exchange', 'CRYPTO', 'FLAGGED', 'Lagos, NG', 140.00, 0.94, 'HIGH', TRUE, 'Extreme deviation (60.7x customer average) via CRYPTO rail during 03:00 AM window'),
('TXN-SEED-004', 'C1003', 'M2003', 4200.00, 'USD', '2026-03-03 03:45:00', 'Wire Transfer', 'WIRE_TRANSFER', 'FLAGGED', 'London, UK', 60.00, 0.88, 'HIGH', TRUE, 'High velocity wire transfer from foreign jurisdiction'),
('TXN-SEED-005', 'C1004', 'M2004', 350.00, 'USD', '2026-03-04 16:10:00', 'Luxury', 'CREDIT_CARD', 'COMPLETED', 'Toronto, CA', 103.00, 0.35, 'LOW', FALSE, NULL)
ON CONFLICT (transaction_id) DO NOTHING;

-- Fraud Alerts
INSERT INTO fraud_alerts (alert_id, transaction_id, customer_id, risk_level, anomaly_score, reason, status)
VALUES
('ALT-SEED-101', 'TXN-SEED-003', 'C1002', 'HIGH', 0.94, 'Extreme deviation (60.7x customer average) via CRYPTO rail during 03:00 AM window', 'PENDING_REVIEW'),
('ALT-SEED-102', 'TXN-SEED-004', 'C1003', 'HIGH', 0.88, 'High velocity wire transfer from foreign jurisdiction', 'PENDING_REVIEW')
ON CONFLICT (alert_id) DO NOTHING;
