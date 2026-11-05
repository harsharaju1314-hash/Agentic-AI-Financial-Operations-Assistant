import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Agentic AI Financial Operations Assistant"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    DEBUG: bool = True
    API_KEY: str = "finops-secret-key-development"

    # Database
    DATABASE_URL: str = "sqlite:///./financial_ops.db"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20

    # Agent & LLM
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    MAX_AGENT_ITERATIONS: int = 6

    # Machine Learning & Fraud
    MODEL_PATH: str = "ml/models/fraud_isolation_forest.joblib"
    FRAUD_CONTAMINATION: float = 0.03
    HIGH_RISK_THRESHOLD: float = 0.75
    MEDIUM_RISK_THRESHOLD: float = 0.40

    # Cloud Storage (AWS S3)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_DEFAULT_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "finops-transactions-archive"

    # Streamlit UI
    STREAMLIT_PORT: int = 8501
    BACKEND_API_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
