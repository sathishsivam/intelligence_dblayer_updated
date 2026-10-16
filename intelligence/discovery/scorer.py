from ...scoretablewithtd import (
    score_table,
    build_term_frequency,
)


def build_frequency(all_schema_texts):
    return build_term_frequency(all_schema_texts)


def calculate_score(
    query,
    schema_text,
    mapping_text,
    term_frequency,
    total_tables,
):
    return score_table(
        query=query,
        schema_text=schema_text,
        mapping_text=mapping_text,
        term_frequency=term_frequency,
        total_tables=total_tables,
    )