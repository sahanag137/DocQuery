from ..doc_processing.embedder import Embedder
from ..doc_processing.vector_store import VectorStore


class Retriever:

    def __init__(
        self,
        storage_dir: str = "data/vector_store"
    ):

        self.embedder = Embedder()

        self.store = VectorStore(
            storage_dir
        )

        self.store.load()

    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> list[dict]:

        query_embedding = (
            self.embedder.embed_query(query)
        )

        return self.store.search(
            query_embedding,
            top_k
        )
