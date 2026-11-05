from api.routers.transactions import router as transactions_router
from api.routers.fraud import router as fraud_router
from api.routers.analytics import router as analytics_router
from api.routers.agents import router as agents_router
from api.routers.reports import router as reports_router

__all__ = [
    "transactions_router",
    "fraud_router",
    "analytics_router",
    "agents_router",
    "reports_router",
]
