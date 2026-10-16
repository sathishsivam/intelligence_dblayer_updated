import asyncio
import json

from fastmcp import Client
from langchain_ollama import ChatOllama


MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"


async def main():

    # ---------------------------------------------------------
    # 1. Connect to MCP Server
    # ---------------------------------------------------------

    async with Client(MCP_SERVER_URL) as client:

        print("=" * 80)
        print("CONNECTED TO MCP SERVER")
        print("=" * 80)
        print(MCP_SERVER_URL)

        # -----------------------------------------------------
        # 2. Discover MCP tools
        # -----------------------------------------------------

        tools = await client.list_tools()

        print("\n" + "=" * 80)
        print("MCP TOOLS AVAILABLE")
        print("=" * 80)

        for tool in tools:
            print(f"Name        : {tool.name}")
            print(f"Description : {tool.description}")
            print(f"Schema      : {tool.inputSchema}")
            print("-" * 80)

        # -----------------------------------------------------
        # 3. User's natural-language request
        # -----------------------------------------------------

        user_query = "What is the current balance of account 101?"

        print("\n" + "=" * 80)
        print("USER QUERY")
        print("=" * 80)
        print(user_query)

        # -----------------------------------------------------
        # 4. Create Ollama model
        # -----------------------------------------------------

        llm = ChatOllama(
            model="qwen3:4b",
            temperature=0,
        )

        # -----------------------------------------------------
        # 5. Give the available MCP tools to the LLM
        # -----------------------------------------------------

        tool_information = []

        for tool in tools:

            tool_information.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
            )

        prompt = f"""
You are a banking assistant.

You have access to the following MCP tools:

{json.dumps(tool_information, indent=2, default=str)}

User request:

{user_query}

Determine which MCP tool should be used.

Return ONLY valid JSON in this format:

{{
    "tool_name": "tool name",
    "arguments": {{
        "parameter": "value"
    }}
}}

Do not return anything else.
"""

        # -----------------------------------------------------
        # 6. Ask Ollama to select the MCP tool
        # -----------------------------------------------------

        response = await llm.ainvoke(prompt)

        print("\n" + "=" * 80)
        print("LLM TOOL SELECTION")
        print("=" * 80)
        print(response.content)

        # -----------------------------------------------------
        # 7. Parse LLM response
        # -----------------------------------------------------

        selection_text = response.content.strip()

        # Handle possible markdown code fences
        if selection_text.startswith("```"):

            selection_text = (
                selection_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        selection = json.loads(selection_text)

        tool_name = selection["tool_name"]
        arguments = selection.get("arguments", {})

        print("\n" + "=" * 80)
        print("SELECTED MCP TOOL")
        print("=" * 80)
        print(f"Tool      : {tool_name}")
        print(f"Arguments : {arguments}")

        # -----------------------------------------------------
        # 8. Call MCP tool
        # -----------------------------------------------------

        print("\n" + "=" * 80)
        print("CALLING MCP TOOL")
        print("=" * 80)

        result = await client.call_tool(
            tool_name,
            arguments,
        )

        # -----------------------------------------------------
        # 9. Display MCP result
        # -----------------------------------------------------

        print("\n" + "=" * 80)
        print("MCP TOOL RESULT")
        print("=" * 80)

        print(result)

        # -----------------------------------------------------
        # 10. Send result back to LLM for natural response
        # -----------------------------------------------------

        final_prompt = f"""
You are a banking assistant.

The user asked:

{user_query}

The MCP tool returned:

{result}

Give a concise natural-language answer to the user.

Do not invent any information.
"""

        final_response = await llm.ainvoke(final_prompt)

        print("\n" + "=" * 80)
        print("FINAL AGENT RESPONSE")
        print("=" * 80)

        print(final_response.content)


if __name__ == "__main__":
    asyncio.run(main())

