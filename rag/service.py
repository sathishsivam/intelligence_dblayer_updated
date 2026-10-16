# from .graph.retrieval_graph import RetrievalGraph
# from .graph.ingestion_graph import IngestionGraph
# from .storage.repository import (
#     RagSpaceRepository,
#     RagDocumentRepository,
# )


# class RagService:
#     def __init__(self):
#         self.repository = RagSpaceRepository()
#         self.document_repository = RagDocumentRepository()
#         self.ingestion_graph = IngestionGraph()
#         self.retrieval_graph = RetrievalGraph()

#     def list_spaces(self):
#         return self.repository.list_spaces()
    
#     def get_space(self, space_id):
#         return self.repository.get_space(space_id)

#     def retrieve(
#         self,
#         space_id: str,
#         query: str,
#         top_k: int = 5,
#     ) -> dict:

#         space = self.repository.get_space(space_id)

#         if space is None:
#             raise ValueError("RAG space not found")

#         result = self.retrieval_graph.invoke(
#             {
#                 "space_id": space_id,
#                 "query": query,
#                 "top_k": top_k,
#             }
#         )

#         return {
#             "query": query,
#             "status": result.get(
#                 "status",
#                 "RETRIEVED",
#             ),
#             "documents": result.get(
#                 "retrieved_documents",
#                 [],
#             ),
#             "sources": result.get(
#                 "sources",
#                 [],
#             ),
#             "context": result.get(
#                 "context",
#                 "",
#             ),
#         }
    


# from .graph.retrieval_graph import RetrievalGraph
# from .graph.ingestion_graph import IngestionGraph
# from .storage.repository import (
#     RagSpaceRepository,
#     RagDocumentRepository,
# )


# class RagService:
#     def __init__(self):
#         self.repository = RagSpaceRepository()
#         self.document_repository = RagDocumentRepository()
#         self.ingestion_graph = IngestionGraph()
#         self.retrieval_graph = RetrievalGraph()

#     def list_spaces(self):
#         return self.repository.list_spaces()

#     def create_space(self, request):
#         return self.repository.create_space(
#             name=request.name,
#             description=request.description,
#             embedding_provider=request.embedding_provider,
#             embedding_model=request.embedding_model,
#             vector_store=request.vector_store,
#             chunk_size=request.chunk_size,
#             chunk_overlap=request.chunk_overlap,
#         )

#     def get_space(self, space_id):
#         return self.repository.get_space(space_id)

#     def retrieve(
#         self,
#         space_id: str,
#         query: str,
#         top_k: int = 5,
#     ) -> dict:

#         space = self.repository.get_space(space_id)

#         if space is None:
#             raise ValueError("RAG space not found")

#         result = self.retrieval_graph.invoke(
#             {
#                 "space_id": space_id,
#                 "query": query,
#                 "top_k": top_k,
#             }
#         )

#         return {
#             "query": query,
#             "status": result.get(
#                 "status",
#                 "RETRIEVED",
#             ),
#             "documents": result.get(
#                 "retrieved_documents",
#                 [],
#             ),
#             "sources": result.get(
#                 "sources",
#                 [],
#             ),
#             "context": result.get(
#                 "context",
#                 "",
#             ),
#         }

# from .graph.retrieval_graph import RetrievalGraph
# from .graph.ingestion_graph import IngestionGraph
# from .storage.repository import (
#     RagSpaceRepository,
#     RagDocumentRepository,
# )


# class RagService:
#     def __init__(self):
#         self.repository = RagSpaceRepository()
#         self.document_repository = RagDocumentRepository()
#         self.ingestion_graph = IngestionGraph()
#         self.retrieval_graph = RetrievalGraph()

#     def list_spaces(self):
#         return self.repository.list_spaces()

#     def create_space(self, request):
#         return self.repository.create_space(
#             name=request.name,
#             description=request.description,
#             embedding_provider=request.embedding_provider,
#             embedding_model=request.embedding_model,
#             vector_store=request.vector_store,
#             chunk_size=request.chunk_size,
#             chunk_overlap=request.chunk_overlap,
#         )

#     def get_space(self, space_id):
#         return self.repository.get_space(space_id)

#     def list_documents(self, space_id):
#         return self.document_repository.list_documents(space_id)

#     def retrieve(
#         self,
#         space_id: str,
#         query: str,
#         top_k: int = 5,
#     ) -> dict:

#         space = self.repository.get_space(space_id)

#         if space is None:
#             raise ValueError("RAG space not found")

#         result = self.retrieval_graph.invoke(
#             {
#                 "space_id": space_id,
#                 "query": query,
#                 "top_k": top_k,
#             }
#         )

#         return {
#             "query": query,
#             "status": result.get(
#                 "status",
#                 "RETRIEVED",
#             ),
#             "documents": result.get(
#                 "retrieved_documents",
#                 [],
#             ),
#             "sources": result.get(
#                 "sources",
#                 [],
#             ),
#             "context": result.get(
#                 "context",
#                 "",
#             ),
#         }


from pathlib import Path

from .graph.retrieval_graph import RetrievalGraph
from .graph.ingestion_graph import IngestionGraph
from .storage.repository import (
    RagSpaceRepository,
    RagDocumentRepository,
)
from .storage.metadata import STORAGE_ROOT
import uuid


class RagService:
    def __init__(self):
        self.repository = RagSpaceRepository()
        self.document_repository = RagDocumentRepository()
        self.ingestion_graph = IngestionGraph()
        self.retrieval_graph = RetrievalGraph()

    # ==================================================================
    # RAG SPACE
    # ==================================================================

    def list_spaces(self):
        return self.repository.list_spaces()

    def create_space(self, request):
        return self.repository.create_space(
            name=request.name,
            description=request.description,
            embedding_provider=request.embedding_provider,
            embedding_model=request.embedding_model,
            vector_store=request.vector_store,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

    def get_space(self, space_id):
        return self.repository.get_space(space_id)

    def delete_space(self, space_id):
        return self.repository.delete_space(space_id)

    # ==================================================================
    # DOCUMENTS
    # ==================================================================

    def list_documents(self, space_id: str):
        """
        Return all documents belonging to a RAG space.
        """

        space = self.repository.get_space(space_id)

        if space is None:
            raise ValueError("RAG space not found")

        return self.document_repository.list_documents(space_id)

    def upload_document(
        self,
        *,
        space_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
        file_content: bytes,
    ):
        """
        Upload and ingest a document into a RAG space.

        Flow:

            Validate space
                ↓
            Generate document ID
                ↓
            Save physical document
                ↓
            Create document metadata
                ↓
            Run IngestionGraph
                ↓
            Return completed document
        """

        # --------------------------------------------------------------
        # Validate RAG space
        # --------------------------------------------------------------

        space = self.repository.get_space(space_id)

        if space is None:
            raise ValueError("RAG space not found")

        # --------------------------------------------------------------
        # Validate file
        # --------------------------------------------------------------

        if not file_name or not file_name.strip():
            raise ValueError("Uploaded file name is required")

        if not file_content:
            raise ValueError("Uploaded file is empty")

        # Prevent path traversal from uploaded filenames.
        safe_file_name = Path(file_name).name

        if not safe_file_name:
            raise ValueError("Invalid uploaded file name")

        # --------------------------------------------------------------
        # Generate document ID
        # --------------------------------------------------------------

        document_id = str(uuid.uuid4())

        # --------------------------------------------------------------
        # Physical document storage
        # --------------------------------------------------------------

        documents_root = (
            STORAGE_ROOT
            / "spaces"
            / space_id
            / "documents"
        )

        documents_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = (
            documents_root
            / f"{document_id}_{safe_file_name}"
        )

        # --------------------------------------------------------------
        # Save uploaded file
        # --------------------------------------------------------------

        try:

            file_path.write_bytes(file_content)

        except Exception as exc:

            raise RuntimeError(
                f"Failed to save uploaded document: {exc}"
            ) from exc

        # --------------------------------------------------------------
        # Create document metadata
        # --------------------------------------------------------------

        try:

            document = self.document_repository.create_document(
                document_id=document_id,
                space_id=space_id,
                file_name=safe_file_name,
                file_type=file_type,
                file_size=file_size,
            )

        except Exception as exc:

            # Remove physical file if metadata creation fails.
            if file_path.exists():
                file_path.unlink()

            raise RuntimeError(
                f"Failed to create document metadata: {exc}"
            ) from exc

        # --------------------------------------------------------------
        # Run ingestion graph
        # --------------------------------------------------------------

        ingestion_state = {
            "space_id": space_id,
            "document_id": document_id,
            "file_path": str(file_path),
            "file_name": safe_file_name,
        }

        try:

            result = self.ingestion_graph.invoke(
                ingestion_state
            )

        except Exception as exc:

            # The document was created as PROCESSING.
            # Remove the physical file and metadata so that
            # failed uploads do not remain as orphan records.

            if file_path.exists():
                file_path.unlink()

            try:
                self.document_repository.delete_document(
                    document_id
                )
            except Exception:
                pass

            raise RuntimeError(
                f"RAG document ingestion failed: {exc}"
            ) from exc

        # --------------------------------------------------------------
        # Return latest document metadata
        # --------------------------------------------------------------

        completed_document = (
            self.document_repository.get_document(
                document_id
            )
        )

        if completed_document is None:
            raise RuntimeError(
                "Document ingestion completed but "
                "document metadata could not be found"
            )

        return completed_document

    def get_document(
        self,
        *,
        space_id: str,
        document_id: str,
    ):
        """
        Return a single document belonging to the specified space.
        """

        space = self.repository.get_space(space_id)

        if space is None:
            raise ValueError("RAG space not found")

        document = self.document_repository.get_document(
            document_id
        )

        if document is None:
            raise ValueError("RAG document not found")

        if document.get("space_id") != space_id:
            raise ValueError("RAG document not found")

        return document

    def delete_document(
        self,
        *,
        space_id: str,
        document_id: str,
    ):
        """
        Delete a document from a RAG space.

        Removes:
            - document metadata
            - physical uploaded document

        Vector-store cleanup is intentionally not performed here
        because the current FAISS store is shared by documents in
        the RAG space and requires a rebuild/removal strategy.
        """

        space = self.repository.get_space(space_id)

        if space is None:
            raise ValueError("RAG space not found")

        document = self.document_repository.get_document(
            document_id
        )

        if document is None:
            raise ValueError("RAG document not found")

        if document.get("space_id") != space_id:
            raise ValueError("RAG document not found")

        # --------------------------------------------------------------
        # Remove physical document
        # --------------------------------------------------------------

        documents_root = (
            STORAGE_ROOT
            / "spaces"
            / space_id
            / "documents"
        )

        original_file_name = document.get("file_name") or ""

        # Uploaded files are stored as:
        #
        # <document_id>_<original_filename>
        #
        physical_file = (
            documents_root
            / f"{document_id}_{Path(original_file_name).name}"
        )

        if physical_file.exists():
            physical_file.unlink()

        # --------------------------------------------------------------
        # Remove metadata
        # --------------------------------------------------------------

        deleted = self.document_repository.delete_document(
            document_id
        )

        if not deleted:
            raise ValueError("RAG document not found")

        return True

    # ==================================================================
    # RETRIEVAL
    # ==================================================================

    def retrieve(
        self,
        space_id: str,
        query: str,
        top_k: int = 5,
    ) -> dict:

        space = self.repository.get_space(space_id)

        if space is None:
            raise ValueError("RAG space not found")

        result = self.retrieval_graph.invoke(
            {
                "space_id": space_id,
                "query": query,
                "top_k": top_k,
            }
        )

        return {
            "query": query,
            "status": result.get(
                "status",
                "RETRIEVED",
            ),
            "documents": result.get(
                "retrieved_documents",
                [],
            ),
            "sources": result.get(
                "sources",
                [],
            ),
            "context": result.get(
                "context",
                "",
            ),
        }