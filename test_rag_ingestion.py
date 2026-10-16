from pathlib import Path

from rag.ingestion.document_loader import DocumentLoader
from rag.ingestion.chunker import DocumentChunker


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


def main():

    print("=" * 70)
    print("RAG INGESTION TEST")
    print("=" * 70)

    # --------------------------------------------------
    # 1. Locate document
    # --------------------------------------------------

    print("\n[1] Document directory:")
    print(DOCUMENT_DIR)

    files = list(
        DOCUMENT_DIR.glob(
            f"{DOCUMENT_ID}_*"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"Uploaded document was not found in: {DOCUMENT_DIR}"
        )

    document_path = files[0]

    print("\n[OK] Document found:")
    print(document_path)

    # --------------------------------------------------
    # 2. Load document
    # --------------------------------------------------

    print("\n[2] Loading document...")

    loader = DocumentLoader()

    document = loader.load(
        str(document_path)
    )

    print("[OK] Document loaded")

    print(
        f"File name   : {document['file_name']}"
    )

    print(
        f"File type   : {document['file_type']}"
    )

    print(
        f"Page count  : {document['page_count']}"
    )

    print(
        f"Text length : {len(document['text'])}"
    )

    # --------------------------------------------------
    # 3. Show page information
    # --------------------------------------------------

    print("\n[3] Pages:")

    for page in document["pages"][:5]:

        print(
            f"  Page {page['page_number']}: "
            f"{len(page['text'])} characters"
        )

    if document["page_count"] > 5:
        print(
            f"  ... {document['page_count'] - 5} more pages"
        )

    # --------------------------------------------------
    # 4. Chunk document
    # --------------------------------------------------

    print("\n[4] Creating chunks...")

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=150,
    )

    chunks = chunker.chunk(
        document
    )

    print(
        f"[OK] Total chunks: {len(chunks)}"
    )

    # --------------------------------------------------
    # 5. Display sample chunks
    # --------------------------------------------------

    print("\n[5] Sample chunks:")
    print("=" * 70)

    for chunk in chunks[:5]:

        print(
            f"\nChunk index : {chunk['chunk_index']}"
        )

        print(
            f"Page number : {chunk['page_number']}"
        )

        print(
            f"Characters  : {len(chunk['text'])}"
        )

        print("\nText:")
        print(chunk["text"][:500])

        print("-" * 70)

    # --------------------------------------------------
    # 6. Summary
    # --------------------------------------------------

    print("\n" + "=" * 70)
    print("INGESTION TEST COMPLETED")
    print("=" * 70)

    print(
        f"Pages  : {document['page_count']}"
    )

    print(
        f"Chunks : {len(chunks)}"
    )

    print(
        f"Text   : {len(document['text'])} characters"
    )


if __name__ == "__main__":
    main()