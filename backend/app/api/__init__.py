"""API package."""
from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.search import router as search_router
from app.api.ask import router as ask_router
from app.api.evaluation import router as evaluation_router

__all__ = [
    "health_router",
    "documents_router",
    "search_router",
    "ask_router",
    "evaluation_router",
]
