from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIParameter:
    name: str
    location: str
    required: bool = False
    description: str | None = None
    schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class APIRequestBody:
    required: bool = False
    description: str | None = None
    content: dict[str, Any] = field(default_factory=dict)


@dataclass
class APIResponse:
    status_code: str
    description: str | None = None
    content: dict[str, Any] = field(default_factory=dict)


@dataclass
class APIEndpoint:

    path: str
    method: str

    summary: str | None = None
    description: str | None = None
    operation_id: str | None = None

    tags: list[str] = field(default_factory=list)

    parameters: list[APIParameter] = field(
        default_factory=list
    )

    request_body: APIRequestBody | None = None

    responses: list[APIResponse] = field(
        default_factory=list
    )

    security: list[dict[str, Any]] = field(
        default_factory=list
    )