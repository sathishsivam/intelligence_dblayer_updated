from ...scil_resolver import resolve_columns


def resolve_table_columns(
    matched_terms,
    mapping_text,
):

    return resolve_columns(

        matched_terms=matched_terms,

        mapping_text=mapping_text,
    )