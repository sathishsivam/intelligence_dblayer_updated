import time

from langchain_ollama import ChatOllama


def main():

    print("=" * 80)
    print("OLLAMA PLANNER SPEED TEST")
    print("=" * 80)

    model = "qwen3:4b"

    print(f"\nModel: {model}")

    start = time.perf_counter()

    llm = ChatOllama(
        model=model,
        temperature=0,
    )

    init_time = time.perf_counter() - start

    print(f"LLM initialization : {init_time:.3f} sec")

    prompt = """
You are a banking intent classifier.

Classify this query into exactly one intent:

- RAG
- MCP
- DB
- CLARIFICATION

Return only the intent.

Query:
What documents are required for account opening?
"""

    start = time.perf_counter()

    result = llm.invoke(prompt)

    inference_time = time.perf_counter() - start

    print(f"\nInference time     : {inference_time:.3f} sec")
    print(f"Result             : {result.content}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()