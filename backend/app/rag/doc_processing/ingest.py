from pathlib import Path

from .extractor import extract_pages
from .chunker import chunk_pages
from .embedder import Embedder
from .vector_store import VectorStore


def ingest_pdf(
    file_path: str,
    storage_dir: str = "data/vector_store"
) -> int:

    pages = extract_pages(file_path)

    if not pages:
        raise ValueError(
            "No text found in PDF"
        )

    chunks = chunk_pages(pages)

    if not chunks:
        raise ValueError(
            "No chunks created from PDF"
        )

    file_name = Path(file_path).name

    for chunk in chunks:
        chunk["source"] = file_name

    embedder = Embedder()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedder.embed_documents(
        texts
    )

    store = VectorStore(storage_dir)

    store.create(
        embeddings,
        chunks
    )

    store.save()

    return len(chunks)
