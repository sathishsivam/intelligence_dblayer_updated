"""
Build Business Metadata for approved table.
"""


def build_metadata(
    table_name: str,
    runtime_schema: dict,
):
    """
    Convert runtime schema into UI-friendly metadata.
    """

    table = runtime_schema.get(table_name, {})
    metadata_columns = []
    

    for column_name,info  in table.items():

        metadata_columns.append({

            "column_name": column_name    ,

            "business_name": column_name.replace("_", " ").title(),

            "datatype": info.get("type"),

            "nullable": info.get(
                "nullable",
                True,
            ),

            "primary_key": info.get(
                "primary_key",
                False,
            ),
        })

    metadata = {

        "summary": {

            "table_name": table_name,

            "row_count": 0,

            "column_count": len(metadata_columns),

            "relationship_count": 0,

            "business_term_count": len(metadata_columns),
        },

        "columns": metadata_columns,

        "relationships": [],
    }

    return metadata