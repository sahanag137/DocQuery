
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)


class QuerySource(BaseModel):
    source: str | None = None
    page: int | None = None
    chunk_id: int | None = None
    score: float | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[QuerySource] = Field(default_factory=list)
    retrieved_chunks: int = 0
