from typing import Any

from ...mcp_builder.registry.tool_registry import tool_registry
from ...mcp_builder.runtime.rest_executor import RestExecutor


class MCPExecutor:

    def __init__(self):

        self.rest_executor = RestExecutor()

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        # --------------------------------------------------------
        # Find MCP capability
        # --------------------------------------------------------

        tool_definition = tool_registry.get(
            tool_name
        )

        if not tool_definition:

            return {
                "success": False,
                "error": (
                    f"MCP tool not found: {tool_name}"
                ),
            }

        # --------------------------------------------------------
        # Check enabled state
        # --------------------------------------------------------

        if not tool_definition.get(
            "enabled",
            True,
        ):

            return {
                "success": False,
                "error": (
                    f"MCP tool disabled: {tool_name}"
                ),
            }

        # --------------------------------------------------------
        # Execute through existing runtime
        # --------------------------------------------------------

        return await self.rest_executor.execute(
            tool_definition,
            arguments or {},
        )
    