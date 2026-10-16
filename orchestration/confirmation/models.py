from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PendingConfirmation(BaseModel):
    confirmation_id: str

    session_id: str | None = None

    intent: str

    capability_name: str

    arguments: dict[str, Any] = Field(
        default_factory=dict
    )

    created_at: datetime

    expires_at: datetime

    status: str = "PENDING"