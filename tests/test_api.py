import pytest
from fastapi import status


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == status.HTTP_200_OK
    assert "version" in res.json()


def test_list_transactions(client):
    res = client.get("/transactions")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_get_single_transaction(client):
    res = client.get("/transactions/TXN-TEST-101")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["transaction_id"] == "TXN-TEST-101"
    assert data["amount"] == 55.00


def test_get_single_transaction_not_found(client):
    res = client.get("/transactions/TXN-NONEXISTENT")
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_get_customer_transactions(client):
    res = client.get("/transactions/customer/C1001")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["customer_id"] == "C1001"
    assert data["total_spent_usd"] == 55.00


def test_create_transaction(client):
    payload = {
        "customer_id": "C1001",
        "merchant_id": "M2001",
        "amount": 120.00,
        "category": "Electronics",
        "payment_method": "CREDIT_CARD",
        "location": "New York, US",
        "historical_avg_spending": 60.0,
    }
    res = client.post("/transactions", json=payload)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["amount"] == 120.00
    assert "anomaly_score" in data
    assert "risk_level" in data


def test_batch_create_transactions(client):
    payload = {
        "transactions": [
            {
                "customer_id": "C1001",
                "merchant_id": "M2001",
                "amount": 45.0,
                "category": "Groceries",
                "payment_method": "DEBIT_CARD",
            },
            {
                "customer_id": "C1002",
                "merchant_id": "M2002",
                "amount": 9000.0,
                "category": "Crypto Exchange",
                "payment_method": "CRYPTO",
            },
        ]
    }
    res = client.post("/transactions/batch", json=payload)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["ingested_count"] == 2


def test_fraud_analyze(client):
    payload = {
        "amount": 8000.0,
        "historical_avg_spending": 50.0,
        "category": "Crypto Exchange",
        "payment_method": "CRYPTO",
        "location": "Lagos, NG",
    }
    res = client.post("/fraud/analyze", json=payload)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["risk_level"] == "HIGH"
    assert data["is_flagged"] is True


def test_get_fraud_alerts(client):
    res = client.get("/fraud/alerts")
    assert res.status_code == status.HTTP_200_OK
    alerts = res.json()
    assert len(alerts) >= 1
    assert alerts[0]["alert_id"] == "ALT-TEST-501"


def test_take_alert_action(client):
    action_payload = {
        "action": "ACCOUNT_FROZEN",
        "reviewed_by": "Senior_Risk_Officer",
        "resolution_notes": "Confirmed high velocity fraudulent crypto purchase.",
    }
    res = client.post("/fraud/alerts/ALT-TEST-501/action", json=action_payload)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "APPROVED_ACTION"
    assert data["action_taken"] == "ACCOUNT_FROZEN"
    assert data["reviewed_by"] == "Senior_Risk_Officer"


def test_analytics_summary(client):
    res = client.get("/analytics/summary")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "total_transactions" in data
    assert "total_volume_usd" in data


def test_analytics_top_merchants(client):
    res = client.get("/analytics/merchants/top?limit=3")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert isinstance(data, list)


def test_agent_query_endpoint(client):
    payload = {"query": "Find unusual transactions for customer C1002."}
    res = client.post("/agents/query", json=payload)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["intent"] == "FRAUD_INVESTIGATION"
    assert len(data["routed_agents"]) > 0
    assert "final_response" in data


def test_financial_report_endpoint(client):
    res = client.get("/reports/financial?customer_id=C1001")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "title" in data
    assert "executive_summary" in data
