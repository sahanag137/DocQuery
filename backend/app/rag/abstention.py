"""
abstention.py — decide whether retrieval quality is high enough to answer at all.
"""

MIN_SCORE = 0.35          # below this, top hit is too weak to trust
MIN_HITS = 1              # need at least this many retrieved chunks

ABSTENTION_MESSAGE = (
    "I don't have enough information in the provided documents to answer that confidently."
)


def should_abstain(hits: list, top_score: float) -> bool:
    """Return True if the pipeline should refuse to answer rather than guess."""
    if len(hits) < MIN_HITS:
        return True
    if top_score < MIN_SCORE:
        return True
    return False
  
