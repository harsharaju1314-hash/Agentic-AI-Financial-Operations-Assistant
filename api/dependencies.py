from typing import Optional
from fastapi import Header, HTTPException, Security, status, Depends
from sqlalchemy.orm import Session
from database.connection import get_db
from config.settings import settings


def get_database() -> Session:
    """Yields SQLAlchemy database session."""
    yield from get_db()


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Validates API key for secured endpoints.
    Allows local development bypass if APP_ENV == 'development' and no header sent.
    """
    if settings.APP_ENV in ("development", "test") and not x_api_key:
        return "development_bypass"

    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
