from datetime import datetime

from pydantic import BaseModel, Field


class RagSpaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""

    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"

    vector_store: str = "faiss"

    chunk_size: int = Field(default=1000, ge=100, le=10000)
    chunk_overlap: int = Field(default=150, ge=0, le=500)


class RagSpaceResponse(BaseModel):
    id: str
    name: str
    description: str

    embedding_provider: str
    embedding_model: str

    vector_store: str

    chunk_size: int
    chunk_overlap: int

    document_count: int
    chunk_count: int

    status: str

    created_at: datetime
    updated_at: datetime