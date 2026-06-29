from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from .db import global_db
from .promptutils import build_messages

# def build_messages(prompt_template, user_query: str):
#     messages = prompt_template.format_messages(user_query=user_query)

#     system_msg = "\n".join(
#         [m.content for m in messages if m.type == "system"]
#     )

#     user_msg = "\n".join(
#         [m.content for m in messages if m.type == "human"]
#     )
#     print(system_msg)

#     return system_msg, user_msg

def callTool(table:str):
    """ function  to call the QuerySQLDatabaseTool"""
    print("tool called")
    tool = QuerySQLDatabaseTool(
        db=global_db,
        description=""" This tool executes SQL queries on the Oracle database.

        CRITICAL INSTRUCTIONS:
        - You MUST use this tool to answer any question related to data
        - DO NOT generate SQL without executing it
        - DO NOT return SQL queries as text
        - ALWAYS execute the query using this tool
        - The final answer must come from this tool's output

        INPUT:
        - A valid Oracle SQL SELECT query

        OUTPUT:
        - Query results from the database

         """,
        include_tables=[table]
    )
    return tool


def create_sql_agent(table: str,system_msg:str):
    """
    Creates SQL agent bound to a specific table
    """
    print("Called Agent mechanism for",table)
    
    sys_tool=callTool(table)
    print("sys_tool",sys_tool)
    # tool = QuerySQLDatabaseTool(
    #     db=global_db,description=""" Use this tool to query the database """,
    #     include_tables=[table]
    # )
    

    llm = ChatOllama(
        model="qwen3:4b",
        temperature=0
    )

    agent = create_agent(
        model=llm,
        tools=[sys_tool],
        system_prompt=system_msg  # will be injected dynamically later
    )

    return agent

def prepare_agent_context(prompt_template, user_query: str, table: str):
    """
    Central function used by FastAPI
    """

    system_msg, user_msg = build_messages(prompt_template, user_query)

    agent = create_sql_agent(table,system_msg)
    

    return {
        "agent": agent,
        "system_msg": system_msg,
        "user_msg": user_msg
    }
