from typing import Any

from ...rag.service import RagService


class RAGSelector:
    """
    Selects relevant knowledge from ACTIVE RAG spaces.

    Retrieval is intentionally lightweight:

    1. Search each ACTIVE RAG space using FAISS.
    2. Build a relevance profile for each space.
    3. Rank spaces using their FAISS results.
    4. Select the strongest RAG space.
    5. Return the top chunks from that space.

    No LLM is called during retrieval.

    Multi-space retrieval can be introduced later if testing
    proves that a single RAG space is insufficient.
    """

    def __init__(
        self,
        rag_service: RagService | None = None,
    ):
        self.rag_service = (
            rag_service or RagService()
        )

    def search(
        self,
        query: str,
        top_k_per_space: int = 5,
        final_top_k: int = 5,
    ) -> dict[str, Any]:

        if not query or not query.strip():
            return {
                "success": False,
                "results": [],
                "error": "RAG query is required",
            }

        spaces = self.rag_service.list_spaces()

        active_spaces = [
            space
            for space in spaces
            if space.get("status") == "ACTIVE"
        ]

        space_profiles: list[dict[str, Any]] = []
        space_errors: list[dict[str, Any]] = []

        # ---------------------------------------------------------
        # Search every ACTIVE RAG space
        # ---------------------------------------------------------

        for space in active_spaces:

            space_id = space.get("id")
            space_name = space.get("name")

            if not space_id:
                continue

            try:
                result = self.rag_service.retrieve(
                    space_id=space_id,
                    query=query.strip(),
                    top_k=top_k_per_space,
                )

                documents = result.get(
                    "documents",
                    [],
                )

                valid_documents = [
                    document
                    for document in documents
                    if document.get("content")
                ]

                if not valid_documents:
                    continue

                distances = [
                    float(document["distance"])
                    for document in valid_documents
                    if document.get("distance") is not None
                ]

                if not distances:
                    continue

                # Lower FAISS distance means a stronger
                # vector similarity match.
                best_distance = min(distances)

                # Average distance across retrieved chunks.
                sorted_distances = sorted(distances)

                average_distance = (
                    sum(sorted_distances)
                    / len(sorted_distances)
                )

                # Number of chunks reasonably close to the
                # strongest result.
                #
                # This is retained as diagnostic information.
                # It is NOT currently used to select spaces.
                strong_candidates = sum(
                    1
                    for distance in distances
                    if distance <= best_distance + 0.20
                )

                space_profiles.append(
                    {
                        "space_id": space_id,
                        "space_name": space_name,
                        "documents": valid_documents,
                        "best_distance": best_distance,
                        "average_distance": average_distance,
                        "strong_candidates": strong_candidates,
                    }
                )

            except Exception as exc:

                space_errors.append(
                    {
                        "space_id": space_id,
                        "space_name": space_name,
                        "error": str(exc),
                    }
                )

        # ---------------------------------------------------------
        # No usable RAG results
        # ---------------------------------------------------------

        if not space_profiles:
            return {
                "success": False,
                "query": query.strip(),
                "spaces_searched": len(active_spaces),
                "spaces_selected": [],
                "results": [],
                "space_profiles": [],
                "errors": space_errors,
                "error": "No RAG results found",
            }

        # ---------------------------------------------------------
        # Rank spaces
        # ---------------------------------------------------------
        #
        # Primary signal:
        #     best FAISS distance
        #
        # Secondary signals:
        #     strong candidate count
        #     average distance
        #
        # Lower distance is better.
        #
        # At this stage we intentionally use the best distance
        # as the primary ranking signal. The other metrics are
        # retained for diagnostics and future evaluation.
        #

        space_profiles.sort(
            key=lambda profile: (
                profile["best_distance"],
                -profile["strong_candidates"],
                profile["average_distance"],
            )
        )

        # ---------------------------------------------------------
        # Select strongest RAG space
        # ---------------------------------------------------------

        selected_profiles = self._select_spaces(
            space_profiles
        )

        # ---------------------------------------------------------
        # Collect chunks only from selected space(s)
        # ---------------------------------------------------------

        selected_results: list[dict[str, Any]] = []

        for profile in selected_profiles:

            for document in profile["documents"]:

                metadata = document.get(
                    "metadata",
                    {},
                )

                selected_results.append(
                    {
                        "space_id": profile["space_id"],
                        "space_name": profile["space_name"],
                        "content": document.get(
                            "content",
                            "",
                        ),
                        "metadata": metadata,
                        "distance": document.get(
                            "distance"
                        ),
                    }
                )

        # ---------------------------------------------------------
        # Rank chunks within selected space(s)
        # ---------------------------------------------------------

        selected_results.sort(
            key=lambda item: (
                float(item["distance"])
                if item.get("distance") is not None
                else float("inf")
            )
        )

        selected_results = selected_results[
            :final_top_k
        ]

        return {
            "success": bool(selected_results),
            "query": query.strip(),
            "spaces_searched": len(active_spaces),
            "spaces_selected": [
                profile["space_name"]
                for profile in selected_profiles
            ],
            "space_profiles": [
                {
                    "space_id": profile["space_id"],
                    "space_name": profile["space_name"],
                    "best_distance": profile["best_distance"],
                    "average_distance": profile["average_distance"],
                    "strong_candidates": profile[
                        "strong_candidates"
                    ],
                }
                for profile in space_profiles
            ],
            "results": selected_results,
            "errors": space_errors,
        }

    def _select_spaces(
        self,
        profiles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        if not profiles:
            return []

        # Initial strategy:
        # select only the strongest RAG space.
        #
        # Multi-space retrieval will be introduced later
        # only if testing proves that a single RAG space
        # is insufficient.

        return [profiles[0]]