import json

from langchain_ollama import ChatOllama

from rag.service import RagService


QUERY = "What documents are required for a account opening?"

SPACES = {
    "CUB Operations": "6772e8ed-b865-4e46-9e0f-0aa542a7d2b4",
    "Banking Operations": "50705c2f-1eda-47e0-a69e-c671e16c5a0b",
}


llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)

rag_service = RagService()


def evaluate_chunk(
    query: str,
    content: str,
) -> dict:

    prompt = f"""
You are evaluating whether a retrieved banking document chunk
is relevant to a user's question.

USER QUESTION:
{query}

RETRIEVED DOCUMENT CHUNK:
{content}

Determine whether this chunk contains information that directly
helps answer the user's question.

Return ONLY valid JSON:

{{
  "relevant": true,
  "score": 0.0,
  "reason": "short explanation"
}}

Rules:

- score must be between 0.0 and 1.0
- 1.0 means directly answers the question
- 0.0 means unrelated
- Do not judge based only on shared words.
- Consider the actual meaning and context.
"""

    response = llm.invoke(prompt)

    text = response.content.strip()

    # Handle accidental markdown fences.
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    try:
        result = json.loads(text)

        return {
            "relevant": bool(
                result.get("relevant", False)
            ),
            "score": float(
                result.get("score", 0.0)
            ),
            "reason": result.get(
                "reason",
                "",
            ),
        }

    except Exception as exc:

        return {
            "relevant": False,
            "score": 0.0,
            "reason": f"Invalid LLM response: {exc}",
            "raw_response": text,
        }


def main():

    print("\n" + "=" * 80)
    print("RAG RERANKING EXPERIMENT")
    print("=" * 80)

    print(f"\nQuery:")
    print(QUERY)

    all_results = []

    for space_name, space_id in SPACES.items():

        print("\n" + "-" * 80)
        print(f"SPACE: {space_name}")
        print("-" * 80)

        result = rag_service.retrieve(
            space_id=space_id,
            query=QUERY,
            top_k=5,
        )

        for index, document in enumerate(
            result.get("documents", []),
            start=1,
        ):

            metadata = document.get(
                "metadata",
                {},
            )

            content = document.get(
                "content",
                "",
            )

            distance = document.get(
                "distance"
            )

            evaluation = evaluate_chunk(
                query=QUERY,
                content=content,
            )

            item = {
                "space_name": space_name,
                "space_id": space_id,
                "distance": distance,
                "file_name": metadata.get(
                    "file_name"
                ),
                "page_number": metadata.get(
                    "page_number"
                ),
                "chunk_index": metadata.get(
                    "chunk_index"
                ),
                "relevant": evaluation.get(
                    "relevant",
                    False,
                ),
                "score": evaluation.get(
                    "score",
                    0.0,
                ),
                "reason": evaluation.get(
                    "reason",
                    "",
                ),
            }

            all_results.append(item)

            print(f"\nResult #{index}")
            print(f"Distance : {item['distance']}")
            print(f"File     : {item['file_name']}")
            print(f"Page     : {item['page_number']}")
            print(f"Chunk    : {item['chunk_index']}")
            print(f"Relevant : {item['relevant']}")
            print(f"Score    : {item['score']}")
            print(f"Reason   : {item['reason']}")

    print("\n" + "=" * 80)
    print("RERANKED RESULTS")
    print("=" * 80)

    ranked_results = sorted(
        all_results,
        key=lambda item: item["score"],
        reverse=True,
    )

    for index, item in enumerate(
        ranked_results,
        start=1,
    ):

        print(
            f"\n#{index} "
            f"{item['score']:.2f} "
            f"{item['space_name']} "
            f"| distance={item['distance']}"
        )

        print(
            f"   {item['file_name']} "
            f"(page {item['page_number']}, "
            f"chunk {item['chunk_index']})"
        )

        print(
            f"   Relevant: {item['relevant']}"
        )

        print(
            f"   Reason: {item['reason']}"
        )


if __name__ == "__main__":
    main()

