"""
retriever.py

Advanced semantic and hybrid retrieval module for DocQuery.
Supports query intent detection (summary, topics, page-specific, comparison, factual),
multi-query expansion, page filtering, and document-wide representative sampling.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from ..doc_processing.embedder import Embedder
from ..doc_processing.vector_store import VectorStore


class QueryIntent:
    SUMMARY = "summary"
    TOPICS = "topics"
    PAGE_SPECIFIC = "page_specific"
    COMPARISON = "comparison"
    FACTUAL = "factual"
    GENERAL = "general"


def detect_intent(query: str) -> Tuple[str, Dict]:
    """
    Detect the user's information need and extract metadata
    (e.g., target page number, comparison entities).
    """
    q_lower = query.lower().strip()
    meta = {}

    # 1. Page-specific check: e.g. "page 4", "on page 12", "page number 3"
    page_match = re.search(r"\bpage\s*(?:no\.?|number)?\s*(\d+)\b", q_lower)
    if page_match:
        meta["target_page"] = int(page_match.group(1))
        return QueryIntent.PAGE_SPECIFIC, meta

    # 2. Document summary check
    summary_triggers = [
        "summarize", "summary", "overview", "what is this document about",
        "explain the document", "explain this document", "brief me on",
        "tl;dr", "tldr", "synopsis", "in simple language"
    ]
    if any(trigger in q_lower for trigger in summary_triggers):
        return QueryIntent.SUMMARY, meta

    # 3. Main topics / Structure check
    topics_triggers = [
        "main topics", "key topics", "important concepts", "key concepts",
        "what are the topics", "chapters", "sections", "table of contents",
        "key points", "outline", "what does this cover", "list of topics"
    ]
    if any(trigger in q_lower for trigger in topics_triggers):
        return QueryIntent.TOPICS, meta

    # 4. Comparison check: "compare X and Y", "difference between X and Y"
    comp_match = re.search(r"(?:compare|difference between|versus|vs\.?)\s+(.+?)\s+(?:and|with|to|vs\.?)\s+(.+)", q_lower)
    if comp_match:
        meta["entity_a"] = comp_match.group(1).strip()
        meta["entity_b"] = comp_match.group(2).strip()
        return QueryIntent.COMPARISON, meta

    # 5. Definitions / Specific facts
    factual_triggers = [
        "what is", "define", "definition of", "how does", "why does",
        "when did", "who is", "formula", "meaning of"
    ]
    if any(q_lower.startswith(trigger) for trigger in factual_triggers):
        return QueryIntent.FACTUAL, meta

    return QueryIntent.GENERAL, meta


class Retriever:

    def __init__(self, storage_dir: str):
        try:
            from app.core.config import settings
            model_name = getattr(settings, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        except Exception:
            model_name = "all-MiniLM-L6-v2"
        self.embedder = Embedder(model_name=model_name)
        self.store = VectorStore(storage_dir)

        try:
            self.store.load()
        except FileNotFoundError:
            pass

    def _sample_document_wide(
        self,
        document_ids: Optional[Set[str]],
        max_chunks: int = 15
    ) -> List[Dict]:
        """
        Retrieve representative chunks evenly distributed across all pages
        of the selected document(s) for broad/summary questions.
        """
        all_chunks = self.store.get_all_chunks(document_ids)
        if not all_chunks:
            return []

        if len(all_chunks) <= max_chunks:
            for c in all_chunks:
                c.setdefault("score", 0.90)
            return all_chunks

        # Sample evenly across the entire length of the document
        step = len(all_chunks) / max_chunks
        sampled = []
        for i in range(max_chunks):
            idx = int(i * step)
            if idx < len(all_chunks):
                chunk = all_chunks[idx].copy()
                chunk["score"] = 0.90
                sampled.append(chunk)

        return sampled

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        document_ids: set[str] | None = None
    ) -> list[dict]:
        """
        Execute intent-aware retrieval across the target document(s).
        """
        clean_query = query.strip()
        if not clean_query or top_k < 1:
            return []

        if document_ids is not None and not document_ids:
            return []

        if self.store.index is None or self.store.index.ntotal == 0:
            return []

        intent, meta = detect_intent(clean_query)

        # STRATEGY 1: Page-specific query
        if intent == QueryIntent.PAGE_SPECIFIC:
            target_page = meta.get("target_page")
            all_chunks = self.store.get_all_chunks(document_ids)
            page_chunks = [c for c in all_chunks if int(c.get("page", 0)) == target_page]

            if page_chunks:
                for c in page_chunks:
                    c["score"] = 0.95

                # Also retrieve a few semantic matches for broader context
                q_emb = self.embedder.embed_query(clean_query)
                semantic = self.store.search(
                    q_emb,
                    top_k=max(3, top_k // 2),
                    document_ids=document_ids,
                    query_text=clean_query
                )
                seen_ids = {c.get("chunk_id") for c in page_chunks}
                for s in semantic:
                    if s.get("chunk_id") not in seen_ids:
                        page_chunks.append(s)

                return page_chunks[:max(top_k, 10)]

        # STRATEGY 2: Summary or Document Topics
        if intent in (QueryIntent.SUMMARY, QueryIntent.TOPICS):
            # Sample broadly across the document, plus include top semantic matches
            sampled = self._sample_document_wide(document_ids, max_chunks=max(top_k, 12))
            q_emb = self.embedder.embed_query(clean_query)
            semantic = self.store.search(
                q_emb,
                top_k=5,
                document_ids=document_ids,
                query_text=clean_query
            )

            seen_ids = {c.get("chunk_id") for c in sampled}
            merged = list(sampled)
            for s in semantic:
                if s.get("chunk_id") not in seen_ids:
                    merged.append(s)

            return merged

        # STRATEGY 3: Comparison query (sub-query expansion)
        if intent == QueryIntent.COMPARISON and "entity_a" in meta and "entity_b" in meta:
            entity_a = meta["entity_a"]
            entity_b = meta["entity_b"]

            emb_a = self.embedder.embed_query(entity_a)
            emb_b = self.embedder.embed_query(entity_b)
            emb_full = self.embedder.embed_query(clean_query)

            half_k = max(3, top_k // 2)
            results_a = self.store.search(emb_a, top_k=half_k, document_ids=document_ids, query_text=entity_a)
            results_b = self.store.search(emb_b, top_k=half_k, document_ids=document_ids, query_text=entity_b)
            results_full = self.store.search(emb_full, top_k=half_k, document_ids=document_ids, query_text=clean_query)

            combined = []
            seen_ids = set()
            for r in results_a + results_b + results_full:
                cid = r.get("chunk_id")
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    combined.append(r)

            combined.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            return combined[:max(top_k, 10)]

        # STRATEGY 4: Standard / Factual / General query
        # Use hybrid retrieval (vector similarity + keyword boost)
        effective_k = max(top_k, 8)
        query_embedding = self.embedder.embed_query(clean_query)

        results = self.store.search(
            query_embedding,
            top_k=effective_k,
            document_ids=document_ids,
            query_text=clean_query
        )

        return results
