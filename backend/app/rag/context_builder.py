"""
context_builder.py — turn raw retrieval hits into a clean, citation-tagged context string.
"""
from source import Chunk


def dedupe(hits: list[tuple[Chunk, float]], similarity_threshold: float = 0.95) -> list[tuple[Chunk, float]]:
    """Drop near-duplicate chunks (e.g. overlapping windows from the same source)."""
    seen_text = []
    deduped = []
    for chunk, score in hits:
        is_dupe = any(
            _text_overlap(chunk.text, t) > similarity_threshold for t in seen_text
        )
        if not is_dupe:
            seen_text.append(chunk.text)
            deduped.append((chunk, score))
    return deduped


def _text_overlap(a: str, b: str) -> float:
    """Cheap word-overlap ratio, used only for dedup (not real similarity)."""
    set_a, set_b = set(a.split()), set(b.split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def build_context(hits: list[tuple[Chunk, float]], max_chunks: int = 5) -> str:
    """Format top hits into a numbered, citable context block for the prompt."""
    hits = dedupe(hits)[:max_chunks]
    blocks = []
    for i, (chunk, score) in enumerate(hits, start=1):
        blocks.append(f"[{i}] (source: {chunk.source}, score: {score:.2f})\n{chunk.text}")
    return "\n\n".join(blocks)


def top_score(hits: list[tuple[Chunk, float]]) -> float:
    """Highest retrieval score in the hit list, or 0.0 if empty — used by abstention."""
    return max((s for _, s in hits), default=0.0)
