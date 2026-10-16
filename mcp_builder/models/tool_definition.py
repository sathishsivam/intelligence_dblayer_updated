from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPToolDefinition:

    name: str

    description: str

    input_schema: dict[str, Any]

    backend_url: str

    method: str

    path: str

    operation_id: str | None = None

    headers: dict[str, str] = field(
        default_factory=dict
    )

    enabled: bool = True