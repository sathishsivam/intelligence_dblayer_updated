from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Strategy(str, Enum):

    MCP = "MCP"

    RAG = "RAG"

    MCP_AND_RAG = "MCP_AND_RAG"

    CLARIFICATION = "CLARIFICATION"


class CapabilityType(str, Enum):

    MCP = "MCP"

    RAG = "RAG"


class CapabilitySelection(BaseModel):

    type: CapabilityType

    name: str

    space_id: str | None = None

    arguments: dict = Field(
        default_factory=dict
    )

    reason: str | None = None


class QueryPlan(BaseModel):

    intent: str = Field(
        description="Normalized banking intent"
    )

    strategy: Strategy

    capabilities: list[
        CapabilitySelection
    ] = Field(
        default_factory=list
    )

    requires_authentication: bool = False

    requires_confirmation: bool = False

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    clarification_question: str | None = None

    @model_validator(mode="after")
    def validate_capabilities(self):
        """
        A non-clarification execution plan must contain
        at least one selected capability.

        CLARIFICATION plans may legitimately have no
        capabilities because the required information
        is missing or ambiguous.
        """

        if (
            self.strategy != Strategy.CLARIFICATION
            and not self.capabilities
        ):
            raise ValueError(
                "A non-clarification plan must select "
                "at least one capability."
            )

        return self
