from fastapi import (
    APIRouter,
    HTTPException,
    status,
    UploadFile,
    File,
)

from .schemas.rag_document import RagDocumentResponse
from .schemas.rag_space import (
    RagSpaceCreate,
    RagSpaceResponse,
)
from .schemas.rag_retrieval import (
    RagRetrievalRequest,
    RagRetrievalResponse,
)
from .service import RagService


ALLOWED_FILE_TYPES = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
}


router = APIRouter(
    prefix="/rag",
    tags=["RAG Management"],
)


rag_service = RagService()


# ======================================================================
# RAG SPACE
# ======================================================================

@router.post(
    "/spaces",
    response_model=RagSpaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rag_space(
    request: RagSpaceCreate,
):
    return rag_service.create_space(request)


@router.get(
    "/spaces",
    response_model=list[RagSpaceResponse],
)
def list_rag_spaces():
    return rag_service.list_spaces()


@router.get(
    "/spaces/{space_id}",
    response_model=RagSpaceResponse,
)
def get_rag_space(
    space_id: str,
):
    space = rag_service.get_space(space_id)

    if space is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RAG space not found",
        )

    return space


@router.delete(
    "/spaces/{space_id}",
)
def delete_rag_space(
    space_id: str,
):
    deleted = rag_service.delete_space(space_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RAG space not found",
        )

    return {
        "success": True,
        "message": "RAG space deleted successfully",
        "space_id": space_id,
    }


# ======================================================================
# DOCUMENT UPLOAD
# ======================================================================

@router.post(
    "/spaces/{space_id}/documents",
    response_model=RagDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    space_id: str,
    file: UploadFile = File(...),
):
    file_name = file.filename or ""

    extension = ""

    if "." in file_name:
        extension = (
            "."
            + file_name.rsplit(".", 1)[1].lower()
        )

    if extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: {extension}. "
                f"Allowed types: "
                f"{sorted(ALLOWED_FILE_TYPES)}"
            ),
        )

    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    try:

        document = rag_service.upload_document(
            space_id=space_id,
            file_name=file_name,
            file_type=extension,
            file_size=len(file_content),
            file_content=file_content,
        )

        return document

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ======================================================================
# LIST DOCUMENTS
# ======================================================================

@router.get(
    "/spaces/{space_id}/documents",
    response_model=list[RagDocumentResponse],
)
def list_documents(
    space_id: str,
):

    try:

        return rag_service.list_documents(
            space_id
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ======================================================================
# GET SINGLE DOCUMENT
# ======================================================================

@router.get(
    "/spaces/{space_id}/documents/{document_id}",
    response_model=RagDocumentResponse,
)
def get_document(
    space_id: str,
    document_id: str,
):

    try:

        return rag_service.get_document(
            space_id=space_id,
            document_id=document_id,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ======================================================================
# DELETE SINGLE DOCUMENT
# ======================================================================

@router.delete(
    "/spaces/{space_id}/documents/{document_id}",
)
def delete_document(
    space_id: str,
    document_id: str,
):

    try:

        rag_service.delete_document(
            space_id=space_id,
            document_id=document_id,
        )

        return {
            "success": True,
            "message": "RAG document deleted successfully",
            "space_id": space_id,
            "document_id": document_id,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete RAG document: {exc}",
        )


# ======================================================================
# RETRIEVAL
# ======================================================================

@router.post(
    "/spaces/{space_id}/retrieve",
    response_model=RagRetrievalResponse,
)
def retrieve_documents(
    space_id: str,
    request: RagRetrievalRequest,
):

    try:

        return rag_service.retrieve(
            space_id=space_id,
            query=request.query,
            top_k=request.top_k,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG retrieval failed: {exc}",
        )