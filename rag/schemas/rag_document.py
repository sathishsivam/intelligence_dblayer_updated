from datetime import datetime

from pydantic import BaseModel


class RagDocumentResponse(BaseModel):
    id: str
    space_id: str

    file_name: str
    file_type: str
    file_size: int

    page_count: int
    chunk_count: int

    status: str

    created_at: datetime
    updated_at: datetime