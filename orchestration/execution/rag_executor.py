from typing import Any

from ...rag.service import RagService


class RAGExecutor:

    def __init__(self):

        self.rag_service = RagService()

    def execute(
        self,
        space_id: str,
        query: str,
        top_k: int = 5,
    ) -> dict[str, Any]:

        if not space_id:

            return {
                "success": False,
                "error": "RAG space_id is required",
            }

        if not query:

            return {
                "success": False,
                "error": "RAG query is required",
            }

        try:

            result = self.rag_service.retrieve(
                space_id=space_id,
                query=query,
                top_k=top_k,
            )

            return {
                "success": True,
                **result,
            }

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }
    