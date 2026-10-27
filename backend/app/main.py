"""
main.py

Entry point for the DocQuery API.

DoscQuery is a RAG-Based Documentation Question Answering System.
This file only sets up the core FastAPI application and a couple of
basic endpoints (root and health check). Other features such as
document upload, embeddings, FAISS search, RAG retrieval, LLM
generation, database access, and authentication will be added later
in separate modules to keep this file clean and easy to maintain.

Run locally with:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager

from rag.source import build_corpus
from rag.retriever import Retriever
from rag.context_builder import build_context, top_score
from rag.prompt import build_prompt
from rag.abstention import should_abstain, ABSTENTION_MESSAGE
from rag.generator import generate
from typing import Dict


from fastapi import FastAPI
from app.api.documents import router as documents_router

app = FastAPI(
    title="DocQuery API",
    description="RAG-Based Documentation Question Answering System",
    version="1.0.0"
)

app.include_router(documents_router)


@app.get("/")
def read_root() -> Dict[str, str]:
    """
    Root endpoint.

    A simple endpoint to confirm that the API is up and reachable.

    Returns:
        A JSON object with a short status message.
    """
    return {"message": "DocQuery API is running"}


@app.get("/health")
def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Used by monitoring tools, load balancers, or deployment platforms
    to verify that the service is alive and responding.

    Returns:
        A JSON object indicating the service is healthy.
    """
    return {"status": "healthy"}
