
from .build_metadata import retriever
from .columfrmtable import get_clean_schema
from .scoretablewithtd import score_table,build_term_frequency
from .db import global_db




def get_relevant_tables(user_query: str):

    ranked_tables = []

    docs = retriever.invoke(user_query)

    all_schema_texts = []

    table_data = []

    # =====================================================
    # PREPARE ALL SCHEMAS
    # =====================================================
    for doc in docs:

        table_name = doc.metadata["table_name"]

        schema_text, mapping_text = get_clean_schema(
            engine=global_db._engine,
            tables=[table_name]
        )

        combined_text = (
            schema_text + "\n" + mapping_text
        )

        all_schema_texts.append(combined_text)

        table_data.append({
            "table_name": table_name,
            "schema_text": schema_text,
            "mapping_text": mapping_text
        })

    # =====================================================
    # BUILD GLOBAL TERM FREQUENCY
    # =====================================================
    term_frequency = build_term_frequency(
        all_schema_texts
    )

    total_tables = len(all_schema_texts)

    # =====================================================
    # SCORE TABLES
    # =====================================================
    for item in table_data:

        result = score_table(
            query=user_query,
            schema_text=item["schema_text"],
            mapping_text=item["mapping_text"],
            term_frequency=term_frequency,
            total_tables=total_tables
        )

        ranked_tables.append({
            "table": item["table_name"],
            "score": result["score"],
            "matched_terms": result["matched_terms"]
        })

    # =====================================================
    # SORT TABLES
    # =====================================================
    ranked_tables = sorted(
        ranked_tables,
        key=lambda x: x["score"],
        reverse=True
    )

    # =====================================================
    # DISPLAY RESULTS
    # =====================================================
    print("\nI found these potentially relevant tables:\n")

    for idx, table in enumerate(ranked_tables[:5]):

        confidence = "LOW"

        if table["score"] >= 120:
            confidence = "HIGH"

        elif table["score"] >= 50:
            confidence = "MEDIUM"

        matched = ", ".join(
            table["matched_terms"]
        )

        print(f"""
━━━━━━━━━━━━━━━━━━━━━━
Suggestion {idx + 1}

Table:
{table['table']}

Confidence:
{confidence}

Score:
{table['score']}

Matched Terms:
{matched}
━━━━━━━━━━━━━━━━━━━━━━
""")

    # =====================================================
    # HUMAN IN LOOP
    # =====================================================
    selected = input(
        "\nSelect a table by number or table name: "
    ).strip()

    approved_table = None

    if selected.isdigit():

        idx = int(selected) - 1

        if 0 <= idx < len(ranked_tables):

            approved_table = ranked_tables[idx]

    else:

        for table in ranked_tables:

            if table["table"].lower() == selected.lower():

                approved_table = table

                break

    # =====================================================
    # FINAL OUTPUT
    # =====================================================
    if approved_table:

        print("\nApproved Table:")
        print(approved_table)

        return approved_table,ranked_tables

    else:

        print("\nInvalid selection")

        return None


# =========================================================
# TEST
# =========================================================
# perfect_table=get_relevant_tables(
#     "Find out Format sequence number, format field enabled and validation columns"
# )

