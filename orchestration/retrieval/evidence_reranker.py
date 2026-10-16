from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class RankedEvidence:
    """
    Generic ranked RAG evidence.

    score:
        Higher means more relevant to the query.

    content:
        Actual retrieved evidence text.

    metadata:
        Original metadata associated with the evidence.
    """

    score: float
    content: str
    metadata: dict[str, Any]


class EvidenceReranker:
    """
    Generic evidence reranker for retrieved RAG documents.

    Responsibilities:
        - Rerank already-retrieved evidence.
        - Combine retrieval relevance with lexical relevance.
        - Preserve original evidence metadata.
        - Prefer strong multi-token phrase matches.
        - Avoid domain-specific rules.

    It does NOT:
        - retrieve documents
        - select RAG spaces
        - know banking concepts
        - generate answers
        - modify document content

    Architecture:

        RAGSelector
            ↓
        Retrieved candidates
            ↓
        EvidenceReranker
            ↓
        Relevant evidence
    """

    def __init__(
        self,
        max_results: int = 3,
        min_score: float = 0.0,
    ):
        self.max_results = max_results
        self.min_score = min_score

    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Rerank retrieved RAG documents.

        The returned documents preserve their original structure and
        receive an additional `_rerank_score` field.
        """

        if not query:
            return documents[: self.max_results]

        if not documents:
            return []

        query_tokens = self._tokenize(query)

        ranked: list[tuple[float, dict[str, Any]]] = []

        for document in documents:

            content = self._extract_content(
                document
            )

            if not content:
                continue

            retrieval_score = (
                self._retrieval_score(document)
            )

            lexical_score = (
                self._lexical_score(
                    query_tokens,
                    content,
                )
            )

            phrase_score = (
                self._phrase_score(
                    query_tokens,
                    content,
                )
            )

            proximity_score = (
                self._proximity_score(
                    query_tokens,
                    content,
                )
            )

            # Strong phrase matches are particularly useful when
            # several semantically similar documents are returned.
            #
            # Retrieval remains the strongest baseline signal,
            # while lexical, phrase, and proximity signals provide
            # increasingly precise evidence.
            final_score = (
                retrieval_score * 0.45
                + lexical_score * 0.20
                + phrase_score * 0.25
                + proximity_score * 0.10
            )

            enriched = dict(document)

            enriched["_rerank_score"] = round(
                final_score,
                6,
            )

            ranked.append(
                (
                    final_score,
                    enriched,
                )
            )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            document
            for score, document in ranked
            if score >= self.min_score
        ][: self.max_results]

    # ================================================================
    # Retrieval score
    # ================================================================

    def _retrieval_score(
        self,
        document: dict[str, Any],
    ) -> float:
        """
        Normalize the original vector retrieval distance.

        Lower distance normally means better similarity.

        If no distance exists, return a neutral value so that
        lexical relevance can still operate.
        """

        distance = document.get("distance")

        if distance is None:
            return 0.5

        try:
            distance = float(distance)
        except (
            TypeError,
            ValueError,
        ):
            return 0.5

        if not math.isfinite(distance):
            return 0.5

        return 1.0 / (
            1.0 + max(distance, 0.0)
        )

    # ================================================================
    # Lexical relevance
    # ================================================================

    def _lexical_score(
        self,
        query_tokens: list[str],
        content: str,
    ) -> float:

        if not query_tokens:
            return 0.0

        document_tokens = self._tokenize(
            content
        )

        if not document_tokens:
            return 0.0

        matched = 0

        for query_token in query_tokens:

            if query_token in document_tokens:
                matched += 1
                continue

            if any(
                self._token_similarity(
                    query_token,
                    document_token,
                )
                >= 0.88
                for document_token
                in document_tokens
            ):
                matched += 1

        return matched / len(query_tokens)

    # ================================================================
    # Phrase relevance
    # ================================================================

    def _phrase_score(
        self,
        query_tokens: list[str],
        content: str,
    ) -> float:
        """
        Measure the strongest meaningful phrase match.

        Longer contiguous phrases receive more weight than
        individual token matches.

        This is intentionally domain-agnostic.

        Example:

            query:
                "minimum balance policy"

        A document containing:

            "minimum balance"

        receives a stronger phrase signal than a document
        containing the words "balance" and "policy" far apart.
        """

        if len(query_tokens) < 2:
            return 0.0

        document_tokens = self._tokenize(
            content
        )

        if len(document_tokens) < 2:
            return 0.0

        best_score = 0.0

        # Prefer longer phrases.
        #
        # 3-token phrase > 2-token phrase.
        for size in (2, 3):

            if len(query_tokens) < size:
                continue

            for index in range(
                len(query_tokens) - size + 1
            ):

                query_phrase = query_tokens[
                    index : index + size
                ]

                similarity = (
                    self._best_phrase_similarity(
                        query_phrase,
                        document_tokens,
                    )
                )

                if similarity <= 0:
                    continue

                # Longer phrase matches are more informative.
                phrase_weight = (
                    1.0
                    if size == 2
                    else 1.25
                )

                candidate_score = (
                    similarity
                    * phrase_weight
                )

                best_score = max(
                    best_score,
                    candidate_score,
                )

        # Keep the score bounded.
        return min(
            best_score,
            1.0,
        )

    def _best_phrase_similarity(
        self,
        query_phrase: list[str],
        document_tokens: list[str],
    ) -> float:

        phrase_size = len(query_phrase)

        if len(document_tokens) < phrase_size:
            return 0.0

        best = 0.0

        for index in range(
            len(document_tokens)
            - phrase_size
            + 1
        ):

            window = document_tokens[
                index : index + phrase_size
            ]

            similarities = [
                self._token_similarity(
                    query_token,
                    document_token,
                )
                for query_token, document_token
                in zip(
                    query_phrase,
                    window,
                )
            ]

            if similarities:

                candidate = (
                    sum(similarities)
                    / len(similarities)
                )

                best = max(
                    best,
                    candidate,
                )

        return best

    # ================================================================
    # Proximity relevance
    # ================================================================

    def _proximity_score(
        self,
        query_tokens: list[str],
        content: str,
    ) -> float:

        if len(query_tokens) < 2:
            return 0.0

        document_tokens = self._tokenize(
            content
        )

        positions: list[list[int]] = []

        for query_token in query_tokens:

            matches = []

            for index, document_token in enumerate(
                document_tokens
            ):

                if (
                    self._token_similarity(
                        query_token,
                        document_token,
                    )
                    >= 0.88
                ):
                    matches.append(index)

            if matches:
                positions.append(matches)

        if len(positions) < 2:
            return 0.0

        best_span = None

        for start_group in positions:

            for start in start_group:

                covered = set()
                end = start

                for position in range(
                    start,
                    len(document_tokens),
                ):

                    for group_index, group in enumerate(
                        positions
                    ):

                        if position in group:
                            covered.add(
                                group_index
                            )

                    if len(covered) == len(
                        positions
                    ):
                        end = position
                        break

                if len(covered) == len(
                    positions
                ):

                    span = end - start + 1

                    if (
                        best_span is None
                        or span < best_span
                    ):
                        best_span = span

        if best_span is None:
            return 0.0

        return 1.0 / math.log2(
            best_span + 1
        )

    # ================================================================
    # Text handling
    # ================================================================

    def _extract_content(
        self,
        document: dict[str, Any],
    ) -> str:

        for key in (
            "content",
            "text",
            "page_content",
            "chunk",
            "snippet",
        ):

            value = document.get(key)

            if (
                isinstance(value, str)
                and value.strip()
            ):
                return value.strip()

        nested = document.get(
            "document"
        )

        if isinstance(nested, dict):

            return self._extract_content(
                nested
            )

        return ""

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:

        return re.findall(
            r"\b[\w]+\b",
            text.lower(),
        )

    def _token_similarity(
        self,
        left: str,
        right: str,
    ) -> float:

        if left == right:
            return 1.0

        if (
            len(left) >= 4
            and len(right) >= 4
            and (
                left.startswith(right)
                or right.startswith(left)
            )
        ):
            return 0.90

        common = self._longest_common_substring(
            left,
            right,
        )

        denominator = max(
            len(left),
            len(right),
        )

        if denominator == 0:
            return 0.0

        return common / denominator

    def _longest_common_substring(
        self,
        left: str,
        right: str,
    ) -> int:

        previous = [0] * (
            len(right) + 1
        )

        longest = 0

        for left_char in left:

            current = [0] * (
                len(right) + 1
            )

            for index, right_char in enumerate(
                right,
                start=1,
            ):

                if left_char == right_char:

                    current[index] = (
                        previous[index - 1]
                        + 1
                    )

                    longest = max(
                        longest,
                        current[index],
                    )

            previous = current

        return longest
