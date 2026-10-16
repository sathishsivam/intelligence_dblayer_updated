import re
from typing import Any


class FastIntentRouter:
    """
    Lightweight first-level intent router.

    Purpose:
        Avoid expensive LLM planning for obvious single-intent queries.

    Possible results:
        RAG
        MCP
        DB
        UNKNOWN

    Important:
        The router does not select a specific MCP tool.
        Specific MCP tool selection is handled by
        MCPCapabilitySelector.

    Fast-path principle:
        Prefer dynamically registered capabilities over
        hardcoded tool names or endpoint names.

    Multi-intent principle:
        If a query contains strong signals for more than one
        capability type, do not force it into a fast path.

        Example:
            "What is my balance for account 101 and what is
             the bank policy for minimum balance?"

        This should return UNKNOWN so that the LLM planner
        can produce an MCP_AND_RAG plan.
    """

    def route(
        self,
        query: str,
        capabilities: list[dict[str, Any]],
    ) -> dict[str, Any]:

        normalized_query = query.strip().lower()

        if not normalized_query:
            return {
                "route": "UNKNOWN",
                "confidence": 0.0,
                "reason": "Empty query",
            }

        available_types = {
            capability.get("type")
            for capability in capabilities
        }

        rag_score = self._score_rag(
            normalized_query
        )

        mcp_score = self._score_mcp(
            normalized_query,
            capabilities,
        )

        db_score = self._score_db(
            normalized_query
        )

        scores = {
            "RAG": rag_score,
            "MCP": mcp_score,
            "DB": db_score,
        }

        # Only consider capability types that actually exist.
        scores = {
            capability_type: score
            for capability_type, score in scores.items()
            if capability_type in available_types
        }

        if not scores:
            return {
                "route": "UNKNOWN",
                "confidence": 0.0,
                "reason": (
                    "No supported capability types available"
                ),
                "scores": scores,
            }

        # ------------------------------------------------------
        # MULTI-INTENT PROTECTION
        #
        # If both MCP and RAG have meaningful signals, do not
        # choose one using the fast router.
        #
        # The planner is responsible for deciding whether the
        # correct strategy is MCP_AND_RAG.
        #
        # Example:
        #
        #   "What is my balance for account 101 and what is
        #    the bank policy for minimum balance?"
        #
        # MCP -> balance
        # RAG -> policy
        #
        # Result:
        #   UNKNOWN -> planner -> MCP_AND_RAG
        # ------------------------------------------------------

        if (
            "MCP" in available_types
            and "RAG" in available_types
            and mcp_score >= 2
            and rag_score >= 2
        ):
            return {
                "route": "UNKNOWN",
                "confidence": 0.0,
                "reason": (
                    "Multiple capability types matched; "
                    "LLM planner required"
                ),
                "scores": scores,
            }

        # ------------------------------------------------------
        # Strong dynamic MCP read signal
        #
        # This is intentionally before the generic ranking.
        #
        # Example:
        #   "What is my current balance for account 101?"
        #
        # If the registered MCP catalog contains a GET
        # capability whose metadata indicates a balance
        # operation, route directly to MCP.
        #
        # No MCP tool name is hardcoded here.
        # ------------------------------------------------------

        if "MCP" in available_types:

            if self._is_dynamic_mcp_read_request(
                normalized_query,
                capabilities,
            ):
                return {
                    "route": "MCP",
                    "confidence": 0.95,
                    "reason": (
                        "Strong read-only MCP capability "
                        "detected from the registered catalog"
                    ),
                    "scores": scores,
                }

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        best_type, best_score = ranked[0]

        second_score = (
            ranked[1][1]
            if len(ranked) > 1
            else 0
        )

        # Require a meaningful signal.
        if best_score < 2:
            return {
                "route": "UNKNOWN",
                "confidence": 0.0,
                "reason": "No strong intent signal",
                "scores": scores,
            }

        # If multiple capability types have similar scores,
        # let the LLM planner handle the ambiguity.
        #
        # Exception:
        # A strong MCP read signal with a dynamically matching
        # GET capability should be allowed to enter the MCP
        # selector path.
        if (
            len(ranked) > 1
            and second_score >= 2
            and (best_score - second_score) < 2
        ):
            if best_type == "MCP":
                return {
                    "route": "MCP",
                    "confidence": min(
                        0.90,
                        0.50 + (best_score * 0.10),
                    ),
                    "reason": (
                        "MCP read capability detected"
                    ),
                    "scores": scores,
                }

            return {
                "route": "UNKNOWN",
                "confidence": 0.0,
                "reason": "Multiple capability types matched",
                "scores": scores,
            }

        confidence = min(
            0.99,
            0.50 + (best_score * 0.10),
        )

        return {
            "route": best_type,
            "confidence": confidence,
            "reason": (
                f"Strong {best_type} language pattern"
            ),
            "scores": scores,
        }

    # ==========================================================
    # RAG
    # ==========================================================

    def _score_rag(
        self,
        query: str,
    ) -> int:

        score = 0

        rag_patterns = [
            r"\bwhat documents\b",
            r"\bwhich documents\b",
            r"\brequired documents\b",
            r"\bdocuments required\b",
            r"\bwhat is required\b",
            r"\bwhat are the requirements\b",
            r"\brequirements for\b",
            r"\bpolicy\b",
            r"\bpolicies\b",
            r"\bguidelines\b",
            r"\bprocedure\b",
            r"\bprocedures\b",
            r"\bprocess\b",
            r"\bexplain\b",
            r"\bhow does\b",
            r"\bhow do i\b",
            r"\bwhat does the policy say\b",
            r"\baccording to\b",
            r"\beligibility\b",
            r"\bcriteria\b",
            r"\bkyc\b",
            r"\bterms and conditions\b",
        ]

        for pattern in rag_patterns:
            if re.search(
                pattern,
                query,
            ):
                score += 2

        return score

    # ==========================================================
    # MCP
    # ==========================================================

    def _score_mcp(
        self,
        query: str,
        capabilities: list[dict[str, Any]],
    ) -> int:

        score = 0

        mcp_capabilities = [
            capability
            for capability in capabilities
            if capability.get("type") == "MCP"
        ]

        if not mcp_capabilities:
            return 0

        # ------------------------------------------------------
        # Action language
        # ------------------------------------------------------

        action_patterns = [
            r"\btransfer\b",
            r"\bsend\b",
            r"\bpay\b",
            r"\bpayment\b",
            r"\bcreate\b",
            r"\bupdate\b",
            r"\bdelete\b",
            r"\bsubmit\b",
            r"\bactivate\b",
            r"\bdeactivate\b",
            r"\block\b",
            r"\bunblock\b",
            r"\bopen\b",
            r"\bclose\b",
        ]

        for pattern in action_patterns:
            if re.search(
                pattern,
                query,
            ):
                score += 2

        # ------------------------------------------------------
        # Read/query language
        #
        # These are intentionally generic.
        # We do NOT assume that "posts", "accounts", etc.
        # belong to any particular tool.
        # ------------------------------------------------------

        read_patterns = [
            r"\bshow\b",
            r"\blist\b",
            r"\bget\b",
            r"\bfetch\b",
            r"\bview\b",
            r"\bdisplay\b",
            r"\bretrieve\b",
        ]

        read_request = any(
            re.search(
                pattern,
                query,
            )
            for pattern in read_patterns
        )

        if read_request:

            # A read request is only considered an MCP signal
            # when there is at least one registered GET
            # capability.
            has_get_capability = any(
                self._is_get_capability(
                    capability
                )
                for capability in mcp_capabilities
            )

            if has_get_capability:
                score += 2

                # --------------------------------------------------
                # Give additional weight when the user's query
                # contains words that appear in the registered
                # MCP capability metadata.
                #
                # This does not select the tool.
                # MCPCapabilitySelector still performs selection.
                # --------------------------------------------------

                query_tokens = set(
                    self._tokens(query)
                )

                metadata_match = False

                for capability in mcp_capabilities:

                    if not self._is_get_capability(
                        capability
                    ):
                        continue

                    metadata = self._capability_text(
                        capability
                    )

                    metadata_tokens = set(
                        self._tokens(metadata)
                    )

                    meaningful_matches = (
                        query_tokens
                        & metadata_tokens
                    )

                    # Ignore generic conversational words.
                    meaningful_matches -= {
                        "show",
                        "me",
                        "the",
                        "a",
                        "an",
                        "please",
                        "get",
                        "list",
                        "fetch",
                        "view",
                        "display",
                        "retrieve",
                    }

                    if meaningful_matches:
                        metadata_match = True
                        break

                if metadata_match:
                    score += 3

        # ------------------------------------------------------
        # Read-only domain language
        #
        # These signals are only promoted to MCP when a matching
        # registered MCP capability exists.
        # ------------------------------------------------------

        read_domain_patterns = [
            r"\bbalance\b",
            r"\bavailable balance\b",
            r"\baccount balance\b",
            r"\bcurrent balance\b",
        ]

        domain_read_request = any(
            re.search(
                pattern,
                query,
            )
            for pattern in read_domain_patterns
        )

        if domain_read_request:

            if self._has_matching_read_capability(
                query,
                mcp_capabilities,
                domain_keywords={
                    "balance",
                    "account",
                },
            ):
                score += 5

        return score

    # ==========================================================
    # DYNAMIC MCP READ FAST PATH
    # ==========================================================

    def _is_dynamic_mcp_read_request(
        self,
        query: str,
        capabilities: list[dict[str, Any]],
    ) -> bool:
        """
        Detect a strong read-only MCP request using only
        dynamically registered MCP capability metadata.

        This method does NOT select a tool.

        Tool selection remains the responsibility of
        MCPCapabilitySelector.
        """

        mcp_capabilities = [
            capability
            for capability in capabilities
            if capability.get("type") == "MCP"
        ]

        if not mcp_capabilities:
            return False

        # ------------------------------------------------------
        # Account balance
        # ------------------------------------------------------

        balance_request = bool(
            re.search(
                r"\bbalance\b",
                query,
            )
        )

        if balance_request:

            if self._has_matching_read_capability(
                query,
                mcp_capabilities,
                domain_keywords={
                    "balance",
                    "account",
                },
            ):
                return True

        return False

    # ==========================================================
    # DYNAMIC CAPABILITY MATCHING
    # ==========================================================

    def _has_matching_read_capability(
        self,
        query: str,
        capabilities: list[dict[str, Any]],
        domain_keywords: set[str],
    ) -> bool:
        """
        Determine whether a read-only MCP capability dynamically
        matches the semantic/domain words in the query.

        No capability name is hardcoded.
        """

        query_tokens = set(
            self._tokens(query)
        )

        domain_match = bool(
            query_tokens & domain_keywords
        )

        if not domain_match:
            return False

        for capability in capabilities:

            if not self._is_get_capability(
                capability
            ):
                continue

            metadata = self._capability_text(
                capability
            )

            metadata_tokens = set(
                self._tokens(metadata)
            )

            # At least one domain term must appear in the
            # registered capability metadata.
            if query_tokens & metadata_tokens & domain_keywords:
                return True

        return False

    # ==========================================================
    # DATABASE
    # ==========================================================

    def _score_db(
        self,
        query: str,
    ) -> int:

        score = 0

        data_patterns = [
            r"\bhow much\b",
            r"\bhow many\b",
            r"\bcount\b",
            r"\btotal\b",
            r"\blist\b",
            r"\bshow me\b",
            r"\bfetch\b",
            r"\bfind\b",
            r"\bsearch\b",
            r"\btransactions\b",
            r"\btransaction\b",
            r"\bbalance\b",
            r"\baccounts\b",
            r"\bcustomers\b",
            r"\bbranches\b",
            r"\breports?\b",
        ]

        for pattern in data_patterns:
            if re.search(
                pattern,
                query,
            ):
                score += 2

        return score

    # ==========================================================
    # HELPERS
    # ==========================================================

    def _is_get_capability(
        self,
        capability: dict[str, Any],
    ) -> bool:

        method = str(
            capability.get(
                "method",
                capability.get(
                    "backend",
                    {},
                ).get(
                    "method",
                    "",
                ),
            )
        ).upper()

        return method == "GET"

    def _is_simple_get_capability(
        self,
        capability: dict[str, Any],
    ) -> bool:

        method = str(
            capability.get(
                "method",
                capability.get(
                    "backend",
                    {},
                ).get(
                    "method",
                    "",
                ),
            )
        ).upper()

        path = str(
            capability.get(
                "path",
                capability.get(
                    "backend",
                    {},
                ).get(
                    "path",
                    "",
                ),
            )
        )

        if method != "GET":
            return False

        # Do not classify tools requiring path parameters
        # as simple fast-path capabilities.
        if "{" in path or "}" in path:
            return False

        return True

    def _capability_text(
        self,
        capability: dict[str, Any],
    ) -> str:

        backend = capability.get(
            "backend",
            {},
        )

        return " ".join(
            [
                str(
                    capability.get(
                        "name",
                        "",
                    )
                ),
                str(
                    capability.get(
                        "description",
                        "",
                    )
                ),
                str(
                    capability.get(
                        "operation_id",
                        "",
                    )
                ),
                str(
                    capability.get(
                        "path",
                        backend.get(
                            "path",
                            "",
                        ),
                    )
                ),
            ]
        ).lower()

    def _tokens(
        self,
        text: str,
    ) -> list[str]:

        return re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )
