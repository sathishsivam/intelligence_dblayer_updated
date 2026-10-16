from typing import Any

from pydantic import BaseModel, Field


class OrchestrationRequest(BaseModel):

    query: str = Field(
        ...,
        min_length=1,
        description="Natural language banking query",
    )

    session_id: str | None = None

    user_context: dict[str, Any] | None = None


class ConfirmationRequest(BaseModel):

    confirmation_id: str = Field(
        ...,
        min_length=1,
        description="Pending confirmation identifier",
    )

    session_id: str | None = Field(
        default=None,
        description="Session associated with the pending operation",
    )

    user_context: dict[str, Any] | None = None
