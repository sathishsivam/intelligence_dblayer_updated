from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ..intelligence_layer_td import get_relevant_tables
from ..columfrmtable import get_clean_schema
from ..db import global_db
from ..columnresolver import resolve_columns_from_terms
from ..buildPrompt4ChatPromptTemplate import build_agent_prompt
from ..promptutils import build_messages
from ..agent import prepare_agent_context,callTool
from ..hitl_column_selector import build_hitl_payload
from ..column_intent_extractor import extract_column_terms
from ..filterresolver import sql_intent_parser
from ..scil_resolver import resolve_columns
from ..scil_value_resolver import build_scil_value_registry
from ..scil_builder import build_scil
from ..myagent import get_agent
from langchain_core.messages import ToolMessage
import pandas as pd
import ast
import uuid

from ..hilt import detect_ambiguities



app=FastAPI()

if not hasattr(app.state, "column_memory"):
    app.state.column_memory = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class TableSelectionRequest(BaseModel):
    table: str
    query: str
    matched_terms: list[str] = []

class AmbiguityResolutionRequest(BaseModel):
    session_id: str
    selections: dict[str, str]

@app.post("/discover_tables")
def discover_tables(req: QueryRequest):

    tables, ranked_tables,runtime_schema = get_relevant_tables(req.query)

    app.state.ranked_tables = ranked_tables

    return {
        "query": req.query,
        "suggestion": tables,
        "ranked_tables": ranked_tables
    }


@app.post("/approve_table")
def approve_table(req: TableSelectionRequest):

    schema_text, mapping_text,runtime_schema= get_clean_schema(
        global_db._engine,
        [req.table]
    )

    selected_table = next(
        (
            t for t in app.state.ranked_tables
            if t["table"] == req.table
        ),
        None
    )

    if not selected_table:
        return {"error": "Table not found"}
    
    

    # column_result = resolve_columns_from_terms(
    # matched_terms=req.matched_terms,
    # mapping_text=mapping_text)

    scil_result = resolve_columns(
    matched_terms=req.matched_terms,
    mapping_text=mapping_text
)

    # resolved_columns = column_result["resolved_columns"]
    # ambiguities = column_result["ambiguities"]
    # candidate_columns = column_result["candidate_columns"]

    resolved_columns = scil_result["resolved_columns"]
    ambiguities = scil_result["ambiguities"]

    scil_registry = build_scil_value_registry(
    global_db._engine,
    req.table
    )

    intent = sql_intent_parser(
    query=req.query,
    resolved_columns=resolved_columns,
    scil_registry=scil_registry
    )


    # intent = sql_intent_parser(
    # query=req.query,
    # mapping_text=mapping_text,
    # resolved_columns=resolved_columns
    # )
    # -----------------------------
    # FILTER EXTRACTION
    # -----------------------------
   
    # intent = sql_intent_parser(
    # query=req.query,
    # mapping_text=mapping_text,
    # runtime_schema=runtime_schema,
    # allowed_columns=resolved_columns
    # )
    filters = intent.get("filters", [])
    print("FILTERS",filters)

    # enum_index = build_enum_index(global_db._engine, req.table)

    # -----------------------------
    # VALUE INTELLIGENCE FIX
    # -----------------------------
    # final_filters = []

    # for f in filters:
    #     final_filters.append({
    #     "column": f["column"],
    #     "operator": f["operator"],
    #     "value": scil_registry.get(f["column"], {})
    #                 .get(str(f["value"]).lower(), f["value"])
    # })

    # filters = final_filters

    # unique_filters = []
    # seen = set()

    # for f in filters:
    #     key = (
    #         f["column"],
    #         f["operator"],
    #         str(f["value"]).upper()
    #         )

    #     if key not in seen:
    #         seen.add(key)
    #         unique_filters.append(f)

    # filters = unique_filters

    # scil_filters = scil_filter_resolver(
    # query=req.query,
    # scil_schema=scil_schema,
    # raw_filters=intent["filters"]
    # )

    # -----------------------------
    # HITL CHECK
    # -----------------------------
    if ambiguities:
        return build_hitl_payload(
        ambiguities=ambiguities,
        resolved_columns=resolved_columns,
        schema_text=schema_text,
        mapping_text=mapping_text,
        table_name=req.table,
        query=req.query,
        session_store=app.state.column_memory
    )


    # filter_candidates = intent.get("filter_candidates", [])
    

    # ambiguities = detect_ambiguities(candidate_columns)
    # # filter_ambiguities = detect_ambiguities(filter_candidates)

    # invalid_filters = [
    #     f for f in filters
    #     if f["column"] not in resolved_columns
    # ]

   
    # if ambiguities or invalid_filters:

    #     return {
    #          "status": "HITL_REQUIRED",
    #          "query": req.query,
    #          "table": req.table,
    #          "ambiguities": ambiguities,
    #         #  "filter_ambiguties":filter_ambiguities,
    #          "invalid_filters":invalid_filters
    #          }
    # # =========================
    # MEMORY (optional but critical)
    # =========================
    # if not hasattr(app.state, "column_memory"):
    #     app.state.column_memory = {}

    # key = f"{req.table}:{req.query}"

    # if key in app.state.column_memory:
    #     resolved_columns = app.state.column_memory[key]["columns"]

    print("RESOLVED COLUMNS:", resolved_columns)
    print("SCIL REGISTRY STATE:", scil_registry.get("state"))
    print("INTENT:", intent)
    print("FILTERS:", filters)

    print("FILTERS SENT TO PROMPT:", filters)

    prompt_template = build_agent_prompt(
         schema_text=schema_text,
         mapping_text=mapping_text,
         table_name=req.table,
         matched_terms=req.matched_terms,
         resolved_columns=resolved_columns,
         filters=filters
         
    )
    system_msg,user_msg=build_messages(prompt_template=prompt_template,user_query=req.query)
    print("SYSTEM MESSAGE",system_msg)
    print("USER MESSAGE",user_msg)

    agent1=get_agent(table=req.table,sys_msg=system_msg)

    res=agent1.invoke({"messages":[{"role":"user","content":user_msg}]})
   
    
    print("Result from tool...",res)
    tool=callTool(req.table)
    for msg in res.get('messages',[]):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                sql_query = msg.tool_calls[0]["args"]["query"]
                print("Query from LLM....",sql_query)
            
            if(isinstance(msg,ToolMessage)):
                print(msg.content)
               
    
    return {
        "table": req.table,
        "resolved_columns":resolved_columns,
        "filters":filters,
        "schema": schema_text,
        "mapping": mapping_text,
        "matched_terms": selected_table["matched_terms"],
        "intent":intent,
        # "system_msg":result["system_msg"],
        # "user_msg":result["user_msg"],
        # "agent_ready": True
    }

@app.post("/resolve_ambiguity")
def resolve_ambiguity(req: AmbiguityResolutionRequest):

    ctx = app.state.column_memory.get(req.session_id)

    if not ctx:
        return {"error": "Session expired or invalid session_id"}

    resolved_columns = list(ctx["resolved_columns"])

    for column in req.selections.values():

        if column not in resolved_columns:
            resolved_columns.append(column)
    

    return {
        "status": "READY_FOR_EXECUTION",
        "table": ctx["table"],
        "query": ctx["query"],
        "resolved_columns": resolved_columns
    }

    
