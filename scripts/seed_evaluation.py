"""
Seed 30+ evaluation cases into MongoDB.
These cases cover all evaluation categories.
"""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime

# Import document IDs as placeholders — replace with actual IDs after ingestion
DOC_2019 = "doc_2019_circular"
DOC_2022 = "doc_2022_amendment"
DOC_2024 = "doc_2024_master_direction"

EVALUATION_CASES = [
    # ── SINGLE DOCUMENT QUESTIONS (5) ─────────────────────────────────────────
    {
        "case_id": "SD_001",
        "question": "What is the minimum Capital Adequacy Ratio as per the 2024 Master Direction?",
        "question_type": "SINGLE_DOCUMENT",
        "expected_documents": [DOC_2024],
        "expected_sections": ["2.1"],
        "expected_answer": "20 percent",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "SD_002",
        "question": "What did the 2019 RBI Circular specify about capital requirements?",
        "question_type": "SINGLE_DOCUMENT",
        "expected_documents": [DOC_2019],
        "expected_sections": ["2.1"],
        "expected_answer": "10 percent",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "SD_003",
        "question": "What is the Capital Conservation Buffer requirement in the 2024 Master Direction?",
        "question_type": "SINGLE_DOCUMENT",
        "expected_documents": [DOC_2024],
        "expected_sections": ["2.2"],
        "expected_answer": "2.5 percent",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "SD_004",
        "question": "When did the 2022 amendment come into effect?",
        "question_type": "SINGLE_DOCUMENT",
        "expected_documents": [DOC_2022],
        "expected_sections": ["4"],
        "expected_answer": "July 1, 2022",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "SD_005",
        "question": "To whom does the 2019 capital requirements circular apply?",
        "question_type": "SINGLE_DOCUMENT",
        "expected_documents": [DOC_2019],
        "expected_sections": ["4"],
        "expected_answer": "All scheduled commercial banks",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },

    # ── SECTION RETRIEVAL (4) ─────────────────────────────────────────────────
    {
        "case_id": "SR_001",
        "question": "What does Section 2.1 of the 2024 Master Direction say?",
        "question_type": "SECTION_RETRIEVAL",
        "expected_documents": [DOC_2024],
        "expected_sections": ["2.1"],
        "expected_answer": "minimum Capital Adequacy Ratio (CAR) of 20 percent",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "SR_002",
        "question": "What is specified under Section 3 of the 2024 Master Direction?",
        "question_type": "SECTION_RETRIEVAL",
        "expected_documents": [DOC_2024],
        "expected_sections": ["3"],
        "expected_answer": "Evolution of capital requirements",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "SR_003",
        "question": "What does paragraph 2.2 of the 2022 amendment specify?",
        "question_type": "SECTION_RETRIEVAL",
        "expected_documents": [DOC_2022],
        "expected_sections": ["2.2"],
        "expected_answer": "Capital Conservation Buffer of 2.5 percent",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "SR_004",
        "question": "What are the reporting requirements specified in the 2024 Master Direction?",
        "question_type": "SECTION_RETRIEVAL",
        "expected_documents": [DOC_2024],
        "expected_sections": ["4"],
        "expected_answer": "quarterly basis",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },

    # ── TABLE QUESTIONS (2) ───────────────────────────────────────────────────
    {
        "case_id": "TQ_001",
        "question": "What does the table in the 2024 Master Direction show about the evolution of CAR requirements?",
        "question_type": "TABLE_QUESTION",
        "expected_documents": [DOC_2024],
        "expected_sections": ["3"],
        "expected_answer": "10% in 2019, 15% in 2022, 20% in 2024",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "TQ_002",
        "question": "According to the historical table, what was the CAR in 2022?",
        "question_type": "TABLE_QUESTION",
        "expected_documents": [DOC_2024],
        "expected_sections": ["3"],
        "expected_answer": "15%",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },

    # ── CROSS-DOCUMENT QUESTIONS (4) ─────────────────────────────────────────
    {
        "case_id": "CD_001",
        "question": "How did the capital adequacy requirement change between 2019 and 2022?",
        "question_type": "CROSS_DOCUMENT",
        "expected_documents": [DOC_2019, DOC_2022],
        "expected_sections": ["2.1"],
        "expected_answer": "increased from 10% to 15%",
        "requires_multiple_documents": True,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "CD_002",
        "question": "What changed between the 2022 amendment and the 2024 Master Direction?",
        "question_type": "CROSS_DOCUMENT",
        "expected_documents": [DOC_2022, DOC_2024],
        "expected_sections": ["2.1"],
        "expected_answer": "CAR increased from 15% to 20%",
        "requires_multiple_documents": True,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "CD_003",
        "question": "Explain the evolution of capital requirements from 2019 to 2024.",
        "question_type": "CROSS_DOCUMENT",
        "expected_documents": [DOC_2019, DOC_2022, DOC_2024],
        "expected_sections": ["2.1"],
        "expected_answer": "10% in 2019, 15% in 2022, 20% in 2024",
        "requires_multiple_documents": True,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "CD_004",
        "question": "Does the 2024 Master Direction supersede both the 2019 circular and the 2022 amendment?",
        "question_type": "CROSS_DOCUMENT",
        "expected_documents": [DOC_2019, DOC_2022, DOC_2024],
        "expected_sections": ["1", "7"],
        "expected_answer": "Yes, it supersedes both",
        "requires_multiple_documents": True,
        "requires_supersession_reasoning": True,
    },

    # ── SUPERSESSION QUESTIONS (5) ────────────────────────────────────────────
    {
        "case_id": "SUP_001",
        "question": "Was the 2019 circular superseded?",
        "question_type": "SUPERSESSION",
        "expected_documents": [DOC_2019, DOC_2024],
        "expected_sections": ["1", "7"],
        "expected_answer": "Yes, superseded by the 2024 Master Direction",
        "requires_multiple_documents": True,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "SUP_002",
        "question": "Which circular supersedes RBI/2019-20/001?",
        "question_type": "SUPERSESSION",
        "expected_documents": [DOC_2024],
        "expected_sections": ["7"],
        "expected_answer": "RBI/2024-25/MD-01, the 2024 Master Direction",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "SUP_003",
        "question": "Is the 2022 amendment still valid?",
        "question_type": "SUPERSESSION",
        "expected_documents": [DOC_2022, DOC_2024],
        "expected_sections": ["7"],
        "expected_answer": "No, it was superseded by the 2024 Master Direction",
        "requires_multiple_documents": True,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "SUP_004",
        "question": "Does the 2022 amendment supersede the 2019 circular?",
        "question_type": "SUPERSESSION",
        "expected_documents": [DOC_2019, DOC_2022],
        "expected_sections": ["1"],
        "expected_answer": "It partially amends the 2019 circular (not full supersession)",
        "requires_multiple_documents": True,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "SUP_005",
        "question": "List all the circulars that were superseded by the 2024 Master Direction.",
        "question_type": "SUPERSESSION",
        "expected_documents": [DOC_2024],
        "expected_sections": ["1", "7"],
        "expected_answer": "RBI/2019-20/001 and RBI/2022-23/045",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": True,
    },

    # ── HISTORICAL QUESTIONS (3) ──────────────────────────────────────────────
    {
        "case_id": "HIS_001",
        "question": "What was the capital adequacy requirement in 2019?",
        "question_type": "HISTORICAL",
        "expected_documents": [DOC_2019],
        "expected_sections": ["2.1"],
        "expected_answer": "10 percent",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "HIS_002",
        "question": "What was the CAR requirement before the 2024 Master Direction?",
        "question_type": "HISTORICAL",
        "expected_documents": [DOC_2022],
        "expected_sections": ["2.1"],
        "expected_answer": "15 percent (as per 2022 amendment)",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "HIS_003",
        "question": "When was the first capital adequacy requirement introduced per these documents?",
        "question_type": "HISTORICAL",
        "expected_documents": [DOC_2019],
        "expected_sections": ["3"],
        "expected_answer": "April 1, 2019",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },

    # ── CURRENT RULE QUESTIONS (4) ────────────────────────────────────────────
    {
        "case_id": "CR_001",
        "question": "What is the current minimum capital adequacy requirement?",
        "question_type": "CURRENT_RULE",
        "expected_documents": [DOC_2024],
        "expected_sections": ["2.1"],
        "expected_answer": "20 percent",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "CR_002",
        "question": "What CAR must banks maintain today?",
        "question_type": "CURRENT_RULE",
        "expected_documents": [DOC_2024],
        "expected_sections": ["2.1"],
        "expected_answer": "20 percent",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "CR_003",
        "question": "Which document contains the latest applicable capital requirements?",
        "question_type": "CURRENT_RULE",
        "expected_documents": [DOC_2024],
        "expected_sections": ["1"],
        "expected_answer": "RBI Master Direction 2024",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "CR_004",
        "question": "Is the 10% capital requirement still applicable?",
        "question_type": "CURRENT_RULE",
        "expected_documents": [DOC_2019, DOC_2024],
        "expected_sections": ["2.1"],
        "expected_answer": "No, it was superseded. Current requirement is 20%.",
        "requires_multiple_documents": True,
        "requires_supersession_reasoning": True,
    },

    # ── CITATION QUESTIONS (2) ────────────────────────────────────────────────
    {
        "case_id": "CIT_001",
        "question": "Cite the exact provision that sets the current CAR at 20%.",
        "question_type": "CITATION",
        "expected_documents": [DOC_2024],
        "expected_sections": ["2.1"],
        "expected_answer": "Section 2.1 of RBI/2024-25/MD-01",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": True,
    },
    {
        "case_id": "CIT_002",
        "question": "What is the reference number of the circular that first set CAR at 10%?",
        "question_type": "CITATION",
        "expected_documents": [DOC_2019],
        "expected_sections": ["1"],
        "expected_answer": "RBI/2019-20/001",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },

    # ── INSUFFICIENT EVIDENCE QUESTIONS (3) ──────────────────────────────────
    {
        "case_id": "IE_001",
        "question": "What is the Liquidity Coverage Ratio requirement?",
        "question_type": "INSUFFICIENT_EVIDENCE",
        "expected_documents": [],
        "expected_sections": [],
        "expected_answer": "Insufficient evidence",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "IE_002",
        "question": "What are the SEBI regulations for mutual fund NAV?",
        "question_type": "INSUFFICIENT_EVIDENCE",
        "expected_documents": [],
        "expected_sections": [],
        "expected_answer": "Insufficient evidence",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
    {
        "case_id": "IE_003",
        "question": "What is the maximum interest rate on savings accounts?",
        "question_type": "INSUFFICIENT_EVIDENCE",
        "expected_documents": [],
        "expected_sections": [],
        "expected_answer": "Insufficient evidence",
        "requires_multiple_documents": False,
        "requires_supersession_reasoning": False,
    },
]


def seed_to_mongodb():
    """Seed evaluation cases into MongoDB."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    from app.database import Collections, get_sync_db

    db = get_sync_db()
    col = db[Collections.EVALUATION_CASES]

    inserted = 0
    updated = 0
    for case in EVALUATION_CASES:
        result = col.update_one(
            {"case_id": case["case_id"]},
            {"$set": case},
            upsert=True,
        )
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1

    print(f"Evaluation cases seeded: {inserted} inserted, {updated} updated")
    print(f"Total cases: {len(EVALUATION_CASES)}")


if __name__ == "__main__":
    seed_to_mongodb()
