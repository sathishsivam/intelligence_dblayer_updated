import re
from typing import Any


class MCPCapabilitySelector:
    """
    Lightweight deterministic MCP capability selector.

    Responsibilities:
        - identify the best MCP tool
        - extract arguments from natural language
        - support path/query/body parameters
        - support read and write operations
        - validate required parameters
        - never execute tools
        - never make authorization decisions

    Authorization, authentication and confirmation remain
    responsibilities of the policy layer.
    """

    def select(
        self,
        query: str,
        capabilities: list[dict[str, Any]],
    ) -> dict[str, Any]:

        normalized_query = query.strip().lower()

        if not normalized_query:
            return {
                "success": False,
                "selected_tool": None,
                "confidence": 0.0,
                "reason": "Empty query",
            }

        mcp_tools = [
            capability
            for capability in capabilities
            if capability.get("type") == "MCP"
        ]

        if not mcp_tools:
            return {
                "success": False,
                "selected_tool": None,
                "confidence": 0.0,
                "reason": "No MCP capabilities available",
            }

        candidates: list[dict[str, Any]] = []

        for tool in mcp_tools:

            score = self._score_tool(
                normalized_query,
                tool,
            )

            if score <= 0:
                continue

            arguments = self._extract_arguments(
                query=normalized_query,
                tool=tool,
            )

            required_parameters = (
                self._get_required_parameters(tool)
            )

            print(
                f"[FAST MCP DEBUG] "
                f"tool={tool.get('name')} "
                f"score={score} "
                f"required={required_parameters} "
                f"arguments={arguments}"
            )
               

            if not self._has_required_arguments(
                required_parameters,
                arguments,
            ):
                missing_required = [
                                 p for p in required_parameters
                                 if p not in arguments
                        ]

                print(
                    f"[FAST MCP DEBUG] REJECTED "
                    f"tool={tool.get('name')} "
                    f"missing_required={missing_required}"
                 )
                continue

            candidates.append(
                {
                    "tool": tool,
                    "score": score,
                    "arguments": arguments,
                }
            )

        if not candidates:
            return {
                "success": False,
                "selected_tool": None,
                "confidence": 0.0,
                "reason": (
                    "No suitable MCP capability found "
                    "with resolvable arguments"
                ),
            }

        candidates.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        best = candidates[0]

        second_score = (
            candidates[1]["score"]
            if len(candidates) > 1
            else 0
        )

        # ---------------------------------------------------------
        # Ambiguity handling
        #
        # Do not reject a strong operation-specific match just
        # because another generic tool also contains words such
        # as "account".
        # ---------------------------------------------------------

        if (
            second_score > 0
            and best["score"] - second_score < 2
            and best["score"] < 10
        ):
            return {
                "success": False,
                "selected_tool": None,
                "confidence": 0.0,
                "reason": "Multiple MCP capabilities matched",
                "candidates": [
                    {
                        "name": item["tool"].get("name"),
                        "score": item["score"],
                        "method": self._get_method(
                            item["tool"]
                        ),
                        "path": self._get_path(
                            item["tool"]
                        ),
                    }
                    for item in candidates[:5]
                ],
            }

        confidence = min(
            0.99,
            0.50 + (best["score"] * 0.08),
        )

        return {
            "success": True,
            "selected_tool": best["tool"],
            "confidence": confidence,
            "reason": "Strong MCP capability match",
            "score": best["score"],
            "arguments": best["arguments"],
        }

    # ============================================================
    # TOOL SCORING
    # ============================================================

    def _score_tool(
        self,
        query: str,
        tool: dict[str, Any],
    ) -> int:

        method = self._get_method(tool)
        path = self._get_path(tool)

        name = str(
            tool.get("name", "")
        ).lower()

        description = str(
            tool.get("description", "")
        ).lower()

        operation_id = str(
            tool.get("operation_id", "")
        ).lower()

        query_tokens = set(
            self._tokens(query)
        )

        searchable_text = " ".join(
            [
                name,
                description,
                path,
                operation_id,
            ]
        )

        tool_tokens = set(
            self._tokens(searchable_text)
        )

        score = 0

        # --------------------------------------------------------
        # 1. Strong operation/action matching
        #
        # Action words should dominate generic words such as
        # "account".
        # --------------------------------------------------------

        operation_patterns = {
            "transfer": {
                "keywords": {
                    "transfer",
                    "send",
                    "payment",
                    "pay",
                },
                "tool_keywords": {
                    "transfer",
                },
                "methods": {
                    "POST",
                },
                "path_keywords": {
                    "transfer",
                },
                "bonus": 12,
            },

            "balance": {
                "keywords": {
                    "balance",
                    "balances",
                    "available",
                },
                "tool_keywords": {
                    "balance",
                },
                "methods": {
                    "GET",
                },
                "path_keywords": {
                    "balance",
                },
                "bonus": 10,
            },

            "create": {
                "keywords": {
                    "create",
                    "add",
                    "register",
                },
                "tool_keywords": {
                    "create",
                    "add",
                },
                "methods": {
                    "POST",
                },
                "path_keywords": set(),
                "bonus": 10,
            },

            "update": {
                "keywords": {
                    "update",
                    "modify",
                    "change",
                },
                "tool_keywords": {
                    "update",
                    "modify",
                },
                "methods": {
                    "PUT",
                    "PATCH",
                },
                "path_keywords": set(),
                "bonus": 10,
            },

            "delete": {
                "keywords": {
                    "delete",
                    "remove",
                    "cancel",
                },
                "tool_keywords": {
                    "delete",
                    "remove",
                },
                "methods": {
                    "DELETE",
                },
                "path_keywords": set(),
                "bonus": 10,
            },
        }

        path_tokens = set(
            self._tokens(path)
        )

        for operation in operation_patterns.values():

            query_action_match = bool(
                query_tokens.intersection(
                    operation["keywords"]
                )
            )

            if not query_action_match:
                continue

            tool_action_match = bool(
                tool_tokens.intersection(
                    operation["tool_keywords"]
                )
            )

            path_match = bool(
                path_tokens.intersection(
                    operation["path_keywords"]
                )
            )

            method_match = (
                method in operation["methods"]
            )

            if tool_action_match:
                score += operation["bonus"]

            if path_match:
                score += 5

            if method_match:
                score += 3

        # --------------------------------------------------------
        # 2. Strong token matching
        #
        # Generic words are deliberately ignored here.
        # --------------------------------------------------------

        ignored_tokens = {
            "account",
            "accounts",
            "number",
            "no",
            "id",
            "from",
            "to",
            "the",
            "a",
            "an",
            "of",
            "for",
            "in",
            "on",
            "with",
            "please",
            "rs",
            "inr",
            "rupees",
            "rupee",
        }

        for token in query_tokens:

            if token in ignored_tokens:
                continue

            if token in tool_tokens:
                score += 2

        # --------------------------------------------------------
        # 3. Generic entity matching
        #
        # Keep this intentionally weak.
        #
        # "account" should not beat "transfer".
        # --------------------------------------------------------

        if query_tokens.intersection(
            {
                "account",
                "accounts",
            }
        ):

            if "account" in tool_tokens:
                score += 1

        # --------------------------------------------------------
        # 4. Parameter compatibility
        #
        # Strong evidence that a tool can actually satisfy the
        # requested operation.
        # --------------------------------------------------------

        parameters = self._get_parameters(tool)

        parameter_names = {
            str(
                parameter.get("name", "")
            ).lower()
            for parameter in parameters
            if isinstance(parameter, dict)
        }

        # Transfer
        if query_tokens.intersection(
            {
                "transfer",
                "send",
                "pay",
                "payment",
            }
        ):

            if "from_account" in parameter_names:
                score += 4

            if "to_account" in parameter_names:
                score += 4

            if "amount" in parameter_names:
                score += 4

        # Balance
        if query_tokens.intersection(
            {
                "balance",
                "balances",
                "available",
            }
        ):

            if "account_number" in parameter_names:
                score += 4

            if "account_id" in parameter_names:
                score += 2

        # Account details
        if query_tokens.intersection(
            {
                "account",
                "accounts",
            }
        ):

            if "account_id" in parameter_names:
                score += 1

            if "account_number" in parameter_names:
                score += 1

        return score

    # ============================================================
    # ARGUMENT EXTRACTION
    # ============================================================

    def _extract_arguments(
        self,
        query: str,
        tool: dict[str, Any],
    ) -> dict[str, Any]:

        arguments: dict[str, Any] = {}

        parameters = self._get_parameters(tool)

        for parameter in parameters:

            name = parameter.get("name")

            if not name:
                continue

            value = self._extract_parameter_value(
                query=query,
                parameter=name,
            )

            if value is None:
                continue

            value = self._convert_value(
                value,
                parameter,
            )

            arguments[name] = value

        return arguments

    def _extract_parameter_value(
        self,
        query: str,
        parameter: str,
    ) -> Any:

        parameter_lower = parameter.lower()

        # --------------------------------------------------------
        # FROM ACCOUNT
        # --------------------------------------------------------

        if parameter_lower in {
            "from_account",
            "source_account",
            "sender_account",
        }:

            patterns = [
                r"\bfrom\s+account\s*"
                r"(?:number|no\.?|id)?\s*"
                r"[:#]?\s*(\d+)\b",

                r"\bfrom\s+"
                r"(?:account\s*)?"
                r"[:#]?\s*(\d+)\b",
            ]

            for pattern in patterns:

                match = re.search(
                    pattern,
                    query,
                    re.IGNORECASE,
                )

                if match:
                    return int(match.group(1))

        # --------------------------------------------------------
        # TO ACCOUNT
        # --------------------------------------------------------

        if parameter_lower in {
            "to_account",
            "destination_account",
            "recipient_account",
        }:

            patterns = [
                r"\bto\s+account\s*"
                r"(?:number|no\.?|id)?\s*"
                r"[:#]?\s*(\d+)\b",

                r"\bto\s+"
                r"(?:account\s*)?"
                r"[:#]?\s*(\d+)\b",
            ]

            for pattern in patterns:

                match = re.search(
                    pattern,
                    query,
                    re.IGNORECASE,
                )

                if match:
                    return int(match.group(1))

        # --------------------------------------------------------
        # ACCOUNT NUMBER / ACCOUNT ID
        # --------------------------------------------------------

        if parameter_lower in {
            "account_number",
            "account_no",
            "account_id",
        }:

            patterns = [
                r"\baccount\s+number\s*"
                r"[:#]?\s*(\d+)\b",

                r"\baccount\s+no\.?\s*"
                r"[:#]?\s*(\d+)\b",

                r"\baccount\s+id\s*"
                r"[:#]?\s*(\d+)\b",

                r"\baccount\s*"
                r"[:#]?\s*(\d+)\b",
            ]

            for pattern in patterns:

                match = re.search(
                    pattern,
                    query,
                    re.IGNORECASE,
                )

                if match:
                    return int(match.group(1))

        # --------------------------------------------------------
        # AMOUNT
        # --------------------------------------------------------

        if parameter_lower in {
            "amount",
            "transfer_amount",
            "payment_amount",
        }:

            patterns = [

                # ₹1000
                r"(?:₹)\s*"
                r"([0-9]+(?:\.[0-9]+)?)\b",

                # Rs 1000 / Rs. 1000 / INR 1000
                r"\b(?:rs\.?|inr)\s*"
                r"([0-9]+(?:\.[0-9]+)?)\b",

                # amount 1000
                r"\bamount\s*"
                r"(?:is|of|:)?\s*"
                r"([0-9]+(?:\.[0-9]+)?)\b",

                # transfer amount of 1000
                r"\b(?:transfer|send|pay)\s+"
                r"(?:an?\s+)?"
                r"amount\s+of\s+"
                r"([0-9]+(?:\.[0-9]+)?)\b",

                # transfer 1000
                r"\b(?:transfer|send|pay)\s+"
                r"([0-9]+(?:\.[0-9]+)?)\b",
            ]

            for pattern in patterns:

                match = re.search(
                    pattern,
                    query,
                    re.IGNORECASE,
                )

                if match:

                    value = match.group(1)

                    if "." in value:
                        return float(value)

                    return int(value)

        # --------------------------------------------------------
        # GENERIC PARAMETER EXTRACTION
        # --------------------------------------------------------

        readable_parameter = (
            parameter_lower.replace(
                "_",
                " ",
            )
        )

        escaped_parameter = re.escape(
            readable_parameter
        )

        patterns = [

            rf"\b{escaped_parameter}\s*"
            rf"[:#]?\s*"
            rf"([A-Za-z0-9_.-]+)\b",

            rf"\b{escaped_parameter}\s+number\s*"
            rf"[:#]?\s*"
            rf"([A-Za-z0-9_.-]+)\b",

            rf"\b{escaped_parameter}\s+id\s*"
            rf"[:#]?\s*"
            rf"([A-Za-z0-9_.-]+)\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                query,
                re.IGNORECASE,
            )

            if match:
                return match.group(1)

        return None

    # ============================================================
    # TYPE CONVERSION
    # ============================================================

    def _convert_value(
        self,
        value: Any,
        parameter: dict[str, Any],
    ) -> Any:

        parameter_type = str(
            parameter.get("type", "")
        ).lower()

        if parameter_type == "integer":

            try:
                return int(value)
            except (
                TypeError,
                ValueError,
            ):
                return value

        if parameter_type in {
            "number",
            "float",
        }:

            try:
                return float(value)
            except (
                TypeError,
                ValueError,
            ):
                return value

        if parameter_type == "boolean":

            if isinstance(value, bool):
                return value

            value_lower = str(
                value
            ).lower()

            if value_lower in {
                "true",
                "yes",
                "1",
            }:
                return True

            if value_lower in {
                "false",
                "no",
                "0",
            }:
                return False

        return value

    # ============================================================
    # PARAMETER HELPERS
    # ============================================================

    def _get_parameters(
        self,
        tool: dict[str, Any],
    ) -> list[dict[str, Any]]:

        parameters = tool.get(
            "parameters",
            [],
        )

        if not isinstance(
            parameters,
            list,
        ):
            return []

        return [
            parameter
            for parameter in parameters
            if isinstance(
                parameter,
                dict,
            )
        ]

    def _get_required_parameters(
        self,
        tool: dict[str, Any],
    ) -> list[str]:

        required: list[str] = []

        for parameter in self._get_parameters(
            tool
        ):

            if not parameter.get(
                "required",
                False,
            ):
                continue

            name = parameter.get(
                "name"
            )

            if name:
                required.append(name)

        return required

    def _has_required_arguments(
        self,
        required_parameters: list[str],
        arguments: dict[str, Any],
    ) -> bool:

        return all(
            parameter in arguments
            for parameter in required_parameters
        )

    # ============================================================
    # TOOL METADATA HELPERS
    # ============================================================

    def _get_method(
        self,
        tool: dict[str, Any],
    ) -> str:

        method = tool.get("method")

        if method:
            return str(method).upper()

        backend = tool.get(
            "backend",
            {},
        )

        if not isinstance(
            backend,
            dict,
        ):
            return "GET"

        return str(
            backend.get(
                "method",
                "GET",
            )
        ).upper()

    def _get_path(
        self,
        tool: dict[str, Any],
    ) -> str:

        path = tool.get("path")

        if path:
            return str(path)

        backend = tool.get(
            "backend",
            {},
        )

        if not isinstance(
            backend,
            dict,
        ):
            return ""

        return str(
            backend.get(
                "path",
                "",
            )
        )

    def _get_path_parameters(
        self,
        path: str,
    ) -> list[str]:

        return re.findall(
            r"\{([^{}]+)\}",
            path,
        )

    # ============================================================
    # TOKENIZATION
    # ============================================================

    def _tokens(
        self,
        text: str,
    ) -> list[str]:

        return re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )
    