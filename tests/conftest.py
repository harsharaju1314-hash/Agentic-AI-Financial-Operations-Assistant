import os
os.environ["TESTING"] = "1"
os.environ["APP_ENV"] = "test"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from database.connection import Base, get_db
from database.models import Customer, Merchant, Transaction, FraudAlert
from api.main import app
from ml.fraud_detector import FraudDetector
import datetime


# Setup SQLite in-memory engine with StaticPool for fast, isolated test runs
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Creates a clean database session for each test function."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Seed minimal baseline fixtures
    seed_test_fixtures(session)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def seed_test_fixtures(session):
    """Seeds predictable test entities."""
    cust = Customer(
        customer_id="C1001",
        name="Test Customer 1001",
        email="c1001@test.com",
        risk_profile="LOW",
        avg_monthly_spend=1500.0,
        home_country="US",
        home_city="New York",
        account_status="ACTIVE",
    )
    cust2 = Customer(
        customer_id="C1002",
        name="Test Customer 1002",
        email="c1002@test.com",
        risk_profile="HIGH",
        avg_monthly_spend=3000.0,
        home_country="US",
        home_city="San Francisco",
        account_status="ACTIVE",
    )
    merch = Merchant(
        merchant_id="M2001",
        name="Test Merchant Electronics",
        category="Electronics",
        base_risk_score=0.10,
        city="New York",
        country="US",
    )
    merch2 = Merchant(
        merchant_id="M2002",
        name="Test Crypto Exchange",
        category="Crypto Exchange",
        base_risk_score=0.40,
        city="London",
        country="UK",
    )
    session.add_all([cust, cust2, merch, merch2])
    session.commit()

    # Add transactions
    txn1 = Transaction(
        transaction_id="TXN-TEST-101",
        customer_id="C1001",
        merchant_id="M2001",
        amount=55.00,
        currency="USD",
        timestamp=datetime.datetime(2026, 1, 15, 12, 0, 0),
        category="Electronics",
        payment_method="CREDIT_CARD",
        status="COMPLETED",
        location="New York, US",
        historical_avg_spending=50.0,
        anomaly_score=0.12,
        risk_level="LOW",
        is_flagged=False,
    )
    txn2 = Transaction(
        transaction_id="TXN-TEST-102",
        customer_id="C1002",
        merchant_id="M2002",
        amount=4500.00,
        currency="USD",
        timestamp=datetime.datetime(2026, 1, 15, 3, 30, 0),
        category="Crypto Exchange",
        payment_method="CRYPTO",
        status="FLAGGED",
        location="Lagos, NG",
        historical_avg_spending=50.0,
        anomaly_score=0.89,
        risk_level="HIGH",
        is_flagged=True,
        flagged_reason="High risk Crypto Exchange transaction at 03:30 AM",
    )
    session.add_all([txn1, txn2])
    session.commit()

    alert = FraudAlert(
        alert_id="ALT-TEST-501",
        transaction_id="TXN-TEST-102",
        customer_id="C1002",
        risk_level="HIGH",
        anomaly_score=0.89,
        reason="High risk Crypto Exchange transaction at 03:30 AM",
        status="PENDING_REVIEW",
    )
    session.add(alert)
    session.commit()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app, raise_server_exceptions=True)
    yield test_client
    app.dependency_overrides.clear()
