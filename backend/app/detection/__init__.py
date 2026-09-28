"""Detection package."""
from app.detection.duplicate_detector import (
    detect_exact_duplicates,
    detect_near_duplicates,
    detect_semantic_duplicates,
    run_full_duplicate_detection,
)
from app.detection.supersession_engine import (
    create_relationship,
    detect_relationships_from_text,
    get_document_lineage,
    resolve_current_status,
)

__all__ = [
    "detect_exact_duplicates",
    "detect_near_duplicates",
    "detect_semantic_duplicates",
    "run_full_duplicate_detection",
    "create_relationship",
    "detect_relationships_from_text",
    "get_document_lineage",
    "resolve_current_status",
]
