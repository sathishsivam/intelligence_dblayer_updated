def build_hitl_payload(
    session_id,
    ambiguities,
    resolved_columns,
):
    """
    Build HITL response.
    Does NOT create a new session.
    Uses the existing session created during discover.
    """

    hitl_view = []

    for item in ambiguities:
        hitl_view.append(
            {
                "term": item["term"],
                "candidates": sorted(
                    [
                        {
                            "column": c["column"],
                            "score": c["score"],
                            "business_term": c.get("business_term"),
                        }
                        for c in item["all_candidates"]
                    ],
                    key=lambda x: x["score"],
                    reverse=True,
                ),
            }
        )

    return {
        "status": "HITL_REQUIRED",
        "session_id": session_id,
        "resolved_columns": resolved_columns,
        "ambiguities": hitl_view,
    }