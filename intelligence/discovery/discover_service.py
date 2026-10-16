from .retrieval import retrieve_documents
from .schema_loader import load_table_schema
from .scorer import (
    build_frequency,
    calculate_score,
)
from .ranker import rank_tables
from .models import build_discovery_response


def discover_tables(user_query: str):
    """
    Discover and rank relevant tables.
    Returns pure data.
    No CLI interaction.
    """

    all_schema_texts = []

    table_data = []

    runtime_schema = {}

    ranked_tables = []

    # =====================================================
    # STEP 1
    # Retrieve candidate tables
    # =====================================================

    docs = retrieve_documents(user_query)

    # =====================================================
    # STEP 2
    # Load schemas
    # =====================================================

    for doc in docs:

        table_name = doc.metadata["table_name"]

        schema_text, mapping_text, runtime = load_table_schema(
            table_name
        )

        runtime_schema[table_name] = runtime[table_name]

        all_schema_texts.append(
            schema_text + "\n" + mapping_text
        )

        table_data.append(
            {
                "table": table_name,
                "schema_text": schema_text,
                "mapping_text": mapping_text,
            }
        )

    # =====================================================
    # STEP 3
    # Build global term frequency
    # =====================================================

    term_frequency = build_frequency(
        all_schema_texts
    )

    total_tables = len(all_schema_texts)

    # =====================================================
    # STEP 4
    # Calculate score
    # =====================================================

    for table in table_data:

        score = calculate_score(
            query=user_query,
            schema_text=table["schema_text"],
            mapping_text=table["mapping_text"],
            term_frequency=term_frequency,
            total_tables=total_tables,
        )

        ranked_tables.append(
            {
                "table": table["table"],
                "score": score["score"],
                "matched_terms": score["matched_terms"],
            }
        )

    # =====================================================
    # STEP 5
    # Rank
    # =====================================================

    ranked_tables = rank_tables(
        ranked_tables
    )

    suggestion = ranked_tables[0] if ranked_tables else None

    # =====================================================
    # STEP 6
    # Return response
    # =====================================================

    return build_discovery_response(
        suggestion=suggestion,
        ranked_tables=ranked_tables,
        runtime_schema=runtime_schema,
    )