"""
pipeline.py

RAGPipeline orchestrator for DocQuery.
Manages:
- Intent-aware retrieval and question answering
- Multi-turn conversation awareness
- Dedicated hierarchical document summarization
- Reliable source attribution
"""

import logging
from typing import Dict, List, Optional, Set, Union

from .doc_processing.vector_store import VectorStore
from .generation.context_builder import build_context, format_chat_history
from .generation.generator import OpenRouterGenerator
from .generation.prompt import build_prompt
from .retrieval.abstention import get_abstention_message, should_abstain
from .retrieval.retriever import QueryIntent, Retriever, detect_intent

logger = logging.getLogger(__name__)


class RAGPipeline:

    def __init__(
        self,
        storage_dir: str,
        model: str = "openai/gpt-4o-mini"
    ):
        self.storage_dir = storage_dir
        self.retriever = Retriever(storage_dir)
        self.model = model
        self.generator = None

    def _get_generator(self) -> OpenRouterGenerator:
        if self.generator is None:
            self.generator = OpenRouterGenerator(self.model)
        return self.generator

    async def ask(
        self,
        question: str,
        top_k: int = 8,
        document_ids: Optional[Union[Set[str], List[str]]] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Answer a question about the selected document(s) with intent-awareness,
        broad content coverage, and page-level source attribution.
        """
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Question cannot be empty")

        if document_ids is not None and not document_ids:
            return {
                "answer": get_abstention_message(),
                "sources": [],
                "retrieved_chunks": 0
            }

        intent, meta = detect_intent(clean_question)

        # 1. Retrieve relevant document chunks using intent-aware strategy
        results = self.retriever.retrieve(
            query=clean_question,
            top_k=max(top_k, 8),
            document_ids=set(str(d) for d in document_ids) if document_ids else None
        )

        logger.info(
            "RAG Query: '%s' | Intent: %s | Retrieved: %d chunks",
            clean_question, intent, len(results)
        )

        # 2. Check relevance / abstention
        if should_abstain(results, intent=intent):
            logger.info("Abstaining on query '%s' due to low relevance", clean_question)
            return {
                "answer": get_abstention_message(),
                "sources": [],
                "retrieved_chunks": 0
            }

        # 3. Construct rich context (up to 24,000 characters)
        context = build_context(results, max_characters=24000)

        # 4. Format prior conversation history if provided
        history_str = format_chat_history(chat_history) if chat_history else None

        # 5. Build prompt
        prompt = build_prompt(
            question=clean_question,
            context=context,
            chat_history=history_str,
            intent=intent
        )

        # 6. Generate answer
        generator = self._get_generator()
        answer = await generator.generate(prompt)

        # 7. Collect sources with valid page and filename
        sources = []
        seen_source_keys = set()
        for r in results:
            src = r.get("source") or "Document"
            pg = r.get("page")
            cid = r.get("chunk_id")
            score = r.get("score")
            key = (src, pg, cid)
            if key not in seen_source_keys:
                seen_source_keys.add(key)
                sources.append({
                    "source": src,
                    "page": pg,
                    "chunk_id": cid,
                    "score": score
                })

        return {
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": len(results)
        }

    async def summarize_document(
        self,
        document_id: str
    ) -> Dict:
        """
        Produce a comprehensive, structured summary of the entire selected PDF.
        For large documents, applies a hierarchical / map-reduce summarization
        strategy to cover all chapters and sections without exceeding context limits.
        """
        store = VectorStore(self.storage_dir)
        chunks = store.get_document_chunks(str(document_id))

        if not chunks:
            raise ValueError(f"No indexed content found for document '{document_id}'.")

        generator = self._get_generator()
        doc_filename = chunks[0].get("source") or "Document"
        total_chunks = len(chunks)

        logger.info("Summarizing document '%s' with %d chunks", doc_filename, total_chunks)

        # APPROACH A: Single-pass summary for small/medium documents (up to 12 chunks, ~12k chars)
        if total_chunks <= 12:
            combined_text = "\n\n".join(
                f"[Page {c.get('page', 1)}]\n{c.get('text', '').strip()}"
                for c in chunks if c.get("text")
            )

            prompt = f"""You are an expert document summarization assistant.

Summarize the entire document '{doc_filename}' using ONLY the content provided below.

INSTRUCTIONS:
1. Executive Overview: Provide a concise summary of the document's main purpose.
2. Key Topics & Structure: Outline all primary sections, chapters, or phases.
3. Important Concepts & Definitions: Explain the key ideas, terminology, and principles.
4. Key Findings & Recommendations: Highlight the main conclusions, steps, numbers, or outcomes.
5. Cite page numbers where topics originate (e.g., "[Page 2]").
6. Present the summary cleanly with markdown headings and bullet points.

DOCUMENT CONTENT:
{combined_text}

SUMMARY:
"""
            summary = await generator.generate(prompt)

        # APPROACH B: Hierarchical / Map-Reduce for large documents (>12 chunks)
        else:
            batch_size = 10
            section_summaries = []

            for i in range(0, total_chunks, batch_size):
                batch = chunks[i:i + batch_size]
                pages_covered = sorted(list({c.get("page", 1) for c in batch}))
                page_label = f"Pages {pages_covered[0]}-{pages_covered[-1]}" if len(pages_covered) > 1 else f"Page {pages_covered[0]}"

                batch_text = "\n\n".join(
                    f"[Page {c.get('page', 1)}]\n{c.get('text', '').strip()}"
                    for c in batch if c.get("text")
                )

                batch_prompt = f"""Summarize this section ({page_label}) of '{doc_filename}'.
Extract all major facts, definitions, findings, steps, and topic points.
Include page citations.

SECTION CONTENT:
{batch_text}

SECTION SUMMARY:
"""
                batch_summary = await generator.generate(batch_prompt)
                section_summaries.append(f"### {page_label}\n{batch_summary}")

            # Combine section summaries into final cohesive executive summary
            combined_sections = "\n\n".join(section_summaries)

            final_prompt = f"""You are an expert document analyst. Below are section summaries covering the entire document '{doc_filename}'.

Synthesize them into one comprehensive, unified document summary.

STRUCTURE:
# Executive Overview
Brief description of the document's core subject and goals.

# Main Topics & Chapter Breakdown
Summary of each primary topic covered across the sections, preserving page references.

# Key Concepts & Definitions
Important terms, definitions, and technical details.

# Major Findings, Statistics & Recommendations
Key conclusions, numbers, dates, outcomes, and actionable points.

SECTION SUMMARIES TO SYNTHESIZE:
{combined_sections}

FINAL DOCUMENT SUMMARY:
"""
            summary = await generator.generate(final_prompt)

        # Format sources with unique pages
        sources = []
        seen_pages = set()
        for c in chunks:
            pg = c.get("page")
            if pg not in seen_pages:
                seen_pages.add(pg)
                sources.append({
                    "source": c.get("source") or doc_filename,
                    "page": pg,
                    "chunk_id": c.get("chunk_id"),
                    "score": None
                })

        return {
            "answer": summary,
            "sources": sources,
            "retrieved_chunks": total_chunks
        }
