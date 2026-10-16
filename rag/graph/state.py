from typing import TypedDict


class IngestionState(TypedDict, total=False):

    # -----------------------------------------
    # Input
    # -----------------------------------------

    space_id: str
    document_id: str
    file_path: str
    file_name: str
    # -----------------------------------------
    # Document
    # -----------------------------------------

    document: dict

    # -----------------------------------------
    # Chunks
    # -----------------------------------------

    chunks: list[dict]

    # -----------------------------------------
    # Vector store
    # -----------------------------------------

    index_path: str

    # -----------------------------------------
    # Processing status
    # -----------------------------------------

    page_count: int
    chunk_count: int
    status: str
    error: str

class RetrievalState(TypedDict, total=False):
    space_id: str
    query: str
    top_k: int
    retrieved_documents: list[dict]
    context: str
    sources: list[dict]
    status: str
    error: str