from typing import Any, TypedDict


class OrchestrationState(TypedDict, total=False):

    # ------------------------------------------------------------
    # Input
    # ------------------------------------------------------------

    user_query: str

    session_id: str | None

    user_context: dict[str, Any] | None

    # ------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------

    intent: str

    strategy: str

    confidence: float

    selected_mcp_tools: list[dict[str, Any]]

    selected_rag_sources: list[dict[str, Any]]

    requires_authentication: bool

    requires_confirmation: bool

    clarification_question: str | None

    # ------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------

    mcp_results: list[dict[str, Any]]

    rag_results: list[dict[str, Any]]

    # ------------------------------------------------------------
    # Response
    # ------------------------------------------------------------

    merged_context: list[dict[str, Any]]

    final_response: str

    error: str | None
