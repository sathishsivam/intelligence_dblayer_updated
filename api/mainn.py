
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import uuid
import re
import ast
import json
import datetime
import plotly.io as pio
import numpy as np

from ..intelligence_layer_td import get_relevant_tables
from ..columfrmtable import get_clean_schema
from ..db import global_db
# from ..hilt import detect_ambiguities
from ..hitl_column_selector import build_hitl_payload
from ..scil_resolver import resolve_columns
from ..scil_value_resolver import build_scil_value_registry
from ..filterresolver import sql_intent_parser
from ..buildPrompt4ChatPromptTemplate import build_agent_prompt
from ..promptutils import build_messages
from ..myagent import get_agent
from ..query_column import extract_columns_from_query

from langchain_core.messages import ToolMessage
import pandas as pd

from ..visualization_agent.profiler import DataProfiler
from ..insight_agent.service import InsightService
from ..serializer import make_json_serializable
from ..result_engine.aggregation import AggregationEngine
from ..result_engine.visualization import VisualizationEngine

from ..intelligence.discovery.discover_service import discover_tables
# from ..intelligence.discovery.cli_selector import discover_tables_cli

from ..intelligence.approval.schema_loader import load_schema
from ..intelligence.session.session_store import session_store
from ..intelligence.session.session_manager import (
    get_session,
    update_approved_session,
    mark_hitl_required,
)

from ..intelligence.approval.column_resolver import resolve_table_columns
from ..intelligence.approval.filter_resolver import resolve_filters
from ..intelligence.approval.response_builder import (
    build_hitl_response,
    build_ready_response,
)

from ..intelligence.session.session_manager import (
    update_approved_session,
    mark_hitl_required,
    get_ranked_tables,
    get_selected_table,
    update_session,
)

from ..intelligence.approval.metadata_builder import build_metadata
from ..intelligence.approval.approve_service import (
    approve_table as approve_table_service,
)

from ..api.routes.api_discovery import router as api_discovery_router
from ..rag.router import router as rag_router

# =====================================================
# ORCHESTRATION ROUTER
# =====================================================
from ..orchestration.api import router as orchestration_router

from ..auth.router import router as auth_router


app = FastAPI()

# =====================================================
# ROUTERS
# =====================================================

app.include_router(auth_router)

app.include_router(rag_router)

app.include_router(api_discovery_router)

app.include_router(orchestration_router)


# =====================================================
# SESSION STORE (REPLACES app.state hacks)
# =====================================================

# class SessionStore:
#     def __init__(self):
#         self.sessions = {}

#     def create(self, session_id: str, data: dict):
#         self.sessions[session_id] = data

#     def get(self, session_id: str):
#         return self.sessions.get(session_id)

#     def update(self, session_id: str, patch: dict):
#         if session_id in self.sessions:
#             self.sessions[session_id].update(patch)


# =====================================================
# GLOBAL SINGLETONS
# =====================================================

data_profiler = DataProfiler()
insight_service = InsightService()
aggregation_engine = AggregationEngine()
visualization_engine = VisualizationEngine()


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


class AnalysisRequest(BaseModel):
    session_id: str
    insight_id: str


class VisualizationRequest(BaseModel):
    session_id: str


# =====================================================
# 1. DISCOVER TABLES
# =====================================================

@app.post("/discover_tables")
def discover_tables_api(req: QueryRequest):

    session_id = str(uuid.uuid4())

    result = discover_tables(req.query)

    # tables, ranked_tables, runtime_schema = get_relevant_tables(req.query)

    session_store.create(
        session_id,
        {
            "session_id": session_id,
            "query": req.query,
            "ranked_tables": result["ranked_tables"],
            "status": "DISCOVERED",
        },
    )

    print("DISCOVER STORE :", id(session_store))

    return {
        "session_id": session_id,
        "query": req.query,
        "suggestion": result["suggestion"],
        "ranked_tables": result["ranked_tables"],
    }


# =====================================================
# 2. APPROVE TABLE + COLUMN RESOLUTION + HITL CHECK
# =====================================================

@app.post("/approve_table")
def approve_table(req: TableSelectionRequest):

    print(session_store.get(req.session_id))
    print("APPROVE STORE :", id(session_store))

    return approve_table_service(
        request=req,
        session_store=session_store,
    )


# =====================================================
# 3. RESOLVE AMBIGUITY
# =====================================================

@app.post("/resolve_ambiguity")
def resolve_ambiguity(req: AmbiguityResolutionRequest):

    session = session_store.get(req.session_id)

    runtime = session.get("runtime_context")

    if runtime is None:
        return {"error": "Runtime context missing"}

    resolved_columns = runtime.get("resolved_columns", [])

    for col in req.selections.values():
        if col not in resolved_columns:
            resolved_columns.append(col)

    runtime["resolved_columns"] = resolved_columns

    session_store.update(
        req.session_id,
        {
            "runtime_context": runtime,
            "status": "RESOLVED",
        },
    )

    return {
        "status": "READY_FOR_EXECUTION",
        "session_id": req.session_id,
        "resolved_columns": resolved_columns,
    }


# =====================================================
# 4. EXECUTE (FINAL STEP 🚀)
# =====================================================

@app.post("/execute")
def execute(req: ExecuteRequest):

    session = get_session(req.session_id)

    print("=" * 80)
    print("EXECUTE SESSION")
    print(session)
    print("=" * 80)

    print(
        "SESSION KEYS:",
        session.keys() if session else None,
    )

    if session is None:
        return {"error": "Invalid session_id"}

    if session.get("status") not in [
        "TABLE_APPROVED",
        "RESOLVED",
    ]:
        return {
            "error": "Session not ready for execution",
            "status": session.get("status"),
        }

    # =====================================================
    # LOAD RUNTIME CONTEXT
    # =====================================================

    runtime = session.get("runtime_context")

    print("EXECUTE STORE :", id(session_store))

    if runtime is None:
        return {
            "error": "Runtime context missing"
        }

    table = runtime["approved_table"]
    query = session["query"]

    schema_text = runtime["schema_text"]
    mapping_text = runtime["mapping_text"]

    resolved_columns = runtime.get(
        "resolved_columns",
        [],
    )

    filters = runtime.get(
        "filters",
        [],
    )

    metadata = runtime.get(
        "metadata",
    )

    # =====================================================
    # BUILD PROMPT
    # =====================================================

    prompt_template = build_agent_prompt(
        schema_text=schema_text,
        mapping_text=mapping_text,
        table_name=table,
        matched_terms=[],
        resolved_columns=resolved_columns,
        filters=filters,
    )

    system_msg, user_msg = build_messages(
        prompt_template=prompt_template,
        user_query=query,
    )

    # =====================================================
    # RUN AGENT
    # =====================================================

    agent = get_agent(
        table=table,
        sys_msg=system_msg,
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_msg,
                }
            ]
        }
    )

    # =====================================================
    # EXTRACT SQL
    # =====================================================

    sql_query = None
    df = None
    profile = None
    insight = None

    for msg in result.get("messages", []):

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            sql_query = msg.tool_calls[0]["args"]["query"]
            columns = extract_columns_from_query(sql_query)

        # =================================================
        # EXTRACT DB RESULT SAFELY
        # =================================================

        if isinstance(msg, ToolMessage):

            try:

                content = msg.content

                print("=" * 100)
                print(type(content))
                print(repr(content))
                print("=" * 100)

                if isinstance(content, list):

                    data = content

                elif isinstance(content, str):

                    try:
                        data = json.loads(content)

                    except Exception:

                        try:
                            data = ast.literal_eval(content)

                        except Exception:

                            safe_globals = {
                                "__builtins__": {},
                                "datetime": datetime,
                            }

                            data = eval(
                                content,
                                safe_globals,
                                {},
                            )

                else:

                    data = content

                if isinstance(data, list):

                    df = pd.DataFrame(
                        data,
                        columns=columns,
                    )

                    print(df)

                else:

                    print(
                        "Unexpected ToolMessage format"
                    )

                    print(type(data))

            except Exception as e:

                print(
                    "⚠️ Data parsing error:",
                    e,
                )

                df = None

    # =====================================================
    # INSIGHT
    # =====================================================

    if df is not None:

        if df.empty:

            insight = {
                "recommended": "No Data",
                "options": [],
            }

        else:

            profile = data_profiler.profile(df)

            profile = make_json_serializable(profile)

            print(profile)

            try:

                insight = insight_service.recommend(
                    query=query,
                    sql=sql_query,
                    dataframe=df,
                    profile=profile,
                )

            except Exception as ex:

                print(
                    "Insight Agent Error:",
                    ex,
                )

                insight = {
                    "recommended": "View Raw Table",
                    "options": [
                        {
                            "id": "table",
                            "title": "View Raw Table",
                            "action": "table",
                        }
                    ],
                }

            update_session(
                req.session_id,
                {
                    "status": "INSIGHT_READY",
                    "last_sql": sql_query,
                    "profile": profile,
                    "insight": insight,
                    "dataframe": df.to_dict("records"),
                    "columns": df.columns.tolist(),
                },
            )

    return {
        "status": "INSIGHT_READY",
        "session_id": req.session_id,
        "sql": sql_query,
        "row_count": 0 if df is None else len(df),
        "column_count": 0 if df is None else len(df.columns),
        "insights": insight,
    }


# =====================================================
# 5. EXECUTE ANALYSIS
# =====================================================

@app.post("/execute_analysis")
def execute_analysis(req: AnalysisRequest):

    session = session_store.get(
        req.session_id
    )

    if not session:

        return {
            "error": "Invalid session"
        }

    if "insight" not in session:

        return {
            "error": "No insights available"
        }

    if "dataframe" not in session:

        return {
            "error": "No dataframe available"
        }

    insight = session["insight"]

    dataframe = pd.DataFrame(
        session["dataframe"]
    )

    # ------------------------------------------
    # Find selected insight
    # ------------------------------------------

    selected = next(

        (
            option
            for option in insight["options"]
            if option["id"] == req.insight_id
        ),

        None,
    )

    if selected is None:

        return {
            "error": "Insight not found"
        }

    execution = selected.get(
        "execution"
    )

    # ------------------------------------------
    # View Raw Table
    # ------------------------------------------

    if execution is None:

        session_store.update(
            req.session_id,
            {
                "analysis_df": dataframe.to_dict(
                    "records"
                ),
                "analysis_columns": dataframe.columns.tolist(),
                "selected_analysis": selected,
            },
        )

        return {
            "status": "SUCCESS",
            "title": selected["title"],
            "rows": len(dataframe),
            "columns": len(dataframe.columns),
            "table": dataframe.to_dict("records"),
        }

    # ------------------------------------------
    # Aggregation
    # ------------------------------------------

    analysis_df = aggregation_engine.execute(
        dataframe,
        execution,
    )

    analysis_df = analysis_df.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    analysis_df = analysis_df.where(
        analysis_df.notna(),
        None,
    )

    session_store.update(
        req.session_id,
        {
            "analysis_df": analysis_df.to_dict(
                "records"
            ),
            "analysis_columns": analysis_df.columns.tolist(),
            "selected_analysis": selected,
        },
    )

    print("=" * 80)
    print("Checking Analysis DataFrame")
    print("=" * 80)

    print(analysis_df)

    print("\nNaN count:")
    print(analysis_df.isna().sum())

    print("\nInfinity count:")

    print(
        analysis_df.select_dtypes(
            include="number"
        ).apply(
            lambda c: np.isinf(c).sum()
        )
    )

    return {
        "status": "SUCCESS",
        "title": selected["title"],
        "rows": len(analysis_df),
        "columns": len(analysis_df.columns),
        "table": analysis_df.to_dict(
            "records"
        ),
    }


# =====================================================
# GENERATE VISUALIZATION
# =====================================================

def generate_visualization(
    session_id: str,
):

    """
    Generates the Plotly chart JSON
    from the current session.
    """

    session = session_store.get(
        session_id
    )

    if not session:

        raise HTTPException(
            status_code=404,
            detail="Invalid session",
        )

    if "analysis_df" not in session:

        raise HTTPException(
            status_code=400,
            detail="Run execute_analysis first",
        )

    df = pd.DataFrame(
        session["analysis_df"]
    )

    execution = session[
        "selected_analysis"
    ].get("execution")

    if execution is None:

        raise HTTPException(
            status_code=400,
            detail="No visualization available.",
        )

    chart = visualization_engine.render(
        df=df,
        execution=execution,
    )

    return {
        "title": session[
            "selected_analysis"
        ]["title"],
        "chart": chart,
    }


# =====================================================
# VISUALIZATION
# =====================================================

@app.post("/visualization")
def visualization(
    req: VisualizationRequest,
):

    result = generate_visualization(
        req.session_id
    )

    return {
        "status": "SUCCESS",
        "title": result["title"],
        "chart": result["chart"],
    }


# =====================================================
# VISUALIZATION PREVIEW
# =====================================================

@app.post("/visualization/preview")
def visualization_preview(
    req: VisualizationRequest,
):

    result = generate_visualization(
        req.session_id
    )

    fig = pio.from_json(
        json.dumps(result["chart"])
    )

    image = fig.to_image(
        format="png",
        width=1400,
        height=800,
        scale=2,
    )

    return Response(
        content=image,
        media_type="image/png",
    )


# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
def health():

    return {
        "status": "UP",
        "service": "AIZillon Backend",
        "database": "CONNECTED",
        "llm": "READY",
    }
