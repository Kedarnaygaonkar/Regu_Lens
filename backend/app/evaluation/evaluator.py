"""
Evaluation engine for ReguLens.
Runs evaluation cases against System A (Naive RAG) and System B (ReguLens).
Computes: Recall@K, Precision@K, MRR, answer correctness, citation accuracy,
supersession accuracy, cross-document accuracy, latency.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.database import Collections, get_sync_db
from app.models.evaluation import (
    EvaluationCase, EvaluationMetrics, EvaluationResult, EvaluationSummary
)
from app.models.query import AskRequest, AskResponse
from app.rag.answer_generator import AnswerGenerator
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.retrieval.keyword_search import keyword_search

logger = logging.getLogger(__name__)


def _recall_at_k(retrieved: List[str], expected: List[str], k: int) -> float:
    if not expected:
        return 1.0
    retrieved_k = set(retrieved[:k])
    expected_set = set(expected)
    overlap = retrieved_k & expected_set
    return len(overlap) / len(expected_set)


def _precision_at_k(retrieved: List[str], expected: List[str], k: int) -> float:
    if not retrieved or k == 0:
        return 0.0
    retrieved_k = retrieved[:k]
    expected_set = set(expected)
    hits = sum(1 for r in retrieved_k if r in expected_set)
    return hits / k


def _mrr(retrieved: List[str], expected: List[str]) -> float:
    expected_set = set(expected)
    for rank, r in enumerate(retrieved, 1):
        if r in expected_set:
            return 1.0 / rank
    return 0.0


def _answer_correctness_heuristic(answer: str, expected: str) -> float:
    """
    Heuristic: check if key phrases from expected answer appear in generated answer.
    Returns fraction of expected key terms found.
    """
    if not expected:
        return 1.0
    # Extract key numeric/percent values
    import re
    expected_nums = set(re.findall(r"\d+(?:\.\d+)?%?", expected.lower()))
    answer_nums = set(re.findall(r"\d+(?:\.\d+)?%?", answer.lower()))
    if not expected_nums:
        # Keyword overlap
        expected_words = set(expected.lower().split())
        answer_words = set(answer.lower().split())
        overlap = expected_words & answer_words
        return min(1.0, len(overlap) / max(len(expected_words), 1))
    hit = len(expected_nums & answer_nums)
    return hit / len(expected_nums)


def run_evaluation_case(
    case: EvaluationCase,
    system_name: str,
    generator: AnswerGenerator,
    embedding_provider=None,
    k: int = 10,
) -> EvaluationResult:
    """Run a single evaluation case and return results."""
    start = time.time()

    # Get answer
    request = AskRequest(
        question=case.question,
        top_k=k,
        include_superseded=True,  # Include all for evaluation
        use_cross_document_reasoning=case.requires_multiple_documents,
    )

    try:
        response: AskResponse = generator.answer(request)
        answer = response.answer
        citations = [c.model_dump() for c in response.citations]
        retrieved_chunks = response.retrieved_chunk_ids
        retrieved_docs = list(set(
            e.get("document_id", "") for e in response.evidence
        ))
    except Exception as e:
        logger.error(f"Evaluation case {case.case_id} failed: {e}")
        answer = ""
        citations = []
        retrieved_chunks = []
        retrieved_docs = []

    elapsed = (time.time() - start) * 1000

    # Compute metrics
    recall = _recall_at_k(retrieved_docs, case.expected_documents, k)
    precision = _precision_at_k(retrieved_docs, case.expected_documents, k)
    mrr = _mrr(retrieved_docs, case.expected_documents)
    correctness = _answer_correctness_heuristic(answer, case.expected_answer)

    # Citation accuracy: did we cite any expected document?
    cited_doc_ids = [c.get("document_id", "") for c in citations]
    expected_doc_set = set(case.expected_documents)
    citation_accuracy = (
        len(set(cited_doc_ids) & expected_doc_set) / max(len(expected_doc_set), 1)
        if expected_doc_set else 1.0
    )

    # Supersession accuracy
    supersession_acc = 0.0
    if case.requires_supersession_reasoning:
        # Check if the answer mentions supersession or historical context
        supersession_keywords = ["supersed", "replac", "amend", "current", "historical", "2019", "2022", "2024"]
        hits = sum(1 for kw in supersession_keywords if kw.lower() in answer.lower())
        supersession_acc = min(1.0, hits / 3.0)
    else:
        supersession_acc = 1.0

    # Cross-document accuracy
    cross_doc_acc = 0.0
    if case.requires_multiple_documents:
        cross_doc_acc = 1.0 if len(retrieved_docs) >= 2 else 0.0
    else:
        cross_doc_acc = 1.0

    metrics = EvaluationMetrics(
        recall_at_k=recall,
        precision_at_k=precision,
        mrr=mrr,
        answer_correctness=correctness,
        citation_accuracy=citation_accuracy,
        supersession_accuracy=supersession_acc,
        cross_document_accuracy=cross_doc_acc,
        latency_ms=elapsed,
    )

    return EvaluationResult(
        case_id=case.case_id,
        system_name=system_name,
        retrieved_documents=retrieved_docs,
        retrieved_chunks=retrieved_chunks[:20],
        answer=answer,
        citations=citations,
        metrics=metrics,
        latency=elapsed,
    )


def run_naive_rag_evaluation(
    case: EvaluationCase,
    embedding_provider=None,
    k: int = 10,
) -> EvaluationResult:
    """
    System A — Naive RAG evaluation.
    Fixed-size chunks, vector search only.
    """
    from app.retrieval.vector_search import vector_search
    import time

    start = time.time()
    query_embedding = []
    if embedding_provider:
        try:
            query_embedding = embedding_provider.embed_query(case.question)
        except Exception:
            pass

    # Vector search only, naive chunks
    db = get_sync_db()
    chunks_col = db[Collections.CHUNKS]
    
    results = vector_search(
        query_embedding=query_embedding,
        top_k=k,
        include_superseded=True,
    )
    
    # Filter to naive chunks only
    results = [r for r in results if r.get("metadata", {}).get("chunking_strategy") == "naive"][:k]
    
    retrieved_docs = list(set(r.get("document_id", "") for r in results))
    retrieved_chunks = [r.get("chunk_id", "") for r in results]
    
    # Simple answer: concatenate top chunks
    context = "\n\n".join([r.get("text", "") for r in results[:5]])
    answer = f"[Naive RAG] Based on retrieved context:\n{context[:1000]}"
    
    elapsed = (time.time() - start) * 1000
    
    recall = _recall_at_k(retrieved_docs, case.expected_documents, k)
    precision = _precision_at_k(retrieved_docs, case.expected_documents, k)
    mrr = _mrr(retrieved_docs, case.expected_documents)
    correctness = _answer_correctness_heuristic(answer, case.expected_answer)

    metrics = EvaluationMetrics(
        recall_at_k=recall,
        precision_at_k=precision,
        mrr=mrr,
        answer_correctness=correctness,
        citation_accuracy=0.0,
        supersession_accuracy=0.0,
        cross_document_accuracy=0.0,
        latency_ms=elapsed,
    )

    return EvaluationResult(
        case_id=case.case_id,
        system_name="naive_rag",
        retrieved_documents=retrieved_docs,
        retrieved_chunks=retrieved_chunks,
        answer=answer,
        citations=[],
        metrics=metrics,
        latency=elapsed,
    )


def run_full_evaluation(
    system: str = "both",
    case_ids: Optional[List[str]] = None,
    embedding_provider=None,
) -> Dict[str, EvaluationSummary]:
    """
    Run all evaluation cases for the specified system(s).
    Returns dict of system_name → EvaluationSummary.
    """
    db = get_sync_db()
    
    # Load cases
    query = {}
    if case_ids:
        query["case_id"] = {"$in": case_ids}
    
    cases_raw = list(db[Collections.EVALUATION_CASES].find(query, {"_id": 0}))
    cases = [EvaluationCase(**c) for c in cases_raw]
    
    if not cases:
        logger.warning("No evaluation cases found in database")
        return {}

    generator = AnswerGenerator(embedding_provider=embedding_provider)
    summaries = {}

    systems_to_run = []
    if system in ("regulens", "both"):
        systems_to_run.append("regulens")
    if system in ("naive_rag", "both"):
        systems_to_run.append("naive_rag")

    for sys_name in systems_to_run:
        results = []
        for case in cases:
            logger.info(f"Running {sys_name} on case: {case.case_id}")
            if sys_name == "regulens":
                result = run_evaluation_case(case, "regulens", generator, embedding_provider)
            else:
                result = run_naive_rag_evaluation(case, embedding_provider)
            
            # Store result
            db[Collections.EVALUATION_RESULTS].update_one(
                {"case_id": result.case_id, "system_name": result.system_name},
                {"$set": result.model_dump()},
                upsert=True,
            )
            results.append(result)

        # Aggregate metrics
        n = len(results)
        if n > 0:
            avg = EvaluationMetrics(
                recall_at_k=sum(r.metrics.recall_at_k for r in results) / n,
                precision_at_k=sum(r.metrics.precision_at_k for r in results) / n,
                mrr=sum(r.metrics.mrr for r in results) / n,
                answer_correctness=sum(r.metrics.answer_correctness for r in results) / n,
                citation_accuracy=sum(r.metrics.citation_accuracy for r in results) / n,
                supersession_accuracy=sum(r.metrics.supersession_accuracy for r in results) / n,
                cross_document_accuracy=sum(r.metrics.cross_document_accuracy for r in results) / n,
                latency_ms=sum(r.metrics.latency_ms for r in results) / n,
            )
        else:
            avg = EvaluationMetrics()

        summaries[sys_name] = EvaluationSummary(
            system_name=sys_name,
            total_cases=n,
            metrics=avg,
            results=results,
        )

    return summaries
