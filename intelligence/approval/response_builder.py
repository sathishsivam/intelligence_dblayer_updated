
from ...hitl_column_selector import build_hitl_payload

"""
Build final approve response.
"""
def build_ready_response(
    session_id,
    table,
    metadata,
    resolved_columns,
    filters,
):

    return {

        "status": "READY_FOR_EXECUTION",

        "session_id": session_id,

        "table": table,

        "metadata": metadata,

        "resolved_columns": resolved_columns,

        "filters": filters,
    }



def build_hitl_response(

    ambiguities,

    resolved_columns,

    schema_text,

    mapping_text,

    table_name,

    query,

    session_store,

):

    return build_hitl_payload(

        ambiguities=ambiguities,

        resolved_columns=resolved_columns,

        schema_text=schema_text,

        mapping_text=mapping_text,

        table_name=table_name,

        query=query,

        session_store=session_store,
    )
