from __future__ import annotations

import re
from typing import Any


class EvidenceExtractor:
    """
    Extract focused evidence from already-ranked RAG documents.

    Design principles:
    - The reranker's document ordering is authoritative.
    - This class does not perform another document-level ranking.
    - Evidence is extracted from the highest-ranked usable document.
    - If the selected passage belongs to a headed section, the relevant
      section is preserved until the next heading.
    - The implementation is domain-agnostic.
    """

    def __init__(
        self,
        max_passages: int = 3,
        max_passage_chars: int = 1200,
        minimum_overlap: float = 0.5,
    ):
        self.max_passages = max_passages
        self.max_passage_chars = max_passage_chars
        self.minimum_overlap = minimum_overlap

    def extract(
        self,
        query: str,
        documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Extract evidence from already-reranked documents.

        The first usable document is authoritative because the
        EvidenceReranker has already performed document-level ranking.
        """
        if not query or not query.strip():
            return []

        if not documents:
            return []

        candidates = [
            document
            for document in documents[: self.max_passages]
            if isinstance(document, dict)
        ]

        if not candidates:
            return []

        # IMPORTANT:
        # Reranker ordering is authoritative.
        primary_document = candidates[0]
        primary_text = self._extract_text(primary_document)

        if primary_text:
            passage, extraction_score = self._extract_best_passage(
                query=query,
                text=primary_text,
            )

            if passage:
                result = dict(primary_document)

                result["extracted_evidence"] = passage
                result["extraction_method"] = (
                    "query_local_passage"
                    if passage != self._clean_text(primary_text)
                    else "full_document_fallback"
                )
                result["_extraction_score"] = round(
                    extraction_score,
                    6,
                )

                return [result]

        # Only fall back if the highest-ranked document has
        # no usable text.
        for document in candidates[1:]:
            text = self._extract_text(document)

            if not text:
                continue

            passage, extraction_score = self._extract_best_passage(
                query=query,
                text=text,
            )

            if not passage:
                continue

            result = dict(document)

            result["extracted_evidence"] = passage
            result["extraction_method"] = (
                "query_local_passage"
                if passage != self._clean_text(text)
                else "full_document_fallback"
            )
            result["_extraction_score"] = round(
                extraction_score,
                6,
            )

            return [result]

        return []

    def _extract_text(
        self,
        document: dict[str, Any],
    ) -> str:
        """
        Extract source text from a retrieved document.
        """
        content = document.get("content")

        if isinstance(content, str) and content.strip():
            return content

        extracted_evidence = document.get("extracted_evidence")

        if (
            isinstance(extracted_evidence, str)
            and extracted_evidence.strip()
        ):
            return extracted_evidence

        page_content = document.get("page_content")

        if isinstance(page_content, str) and page_content.strip():
            return page_content

        return ""

    def _extract_best_passage(
        self,
        query: str,
        text: str,
    ) -> tuple[str, float]:
        """
        Find the most relevant local section inside one document.

        Document selection has already been completed by the reranker.

        Within the selected document:
        1. Split source into structural units.
        2. Score each unit against the query.
        3. Select the strongest unit.
        4. Expand to its containing section when possible.
        5. Apply the final character safety limit.
        """
        cleaned_text = self._clean_text(text)

        if not cleaned_text:
            return "", 0.0

        units = self._split_into_units(cleaned_text)

        if not units:
            return (
                self._limit_length(cleaned_text),
                0.0,
            )

        query_tokens = self._query_tokens(query)

        if not query_tokens:
            return (
                self._limit_length(cleaned_text),
                0.0,
            )

        scored_units: list[tuple[float, int, str]] = []

        for index, unit in enumerate(units):
            score = self._unit_relevance_score(
                query_tokens=query_tokens,
                unit=unit,
                units=units,
                index=index,
            )

            scored_units.append(
                (
                    score,
                    index,
                    unit,
                )
            )

        scored_units.sort(
            key=lambda item: (
                item[0],
                -item[1],
            ),
            reverse=True,
        )

        if not scored_units:
            return (
                self._limit_length(cleaned_text),
                0.0,
            )

        best_score, best_index, _ = scored_units[0]

        selected_units = self._build_local_window(
            units=units,
            center_index=best_index,
        )

        passage = " ".join(
            unit.strip()
            for unit in selected_units
            if unit.strip()
        ).strip()

        if not passage:
            passage = units[best_index].strip()

        passage = self._limit_length(passage)

        return passage, best_score

    def _unit_relevance_score(
        self,
        query_tokens: list[str],
        unit: str,
        units: list[str] | None = None,
        index: int | None = None,
    ) -> float:
        """
        Calculate relevance of one source unit to the query.

        `units` and `index` are optional for backward compatibility with
        existing diagnostic/debug callers.

        The relevance calculation itself is domain-agnostic and does not
        require the surrounding document.
        """
        unit_tokens = self._normalised_tokens(unit)

        if not unit_tokens:
            return 0.0

        query_set = set(query_tokens)

        if not query_set:
            return 0.0

        unit_set = set(unit_tokens)

        overlap_count = len(
            query_set.intersection(unit_set)
        )

        coverage = overlap_count / len(query_set)

        token_similarity = self._token_similarity(
            query_tokens,
            unit_tokens,
        )

        phrase_score = self._phrase_score(
            query_tokens,
            unit_tokens,
        )

        proximity_score = self._position_proximity_score(
            query_tokens,
            unit_tokens,
        )

        adjacent_score = (
            1.0
            if self._has_adjacent_matches(
                query_tokens,
                unit_tokens,
            )
            else 0.0
        )

        score = (
            coverage * 0.40
            + token_similarity * 0.25
            + phrase_score * 0.20
            + proximity_score * 0.10
            + adjacent_score * 0.05
        )

        # Headings containing no actual query terms should not
        # artificially dominate content units.
        if (
            self._looks_like_heading(unit)
            and overlap_count == 0
        ):
            score *= 0.85

        return min(
            max(score, 0.0),
            1.0,
        )

    def _query_tokens(
        self,
        query: str,
    ) -> list[str]:
        """
        Return normalized query tokens with generic stop words removed.
        """
        tokens = self._token_list(query)

        stop_words = self._stop_words()

        return [
            token
            for token in tokens
            if token not in stop_words
        ]

    def _token_list(
        self,
        text: str,
    ) -> list[str]:
        """
        Tokenize text using a simple domain-agnostic strategy.
        """
        if not text:
            return []

        return re.findall(
            r"[A-Za-z0-9]+",
            text.lower(),
        )

    def _normalised_tokens(
        self,
        text: str,
    ) -> list[str]:
        return self._token_list(text)

    def _token_similarity(
        self,
        query_tokens: list[str],
        unit_tokens: list[str],
    ) -> float:
        """
        Measure soft token similarity between query and source unit.
        """
        if not query_tokens or not unit_tokens:
            return 0.0

        unit_set = set(unit_tokens)

        similarities: list[float] = []

        for query_token in query_tokens:
            if query_token in unit_set:
                similarities.append(1.0)
                continue

            best_similarity = 0.0

            for unit_token in unit_set:
                if not unit_token:
                    continue

                if (
                    query_token.startswith(unit_token)
                    or unit_token.startswith(query_token)
                ):
                    best_similarity = max(
                        best_similarity,
                        0.75,
                    )

                common_length = self._longest_common_substring(
                    query_token,
                    unit_token,
                )

                if common_length >= 4:
                    similarity = common_length / max(
                        len(query_token),
                        len(unit_token),
                    )

                    best_similarity = max(
                        best_similarity,
                        similarity,
                    )

            similarities.append(best_similarity)

        if not similarities:
            return 0.0

        return sum(similarities) / len(similarities)

    def _longest_common_substring(
        self,
        first: str,
        second: str,
    ) -> int:
        """
        Return the length of the longest common contiguous substring.
        """
        if not first or not second:
            return 0

        previous = [0] * (len(second) + 1)
        longest = 0

        for first_char in first:
            current = [0] * (len(second) + 1)

            for index, second_char in enumerate(
                second,
                start=1,
            ):
                if first_char == second_char:
                    current[index] = (
                        previous[index - 1] + 1
                    )

                    longest = max(
                        longest,
                        current[index],
                    )

            previous = current

        return longest

    def _phrase_score(
        self,
        query_tokens: list[str],
        unit_tokens: list[str],
    ) -> float:
        """
        Measure whether query token sequences occur together.
        """
        if not query_tokens or not unit_tokens:
            return 0.0

        if len(query_tokens) == 1:
            return (
                1.0
                if query_tokens[0] in unit_tokens
                else 0.0
            )

        unit_text = " ".join(unit_tokens)

        phrase_scores: list[float] = []

        # Bigrams.
        for index in range(
            len(query_tokens) - 1
        ):
            phrase = (
                f"{query_tokens[index]} "
                f"{query_tokens[index + 1]}"
            )

            if phrase in unit_text:
                phrase_scores.append(1.0)

        # Trigrams.
        for index in range(
            len(query_tokens) - 2
        ):
            phrase = (
                f"{query_tokens[index]} "
                f"{query_tokens[index + 1]} "
                f"{query_tokens[index + 2]}"
            )

            if phrase in unit_text:
                phrase_scores.append(1.0)

        if not phrase_scores:
            return 0.0

        return min(
            1.0,
            sum(phrase_scores) / len(phrase_scores),
        )

    def _position_proximity_score(
        self,
        query_tokens: list[str],
        unit_tokens: list[str],
    ) -> float:
        """
        Measure how closely matching query tokens occur.
        """
        if not query_tokens or not unit_tokens:
            return 0.0

        positions: list[int] = []

        for query_token in query_tokens:
            matches = [
                index
                for index, unit_token in enumerate(
                    unit_tokens
                )
                if (
                    unit_token == query_token
                    or unit_token.startswith(query_token)
                    or query_token.startswith(unit_token)
                )
            ]

            if matches:
                positions.append(matches[0])

        if len(positions) < 2:
            return 0.0

        span = max(positions) - min(positions) + 1

        if span <= 3:
            return 1.0

        if span <= 6:
            return 0.8

        if span <= 10:
            return 0.6

        if span <= 20:
            return 0.4

        return 0.2

    def _has_adjacent_matches(
        self,
        query_tokens: list[str],
        unit_tokens: list[str],
    ) -> bool:
        """
        Detect adjacent query terms in the source unit.
        """
        if len(query_tokens) < 2:
            return False

        if not unit_tokens:
            return False

        for index in range(
            len(unit_tokens) - 1
        ):
            first = unit_tokens[index]
            second = unit_tokens[index + 1]

            for query_index in range(
                len(query_tokens) - 1
            ):
                query_first = query_tokens[
                    query_index
                ]
                query_second = query_tokens[
                    query_index + 1
                ]

                first_matches = (
                    first == query_first
                    or first.startswith(query_first)
                    or query_first.startswith(first)
                )

                second_matches = (
                    second == query_second
                    or second.startswith(query_second)
                    or query_second.startswith(second)
                )

                if (
                    first_matches
                    and second_matches
                ):
                    return True

        return False

    def _looks_like_heading(
        self,
        text: str,
    ) -> bool:
        """
        Detect common document heading structures.

        This intentionally does not contain domain-specific words.
        """
        if not text:
            return False

        value = text.strip()

        if not value:
            return False

        # Numbered headings:
        # 1. TITLE
        # 1.1 TITLE
        # 10) TITLE
        if re.match(
            r"^\d+(?:\.\d+)*[\.)]?\s+\S+",
            value,
        ):
            return True

        # Roman numeral headings:
        # I. TITLE
        # IV. TITLE
        if re.match(
            r"^[IVXLCDM]+[\.)]\s+\S+",
            value,
            re.IGNORECASE,
        ):
            return True

        # Short all-uppercase headings.
        words = value.split()

        if (
            1 <= len(words) <= 12
            and any(
                char.isalpha()
                for char in value
            )
            and value == value.upper()
        ):
            return True

        return False

    def _clean_text(
        self,
        text: str,
    ) -> str:
        """
        Normalize source text while preserving structural line breaks.

        We intentionally do NOT use:

            re.sub(r"\\s+", " ", text)

        because that destroys document structure.
        """
        if not text:
            return ""

        text = text.replace(
            "\u00ad",
            "",
        )

        # Repair words split across a line break:
        # docu-
        # ment
        #
        # becomes:
        # document
        text = re.sub(
            r"-\s*\n\s*",
            "",
            text,
        )

        # Normalize horizontal whitespace only.
        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        # Preserve meaningful blank-line boundaries.
        text = re.sub(
            r"\n\s*\n+",
            "\n\n",
            text,
        )

        return text.strip()

    def _split_into_units(
        self,
        text: str,
    ) -> list[str]:
        """
        Split source text into semantic structural units.

        Units may be:
        - headings
        - paragraphs
        - bullet/list entries
        """
        if not text:
            return []

        normalized_text = self._clean_text(text)

        if not normalized_text:
            return []

        lines = [
            line.strip()
            for line in normalized_text.splitlines()
            if line.strip()
        ]

        if not lines:
            return []

        units: list[str] = []
        buffer: list[str] = []

        def flush_buffer() -> None:
            if not buffer:
                return

            value = " ".join(
                buffer
            ).strip()

            if value:
                units.append(value)

            buffer.clear()

        for line in lines:
            # Headings are always separate units.
            if self._looks_like_heading(line):
                flush_buffer()
                units.append(line)
                continue

            # Common list markers are separate units.
            if re.match(
                r"^(?:↗|•|▪|●|○|[-*])\s*",
                line,
            ):
                flush_buffer()
                units.append(line)
                continue

            buffer.append(line)

        flush_buffer()

        return units

    def _build_local_window(
        self,
        units: list[str],
        center_index: int,
    ) -> list[str]:
        """
        Build a structure-aware evidence section.

        Starting from the nearest heading before the selected unit,
        include all content until the next heading.

        Example:

            FOR PARTNERSHIP FIRMS
            item 1
            item 2
            item 3
            FOR COMPANIES
            item 4

        Selecting item 2 returns:

            FOR PARTNERSHIP FIRMS
            item 1
            item 2
            item 3

        It does not include FOR COMPANIES.
        """
        if not units:
            return []

        center_index = max(
            0,
            min(
                center_index,
                len(units) - 1,
            ),
        )

        # Find nearest preceding heading.
        section_start = center_index

        for index in range(
            center_index,
            -1,
            -1,
        ):
            if self._looks_like_heading(
                units[index]
            ):
                section_start = index
                break

        # Find next heading.
        section_end = len(units)

        for index in range(
            section_start + 1,
            len(units),
        ):
            if self._looks_like_heading(
                units[index]
            ):
                section_end = index
                break

        selected = units[
            section_start:section_end
        ]

        if not selected:
            return [
                units[center_index]
            ]

        return selected

    def _limit_length(
        self,
        text: str,
    ) -> str:
        """
        Apply the final evidence-size safety limit.
        """
        if not text:
            return ""

        text = text.strip()

        if len(text) <= self.max_passage_chars:
            return text

        truncated = text[
            : self.max_passage_chars
        ]

        # Prefer complete sentence.
        sentence_end = max(
            truncated.rfind(". "),
            truncated.rfind("? "),
            truncated.rfind("! "),
        )

        if sentence_end >= int(
            self.max_passage_chars * 0.60
        ):
            return truncated[
                : sentence_end + 1
            ].strip()

        # Otherwise prefer a complete line.
        newline_end = truncated.rfind(
            "\n"
        )

        if newline_end >= int(
            self.max_passage_chars * 0.60
        ):
            return truncated[
                :newline_end
            ].strip()

        return truncated.rstrip() + "..."

    def _stop_words(self) -> set[str]:
        """
        Generic English retrieval stop words.

        No banking/domain-specific terms are included.
        """
        return {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "have",
            "how",
            "i",
            "in",
            "is",
            "it",
            "me",
            "my",
            "of",
            "on",
            "or",
            "please",
            "the",
            "to",
            "what",
            "which",
            "who",
            "with",
        }
