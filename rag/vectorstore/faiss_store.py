
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from ..embeddings.ollama_embeddings import OllamaEmbeddingService


class FAISSStore:

    def __init__(
        self,
        index_path: str | Path,
        embedding_service: OllamaEmbeddingService,
    ):
        self.index_path = Path(index_path)
        self.embedding_service = embedding_service

    def _build_documents(
        self,
        chunks: list[dict],
    ) -> list[Document]:

        documents = []

        for chunk in chunks:

            documents.append(
                Document(
                    page_content=chunk["text"],
                    metadata={
                        "chunk_index": chunk["chunk_index"],
                        "page_number": chunk.get("page_number"),
                        "document_id": chunk.get("document_id"),
                        "file_name": chunk.get("file_name"),
                    },
                )
            )

        return documents

    def create(
        self,
        chunks: list[dict],
    ) -> FAISS:

        documents = self._build_documents(chunks)

        if not documents:
            raise ValueError(
                "Cannot create FAISS index with no documents"
            )

        vector_store = FAISS.from_documents(
            documents,
            self.embedding_service.embeddings,
        )

        self.index_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        vector_store.save_local(
            str(self.index_path)
        )

        return vector_store

    def add_documents(
        self,
        chunks: list[dict],
    ) -> FAISS:

        documents = self._build_documents(chunks)

        if not documents:
            raise ValueError(
                "Cannot add empty document list"
            )

        vector_store = self.load()

        vector_store.add_documents(
            documents
        )

        vector_store.save_local(
            str(self.index_path)
        )

        return vector_store

    def create_or_add(
        self,
        chunks: list[dict],
    ) -> FAISS:

        if self.exists():
            return self.add_documents(chunks)

        return self.create(chunks)

    def load(self) -> FAISS:

        if not self.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {self.index_path}"
            )

        return FAISS.load_local(
            str(self.index_path),
            self.embedding_service.embeddings,
            allow_dangerous_deserialization=True,
        )

    def exists(self) -> bool:

        return (
            (self.index_path / "index.faiss").exists()
            and
            (self.index_path / "index.pkl").exists()
        )

    def delete_index(self) -> None:

        if not self.index_path.exists():
            return

        for file_name in [
            "index.faiss",
            "index.pkl",
        ]:

            file_path = self.index_path / file_name

            if file_path.exists():
                file_path.unlink()

    def similarity_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:

        vector_store = self.load()

        return vector_store.similarity_search(
            query,
            k=k,
        )

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[Document, float]]:

        vector_store = self.load()

        return vector_store.similarity_search_with_score(
            query,
            k=k,
        )

