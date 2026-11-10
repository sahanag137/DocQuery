from pathlib import Path
import pickle
import re
from typing import List, Optional, Set, Union

import faiss
import numpy as np


def _tokenize(text: str) -> Set[str]:
    """Extract lowercased alphanumeric words for lexical matching."""
    if not text:
        return set()
    return set(re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower()))


class VectorStore:

    def __init__(self, storage_dir: str = "data/vector_store"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.index = None
        self.documents = []

    def create(
        self,
        embeddings: np.ndarray,
        documents: list[dict]
    ):
        """Create a new FAISS index from embeddings and metadata."""
        embeddings = np.ascontiguousarray(embeddings, dtype="float32")

        if embeddings.ndim != 2 or embeddings.shape[0] == 0:
            raise ValueError("Embeddings must be a non-empty 2D array")

        if len(documents) != embeddings.shape[0]:
            raise ValueError("Embedding count and document count do not match")

        if not np.isfinite(embeddings).all():
            raise ValueError("Embeddings contain invalid values")

        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
        self.documents = [dict(doc) for doc in documents]

        self.save()

    def add(
        self,
        embeddings: np.ndarray,
        documents: list[dict]
    ):
        """Add new document chunks without overwriting existing chunks."""
        embeddings = np.ascontiguousarray(embeddings, dtype="float32")

        if embeddings.ndim != 2 or embeddings.shape[0] == 0:
            raise ValueError("Embeddings must be a non-empty 2D array")

        if len(documents) != embeddings.shape[0]:
            raise ValueError("Embedding count and document count do not match")

        if not np.isfinite(embeddings).all():
            raise ValueError("Embeddings contain invalid values")

        if self.index is None:
            self._load_if_exists()

        if self.index is None:
            self.create(embeddings, documents)
            return

        if embeddings.shape[1] != self.index.d:
            raise ValueError("Embedding dimensions do not match the existing index")

        self.index.add(embeddings)
        self.documents.extend(dict(doc) for doc in documents)

        self.save()

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        document_ids: set[str] | list[str] | None = None,
        query_text: Optional[str] = None
    ) -> list[dict]:
        """
        Search the index, filter by document IDs, and optionally apply
        hybrid keyword boosting to guarantee exact terms/numbers are retrieved.
        """
        if self.index is None:
            self._load_if_exists()

        if self.index is None or self.index.ntotal == 0:
            return []

        if top_k < 1:
            return []

        query_embedding = np.ascontiguousarray(query_embedding, dtype="float32")

        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        if query_embedding.ndim != 2 or query_embedding.shape[0] != 1:
            raise ValueError("Query embedding must contain exactly one vector")

        if query_embedding.shape[1] != self.index.d:
            raise ValueError("Query embedding dimension does not match the index")

        if not np.isfinite(query_embedding).all():
            raise ValueError("Query embedding contains invalid values")

        filter_ids = None
        if document_ids is not None:
            filter_ids = {str(doc_id) for doc_id in document_ids}
            if not filter_ids:
                return []

        # Retrieve scores across all indexed items
        search_count = self.index.ntotal
        scores, indices = self.index.search(query_embedding, search_count)

        query_tokens = _tokenize(query_text) if query_text else set()

        candidates = []
        for score, index in zip(scores[0], indices[0]):
            if index == -1 or index >= len(self.documents):
                continue

            doc_meta = self.documents[index].copy()

            if filter_ids is not None:
                doc_id_val = str(doc_meta.get("document_id", ""))
                if doc_id_val not in filter_ids:
                    continue

            vec_score = float(score)

            # Optional hybrid scoring with lexical token overlap
            if query_tokens:
                doc_text = doc_meta.get("text", "")
                doc_tokens = _tokenize(doc_text)
                if doc_tokens:
                    overlap = len(query_tokens & doc_tokens) / max(len(query_tokens), 1)
                    # Blend vector score (70%) and keyword overlap (30%)
                    combined_score = 0.70 * vec_score + 0.30 * overlap
                else:
                    combined_score = vec_score
            else:
                combined_score = vec_score

            doc_meta["score"] = combined_score
            doc_meta["raw_score"] = vec_score
            candidates.append(doc_meta)

        # Sort by combined score descending
        candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        return candidates[:top_k]

    def get_document_chunks(
        self,
        document_id: str
    ) -> list[dict]:
        """Get all chunks belonging to a specific document in reading order."""
        if self.index is None:
            self._load_if_exists()

        if self.index is None:
            return []

        doc_id_str = str(document_id)

        chunks = [
            document.copy()
            for document in self.documents
            if str(document.get("document_id")) == doc_id_str
        ]

        # Sort by page then chunk_id or chunk_index
        chunks.sort(
            key=lambda c: (
                int(c.get("page", 1) or 1),
                int(c.get("chunk_index", c.get("chunk_id", 0)) or 0)
            )
        )
        return chunks

    def get_all_chunks(
        self,
        document_ids: set[str] | list[str] | None = None
    ) -> list[dict]:
        """Get all chunks, optionally filtered by document IDs, in reading order."""
        if self.index is None:
            self._load_if_exists()

        if self.index is None:
            return []

        filter_ids = {str(d) for d in document_ids} if document_ids is not None else None

        chunks = []
        for doc in self.documents:
            if filter_ids is not None:
                doc_id_str = str(doc.get("document_id", ""))
                if doc_id_str not in filter_ids:
                    continue
            chunks.append(doc.copy())

        chunks.sort(
            key=lambda c: (
                str(c.get("document_id", "")),
                int(c.get("page", 1) or 1),
                int(c.get("chunk_index", c.get("chunk_id", 0)) or 0)
            )
        )
        return chunks

    def remove_document(self, document_id: str):
        """Remove all chunks belonging to a document."""
        if self.index is None:
            self._load_if_exists()

        if self.index is None:
            return

        document_id = str(document_id)

        keep_indices = [
            i for i, document in enumerate(self.documents)
            if str(document.get("document_id")) != document_id
        ]

        if len(keep_indices) == len(self.documents):
            return

        if not keep_indices:
            dimension = self.index.d
            self.index = faiss.IndexFlatIP(dimension)
            self.documents = []
            self.save()
            return

        all_embeddings = self.index.reconstruct_n(0, self.index.ntotal)
        remaining_embeddings = np.ascontiguousarray(
            all_embeddings[keep_indices], dtype="float32"
        )
        remaining_documents = [self.documents[i] for i in keep_indices]

        self.index = faiss.IndexFlatIP(remaining_embeddings.shape[1])
        self.index.add(remaining_embeddings)
        self.documents = remaining_documents

        self.save()

    def save(self):
        """Persist the FAISS index and matching metadata."""
        if self.index is None:
            raise RuntimeError("Nothing to save")

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(self.storage_dir / "index.faiss"))

        with open(self.storage_dir / "documents.pkl", "wb") as file:
            pickle.dump(self.documents, file)

    def _load_if_exists(self):
        """Load an existing index if both storage files are available."""
        index_path = self.storage_dir / "index.faiss"
        documents_path = self.storage_dir / "documents.pkl"

        if not index_path.exists() and not documents_path.exists():
            return

        if not index_path.exists() or not documents_path.exists():
            raise RuntimeError("Vector store files are incomplete")

        self.load()

    def load(self):
        """Load the saved FAISS index and metadata."""
        index_path = self.storage_dir / "index.faiss"
        documents_path = self.storage_dir / "documents.pkl"

        if not index_path.exists() or not documents_path.exists():
            raise FileNotFoundError("FAISS index or metadata file not found")

        index = faiss.read_index(str(index_path))

        with open(documents_path, "rb") as file:
            documents = pickle.load(file)

        if index.ntotal != len(documents):
            raise RuntimeError("FAISS index and document metadata are inconsistent")

        self.index = index
        self.documents = documents
