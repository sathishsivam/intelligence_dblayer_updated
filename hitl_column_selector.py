import uuid

# def build_hitl_payload(ambiguities,resolved_columns,schema_text, mapping_text):

#     hitl_view = []

#     for item in ambiguities:

#         hitl_view.append({
#             "term": item["term"],
#             "candidates": [
#                 {
#                     "column": c["column"],
#                     "score": c["score"],
#                     "business_term": c["business_term"]
#                 }
#                 for c in item["all_candidates"]
#             ]
#         })

#     return {
#         "status": "HITL_REQUIRED",
#         # ✅ already resolved confidently
#         "resolved_columns": resolved_columns,
#         "ambiguities": hitl_view,
#         "schema": schema_text,
#         "mapping": mapping_text
#     }


import uuid

def build_hitl_payload(
    ambiguities,
    resolved_columns,
    schema_text,
    mapping_text,
    table_name=None,
    query=None,
    session_store=None
):

    hitl_view = []

    for item in ambiguities:

        hitl_view.append({
            "term": item["term"],
            "candidates": sorted(
                [
                    {
                        "column": c["column"],
                        "score": c["score"],
                        "business_term": c.get("business_term")
                    }
                    for c in item["all_candidates"]
                ],
                key=lambda x: x["score"],
                reverse=True
            )
        })

    # 🔥 CREATE SESSION (this is the key fix)
    session_id = str(uuid.uuid4())

    if session_store is not None:
        session_store[session_id] = {
            "query": query,
            "table": table_name,
            "resolved_columns": resolved_columns,
            "ambiguities": ambiguities,
            "schema": schema_text,
            "mapping": mapping_text
        }

    return {
        "status": "HITL_REQUIRED",
        "session_id": session_id,
        "resolved_columns": resolved_columns,
        "ambiguities": hitl_view
    }