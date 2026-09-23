"""
retriever.py — embed chunks and retrieve the top-k most relevant ones for a query.
"""
import numpy as np
from source import Chunk


class Retriever:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        import faiss

        self._faiss = faiss
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks: list[Chunk] = []

    def build_index(self, chunks: list[Chunk]) -> None:
        """Embed all chunks and load them into a FAISS index."""
        self.chunks = chunks
        embeddings = self.model.encode(
            [c.text for c in chunks], normalize_embeddings=True, show_progress_bar=False
        )
        dim = embeddings.shape[1]
        self.index = self._faiss.IndexFlatIP(dim)  # cosine sim via normalized inner product
        self.index.add(np.array(embeddings, dtype="float32"))

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        """Return the top_k (chunk, score) pairs for a query, highest score first."""
        if self.index is None:
            raise RuntimeError("Call build_index() before search().")

        q_emb = self.model.encode([query], normalize_embeddings=True)
        scores, idxs = self.index.search(np.array(q_emb, dtype="float32"), top_k)

        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results
