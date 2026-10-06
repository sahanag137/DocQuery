from .retrieval.retriever import Retriever
from .retrieval.abstention import (
    should_abstain,
    get_abstention_message
)
from .generation.context_builder import build_context
from .generation.prompt import build_prompt
from .generation.generator import OpenRouterGenerator


class RAGPipeline:

    def __init__(
        self,
        storage_dir: str = "data/vector_store",
        model: str = "openai/gpt-4o-mini"
    ):

        self.retriever = Retriever(
            storage_dir
        )

        self.generator = OpenRouterGenerator(
            model
        )

    async def ask(
        self,
        question: str,
        top_k: int = 5
    ) -> dict:

        results = self.retriever.retrieve(
            question,
            top_k
        )

        if should_abstain(results):

            return {
                "answer": get_abstention_message(),
                "sources": [],
                "retrieved_chunks": 0
            }

        context = build_context(
            results
        )

        prompt = build_prompt(
            question,
            context
        )

        answer = await self.generator.generate(
            prompt
        )

        sources = [
            {
                "source": result.get("source"),
                "page": result.get("page"),
                "chunk_id": result.get("chunk_id"),
                "score": result.get("score")
            }
            for result in results
        ]

        return {
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": len(results)
        }
