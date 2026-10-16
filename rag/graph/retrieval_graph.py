from langgraph.graph import StateGraph, START, END

from ..embeddings.ollama_embeddings import OllamaEmbeddingService
from ..storage.metadata import STORAGE_ROOT
from ..vectorstore.faiss_store import FAISSStore
from .state import RetrievalState


class RetrievalGraph:

    def __init__(self):
        self.embedding_service = OllamaEmbeddingService(
            model="nomic-embed-text"
        )

    def retrieve(
        self,
        state: RetrievalState,
    ) -> RetrievalState:

        space_id = state["space_id"]
        query = state["query"]
        top_k = state.get("top_k", 5)

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

        results = store.similarity_search_with_score(
            query=query,
            k=top_k,
        )

        retrieved_documents = []

        for document, distance in results:

            retrieved_documents.append(
                {
                    "content": document.page_content,
                    "metadata": document.metadata,
                    "distance": float(distance),
                }
            )

        return {
            **state,
            "retrieved_documents": retrieved_documents,
            "status": "RETRIEVED",
        }

    def build_context(
        self,
        state: RetrievalState,
    ) -> RetrievalState:

        documents = state.get(
            "retrieved_documents",
            [],
        )

        context_parts = []
        sources = []

        for document in documents:

            content = document["content"]
            metadata = document["metadata"]

            file_name = metadata.get("file_name")
            document_id = metadata.get("document_id")
            page_number = metadata.get("page_number")
            chunk_index = metadata.get("chunk_index")
            distance = document.get("distance")

            context_parts.append(
                f"""
Source: {file_name}
Page: {page_number}
Chunk: {chunk_index}
Distance: {distance}

{content}
""".strip()
            )

            sources.append(
                {
                    "file_name": file_name,
                    "document_id": document_id,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "distance": distance,
                }
            )

        return {
            **state,
            "context": "\n\n---\n\n".join(context_parts),
            "sources": sources,
        }

    def build(self):

        graph = StateGraph(RetrievalState)

        graph.add_node(
            "retrieve",
            self.retrieve,
        )

        graph.add_node(
            "build_context",
            self.build_context,
        )

        graph.add_edge(
            START,
            "retrieve",
        )

        graph.add_edge(
            "retrieve",
            "build_context",
        )

        graph.add_edge(
            "build_context",
            END,
        )

        return graph.compile()

    def invoke(
        self,
        state: RetrievalState,
    ) -> RetrievalState:

        graph = self.build()

        return graph.invoke(state)

