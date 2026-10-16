def build_discovery_response(
    suggestion,
    ranked_tables,
    runtime_schema,
):

    return {
        "suggestion": suggestion,
        "ranked_tables": ranked_tables,
        "runtime_schema": runtime_schema,
    }