from ...db import global_db


def manual_table_search(keyword: str):

    all_tables = global_db.get_usable_table_names()

    return [
        table
        for table in all_tables
        if keyword.lower() in table.lower()
    ]