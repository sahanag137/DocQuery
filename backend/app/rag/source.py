"""
source.py — load raw documents and split them into retrievable chunks.
"""
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    page: int = 0


def load_text_files(folder: str) -> list[dict]:
    """Load all .txt/.md files from a folder as {source, text} dicts."""
    docs = []
    for path in Path(folder).glob("**/*"):
        if path.suffix.lower() in (".txt", ".md"):
            docs.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
    return docs


def chunk_text(text: str, source: str, chunk_size: int = 500, overlap: int = 80) -> list[Chunk]:
    """Simple sliding-window chunker, splitting on sentence boundaries where possible."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, current, current_len = [], [], 0

    for sent in sentences:
        current.append(sent)
        current_len += len(sent)
        if current_len >= chunk_size:
            chunk_str = " ".join(current)
            chunks.append(chunk_str)
            # keep the tail for overlap
            overlap_text = chunk_str[-overlap:]
            current, current_len = [overlap_text], len(overlap_text)

    if current:
        chunks.append(" ".join(current))

    return [
        Chunk(id=f"{source}::{i}", text=c, source=source)
        for i, c in enumerate(chunks) if c.strip()
    ]


def build_corpus(folder: str, chunk_size: int = 500, overlap: int = 80) -> list[Chunk]:
    """Load every doc in folder and return a flat list of Chunks."""
    all_chunks = []
    for doc in load_text_files(folder):
        all_chunks.extend(chunk_text(doc["text"], doc["source"], chunk_size, overlap))
    return all_chunks
