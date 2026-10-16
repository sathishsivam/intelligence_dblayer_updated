from pathlib import Path

from rag.graph.ingestion_graph import (
    IngestionGraph,
)


SPACE_ID = (
    "d9317716-a775-4c50-a544-67e6d9c3aa45"
)

DOCUMENT_ID = (
    "b30ca910-5d38-459f-83b1-574c90a32d4c"
)

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


def main():

    print("=" * 70)
    print("LANGGRAPH RAG INGESTION TEST")
    print("=" * 70)

    # ---------------------------------------------
    # Locate document
    # ---------------------------------------------

    files = list(
        DOCUMENT_DIR.glob(
            f"{DOCUMENT_ID}_*"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"Document not found: {DOCUMENT_DIR}"
        )

    file_path = files[0]

    print("\nDocument:")
    print(file_path)

    # ---------------------------------------------
    # Build graph
    # ---------------------------------------------

    ingestion_graph = (
        IngestionGraph()
        .build()
    )

    # ---------------------------------------------
    # Initial state
    # ---------------------------------------------

    state = {
        "space_id": SPACE_ID,
        "document_id": DOCUMENT_ID,
        "file_path": str(file_path),
        "status": "PROCESSING",
    }

    # ---------------------------------------------
    # Run graph
    # ---------------------------------------------

    print("\nStarting LangGraph ingestion...")

    result = ingestion_graph.invoke(
        state
    )

    # ---------------------------------------------
    # Result
    # ---------------------------------------------

    print("\n" + "=" * 70)
    print("LANGGRAPH INGESTION COMPLETED")
    print("=" * 70)

    print(
        f"\nPages      : "
        f"{result.get('page_count')}"
    )

    print(
        f"Chunks     : "
        f"{result.get('chunk_count')}"
    )

    print(
        f"Status     : "
        f"{result.get('status')}"
    )

    print(
        f"Index path : "
        f"{result.get('index_path')}"
    )


if __name__ == "__main__":
    main()