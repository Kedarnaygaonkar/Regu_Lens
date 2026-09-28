"""Pydantic models for evaluation cases and results."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    SINGLE_DOCUMENT = "SINGLE_DOCUMENT"
    SECTION_RETRIEVAL = "SECTION_RETRIEVAL"
    TABLE_QUESTION = "TABLE_QUESTION"
    CROSS_DOCUMENT = "CROSS_DOCUMENT"
    SUPERSESSION = "SUPERSESSION"
    HISTORICAL = "HISTORICAL"
    CURRENT_RULE = "CURRENT_RULE"
    CITATION = "CITATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvaluationCase(BaseModel):
    case_id: str
    question: str
    question_type: QuestionType
    expected_documents: List[str] = Field(default_factory=list)
    expected_sections: List[str] = Field(default_factory=list)
    expected_answer: str = ""
    requires_multiple_documents: bool = False
    requires_supersession_reasoning: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationMetrics(BaseModel):
    recall_at_k: float = 0.0
    precision_at_k: float = 0.0
    mrr: float = 0.0
    answer_correctness: float = 0.0
    citation_accuracy: float = 0.0
    supersession_accuracy: float = 0.0
    cross_document_accuracy: float = 0.0
    latency_ms: float = 0.0


class EvaluationResult(BaseModel):
    case_id: str
    system_name: str  # "naive_rag" | "regulens"
    retrieved_documents: List[str] = Field(default_factory=list)
    retrieved_chunks: List[str] = Field(default_factory=list)
    answer: str = ""
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: EvaluationMetrics = Field(default_factory=EvaluationMetrics)
    latency: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EvaluationRunRequest(BaseModel):
    system: str = "regulens"  # "naive_rag" | "regulens" | "both"
    case_ids: Optional[List[str]] = None  # None = run all
    question_types: Optional[List[QuestionType]] = None


class EvaluationSummary(BaseModel):
    system_name: str
    total_cases: int
    metrics: EvaluationMetrics
    results: List[EvaluationResult] = Field(default_factory=list)
