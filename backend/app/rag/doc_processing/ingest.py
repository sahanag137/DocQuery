"""
ingest.py

Pipeline module to ingest, chunk, embed, and index documents into FAISS vector store.
"""

from pathlib import Path
from typing import Optional

from .extractor import extract_pages
from .chunker import chunk_pages
from .embedder import Embedder
from .vector_store import VectorStore


def extract_document(file_path: str) -> list[dict]:
    """Extract text from PDF, TXT, or Markdown documents."""
    return extract_pages(file_path)


def ingest_document(
    file_path: str,
    document_id: str,
    user_id: int,
    storage_dir: str,
    original_filename: Optional[str] = None
) -> int:
    """
    Extract, chunk, embed, and index one document for a user.
    Removes existing chunks for this document first to prevent duplicates.
    """
    try:
        from app.core.config import settings
        chunk_size = getattr(settings, "CHUNK_SIZE", 1000)
        chunk_overlap = getattr(settings, "CHUNK_OVERLAP", 150)
        embedding_model = getattr(settings, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    except Exception:
        chunk_size = 1000
        chunk_overlap = 150
        embedding_model = "all-MiniLM-L6-v2"

    pages = extract_pages(file_path)

    if not pages:
        raise ValueError("No readable text found in document")

    chunks = chunk_pages(pages, chunk_size=chunk_size, overlap=chunk_overlap)

    if not chunks:
        raise ValueError("No chunks created from document")

    file_name = original_filename or Path(file_path).name

    for chunk in chunks:
        chunk["source"] = file_name
        chunk["document_id"] = str(document_id)
        chunk["user_id"] = int(user_id)

    embedder = Embedder(model_name=embedding_model)
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.embed_documents(texts)

    store = VectorStore(storage_dir)
    # Remove existing chunks for this document if any to prevent duplicate indexing
    store.remove_document(str(document_id))
    store.add(embeddings, chunks)
    store.save()

    return len(chunks)


def ingest_pdf(
    file_path: str,
    storage_dir: str = "data/vector_store",
    document_id: Optional[str] = None
) -> int:
    """Legacy PDF ingestion helper."""
    pages = extract_pages(file_path)

    if not pages:
        raise ValueError("No text found in PDF")

    chunks = chunk_pages(pages)

    if not chunks:
        raise ValueError("No chunks created from PDF")

    file_name = Path(file_path).name
    doc_id = str(document_id or Path(file_path).stem)

    for chunk in chunks:
        chunk["source"] = file_name
        chunk["document_id"] = doc_id

    embedder = Embedder()
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.embed_documents(texts)

    store = VectorStore(storage_dir)
    store.remove_document(doc_id)
    store.add(embeddings, chunks)
    store.save()

    return len(chunks)
