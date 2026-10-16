import asyncio
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.tools import Tool




FASTAPI_BASE_URL = "http://127.0.0.1:8000"


mcp = FastMCP("Dynamic REST Tools")

async def get_registered_tools() -> list[dict]:
    """
    Get all MCP tool definitions registered
    in the FastAPI API Discovery service.
    """

    url = f"{FASTAPI_BASE_URL}/api-discovery/tools"

    async with httpx.AsyncClient(timeout=10) as client:

        response = await client.get(url)

        response.raise_for_status()

        data = response.json()

    return data.get("tools", [])







# ============================================================
# GET REGISTERED TOOLS FROM FASTAPI
# ============================================================


# async def get_registered_tools() -> list[dict]:

#     url = f"{FASTAPI_BASE_URL}/api-discovery/tools"

#     async with httpx.AsyncClient(timeout=10) as client:

#         response = await client.get(url)

#         response.raise_for_status()

#         data = response.json()

#     return data.get("tools", [])


# ============================================================
# REGISTER DYNAMIC TOOLS
# ============================================================

async def register_dynamic_tools():

    tools = await get_registered_tools()

    print("=" * 80)
    print("DYNAMIC MCP TOOL REGISTRATION")
    print("=" * 80)

    for tool_definition in tools:

        name = tool_definition.get("name")

        if not name:
            continue

        description = tool_definition.get(
            "description",
            f"Dynamic REST tool: {name}",
        )

        # ----------------------------------------------------
        # Create a separate closure for this tool
        # ----------------------------------------------------

        async def dynamic_executor(
            arguments: dict,
            _tool_name=name,
        ):
            return await execute_registered_tool(
                tool_name=_tool_name,
                arguments=arguments,
            )

        # ----------------------------------------------------
        # Give the callable a useful name/documentation
        # ----------------------------------------------------

        dynamic_executor.__name__ = name

        dynamic_executor.__doc__ = description

        # ----------------------------------------------------
        # Convert callable into FastMCP FunctionTool
        # ----------------------------------------------------

        mcp_tool = Tool.from_function(
            dynamic_executor,
            name=name,
            description=description,
        )

        # ----------------------------------------------------
        # Register with FastMCP
        # ----------------------------------------------------

        mcp.add_tool(mcp_tool)

        print(
            f"✓ Registered MCP tool: {name}"
        )

    print("=" * 80)

    print(
        f"Total dynamic tools: {len(tools)}"
    )


# ============================================================
# EXECUTE REGISTERED REST TOOL
# ============================================================

async def execute_registered_tool(
    tool_name: str,
    arguments: dict,
) -> Any:

    url = (
        f"{FASTAPI_BASE_URL}"
        f"/api-discovery/execute-tool/{tool_name}"
    )

    async with httpx.AsyncClient(timeout=60) as client:

        response = await client.post(
            url,
            json=arguments,
        )

        response.raise_for_status()

        return response.json()


# ============================================================
# CONVERT OPENAPI SCHEMA TO MCP INPUT SCHEMA
# ============================================================

def get_input_schema(tool: dict) -> dict:

    request_body = tool.get("request_body")

    if isinstance(request_body, dict):

        content = request_body.get(
            "content",
            {},
        )

        if isinstance(content, dict):

            json_content = content.get(
                "application/json"
            )

            if isinstance(json_content, dict):

                schema = json_content.get(
                    "schema"
                )

                if isinstance(schema, dict):

                    return schema

    # --------------------------------------------------------
    # No request body
    # --------------------------------------------------------

    properties = {}

    required = []

    parameters = tool.get(
        "parameters",
        [],
    )

    if isinstance(parameters, list):

        for parameter in parameters:

            if not isinstance(parameter, dict):
                continue

            name = parameter.get("name")

            if not name:
                continue

            schema = parameter.get(
                "schema",
                {},
            )

            if not isinstance(schema, dict):
                schema = {}

            properties[name] = schema

            if parameter.get(
                "required",
                False,
            ):
                required.append(name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


# ============================================================
# CREATE MCP TOOL
# ============================================================

def create_mcp_tool(
    tool_definition: dict,
) -> Tool:

    tool_name = tool_definition["name"]

    description = tool_definition.get(
        "description",
        f"Dynamic REST tool: {tool_name}",
    )

    input_schema = get_input_schema(
        tool_definition
    )

    # --------------------------------------------------------
    # MCP execution callback
    # --------------------------------------------------------

    async def execute(
        arguments: dict,
    ) -> Any:

        return await execute_registered_tool(
            tool_name=tool_name,
            arguments=arguments,
        )

    # --------------------------------------------------------
    # FastMCP Tool
    # --------------------------------------------------------

    return Tool(
        name=tool_name,

        description=description,

        parameters=input_schema,

        # The callable used when the MCP client invokes tool
        # is attached below.
    )


# ============================================================
# REGISTER DYNAMIC TOOLS
# ============================================================

async def register_dynamic_tools():

    tools = await get_registered_tools()

    print("=" * 80)
    print("DYNAMIC MCP TOOL REGISTRATION")
    print("=" * 80)

    for tool_definition in tools:

        name = tool_definition.get(
            "name"
        )

        if not name:
            continue

        print(
            f"Registering MCP tool: {name}"
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # FastMCP 3.4.7's Tool constructor defines the schema,
        # while add_tool() registers a callable or Tool.
        #
        # For execution we create a callable whose signature
        # is generated from the OpenAPI schema.
        # ----------------------------------------------------

        input_schema = get_input_schema(
            tool_definition
        )

        properties = input_schema.get(
            "properties",
            {},
        )

        required = set(
            input_schema.get(
                "required",
                [],
            )
        )

        # ----------------------------------------------------
        # Create dynamic callable
        # ----------------------------------------------------

        async def dynamic_executor(
            _tool_name=name,
            **kwargs,
        ):

            return await execute_registered_tool(
                tool_name=_tool_name,
                arguments=kwargs,
            )

        dynamic_executor.__name__ = name

        dynamic_executor.__doc__ = (
            tool_definition.get(
                "description",
                f"Dynamic REST tool: {name}",
            )
        )

        # ----------------------------------------------------
        # FastMCP automatically inspects callable parameters.
        #
        # Because arbitrary **kwargs does not expose the
        # OpenAPI schema, we use the Tool object directly.
        # ----------------------------------------------------

        async def call_tool(
            arguments: dict,
            _tool_name=name,
        ):

            return await execute_registered_tool(
                tool_name=_tool_name,
                arguments=arguments,
            )

        # ----------------------------------------------------
        # Create Tool object
        # ----------------------------------------------------

        mcp_tool = Tool(
            name=name,

            description=tool_definition.get(
                "description",
                f"Dynamic REST tool: {name}",
            ),

            parameters={
                "type": "object",
                "properties": properties,
                "required": list(required),
            },
        )

        # ----------------------------------------------------
        # Store execution function on Tool
        # ----------------------------------------------------

        mcp_tool.fn = call_tool

        # ----------------------------------------------------
        # Register
        # ----------------------------------------------------

        mcp.add_tool(
            mcp_tool
        )

        print(
            f"✓ Registered: {name}"
        )

    print("=" * 80)

    print(
        f"Total dynamic tools: {len(tools)}"
    )


# ============================================================
# STATIC TOOL
# ============================================================

@mcp.tool()
async def list_dynamic_tools() -> dict:
    """
    List REST tools registered in the API Discovery service.
    """

    tools = await get_registered_tools()

    return {
        "tools": tools
    }


# ============================================================
# STATIC TOOL
# ============================================================

@mcp.tool()
async def execute_dynamic_tool(
    tool_name: str,
    arguments: dict,
) -> dict:
    """
    Execute a REST API tool registered through API Discovery.
    """

    return await execute_registered_tool(
        tool_name=tool_name,
        arguments=arguments,
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    # --------------------------------------------------------
    # Load tools created by MCP Builder
    # --------------------------------------------------------

    await register_dynamic_tools()

    # --------------------------------------------------------
    # Start MCP server
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("MCP SERVER")
    print("=" * 80)
    print("URL: http://127.0.0.1:8001")
    print("Transport: Streamable HTTP")
    print("=" * 80)
    print()

    await mcp.run_async(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
