from fastapi import FastAPI
from pydantic import BaseModel
from ..intelligence_layer_td import get_relevant_tables
from ..columfrmtable import get_clean_schema
from ..db import global_db
from ..buildPrompt import build_agent_prompt
from ..columnresolver import resolve_columns_from_terms


app=FastAPI()

class QueryRequest(BaseModel):
    query: str

class TableSelectionRequest(BaseModel):
    table: str
    query: str
    matched_terms: list[str] = []

@app.post("/discover_tables")
def discover_tables(req: QueryRequest):

    tables, ranked_tables = get_relevant_tables(req.query)

    app.state.ranked_tables = ranked_tables

    return {
        "query": req.query,
        "suggestion": tables,
        "ranked_tables": ranked_tables
    }


@app.post("/approve_table")
def approve_table(req: TableSelectionRequest):

    schema_text, mapping_text = get_clean_schema(
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
    
    resolved_columns = resolve_columns_from_terms(
    matched_terms=req.matched_terms,
    mapping_text=mapping_text
    )

    prompt = build_agent_prompt(
        user_query=req.query,
        schema_text=schema_text,
        mapping_text=mapping_text,
        table_name=selected_table["table"],
        matched_terms=req.matched_terms,
        resolved_columns=resolved_columns
    )

    print(prompt)
    app.state.current_prompt = prompt
    app.state.current_table = req.table

 

    return {
        "table": req.table,
        "schema": schema_text,
        "mapping": mapping_text,
        "matched_terms": selected_table["matched_terms"],
        "agent_ready": True
    }