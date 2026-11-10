"""
test_document_processing_pipeline.py

Comprehensive tests for the DocQuery Document Processing Pipeline & RAG:
1. PDF, TXT, and Markdown text extraction with page preservation
2. Text cleaning and formatting normalization
3. Natural boundary chunking and overlap context preservation
4. Vector store indexing, hybrid scoring, and chunk retrieval
5. Query intent classification (summary, topics, page-specific, comparison, factual)
6. Abstention logic and relevance verification
7. Context builder with deduplication and chat history formatting
8. Dedicated document summarization (single-pass and hierarchical map-reduce)
9. End-to-end API testing of /query/{conversation_id} and /query/{conversation_id}/summarize/{document_id}
"""

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.rag.doc_processing.cleaner import clean_text
from app.rag.doc_processing.chunker import chunk_pages, chunk_text
from app.rag.doc_processing.extractor import extract_pages
from app.rag.doc_processing.vector_store import VectorStore
from app.rag.doc_processing.embedder import Embedder
from app.rag.retrieval.abstention import get_abstention_message, should_abstain
from app.rag.retrieval.retriever import QueryIntent, Retriever, detect_intent
from app.rag.generation.context_builder import build_context, format_chat_history
from app.rag.generation.prompt import build_prompt
from app.rag.pipeline import RAGPipeline


# ---------------------------------------------------------------------------
# 1. Text Extraction Tests
# ---------------------------------------------------------------------------
def test_extract_text_and_markdown(tmp_path: Path):
    """Verify TXT and Markdown files are correctly extracted."""
    # 1. TXT extraction
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Line 1: Introduction to Machine Learning.\nLine 2: Supervised learning.", encoding="utf-8")
    txt_pages = extract_pages(txt_file)
    assert len(txt_pages) == 1
    assert txt_pages[0]["page"] == 1
    assert "Supervised learning" in txt_pages[0]["text"]

    # 2. Markdown extraction
    md_file = tmp_path / "sample.md"
    md_file.write_text("# Chapter 1\n\nDeep Neural Networks.\n\n## Subtopic\nBackpropagation.", encoding="utf-8")
    md_pages = extract_pages(md_file)
    assert len(md_pages) == 1
    assert md_pages[0]["page"] == 1
    assert "# Chapter 1" in md_pages[0]["text"]


def test_extract_pdf_pages(tmp_path: Path):
    """Verify PDF extraction preserves page numbers across multiple pages."""
    from fpdf import FPDF

    pdf = FPDF()
    # Page 1
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Page 1: DocQuery Architecture and RAG Fundamentals.")
    # Page 2
    pdf.add_page()
    pdf.cell(text="Page 2: Vector Search with FAISS and Sentence Transformers.")
    
    pdf_path = tmp_path / "multipage.pdf"
    pdf.output(str(pdf_path))

    pages = extract_pages(pdf_path)
    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert "DocQuery Architecture" in pages[0]["text"]
    assert pages[1]["page"] == 2
    assert "Vector Search" in pages[1]["text"]


def test_extract_nonexistent_or_unsupported(tmp_path: Path):
    """Verify errors for missing and unsupported files."""
    with pytest.raises(FileNotFoundError):
        extract_pages(tmp_path / "does_not_exist.pdf")

    bad_file = tmp_path / "invalid.xyz"
    bad_file.write_text("Hello", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported document format"):
        extract_pages(bad_file)


# ---------------------------------------------------------------------------
# 2. Text Cleaning Tests
# ---------------------------------------------------------------------------
def test_clean_text():
    """Verify text cleaning normalizes line breaks while preserving headings and punctuation."""
    raw = "\r\n# Architecture Overview\r\n\r\n\r\n\r\n\r\nLine with   extra   spaces.  \r\n\x00Code: f(x) = x^2 + 10;\r\n"
    cleaned = clean_text(raw)

    assert "\r" not in cleaned
    assert "\x00" not in cleaned
    assert "\n\n\n" not in cleaned
    assert "# Architecture Overview" in cleaned
    assert "Code: f(x) = x^2 + 10;" in cleaned
    assert "Line with extra spaces." in cleaned


# ---------------------------------------------------------------------------
# 3. Chunking & Overlap Tests
# ---------------------------------------------------------------------------
def test_chunk_text_and_overlap():
    """Verify natural boundary splitting and overlap context preservation."""
    text = (
        "Paragraph 1: Artificial intelligence has transformed computing. "
        "It enables systems to learn from data.\n\n"
        "Paragraph 2: Natural Language Processing deals with understanding text. "
        "Large language models have revolutionized this domain.\n\n"
        "Paragraph 3: Information retrieval systems find relevant documents. "
        "Combining them yields Retrieval-Augmented Generation."
    )

    chunks = chunk_text(text, chunk_size=150, overlap=30)
    assert len(chunks) >= 2
    # Verify no chunk exceeds chunk_size
    for c in chunks:
        assert len(c) <= 180

    # Short document test
    short_chunks = chunk_text("A very short document.", chunk_size=500, overlap=50)
    assert len(short_chunks) == 1
    assert short_chunks[0] == "A very short document."


def test_chunk_pages_preserves_metadata():
    """Verify chunk_pages preserves page numbering and attaches metrics."""
    pages = [
        {"page": 1, "text": "Page one text content about system setup."},
        {"page": 2, "text": "Page two text content about query evaluation."}
    ]
    chunks = chunk_pages(pages, chunk_size=200, overlap=40)
    assert len(chunks) == 2
    assert chunks[0]["page"] == 1
    assert chunks[0]["chunk_id"] == 0
    assert chunks[1]["page"] == 2
    assert chunks[1]["chunk_id"] == 1
    assert chunks[0]["char_count"] > 0
    assert chunks[0]["word_count"] > 0


# ---------------------------------------------------------------------------
# 4. Vector Store & Hybrid Search Tests
# ---------------------------------------------------------------------------
def test_vector_store_indexing_and_hybrid_search(tmp_path: Path):
    """Verify VectorStore indexing, get_document_chunks, and hybrid search."""
    store = VectorStore(str(tmp_path / "vs_test"))
    
    # 3 dummy chunks with 4-dim embeddings
    embeddings = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0]
    ], dtype="float32")

    documents = [
        {"document_id": "doc_1", "page": 1, "chunk_id": 0, "text": "Supervised learning algorithm"},
        {"document_id": "doc_1", "page": 2, "chunk_id": 1, "text": "Unsupervised clustering algorithm"},
        {"document_id": "doc_2", "page": 1, "chunk_id": 2, "text": "Reinforcement learning policy"}
    ]

    store.create(embeddings, documents)

    # Test get_document_chunks
    doc1_chunks = store.get_document_chunks("doc_1")
    assert len(doc1_chunks) == 2
    assert doc1_chunks[0]["page"] == 1
    assert doc1_chunks[1]["page"] == 2

    # Test get_all_chunks with filtering
    doc2_chunks = store.get_all_chunks(document_ids={"doc_2"})
    assert len(doc2_chunks) == 1
    assert doc2_chunks[0]["document_id"] == "doc_2"

    # Test hybrid search with keyword boost
    query_vector = np.array([[0.1, 0.9, 0.0, 0.0]], dtype="float32")
    results = store.search(
        query_vector,
        top_k=2,
        document_ids={"doc_1"},
        query_text="clustering"
    )
    assert len(results) >= 1
    assert results[0]["document_id"] == "doc_1"
    assert "clustering" in results[0]["text"]


# ---------------------------------------------------------------------------
# 5. Intent Detection & Abstention Tests
# ---------------------------------------------------------------------------
def test_detect_intent():
    """Verify accurate query intent classification."""
    intent, meta = detect_intent("Summarize this document for me")
    assert intent == QueryIntent.SUMMARY

    intent, meta = detect_intent("What are the main topics covered?")
    assert intent == QueryIntent.TOPICS

    intent, meta = detect_intent("What is discussed on page 5?")
    assert intent == QueryIntent.PAGE_SPECIFIC
    assert meta.get("target_page") == 5

    intent, meta = detect_intent("Compare supervised learning and unsupervised learning")
    assert intent == QueryIntent.COMPARISON
    assert "supervised learning" in meta.get("entity_a", "")

    intent, meta = detect_intent("What is the definition of neural network?")
    assert intent == QueryIntent.FACTUAL


def test_abstention_logic():
    """Verify that abstention does not trigger on summaries or valid matches."""
    # Summary intent with chunks should never abstain
    assert not should_abstain([{"score": 0.10}], intent="summary")
    assert not should_abstain([{"score": 0.05}], intent="topics")
    assert not should_abstain([{"page": 3, "score": 0.12}], intent="page_specific")

    # High score should not abstain
    assert not should_abstain([{"score": 0.35}], intent="general")

    # Low score on general query should abstain
    assert should_abstain([{"score": 0.12}], intent="general", threshold=0.18)

    # Empty results should always abstain
    assert should_abstain([], intent="general")


# ---------------------------------------------------------------------------
# 6. Context Builder & Prompt Construction Tests
# ---------------------------------------------------------------------------
def test_context_builder_and_history():
    """Verify context formatting, deduplication, and chat history formatting."""
    results = [
        {"source": "report.pdf", "page": 1, "text": "Findings: 85% accuracy achieved."},
        {"source": "report.pdf", "page": 1, "text": "Findings: 85% accuracy achieved."},  # duplicate
        {"source": "report.pdf", "page": 3, "text": "Next steps: deployment."}
    ]

    context = build_context(results)
    assert "[Document: report.pdf | Page: 1]" in context
    assert "[Document: report.pdf | Page: 3]" in context
    # Duplicate was ignored
    assert context.count("85% accuracy achieved") == 1

    # History formatting
    history = [
        {"role": "user", "content": "What is the project name?"},
        {"role": "assistant", "content": "The project is DocQuery."}
    ]
    formatted_history = format_chat_history(history)
    assert "User: What is the project name?" in formatted_history
    assert "Assistant: The project is DocQuery." in formatted_history


def test_prompt_construction():
    """Verify prompt contains document context and question."""
    prompt = build_prompt(
        question="What was the accuracy?",
        context="[Document: test.pdf | Page: 1]\nAccuracy was 94%.",
        chat_history="User: Hello\nAssistant: Hi!"
    )
    assert "PREVIOUS CONVERSATION CONTEXT:" in prompt
    assert "Accuracy was 94%." in prompt
    assert "USER QUESTION:\nWhat was the accuracy?" in prompt


# ---------------------------------------------------------------------------
# 7. Document Summarization Tests (Single-pass and Hierarchical)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_summarize_document_single_pass(tmp_path: Path):
    """Verify single-pass summarization on a document."""
    store_dir = tmp_path / "sum_test"
    store = VectorStore(str(store_dir))

    # Add 4 chunks
    embeddings = np.ones((4, 4), dtype="float32")
    chunks = [
        {"document_id": "doc_100", "source": "guide.pdf", "page": 1, "chunk_id": 0, "text": "Introduction to DocQuery."},
        {"document_id": "doc_100", "source": "guide.pdf", "page": 2, "chunk_id": 1, "text": "Architecture and ingestion."},
        {"document_id": "doc_100", "source": "guide.pdf", "page": 3, "chunk_id": 2, "text": "Vector search and LLM synthesis."},
        {"document_id": "doc_100", "source": "guide.pdf", "page": 4, "chunk_id": 3, "text": "Conclusions and takeaways."}
    ]
    store.create(embeddings, chunks)

    pipeline = RAGPipeline(storage_dir=str(store_dir))
    
    mock_generator = AsyncMock()
    mock_generator.generate.return_value = "# Summary\nDocQuery is a high-performance RAG system."
    pipeline.generator = mock_generator

    result = await pipeline.summarize_document("doc_100")

    assert "DocQuery is a high-performance RAG system" in result["answer"]
    assert result["retrieved_chunks"] == 4
    assert len(result["sources"]) == 4
    mock_generator.generate.assert_called_once()


@pytest.mark.anyio
async def test_summarize_document_hierarchical_for_large_pdf(tmp_path: Path):
    """Verify hierarchical / map-reduce summarization triggers for documents > 12 chunks."""
    store_dir = tmp_path / "sum_large"
    store = VectorStore(str(store_dir))

    # Create 20 chunks (simulating a 20-page document)
    embeddings = np.ones((20, 4), dtype="float32")
    chunks = [
        {
            "document_id": "doc_large",
            "source": "textbook.pdf",
            "page": i + 1,
            "chunk_id": i,
            "text": f"Chapter {i + 1} content explaining complex algorithms and applications."
        }
        for i in range(20)
    ]
    store.create(embeddings, chunks)

    pipeline = RAGPipeline(storage_dir=str(store_dir))
    
    mock_generator = AsyncMock()
    # Mock calls for section batches + final synthesis
    mock_generator.generate.side_effect = [
        "Section 1 Summary: Covers Chapters 1 to 10.",
        "Section 2 Summary: Covers Chapters 11 to 20.",
        "# Executive Summary\nComplete textbook breakdown covering all 20 chapters."
    ]
    pipeline.generator = mock_generator

    result = await pipeline.summarize_document("doc_large")

    assert "Complete textbook breakdown" in result["answer"]
    assert result["retrieved_chunks"] == 20
    assert mock_generator.generate.call_count == 3  # 2 section batches + 1 final synthesis


# ---------------------------------------------------------------------------
# 8. End-to-End API Integration Tests (/query and /summarize)
# ---------------------------------------------------------------------------
def test_query_and_summarize_api_e2e(client: TestClient, user_one: dict, tmp_path: Path):
    """Verify /query/{conversation_id} and /query/{conversation_id}/summarize/{document_id} endpoints."""
    headers = user_one["headers"]

    # 1. Create a conversation
    chat_resp = client.post("/chats", headers=headers)
    assert chat_resp.status_code == 201
    conversation_id = chat_resp.json()["id"]

    # 2. Upload a text document
    txt_content = b"DocQuery System Documentation.\nPage 1: DocQuery supports multi-page PDF understanding.\nPage 2: It features hybrid retrieval and hierarchical summarization."
    files = {"file": ("manual.txt", io.BytesIO(txt_content), "text/plain")}
    up_resp = client.post("/documents/upload", files=files, headers=headers)
    assert up_resp.status_code == 201
    doc_id = up_resp.json()["document_id"]

    # 3. Associate document with conversation
    assoc_resp = client.post(
        f"/chats/{conversation_id}/documents",
        json={"document_id": doc_id},
        headers=headers
    )
    assert assoc_resp.status_code == 201

    # 4. Query the document with mocked OpenRouter generator
    with patch("app.rag.pipeline.OpenRouterGenerator.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "DocQuery supports multi-page PDF understanding and hybrid retrieval (Page 1)."

        # Test normal question answering
        query_payload = {"question": "What does DocQuery support?", "top_k": 5}
        q_resp = client.post(f"/query/{conversation_id}", json=query_payload, headers=headers)
        assert q_resp.status_code == 200
        q_data = q_resp.json()
        assert "multi-page PDF understanding" in q_data["answer"]
        assert len(q_data["sources"]) >= 1

        # Test dedicated summarization endpoint
        mock_gen.return_value = "# Document Summary\nDocQuery is a complete documentation QA platform."
        sum_resp = client.post(f"/query/{conversation_id}/summarize/{doc_id}", headers=headers)
        assert sum_resp.status_code == 200
        sum_data = sum_resp.json()
        assert "Document Summary" in sum_data["answer"]
        assert len(sum_data["sources"]) >= 1
