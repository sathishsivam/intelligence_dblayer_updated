from typing import Any

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):

    type: str

    name: str

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class OrchestrationResponse(BaseModel):

    success: bool

    intent: str | None = None

    strategy: str | None = None

    response: str | None = None

    sources: list[SourceInfo] = Field(
        default_factory=list
    )

    requires_authentication: bool = False

    requires_confirmation: bool = False

    confirmation_id: str | None = None

    clarification_question: str | None = None

    error: str | None = None