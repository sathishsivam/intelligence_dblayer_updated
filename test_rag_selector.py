from orchestration.retrieval.rag_selector import RAGSelector


query = "What should the bank do when an account becomes inoperative?"

selector = RAGSelector()

result = selector.search(
    query=query,
    top_k_per_space=5,
    final_top_k=10,
)

print("\n" + "=" * 80)
print("RAG SELECTOR TEST")
print("=" * 80)

print(f"\nQuery: {result.get('query')}")
print(f"Spaces searched: {result.get('spaces_searched')}")
print(f"Success: {result.get('success')}")

print("\nSELECTED RESULTS")
print("-" * 80)

for index, item in enumerate(
    result.get("results", []),
    start=1,
):

    metadata = item.get("metadata", {})

    print(f"\n#{index}")
    print(f"Space    : {item.get('space_name')}")
    print(f"Distance : {item.get('distance')}")
    print(f"File     : {metadata.get('file_name')}")
    print(f"Page     : {metadata.get('page_number')}")
    print(f"Chunk    : {metadata.get('chunk_index')}")
    print(f"Content  : {item.get('content', '')[:250]}")

if result.get("errors"):
    print("\nSPACE ERRORS")
    print("-" * 80)

    for error in result["errors"]:
        print(error)
