"""
Return runtime schema for approved table.
"""


def build_runtime_schema(
    runtime_schema: dict,
    table_name: str,
):

    return runtime_schema.get(
        table_name,
        {},
    )