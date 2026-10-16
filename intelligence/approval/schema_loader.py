from ...columfrmtable import get_clean_schema
from ...db import global_db


def load_schema(table_name: str):

    return get_clean_schema(
        global_db._engine,
        [table_name]
    )