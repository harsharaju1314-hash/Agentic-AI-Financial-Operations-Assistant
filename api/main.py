import os
import time
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from database.connection import init_db
from database.sql_validator import SQLSecurityError
from data.ingestion import ingest_initial_seed_data
from api.routers import (
    transactions_router,
    fraud_router,
    analytics_router,
    agents_router,
    reports_router,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finops_api")

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Multi-Agent AI Financial Operations & Fraud Investigation Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized Exception Handlers
@app.exception_handler(SQLSecurityError)
async def sql_security_exception_handler(request: Request, exc: SQLSecurityError):
    logger.warning(f"SQL Security Violation: {str(exc)} on path {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "SQLSecurityViolation", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "InternalServerError", "detail": "An unexpected error occurred during processing."},
    )


# Mount API Routers
app.include_router(transactions_router)
app.include_router(fraud_router)
app.include_router(analytics_router)
app.include_router(agents_router)
app.include_router(reports_router)


@app.get("/health", tags=["Health"])
def health_check():
    """System health-check endpoint for load balancers and container orchestrators."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
