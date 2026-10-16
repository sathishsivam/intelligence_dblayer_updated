from .session_store import session_store


def get_session(session_id: str):
    return session_store.get(session_id)


def create_session(session_id: str, data: dict):
    session_store.create(session_id, data)


def update_session(session_id: str, patch: dict):
    session_store.update(session_id, patch)


def update_approved_session(
    session_id: str,
    table: str,
    schema_text: str,
    mapping_text: str,
    business_terms: list,
    metadata: dict,
    resolved_columns: list,
    filters: list,
    ambiguities: list,
):
    
    runtime_context = {
        "approved_table": table,
        "business_terms": business_terms,
        "metadata": metadata,
        "resolved_columns": resolved_columns,
        "filters": filters,
        "schema_text": schema_text,
        "mapping_text": mapping_text,
    }

    update_session(
        session_id,
        {
           "runtime_context": runtime_context,
            "status": "TABLE_APPROVED",
        },
    )


def mark_hitl_required(session_id: str):

    update_session(
        session_id,
        {
            "status": "HITL_REQUIRED",
        },
    )
def get_selected_table(session: dict, table_name: str):
    """
    Return the approved table object from ranked tables.
    """
    return next(
        (
            table
            for table in session.get("ranked_tables", [])
            if table["table"] == table_name
        ),
        None,
    )


def get_ranked_tables(session: dict):
    """
    Return ranked tables stored in the session.
    """
    return session.get("ranked_tables", [])