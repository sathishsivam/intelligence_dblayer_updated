from typing import Any

from ..planner.intent_schema import CapabilityType, QueryPlan
from .risk_policy import RiskPolicy


class PolicyEngine:
    """
    Evaluates security and confirmation requirements
    for an orchestration plan.

    Policy decisions are derived from the resolved capabilities
    in the plan, rather than relying only on the normalized intent.

    This keeps composite/hybrid intents scalable:
        MCP + RAG
        MCP + MCP
        MCP + RAG + MCP
        etc.

    This layer does not execute tools.
    """

    def evaluate(
        self,
        plan: QueryPlan,
        user_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        user_context = user_context or {}

        # ---------------------------------------------------------
        # 1. Start with the policy for the overall intent.
        #
        # This preserves existing behaviour for simple intents.
        # ---------------------------------------------------------
        intent_policy = RiskPolicy.get_policy(plan.intent)

        requires_authentication = bool(
            intent_policy.get(
                "requires_authentication",
                False,
            )
        )

        requires_confirmation = bool(
            intent_policy.get(
                "requires_confirmation",
                False,
            )
        )

        risk_level = intent_policy.get(
            "risk_level"
        )

        # ---------------------------------------------------------
        # 2. Evaluate each resolved capability independently.
        #
        # This is critical for composite plans.
        #
        # Example:
        #
        #   MCP account_balance
        #   +
        #   RAG banking_policy
        #
        # Even if the composite intent has no explicit policy,
        # account_balance still requires authentication.
        # ---------------------------------------------------------
        capability_policies: list[dict[str, Any]] = []

        for capability in plan.capabilities:

            # RAG capabilities normally have no RiskPolicy entry.
            # Unknown capabilities therefore remain unrestricted
            # unless a policy explicitly exists.
            capability_policy = RiskPolicy.get_policy(
                capability.name
            )

            # If the capability name itself is not a policy key,
            # try the planner's normalized intent only where
            # appropriate for non-MCP capabilities.
            #
            # We intentionally do not infer security from arbitrary
            # tool-name text.
            if (
                capability.type == CapabilityType.RAG
                and not capability_policy
            ):
                capability_policy = {}

            capability_policies.append(
                capability_policy
            )

            requires_authentication = (
                requires_authentication
                or bool(
                    capability_policy.get(
                        "requires_authentication",
                        False,
                    )
                )
            )

            requires_confirmation = (
                requires_confirmation
                or bool(
                    capability_policy.get(
                        "requires_confirmation",
                        False,
                    )
                )
            )

            # Preserve the highest available risk level.
            capability_risk = capability_policy.get(
                "risk_level"
            )

            if capability_risk is not None:
                risk_level = self._higher_risk(
                    risk_level,
                    capability_risk,
                )

        # ---------------------------------------------------------
        # 3. Authentication evaluation
        # ---------------------------------------------------------
        authenticated = bool(
            user_context.get(
                "authenticated",
                False,
            )
        )

        authentication_satisfied = (
            not requires_authentication
            or authenticated
        )

        # ---------------------------------------------------------
        # 4. Confirmation evaluation
        # ---------------------------------------------------------
        confirmation_satisfied = bool(
            user_context.get(
                "confirmation_satisfied",
                False,
            )
        )

        # If nothing requires confirmation, it is automatically
        # satisfied.
        if not requires_confirmation:
            confirmation_satisfied = True

        # ---------------------------------------------------------
        # 5. Final authorization decision
        # ---------------------------------------------------------
        allowed = (
            authentication_satisfied
            and confirmation_satisfied
        )

        return {
            "allowed": allowed,
            "risk_level": risk_level,
            "requires_authentication": (
                requires_authentication
            ),
            "requires_confirmation": (
                requires_confirmation
            ),
            "authentication_satisfied": (
                authentication_satisfied
            ),
            "confirmation_satisfied": (
                confirmation_satisfied
            ),
        }

    @staticmethod
    def _higher_risk(
        current: Any,
        candidate: Any,
    ) -> Any:
        """
        Return the higher of two risk levels.

        RiskLevel is expected to be an Enum whose values represent
        increasing risk. If comparison is not possible, preserve
        the existing value unless it is missing.
        """

        if current is None:
            return candidate

        if candidate is None:
            return current

        try:
            current_value = (
                current.value
                if hasattr(current, "value")
                else str(current)
            )

            candidate_value = (
                candidate.value
                if hasattr(candidate, "value")
                else str(candidate)
            )

            priority = {
                "LOW": 1,
                "MEDIUM": 2,
                "HIGH": 3,
                "CRITICAL": 4,
            }

            if (
                priority.get(
                    candidate_value.upper(),
                    0,
                )
                > priority.get(
                    current_value.upper(),
                    0,
                )
            ):
                return candidate

        except Exception:
            pass

        return current
    