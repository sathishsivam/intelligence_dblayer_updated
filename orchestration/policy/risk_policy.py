from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskPolicy:
    """
    Defines orchestration security requirements by intent category.

    This policy is independent of MCP tool names.

    Composite intents are supported by resolving known policy
    categories contained within the normalized intent.
    """

    POLICIES = {
        "transfer_funds": {
            "risk_level": RiskLevel.HIGH,
            "requires_authentication": True,
            "requires_confirmation": True,
        },
        "payment": {
            "risk_level": RiskLevel.HIGH,
            "requires_authentication": True,
            "requires_confirmation": True,
        },
        "beneficiary_creation": {
            "risk_level": RiskLevel.HIGH,
            "requires_authentication": True,
            "requires_confirmation": True,
        },
        "account_balance": {
            "risk_level": RiskLevel.MEDIUM,
            "requires_authentication": True,
            "requires_confirmation": False,
        },
    }

    DEFAULT_POLICY = {
        "risk_level": RiskLevel.LOW,
        "requires_authentication": False,
        "requires_confirmation": False,
    }

    @classmethod
    def get_policy(cls, intent: str) -> dict:
        """
        Return the applicable policy for an intent.

        Resolution order:

        1. Exact intent match.
        2. Composite intent containing a known policy category.
        3. Default LOW-risk policy.

        Example:

            account_balance
                -> account_balance policy

            get_account_balance_and_policy
                -> account_balance policy

            transfer_funds_and_policy
                -> transfer_funds policy

        This policy works at the intent/category level and does not
        depend on MCP tool names.
        """

        normalized_intent = (
            intent or ""
        ).strip().lower()

        if not normalized_intent:
            return dict(cls.DEFAULT_POLICY)

        # ---------------------------------------------------------
        # 1. Exact match
        # ---------------------------------------------------------
        exact_policy = cls.POLICIES.get(
            normalized_intent
        )

        if exact_policy is not None:
            return dict(exact_policy)

        # ---------------------------------------------------------
        # 2. Composite intent
        #
        # Example:
        #   get_account_balance_and_policy
        #
        # contains:
        #   account_balance
        #
        # Prefer the most specific/longest matching policy key.
        # ---------------------------------------------------------
        matching_policies = [
            (policy_key, policy)
            for policy_key, policy in cls.POLICIES.items()
            if policy_key in normalized_intent
        ]

        if matching_policies:
            _, policy = max(
                matching_policies,
                key=lambda item: len(item[0]),
            )

            return dict(policy)

        # ---------------------------------------------------------
        # 3. Unknown intent
        # ---------------------------------------------------------
        return dict(cls.DEFAULT_POLICY)
