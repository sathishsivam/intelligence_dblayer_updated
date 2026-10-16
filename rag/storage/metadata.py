import os
import sqlite3
from pathlib import Path


DEFAULT_STORAGE = Path(
    os.getenv(
        "AIZILLON_RAG_STORAGE",
        str(Path.home() / ".aizillon" / "rag"),
    )
)

STORAGE_ROOT = DEFAULT_STORAGE
METADATA_DB = STORAGE_ROOT / "metadata.db"


def initialize_storage() -> None:
    """
    Initialize isolated RAG storage.

    This database is completely separate from the
    existing Apzillon Oracle database.
    """

    STORAGE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    (STORAGE_ROOT / "spaces").mkdir(
        parents=True,
        exist_ok=True,
    )

    with sqlite3.connect(METADATA_DB) as conn:

        # -----------------------------------------
        # RAG Spaces
        # -----------------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_spaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,

                embedding_provider TEXT NOT NULL,
                embedding_model TEXT NOT NULL,

                vector_store TEXT NOT NULL,

                chunk_size INTEGER NOT NULL,
                chunk_overlap INTEGER NOT NULL,

                document_count INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,

                status TEXT NOT NULL,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # -----------------------------------------
        # RAG Documents
        # -----------------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_documents (
                id TEXT PRIMARY KEY,
                space_id TEXT NOT NULL,

                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,

                page_count INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,

                status TEXT NOT NULL,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY (space_id)
                    REFERENCES rag_spaces(id)
                    ON DELETE CASCADE
            )
            """
        )

        conn.commit()


def get_connection() -> sqlite3.Connection:
    initialize_storage()

    connection = sqlite3.connect(
        METADATA_DB,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    # Enable foreign-key support for this connection.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection