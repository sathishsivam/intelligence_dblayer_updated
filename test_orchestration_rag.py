import asyncio
import time

from orchestration.models.request import OrchestrationRequest
from orchestration.service import OrchestrationService


async def main():
    print("=" * 80)
    print("AIZILLON ORCHESTRATION - RAG FAST ROUTING TEST")
    print("=" * 80)

    query = "What documents are required for account opening?"

    print(f"\nQuery: {query}")

    service = OrchestrationService()

    request = OrchestrationRequest(
        query=query,
    )

    start = time.perf_counter()

    response = await service.process(request)

    total_time = time.perf_counter() - start

    print("\n" + "-" * 80)
    print("ORCHESTRATION RESULT")
    print("-" * 80)

    print(f"\nSuccess       : {response.success}")
    print(f"Intent        : {response.intent}")
    print(f"Strategy      : {response.strategy}")
    print(
        f"Authentication: "
        f"{response.requires_authentication}"
    )
    print(
        f"Confirmation  : "
        f"{response.requires_confirmation}"
    )

    print(f"\nTotal time    : {total_time:.3f} sec")

    if response.sources:
        print("\nSources:")

        for source in response.sources:
            print(
                f"  - {source.type}: "
                f"{source.name}"
            )

            if source.metadata:
                print(
                    f"    Metadata: "
                    f"{source.metadata}"
                )

    if response.error:
        print(f"\nError: {response.error}")

    if response.clarification_question:
        print(
            "\nClarification:"
            f" {response.clarification_question}"
        )

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())