from typing import Any

from ..execution.mcp_executor import MCPExecutor
from ..execution.rag_executor import RAGExecutor
from ..retrieval.rag_selector import RAGSelector
from ..retrieval.evidence_reranker import EvidenceReranker
from ..retrieval.evidence_extractor import EvidenceExtractor
from ..planner.intent_schema import CapabilityType, QueryPlan


class ExecutionRouter:
    """
    Routes planned capabilities to their respective executors.

    Architecture:

        Planner
           ↓
        ExecutionRouter
           ├── MCP → MCPExecutor
           │
           └── RAG → RAGSelector
                        ↓
                   EvidenceReranker
                        ↓
                   EvidenceExtractor
                        ↓
                   selected evidence

    Responsibilities:
        - Execute MCP capabilities through MCPExecutor.
        - Retrieve RAG evidence through RAGSelector.
        - Rank retrieved RAG evidence through EvidenceReranker.
        - Extract the most relevant passage through EvidenceExtractor.
        - Preserve retrieval/ranking information for downstream response
          generation and provenance.

    The planner decides the high-level strategy/capability type.
    RAGSelector discovers the best ACTIVE RAG space.
    EvidenceReranker ranks retrieved candidates.
    EvidenceExtractor extracts the relevant passage from the ranked evidence.

    This class does NOT:
        - contain domain-specific keywords
        - select MCP tools using hardcoded tool names
        - select RAG spaces using hardcoded space names
        - generate the final natural-language response
    """

    def __init__(self):
        self.mcp_executor = MCPExecutor()

        self.rag_executor = RAGExecutor()

        self.rag_selector = RAGSelector()

        self.evidence_reranker = EvidenceReranker(
            max_results=3,
        )

        self.evidence_extractor = EvidenceExtractor(
            max_passages=3,
            max_passage_chars=1200,
        )

    async def execute(
        self,
        plan: QueryPlan,
        user_query: str,
    ) -> dict[str, Any]:
        """
        Execute all capabilities selected by the planner.

        MCP capabilities are executed asynchronously.

        RAG capabilities follow:

            RAGSelector
                ↓
            EvidenceReranker
                ↓
            EvidenceExtractor
        """

        results: list[dict[str, Any]] = []

        for capability in plan.capabilities:

            if capability.type == CapabilityType.MCP:
                result = await self._execute_mcp(capability)

            elif capability.type == CapabilityType.RAG:
                result = self._execute_rag(
                    capability,
                    user_query,
                )

            else:
                result = {
                    "success": False,
                    "type": capability.type.value,
                    "name": capability.name,
                    "error": (
                        f"Unsupported capability type: "
                        f"{capability.type}"
                    ),
                }

            results.append(result)

        return {
            "success": (
                all(
                    result.get("success", False)
                    for result in results
                )
                if results
                else False
            ),
            "strategy": plan.strategy.value,
            "intent": plan.intent,
            "results": results,
        }

    async def _execute_mcp(
        self,
        capability,
    ) -> dict[str, Any]:
        """
        Execute one MCP capability.
        """

        result = await self.mcp_executor.execute(
            tool_name=capability.name,
            arguments=capability.arguments,
        )

        return {
            "type": "MCP",
            "name": capability.name,
            **result,
        }

    def _execute_rag(
        self,
        capability,
        user_query: str,
    ) -> dict[str, Any]:
        """
        Execute one RAG capability.

        Retrieval pipeline:

            RAGSelector
                ↓
            EvidenceReranker
                ↓
            EvidenceExtractor
        """

        # ---------------------------------------------------------
        # 1. Retrieve candidate evidence from active RAG spaces
        # ---------------------------------------------------------

        selection = self.rag_selector.search(
            query=user_query,
            top_k_per_space=5,
            final_top_k=5,
        )

        if not selection.get("success", False):
            return {
                "success": False,
                "type": "RAG",
                "name": capability.name,
                "error": selection.get(
                    "error",
                    "RAG retrieval failed",
                ),
                "spaces_searched": selection.get(
                    "spaces_searched",
                    0,
                ),
                "spaces_selected": selection.get(
                    "spaces_selected",
                    [],
                ),
                "space_profiles": selection.get(
                    "space_profiles",
                    [],
                ),
                "results": [],
            }

        selected_spaces = selection.get(
            "spaces_selected",
            [],
        )

        selected_results = selection.get(
            "results",
            [],
        )

        # ---------------------------------------------------------
        # 2. Ensure a relevant RAG space was selected
        # ---------------------------------------------------------

        if not selected_spaces:
            return {
                "success": False,
                "type": "RAG",
                "name": capability.name,
                "error": "No relevant RAG space selected",
                "spaces_searched": selection.get(
                    "spaces_searched",
                    0,
                ),
                "spaces_selected": [],
                "space_profiles": selection.get(
                    "space_profiles",
                    [],
                ),
                "results": [],
            }

        # ---------------------------------------------------------
        # 3. Rank retrieved evidence
        # ---------------------------------------------------------

        reranked_results = self.evidence_reranker.rerank(
            query=user_query,
            documents=selected_results,
        )

        # ---------------------------------------------------------
        # 4. Extract the relevant passage from the
        #    highest-ranked evidence
        # ---------------------------------------------------------

        extracted_results = self.evidence_extractor.extract(
            query=user_query,
            documents=reranked_results,
        )

        print("DEBUG RERANKED:")
        for item in reranked_results:
            print(
                "chunk=",
                item.get("metadata", {}).get("chunk_index"),
                "rerank=",
                item.get("_rerank_score"),
                "content=",
                item.get("content", "")[:300],
            )

        print("DEBUG EXTRACTION SCORES:")

        query_tokens = self.evidence_extractor._query_tokens(user_query)

        for item in reranked_results:
            chunk = item.get("metadata", {}).get("chunk_index")
            text = self.evidence_extractor._extract_text(item)
            units = self.evidence_extractor._split_into_units(
                self.evidence_extractor._clean_text(text)
            )

            print(f"\nCHUNK {chunk}")
            print("NUMBER OF UNITS:", len(units))

            scored = []

            for index, unit in enumerate(units):
                score = self.evidence_extractor._unit_relevance_score(
                    query_tokens,
                    unit,
                )
                if score >= self.evidence_extractor.minimum_overlap:
                    scored.append((score, index, unit))

            scored.sort(reverse=True)

            for score, index, unit in scored[:5]:
                print(
                    f"SCORE={score:.6f} INDEX={index} "
                    f"UNIT={unit[:500]}"
                )
        primary_space = selected_spaces[0]

        # ---------------------------------------------------------
        # 5. Return all useful retrieval information
        #
        # documents/results:
        #     final evidence intended for response generation
        #
        # reranked_results:
        #     ranked evidence before passage extraction
        #
        # retrieved_results:
        #     original RAGSelector output
        # ---------------------------------------------------------

        return {
            "success": True,
            "type": "RAG",
            "name": primary_space,
            "space_name": primary_space,

            "spaces_searched": selection.get(
                "spaces_searched",
                0,
            ),

            "spaces_selected": selected_spaces,

            "space_profiles": selection.get(
                "space_profiles",
                [],
            ),

            "documents": extracted_results,

            "results": extracted_results,

            "errors": selection.get(
                "errors",
                [],
            ),

            "retrieved_results": selected_results,

            "reranked_results": reranked_results,
        }
