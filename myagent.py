from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_ollama import ChatOllama
from .db import global_db

def get_agent(table,sys_msg):
 sys_tool=QuerySQLDatabaseTool(db=global_db,description="""
        This tool executes SQL queries on the Oracle database.

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

        EXAMPLE:
        Input: SELECT ATM_ID, CITY FROM tb_abmi_atm_locator WHERE STATE='Karnataka'
        Output: [(...), (...)]
        """,include_tables=[table])
 
 atm_agent=create_agent(model=ChatOllama(model="qwen3:4b",temperature=0),tools=[sys_tool],system_prompt=sys_msg)
 return atm_agent
