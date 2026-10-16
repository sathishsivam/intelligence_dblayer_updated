from __future__ import annotations

from typing import Any


class ResponseGenerator:
    """
    Deterministic response composition layer for AI orchestration.

    Responsibilities:
        - Compose MCP results into user-facing facts.
        - Compose RAG evidence into user-facing supporting information.
        - Combine MCP and RAG results for hybrid responses.
        - Preserve source provenance.
        - Provide deterministic fallback responses.

    This class does NOT:
        - retrieve RAG documents
        - select RAG spaces
        - rank RAG documents
        - calculate relevance scores
        - perform lexical similarity
        - generate query terms
        - contain domain-specific keywords
        - execute MCP tools
        - make authorization decisions

    Retrieval pipeline:

        RAGSelector
            ↓
        EvidenceReranker
            ↓
        EvidenceExtractor
            ↓
        ResponseGenerator
    """

    async def generate(
        self,
        user_query: str,
        intent: str | None = None,
        strategy: str | None = None,
        plan: Any = None,
        execution_result: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate the final orchestration response.

        The method is async because OrchestrationService invokes it
        using await.

        Parameters:
            user_query:
                Original user query.

            intent:
                Planner/inferred intent.

            strategy:
                Selected orchestration strategy.

            plan:
                Optional QueryPlan. Retained for compatibility with
                callers that provide the complete plan.

            execution_result:
                Actual execution result from ExecutionRouter.

        Important:
            Response generation does not perform retrieval,
            ranking, or relevance selection. Those responsibilities
            have already been completed by the retrieval pipeline.
        """

        execution_result = execution_result or {}

        results = execution_result.get(
            "results",
            [],
        )

        if not results:
            return (
                "I could not find any execution result "
                "for your request."
            )

        mcp_results = [
            result
            for result in results
            if result.get("type") == "MCP"
        ]

        rag_results = [
            result
            for result in results
            if result.get("type") == "RAG"
        ]

        response_parts: list[str] = []

        # =========================================================
        # MCP RESULTS
        # =========================================================

        for result in mcp_results:

            if not result.get(
                "success",
                False,
            ):
                continue

            text = self._format_mcp_result(
                result
            )

            if text:
                response_parts.append(
                    text
                )

        # =========================================================
        # RAG RESULTS
        # =========================================================

        for result in rag_results:

            if not result.get(
                "success",
                False,
            ):
                continue

            evidence = (
                self._select_reranked_rag_evidence(
                    rag_result=result,
                )
            )

            if evidence:
                response_parts.append(
                    self._format_rag_evidence(
                        evidence
                    )
                )

        # =========================================================
        # FALLBACK
        # =========================================================

        if not response_parts:

            response_parts.append(
                self._build_fallback_response(
                    execution_result
                )
            )

        return "\n\n".join(
            part
            for part in response_parts
            if part
        )

    # =============================================================
    # MCP
    # =============================================================

    def _format_mcp_result(
        self,
        result: dict[str, Any],
    ) -> str:
        """
        Convert a successful MCP execution result into a
        deterministic human-readable response.

        The method intentionally does not depend on specific
        banking tool names.
        """

        response = result.get(
            "response"
        )

        if (
            isinstance(response, str)
            and response.strip()
        ):
            return response.strip()

        data = result.get(
            "data"
        )

        if data is None:
            data = result.get(
                "result"
            )

        if data is None:
            data = result.get(
                "output"
            )

        if data is None:
            return ""

        if isinstance(data, str):
            return data.strip()

        if isinstance(data, dict):
            return self._format_dict_result(
                data
            )

        if isinstance(data, list):
            return self._format_list_result(
                data
            )

        return str(data)

    def _format_dict_result(
        self,
        data: dict[str, Any],
    ) -> str:
        """
        Deterministically format a dictionary returned by an MCP tool.
        """

        # Prefer a direct human-readable message when supplied
        # by the underlying API.
        for key in (
            "message",
            "description",
            "detail",
        ):
            value = data.get(
                key
            )

            if (
                isinstance(value, str)
                and value.strip()
            ):
                return value.strip()

        parts: list[str] = []

        for key, value in data.items():

            if value is None:
                continue

            label = self._humanize_key(
                key
            )

            if isinstance(value, dict):

                value_text = (
                    self._format_dict_value(
                        value
                    )
                )

            elif isinstance(value, list):

                value_text = (
                    self._format_list_value(
                        value
                    )
                )

            else:

                value_text = str(
                    value
                )

            parts.append(
                f"{label}: {value_text}"
            )

        return "\n".join(parts)

    def _format_list_result(
        self,
        data: list[Any],
    ) -> str:
        """
        Deterministically format a list returned by an MCP tool.
        """

        if not data:
            return ""

        lines: list[str] = []

        for index, item in enumerate(
            data,
            start=1,
        ):

            if isinstance(item, dict):

                formatted = (
                    self._format_dict_value(
                        item
                    )
                )

            elif isinstance(item, list):

                formatted = (
                    self._format_list_value(
                        item
                    )
                )

            else:

                formatted = str(
                    item
                )

            lines.append(
                f"{index}. {formatted}"
            )

        return "\n".join(
            lines
        )

    def _format_dict_value(
        self,
        value: dict[str, Any],
    ) -> str:

        parts: list[str] = []

        for key, item in value.items():

            if item is None:
                continue

            label = self._humanize_key(
                key
            )

            if isinstance(item, dict):

                item_text = (
                    self._format_dict_value(
                        item
                    )
                )

            elif isinstance(item, list):

                item_text = (
                    self._format_list_value(
                        item
                    )
                )

            else:

                item_text = str(
                    item
                )

            parts.append(
                f"{label}: {item_text}"
            )

        return ", ".join(
            parts
        )

    def _format_list_value(
        self,
        value: list[Any],
    ) -> str:

        parts: list[str] = []

        for item in value:

            if isinstance(item, dict):

                parts.append(
                    self._format_dict_value(
                        item
                    )
                )

            elif isinstance(item, list):

                parts.append(
                    self._format_list_value(
                        item
                    )
                )

            else:

                parts.append(
                    str(item)
                )

        return ", ".join(
            parts
        )

    # =============================================================
    # RAG
    # =============================================================

    def _select_reranked_rag_evidence(
        self,
        rag_result: dict[str, Any],
    ) -> list[str]:
        """
        Select evidence from the output of the retrieval pipeline.

        Priority:

            1. EvidenceExtractor.extracted_evidence
            2. RAG document text as fallback

        This method does NOT perform relevance scoring or ranking.
        """

        documents = rag_result.get(
            "documents"
        )

        if not documents:
            documents = rag_result.get(
                "results"
            )

        if not documents:
            return []

        if not isinstance(
            documents,
            list,
        ):
            documents = [
                documents
            ]

        for document in documents:

            if not isinstance(
                document,
                dict,
            ):
                continue

            # -----------------------------------------------------
            # EvidenceExtractor output.
            #
            # This is the preferred source because the extraction
            # stage has already identified the relevant passage.
            # -----------------------------------------------------

            extracted = document.get(
                "extracted_evidence"
            )

            if (
                isinstance(
                    extracted,
                    str,
                )
                and extracted.strip()
            ):

                cleaned = (
                    self._clean_rag_text(
                        extracted
                    )
                )

                if cleaned:
                    return [
                        cleaned
                    ]

            # -----------------------------------------------------
            # Backward-compatible fallback.
            #
            # Older RAG results may not contain extracted_evidence.
            # In that case, use the document content.
            # -----------------------------------------------------

            text = (
                self._extract_single_document_text(
                    document
                )
            )

            if not text:
                continue

            cleaned = (
                self._clean_rag_text(
                    text
                )
            )

            if cleaned:
                return [
                    cleaned
                ]

        return []

    def _extract_single_document_text(
        self,
        document: Any,
    ) -> str:
        """
        Extract text from one RAG document.

        Supports common result shapes produced by the retrieval layer.
        """

        if isinstance(
            document,
            str,
        ):
            return document

        if not isinstance(
            document,
            dict,
        ):
            return ""

        for key in (
            "content",
            "text",
            "page_content",
            "document",
        ):

            value = document.get(
                key
            )

            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            ):
                return value

        return ""

    def _clean_rag_text(
        self,
        text: str,
    ) -> str:
        """
        Clean formatting artifacts without changing the meaning
        or inventing source content.
        """

        if not isinstance(
            text,
            str,
        ):
            return ""

        text = text.replace(
            "\u00ad",
            "",
        )

        # Join words split by PDF line wrapping.
        text = text.replace(
            "-\n",
            "",
        )

        # Normalize remaining whitespace.
        text = " ".join(
            text.split()
        )

        return text.strip()

    def _format_rag_evidence(
        self,
        evidence: list[str],
    ) -> str:
        """
        Format extracted RAG evidence.

        The evidence is already selected by the retrieval pipeline,
        so this method only presents it.
        """

        if not evidence:
            return ""

        cleaned = [
            self._clean_rag_text(
                item
            )
            for item in evidence
            if (
                isinstance(
                    item,
                    str,
                )
                and item.strip()
            )
        ]

        cleaned = [
            item
            for item in cleaned
            if item
        ]

        if not cleaned:
            return ""

        return (
            "Regarding the relevant policy:\n"
            + "\n\n".join(
                cleaned
            )
        )

    # =============================================================
    # FALLBACK
    # =============================================================

    def _build_fallback_response(
        self,
        execution_result: dict[str, Any],
    ) -> str:
        """
        Deterministic fallback when no successful MCP or RAG
        response could be composed.
        """

        errors: list[str] = []

        for result in execution_result.get(
            "results",
            [],
        ):

            error = result.get(
                "error"
            )

            if (
                isinstance(
                    error,
                    str,
                )
                and error.strip()
            ):
                errors.append(
                    error.strip()
                )

        if errors:
            return errors[0]

        return (
            "I could not generate a response "
            "from the available capabilities."
        )

    # =============================================================
    # UTILITIES
    # =============================================================

    def _humanize_key(
        self,
        key: str,
    ) -> str:
        """
        Convert a machine-oriented field name into a readable label.
        """

        if not isinstance(
            key,
            str,
        ):
            return str(key)

        text = key.replace(
            "_",
            " ",
        )

        text = " ".join(
            text.split()
        )

        return (
            text[:1].upper()
            + text[1:]
        )
