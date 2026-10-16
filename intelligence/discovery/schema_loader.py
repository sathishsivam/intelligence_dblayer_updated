from ...columfrmtable import get_clean_schema
from ...db import global_db


def load_table_schema(table_name: str):
    """
    Load schema, mapping and runtime schema.
    """

    return get_clean_schema(
        engine=global_db._engine,
        tables=[table_name]
    )