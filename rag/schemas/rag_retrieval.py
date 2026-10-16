from pydantic import BaseModel, Field


class RagRetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RagRetrievedDocument(BaseModel):
    content: str
    metadata: dict


class RagRetrievalResponse(BaseModel):
    query: str
    status: str
    documents: list[RagRetrievedDocument]
    sources: list[dict]
    context: str