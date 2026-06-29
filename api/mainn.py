from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

from ..intelligence_layer_td import get_relevant_tables
from ..columfrmtable import get_clean_schema
from ..db import global_db
from ..scil_resolver import resolve_columns
from ..scil_value_resolver import build_scil_value_registry
from ..filterresolver import sql_intent_parser
from ..buildPrompt4ChatPromptTemplate import build_agent_prompt
from ..promptutils import build_messages
from ..myagent import get_agent
from ..query_column import extract_columns_from_query
import re
import ast
from langchain_core.messages import ToolMessage
import pandas as pd

app = FastAPI()

# =====================================================
# SESSION STORE (REPLACES app.state hacks)
# =====================================================
class SessionStore:
    def __init__(self):
        self.sessions = {}

    def create(self, session_id: str, data: dict):
        self.sessions[session_id] = data

    def get(self, session_id: str):
        return self.sessions.get(session_id)

    def update(self, session_id: str, patch: dict):
        if session_id in self.sessions:
            self.sessions[session_id].update(patch)

session_store = SessionStore()

# =====================================================
# CORS
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# REQUEST MODELS
# =====================================================
class QueryRequest(BaseModel):
    query: str


class TableSelectionRequest(BaseModel):
    session_id: str
    table: str
    query: str
    matched_terms: list[str] = []


class AmbiguityResolutionRequest(BaseModel):
    session_id: str
    selections: dict[str, str]


class ExecuteRequest(BaseModel):
    session_id: str


# =====================================================
# 1. DISCOVER TABLES
# =====================================================
@app.post("/discover_tables")
def discover_tables(req: QueryRequest):

    session_id = str(uuid.uuid4())

    tables, ranked_tables, runtime_schema = get_relevant_tables(req.query)

    session_store.create(session_id, {
        "session_id": session_id,
        "query": req.query,
        "ranked_tables": ranked_tables,
        "status": "DISCOVERED"
    })

    return {
        "session_id": session_id,
        "query": req.query,
        "suggestion": tables,
        "ranked_tables": ranked_tables
    }


# =====================================================
# 2. APPROVE TABLE + COLUMN RESOLUTION + HITL CHECK
# =====================================================
@app.post("/approve_table")
def approve_table(req: TableSelectionRequest):

    session = session_store.get(req.session_id)
    if not session:
        return {"error": "Invalid session_id"}

    schema_text, mapping_text, runtime_schema = get_clean_schema(
        global_db._engine,
        [req.table]
    )

    selected_table = next(
        (t for t in session["ranked_tables"] if t["table"] == req.table),
        None
    )

    if not selected_table:
        return {"error": "Table not found"}

    # =====================================================
    # COLUMN RESOLUTION
    # =====================================================
    scil_result = resolve_columns(
        matched_terms=req.matched_terms,
        mapping_text=mapping_text
    )

    resolved_columns = scil_result["resolved_columns"]
    ambiguities = scil_result["ambiguities"]

    # =====================================================
    # SCIL + FILTER INTENT
    # =====================================================
    scil_registry = build_scil_value_registry(
        global_db._engine,
        req.table
    )

    intent = sql_intent_parser(
        query=req.query,
        resolved_columns=resolved_columns,
        scil_registry=scil_registry
    )

    filters = intent.get("filters", [])

    # =====================================================
    # STORE SESSION CONTEXT
    # =====================================================
    session_store.update(req.session_id, {
        "table": req.table,
        "schema_text": schema_text,
        "mapping_text": mapping_text,
        "resolved_columns": resolved_columns,
        "filters": filters,
        "ambiguities": ambiguities,
        "status": "TABLE_APPROVED"
    })

    # =====================================================
    # HITL CHECK
    # =====================================================
    if ambiguities:
        session_store.update(req.session_id, {
            "status": "HITL_REQUIRED"
        })

        return {
            "status": "HITL_REQUIRED",
            "session_id": req.session_id,
            "ambiguities": ambiguities,
            "resolved_columns": resolved_columns,
            "schema": schema_text,
            "mapping": mapping_text
        }

    return {
        "status": "READY_FOR_EXECUTION",
        "session_id": req.session_id,
        "resolved_columns": resolved_columns,
        "filters": filters
    }


# =====================================================
# 3. RESOLVE AMBIGUITY
# =====================================================
@app.post("/resolve_ambiguity")
def resolve_ambiguity(req: AmbiguityResolutionRequest):

    session = session_store.get(req.session_id)

    if not session:
        return {"error": "Session expired or invalid"}

    resolved_columns = session.get("resolved_columns", [])

    for col in req.selections.values():
        if col not in resolved_columns:
            resolved_columns.append(col)

    session_store.update(req.session_id, {
        "resolved_columns": resolved_columns,
        "status": "RESOLVED"
    })

    return {
        "status": "READY_FOR_EXECUTION",
        "session_id": req.session_id,
        "resolved_columns": resolved_columns
    }


# =====================================================
# 4. EXECUTE (FINAL STEP 🚀)
# =====================================================
@app.post("/execute")
def execute(req: ExecuteRequest):

    session = session_store.get(req.session_id)

    if not session:
        return {"error": "Invalid session_id"}

    if session.get("status") not in ["RESOLVED", "TABLE_APPROVED"]:
        return {
            "error": "Session not ready for execution",
            "status": session.get("status")
        }

    table = session["table"]
    query = session["query"]
    schema_text = session["schema_text"]
    mapping_text = session["mapping_text"]
    resolved_columns = session.get("resolved_columns", [])
    filters = session.get("filters", [])

    # =====================================================
    # BUILD PROMPT
    # =====================================================
    prompt_template = build_agent_prompt(
        schema_text=schema_text,
        mapping_text=mapping_text,
        table_name=table,
        matched_terms=[],
        resolved_columns=resolved_columns,
        filters=filters
    )

    system_msg, user_msg = build_messages(
        prompt_template=prompt_template,
        user_query=query
    )

    # =====================================================
    # RUN AGENT
    # =====================================================
    agent = get_agent(table=table, sys_msg=system_msg)

    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": user_msg
            }
        ]
    })

    # =====================================================
    # EXTRACT SQL (optional debug)
    # =====================================================
    sql_query = None
    

    for msg in result.get("messages", []):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            sql_query = msg.tool_calls[0]["args"]["query"]
            columns=extract_columns_from_query(sql_query)
         # ✅ Extract DB result safely
        if isinstance(msg, ToolMessage):
                try:
                    print(msg.content)
                    cleaned = re.sub(r'\b0+(\d+)', r'\1', msg.content)
                    data = ast.literal_eval(msg.content)
                
                    if isinstance(data, list):
                        df = pd.DataFrame(data,columns=columns)
                        print(df)

                except Exception as e:
                    print("⚠️ Data parsing error:", e)
                    df = None

    # =====================================================
    # UPDATE SESSION
    # =====================================================
    session_store.update(req.session_id, {
        "status": "EXECUTED",
        "last_sql": sql_query
    })

    return {
        "status": "EXECUTED",
        "session_id": req.session_id,
        "table": table,
        "query": query,
        "resolved_columns": resolved_columns,
        "filters": filters,
        "sql": sql_query,
        "result": result
    }

