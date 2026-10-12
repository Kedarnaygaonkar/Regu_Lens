"""
Ask API route.
POST /ask — RAG question answering with provenance
"""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.embeddings import get_embedding_provider
from app.models.query import AskRequest, AskResponse
from app.rag.answer_generator import AnswerGenerator

router = APIRouter(tags=["Ask"])


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


@router.post("/ask", response_model=AskResponse, summary="Ask a regulatory question")
def ask(request: AskRequest):
    """
    Ask a question about regulatory documents.
    Returns an answer with citations, supersession notes, and an evidence graph.
    """
    emb_provider = _get_embedding_provider()
    generator = AnswerGenerator(embedding_provider=emb_provider)
    try:
        return generator.answer(request)
    except Exception as exc:
        from app.models.query import AnswerStatus
        return AskResponse(
            question=request.question,
            answer=f"An error occurred while generating the answer: {exc}",
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            citations=[],
            supersession_notes=[],
            evidence=[],
            related_documents=[],
            latency_ms=0.0,
        )
