from fastapi import APIRouter, HTTPException
import httpx
import re
from typing import Any

from ...mcp_builder.discovery.schema_resolver import resolve_schema
from ...mcp_builder.models.build_tool_request import BuildToolRequest
from ...mcp_builder.runtime.rest_executor import RestExecutor
from ...mcp_builder.registry.tool_registry import tool_registry


router = APIRouter(
    prefix="/api-discovery",
    tags=["API Discovery"],
)


SUPPORTED_METHODS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
}


# =============================================================
# HELPERS
# =============================================================

def _generate_tool_name(method: str, path: str) -> str:
    """
    Generate a stable tool name from HTTP method + API path.

    Example:
        GET /accounts/{account_number}/balance

    becomes:
        get_accounts_account_number_balance
    """

    clean_path = (
        path.strip("/")
        .replace("/", "_")
        .replace("{", "")
        .replace("}", "")
        .replace("-", "_")
    )

    if clean_path:
        return f"{method.lower()}_{clean_path}"

    return f"{method.lower()}_root"


def _extract_path_parameters(path: str) -> list[dict[str, Any]]:
    """
    Extract {parameter} names directly from the API path.

    Example:
        /accounts/{account_number}/balance

    returns:
        [
            {
                "name": "account_number",
                "in": "path",
                "required": True,
                ...
            }
        ]
    """

    parameter_names = re.findall(
        r"\{([^{}]+)\}",
        path,
    )

    return [
        {
            "name": name,
            "in": "path",
            "required": True,
            "description": f"Path parameter: {name}",
            "schema": {
                "type": "string"
            },
        }
        for name in parameter_names
    ]


def _merge_parameters(
    existing_parameters: list[dict[str, Any]] | None,
    path_parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge OpenAPI parameters with parameters extracted from
    the URL path.

    Path parameters are added only when they don't already
    exist in the OpenAPI definition.
    """

    existing_parameters = existing_parameters or []

    result = list(existing_parameters)

    existing_keys = {
        (
            parameter.get("name"),
            parameter.get("in"),
        )
        for parameter in existing_parameters
    }

    for parameter in path_parameters:
        key = (
            parameter.get("name"),
            parameter.get("in"),
        )

        if key not in existing_keys:
            result.append(parameter)

    return result


async def fetch_openapi(
    base_url: str,
) -> dict[str, Any]:
    """
    Fetch OpenAPI specification from any REST backend.

    IMPORTANT:
    The backend URL is supplied dynamically.

    Examples:
        http://127.0.0.1:9000
        http://127.0.0.1:9001
        http://127.0.0.1:8002
        https://bank.example.com
    """

    base_url = str(base_url).rstrip("/")

    openapi_url = f"{base_url}/openapi.json"

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
        ) as client:

            response = await client.get(
                openapi_url
            )

    except httpx.RequestError as exc:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unable to reach backend API",
                "base_url": base_url,
                "openapi_url": openapi_url,
                "error": str(exc),
            },
        )

    if response.status_code != 200:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unable to fetch OpenAPI specification",
                "base_url": base_url,
                "openapi_url": openapi_url,
                "status_code": response.status_code,
                "response": response.text,
            },
        )

    try:
        return response.json()

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Backend did not return valid JSON",
                "openapi_url": openapi_url,
            },
        )


def _resolve_schema(
    schema: dict[str, Any],
    openapi_spec: dict[str, Any],
):
    """
    Resolve an OpenAPI schema using the existing schema resolver.

    Falls back to the original schema if resolution fails.
    """

    try:
        return resolve_schema(
            schema,
            openapi_spec,
        )

    except Exception:
        return schema


def _build_endpoint_definition(
    *,
    path: str,
    method: str,
    operation: dict[str, Any],
    path_item: dict[str, Any],
    openapi_spec: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert one OpenAPI operation into the endpoint structure
    used by MCP Builder.
    """

    method = method.lower()

    # ---------------------------------------------------------
    # Parameters
    # ---------------------------------------------------------

    path_level_parameters = path_item.get(
        "parameters",
        []
    )

    operation_parameters = operation.get(
        "parameters",
        []
    )

    all_parameters = (
        list(path_level_parameters)
        + list(operation_parameters)
    )

    resolved_parameters = []

    seen = set()

    for parameter in all_parameters:

        name = parameter.get("name")
        location = parameter.get("in")

        key = (
            name,
            location,
        )

        if key in seen:
            continue

        seen.add(key)

        schema = parameter.get(
            "schema",
            {}
        )

        resolved_schema = _resolve_schema(
            schema,
            openapi_spec,
        )

        resolved_parameters.append(
            {
                "name": name,
                "in": location,
                "required": parameter.get(
                    "required",
                    False,
                ),
                "description": parameter.get(
                    "description"
                ),
                "schema": resolved_schema,
            }
        )

    # ---------------------------------------------------------
    # Path parameters
    # ---------------------------------------------------------

    path_parameters = _extract_path_parameters(
        path
    )

    parameters = _merge_parameters(
        resolved_parameters,
        path_parameters,
    )

    # ---------------------------------------------------------
    # Request Body
    # ---------------------------------------------------------

    request_body = None

    raw_request_body = operation.get(
        "requestBody"
    )

    if raw_request_body:

        request_body = {
            "required": raw_request_body.get(
                "required",
                False,
            ),
            "content": {},
        }

        content = raw_request_body.get(
            "content",
            {},
        )

        for content_type, media_type in content.items():

            schema = media_type.get(
                "schema",
                {},
            )

            resolved_schema = _resolve_schema(
                schema,
                openapi_spec,
            )

            request_body["content"][
                content_type
            ] = {
                "schema": resolved_schema
            }

    # ---------------------------------------------------------
    # Responses
    # ---------------------------------------------------------

    responses = {}

    for status_code, response_definition in (
        operation.get(
            "responses",
            {}
        ).items()
    ):

        response_data = {
            "description": response_definition.get(
                "description"
            ),
            "content": {},
        }

        content = response_definition.get(
            "content",
            {}
        )

        for content_type, media_type in content.items():

            schema = media_type.get(
                "schema",
                {}
            )

            resolved_schema = _resolve_schema(
                schema,
                openapi_spec,
            )

            response_data["content"][
                content_type
            ] = {
                "schema": resolved_schema
            }

        responses[status_code] = response_data

    # ---------------------------------------------------------
    # Endpoint Definition
    # ---------------------------------------------------------

    operation_id = operation.get(
        "operationId"
    )

    tool_name = (
        operation_id
        or _generate_tool_name(
            method,
            path,
        )
    )

    description = (
        operation.get("description")
        or operation.get("summary")
        or f"{method.upper()} {path}"
    )

    return {
        "name": tool_name,
        "description": description,
        "path": path,
        "method": method.upper(),
        "summary": operation.get(
            "summary"
        ),
        "operation_id": operation_id,
        "tags": operation.get(
            "tags",
            [],
        ),
        "parameters": parameters,
        "request_body": request_body,
        "responses": responses,
        "security": operation.get(
            "security",
            openapi_spec.get(
                "security",
                [],
            ),
        ),
    }


# =============================================================
# DISCOVER API
# =============================================================

@router.post("/discover")
async def discover_api(
    payload: dict,
):
    """
    Discover APIs from any OpenAPI-compatible REST backend.

    Flutter calls:

        POST /api-discovery/discover

    Body:

        {
            "base_url": "http://127.0.0.1:9000"
        }
    """

    base_url = payload.get(
        "base_url"
    )

    if not base_url:

        raise HTTPException(
            status_code=400,
            detail="base_url is required",
        )

    base_url = str(
        base_url
    ).rstrip("/")

    openapi_spec = await fetch_openapi(
        base_url
    )

    paths = openapi_spec.get(
        "paths",
        {}
    )

    endpoints = []

    for path, path_item in paths.items():

        if not isinstance(
            path_item,
            dict,
        ):
            continue

        for method in SUPPORTED_METHODS:

            operation = path_item.get(
                method
            )

            if not operation:
                continue

            endpoint = _build_endpoint_definition(
                path=path,
                method=method,
                operation=operation,
                path_item=path_item,
                openapi_spec=openapi_spec,
            )

            endpoints.append(
                endpoint
            )

    info = openapi_spec.get(
        "info",
        {}
    )

    return {
        "base_url": base_url,
        "title": info.get(
            "title",
            "",
        ),
        "version": info.get(
            "version",
            "",
        ),
        "openapi_version": openapi_spec.get(
            "openapi",
            "",
        ),
        "endpoints": endpoints,
    }


# =============================================================
# BUILD TOOL
# =============================================================

@router.post("/build-tool")
async def build_tool(
    request: BuildToolRequest,
):
    """
    Build an MCP tool from one discovered REST endpoint.

    The backend URL is dynamic.

    Example:

        base_url:
            http://127.0.0.1:9000

        path:
            /accounts/{account_number}/balance

        method:
            GET
    """

    base_url = str(
        request.base_url
    ).rstrip("/")

    path = "/" + str(
        request.path
    ).lstrip("/")

    method = str(
        request.method
    ).lower()

    if method not in SUPPORTED_METHODS:

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported HTTP method: {method}",
        )

    openapi_spec = await fetch_openapi(
        base_url
    )

    paths = openapi_spec.get(
        "paths",
        {}
    )

    path_item = paths.get(
        path
    )

    if not path_item:

        raise HTTPException(
            status_code=404,
            detail={
                "message": (
                    "API path not found in "
                    "OpenAPI specification"
                ),
                "path": path,
                "base_url": base_url,
            },
        )

    operation = path_item.get(
        method
    )

    if not operation:

        raise HTTPException(
            status_code=404,
            detail={
                "message": (
                    "HTTP method not found "
                    "for API path"
                ),
                "path": path,
                "method": method.upper(),
                "base_url": base_url,
            },
        )

    endpoint = _build_endpoint_definition(
        path=path,
        method=method,
        operation=operation,
        path_item=path_item,
        openapi_spec=openapi_spec,
    )

    tool_name = endpoint["name"]

    # ---------------------------------------------------------
    # MCP Tool Definition
    # ---------------------------------------------------------

    tool_definition = {
        "name": tool_name,

        "description": (
            endpoint.get("description")
            or tool_name
        ),

        "transport": "streamable_http",

        "backend": {
            "type": "REST_API",
            "base_url": base_url,
            "path": path,
            "method": method.upper(),
        },

        "operation_id": (
            endpoint.get("operation_id")
            or tool_name
        ),

        "tags": endpoint.get(
            "tags",
            [],
        ),

        "parameters": endpoint.get(
            "parameters",
            [],
        ),

        "request_body": endpoint.get(
            "request_body"
        ),

        "responses": endpoint.get(
            "responses",
            {},
        ),

        "security": endpoint.get(
            "security",
            [],
        ),
    }

    # ---------------------------------------------------------
    # Register Tool
    # ---------------------------------------------------------

    tool_registry.register(
        tool_definition
    )

    return tool_definition


# =============================================================
# MANUAL REST TOOL REGISTRATION
# =============================================================

@router.post("/register-rest-tool")
async def register_rest_tool(
    payload: dict,
):
    """
    Register a REST API directly without OpenAPI discovery.

    This is useful when the backend doesn't expose
    /openapi.json.
    """

    base_url = payload.get(
        "base_url"
    )

    path = payload.get(
        "path"
    )

    method = payload.get(
        "method"
    )

    if not base_url:
        raise HTTPException(
            status_code=400,
            detail="base_url is required",
        )

    if not path:
        raise HTTPException(
            status_code=400,
            detail="path is required",
        )

    if not method:
        raise HTTPException(
            status_code=400,
            detail="method is required",
        )

    base_url = str(
        base_url
    ).rstrip("/")

    path = "/" + str(
        path
    ).lstrip("/")

    method = str(
        method
    ).upper()

    if method.lower() not in SUPPORTED_METHODS:

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported HTTP method: {method}",
        )

    tool_name = _generate_tool_name(
        method,
        path,
    )

    path_parameters = _extract_path_parameters(
        path
    )

    parameters = _merge_parameters(
        payload.get(
            "parameters",
            [],
        ),
        path_parameters,
    )

    tool_definition = {
        "name": tool_name,

        "description": (
            payload.get(
                "description"
            )
            or f"{method} {path}"
        ),

        "transport": "streamable_http",

        "backend": {
            "type": "REST_API",
            "base_url": base_url,
            "path": path,
            "method": method,
        },

        "operation_id": tool_name,

        "tags": payload.get(
            "tags",
            [],
        ),

        "parameters": parameters,

        "request_body": payload.get(
            "request_body"
        ),

        "responses": payload.get(
            "responses",
            {},
        ),

        "security": payload.get(
            "security",
            [],
        ),
    }

    # ---------------------------------------------------------
    # Register Tool
    # ---------------------------------------------------------

    tool_registry.register(
        tool_definition
    )

    return tool_definition


# =============================================================
# LIST TOOLS
# =============================================================

@router.get("/tools")
async def list_tools():
    """
    Return all registered MCP tools.

    The ToolRegistry is the single source of truth.
    """

    return {
        "tools": tool_registry.list()
    }


# =============================================================
# EXECUTE TOOL
# =============================================================

@router.post(
    "/execute-tool/{tool_name}"
)
async def execute_tool(
    tool_name: str,
    arguments: dict,
):
    """
    Execute a registered REST tool.
    """

    tool = tool_registry.get(
        tool_name
    )

    if not tool:

        raise HTTPException(
            status_code=404,
            detail=f"Tool not found: {tool_name}",
        )

    executor = RestExecutor()

    try:

        result = await executor.execute(
            tool_definition=tool,
            arguments=arguments,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )