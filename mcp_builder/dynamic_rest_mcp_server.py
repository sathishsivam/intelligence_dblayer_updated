# import asyncio
# import httpx

# from fastmcp import FastMCP
# from fastmcp.tools import FunctionTool


# # ============================================================
# # Configuration
# # ============================================================

# BACKEND_URL = "http://127.0.0.1:8000"

# TOOLS_URL = (
#     f"{BACKEND_URL}/api-discovery/tools"
# )


# # ============================================================
# # MCP Server
# # ============================================================

# mcp = FastMCP("Dynamic REST Tools")


# # ============================================================
# # Execute REST tool through API Discovery
# # ============================================================

# async def execute_dynamic_tool(
#     tool_name: str,
#     arguments: dict,
# ):
#     """
#     Forward MCP tool invocation to the
#     API Discovery execution endpoint.
#     """

#     url = (
#         f"{BACKEND_URL}"
#         f"/api-discovery/execute-tool/"
#         f"{tool_name}"
#     )

#     print("=" * 80)
#     print("EXECUTING API DISCOVERY TOOL")
#     print("=" * 80)

#     print(f"Tool     : {tool_name}")
#     print(f"Arguments: {arguments}")
#     print(f"URL      : {url}")

#     try:

#         async with httpx.AsyncClient(
#             timeout=120,
#             follow_redirects=True,
#         ) as client:

#             response = await client.post(
#                 url,
#                 json=arguments,
#             )

#     except httpx.RequestError as exc:

#         print(
#             f"ERROR calling API Discovery: {exc}"
#         )

#         return {
#             "success": False,
#             "status_code": 502,
#             "error": "Unable to reach API Discovery",
#             "details": str(exc),
#         }

#     print(
#         f"API Discovery status: "
#         f"{response.status_code}"
#     )

#     # --------------------------------------------------------
#     # Try to parse JSON
#     # --------------------------------------------------------

#     try:

#         response_data = response.json()

#     except ValueError:

#         response_data = {
#             "raw": response.text
#         }

#     # --------------------------------------------------------
#     # Don't use raise_for_status()
#     #
#     # API Discovery already returns useful error
#     # information such as missing parameters.
#     # --------------------------------------------------------

#     if not response.is_success:

#         return {
#             "success": False,
#             "status_code": response.status_code,
#             "error": (
#                 f"API Discovery returned "
#                 f"HTTP {response.status_code}"
#             ),
#             "data": response_data,
#         }

#     return response_data


# # ============================================================
# # Build MCP input schema from REST parameters
# # ============================================================

# def build_input_schema(
#     tool_definition: dict,
# ) -> dict:

#     properties = {}
#     required = []

#     # --------------------------------------------------------
#     # REST parameters
#     #
#     # Handles:
#     #
#     # path
#     # query
#     # header
#     # cookie
#     # --------------------------------------------------------

#     parameters = tool_definition.get(
#         "parameters",
#         [],
#     )

#     for parameter in parameters:

#         name = parameter.get("name")

#         if not name:
#             continue

#         description = (
#             parameter.get("description")
#             or f"Parameter: {name}"
#         )

#         schema = parameter.get(
#             "schema",
#             {},
#         )

#         # ----------------------------------------------------
#         # Copy parameter schema
#         # ----------------------------------------------------

#         property_schema = schema.copy()

#         property_schema["description"] = (
#             description
#         )

#         properties[name] = property_schema

#         # ----------------------------------------------------
#         # Required parameter
#         # ----------------------------------------------------

#         if parameter.get(
#             "required",
#             False,
#         ):

#             required.append(name)

#     # --------------------------------------------------------
#     # Request body parameters
#     # --------------------------------------------------------

#     request_body = tool_definition.get(
#         "request_body"
#     )

#     if request_body:

#         content = request_body.get(
#             "content",
#             {},
#         )

#         json_content = content.get(
#             "application/json"
#         )

#         if json_content:

#             body_schema = json_content.get(
#                 "schema",
#                 {},
#             )

#             body_properties = body_schema.get(
#                 "properties",
#                 {},
#             )

#             for name, schema in body_properties.items():

#                 # Do not overwrite an existing
#                 # path/query/header parameter.

#                 if name not in properties:

#                     properties[name] = schema.copy()

#             body_required = body_schema.get(
#                 "required",
#                 [],
#             )

#             for name in body_required:

#                 if name not in required:

#                     required.append(name)

#     # --------------------------------------------------------
#     # Final MCP schema
#     # --------------------------------------------------------

#     schema = {
#         "type": "object",
#         "properties": properties,
#     }

#     if required:

#         schema["required"] = required

#     return schema


# # ============================================================
# # Load REST APIs and convert them to MCP tools
# # ============================================================

# async def load_tools():

#     print("=" * 80)
#     print("LOADING DYNAMIC REST TOOLS")
#     print("=" * 80)

#     print(
#         f"API Discovery URL: {TOOLS_URL}"
#     )

#     # --------------------------------------------------------
#     # Get registered REST tools
#     # --------------------------------------------------------

#     try:

#         async with httpx.AsyncClient(
#             timeout=30,
#             follow_redirects=True,
#         ) as client:

#             response = await client.get(
#                 TOOLS_URL
#             )

#             response.raise_for_status()

#             data = response.json()

#     except httpx.RequestError as exc:

#         print(
#             f"ERROR connecting to API Discovery: "
#             f"{exc}"
#         )

#         return

#     except httpx.HTTPStatusError as exc:

#         print(
#             "ERROR API Discovery returned "
#             f"HTTP {exc.response.status_code}"
#         )

#         return

#     # --------------------------------------------------------
#     # Extract tools
#     # --------------------------------------------------------

#     tools = data.get(
#         "tools",
#         [],
#     )

#     print(
#         f"Discovered {len(tools)} REST tools"
#     )

#     print()

#     # --------------------------------------------------------
#     # Register every REST tool as MCP tool
#     # --------------------------------------------------------

#     for tool_definition in tools:

#         tool_name = tool_definition.get(
#             "name"
#         )

#         if not tool_name:

#             continue

#         description = (
#             tool_definition.get(
#                 "description"
#             )
#             or tool_name
#         )

#         # ----------------------------------------------------
#         # Build input schema
#         # ----------------------------------------------------

#         parameters = build_input_schema(
#             tool_definition
#         )

#         print("-" * 80)

#         print(
#             f"REST TOOL : {tool_name}"
#         )

#         print(
#             f"Description: {description}"
#         )

#         print(
#             f"MCP Schema : {parameters}"
#         )

#         # ----------------------------------------------------
#         # Dynamic function
#         #
#         # IMPORTANT:
#         #
#         # We use **kwargs so FastMCP can pass
#         # dynamically discovered parameters.
#         # ----------------------------------------------------

#         async def dynamic_function(
#             _tool_name=tool_name,
#             **kwargs,
#         ):

#             print()
#             print("=" * 80)
#             print("MCP TOOL INVOCATION")
#             print("=" * 80)

#             print(
#                 f"Tool      : {_tool_name}"
#             )

#             print(
#                 f"Arguments : {kwargs}"
#             )

#             return await execute_dynamic_tool(
#                 _tool_name,
#                 kwargs,
#             )

#         # ----------------------------------------------------
#         # Create FastMCP FunctionTool
#         # ----------------------------------------------------

#         function_tool = FunctionTool(

#             name=tool_name,

#             description=description,

#             parameters=parameters,

#             fn=dynamic_function,

#             run_in_thread=False,
#         )

#         # ----------------------------------------------------
#         # Register tool
#         # ----------------------------------------------------

#         mcp.add_tool(
#             function_tool
#         )

#         print(
#             f"Registered MCP tool: "
#             f"{tool_name}"
#         )

#     print()
#     print("=" * 80)
#     print("ALL DYNAMIC REST TOOLS LOADED")
#     print("=" * 80)


# # ============================================================
# # Start MCP Server
# # ============================================================

# if __name__ == "__main__":

#     asyncio.run(
#         load_tools()
#     )

#     print()
#     print("=" * 80)
#     print("STARTING MCP SERVER")
#     print("=" * 80)

#     print(
#         "MCP URL: "
#         "http://127.0.0.1:8001/mcp"
#     )

#     mcp.run(
#         transport="streamable-http",
#         host="127.0.0.1",
#         port=8001,
#     )


import asyncio
import httpx

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool


# ============================================================
# Configuration
# ============================================================

BACKEND_URL = "http://127.0.0.1:8000"

TOOLS_URL = (
    f"{BACKEND_URL}/api-discovery/tools"
)


# ============================================================
# MCP Server
# ============================================================

mcp = FastMCP("Dynamic REST Tools")


# ============================================================
# Execute REST tool through API Discovery
# ============================================================

async def execute_dynamic_tool(
    tool_name: str,
    arguments: dict,
):
    """
    Forward MCP tool invocation to the
    API Discovery execution endpoint.
    """

    url = (
        f"{BACKEND_URL}"
        f"/api-discovery/execute-tool/"
        f"{tool_name}"
    )

    print("=" * 80)
    print("EXECUTING API DISCOVERY TOOL")
    print("=" * 80)

    print(f"Tool     : {tool_name}")
    print(f"Arguments: {arguments}")
    print(f"URL      : {url}")

    try:

        async with httpx.AsyncClient(
            timeout=120,
            follow_redirects=True,
        ) as client:

            response = await client.post(
                url,
                json=arguments,
            )

    except httpx.RequestError as exc:

        print(
            f"ERROR calling API Discovery: {exc}"
        )

        return {
            "success": False,
            "status_code": 502,
            "error": "Unable to reach API Discovery",
            "details": str(exc),
        }

    print(
        f"API Discovery status: "
        f"{response.status_code}"
    )

    # --------------------------------------------------------
    # Parse response
    # --------------------------------------------------------

    try:

        response_data = response.json()

    except ValueError:

        response_data = {
            "raw": response.text
        }

    # --------------------------------------------------------
    # Return API Discovery errors
    # --------------------------------------------------------

    if not response.is_success:

        return {
            "success": False,
            "status_code": response.status_code,
            "error": (
                f"API Discovery returned "
                f"HTTP {response.status_code}"
            ),
            "data": response_data,
        }

    return response_data


# ============================================================
# Convert REST parameter schema into MCP property
# ============================================================

def build_parameter_property(
    parameter: dict,
) -> tuple[str | None, dict]:

    name = parameter.get("name")

    if not name:
        return None, {}

    description = (
        parameter.get("description")
        or f"Parameter: {name}"
    )

    parameter_schema = parameter.get(
        "schema",
        {}
    )

    property_schema = parameter_schema.copy()

    property_schema["description"] = description

    return name, property_schema


# ============================================================
# Build MCP input schema
# ============================================================

def build_input_schema(
    tool_definition: dict,
) -> dict:
    """
    Build a generic MCP input schema from a REST tool.

    Supports:

        Path parameters
        Query parameters
        Header parameters
        Cookie parameters
        JSON request bodies

    Examples:

        /accounts/{id}

        /accounts/{id}/balance

        /posts/{id}

        /accounts?customer_id=10

        /transfer
    """

    properties = {}
    required = []

    # ========================================================
    # 1. REST parameters
    #
    # Handles:
    #
    # path
    # query
    # header
    # cookie
    # ========================================================

    parameters = tool_definition.get(
        "parameters",
        []
    )

    for parameter in parameters:

        name, property_schema = (
            build_parameter_property(parameter)
        )

        if not name:
            continue

        properties[name] = property_schema

        if parameter.get(
            "required",
            False
        ):

            if name not in required:

                required.append(name)

    # ========================================================
    # 2. JSON request body
    #
    # API Discovery stores request_body directly
    # as a JSON Schema:
    #
    # {
    #     "type": "object",
    #     "properties": {...},
    #     "required": [...]
    # }
    # ========================================================

    request_body = tool_definition.get(
        "request_body"
    )

    if request_body:

        body_type = request_body.get(
            "type"
        )

        # ----------------------------------------------------
        # Normal JSON object body
        # ----------------------------------------------------

        if body_type == "object":

            body_properties = request_body.get(
                "properties",
                {}
            )

            for name, schema in (
                body_properties.items()
            ):

                # Don't overwrite an existing
                # REST parameter.

                if name not in properties:

                    properties[name] = schema.copy()

            body_required = request_body.get(
                "required",
                []
            )

            for name in body_required:

                if name not in required:

                    required.append(name)

        # ----------------------------------------------------
        # Fallback for schemas wrapped in content
        #
        # This also makes the code compatible with
        # OpenAPI-style request_body definitions.
        # ----------------------------------------------------

        else:

            content = request_body.get(
                "content",
                {}
            )

            json_content = content.get(
                "application/json"
            )

            if json_content:

                body_schema = json_content.get(
                    "schema",
                    {}
                )

                body_properties = (
                    body_schema.get(
                        "properties",
                        {}
                    )
                )

                for name, schema in (
                    body_properties.items()
                ):

                    if name not in properties:

                        properties[name] = (
                            schema.copy()
                        )

                body_required = (
                    body_schema.get(
                        "required",
                        []
                    )
                )

                for name in body_required:

                    if name not in required:

                        required.append(name)

    # ========================================================
    # 3. Final MCP schema
    # ========================================================

    schema = {
        "type": "object",
        "properties": properties,
    }

    if required:

        schema["required"] = required

    return schema


# ============================================================
# Create dynamic MCP function
# ============================================================

def create_dynamic_function(
    tool_name: str,
):

    async def dynamic_function(
        **kwargs,
    ):

        print()
        print("=" * 80)
        print("MCP TOOL INVOCATION")
        print("=" * 80)

        print(
            f"Tool      : {tool_name}"
        )

        print(
            f"Arguments : {kwargs}"
        )

        return await execute_dynamic_tool(
            tool_name,
            kwargs,
        )

    return dynamic_function


# ============================================================
# Load REST APIs and convert them to MCP tools
# ============================================================

async def load_tools():

    print("=" * 80)
    print("LOADING DYNAMIC REST TOOLS")
    print("=" * 80)

    print(
        f"API Discovery URL: {TOOLS_URL}"
    )

    # ========================================================
    # Get registered REST tools
    # ========================================================

    try:

        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
        ) as client:

            response = await client.get(
                TOOLS_URL
            )

            response.raise_for_status()

            data = response.json()

    except httpx.RequestError as exc:

        print(
            f"ERROR connecting to API Discovery: "
            f"{exc}"
        )

        return

    except httpx.HTTPStatusError as exc:

        print(
            "ERROR API Discovery returned "
            f"HTTP {exc.response.status_code}"
        )

        return

    # ========================================================
    # Extract tools
    # ========================================================

    tools = data.get(
        "tools",
        []
    )

    print(
        f"Discovered {len(tools)} REST tools"
    )

    print()

    # ========================================================
    # Register every REST tool as MCP tool
    # ========================================================

    for tool_definition in tools:

        tool_name = tool_definition.get(
            "name"
        )

        if not tool_name:
            continue

        description = (
            tool_definition.get(
                "description"
            )
            or tool_name
        )

        # ----------------------------------------------------
        # Build MCP input schema
        # ----------------------------------------------------

        parameters = build_input_schema(
            tool_definition
        )

        print("-" * 80)

        print(
            f"REST TOOL : {tool_name}"
        )

        print(
            f"Description: {description}"
        )

        print(
            f"MCP Schema : {parameters}"
        )

        # ----------------------------------------------------
        # Create dynamic function
        # ----------------------------------------------------

        dynamic_function = (
            create_dynamic_function(
                tool_name
            )
        )

        # ----------------------------------------------------
        # Create FastMCP FunctionTool
        # ----------------------------------------------------

        function_tool = FunctionTool(

            name=tool_name,

            description=description,

            parameters=parameters,

            fn=dynamic_function,

            run_in_thread=False,
        )

        # ----------------------------------------------------
        # Register MCP tool
        # ----------------------------------------------------

        mcp.add_tool(
            function_tool
        )

        print(
            f"Registered MCP tool: "
            f"{tool_name}"
        )

    print()
    print("=" * 80)
    print("ALL DYNAMIC REST TOOLS LOADED")
    print("=" * 80)


# ============================================================
# Start MCP Server
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        load_tools()
    )

    print()
    print("=" * 80)
    print("STARTING MCP SERVER")
    print("=" * 80)

    print(
        "MCP URL: "
        "http://127.0.0.1:8001/mcp"
    )

    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
    )