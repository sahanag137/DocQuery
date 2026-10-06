from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class Source(BaseModel):
    source: Optional[str] = None
    page: Optional[int] = None
    chunk_id: Optional[int] = None
    score: Optional[float] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    retrieved_chunks: int
