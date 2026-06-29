from .mapping import prettify_column
from sqlalchemy import inspect
import re
from sqlalchemy import inspect

def get_clean_schema(engine, tables):
    inspector = inspect(engine)

    schema_text = ""
    mapping_text = "Column Mapping:\n"
    runtime_schema = {}
    seen_mappings = set()  # avoid duplicates

    for table in tables:
        columns = inspector.get_columns(table)
        runtime_schema[table] = {}
        col_list = []

        for col in columns:
            col_name = col["name"]
            col_type = str(col["type"])
            
            runtime_schema[table][col_name] = {
                "type": col_type,
                "nullable": col.get("nullable", True)
            }

            # Schema part
            col_list.append(f"{col_name}       ({col_type})")

            # Mapping part
            pretty_name = prettify_column(col_name)

            mapping_entry = f'- "{pretty_name}" → {col_name}'

            if mapping_entry not in seen_mappings:
                mapping_text += mapping_entry + "\n"
                seen_mappings.add(mapping_entry)

        schema_text += f"\nTable: {table}\nColumns:\n- " + "\n- ".join(col_list) + "\n"

    return schema_text, mapping_text,runtime_schema