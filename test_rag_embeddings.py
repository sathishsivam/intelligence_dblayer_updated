from pathlib import Path

from rag.ingestion.document_loader import DocumentLoader
from rag.ingestion.chunker import DocumentChunker
from rag.embeddings.ollama_embeddings import (
    OllamaEmbeddingService,
)
from rag.vectorstore.faiss_store import FAISSStore


SPACE_ID = "d9317716-a775-4c50-a544-67e6d9c3aa45"

DOCUMENT_ID = "b30ca910-5d38-459f-83b1-574c90a32d4c"

STORAGE_ROOT = (
    Path.home()
    / ".aizillon"
    / "rag"
)

DOCUMENT_DIR = (
    STORAGE_ROOT
    / "spaces"
    / SPACE_ID
    / "documents"
)

INDEX_DIR = (
    STORAGE_ROOT
    / "spaces"
    / SPACE_ID
    / "index"
)


def main():

    print("=" * 70)
    print("RAG EMBEDDING + FAISS TEST")
    print("=" * 70)

    # --------------------------------------------------
    # 1. Locate document
    # --------------------------------------------------

    files = list(
        DOCUMENT_DIR.glob(
            f"{DOCUMENT_ID}_*"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"Document not found: {DOCUMENT_DIR}"
        )

    document_path = files[0]

    print("\n[1] Document:")
    print(document_path)

    # --------------------------------------------------
    # 2. Extract document
    # --------------------------------------------------

    loader = DocumentLoader()

    document = loader.load(
        str(document_path)
    )

    print("\n[2] PDF extracted")
    print(
        f"Pages: {document['page_count']}"
    )
    print(
        f"Characters: {len(document['text'])}"
    )

    # --------------------------------------------------
    # 3. Create chunks
    # --------------------------------------------------

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=150,
    )

    chunks = chunker.chunk(
        document
    )

    print("\n[3] Chunking completed")
    print(
        f"Chunks: {len(chunks)}"
    )

    # --------------------------------------------------
    # 4. Initialize Ollama
    # --------------------------------------------------

    print("\n[4] Initializing Ollama...")

    embedding_service = (
        OllamaEmbeddingService(
            model="nomic-embed-text"
        )
    )

    print(
        "[OK] Ollama embedding model initialized"
    )

    # --------------------------------------------------
    # 5. Create FAISS index
    # --------------------------------------------------

    print("\n[5] Creating FAISS index...")

    store = FAISSStore(
        index_path=INDEX_DIR,
        embedding_service=embedding_service,
    )

    vector_store = store.create(
        chunks
    )

    print(
        "[OK] FAISS index created"
    )

    # --------------------------------------------------
    # 6. Verify index
    # --------------------------------------------------

    print("\n[6] FAISS verification")

    print(
        f"Index directory: {INDEX_DIR}"
    )

    index_files = list(
        INDEX_DIR.iterdir()
    )

    for file in index_files:
        print(
            f"  {file.name}"
        )

    # --------------------------------------------------
    # 7. Test similarity search
    # --------------------------------------------------

    print("\n[7] Testing similarity search...")

    query = (
        "What are the banking operations policies?"
    )

    results = vector_store.similarity_search(
        query,
        k=5,
    )

    print(
        f"\nQuery: {query}"
    )

    print(
        f"Results: {len(results)}"
    )

    for index, result in enumerate(
        results,
        start=1,
    ):

        print("\n" + "-" * 70)

        print(
            f"Result {index}"
        )

        print(
            f"Page: "
            f"{result.metadata.get('page_number')}"
        )

        print(
            f"Chunk: "
            f"{result.metadata.get('chunk_index')}"
        )

        print("\nText:")

        print(
            result.page_content[:500]
        )

    print("\n" + "=" * 70)
    print("OLLAMA + FAISS TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()