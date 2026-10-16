# import httpx


# class RestExecutor:

#     async def execute(
#         self,
#         tool_definition: dict,
#         arguments: dict | None = None,
#     ) -> dict:

#         arguments = arguments or {}

#         backend = tool_definition.get("backend", {})

#         base_url = backend.get("base_url")
#         path = backend.get("path")
#         method = backend.get("method", "GET").upper()

#         if not base_url:
#             raise ValueError(
#                 "Tool backend base_url is missing"
#             )

#         if not path:
#             raise ValueError(
#                 "Tool backend path is missing"
#             )

#         # -----------------------------------------------------
#         # Build URL
#         # -----------------------------------------------------

#         url = (
#             f"{base_url.rstrip('/')}/"
#             f"{path.lstrip('/')}"
#         )

#         # -----------------------------------------------------
#         # Validate required parameters
#         # -----------------------------------------------------

#         parameters = tool_definition.get(
#             "parameters",
#             []
#         )

#         missing_arguments = []

#         for parameter in parameters:

#             name = parameter.get("name")
#             required = parameter.get(
#                 "required",
#                 False
#             )

#             if required and name not in arguments:

#                 missing_arguments.append(name)

#         if missing_arguments:

#             return {
#                 "success": False,
#                 "status_code": 400,
#                 "error": "Missing required arguments",
#                 "missing_arguments": missing_arguments,
#             }

#         # -----------------------------------------------------
#         # Separate parameters
#         # -----------------------------------------------------

#         query_params = {}
#         path_params = {}
#         headers = {}

#         for parameter in parameters:

#             name = parameter.get("name")
#             location = parameter.get("location")

#             if name not in arguments:
#                 continue

#             value = arguments[name]

#             if location == "query":

#                 query_params[name] = value

#             elif location == "path":

#                 path_params[name] = value

#             elif location == "header":

#                 headers[name] = value

#         # -----------------------------------------------------
#         # Replace path parameters
#         # -----------------------------------------------------

#         for name, value in path_params.items():

#             url = url.replace(
#                 "{" + name + "}",
#                 str(value)
#             )

#         # -----------------------------------------------------
#         # Request body
#         # -----------------------------------------------------

#         request_body = None

#         request_body_definition = (
#             tool_definition.get(
#                 "request_body"
#             )
#         )

#         if request_body_definition:

#             content = request_body_definition.get(
#                 "content",
#                 {}
#             )

#             # -------------------------------------------------
#             # Prefer application/json
#             # -------------------------------------------------

#             json_content = content.get(
#                 "application/json"
#             )

#             if json_content:

#                 schema = json_content.get(
#                     "schema",
#                     {}
#                 )

#                 properties = schema.get(
#                     "properties",
#                     {}
#                 )

#                 body_fields = set(
#                     properties.keys()
#                 )

#                 request_body = {
#                     key: value
#                     for key, value in arguments.items()
#                     if key in body_fields
#                 }

#             # -------------------------------------------------
#             # Fallback
#             # -------------------------------------------------

#             elif content:

#                 first_content_type = next(
#                     iter(content)
#                 )

#                 schema = content[
#                     first_content_type
#                 ].get(
#                     "schema",
#                     {}
#                 )

#                 properties = schema.get(
#                     "properties",
#                     {}
#                 )

#                 body_fields = set(
#                     properties.keys()
#                 )

#                 request_body = {
#                     key: value
#                     for key, value in arguments.items()
#                     if key in body_fields
#                 }

#         # -----------------------------------------------------
#         # GET / DELETE usually don't send JSON body
#         # -----------------------------------------------------

#         if method in {"GET", "HEAD"}:

#             request_body = None

#         # -----------------------------------------------------
#         # Execute REST request
#         # -----------------------------------------------------

#         try:

#             async with httpx.AsyncClient(
#                 timeout=60,
#                 follow_redirects=True,
#             ) as client:

#                 response = await client.request(

#                     method=method,

#                     url=url,

#                     params=query_params,

#                     headers=headers,

#                     json=request_body,
#                 )

#         except httpx.RequestError as exc:

#             return {
#                 "success": False,
#                 "status_code": 502,
#                 "error": "Unable to reach backend API",
#                 "details": str(exc),
#             }

#         # -----------------------------------------------------
#         # Parse response
#         # -----------------------------------------------------

#         try:

#             response_data = response.json()

#         except ValueError:

#             response_data = {
#                 "raw": response.text
#             }

#         # -----------------------------------------------------
#         # Determine success
#         # -----------------------------------------------------

#         success = (
#             200 <= response.status_code < 300
#         )

#         # -----------------------------------------------------
#         # Return normalized result
#         # -----------------------------------------------------

#         result = {
#             "success": success,
#             "status_code": response.status_code,
#             "headers": dict(response.headers),
#             "data": response_data,
#         }

#         # -----------------------------------------------------
#         # Add error information
#         # -----------------------------------------------------

#         if not success:

#             result["error"] = (
#                 "Backend API returned "
#                 f"HTTP {response.status_code}"
#             )

#         return result

import re
import httpx


class RestExecutor:

    async def execute(
        self,
        tool_definition: dict,
        arguments: dict | None = None,
    ) -> dict:

        arguments = arguments or {}

        backend = tool_definition.get("backend", {})

        base_url = backend.get("base_url")
        path = backend.get("path")
        method = backend.get("method", "GET").upper()

        if not base_url:
            raise ValueError(
                "Tool backend base_url is missing"
            )

        if not path:
            raise ValueError(
                "Tool backend path is missing"
            )

        # =====================================================
        # Build initial URL
        # =====================================================

        url = (
            f"{base_url.rstrip('/')}/"
            f"{path.lstrip('/')}"
        )

        # =====================================================
        # Validate required parameters
        # =====================================================

        parameters = tool_definition.get(
            "parameters",
            []
        )

        missing_arguments = []

        for parameter in parameters:

            if not isinstance(parameter, dict):
                continue

            name = parameter.get("name")

            if not name:
                continue

            required = parameter.get(
                "required",
                False
            )

            if required and name not in arguments:

                missing_arguments.append(name)

        if missing_arguments:

            return {
                "success": False,
                "status_code": 400,
                "error": "Missing required arguments",
                "missing_arguments": missing_arguments,
            }

        # =====================================================
        # Separate parameters
        #
        # Supports:
        #
        # OpenAPI:
        #     "in": "path"
        #
        # Existing/custom format:
        #     "location": "path"
        # =====================================================

        query_params = {}
        path_params = {}
        headers = {}
        cookies = {}

        for parameter in parameters:

            if not isinstance(parameter, dict):
                continue

            name = parameter.get("name")

            if not name:
                continue

            location = (
                parameter.get("in")
                or parameter.get("location")
            )

            if name not in arguments:
                continue

            value = arguments[name]

            if location == "query":

                query_params[name] = value

            elif location == "path":

                path_params[name] = value

            elif location == "header":

                headers[name] = value

            elif location == "cookie":

                cookies[name] = value

        # =====================================================
        # Replace path parameters
        # =====================================================

        for name, value in path_params.items():

            placeholder = "{" + name + "}"

            url = url.replace(
                placeholder,
                str(value)
            )

        # =====================================================
        # Request body
        #
        # Supports BOTH:
        #
        # 1. Direct JSON Schema
        #
        #    {
        #        "type": "object",
        #        "properties": {
        #            "from_account": {...},
        #            "to_account": {...},
        #            "amount": {...}
        #        }
        #    }
        #
        # 2. OpenAPI request body
        #
        #    {
        #        "content": {
        #            "application/json": {
        #                "schema": {
        #                    "type": "object",
        #                    "properties": {...}
        #                }
        #            }
        #        }
        #    }
        # =====================================================

        request_body = None

        request_body_definition = (
            tool_definition.get("request_body")
        )

        if request_body_definition:

            # =================================================
            # CASE 1:
            # Direct JSON Schema
            # =================================================

            if request_body_definition.get("type") == "object":

                properties = request_body_definition.get(
                    "properties",
                    {}
                )

                if not isinstance(properties, dict):
                    properties = {}

                body_fields = set(
                    properties.keys()
                )

                request_body = {
                    key: value
                    for key, value in arguments.items()
                    if key in body_fields
                }

            # =================================================
            # CASE 2:
            # OpenAPI content format
            # =================================================

            else:

                content = request_body_definition.get(
                    "content",
                    {}
                )

                if not isinstance(content, dict):
                    content = {}

                # =============================================
                # Prefer application/json
                # =============================================

                json_content = content.get(
                    "application/json"
                )

                if isinstance(json_content, dict):

                    schema = json_content.get(
                        "schema",
                        {}
                    )

                    if not isinstance(schema, dict):
                        schema = {}

                    properties = schema.get(
                        "properties",
                        {}
                    )

                    if not isinstance(properties, dict):
                        properties = {}

                    body_fields = set(
                        properties.keys()
                    )

                    request_body = {
                        key: value
                        for key, value in arguments.items()
                        if key in body_fields
                    }

                # =============================================
                # Fallback to first content type
                # =============================================

                elif content:

                    first_content_type = next(
                        iter(content)
                    )

                    first_content = content.get(
                        first_content_type,
                        {}
                    )

                    if not isinstance(
                        first_content,
                        dict
                    ):
                        first_content = {}

                    schema = first_content.get(
                        "schema",
                        {}
                    )

                    if not isinstance(schema, dict):
                        schema = {}

                    properties = schema.get(
                        "properties",
                        {}
                    )

                    if not isinstance(properties, dict):
                        properties = {}

                    body_fields = set(
                        properties.keys()
                    )

                    request_body = {
                        key: value
                        for key, value in arguments.items()
                        if key in body_fields
                    }

        # =====================================================
        # GET / HEAD normally don't send JSON body
        # =====================================================

        if method in {"GET", "HEAD"}:

            request_body = None

        # =====================================================
        # SAFETY CHECK
        #
        # If the URL still contains:
        #
        #     /posts/{id}
        #
        # then a path parameter was not supplied.
        # =====================================================

        unresolved_parameters = (
            _extract_path_parameters(url)
        )

        if unresolved_parameters:

            return {
                "success": False,
                "status_code": 400,
                "error": "Unresolved path parameters",
                "missing_arguments": unresolved_parameters,
                "url": url,
            }

        # =====================================================
        # Debug logging
        # =====================================================

        print()
        print("=" * 80)
        print("REST EXECUTOR")
        print("=" * 80)
        print(f"METHOD       : {method}")
        print(f"URL          : {url}")
        print(f"QUERY PARAMS : {query_params}")
        print(f"HEADERS      : {headers}")
        print(f"COOKIES      : {cookies}")
        print(f"REQUEST BODY : {request_body}")
        print("=" * 80)

        # =====================================================
        # Execute REST request
        # =====================================================

        try:

            async with httpx.AsyncClient(
                timeout=60,
                follow_redirects=True,
            ) as client:

                response = await client.request(
                    method=method,
                    url=url,
                    params=query_params,
                    headers=headers,
                    cookies=cookies,
                    json=request_body,
                )

                print()
                print("REST RESPONSE")
                print("=" * 80)
                print(f"STATUS : {response.status_code}")
                print(f"BODY   : {response.text}")
                print("=" * 80)

        except httpx.RequestError as exc:

            return {
                "success": False,
                "status_code": 502,
                "error": "Unable to reach backend API",
                "details": str(exc),
            }

        # =====================================================
        # Parse response
        # =====================================================

        try:

            response_data = response.json()

        except ValueError:

            response_data = {
                "raw": response.text
            }

        # =====================================================
        # Determine success
        # =====================================================

        success = (
            200 <= response.status_code < 300
        )

        # =====================================================
        # Return normalized result
        # =====================================================

        result = {
            "success": success,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "data": response_data,
        }

        # =====================================================
        # Add error information
        # =====================================================

        if not success:

            result["error"] = (
                "Backend API returned "
                f"HTTP {response.status_code}"
            )

        return result


# =============================================================
# EXTRACT UNRESOLVED PATH PARAMETERS
# =============================================================

def _extract_path_parameters(
    url: str
) -> list[str]:

    """
    Find unresolved placeholders such as:

        /posts/{id}

    Returns:

        ["id"]
    """

    return re.findall(
        r"\{([^{}]+)\}",
        url
    )