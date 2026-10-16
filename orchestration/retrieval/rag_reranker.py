import json
from typing import Any

from langchain_ollama import ChatOllama


class RAGReranker:
    """
    Reranks RAG candidate chunks using semantic relevance.

    FAISS retrieves candidate chunks.
    Qwen3:4B evaluates all candidates in a single LLM call.

    Higher relevance score means stronger semantic relevance.
    """

    def __init__(
        self,
        model_name: str = "qwen3:4b",
    ):
        self.llm = ChatOllama(
            model=model_name,
            temperature=0,
        )

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:

        if not query or not query.strip():
            return []

        if not candidates:
            return []

        valid_candidates = [
            candidate
            for candidate in candidates
            if candidate.get("content", "").strip()
        ]

        if not valid_candidates:
            return []

        evaluations = self._evaluate_batch(
            query=query.strip(),
            candidates=valid_candidates,
        )

        reranked: list[dict[str, Any]] = []

        for index, candidate in enumerate(valid_candidates):

            evaluation = evaluations.get(
                index,
                {
                    "relevant": False,
                    "score": 0.0,
                    "reason": "",
                },
            )

            reranked.append(
                {
                    **candidate,
                    "relevance": evaluation["relevant"],
                    "relevance_score": evaluation["score"],
                    "relevance_reason": evaluation["reason"],
                }
            )

        reranked.sort(
            key=lambda item: (
                item.get("relevance_score", 0.0)
            ),
            reverse=True,
        )

        return reranked[:top_k]

    def _evaluate_batch(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:

        candidate_text_parts = []

        for index, candidate in enumerate(candidates):

            content = candidate.get(
                "content",
                "",
            ).strip()

            candidate_text_parts.append(
                f"""
CANDIDATE {index}

{content}
""".strip()
            )

        candidate_text = "\n\n---\n\n".join(
            candidate_text_parts
        )

        prompt = f"""
You are a semantic relevance evaluator for a banking
knowledge retrieval system.

USER QUESTION:
{query}

RETRIEVED KNOWLEDGE CHUNKS:

{candidate_text}

Evaluate EVERY candidate independently.

Important rules:

1. Judge the actual meaning and context.
2. Do not mark a chunk relevant merely because it contains
   words that also appear in the question.
3. A highly relevant chunk directly provides information needed
   to answer the user's question.
4. A chunk can be relevant even if it does not contain the
   exact wording of the question.
5. A chunk about a different banking process is NOT relevant.
6. For example, documents required for claims are not relevant
   to a question about documents required for opening an account.
7. Do not assume information that is not present in the chunk.

Scoring:

1.0 = directly answers the question
0.8-0.9 = highly relevant supporting information
0.5-0.7 = partially relevant
0.1-0.4 = weakly related
0.0 = unrelated

Return ONLY valid JSON.

The JSON must contain an array called "results".

Use this exact structure:

{{
  "results": [
    {{
      "index": 0,
      "relevant": true,
      "score": 1.0,
      "reason": "short explanation"
    }}
  ]
}}

You MUST evaluate every candidate.

The index must exactly match the candidate number.
The score must be between 0.0 and 1.0.
"""

        try:
            response = self.llm.invoke(prompt)

            raw_content = response.content

            if isinstance(raw_content, list):
                raw_content = "".join(
                    str(item)
                    for item in raw_content
                )

            raw_content = str(raw_content).strip()

            result = json.loads(raw_content)

            evaluations: dict[
                int,
                dict[str, Any],
            ] = {}

            for item in result.get(
                "results",
                [],
            ):

                try:
                    index = int(
                        item.get("index")
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if index < 0 or index >= len(candidates):
                    continue

                score = float(
                    item.get(
                        "score",
                        0.0,
                    )
                )

                score = max(
                    0.0,
                    min(1.0, score),
                )

                evaluations[index] = {
                    "relevant": bool(
                        item.get(
                            "relevant",
                            score > 0,
                        )
                    ),
                    "score": score,
                    "reason": item.get(
                        "reason",
                        "",
                    ),
                }

            return evaluations

        except Exception:
            return {}
        