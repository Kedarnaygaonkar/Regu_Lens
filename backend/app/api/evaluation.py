"""
Evaluation API routes.
POST /evaluation/run
GET  /evaluation/results
GET  /evaluation/cases
POST /evaluation/cases (seed)
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.database import Collections, get_sync_db
from app.embeddings import get_embedding_provider
from app.evaluation.evaluator import run_full_evaluation
from app.models.evaluation import EvaluationCase, EvaluationRunRequest

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


def _get_embedding_provider():
    settings = get_settings()
    try:
        return get_embedding_provider(
            provider=settings.embedding_provider,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
        )
    except Exception:
        return None


@router.post("/run", summary="Run evaluation")
def run_evaluation(request: EvaluationRunRequest):
    """
    Run evaluation against the specified system(s).
    system: "regulens" | "naive_rag" | "both"
    """
    emb_provider = _get_embedding_provider()
    summaries = run_full_evaluation(
        system=request.system,
        case_ids=request.case_ids,
        embedding_provider=emb_provider,
    )
    return {
        sys_name: {
            "system_name": s.system_name,
            "total_cases": s.total_cases,
            "metrics": s.metrics.model_dump(),
        }
        for sys_name, s in summaries.items()
    }


@router.get("/results", summary="Get evaluation results")
def get_evaluation_results(
    system_name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Get stored evaluation results."""
    db = get_sync_db()
    filter_doc = {}
    if system_name:
        filter_doc["system_name"] = system_name

    results = list(
        db[Collections.EVALUATION_RESULTS]
        .find(filter_doc, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    total = db[Collections.EVALUATION_RESULTS].count_documents(filter_doc)
    return {"results": results, "total": total}


@router.get("/cases", summary="List evaluation cases")
def list_evaluation_cases():
    """List all evaluation cases."""
    db = get_sync_db()
    cases = list(db[Collections.EVALUATION_CASES].find({}, {"_id": 0}))
    return {"cases": cases, "total": len(cases)}


@router.post("/cases/seed", summary="Seed evaluation cases from dataset")
def seed_evaluation_cases():
    """Load the built-in 30+ evaluation cases into MongoDB."""
    from scripts.seed_evaluation import EVALUATION_CASES
    db = get_sync_db()
    col = db[Collections.EVALUATION_CASES]
    inserted = 0
    for case in EVALUATION_CASES:
        existing = col.find_one({"case_id": case["case_id"]})
        if not existing:
            col.insert_one(case)
            inserted += 1
    return {"inserted": inserted, "total": len(EVALUATION_CASES)}
