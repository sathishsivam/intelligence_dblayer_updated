"""
Approval Service

Orchestrates the complete table approval workflow.
"""

from ...intelligence.session.session_manager import (
    get_session,
    update_approved_session,
    mark_hitl_required,
    get_selected_table,
)

from ...intelligence.approval.schema_loader import load_schema
from ...intelligence.approval.metadata_builder import build_metadata
from ...intelligence.approval.column_resolver import resolve_table_columns
from ...intelligence.approval.filter_resolver import resolve_filters
from ...hitl_column_selector import build_hitl_payload


def approve_table(
    request,
    session_store,
):
    """
    Complete Approval Workflow
    """

    # =====================================================
    # SESSION
    # =====================================================

    session = get_session(request.session_id)

    if session is None:
        return {
            "error": "Invalid session_id"
        }

    # =====================================================
    # LOAD SCHEMA
    # =====================================================

    schema_text, mapping_text, runtime_schema = load_schema(
        request.table
    )

    # =====================================================
    # BUILD METADATA
    # =====================================================

    metadata = build_metadata(
        table_name=request.table,
        runtime_schema=runtime_schema,
    )

    # =====================================================
    # VALIDATE TABLE
    # =====================================================

    selected_table = get_selected_table(
        session,
        request.table,
    )

    if selected_table is None:
        return {
            "error": "Table not found"
        }

    # =====================================================
    # COLUMN RESOLUTION
    # =====================================================

    scil_result = resolve_table_columns(
        request.matched_terms,
        mapping_text,
    )

    resolved_columns = scil_result["resolved_columns"]
    ambiguities = scil_result["ambiguities"]

    # =====================================================
    # FILTER RESOLUTION
    # =====================================================

    intent = resolve_filters(
        request.query,
        request.table,
        resolved_columns,
    )

    filters = intent["filters"]

    # =====================================================
    # UPDATE SESSION
    # =====================================================

    update_approved_session(
    session_id=request.session_id,
    table=request.table,
    schema_text=schema_text,
    mapping_text=mapping_text,
    business_terms=request.matched_terms,
    metadata=metadata,
    resolved_columns=resolved_columns,
    filters=filters,
    ambiguities=ambiguities,
)

    # =====================================================
    # HITL
    # =====================================================

    if ambiguities:

        mark_hitl_required(request.session_id)

        # return build_hitl_payload(
        #     ambiguities=ambiguities,
        #     resolved_columns=resolved_columns,
        #     schema_text=schema_text,
        #     mapping_text=mapping_text,
        #     table_name=request.table,
        #     query=request.query,
        #     session_store=session_store.sessions,
        # )
        return build_hitl_payload(
            session_id=request.session_id,
            ambiguities=ambiguities,
            resolved_columns=resolved_columns,
        )

    # =====================================================
    # READY
    # =====================================================

    return {
        "status": "READY_FOR_EXECUTION",

        "session_id": request.session_id,

        "table": request.table,

        "metadata": metadata,

        "resolved_columns": resolved_columns,

        "filters": filters,
    }