"""
Query Decomposer for cross-document reasoning.

For complex questions requiring multiple documents,
this module breaks them into sub-queries.

Example:
  "How did capital requirements change between 2022 and 2024?"
  → subquery_1: "capital requirements in 2022"
  → subquery_2: "capital requirements in 2024"
  → reasoning: "compare and determine evolution"
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Patterns that indicate cross-document / temporal questions
TEMPORAL_PATTERNS = [
    re.compile(r"\b(between|from|since|before|after)\s+\d{4}", re.IGNORECASE),
    re.compile(r"\b(change|evolv|evolution|history|historical)\b", re.IGNORECASE),
    re.compile(r"\b(vs\.?|versus|compare|comparison)\b", re.IGNORECASE),
    re.compile(r"\b(supersed|replace|amend|consolidat)\b", re.IGNORECASE),
    re.compile(r"\b(current|latest|now|today)\s+.*(was|used to|previously)", re.IGNORECASE),
    re.compile(r"\b(was|used to)\s+.*(current|now|today)", re.IGNORECASE),
]

SUPERSESSION_QUESTION_PATTERNS = [
    re.compile(r"(supersed|replac|cancel|withdrawn|amend)", re.IGNORECASE),
    re.compile(r"(is|was|still)\s+(valid|applicable|current|in\s+force)", re.IGNORECASE),
]


@dataclass
class SubQuery:
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    purpose: str = "retrieval"  # "retrieval" | "comparison" | "supersession_check"
    requires_supersession_check: bool = False


@dataclass
class DecomposedQuery:
    original_question: str
    is_cross_document: bool
    requires_supersession_reasoning: bool
    subqueries: List[SubQuery]
    reasoning_type: str  # "simple" | "temporal_comparison" | "supersession" | "cross_document"


def decompose_query(question: str) -> DecomposedQuery:
    """
    Analyze a question and decompose it into sub-queries if needed.
    
    Returns a DecomposedQuery with subqueries and reasoning type.
    """
    is_temporal = any(p.search(question) for p in TEMPORAL_PATTERNS)
    is_supersession = any(p.search(question) for p in SUPERSESSION_QUESTION_PATTERNS)
    is_cross_doc = is_temporal or is_supersession

    # Extract years mentioned
    years = re.findall(r"\b(20\d{2}|19\d{2})\b", question)

    subqueries = []

    if is_temporal and len(years) >= 2:
        # Temporal comparison — generate sub-query per year
        reasoning_type = "temporal_comparison"
        for year in years:
            # Replace year references to focus on that specific year
            sq_text = _focus_query_on_year(question, year)
            subqueries.append(SubQuery(
                query=sq_text,
                filters={"year": year},
                purpose="retrieval",
            ))
        # Add comparison sub-query
        subqueries.append(SubQuery(
            query=question,
            purpose="comparison",
        ))

    elif is_supersession:
        reasoning_type = "supersession"
        # Primary retrieval query
        subqueries.append(SubQuery(
            query=question,
            purpose="retrieval",
            requires_supersession_check=True,
        ))
        # Also retrieve current version
        current_q = _make_current_version_query(question)
        if current_q:
            subqueries.append(SubQuery(
                query=current_q,
                purpose="supersession_check",
                requires_supersession_check=True,
            ))

    else:
        reasoning_type = "simple"
        subqueries.append(SubQuery(
            query=question,
            purpose="retrieval",
        ))

    return DecomposedQuery(
        original_question=question,
        is_cross_document=is_cross_doc,
        requires_supersession_reasoning=is_supersession or is_temporal,
        subqueries=subqueries,
        reasoning_type=reasoning_type,
    )


def _focus_query_on_year(question: str, year: str) -> str:
    """Create a focused sub-query for a specific year."""
    # Add year context
    return f"{question} [focus: year {year}]"


def _make_current_version_query(question: str) -> Optional[str]:
    """Create a query to find the current/latest version."""
    # Strip temporal references and ask for current
    cleaned = re.sub(r"\b(was|were|in \d{4})\b", "", question, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    if cleaned:
        return f"current {cleaned}"
    return None
