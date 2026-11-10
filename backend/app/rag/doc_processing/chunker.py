"""
chunker.py

Context-aware chunking module for DocQuery.
Splits document pages into chunks along natural boundaries (paragraphs,
sentences, headings) with configurable size and overlap to preserve full context.
"""

import re
from typing import Dict, List, Optional


def _find_split_point(text: str, start: int, max_end: int) -> int:
    """
    Find the most natural boundary to split text before max_end.
    Prefers:
    1. Paragraph break (double newline)
    2. Single newline
    3. Sentence boundary (. ! ? followed by space or newline)
    4. Semicolon or colon
    5. Space / word break
    Falls back to max_end if no boundary is found.
    """
    segment = text[start:max_end]
    min_reasonable_len = int((max_end - start) * 0.5)

    # 1. Paragraph boundary
    para_idx = segment.rfind("\n\n")
    if para_idx >= min_reasonable_len:
        return start + para_idx + 2

    # 2. Line boundary
    newline_idx = segment.rfind("\n")
    if newline_idx >= min_reasonable_len:
        return start + newline_idx + 1

    # 3. Sentence boundary (. ! ?)
    sentence_matches = list(re.finditer(r"[\.\!\?]\s+", segment))
    if sentence_matches:
        last_match = sentence_matches[-1]
        if last_match.end() >= min_reasonable_len:
            return start + last_match.end()

    # 4. Clause boundary (; :)
    clause_matches = list(re.finditer(r"[\;\:]\s+", segment))
    if clause_matches:
        last_match = clause_matches[-1]
        if last_match.end() >= min_reasonable_len:
            return start + last_match.end()

    # 5. Word boundary (space)
    space_idx = segment.rfind(" ")
    if space_idx >= min_reasonable_len:
        return start + space_idx + 1

    return max_end


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150
) -> List[str]:
    """Split a single block of text into overlapping chunks."""
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)
    effective_overlap = min(overlap, max(0, chunk_size // 2))

    while start < text_len:
        max_end = min(start + chunk_size, text_len)

        if max_end < text_len:
            split_at = _find_split_point(text, start, max_end)
            chunk = text[start:split_at].strip()
            if chunk:
                chunks.append(chunk)

            # Advance start by (split_at - effective_overlap), ensuring forward progress
            next_start = max(split_at - effective_overlap, start + 1)
            start = next_start
        else:
            chunk = text[start:max_end].strip()
            if chunk:
                chunks.append(chunk)
            break

    return chunks


def chunk_pages(
    pages: List[Dict],
    chunk_size: int = 1000,
    overlap: int = 150
) -> List[Dict]:
    """
    Chunk extracted pages while preserving page numbers and adding metadata.

    Input:
        pages: list of {"page": int, "text": str}
        chunk_size: target chunk size in characters
        overlap: character overlap between consecutive chunks

    Output:
        list of chunk dictionaries:
        {
            "text": str,
            "page": int,
            "chunk_id": int,
            "chunk_index": int,
            "char_count": int,
            "word_count": int
        }
    """
    chunks = []
    global_index = 0

    for page_data in pages:
        page_number = int(page_data.get("page", 1))
        page_text = page_data.get("text", "").strip()

        if not page_text:
            continue

        page_chunks = chunk_text(
            page_text,
            chunk_size=chunk_size,
            overlap=overlap
        )

        for chunk_content in page_chunks:
            chunks.append({
                "text": chunk_content,
                "page": page_number,
                "chunk_id": global_index,
                "chunk_index": global_index,
                "char_count": len(chunk_content),
                "word_count": len(chunk_content.split())
            })
            global_index += 1

    return chunks
