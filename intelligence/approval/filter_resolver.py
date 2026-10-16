from ...scil_value_resolver import build_scil_value_registry
from ...filterresolver import sql_intent_parser
from ...db import global_db


def resolve_filters(
    query,
    table,
    resolved_columns,
):

    registry = build_scil_value_registry(

        global_db._engine,

        table,
    )

    return sql_intent_parser(

        query=query,

        resolved_columns=resolved_columns,

        scil_registry=registry,
    )