from rag.storage.metadata import STORAGE_ROOT
from rag.vectorstore.faiss_store import FAISSStore
from rag.embeddings.ollama_embeddings import (
    OllamaEmbeddingService,
)


SPACE_ID = "b2526b73-d746-4afa-b6cf-2bdedfc76d36"

index_path = (
    STORAGE_ROOT
    / "spaces"
    / SPACE_ID
    / "index"
)

embedding_service = OllamaEmbeddingService(
    model="nomic-embed-text"
)

store = FAISSStore(
    index_path=index_path,
    embedding_service=embedding_service,
)

query = "is pps is mandatory for ?"

results = store.similarity_search(
    query=query,
    k=5,
)

print("=" * 70)
print("RAG RETRIEVAL TEST")
print("=" * 70)

print(f"\nQuery: {query}")
print(f"Results: {len(results)}")

for i, result in enumerate(results, start=1):

    print("\n" + "-" * 70)
    print(f"Result #{i}")

    print("File       :", result.metadata.get("file_name"))
    print("Document ID:", result.metadata.get("document_id"))
    print("Page       :", result.metadata.get("page_number"))
    print("Chunk      :", result.metadata.get("chunk_index"))

    print("\nContent:")
    print(result.page_content[:500])

print("\n" + "=" * 70)