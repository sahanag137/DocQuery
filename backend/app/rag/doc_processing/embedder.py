import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.model = SentenceTransformer(model_name)

    def embed_documents(
        self,
        texts: list[str]
    ) -> np.ndarray:

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embeddings.astype("float32")

    def embed_query(
        self,
        query: str
    ) -> np.ndarray:

        embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embedding.astype("float32")
