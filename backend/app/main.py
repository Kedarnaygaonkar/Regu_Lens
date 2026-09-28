"""
ReguLens FastAPI Application Entry Point.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    health_router, documents_router, search_router, ask_router, evaluation_router
)
from app.config import get_settings
from app.database import ping_db, setup_indexes
from app.utils.logging import setup_logging

# ── Setup logging ──────────────────────────────────────────────────────────────
setup_logging("DEBUG" if os.getenv("DEBUG", "false").lower() == "true" else "INFO")
logger = logging.getLogger(__name__)

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ReguLens API",
    description=(
        "Version-Aware Regulatory Intelligence & Retrieval System for Indian "
        "financial regulations (RBI, SEBI, IRDAI). "
        "Provides hybrid retrieval, supersession tracking, and provenance-rich answers."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(ask_router)
app.include_router(evaluation_router)


# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup_event():
    logger.info("ReguLens API starting up…")
    settings = get_settings()
    logger.info(f"MongoDB database: {settings.mongodb_database}")
    logger.info(f"Embedding provider: {settings.embedding_provider} / {settings.embedding_model}")
    logger.info(f"LLM provider: {settings.llm_provider} / {settings.llm_model}")

    if ping_db():
        logger.info("✓ MongoDB Atlas connected")
        setup_indexes()
        logger.info("✓ MongoDB indexes ensured")
    else:
        logger.error("✗ MongoDB Atlas connection failed — check MONGODB_URI")

    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info("ReguLens API ready")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("ReguLens API shutting down")


# ── Root redirect ──────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return {"message": "ReguLens API — see /docs for API reference"}
