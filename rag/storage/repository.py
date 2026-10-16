import shutil
import uuid
from datetime import datetime, timezone

from .metadata import get_connection, STORAGE_ROOT


class RagSpaceRepository:
    """
    Repository for RAG Space metadata.

    Storage:
        SQLite:
            rag_spaces
            rag_documents

        Filesystem:
            ~/.aizillon/rag/spaces/<space_id>/
    """

    # ------------------------------------------------------------------
    # CREATE SPACE
    # ------------------------------------------------------------------

    def create_space(
        self,
        *,
        name: str,
        description: str,
        embedding_provider: str,
        embedding_model: str,
        vector_store: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> dict:

        space_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as conn:

            conn.execute(
                """
                INSERT INTO rag_spaces (
                    id,
                    name,
                    description,
                    embedding_provider,
                    embedding_model,
                    vector_store,
                    chunk_size,
                    chunk_overlap,
                    document_count,
                    chunk_count,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    space_id,
                    name,
                    description,
                    embedding_provider,
                    embedding_model,
                    vector_store,
                    chunk_size,
                    chunk_overlap,
                    0,
                    0,
                    "DRAFT",
                    now,
                    now,
                ),
            )

            conn.commit()

        # Create filesystem structure
        space_root = STORAGE_ROOT / "spaces" / space_id

        (space_root / "documents").mkdir(
            parents=True,
            exist_ok=True,
        )

        (space_root / "index").mkdir(
            parents=True,
            exist_ok=True,
        )

        return self.get_space(space_id)

    # ------------------------------------------------------------------
    # LIST SPACES
    # ------------------------------------------------------------------

    def list_spaces(self) -> list[dict]:
        """
        Return all RAG spaces.

        document_count and chunk_count are calculated from
        rag_documents rather than relying only on stored counters.
        """

        with get_connection() as conn:

            rows = conn.execute(
                """
                SELECT
                    s.*,

                    (
                        SELECT COUNT(*)
                        FROM rag_documents d
                        WHERE d.space_id = s.id
                    ) AS calculated_document_count,

                    (
                        SELECT COALESCE(SUM(d.chunk_count), 0)
                        FROM rag_documents d
                        WHERE d.space_id = s.id
                    ) AS calculated_chunk_count

                FROM rag_spaces s
                ORDER BY s.created_at DESC
                """
            ).fetchall()

        spaces = []

        for row in rows:

            space = dict(row)

            document_count = int(
                space.get("calculated_document_count", 0) or 0
            )

            chunk_count = int(
                space.get("calculated_chunk_count", 0) or 0
            )

            space["document_count"] = document_count
            space["chunk_count"] = chunk_count

            space["status"] = self._calculate_space_status(
                document_count=document_count,
                chunk_count=chunk_count,
                stored_status=space.get("status"),
            )

            # Internal calculated fields should not be exposed.
            space.pop(
                "calculated_document_count",
                None,
            )

            space.pop(
                "calculated_chunk_count",
                None,
            )

            spaces.append(space)

        return spaces

    # ------------------------------------------------------------------
    # GET SPACE
    # ------------------------------------------------------------------

    def get_space(
        self,
        space_id: str,
    ) -> dict | None:
        """
        Return a single RAG space with calculated document/chunk counts.
        """

        with get_connection() as conn:

            row = conn.execute(
                """
                SELECT
                    s.*,

                    (
                        SELECT COUNT(*)
                        FROM rag_documents d
                        WHERE d.space_id = s.id
                    ) AS calculated_document_count,

                    (
                        SELECT COALESCE(SUM(d.chunk_count), 0)
                        FROM rag_documents d
                        WHERE d.space_id = s.id
                    ) AS calculated_chunk_count

                FROM rag_spaces s
                WHERE s.id = ?
                """,
                (space_id,),
            ).fetchone()

        if row is None:
            return None

        space = dict(row)

        document_count = int(
            space.get("calculated_document_count", 0) or 0
        )

        chunk_count = int(
            space.get("calculated_chunk_count", 0) or 0
        )

        space["document_count"] = document_count
        space["chunk_count"] = chunk_count

        space["status"] = self._calculate_space_status(
            document_count=document_count,
            chunk_count=chunk_count,
            stored_status=space.get("status"),
        )

        space.pop(
            "calculated_document_count",
            None,
        )

        space.pop(
            "calculated_chunk_count",
            None,
        )

        return space

    # ------------------------------------------------------------------
    # SPACE STATUS
    # ------------------------------------------------------------------

    def _calculate_space_status(
        self,
        *,
        document_count: int,
        chunk_count: int,
        stored_status: str | None,
    ) -> str:
        """
        Calculate a user-facing RAG space status.

        Current rules:

        No documents
            -> preserve stored status, normally DRAFT

        Documents exist
            -> ACTIVE

        This keeps the status simple while document processing
        is handled at document level.
        """

        if document_count == 0:
            return stored_status or "DRAFT"

        return "ACTIVE"

    # ------------------------------------------------------------------
    # DELETE SPACE
    # ------------------------------------------------------------------

    def delete_space(
        self,
        space_id: str,
    ) -> bool:
        """
        Delete a RAG space.

        This removes:

        1. Documents metadata from SQLite
        2. Space metadata from SQLite
        3. Physical documents
        4. FAISS index
        5. Space directory

        It does NOT touch the existing Oracle database.
        """

        with get_connection() as conn:

            row = conn.execute(
                """
                SELECT id
                FROM rag_spaces
                WHERE id = ?
                """,
                (space_id,),
            ).fetchone()

            if row is None:
                return False

            # Delete documents belonging to the space first.
            conn.execute(
                """
                DELETE FROM rag_documents
                WHERE space_id = ?
                """,
                (space_id,),
            )

            # Delete the space.
            conn.execute(
                """
                DELETE FROM rag_spaces
                WHERE id = ?
                """,
                (space_id,),
            )

            conn.commit()

        # Delete physical storage.
        space_root = STORAGE_ROOT / "spaces" / space_id

        if space_root.exists():
            shutil.rmtree(space_root)

        return True


class RagDocumentRepository:
    """
    Repository for RAG document metadata.
    """

    # ------------------------------------------------------------------
    # CREATE DOCUMENT
    # ------------------------------------------------------------------

    def create_document(
        self,
        *,
        document_id: str,
        space_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
    ) -> dict:

        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as conn:

            conn.execute(
                """
                INSERT INTO rag_documents (
                    id,
                    space_id,
                    file_name,
                    file_type,
                    file_size,
                    page_count,
                    chunk_count,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    space_id,
                    file_name,
                    file_type,
                    file_size,
                    0,
                    0,
                    "PROCESSING",
                    now,
                    now,
                ),
            )

            conn.commit()

        return self.get_document(document_id)

    # ------------------------------------------------------------------
    # GET DOCUMENT
    # ------------------------------------------------------------------

    def get_document(
        self,
        document_id: str,
    ) -> dict | None:

        with get_connection() as conn:

            row = conn.execute(
                """
                SELECT *
                FROM rag_documents
                WHERE id = ?
                """,
                (document_id,),
            ).fetchone()

        if row is None:
            return None

        return dict(row)

    # ------------------------------------------------------------------
    # LIST DOCUMENTS
    # ------------------------------------------------------------------

    def list_documents(
        self,
        space_id: str,
    ) -> list[dict]:

        with get_connection() as conn:

            rows = conn.execute(
                """
                SELECT *
                FROM rag_documents
                WHERE space_id = ?
                ORDER BY created_at DESC
                """,
                (space_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # DELETE DOCUMENT
    # ------------------------------------------------------------------

    def delete_document(
        self,
        document_id: str,
    ) -> bool:
        """
        Delete only document metadata.

        Physical file and FAISS index handling are performed
        by RagService because they are filesystem/vector-store
        responsibilities rather than metadata responsibilities.
        """

        with get_connection() as conn:

            row = conn.execute(
                """
                SELECT id
                FROM rag_documents
                WHERE id = ?
                """,
                (document_id,),
            ).fetchone()

            if row is None:
                return False

            conn.execute(
                """
                DELETE FROM rag_documents
                WHERE id = ?
                """,
                (document_id,),
            )

            conn.commit()

        return True
    