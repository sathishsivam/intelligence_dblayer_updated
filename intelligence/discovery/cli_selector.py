# from .discover_service import discover_tables
# from .manual_search import manual_table_search


# def discover_tables_cli(user_query: str):

#     result = discover_tables(user_query)

#     ranked_tables = result["ranked_tables"]

#     print("\nI found these potentially relevant tables:\n")

#     for i, table in enumerate(ranked_tables[:10]):

#         confidence = "LOW"

#         if table["score"] >= 120:
#             confidence = "HIGH"

#         elif table["score"] >= 50:
#             confidence = "MEDIUM"

#         print(f"""
# ━━━━━━━━━━━━━━━━━━━━━━
# Suggestion {i+1}

# Table:
# {table['table']}

# Confidence:
# {confidence}

# Score:
# {table['score']}

# Matched Terms:
# {", ".join(table["matched_terms"])}
# ━━━━━━━━━━━━━━━━━━━━━━
# """)


from .discover_service import discover_tables
from .manual_search import manual_table_search


def discover_tables_cli(user_query: str):
    """
    CLI workflow for manual testing.
    Used only from Swagger/local console.
    """

    result = discover_tables(user_query)

    ranked_tables = result["ranked_tables"]
    runtime_schema = result["runtime_schema"]

    print("\nI found these potentially relevant tables:\n")

    for i, table in enumerate(ranked_tables[:10]):

        confidence = "LOW"

        if table["score"] >= 120:
            confidence = "HIGH"
        elif table["score"] >= 50:
            confidence = "MEDIUM"

        print(f"""
━━━━━━━━━━━━━━━━━━━━━━
Suggestion {i + 1}

Table:
{table['table']}

Confidence:
{confidence}

Score:
{table['score']}

Matched Terms:
{", ".join(table["matched_terms"])}
━━━━━━━━━━━━━━━━━━━━━━
""")

    # --------------------------------------------------
    # User Selection
    # --------------------------------------------------

    selected = input(
        """
Select:
- number (1-10)
- full table name
- OR type: search <keyword>

Input: """
    ).strip()

    # --------------------------------------------------
    # Manual Search
    # --------------------------------------------------

    if selected.lower().startswith("search "):

        keyword = selected.replace("search ", "").strip()

        results = manual_table_search(keyword)

        print("\nManual Search Results:\n")

        for i, table in enumerate(results):
            print(f"{i + 1}. {table}")

        return {
            "status": "MANUAL_SEARCH",
            "results": results,
            "ranked_tables": ranked_tables,
        }

    approved_table = None

    # --------------------------------------------------
    # Number Selection
    # --------------------------------------------------

    if selected.isdigit():

        index = int(selected) - 1

        if 0 <= index < len(ranked_tables):
            approved_table = ranked_tables[index]

    # --------------------------------------------------
    # Table Name Selection
    # --------------------------------------------------

    else:

        for table in ranked_tables:

            if table["table"].lower() == selected.lower():
                approved_table = table
                break

    # --------------------------------------------------
    # Final Result
    # --------------------------------------------------

    if approved_table:

        print("\nApproved Table:\n")
        print(approved_table)

        return {
            "status": "APPROVED",
            "approved_table": approved_table,
            "runtime_schema": runtime_schema,
        }

    print("\nInvalid selection.")

    return {
        "status": "INVALID_SELECTION",
        "ranked_tables": ranked_tables,
    }