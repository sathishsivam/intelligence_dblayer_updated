import asyncio
from fastmcp import Client


MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"


async def main():

    async with Client(MCP_SERVER_URL) as client:

        # ====================================================
        # LIST TOOLS
        # ====================================================

        tools = await client.list_tools()

        print("=" * 80)
        print("MCP TOOLS")
        print("=" * 80)

        for tool in tools:

            print(f"NAME: {tool.name}")
            print(f"DESCRIPTION: {tool.description}")
            print(f"INPUT SCHEMA: {tool.inputSchema}")
            print("-" * 80)

        # ====================================================
        # CALL get_posts
        # ====================================================

        print("=" * 80)
        print("CALLING get_posts")
        print("=" * 80)

        result = await client.call_tool(
            "get_posts",
            {},
        )

        print("=" * 80)
        print("MCP RESULT")
        print("=" * 80)

        print(result)


if __name__ == "__main__":
    asyncio.run(main())

