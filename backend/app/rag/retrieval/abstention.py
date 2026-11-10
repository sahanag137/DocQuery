"""
abstention.py

Relevance verification and honest fallback management.
Prevents false-positive abstention on broad/summary questions while ensuring
the system honestly abstains when a query is completely out-of-domain.
"""

import math
from typing import Dict, List, Optional


def should_abstain(
    results: List[Dict],
    threshold: float = 0.18,
    intent: Optional[str] = None
) -> bool:
    """
    Determine if the retrieved document content is insufficient to answer the query.

    Args:
        results: Retrieved chunk dictionaries with "score".
        threshold: Minimum relevance threshold (default: 0.18).
        intent: Detected query intent (summary, topics, page_specific, etc.).
    """
    if not results:
        return True

    # For document summaries, structure, or page-specific requests,
    # as long as chunks exist from the document, we do not abstain.
    if intent in ("summary", "topics", "page_specific"):
        return False

    best_score = results[0].get("score")

    if best_score is None:
        return True

    try:
        best_score = float(best_score)
    except (ValueError, TypeError):
        return True

    if not math.isfinite(best_score):
        return True

    # If the highest scoring chunk fails to meet the calibrated relevance threshold
    return best_score < threshold


def get_abstention_message() -> str:
    """Standardized fallback message when document has insufficient information."""
    return (
        "I couldn't find enough relevant information "
        "in the provided documents to answer this question."
    )
