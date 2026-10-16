
from typing import Any
import time

from .models.request import OrchestrationRequest
from .models.response import (
    OrchestrationResponse,
    SourceInfo,
)
from .planner.intent_schema import (
    CapabilitySelection,
    CapabilityType,
    QueryPlan,
    Strategy,
)
from .planner.planner import QueryPlanner
from .registry.capability_registry import CapabilityRegistry
from .router.execution_router import ExecutionRouter
from .router.fast_intent_router import FastIntentRouter
from .execution.mcp_selector import (
    MCPCapabilitySelector,
)
from .policy.policy_engine import PolicyEngine
from .response.response_generator import (
    ResponseGenerator,
)
from .confirmation.service import ConfirmationService


class OrchestrationService:
    """
    Main runtime service for Ask AIZillon AI.

    Responsibilities:

    1. Receive the user's natural-language query.
    2. Load currently available capabilities.
    3. Perform lightweight fast intent routing.
    4. Bypass the LLM planner for obvious RAG queries.
    5. Bypass the LLM planner for safe/simple MCP read queries.
    6. Use the LLM planner for ambiguous or complex queries.
    7. Apply orchestration security/risk policy.
    8. Create transaction-bound confirmations for
       confirmation-required operations.
    9. Execute selected capabilities when policy allows.
    10. Generate a natural-language response from the actual
        execution result.
    11. Return normalized orchestration results.

    Fast MCP read operations use deterministic response
    formatting and therefore do not invoke Ollama.

    Confirmation-required operations use ConfirmationService
    to bind confirmation to the exact server-created
    capability and arguments.
    """

    def __init__(self):

        self.capability_registry = (
            CapabilityRegistry()
        )

        self.fast_intent_router = (
            FastIntentRouter()
        )

        self.mcp_selector = (
            MCPCapabilitySelector()
        )

        self.planner = QueryPlanner()

        self.policy_engine = PolicyEngine()

        self.execution_router = (
            ExecutionRouter()
        )

        self.response_generator = (
            ResponseGenerator()
        )

        self.confirmation_service = (
            ConfirmationService()
        )

    # ==========================================================
    # MAIN PROCESS
    # ==========================================================

    async def process(
        self,
        request: OrchestrationRequest,
    ) -> OrchestrationResponse:

        total_start = time.perf_counter()

        query = request.query.strip()

        if not query:
            return OrchestrationResponse(
                success=False,
                error="Query is required",
            )

        try:

            print("\n" + "=" * 80)
            print("ORCHESTRATION REQUEST")
            print("=" * 80)
            print("QUERY:", query)
            print("=" * 80)

            # ==================================================
            # 1. LOAD CAPABILITIES
            # ==================================================

            capability_start = time.perf_counter()

            capabilities = (
                self.capability_registry
                .get_capabilities()
            )

            capability_time = (
                time.perf_counter()
                - capability_start
            )

            print(
                f"[TIMING] Capability discovery: "
                f"{capability_time:.3f}s"
            )

            # ==================================================
            # 2. FAST INTENT ROUTING
            # ==================================================

            fast_route_start = time.perf_counter()

            fast_route = (
                self.fast_intent_router.route(
                    query=query,
                    capabilities=capabilities,
                )
            )

            fast_route_time = (
                time.perf_counter()
                - fast_route_start
            )

            print(
                f"[TIMING] Fast intent routing: "
                f"{fast_route_time:.3f}s"
            )

            print(
                "[FAST ROUTE]:",
                fast_route,
            )

            # ==================================================
            # 3. FAST RAG PATH
            # ==================================================

            if fast_route.get("route") == "RAG":

                rag_capability_start = (
                    time.perf_counter()
                )

                rag_capability = (
                    self._build_rag_capability(
                        capabilities
                    )
                )

                rag_capability_time = (
                    time.perf_counter()
                    - rag_capability_start
                )

                print(
                    f"[TIMING] RAG capability build: "
                    f"{rag_capability_time:.3f}s"
                )

                if rag_capability is not None:

                    plan = QueryPlan(
                        intent=self._infer_rag_intent(
                            query
                        ),
                        strategy=Strategy.RAG,
                        capabilities=[
                            rag_capability
                        ],
                        requires_authentication=False,
                        requires_confirmation=False,
                        confidence=fast_route.get(
                            "confidence",
                            0.0,
                        ),
                    )

                    execution_start = (
                        time.perf_counter()
                    )

                    execution_result = (
                        await self.execution_router.execute(
                            plan=plan,
                            user_query=query,
                        )
                    )

                    execution_time = (
                        time.perf_counter()
                        - execution_start
                    )

                    print(
                        f"[TIMING] RAG execution: "
                        f"{execution_time:.3f}s"
                    )

                    sources = (
                        self._build_sources(
                            execution_result.get(
                                "results",
                                [],
                            )
                        )
                    )

                    response_start = (
                        time.perf_counter()
                    )

                    response = (
                        await self.response_generator.generate(
                            user_query=query,
                            intent=plan.intent,
                            strategy=plan.strategy.value,
                            execution_result=execution_result,
                        )
                    )

                    response_time = (
                        time.perf_counter()
                        - response_start
                    )

                    print(
                        f"[TIMING] Response generation: "
                        f"{response_time:.3f}s"
                    )

                    total_time = (
                        time.perf_counter()
                        - total_start
                    )

                    print(
                        f"[TIMING] TOTAL: "
                        f"{total_time:.3f}s"
                    )

                    return OrchestrationResponse(
                        success=execution_result.get(
                            "success",
                            False,
                        ),
                        intent=plan.intent,
                        strategy=plan.strategy.value,
                        response=response,
                        sources=sources,
                        requires_authentication=(
                            plan.requires_authentication
                        ),
                        requires_confirmation=(
                            plan.requires_confirmation
                        ),
                        error=(
                            None
                            if execution_result.get(
                                "success",
                                False,
                            )
                            else self._extract_error(
                                execution_result
                            )
                        ),
                    )

            # ==================================================
            # 4. FAST MCP PATH
            # ==================================================

            if fast_route.get("route") == "MCP":

                fast_mcp_start = (
                    time.perf_counter()
                )

                fast_mcp_response = (
                    await self._execute_fast_mcp(
                        query=query,
                        capabilities=capabilities,
                        user_context=request.user_context,
                        session_id=request.session_id,
                    )
                )

                fast_mcp_time = (
                    time.perf_counter()
                    - fast_mcp_start
                )

                print(
                    f"[TIMING] Fast MCP path: "
                    f"{fast_mcp_time:.3f}s"
                )

                if fast_mcp_response is not None:

                    total_time = (
                        time.perf_counter()
                        - total_start
                    )

                    print(
                        f"[TIMING] TOTAL: "
                        f"{total_time:.3f}s"
                    )

                    return fast_mcp_response

            # ==================================================
            # 5. LLM PLANNER PATH
            # ==================================================

            print("\n" + "=" * 80)
            print("CAPABILITIES SENT TO PLANNER")
            print("=" * 80)

            for capability in capabilities:

                print(
                    capability.get("type"),
                    "|",
                    capability.get("name"),
                    "|",
                    capability.get("method"),
                    "|",
                    capability.get("path"),
                )

            print("=" * 80)

            planner_start = time.perf_counter()

            plan = self.planner.plan(
                query=query,
                capabilities=capabilities,
                user_context=request.user_context,
            )

            planner_elapsed = (
                time.perf_counter()
                - planner_start
            )

            print(
                f"[TIMING] Planner execution: "
                f"{planner_elapsed:.3f}s"
            )

            planner_time = (
                time.perf_counter()
                - planner_start
            )

            print(
                f"[TIMING] Planner: "
                f"{planner_time:.3f}s"
            )

            print("\n" + "=" * 80)
            print("PLANNER RAW PLAN")
            print("=" * 80)

            print("PLAN:", plan)

            print(
                "CAPABILITIES COUNT:",
                len(plan.capabilities),
            )

            print(
                "CAPABILITIES:",
                plan.capabilities,
            )

            print("=" * 80)

            # ==================================================
            # 6. HANDLE PLANNER CLARIFICATION
            # ==================================================

            if plan.strategy == Strategy.CLARIFICATION:

                total_time = (
                    time.perf_counter()
                    - total_start
                )

                print(
                    f"[TIMING] TOTAL: "
                    f"{total_time:.3f}s"
                )

                return OrchestrationResponse(
                    success=True,
                    intent=plan.intent,
                    strategy=plan.strategy.value,
                    clarification_question=(
                        plan.clarification_question
                        or "Could you please clarify your request?"
                    ),
                    requires_authentication=(
                        plan.requires_authentication
                    ),
                    requires_confirmation=(
                        plan.requires_confirmation
                    ),
                )

            # ==================================================
            # 7. POLICY CHECK
            # ==================================================

            policy_start = time.perf_counter()

            policy_result = (
                self.policy_engine.evaluate(
                    plan=plan,
                    user_context=request.user_context,
                )
            )

            policy_time = (
                time.perf_counter()
                - policy_start
            )

            print(
                f"[TIMING] Policy evaluation: "
                f"{policy_time:.3f}s"
            )

            print(
                "[POLICY RESULT]:",
                policy_result,
            )

            # --------------------------------------------------
            # Authentication gate
            # --------------------------------------------------

            if not policy_result.get(
                "authentication_satisfied",
                True,
            ):

                total_time = (
                    time.perf_counter()
                    - total_start
                )

                print(
                    f"[TIMING] TOTAL: "
                    f"{total_time:.3f}s"
                )

                return OrchestrationResponse(
                    success=True,
                    intent=plan.intent,
                    strategy=Strategy.CLARIFICATION.value,
                    requires_authentication=True,
                    requires_confirmation=(
                        policy_result.get(
                            "requires_confirmation",
                            False,
                        )
                    ),
                    clarification_question=(
                        "Authentication is required "
                        "for this operation."
                    ),
                )

            # --------------------------------------------------
            # Transaction-bound confirmation gate
            # --------------------------------------------------

            if not policy_result.get(
                "confirmation_satisfied",
                True,
            ):

                confirmation = (
                    self._create_confirmation(
                        plan=plan,
                        session_id=request.session_id,
                    )
                )

                total_time = (
                    time.perf_counter()
                    - total_start
                )

                print(
                    "[CONFIRMATION CREATED]:",
                    confirmation.confirmation_id,
                )

                print(
                    "[CONFIRMATION INTENT]:",
                    confirmation.intent,
                )

                print(
                    "[CONFIRMATION CAPABILITY]:",
                    confirmation.capability_name,
                )

                print(
                    "[CONFIRMATION ARGUMENTS]:",
                    confirmation.arguments,
                )

                print(
                    f"[TIMING] TOTAL: "
                    f"{total_time:.3f}s"
                )

                return OrchestrationResponse(
                    success=True,
                    intent=plan.intent,
                    strategy=Strategy.CLARIFICATION.value,
                    requires_authentication=(
                        policy_result.get(
                            "requires_authentication",
                            False,
                        )
                    ),
                    requires_confirmation=True,
                    confirmation_id=(
                        confirmation.confirmation_id
                    ),
                    clarification_question=(
                        self._build_confirmation_question(
                            plan=plan
                        )
                    ),
                )

            # ==================================================
            # 8. EXECUTE PLANNED CAPABILITIES
            # ==================================================

            print("\n" + "=" * 80)
            print("FINAL PLAN BEFORE EXECUTION")
            print("=" * 80)

            print("INTENT:", plan.intent)
            print("STRATEGY:", plan.strategy)
            print(
                "AUTH:",
                plan.requires_authentication,
            )
            print(
                "CONFIRM:",
                plan.requires_confirmation,
            )

            for capability in plan.capabilities:

                print(
                    "CAPABILITY TYPE:",
                    capability.type,
                )

                print(
                    "CAPABILITY NAME:",
                    capability.name,
                )

                print(
                    "CAPABILITY ARGUMENTS:",
                    capability.arguments,
                )

            print("=" * 80)

            execution_start = time.perf_counter()

            execution_result = (
                await self.execution_router.execute(
                    plan=plan,
                    user_query=query,
                )
            )

            execution_time = (
                time.perf_counter()
                - execution_start
            )

            print(
                f"[TIMING] Capability execution: "
                f"{execution_time:.3f}s"
            )

            # ==================================================
            # 9. BUILD SOURCES
            # ==================================================

            sources_start = time.perf_counter()

            sources = (
                self._build_sources(
                    execution_result.get(
                        "results",
                        [],
                    )
                )
            )

            sources_time = (
                time.perf_counter()
                - sources_start
            )

            print(
                f"[TIMING] Source building: "
                f"{sources_time:.3f}s"
            )

            # ==================================================
            # 10. GENERATE USER-FACING RESPONSE
            # ==================================================

            response_start = time.perf_counter()

            response = (
                await self.response_generator.generate(
                    user_query=query,
                    intent=plan.intent,
                    strategy=plan.strategy.value,
                    execution_result=execution_result,
                )
            )

            response_time = (
                time.perf_counter()
                - response_start
            )

            print(
                f"[TIMING] Response generation: "
                f"{response_time:.3f}s"
            )

            # ==================================================
            # 11. RETURN NORMALIZED RESPONSE
            # ==================================================

            total_time = (
                time.perf_counter()
                - total_start
            )

            print(
                f"[TIMING] TOTAL: "
                f"{total_time:.3f}s"
            )

            print("\n" + "=" * 80)
            print("ORCHESTRATION COMPLETED")
            print("=" * 80)
            print(
                "TOTAL TIME:",
                f"{total_time:.3f}s",
            )
            print("=" * 80)

            return OrchestrationResponse(
                success=execution_result.get(
                    "success",
                    False,
                ),
                intent=plan.intent,
                strategy=plan.strategy.value,
                response=response,
                sources=sources,
                requires_authentication=(
                    plan.requires_authentication
                    and not bool(
                        request.user_context
                        and request.user_context.get(
                            "authenticated",
                            False,
                        )
                    )
                ),
                requires_confirmation=(
                    plan.requires_confirmation
                ),
                error=(
                    None
                    if execution_result.get(
                        "success",
                        False,
                    )
                    else self._extract_error(
                        execution_result
                    )
                ),
            )

        except Exception as exc:

            total_time = (
                time.perf_counter()
                - total_start
            )

            print(
                f"[TIMING] TOTAL BEFORE ERROR: "
                f"{total_time:.3f}s"
            )

            print(
                "ORCHESTRATION ERROR:",
                exc,
            )

            return OrchestrationResponse(
                success=False,
                error=str(exc),
            )

    # ==========================================================
    # CONFIRMATION EXECUTION
    # ==========================================================

    async def confirm(
        self,
        *,
        confirmation_id: str,
        session_id: str | None,
        user_context: dict[str, Any] | None = None,
    ) -> OrchestrationResponse:

        total_start = time.perf_counter()

        user_context = user_context or {}

        print("\n" + "=" * 80)
        print("ORCHESTRATION CONFIRMATION")
        print("=" * 80)
        print(
            "CONFIRMATION ID:",
            confirmation_id,
        )
        print(
            "SESSION ID:",
            session_id,
        )
        print("=" * 80)

        try:

            # ==================================================
            # 1. LOOK UP PENDING CONFIRMATION
            # ==================================================

            confirmation = (
                self.confirmation_service.get(
                    confirmation_id
                )
            )

            if confirmation is None:

                return OrchestrationResponse(
                    success=False,
                    strategy=Strategy.CLARIFICATION.value,
                    error=(
                        "Confirmation is invalid, "
                        "expired, or no longer available."
                    ),
                )

            print(
                "[CONFIRMATION FOUND]:",
                confirmation,
            )

            # ==================================================
            # 2. VALIDATE SESSION
            # ==================================================

            if (
                confirmation.session_id
                != session_id
            ):

                return OrchestrationResponse(
                    success=False,
                    intent=confirmation.intent,
                    strategy=Strategy.CLARIFICATION.value,
                    error=(
                        "Confirmation does not belong "
                        "to this session."
                    ),
                )

            # ==================================================
            # 3. AUTHENTICATION CHECK
            # ==================================================

            authenticated = bool(
                user_context.get(
                    "authenticated",
                    False,
                )
            )

            if not authenticated:

                return OrchestrationResponse(
                    success=True,
                    intent=confirmation.intent,
                    strategy=Strategy.CLARIFICATION.value,
                    requires_authentication=True,
                    requires_confirmation=True,
                    confirmation_id=(
                        confirmation_id
                    ),
                    clarification_question=(
                        "Authentication is required "
                        "for this operation."
                    ),
                )

            # ==================================================
            # 4. CONSUME CONFIRMATION
            #
            # This makes the confirmation one-time-use.
            #
            # The exact arguments come from the server-side
            # confirmation record, NOT from the client.
            # ==================================================

            consumed = (
                self.confirmation_service.consume(
                    confirmation_id=confirmation_id,
                    session_id=session_id,
                )
            )

            if consumed is None:

                return OrchestrationResponse(
                    success=False,
                    intent=confirmation.intent,
                    strategy=Strategy.CLARIFICATION.value,
                    error=(
                        "Confirmation is invalid, "
                        "expired, or has already been used."
                    ),
                )

            print(
                "[CONFIRMATION CONSUMED]:",
                consumed.confirmation_id,
            )

            print(
                "[CONFIRMED INTENT]:",
                consumed.intent,
            )

            print(
                "[CONFIRMED CAPABILITY]:",
                consumed.capability_name,
            )

            print(
                "[CONFIRMED ARGUMENTS]:",
                consumed.arguments,
            )

            # ==================================================
            # 5. REBUILD EXACT CAPABILITY
            #
            # The capability and arguments are taken from the
            # server-side confirmation record.
            # ==================================================

            capability = CapabilitySelection(
                type=CapabilityType.MCP,
                name=consumed.capability_name,
                arguments=dict(
                    consumed.arguments
                ),
                reason=(
                    "Confirmed transaction-bound "
                    "operation"
                ),
            )

            # ==================================================
            # 6. REBUILD EXECUTION PLAN
            # ==================================================

            plan = QueryPlan(
                intent=consumed.intent,
                strategy=Strategy.MCP,
                capabilities=[
                    capability
                ],
                requires_authentication=True,
                requires_confirmation=True,
            )

            print("\n" + "=" * 80)
            print("CONFIRMED PLAN")
            print("=" * 80)
            print(
                "INTENT:",
                plan.intent,
            )
            print(
                "STRATEGY:",
                plan.strategy,
            )
            print(
                "CAPABILITY:",
                capability.name,
            )
            print(
                "ARGUMENTS:",
                capability.arguments,
            )
            print("=" * 80)

            # ==================================================
            # 7. RE-EVALUATE POLICY
            #
            # confirmation_satisfied=True is NOT supplied by
            # the client.
            #
            # It is created internally only after the
            # ConfirmationService validates and consumes the
            # server-side confirmation.
            # ==================================================

            policy_result = (
                self.policy_engine.evaluate(
                    plan=plan,
                    user_context={
                        **user_context,
                        "confirmation_satisfied": True,
                    },
                )
            )

            print(
                "[CONFIRMATION POLICY]:",
                policy_result,
            )

            # ==================================================
            # 8. AUTHENTICATION GATE
            # ==================================================

            if not policy_result.get(
                "authentication_satisfied",
                True,
            ):

                return OrchestrationResponse(
                    success=True,
                    intent=plan.intent,
                    strategy=Strategy.CLARIFICATION.value,
                    requires_authentication=True,
                    requires_confirmation=True,
                    clarification_question=(
                        "Authentication is required "
                        "for this operation."
                    ),
                )

            # ==================================================
            # 9. EXECUTE EXACT CONFIRMED OPERATION
            # ==================================================

            execution_start = time.perf_counter()

            execution_result = (
                await self.execution_router.execute(
                    plan=plan,
                    user_query=(
                        self._build_confirmation_execution_query(
                            confirmation=consumed
                        )
                    ),
                )
            )

            execution_time = (
                time.perf_counter()
                - execution_start
            )

            print(
                f"[TIMING] Confirmed execution: "
                f"{execution_time:.3f}s"
            )

            # ==================================================
            # 10. BUILD SOURCES
            # ==================================================

            sources = (
                self._build_sources(
                    execution_result.get(
                        "results",
                        [],
                    )
                )
            )

            # ==================================================
            # 11. BUILD DETERMINISTIC MCP RESPONSE
            # ==================================================

            response = (
                self._build_fast_mcp_response(
                    execution_result=execution_result,
                    intent=plan.intent,
                )
            )

            total_time = (
                time.perf_counter()
                - total_start
            )

            print(
                f"[TIMING] CONFIRM TOTAL: "
                f"{total_time:.3f}s"
            )

            print("\n" + "=" * 80)
            print("CONFIRMED OPERATION COMPLETED")
            print("=" * 80)

            return OrchestrationResponse(
                success=execution_result.get(
                    "success",
                    False,
                ),
                intent=plan.intent,
                strategy=Strategy.MCP.value,
                response=response,
                sources=sources,
                requires_authentication=False,
                requires_confirmation=True,
                error=(
                    None
                    if execution_result.get(
                        "success",
                        False,
                    )
                    else self._extract_error(
                        execution_result
                    )
                ),
            )

        except Exception as exc:

            total_time = (
                time.perf_counter()
                - total_start
            )

            print(
                f"[TIMING] CONFIRM TOTAL BEFORE ERROR: "
                f"{total_time:.3f}s"
            )

            print(
                "CONFIRMATION ERROR:",
                exc,
            )

            return OrchestrationResponse(
                success=False,
                error=str(exc),
            )

    # ==========================================================
    # CREATE TRANSACTION-BOUND CONFIRMATION
    # ==========================================================

    def _create_confirmation(
        self,
        *,
        plan: QueryPlan,
        session_id: str | None,
    ):

        capability = (
            plan.capabilities[0]
            if plan.capabilities
            else None
        )

        capability_name = (
            capability.name
            if capability is not None
            else plan.intent
        )

        arguments = (
            capability.arguments
            if capability is not None
            else {}
        )

        if not isinstance(arguments, dict):
            arguments = {}

        return self.confirmation_service.create(
            session_id=session_id,
            intent=plan.intent,
            capability_name=capability_name,
            arguments=dict(arguments),
        )

    # ==========================================================
    # BUILD CONFIRMATION EXECUTION QUERY
    # ==========================================================

    def _build_confirmation_execution_query(
        self,
        confirmation,
    ) -> str:

        arguments = (
            confirmation.arguments
            if isinstance(
                confirmation.arguments,
                dict,
            )
            else {}
        )

        if (
            confirmation.intent
            == "transfer_funds"
        ):

            from_account = arguments.get(
                "from_account"
            )

            to_account = arguments.get(
                "to_account"
            )

            amount = arguments.get(
                "amount"
            )

            return (
                f"Transfer {amount} from account "
                f"{from_account} to account "
                f"{to_account}."
            )

        return (
            f"Execute confirmed operation "
            f"{confirmation.capability_name}."
        )

    # ==========================================================
    # FAST MCP EXECUTION
    # ==========================================================

    async def _execute_fast_mcp(
        self,
        query: str,
        capabilities: list[dict[str, Any]],
        user_context: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> OrchestrationResponse | None:

        # ------------------------------------------------------
        # 1. Dynamically select MCP capability
        # ------------------------------------------------------

        selection_start = time.perf_counter()

        selection = (
            self.mcp_selector.select(
                query=query,
                capabilities=capabilities,
            )
        )

        selection_time = (
            time.perf_counter()
            - selection_start
        )

        print(
            f"[TIMING] MCP capability selection: "
            f"{selection_time:.3f}s"
        )

        print(
            "[FAST MCP SELECTION]:",
            selection,
        )

        if not selection.get("success"):
            return None

        tool = selection.get("selected_tool")

        if not tool:
            return None

        tool_name = tool.get("name")

        if not tool_name:
            return None

        # ------------------------------------------------------
        # 2. Preserve arguments extracted by selector
        # ------------------------------------------------------

        arguments = selection.get(
            "arguments",
            {},
        )

        if not isinstance(arguments, dict):
            arguments = {}

        print(
            "[FAST MCP ARGUMENTS]:",
            arguments,
        )

        # ------------------------------------------------------
        # 3. Infer policy intent
        # ------------------------------------------------------

        intent = self._infer_fast_mcp_intent(
            query=query,
            tool=tool,
        )

        print(
            "[FAST MCP INTENT]:",
            intent,
        )

        # ------------------------------------------------------
        # 4. Build MCP capability
        # ------------------------------------------------------

        capability = (
            self._build_mcp_capability(
                tool=tool,
                arguments=arguments,
                confidence=selection.get(
                    "confidence",
                    0.0,
                ),
                reason=selection.get(
                    "reason",
                    "Fast MCP capability selection",
                ),
            )
        )

        # ------------------------------------------------------
        # 5. Build plan
        # ------------------------------------------------------

        plan = QueryPlan(
            intent=intent,
            strategy=Strategy.MCP,
            capabilities=[capability],
            requires_authentication=False,
            requires_confirmation=False,
            confidence=selection.get(
                "confidence",
                0.0,
            ),
        )

        # ------------------------------------------------------
        # 6. Policy evaluation
        # ------------------------------------------------------

        policy_start = time.perf_counter()

        policy_result = (
            self.policy_engine.evaluate(
                plan=plan,
                user_context=user_context,
            )
        )

        policy_time = (
            time.perf_counter()
            - policy_start
        )

        print(
            f"[TIMING] Fast MCP policy evaluation: "
            f"{policy_time:.3f}s"
        )

        print(
            "[FAST MCP POLICY]:",
            policy_result,
        )

        # ------------------------------------------------------
        # Authentication gate
        # ------------------------------------------------------

        if not policy_result.get(
            "authentication_satisfied",
            True,
        ):

            return OrchestrationResponse(
                success=True,
                intent=plan.intent,
                strategy=Strategy.CLARIFICATION.value,
                requires_authentication=True,
                requires_confirmation=(
                    policy_result.get(
                        "requires_confirmation",
                        False,
                    )
                ),
                clarification_question=(
                    "Authentication is required "
                    "for this operation."
                ),
            )

        # ------------------------------------------------------
        # Transaction-bound confirmation gate
        # ------------------------------------------------------

        if not policy_result.get(
            "confirmation_satisfied",
            True,
        ):

            confirmation = (
                self._create_confirmation(
                    plan=plan,
                    session_id=session_id,
                )
            )

            print(
                "[FAST MCP CONFIRMATION CREATED]:",
                confirmation.confirmation_id,
            )

            return OrchestrationResponse(
                success=True,
                intent=plan.intent,
                strategy=Strategy.CLARIFICATION.value,
                requires_authentication=(
                    policy_result.get(
                        "requires_authentication",
                        False,
                    )
                ),
                requires_confirmation=True,
                confirmation_id=(
                    confirmation.confirmation_id
                ),
                clarification_question=(
                    self._build_confirmation_question(
                        plan=plan,
                    )
                ),
            )

        # ------------------------------------------------------
        # 7. Execute selected MCP capability
        # ------------------------------------------------------

        execution_start = time.perf_counter()

        execution_result = (
            await self.execution_router.execute(
                plan=plan,
                user_query=query,
            )
        )

        execution_time = (
            time.perf_counter()
            - execution_start
        )

        print(
            f"[TIMING] Fast MCP execution: "
            f"{execution_time:.3f}s"
        )

        # ------------------------------------------------------
        # 8. Build sources
        # ------------------------------------------------------

        sources_start = time.perf_counter()

        sources = (
            self._build_sources(
                execution_result.get(
                    "results",
                    [],
                )
            )
        )

        sources_time = (
            time.perf_counter()
            - sources_start
        )

        print(
            f"[TIMING] Fast MCP source building: "
            f"{sources_time:.3f}s"
        )

        # ------------------------------------------------------
        # 9. Deterministic response
        #
        # IMPORTANT:
        # Do NOT invoke ResponseGenerator here.
        #
        # Simple successful MCP GET operations should not need
        # an LLM just to turn structured JSON into a sentence.
        # ------------------------------------------------------

        response_start = time.perf_counter()

        response = (
            self._build_fast_mcp_response(
                execution_result=execution_result,
                intent=plan.intent,
            )
        )

        response_time = (
            time.perf_counter()
            - response_start
        )

        print(
            f"[TIMING] Fast MCP response formatting: "
            f"{response_time:.3f}s"
        )

        return OrchestrationResponse(
            success=execution_result.get(
                "success",
                False,
            ),
            intent=plan.intent,
            strategy=plan.strategy.value,
            response=response,
            sources=sources,
            # Authentication may be required by policy, but once the
            # current user has satisfied that requirement, the UI must not
            # display another authentication prompt.
            requires_authentication=(
                policy_result.get(
                    "requires_authentication",
                    False,
                )
                and not policy_result.get(
                    "authentication_satisfied",
                    False,
                )
            ),
            requires_confirmation=(
                policy_result.get(
                    "requires_confirmation",
                    False,
                )
            ),
            error=(
                None
                if execution_result.get(
                    "success",
                    False,
                )
                else self._extract_error(
                    execution_result
                )
            ),
        )

    # ==========================================================
    # FAST MCP RESPONSE FORMATTER
    # ==========================================================

    def _build_fast_mcp_response(
        self,
        execution_result: dict[str, Any],
        intent: str | None = None,
    ) -> str:

        """
        Build a user-facing response without an LLM.

        This formatter uses ONLY data returned by the executed
        MCP capability.

        It deliberately does not:
            - invent values
            - call Ollama
            - inspect planner prompts
            - make policy decisions
            - execute tools
            - infer missing banking data
        """

        if not execution_result:
            return "The operation did not return a result."

        success = execution_result.get(
            "success",
            False,
        )

        if not success:
            return self._build_fast_mcp_failure_response(
                execution_result
            )

        results = execution_result.get(
            "results",
            [],
        )

        if not results:
            return (
                "The operation completed, "
                "but no result details were returned."
            )

        # ------------------------------------------------------
        # Inspect successful result data.
        #
        # We intentionally use the returned data rather than
        # the MCP tool name.
        # ------------------------------------------------------

        for result in results:

            if not result.get(
                "success",
                False,
            ):
                continue

            data = result.get("data")

            if not isinstance(data, dict):
                continue

            # --------------------------------------------------
            # Account balance
            #
            # This is metadata/data driven rather than based on
            # the registered MCP tool name.
            # --------------------------------------------------

            if (
                "account_number" in data
                and "balance" in data
            ):

                account_number = data.get(
                    "account_number"
                )

                balance = data.get(
                    "balance"
                )

                currency = data.get(
                    "currency"
                )

                if (
                    account_number is not None
                    and balance is not None
                ):

                    formatted_balance = (
                        self._format_amount(
                            amount=balance,
                            currency=currency,
                        )
                    )

                    return (
                        f"Account {account_number} "
                        f"balance: {formatted_balance}"
                    )

            # --------------------------------------------------
            # Generic message returned by MCP
            # --------------------------------------------------

            message = data.get("message")

            if message:
                return str(message)

        # ------------------------------------------------------
        # Safe generic success response
        # ------------------------------------------------------

        return (
            "The operation completed successfully."
        )

    # ==========================================================
    # FAST MCP FAILURE RESPONSE
    # ==========================================================

    def _build_fast_mcp_failure_response(
        self,
        execution_result: dict[str, Any],
    ) -> str:

        errors = []

        for result in execution_result.get(
            "results",
            [],
        ):

            if result.get(
                "success",
                False,
            ):
                continue

            error = result.get(
                "error"
            )

            if error:
                errors.append(
                    str(error)
                )

        if errors:

            return (
                "The operation could not be completed. "
                + " ".join(errors)
            )

        return (
            "The operation could not be completed."
        )

    # ==========================================================
    # FORMAT AMOUNT
    # ==========================================================

    def _format_amount(
        self,
        amount: Any,
        currency: Any = None,
    ) -> str:

        """
        Format an amount using the currency returned by the
        actual MCP response.

        No currency is assumed when the backend does not provide
        one.
        """

        try:

            numeric_amount = float(
                amount
            )

            if numeric_amount.is_integer():

                formatted_number = (
                    f"{int(numeric_amount):,}"
                )

            else:

                formatted_number = (
                    f"{numeric_amount:,.2f}"
                )

        except (
            TypeError,
            ValueError,
        ):

            formatted_number = str(
                amount
            )

        currency_value = (
            str(currency).upper()
            if currency is not None
            else ""
        )

        currency_symbols = {
            "INR": "₹",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
        }

        symbol = currency_symbols.get(
            currency_value
        )

        if symbol:

            return (
                f"{symbol}{formatted_number}"
            )

        if currency_value:

            return (
                f"{formatted_number} "
                f"{currency_value}"
            )

        return formatted_number

    # ==========================================================
    # FAST MCP INTENT INFERENCE
    # ==========================================================

    def _infer_fast_mcp_intent(
        self,
        query: str,
        tool: dict[str, Any],
    ) -> str:

        """
        Infer a lightweight intent for the fast MCP path.

        This is deliberately lexical and metadata-driven.

        It does not call an LLM and does not depend on a
        hard-coded MCP tool name.
        """

        query_tokens = set(
            self._tokens(query)
        )

        tool_text = " ".join(
            [
                str(tool.get("name", "")),
                str(tool.get("description", "")),
                str(tool.get("path", "")),
                str(tool.get("operation_id", "")),
            ]
        ).lower()

        tool_tokens = set(
            self._tokens(tool_text)
        )

        has_account = bool(
            query_tokens.intersection(
                {
                    "account",
                    "accounts",
                }
            )
        )

        has_balance = bool(
            query_tokens.intersection(
                {
                    "balance",
                    "balances",
                }
            )
        )

        capability_is_balance = (
            "balance" in tool_tokens
        )

        if (
            has_account
            and has_balance
            and capability_is_balance
        ):
            return "account_balance"

        return (
            f"execute_"
            f"{tool.get('name', 'mcp_capability')}"
        )

    # ==========================================================
    # TOKENIZATION
    # ==========================================================

    def _tokens(
        self,
        text: str,
    ) -> list[str]:

        import re

        return re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )

    # ==========================================================
    # BUILD MCP CAPABILITY
    # ==========================================================

    def _build_mcp_capability(
        self,
        tool: dict[str, Any],
        arguments: dict[str, Any],
        confidence: float,
        reason: str,
    ) -> CapabilitySelection:

        return CapabilitySelection(
            type=CapabilityType.MCP,
            name=tool.get(
                "name",
                "",
            ),
            arguments=arguments,
            reason=reason,
        )

    # ==========================================================
    # BUILD RAG CAPABILITY
    # ==========================================================

    def _build_rag_capability(
        self,
        capabilities: list[dict[str, Any]],
    ) -> CapabilitySelection | None:

        rag_capabilities = [
            capability
            for capability in capabilities
            if capability.get("type") == "RAG"
        ]

        if not rag_capabilities:
            return None

        capability = rag_capabilities[0]

        return CapabilitySelection(
            type=CapabilityType.RAG,
            name=capability.get(
                "name",
                "RAG",
            ),
            space_id=None,
            arguments={},
            reason="Fast intent router selected RAG",
        )

    # ==========================================================
    # RAG INTENT INFERENCE
    # ==========================================================

    def _infer_rag_intent(
        self,
        query: str,
    ) -> str:

        normalized_query = query.lower()

        if (
            "document" in normalized_query
            and (
                "required" in normalized_query
                or "need" in normalized_query
            )
        ):
            return "document_requirements"

        if (
            "kyc" in normalized_query
            or "know your customer" in normalized_query
        ):
            return "kyc_information"

        if (
            "policy" in normalized_query
            or "policies" in normalized_query
        ):
            return "policy_information"

        if (
            "procedure" in normalized_query
            or "procedures" in normalized_query
        ):
            return "procedure_information"

        if (
            "requirement" in normalized_query
            or "requirements" in normalized_query
        ):
            return "requirements_information"

        return "knowledge_query"

    # ==========================================================
    # BUILD CONFIRMATION QUESTION
    # ==========================================================

    def _build_confirmation_question(
        self,
        plan: QueryPlan,
    ) -> str:

        if plan.intent == "transfer_funds":

            capability = (
                plan.capabilities[0]
                if plan.capabilities
                else None
            )

            arguments = (
                capability.arguments
                if capability is not None
                else {}
            )

            from_account = arguments.get(
                "from_account"
            )

            to_account = arguments.get(
                "to_account"
            )

            amount = arguments.get(
                "amount"
            )

            if (
                from_account is not None
                and to_account is not None
                and amount is not None
            ):

                return (
                    f"Please confirm the transfer "
                    f"of {amount} from account "
                    f"{from_account} to account "
                    f"{to_account}."
                )

            return (
                "Please confirm the fund transfer "
                "before it is executed."
            )

        return (
            "Please confirm this operation "
            "before it is executed."
        )

    # ==========================================================
    # BUILD UI-FACING SOURCES
    # ==========================================================

    def _build_sources(
        self,
        results: list[dict[str, Any]],
    ) -> list[SourceInfo]:
        """
        Build the compact source contract returned to the UI.

        Execution results can contain internal orchestration data such as
        retrieved documents, reranked candidates, space profiles, HTTP
        headers, and diagnostic scores. Those details are useful internally
        but should not be exposed wholesale through the normal API response.

        The UI source contract therefore contains only the provenance needed
        to explain where the answer came from.
        """

        sources: list[SourceInfo] = []

        for result in results:

            result_type = str(
                result.get("type") or ""
            ).upper()

            if not result_type:
                continue

            if result_type == "MCP":
                source = self._build_mcp_source(result)

            elif result_type == "RAG":
                source = self._build_rag_source(result)

            else:
                # Preserve support for future capability types without
                # exposing their complete internal execution result.
                source = SourceInfo(
                    type=result_type,
                    name=str(
                        result.get("name", "unknown")
                    ),
                    metadata={},
                )

            if source is not None:
                sources.append(source)

        return sources

    # ==========================================================
    # BUILD MCP SOURCE
    # ==========================================================

    def _build_mcp_source(
        self,
        result: dict[str, Any],
    ) -> SourceInfo:
        """
        Build a compact UI source for a live MCP execution.

        Only the HTTP status is exposed as normal source metadata. Response
        headers and other REST executor details are intentionally kept out of
        the user-facing contract.
        """

        metadata: dict[str, Any] = {}

        status_code = result.get("status_code")

        if status_code is not None:
            metadata["status_code"] = status_code

        return SourceInfo(
            type="MCP",
            name=str(
                result.get("name", "unknown")
            ),
            metadata=metadata,
        )

    # ==========================================================
    # BUILD RAG SOURCE
    # ==========================================================

    def _build_rag_source(
        self,
        result: dict[str, Any],
    ) -> SourceInfo | None:
        """
        Build a compact UI source from the selected RAG evidence.

        ``documents``/``results`` contain the evidence selected by the
        EvidenceExtractor, while ``reranked_results`` contains the ordered
        candidates used to establish the relevance rank.

        The backend assigns the rank so Flutter does not need to understand
        the reranking implementation.
        """

        documents = result.get("documents")

        if not isinstance(documents, list) or not documents:
            documents = result.get("results")

        if not isinstance(documents, list) or not documents:
            # A failed/empty RAG execution may still have useful space-level
            # information. Return a minimal source rather than exposing the
            # internal execution result.
            space_name = (
                result.get("space_name")
                or result.get("name")
                or "RAG"
            )

            return SourceInfo(
                type="RAG",
                name=str(space_name),
                metadata={
                    "space_name": str(space_name),
                },
            )

        primary_document = documents[0]

        if not isinstance(primary_document, dict):
            return None

        reranked_results = result.get(
            "reranked_results",
            [],
        )

        if not isinstance(reranked_results, list):
            reranked_results = []

        rank = self._find_rag_rank(
            document=primary_document,
            reranked_results=reranked_results,
        )

        document_metadata = primary_document.get(
            "metadata",
            {},
        )

        if not isinstance(document_metadata, dict):
            document_metadata = {}

        matching_reranked_document = (
            self._find_matching_reranked_document(
                document=primary_document,
                reranked_results=reranked_results,
            )
        )

        relevance_score = None

        if matching_reranked_document is not None:
            relevance_score = matching_reranked_document.get(
                "_rerank_score"
            )

        if relevance_score is None:
            relevance_score = primary_document.get(
                "_rerank_score"
            )

        evidence = primary_document.get(
            "extracted_evidence"
    )

        # Fall back to the document content only when an extractor result
        # is unavailable. This keeps the source useful for older RAG results
        # while preferring the focused evidence produced by EvidenceExtractor.
        if evidence is None:
            evidence = primary_document.get("content")

        space_name = (
            primary_document.get("space_name")
            or result.get("space_name")
            or result.get("name")
            or "RAG"
        )

        metadata: dict[str, Any] = {
            "rank": rank,
            "space_name": str(space_name),
            "document_id": document_metadata.get("document_id"),
            "file_name": document_metadata.get("file_name"),
            "page_number": document_metadata.get("page_number"),
            "chunk_index": document_metadata.get("chunk_index"),
            "relevance_score": relevance_score,
            "evidence": evidence,
        }

        # Remove fields whose value is unavailable rather than returning a
        # JSON object full of null values.
        metadata = {
            key: value
            for key, value in metadata.items()
            if value is not None
        }

        return SourceInfo(
            type="RAG",
            name=str(space_name),
            metadata=metadata,
        )

    # ==========================================================
    # FIND RAG RANK
    # ==========================================================

    def _find_rag_rank(
        self,
        document: dict[str, Any],
        reranked_results: list[dict[str, Any]],
    ) -> int:
        """
        Find the backend-assigned relevance rank of a selected RAG document.

        Document identity is matched using document_id + chunk_index first,
        then file_name + chunk_index as a compatibility fallback.
        """

        matching_document = (
            self._find_matching_reranked_document(
                document=document,
                reranked_results=reranked_results,
            )
        )

        if matching_document is None:
            return 1

        for index, candidate in enumerate(
            reranked_results,
            start=1,
        ):
            if candidate is matching_document:
                return index

        return 1

    # ==========================================================
    # FIND MATCHING RERANKED DOCUMENT
    # ==========================================================

    def _find_matching_reranked_document(
        self,
        document: dict[str, Any],
        reranked_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Match an extracted document back to its reranked candidate.
        """

        target_metadata = document.get(
            "metadata",
            {},
        )

        if not isinstance(target_metadata, dict):
            target_metadata = {}

        target_document_id = target_metadata.get(
            "document_id"
        )

        target_chunk_index = target_metadata.get(
            "chunk_index"
        )

        target_file_name = target_metadata.get(
            "file_name"
        )

        for candidate in reranked_results:

            if not isinstance(candidate, dict):
                continue

            candidate_metadata = candidate.get(
                "metadata",
                {},
            )

            if not isinstance(candidate_metadata, dict):
                continue

            candidate_document_id = candidate_metadata.get(
                "document_id"
            )

            candidate_chunk_index = candidate_metadata.get(
                "chunk_index"
            )

            candidate_file_name = candidate_metadata.get(
                "file_name"
            )

            # Strong identity match.
            if (
                target_document_id
                and candidate_document_id
                == target_document_id
                and target_chunk_index is not None
                and candidate_chunk_index
                == target_chunk_index
            ):
                return candidate

            # Compatibility fallback for results where document_id is not
            # present but file_name and chunk_index are available.
            if (
                target_file_name
                and candidate_file_name
                == target_file_name
                and target_chunk_index is not None
                and candidate_chunk_index
                == target_chunk_index
            ):
                return candidate

        return None

    # ==========================================================
    # EXTRACT EXECUTION ERROR
    # ==========================================================

    def _extract_error(
        self,
        execution_result: dict[str, Any],
    ) -> str | None:

        errors = []

        for result in execution_result.get(
            "results",
            [],
        ):

            if not result.get(
                "success",
                False,
            ):

                error = result.get(
                    "error"
                )

                if error:

                    errors.append(
                        f"{result.get('name', 'capability')}: "
                        f"{error}"
                    )

        if not errors:

            return "Capability execution failed"

        return "; ".join(errors)
