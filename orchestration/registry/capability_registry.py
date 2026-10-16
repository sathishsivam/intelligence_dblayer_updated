from typing import Any

from ...mcp_builder.registry.tool_registry import tool_registry
from ...rag.service import RagService


class CapabilityRegistry:

    def __init__(self):
        self._mcp_registry = tool_registry
        self._rag_service = RagService()

    # ============================================================
    # PUBLIC API
    # ============================================================

    def get_capabilities(self) -> list[dict[str, Any]]:
        """
        Return the capability catalog used by the AI Planner.

        This is an adapter over the existing MCP registry and
        existing RAG Management service. It does not maintain
        another persistent registry.
        """

        return (
            self.get_mcp_capabilities()
            + self.get_rag_capabilities()
        )

    # ============================================================
    # MCP CAPABILITIES
    # ============================================================

    def get_mcp_capabilities(self) -> list[dict[str, Any]]:

        capabilities = []

        for tool in self._mcp_registry.list():

            if not tool.get("enabled", True):
                continue

            capabilities.append(
                self._normalize_mcp_tool(tool)
            )

        return capabilities

    # ============================================================
    # RAG CAPABILITIES
    # ============================================================

    def get_rag_capabilities(self) -> list[dict[str, Any]]:

        capabilities = []

        spaces = self._rag_service.list_spaces()

        for space in spaces:
            # Only expose RAG spaces that are ready for runtime retrieval.
           
            if space.get("status") != "ACTIVE":
                 continue

            capabilities.append(
                {
                    "type": "RAG",
                    "name": space.get("name"),
                    "space_id": space.get("id"),
                    "description": space.get(
                        "description",
                        "",
                    ),
                    "embedding_provider": space.get(
                        "embedding_provider"
                    ),
                    "embedding_model": space.get(
                        "embedding_model"
                    ),
                    "vector_store": space.get(
                        "vector_store"
                    ),
                }
            )

        return capabilities

    # ============================================================
    # MCP NORMALIZATION
    # ============================================================

    def _normalize_mcp_tool(
        self,
        tool: dict[str, Any],
    ) -> dict[str, Any]:

        backend = tool.get(
            "backend",
            {},
        )

        parameters = []

        # --------------------------------------------------------
        # OpenAPI parameters
        # --------------------------------------------------------

        for parameter in tool.get(
            "parameters",
            [],
        ):

            parameters.append(
                self._normalize_parameter(
                    parameter
                )
            )

        # --------------------------------------------------------
        # JSON request body
        # --------------------------------------------------------

        request_body = tool.get(
            "request_body"
        )

        body_parameters = (
            self._extract_body_parameters(
                request_body
            )
        )

        parameters.extend(
            body_parameters
        )

        return {
            "type": "MCP",

            "name": tool.get(
                "name"
            ),

            "description": tool.get(
                "description",
                "",
            ),

            "method": backend.get(
                "method",
                "GET",
            ),

            "path": backend.get(
                "path",
                "",
            ),

            "operation_id": tool.get(
                "operation_id"
            ),

            "parameters": parameters,

            "tags": tool.get(
                "tags",
                [],
            ),
        }

    # ============================================================
    # NORMALIZE OPENAPI PARAMETER
    # ============================================================

    def _normalize_parameter(
        self,
        parameter: dict[str, Any],
    ) -> dict[str, Any]:

        schema = parameter.get(
            "schema",
            {},
        )

        return {
            "name": parameter.get(
                "name"
            ),

            "type": schema.get(
                "type",
                parameter.get(
                    "type",
                    "string",
                ),
            ),

            "required": parameter.get(
                "required",
                False,
            ),

            "description": parameter.get(
                "description"
            ),

            "location": parameter.get(
                "in",
                parameter.get(
                    "location"
                ),
            ),
        }

    # ============================================================
    # REQUEST BODY PARAMETERS
    # ============================================================

    def _extract_body_parameters(
        self,
        request_body: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:

        if not request_body:
            return []

        content = request_body.get(
            "content",
            {},
        )

        json_content = content.get(
            "application/json",
            {},
        )

        schema = json_content.get(
            "schema",
            {},
        )

        properties = schema.get(
            "properties",
            {},
        )

        required_fields = set(
            schema.get(
                "required",
                [],
            )
        )

        parameters = []

        for name, property_schema in properties.items():

            parameters.append(
                {
                    "name": name,

                    "type": property_schema.get(
                        "type",
                        "string",
                    ),

                    "required": (
                        name in required_fields
                    ),

                    "description": property_schema.get(
                        "description"
                    ),

                    "location": "body",
                }
            )

        return parameters
