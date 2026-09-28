"""
MongoDB Atlas connection management for ReguLens.
Uses motor for async operations and pymongo for sync operations.
"""
from __future__ import annotations

import logging
from typing import Optional

import motor.motor_asyncio
import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import get_settings

logger = logging.getLogger(__name__)

# ─── Sync client (for scripts and setup) ──────────────────────────────────────
_sync_client: Optional[MongoClient] = None


def get_sync_client() -> MongoClient:
    global _sync_client
    if _sync_client is None:
        settings = get_settings()
        _sync_client = MongoClient(settings.mongodb_uri)
        logger.info("Sync MongoDB client created")
    return _sync_client


def get_sync_db() -> Database:
    settings = get_settings()
    return get_sync_client()[settings.mongodb_database]


def get_sync_collection(name: str) -> Collection:
    return get_sync_db()[name]


# ─── Async client (for FastAPI) ───────────────────────────────────────────────
_async_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None


def get_async_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    global _async_client
    if _async_client is None:
        settings = get_settings()
        _async_client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_uri)
        logger.info("Async MongoDB client created")
    return _async_client


def get_async_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    settings = get_settings()
    return get_async_client()[settings.mongodb_database]


def get_async_collection(name: str) -> motor.motor_asyncio.AsyncIOMotorCollection:
    return get_async_db()[name]


# ─── Collection name constants ────────────────────────────────────────────────
class Collections:
    DOCUMENTS = "documents"
    SECTIONS = "sections"
    CHUNKS = "chunks"
    DOCUMENT_RELATIONSHIPS = "document_relationships"
    DUPLICATE_GROUPS = "duplicate_groups"
    EVALUATION_CASES = "evaluation_cases"
    EVALUATION_RESULTS = "evaluation_results"
    QUERY_LOGS = "query_logs"


# ─── Index setup (run once at startup or via script) ─────────────────────────
def setup_indexes(db: Optional[Database] = None) -> None:
    """Create all required MongoDB indexes. Safe to run multiple times (idempotent)."""
    if db is None:
        db = get_sync_db()

    logger.info("Setting up MongoDB indexes…")

    # documents
    docs = db[Collections.DOCUMENTS]
    docs.create_index("document_id", unique=True)
    docs.create_index("content_hash")
    docs.create_index("status")
    docs.create_index("issuer")
    docs.create_index("document_type")
    docs.create_index([("publication_date", pymongo.DESCENDING)])

    # sections
    secs = db[Collections.SECTIONS]
    secs.create_index("section_id", unique=True)
    secs.create_index("document_id")
    secs.create_index("content_hash")

    # chunks
    chunks = db[Collections.CHUNKS]
    chunks.create_index("chunk_id", unique=True)
    chunks.create_index("document_id")
    chunks.create_index("section_id")
    chunks.create_index("content_hash")
    chunks.create_index("document_status")
    chunks.create_index([("created_at", pymongo.DESCENDING)])

    # document_relationships
    rels = db[Collections.DOCUMENT_RELATIONSHIPS]
    rels.create_index("relationship_id", unique=True)
    rels.create_index("source_document_id")
    rels.create_index("target_document_id")
    rels.create_index("relationship_type")

    # duplicate_groups
    dups = db[Collections.DUPLICATE_GROUPS]
    dups.create_index("group_id", unique=True)
    dups.create_index("canonical_chunk_id")

    # evaluation_cases
    evals = db[Collections.EVALUATION_CASES]
    evals.create_index("case_id", unique=True)
    evals.create_index("question_type")

    # evaluation_results
    results = db[Collections.EVALUATION_RESULTS]
    results.create_index([("case_id", 1), ("system_name", 1)])

    # query_logs
    logs = db[Collections.QUERY_LOGS]
    logs.create_index([("created_at", pymongo.DESCENDING)])

    logger.info("MongoDB indexes created successfully")


def ping_db() -> bool:
    """Returns True if the database is reachable."""
    try:
        get_sync_client().admin.command("ping")
        return True
    except Exception as exc:
        logger.error(f"MongoDB ping failed: {exc}")
        return False
