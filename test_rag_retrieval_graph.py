from rag.graph.retrieval_graph import RetrievalGraph


SPACE_ID = "b2526b73-d746-4afa-b6cf-2bdedfc76d36"


graph = RetrievalGraph()

result = graph.invoke(
    {
        "space_id": SPACE_ID,
        "query": "is pps mandatory for high value cheques?",
        "top_k": 5,
    }
)


print("=" * 70)
print("LANGGRAPH RAG RETRIEVAL TEST")
print("=" * 70)

print("\nStatus:", result.get("status"))

print("\nRetrieved documents:")

for index, document in enumerate(
    result.get("retrieved_documents", []),
    start=1,
):

    metadata = document["metadata"]

    print("\n" + "-" * 70)
    print(f"Result #{index}")
    print("File       :", metadata.get("file_name"))
    print("Document ID:", metadata.get("document_id"))
    print("Page       :", metadata.get("page_number"))
    print("Chunk      :", metadata.get("chunk_index"))

print("\n" + "=" * 70)
print("SOURCES")
print("=" * 70)

for source in result.get("sources", []):

    print(
        f"{source['file_name']} "
        f"| Page {source['page_number']} "
        f"| Chunk {source['chunk_index']}"
    )

print("\n" + "=" * 70)
print("CONTEXT")
print("=" * 70)

print(result.get("context", ""))

