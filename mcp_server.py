from mcp.server.fastmcp import FastMCP
import requests


MCP = FastMCP("sql-agent-mcp")

BASE_URL = "http://localhost:8000"

@MCP.tool()
def discover_tables(query: str):
    """
    Find relevant tables for a natural language query
    """

    res = requests.post(
        f"{BASE_URL}/discover_tables",
        json={"query": query}
    )

    return res.json()

@MCP.tool()
def approve_table(session_id: str, table: str, query: str, matched_terms: list = []):
    """
    Approve a table and trigger column resolution
    """

    res = requests.post(
        f"{BASE_URL}/approve_table",
        json={
            "session_id": session_id,
            "table": table,
            "query": query,
            "matched_terms": matched_terms
        }
    )

    return res.json()
@MCP.tool()
def resolve_ambiguity(session_id: str, selections: dict):
    """
    Resolve ambiguous column mappings
    """

    res = requests.post(
        f"{BASE_URL}/resolve_ambiguity",
        json={
            "session_id": session_id,
            "selections": selections
        }
    )

    return res.json()

@MCP.tool()
def execute(session_id: str):
    """
    Execute final SQL query after resolution
    """

    res = requests.post(
        f"{BASE_URL}/execute",
        json={"session_id": session_id}
    )

    return res.json()

if __name__ == "__main__":
    print("MCP server starting...")
    MCP.run()
