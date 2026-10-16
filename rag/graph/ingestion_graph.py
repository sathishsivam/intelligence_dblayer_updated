from pathlib import Path
from datetime import datetime, timezone

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from ..ingestion.document_loader import (
    DocumentLoader,
)

from ..ingestion.chunker import (
    DocumentChunker,
)

from ..embeddings.ollama_embeddings import (
    OllamaEmbeddingService,
)

from ..vectorstore.faiss_store import (
    FAISSStore,
)

from ..storage.metadata import (
    STORAGE_ROOT,get_connection,
)

from ..graph.state import (
    IngestionState,
)


class IngestionGraph:

    def __init__(self):

        self.loader = DocumentLoader()

        self.chunker = DocumentChunker(
            chunk_size=1000,
            chunk_overlap=150,
        )

        self.embedding_service = (
            OllamaEmbeddingService(
                model="nomic-embed-text"
            )
        )

    # =================================================
    # Node 1: Load Document
    # =================================================

    def load_document(
        self,
        state: IngestionState,
    ) -> IngestionState:

       

        document = self.loader.load(
            state["file_path"]
        )
        # Keep the original uploaded filename in RAG metadata.
        # The physical file may contain the document UUID prefix.
        
        document["file_name"] = state["file_name"]
    

        return {
            **state,
            "document": document,
            "page_count": document["page_count"],
        }

    # =================================================
    # Node 2: Create Chunks
    # =================================================

    def create_chunks(
        self,
        state: IngestionState,
    ) -> IngestionState:

        document = state["document"]

        chunks = self.chunker.chunk(
            document
        )

        for chunk in chunks:
            chunk["document_id"] = state["document_id"]
            chunk["file_name"] = document["file_name"]

        return {
            **state,
            "chunks": chunks,
            "chunk_count": len(chunks),
        }

    # =================================================
    # Node 3: Create Embeddings + FAISS
    # =================================================

    def create_vector_store(
        self,
        state: IngestionState,
    ) -> IngestionState:

        space_id = state["space_id"]

        index_path = (
            STORAGE_ROOT
            / "spaces"
            / space_id
            / "index"
        )

        store = FAISSStore(
            index_path=index_path,
            embedding_service=self.embedding_service,
        )

        store.create_or_add(
            state["chunks"]
            )

        return {
            **state,
            "index_path": str(index_path),
        }

    # =================================================
    # Node 4: Update Status
    # =================================================

    def update_status(
        self,
        state: IngestionState,
    ) -> IngestionState:

        # from ..storage.metadata import (
        #     get_connection,
        # )

        document_id = state["document_id"]

        # now = __import__(
        #     "datetime"
        # ).datetime.now(
        #     __import__(
        #         "datetime"
        #     ).timezone.utc
        # ).isoformat()

        now = datetime.now(
                 timezone.utc
                ).isoformat()

        with get_connection() as conn:

            conn.execute(
                """
                UPDATE rag_documents
                SET
                    page_count = ?,
                    chunk_count = ?,
                    status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    state["page_count"],
                    state["chunk_count"],
                    "COMPLETED",
                    now,
                    document_id,
                ),
            )

            conn.commit()

        return {
            **state,
            "status": "COMPLETED",
        }

    # =================================================
    # Build Graph
    # =================================================

    def build(self):

        graph = StateGraph(
            IngestionState
        )

        graph.add_node(
            "load_document",
            self.load_document,
        )

        graph.add_node(
            "create_chunks",
            self.create_chunks,
        )

        graph.add_node(
            "create_vector_store",
            self.create_vector_store,
        )

        graph.add_node(
            "update_status",
            self.update_status,
        )

        graph.add_edge(
            START,
            "load_document",
        )

        graph.add_edge(
            "load_document",
            "create_chunks",
        )

        graph.add_edge(
            "create_chunks",
            "create_vector_store",
        )

        graph.add_edge(
            "create_vector_store",
            "update_status",
        )

        graph.add_edge(
            "update_status",
            END,
        )

        return graph.compile()
    
    def invoke(self, state: IngestionState) -> IngestionState:
        graph = self.build()
        return graph.invoke(state)