from pathlib import Path
import pickle

import faiss
import numpy as np


class VectorStore:

    def __init__(self, storage_dir: str = "data/vector_store"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.index = None
        self.documents = []

    def create(
        self,
        embeddings: np.ndarray,
        documents: list[dict]
    ):

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(dimension)

        self.index.add(embeddings)

        self.documents = documents

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> list[dict]:

        if self.index is None:
            raise RuntimeError("Vector store is not loaded")

        top_k = min(
            top_k,
            self.index.ntotal
        )

        scores, indices = self.index.search(
            query_embedding,
            top_k
        )

        results = []

        for score, index in zip(
            scores[0],
            indices[0]
        ):

            if index == -1:
                continue

            document = self.documents[index].copy()

            document["score"] = float(score)

            results.append(document)

        return results

    def save(self):

        if self.index is None:
            raise RuntimeError("Nothing to save")

        faiss.write_index(
            self.index,
            str(self.storage_dir / "index.faiss")
        )

        with open(
            self.storage_dir / "documents.pkl",
            "wb"
        ) as f:
            pickle.dump(
                self.documents,
                f
            )

    def load(self):

        index_path = self.storage_dir / "index.faiss"
        documents_path = self.storage_dir / "documents.pkl"

        if not index_path.exists():
            raise FileNotFoundError(
                "FAISS index not found"
            )

        self.index = faiss.read_index(
            str(index_path)
        )

        with open(
            documents_path,
            "rb"
        ) as f:
            self.documents = pickle.load(f)
