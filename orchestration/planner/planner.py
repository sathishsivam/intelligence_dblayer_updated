import json
import re
from typing import Any

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
import time

from .intent_schema import (
    CapabilitySelection,
    CapabilityType,
    QueryPlan,
    Strategy,
)
from .prompts import PLANNER_SYSTEM_PROMPT


class PlannerOutput(BaseModel):
    """
    Intermediate output produced by the LLM planner.

    The model is intentionally permissive. Capability names returned
    by the LLM are treated as hints only and are canonicalized against
    the dynamic capability catalog before QueryPlan is created.
    """

    intent: str

    strategy: Strategy

    capabilities: list[CapabilitySelection] = Field(
        default_factory=list
    )

    requires_authentication: bool = False

    requires_confirmation: bool = False

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    clarification_question: str | None = None


class QueryPlanner:

    def __init__(
        self,
        model_name: str = "qwen3:4b",
    ):
        self.llm = ChatOllama(
            model=model_name,
            temperature=0,
            think=False,
        )
    
        

        self.structured_llm = (
            self.llm.with_structured_output(
                PlannerOutput
            )
        )

    # ============================================================
    # PLAN
    # ============================================================

    def plan(
        self,
        query: str,
        capabilities: list[dict[str, Any]],
        user_context: dict[str, Any] | None = None,
    ) -> QueryPlan:

        capability_text = json.dumps(
            capabilities,
            indent=2,
            ensure_ascii=False,
        )

        context_text = json.dumps(
            user_context or {},
            indent=2,
            ensure_ascii=False,
        )

        prompt = f"""
{PLANNER_SYSTEM_PROMPT}

============================================================
AVAILABLE CAPABILITIES
============================================================

{capability_text}

============================================================
USER CONTEXT
============================================================

{context_text}

============================================================
USER QUERY
============================================================

{query}

============================================================
FINAL PLANNING INSTRUCTIONS
============================================================

Create the execution plan using ONLY the supplied capabilities.

IMPORTANT:

Capability names in AVAILABLE CAPABILITIES are canonical.

Never invent, shorten, rename, reconstruct, or synthesize a
capability name.

For every selected capability, use the exact name supplied in
AVAILABLE CAPABILITIES.

For MCP requests:

1. Select the matching MCP capability from AVAILABLE CAPABILITIES.
2. Copy its exact capability name.
3. Extract all explicitly supplied parameter values.
4. Put those values into capability.arguments.
5. If a required parameter is genuinely missing, use CLARIFICATION.
6. Do NOT use CLARIFICATION merely because authentication or
   confirmation is required.
7. State-changing operations should indicate confirmation is required.
8. Never request authentication credentials, passwords, PINs, OTPs,
   tokens, or other secrets.

For RAG requests:

1. Select the relevant RAG capability/space from AVAILABLE CAPABILITIES.
2. Copy its exact name and space_id when supplied.
3. Do not invent a RAG space.

For hybrid requests:

If the query requires both an operational capability and knowledge/
policy/document evidence, select both capabilities.

For fund transfers:

The canonical intent is:

transfer_funds

NOT:

fund_transfer

For:

"transfer 1000 from account 101 to account 102"

and an available MCP capability representing fund transfer, select
that exact capability and provide:

from_account = 101
to_account = 102
amount = 1000

If a capability is clearly required but its exact catalog name cannot
be selected by the model, the orchestration planner will resolve the
LLM's capability reference against the supplied catalog.

Return only the structured planner output.
"""

        # ========================================================
        # LLM PLANNING
        # ========================================================
        plan_start = time.perf_counter()    
        plan = self.structured_llm.invoke(prompt)
        plan_elapsed = time.perf_counter() - plan_start
        print(
                 f"[TIMING] Structured LLM invoke: "
                 f"{plan_elapsed:.3f}s"
                )

        # ========================================================
        # CANONICAL CAPABILITY RESOLUTION
        # ========================================================
        #
        # IMPORTANT:
        #
        # The LLM is NOT trusted as the source of capability names.
        #
        # It may return:
        #
        #   get_account_balance
        #
        # while the real catalog contains:
        #
        #   get_account_balance_accounts__account_number__balance_get
        #
        # Resolve every selected capability against the catalog.
        # ========================================================

        resolved_capabilities = self._resolve_capabilities(
            query=query,
            selected_capabilities=plan.capabilities,
            available_capabilities=capabilities,
        )

        # ========================================================
        # CAPABILITY REPAIR
        # ========================================================
        #
        # If the model completely omitted capabilities for a clear
        # MCP request, dynamically select one from the catalog.
        #
        # No tool names are hard-coded.
        # ========================================================

        if (
            not resolved_capabilities
            and plan.strategy == Strategy.MCP
        ):
            selected_tool = self._select_mcp_capability(
                query=query,
                capabilities=capabilities,
            )

            if selected_tool is not None:
                arguments = self._extract_arguments(
                    query=query,
                    capability=selected_tool,
                )

                resolved_capabilities = [
                    CapabilitySelection(
                        type=CapabilityType.MCP,
                        name=selected_tool.get(
                            "name",
                            "",
                        ),
                        arguments=arguments,
                        reason=(
                            "Capability selected from "
                            "the registered MCP catalog."
                        ),
                    )
                ]

        # ========================================================
        # STRATEGY NORMALIZATION
        # ========================================================
        #
        # Strategy must reflect the capabilities that will actually
        # execute.
        #
        # Example:
        #
        #   MCP + RAG
        #       ↓
        #   MCP_AND_RAG
        #
        # This prevents the LLM from returning MCP while selecting
        # both MCP and RAG capabilities.
        # ========================================================

        strategy = self._derive_strategy(
            original_strategy=plan.strategy,
            capabilities=resolved_capabilities,
        )

        # ========================================================
        # FINAL VALIDATED PLAN
        # ========================================================

        return QueryPlan(
            intent=plan.intent,
            strategy=strategy,
            capabilities=resolved_capabilities,
            requires_authentication=(
                plan.requires_authentication
            ),
            requires_confirmation=(
                plan.requires_confirmation
            ),
            confidence=plan.confidence,
            clarification_question=(
                plan.clarification_question
            ),
        )

    # ============================================================
    # CAPABILITY RESOLUTION
    # ============================================================

    def _resolve_capabilities(
        self,
        query: str,
        selected_capabilities: list[CapabilitySelection],
        available_capabilities: list[dict[str, Any]],
    ) -> list[CapabilitySelection]:

        resolved: list[CapabilitySelection] = []

        for selected in selected_capabilities:

            canonical = self._resolve_single_capability(
                selected=selected,
                available_capabilities=available_capabilities,
            )

            if canonical is None:
                # Never execute an invented capability.
                continue

            arguments = dict(
                selected.arguments or {}
            )

            # Fill missing arguments from the canonical catalog
            # definition using the actual user query.
            extracted_arguments = self._extract_arguments(
                query=query,
                capability=canonical,
            )

            for key, value in extracted_arguments.items():
                arguments.setdefault(
                    key,
                    value,
                )

            capability_type = self._capability_type(
                canonical
            )

            resolved.append(
                CapabilitySelection(
                    type=capability_type,
                    name=canonical.get(
                        "name",
                        "",
                    ),
                    space_id=canonical.get(
                        "space_id"
                    ),
                    arguments=arguments,
                    reason=(
                        selected.reason
                        or "Resolved from the dynamic capability catalog."
                    ),
                )
            )

        return self._deduplicate_capabilities(
            resolved
        )

    # ============================================================
    # SINGLE CAPABILITY RESOLUTION
    # ============================================================

    def _resolve_single_capability(
        self,
        selected: CapabilitySelection,
        available_capabilities: list[dict[str, Any]],
    ) -> dict[str, Any] | None:

        selected_name = self._normalize(
            selected.name
        )

        selected_type = selected.type.value

        candidates = [
            capability
            for capability in available_capabilities
            if capability.get("type") == selected_type
        ]

        if not candidates:
            return None

        # --------------------------------------------------------
        # 1. Exact canonical name
        # --------------------------------------------------------

        for capability in candidates:

            canonical_name = self._normalize(
                str(
                    capability.get(
                        "name",
                        "",
                    )
                )
            )

            if (
                selected_name
                and selected_name
                == canonical_name
            ):
                return capability

        # --------------------------------------------------------
        # 2. Exact space ID for RAG
        # --------------------------------------------------------

        if selected.space_id:

            for capability in candidates:

                if (
                    capability.get(
                        "space_id"
                    )
                    == selected.space_id
                ):
                    return capability

        # --------------------------------------------------------
        # 3. Catalog-driven fuzzy capability matching
        #
        # The selected name is treated only as a hint.
        #
        # The returned capability ALWAYS comes from the catalog.
        # --------------------------------------------------------

        selected_tokens = set(
            self._tokens(
                selected_name
            )
        )

        if not selected_tokens:
            return None

        scored: list[
            tuple[
                float,
                dict[str, Any]
            ]
        ] = []

        for capability in candidates:

            score = self._capability_name_score(
                selected_tokens=selected_tokens,
                capability=capability,
            )

            if score > 0:
                scored.append(
                    (
                        score,
                        capability,
                    )
                )

        if not scored:
            return None

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best = scored[0]

        # --------------------------------------------------------
        # Never silently resolve an ambiguous capability.
        # --------------------------------------------------------

        if len(scored) > 1:

            second_score = scored[1][0]

            if (
                best_score
                == second_score
            ):
                return None

            if (
                best_score - second_score
                < 1.0
            ):
                return None

        return best

    # ============================================================
    # CAPABILITY NAME SCORE
    # ============================================================

    def _capability_name_score(
        self,
        selected_tokens: set[str],
        capability: dict[str, Any],
    ) -> float:

        name = str(
            capability.get(
                "name",
                "",
            )
        )

        operation_id = str(
            capability.get(
                "operation_id",
                "",
            )
        )

        path = str(
            capability.get(
                "path",
                "",
            )
        )

        description = str(
            capability.get(
                "description",
                "",
            )
        )

        candidate_text = self._normalize(
            " ".join(
                [
                    name,
                    operation_id,
                    path,
                    description,
                ]
            )
        )

        candidate_tokens = set(
            self._tokens(
                candidate_text
            )
        )

        overlap = (
            selected_tokens
            & candidate_tokens
        )

        score = float(
            len(overlap)
        )

        # Stronger match when selected tokens occur in the
        # actual canonical name.
        name_tokens = set(
            self._tokens(
                self._normalize(name)
            )
        )

        name_overlap = (
            selected_tokens
            & name_tokens
        )

        score += (
            len(name_overlap)
            * 2.0
        )

        # Operation ID is also strong evidence.
        operation_tokens = set(
            self._tokens(
                self._normalize(
                    operation_id
                )
            )
        )

        operation_overlap = (
            selected_tokens
            & operation_tokens
        )

        score += (
            len(operation_overlap)
            * 1.5
        )

        return score

    # ============================================================
    # STRATEGY DERIVATION
    # ============================================================

    def _derive_strategy(
        self,
        original_strategy: Strategy,
        capabilities: list[CapabilitySelection],
    ) -> Strategy:

        if (
            original_strategy
            == Strategy.CLARIFICATION
        ):
            return Strategy.CLARIFICATION

        capability_types = {
            capability.type
            for capability in capabilities
        }

        has_mcp = (
            CapabilityType.MCP
            in capability_types
        )

        has_rag = (
            CapabilityType.RAG
            in capability_types
        )

        if has_mcp and has_rag:
            return Strategy.MCP_AND_RAG

        if has_mcp:
            return Strategy.MCP

        if has_rag:
            return Strategy.RAG

        return Strategy.CLARIFICATION

    # ============================================================
    # DYNAMIC MCP CAPABILITY SELECTION
    # ============================================================

    def _select_mcp_capability(
        self,
        query: str,
        capabilities: list[dict[str, Any]],
    ) -> dict[str, Any] | None:

        normalized_query = self._normalize(
            query
        )

        query_tokens = set(
            self._tokens(
                normalized_query
            )
        )

        candidates: list[
            tuple[int, dict[str, Any]]
        ] = []

        for capability in capabilities:

            if capability.get("type") != "MCP":
                continue

            name = capability.get(
                "name",
                "",
            )

            description = capability.get(
                "description",
                "",
            )

            path = capability.get(
                "path",
                "",
            )

            operation_id = capability.get(
                "operation_id",
                "",
            )

            parameter_names = [
                parameter.get(
                    "name",
                    "",
                )
                for parameter in capability.get(
                    "parameters",
                    [],
                )
            ]

            text = " ".join(
                [
                    str(name),
                    str(description),
                    str(path),
                    str(operation_id),
                    " ".join(
                        parameter_names
                    ),
                ]
            )

            capability_tokens = set(
                self._tokens(
                    self._normalize(text)
                )
            )

            overlap = (
                query_tokens
                & capability_tokens
            )

            score = len(overlap)

            if (
                "transfer" in query_tokens
                and "transfer"
                in capability_tokens
            ):
                score += 5

            if (
                "payment" in query_tokens
                and "payment"
                in capability_tokens
            ):
                score += 5

            if (
                "beneficiary" in query_tokens
                and "beneficiary"
                in capability_tokens
            ):
                score += 5

            if (
                "balance" in query_tokens
                and "balance"
                in capability_tokens
            ):
                score += 5

            if (
                "loan" in query_tokens
                and "loan"
                in capability_tokens
            ):
                score += 5

            if score > 0:

                candidates.append(
                    (
                        score,
                        capability,
                    )
                )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_capability = (
            candidates[0]
        )

        if len(candidates) > 1:

            second_score = candidates[1][0]

            if (
                best_score
                == second_score
            ):
                return None

        return best_capability

    # ============================================================
    # ARGUMENT EXTRACTION
    # ============================================================

    def _extract_arguments(
        self,
        query: str,
        capability: dict[str, Any],
    ) -> dict[str, Any]:

        arguments: dict[str, Any] = {}

        normalized_query = self._normalize(
            query
        )

        parameters = capability.get(
            "parameters",
            [],
        )

        for parameter in parameters:

            name = parameter.get(
                "name"
            )

            if not name:
                continue

            value = (
                self._extract_parameter_value(
                    query=query,
                    normalized_query=normalized_query,
                    parameter_name=name,
                    parameter=parameter,
                )
            )

            if value is not None:
                arguments[name] = value

        # --------------------------------------------------------
        # Request body fields
        # --------------------------------------------------------

        request_body = capability.get(
            "request_body"
        )

        if request_body:

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

            for (
                name,
                property_schema,
            ) in properties.items():

                if name in arguments:
                    continue

                value = (
                    self._extract_parameter_value(
                        query=query,
                        normalized_query=normalized_query,
                        parameter_name=name,
                        parameter={
                            "name": name,
                            "schema": property_schema,
                        },
                    )
                )

                if value is not None:
                    arguments[name] = value

        return arguments

    # ============================================================
    # PARAMETER VALUE EXTRACTION
    # ============================================================

    def _extract_parameter_value(
        self,
        query: str,
        normalized_query: str,
        parameter_name: str,
        parameter: dict[str, Any],
    ) -> Any:

        name = parameter_name.lower()

        # --------------------------------------------------------
        # FROM ACCOUNT
        # --------------------------------------------------------

        if (
            name == "from_account"
            or (
                "from" in name
                and "account" in name
            )
        ):

            match = re.search(
                r"from\s+(?:the\s+)?account"
                r"(?:\s+(?:number|no|id))?"
                r"\s*[:=#-]?\s*(\d+)",
                normalized_query,
            )

            if match:
                return int(
                    match.group(1)
                )

        # --------------------------------------------------------
        # TO ACCOUNT
        # --------------------------------------------------------

        if (
            name == "to_account"
            or (
                "to" in name
                and "account" in name
            )
        ):

            match = re.search(
                r"to\s+(?:the\s+)?account"
                r"(?:\s+(?:number|no|id))?"
                r"\s*[:=#-]?\s*(\d+)",
                normalized_query,
            )

            if match:
                return int(
                    match.group(1)
                )

        # --------------------------------------------------------
        # ACCOUNT NUMBER
        #
        # Generic handling for OpenAPI parameters such as:
        #
        # account_number
        # account_no
        # account_id
        #
        # The parameter itself determines that this is an account
        # parameter; no specific tool name is required.
        # --------------------------------------------------------

        if (
            name in {
                "account_number",
                "account_no",
                "account_id",
            }
        ):

            match = re.search(
                r"(?:account"
                r"(?:\s+(?:number|no|id))?"
                r"|a/c)"
                r"\s*[:=#-]?\s*(\d+)",
                normalized_query,
            )

            if match:
                return self._convert_number(
                    match.group(1)
                )

        # --------------------------------------------------------
        # AMOUNT
        # --------------------------------------------------------

        if (
            name == "amount"
            or "amount" in name
        ):

            match = re.search(
                r"(?:transfer|send|pay)\s+"
                r"(?:rs\.?|₹|\$)?\s*"
                r"(\d+(?:\.\d+)?)",
                normalized_query,
            )

            if match:
                return self._convert_number(
                    match.group(1)
                )

        # --------------------------------------------------------
        # Generic numeric parameter
        # --------------------------------------------------------

        schema = parameter.get(
            "schema",
            parameter,
        )

        parameter_type = schema.get(
            "type"
        )

        if parameter_type in {
            "integer",
            "number",
        }:

            match = re.search(
                rf"\b{re.escape(name)}"
                rf"\s*[:=]?\s*"
                rf"(\d+(?:\.\d+)?)\b",
                normalized_query,
            )

            if match:
                return self._convert_number(
                    match.group(1),
                    parameter_type,
                )

        return None

    # ============================================================
    # CAPABILITY TYPE
    # ============================================================

    @staticmethod
    def _capability_type(
        capability: dict[str, Any],
    ) -> CapabilityType:

        value = str(
            capability.get(
                "type",
                ""
            )
        ).upper()

        if value == "MCP":
            return CapabilityType.MCP

        if value == "RAG":
            return CapabilityType.RAG

        raise ValueError(
            f"Unsupported capability type: {value}"
        )

    # ============================================================
    # DEDUPLICATION
    # ============================================================

    @staticmethod
    def _deduplicate_capabilities(
        capabilities: list[CapabilitySelection],
    ) -> list[CapabilitySelection]:

        result: list[
            CapabilitySelection
        ] = []

        seen: set[
            tuple[str, str]
        ] = set()

        for capability in capabilities:

            key = (
                capability.type.value,
                capability.name,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(capability)

        return result

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:

        return re.sub(
            r"\s+",
            " ",
            text.lower().strip(),
        )

    @staticmethod
    def _tokens(
        text: str,
    ) -> list[str]:

        return re.findall(
            r"[a-zA-Z0-9_]+",
            text,
        )

    @staticmethod
    def _convert_number(
        value: str,
        parameter_type: str | None = None,
    ) -> int | float:

        number = float(value)

        if (
            parameter_type == "integer"
            or number.is_integer()
        ):
            return int(number)

        return number


# import json
# import re
# import time
# from typing import Any

# from langchain_ollama import ChatOllama
# from pydantic import BaseModel, Field

# from .intent_schema import (
#     CapabilitySelection,
#     CapabilityType,
#     QueryPlan,
#     Strategy,
# )
# from .prompts import PLANNER_SYSTEM_PROMPT


# class PlannerOutput(BaseModel):
#     """
#     Intermediate output produced by the LLM planner.

#     The model is intentionally permissive. Capability names returned
#     by the LLM are treated as hints only and are canonicalized against
#     the dynamic capability catalog before QueryPlan is created.
#     """

#     intent: str

#     strategy: Strategy

#     capabilities: list[CapabilitySelection] = Field(
#         default_factory=list
#     )

#     requires_authentication: bool = False

#     requires_confirmation: bool = False

#     confidence: float = Field(
#         default=0.0,
#         ge=0.0,
#         le=1.0,
#     )

#     clarification_question: str | None = None


# class QueryPlanner:

#     def __init__(
#         self,
#         model_name: str = "qwen3:4b",
#     ):
#         self.llm = ChatOllama(
#             model=model_name,
#             temperature=0,
#             think=False,
#         )

#         self.structured_llm = (
#             self.llm.with_structured_output(
#                 PlannerOutput
#             )
#         )

#     # ============================================================
#     # PLAN
#     # ============================================================

#     def plan(
#         self,
#         query: str,
#         capabilities: list[dict[str, Any]],
#         user_context: dict[str, Any] | None = None,
#     ) -> QueryPlan:

#         capability_text = json.dumps(
#             capabilities,
#             indent=2,
#             ensure_ascii=False,
#         )

#         context_text = json.dumps(
#             user_context or {},
#             indent=2,
#             ensure_ascii=False,
#         )

#         prompt = f"""
# {PLANNER_SYSTEM_PROMPT}

# ============================================================
# AVAILABLE CAPABILITIES
# ============================================================

# {capability_text}

# ============================================================
# USER CONTEXT
# ============================================================

# {context_text}

# ============================================================
# USER QUERY
# ============================================================

# {query}

# ============================================================
# FINAL PLANNING INSTRUCTIONS
# ============================================================

# Create the execution plan using ONLY the supplied capabilities.

# IMPORTANT:

# Capability names in AVAILABLE CAPABILITIES are canonical.

# Never invent, shorten, rename, reconstruct, or synthesize a
# capability name.

# For every selected capability, use the exact name supplied in
# AVAILABLE CAPABILITIES.

# For MCP requests:

# 1. Select the matching MCP capability from AVAILABLE CAPABILITIES.
# 2. Copy its exact capability name.
# 3. Extract all explicitly supplied parameter values.
# 4. Put those values into capability.arguments.
# 5. If a required parameter is genuinely missing, use CLARIFICATION.
# 6. Do NOT use CLARIFICATION merely because authentication or
#    confirmation is required.
# 7. State-changing operations should indicate confirmation is required.
# 8. Never request authentication credentials, passwords, PINs, OTPs,
#    tokens, or other secrets.

# For RAG requests:

# 1. Select the relevant RAG capability/space from AVAILABLE CAPABILITIES.
# 2. Copy its exact name and space_id when supplied.
# 3. Do not invent a RAG space.

# For hybrid requests:

# If the query requires both an operational capability and knowledge/
# policy/document evidence, select both capabilities.

# For fund transfers:

# The canonical intent is:

# transfer_funds

# NOT:

# fund_transfer

# For:

# "transfer 1000 from account 101 to account 102"

# and an available MCP capability representing fund transfer, select
# that exact capability and provide:

# from_account = 101
# to_account = 102
# amount = 1000

# If a capability is clearly required but its exact catalog name cannot
# be selected by the model, the orchestration planner will resolve the
# LLM's capability reference against the supplied catalog.

# Return only the structured planner output.
# """

#         # ========================================================
#         # DIAGNOSTIC TEST 1: PLAIN LLM
#         # ========================================================
#         #
#         # This is intentionally executed before the structured call.
#         #
#         # PURPOSE:
#         #
#         # Determine whether the latency comes from ChatOllama itself
#         # or specifically from LangChain structured output.
#         #
#         # IMPORTANT:
#         #
#         # This causes TWO LLM calls and is temporary diagnostic code.
#         # Remove this block after the test.
#         # ========================================================

#         plain_start = time.perf_counter()

#         plain_result = self.llm.invoke(prompt)

#         plain_elapsed = (
#             time.perf_counter()
#             - plain_start
#         )

#         print(
#             f"[TIMING] Plain LLM invoke: "
#             f"{plain_elapsed:.3f}s"
#         )

#         print(
#             "[DEBUG] Plain LLM response:"
#         )

#         print(
#             plain_result.content
#         )

#         # ========================================================
#         # DIAGNOSTIC TEST 2: STRUCTURED LLM
#         # ========================================================
#         #
#         # This is the existing planner call.
#         # ========================================================

#         structured_start = time.perf_counter()

#         plan = self.structured_llm.invoke(
#             prompt
#         )

#         structured_elapsed = (
#             time.perf_counter()
#             - structured_start
#         )

#         print(
#             f"[TIMING] Structured LLM invoke: "
#             f"{structured_elapsed:.3f}s"
#         )

#         # ========================================================
#         # CANONICAL CAPABILITY RESOLUTION
#         # ========================================================
#         #
#         # IMPORTANT:
#         #
#         # The LLM is NOT trusted as the source of capability names.
#         #
#         # It may return:
#         #
#         #   get_account_balance
#         #
#         # while the real catalog contains:
#         #
#         #   get_account_balance_accounts__account_number__balance_get
#         #
#         # Resolve every selected capability against the catalog.
#         # ========================================================

#         resolved_capabilities = self._resolve_capabilities(
#             query=query,
#             selected_capabilities=plan.capabilities,
#             available_capabilities=capabilities,
#         )

#         # ========================================================
#         # CAPABILITY REPAIR
#         # ========================================================
#         #
#         # If the model completely omitted capabilities for a clear
#         # MCP request, dynamically select one from the catalog.
#         #
#         # No tool names are hard-coded.
#         # ========================================================

#         if (
#             not resolved_capabilities
#             and plan.strategy == Strategy.MCP
#         ):
#             selected_tool = self._select_mcp_capability(
#                 query=query,
#                 capabilities=capabilities,
#             )

#             if selected_tool is not None:
#                 arguments = self._extract_arguments(
#                     query=query,
#                     capability=selected_tool,
#                 )

#                 resolved_capabilities = [
#                     CapabilitySelection(
#                         type=CapabilityType.MCP,
#                         name=selected_tool.get(
#                             "name",
#                             "",
#                         ),
#                         arguments=arguments,
#                         reason=(
#                             "Capability selected from "
#                             "the registered MCP catalog."
#                         ),
#                     )
#                 ]

#         # ========================================================
#         # STRATEGY NORMALIZATION
#         # ========================================================
#         #
#         # Strategy must reflect the capabilities that will actually
#         # execute.
#         #
#         # Example:
#         #
#         #   MCP + RAG
#         #       ↓
#         #   MCP_AND_RAG
#         #
#         # This prevents the LLM from returning MCP while selecting
#         # both MCP and RAG capabilities.
#         # ========================================================

#         strategy = self._derive_strategy(
#             original_strategy=plan.strategy,
#             capabilities=resolved_capabilities,
#         )

#         # ========================================================
#         # FINAL VALIDATED PLAN
#         # ========================================================

#         return QueryPlan(
#             intent=plan.intent,
#             strategy=strategy,
#             capabilities=resolved_capabilities,
#             requires_authentication=(
#                 plan.requires_authentication
#             ),
#             requires_confirmation=(
#                 plan.requires_confirmation
#             ),
#             confidence=plan.confidence,
#             clarification_question=(
#                 plan.clarification_question
#             ),
#         )

#     # ============================================================
#     # CAPABILITY RESOLUTION
#     # ============================================================

#     def _resolve_capabilities(
#         self,
#         query: str,
#         selected_capabilities: list[CapabilitySelection],
#         available_capabilities: list[dict[str, Any]],
#     ) -> list[CapabilitySelection]:

#         resolved: list[CapabilitySelection] = []

#         for selected in selected_capabilities:

#             canonical = self._resolve_single_capability(
#                 selected=selected,
#                 available_capabilities=available_capabilities,
#             )

#             if canonical is None:
#                 # Never execute an invented capability.
#                 continue

#             arguments = dict(
#                 selected.arguments or {}
#             )

#             # Fill missing arguments from the canonical catalog
#             # definition using the actual user query.
#             extracted_arguments = self._extract_arguments(
#                 query=query,
#                 capability=canonical,
#             )

#             for key, value in extracted_arguments.items():
#                 arguments.setdefault(
#                     key,
#                     value,
#                 )

#             capability_type = self._capability_type(
#                 canonical
#             )

#             resolved.append(
#                 CapabilitySelection(
#                     type=capability_type,
#                     name=canonical.get(
#                         "name",
#                         "",
#                     ),
#                     space_id=canonical.get(
#                         "space_id"
#                     ),
#                     arguments=arguments,
#                     reason=(
#                         selected.reason
#                         or "Resolved from the dynamic capability catalog."
#                     ),
#                 )
#             )

#         return self._deduplicate_capabilities(
#             resolved
#         )

#     # ============================================================
#     # SINGLE CAPABILITY RESOLUTION
#     # ============================================================

#     def _resolve_single_capability(
#         self,
#         selected: CapabilitySelection,
#         available_capabilities: list[dict[str, Any]],
#     ) -> dict[str, Any] | None:

#         selected_name = self._normalize(
#             selected.name
#         )

#         selected_type = selected.type.value

#         candidates = [
#             capability
#             for capability in available_capabilities
#             if capability.get("type") == selected_type
#         ]

#         if not candidates:
#             return None

#         # --------------------------------------------------------
#         # 1. Exact canonical name
#         # --------------------------------------------------------

#         for capability in candidates:

#             canonical_name = self._normalize(
#                 str(
#                     capability.get(
#                         "name",
#                         "",
#                     )
#                 )
#             )

#             if (
#                 selected_name
#                 and selected_name
#                 == canonical_name
#             ):
#                 return capability

#         # --------------------------------------------------------
#         # 2. Exact space ID for RAG
#         # --------------------------------------------------------

#         if selected.space_id:

#             for capability in candidates:

#                 if (
#                     capability.get(
#                         "space_id"
#                     )
#                     == selected.space_id
#                 ):
#                     return capability

#         # --------------------------------------------------------
#         # 3. Catalog-driven fuzzy capability matching
#         #
#         # The selected name is treated only as a hint.
#         #
#         # The returned capability ALWAYS comes from the catalog.
#         # --------------------------------------------------------

#         selected_tokens = set(
#             self._tokens(
#                 selected_name
#             )
#         )

#         if not selected_tokens:
#             return None

#         scored: list[
#             tuple[
#                 float,
#                 dict[str, Any]
#             ]
#         ] = []

#         for capability in candidates:

#             score = self._capability_name_score(
#                 selected_tokens=selected_tokens,
#                 capability=capability,
#             )

#             if score > 0:
#                 scored.append(
#                     (
#                         score,
#                         capability,
#                     )
#                 )

#         if not scored:
#             return None

#         scored.sort(
#             key=lambda item: item[0],
#             reverse=True,
#         )

#         best_score, best = scored[0]

#         # --------------------------------------------------------
#         # Never silently resolve an ambiguous capability.
#         # --------------------------------------------------------

#         if len(scored) > 1:

#             second_score = scored[1][0]

#             if (
#                 best_score
#                 == second_score
#             ):
#                 return None

#             if (
#                 best_score - second_score
#                 < 1.0
#             ):
#                 return None

#         return best

#     # ============================================================
#     # CAPABILITY NAME SCORE
#     # ============================================================

#     def _capability_name_score(
#         self,
#         selected_tokens: set[str],
#         capability: dict[str, Any],
#     ) -> float:

#         name = str(
#             capability.get(
#                 "name",
#                 "",
#             )
#         )

#         operation_id = str(
#             capability.get(
#                 "operation_id",
#                 "",
#             )
#         )

#         path = str(
#             capability.get(
#                 "path",
#                 "",
#             )
#         )

#         description = str(
#             capability.get(
#                 "description",
#                 "",
#             )
#         )

#         candidate_text = self._normalize(
#             " ".join(
#                 [
#                     name,
#                     operation_id,
#                     path,
#                     description,
#                 ]
#             )
#         )

#         candidate_tokens = set(
#             self._tokens(
#                 candidate_text
#             )
#         )

#         overlap = (
#             selected_tokens
#             & candidate_tokens
#         )

#         score = float(
#             len(overlap)
#         )

#         # Stronger match when selected tokens occur in the
#         # actual canonical name.
#         name_tokens = set(
#             self._tokens(
#                 self._normalize(name)
#             )
#         )

#         name_overlap = (
#             selected_tokens
#             & name_tokens
#         )

#         score += (
#             len(name_overlap)
#             * 2.0
#         )

#         # Operation ID is also strong evidence.
#         operation_tokens = set(
#             self._tokens(
#                 self._normalize(
#                     operation_id
#                 )
#             )
#         )

#         operation_overlap = (
#             selected_tokens
#             & operation_tokens
#         )

#         score += (
#             len(operation_overlap)
#             * 1.5
#         )

#         return score

#     # ============================================================
#     # STRATEGY DERIVATION
#     # ============================================================

#     def _derive_strategy(
#         self,
#         original_strategy: Strategy,
#         capabilities: list[CapabilitySelection],
#     ) -> Strategy:

#         if (
#             original_strategy
#             == Strategy.CLARIFICATION
#         ):
#             return Strategy.CLARIFICATION

#         capability_types = {
#             capability.type
#             for capability in capabilities
#         }

#         has_mcp = (
#             CapabilityType.MCP
#             in capability_types
#         )

#         has_rag = (
#             CapabilityType.RAG
#             in capability_types
#         )

#         if has_mcp and has_rag:
#             return Strategy.MCP_AND_RAG

#         if has_mcp:
#             return Strategy.MCP

#         if has_rag:
#             return Strategy.RAG

#         return Strategy.CLARIFICATION

#     # ============================================================
#     # DYNAMIC MCP CAPABILITY SELECTION
#     # ============================================================

#     def _select_mcp_capability(
#         self,
#         query: str,
#         capabilities: list[dict[str, Any]],
#     ) -> dict[str, Any] | None:

#         normalized_query = self._normalize(
#             query
#         )

#         query_tokens = set(
#             self._tokens(
#                 normalized_query
#             )
#         )

#         candidates: list[
#             tuple[int, dict[str, Any]]
#         ] = []

#         for capability in capabilities:

#             if capability.get("type") != "MCP":
#                 continue

#             name = capability.get(
#                 "name",
#                 "",
#             )

#             description = capability.get(
#                 "description",
#                 "",
#             )

#             path = capability.get(
#                 "path",
#                 "",
#             )

#             operation_id = capability.get(
#                 "operation_id",
#                 "",
#             )

#             parameter_names = [
#                 parameter.get(
#                     "name",
#                     "",
#                 )
#                 for parameter in capability.get(
#                     "parameters",
#                     [],
#                 )
#             ]

#             text = " ".join(
#                 [
#                     str(name),
#                     str(description),
#                     str(path),
#                     str(operation_id),
#                     " ".join(
#                         parameter_names
#                     ),
#                 ]
#             )

#             capability_tokens = set(
#                 self._tokens(
#                     self._normalize(text)
#                 )
#             )

#             overlap = (
#                 query_tokens
#                 & capability_tokens
#             )

#             score = len(overlap)

#             if (
#                 "transfer" in query_tokens
#                 and "transfer"
#                 in capability_tokens
#             ):
#                 score += 5

#             if (
#                 "payment" in query_tokens
#                 and "payment"
#                 in capability_tokens
#             ):
#                 score += 5

#             if (
#                 "beneficiary" in query_tokens
#                 and "beneficiary"
#                 in capability_tokens
#             ):
#                 score += 5

#             if (
#                 "balance" in query_tokens
#                 and "balance"
#                 in capability_tokens
#             ):
#                 score += 5

#             if (
#                 "loan" in query_tokens
#                 and "loan"
#                 in capability_tokens
#             ):
#                 score += 5

#             if score > 0:

#                 candidates.append(
#                     (
#                         score,
#                         capability,
#                     )
#                 )

#         if not candidates:
#             return None

#         candidates.sort(
#             key=lambda item: item[0],
#             reverse=True,
#         )

#         best_score, best_capability = (
#             candidates[0]
#         )

#         if len(candidates) > 1:

#             second_score = candidates[1][0]

#             if (
#                 best_score
#                 == second_score
#             ):
#                 return None

#         return best_capability

#     # ============================================================
#     # ARGUMENT EXTRACTION
#     # ============================================================

#     def _extract_arguments(
#         self,
#         query: str,
#         capability: dict[str, Any],
#     ) -> dict[str, Any]:

#         arguments: dict[str, Any] = {}

#         normalized_query = self._normalize(
#             query
#         )

#         parameters = capability.get(
#             "parameters",
#             [],
#         )

#         for parameter in parameters:

#             name = parameter.get(
#                 "name"
#             )

#             if not name:
#                 continue

#             value = (
#                 self._extract_parameter_value(
#                     query=query,
#                     normalized_query=normalized_query,
#                     parameter_name=name,
#                     parameter=parameter,
#                 )
#             )

#             if value is not None:
#                 arguments[name] = value

#         # --------------------------------------------------------
#         # Request body fields
#         # --------------------------------------------------------

#         request_body = capability.get(
#             "request_body"
#         )

#         if request_body:

#             content = request_body.get(
#                 "content",
#                 {},
#             )

#             json_content = content.get(
#                 "application/json",
#                 {},
#             )

#             schema = json_content.get(
#                 "schema",
#                 {},
#             )

#             properties = schema.get(
#                 "properties",
#                 {},
#             )

#             for (
#                 name,
#                 property_schema,
#             ) in properties.items():

#                 if name in arguments:
#                     continue

#                 value = (
#                     self._extract_parameter_value(
#                         query=query,
#                         normalized_query=normalized_query,
#                         parameter_name=name,
#                         parameter={
#                             "name": name,
#                             "schema": property_schema,
#                         },
#                     )
#                 )

#                 if value is not None:
#                     arguments[name] = value

#         return arguments

#     # ============================================================
#     # PARAMETER VALUE EXTRACTION
#     # ============================================================

#     def _extract_parameter_value(
#         self,
#         query: str,
#         normalized_query: str,
#         parameter_name: str,
#         parameter: dict[str, Any],
#     ) -> Any:

#         name = parameter_name.lower()

#         # --------------------------------------------------------
#         # FROM ACCOUNT
#         # --------------------------------------------------------

#         if (
#             name == "from_account"
#             or (
#                 "from" in name
#                 and "account" in name
#             )
#         ):

#             match = re.search(
#                 r"from\s+(?:the\s+)?account"
#                 r"(?:\s+(?:number|no|id))?"
#                 r"\s*[:=#-]?\s*(\d+)",
#                 normalized_query,
#             )

#             if match:
#                 return int(
#                     match.group(1)
#                 )

#         # --------------------------------------------------------
#         # TO ACCOUNT
#         # --------------------------------------------------------

#         if (
#             name == "to_account"
#             or (
#                 "to" in name
#                 and "account" in name
#             )
#         ):

#             match = re.search(
#                 r"to\s+(?:the\s+)?account"
#                 r"(?:\s+(?:number|no|id))?"
#                 r"\s*[:=#-]?\s*(\d+)",
#                 normalized_query,
#             )

#             if match:
#                 return int(
#                     match.group(1)
#                 )

#         # --------------------------------------------------------
#         # ACCOUNT NUMBER
#         #
#         # Generic handling for OpenAPI parameters such as:
#         #
#         # account_number
#         # account_no
#         # account_id
#         #
#         # The parameter itself determines that this is an account
#         # parameter; no specific tool name is required.
#         # --------------------------------------------------------

#         if (
#             name in {
#                 "account_number",
#                 "account_no",
#                 "account_id",
#             }
#         ):

#             match = re.search(
#                 r"(?:account"
#                 r"(?:\s+(?:number|no|id))?"
#                 r"|a/c)"
#                 r"\s*[:=#-]?\s*(\d+)",
#                 normalized_query,
#             )

#             if match:
#                 return self._convert_number(
#                     match.group(1)
#                 )

#         # --------------------------------------------------------
#         # AMOUNT
#         # --------------------------------------------------------

#         if (
#             name == "amount"
#             or "amount" in name
#         ):

#             match = re.search(
#                 r"(?:transfer|send|pay)\s+"
#                 r"(?:rs\.?|₹|\$)?\s*"
#                 r"(\d+(?:\.\d+)?)",
#                 normalized_query,
#             )

#             if match:
#                 return self._convert_number(
#                     match.group(1)
#                 )

#         # --------------------------------------------------------
#         # Generic numeric parameter
#         # --------------------------------------------------------

#         schema = parameter.get(
#             "schema",
#             parameter,
#         )

#         parameter_type = schema.get(
#             "type"
#         )

#         if parameter_type in {
#             "integer",
#             "number",
#         }:

#             match = re.search(
#                 rf"\b{re.escape(name)}"
#                 rf"\s*[:=]?\s*"
#                 rf"(\d+(?:\.\d+)?)\b",
#                 normalized_query,
#             )

#             if match:
#                 return self._convert_number(
#                     match.group(1),
#                     parameter_type,
#                 )

#         return None

#     # ============================================================
#     # CAPABILITY TYPE
#     # ============================================================

#     @staticmethod
#     def _capability_type(
#         capability: dict[str, Any],
#     ) -> CapabilityType:

#         value = str(
#             capability.get(
#                 "type",
#                 ""
#             )
#         ).upper()

#         if value == "MCP":
#             return CapabilityType.MCP

#         if value == "RAG":
#             return CapabilityType.RAG

#         raise ValueError(
#             f"Unsupported capability type: {value}"
#         )

#     # ============================================================
#     # DEDUPLICATION
#     # ============================================================

#     @staticmethod
#     def _deduplicate_capabilities(
#         capabilities: list[CapabilitySelection],
#     ) -> list[CapabilitySelection]:

#         result: list[
#             CapabilitySelection
#         ] = []

#         seen: set[
#             tuple[str, str]
#         ] = set()

#         for capability in capabilities:

#             key = (
#                 capability.type.value,
#                 capability.name,
#             )

#             if key in seen:
#                 continue

#             seen.add(key)
#             result.append(capability)

#         return result

#     # ============================================================
#     # HELPERS
#     # ============================================================

#     @staticmethod
#     def _normalize(
#         text: str,
#     ) -> str:

#         return re.sub(
#             r"\s+",
#             " ",
#             text.lower().strip(),
#         )

#     @staticmethod
#     def _tokens(
#         text: str,
#     ) -> list[str]:

#         return re.findall(
#             r"[a-zA-Z0-9_]+",
#             text,
#         )

#     @staticmethod
#     def _convert_number(
#         value: str,
#         parameter_type: str | None = None,
#     ) -> int | float:

#         number = float(value)

#         if (
#             parameter_type == "integer"
#             or number.is_integer()
#         ):
#             return int(number)

#         return number
