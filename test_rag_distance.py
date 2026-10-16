from rag.graph.retrieval_graph import RetrievalGraph


QUERY = "What documents are required for a account opening?"

SPACES = {
    "CUB Operations": "6772e8ed-b865-4e46-9e0f-0aa542a7d2b4",
    "Banking Operations": "50705c2f-1eda-47e0-a69e-c671e16c5a0b",
}
graph = RetrievalGraph()

for space_name, space_id in SPACES.items():

    print("\n" + "=" * 80)
    print(f"SPACE: {space_name}")
    print(f"SPACE ID: {space_id}")
    print("=" * 80)

    try:
        result = graph.invoke(
            {
                "space_id": space_id,
                "query": QUERY,
                "top_k": 5,
            }
        )

        for index, document in enumerate(
            result.get("retrieved_documents", []),
            start=1,
        ):

            metadata = document.get("metadata", {})

            print(f"\nResult #{index}")
            print(f"Distance   : {document.get('distance')}")
            print(f"File       : {metadata.get('file_name')}")
            print(f"Page       : {metadata.get('page_number')}")
            print(f"Chunk      : {metadata.get('chunk_index')}")
            print(f"Content    : {document.get('content', '')[:300]}")

    except Exception as exc:

        print(f"\nERROR: {exc}")
