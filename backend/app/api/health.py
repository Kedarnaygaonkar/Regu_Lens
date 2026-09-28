"""Health check API route."""
from fastapi import APIRouter
from app.database import ping_db

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
def health_check():
    db_ok = ping_db()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "service": "ReguLens API",
        "version": "1.0.0",
    }
