"""
embedder.py

Modular sentence-transformers embedding generator with singleton model caching.
"""

from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_CACHE = {}


class Embedder:

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.model_name = model_name
        if model_name not in _MODEL_CACHE:
            _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
        self.model = _MODEL_CACHE[model_name]
        self._dimension = None

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Determine dimension from model output
            sample = self.model.encode(["test"], convert_to_numpy=True)
            self._dimension = int(sample.shape[1])
        return self._dimension

    def embed_documents(
        self,
        texts: List[str]
    ) -> np.ndarray:
        """
        Generate normalized float32 embeddings for a list of texts.
        Returns shape (len(texts), dimension).
        """
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")

        sanitized = [t if (t and t.strip()) else " " for t in texts]

        embeddings = self.model.encode(
            sanitized,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        arr = np.asarray(embeddings, dtype="float32")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr

    def embed_query(
        self,
        query: str
    ) -> np.ndarray:
        """
        Generate normalized float32 embedding for a single query.
        Returns shape (1, dimension).
        """
        clean = query.strip() if query else ""
        if not clean:
            clean = " "

        embedding = self.model.encode(
            [clean],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        arr = np.asarray(embedding, dtype="float32")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr
