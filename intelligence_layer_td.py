
from .build_metadata import retriever
from .columfrmtable import get_clean_schema
from .scoretablewithtd import score_table,build_term_frequency
from .db import global_db

import re
from collections import defaultdict


# # =====================================================
# # INTELLIGENCE LAYER: TABLE SIMILARITY EXPANSION
# # =====================================================

# def tokenize(name: str):
#     return set(
#         token.lower()
#         for token in re.split(r"[_\W]+", name)
#         if token
#     )

# def table_similarity(a: str, b: str) -> float:
#     ta = tokenize(a)
#     tb = tokenize(b)

#     if not ta or not tb:
#         return 0.0

#     return len(ta & tb) / len(ta | tb)

# def discover_related_tables(table_name, all_tables, threshold=0.5):
#     related = []

#     for candidate in all_tables:

#         if candidate == table_name:
#             continue

#         score = table_similarity(table_name, candidate)

#         if score >= threshold:
#             related.append(candidate)

#     return related

# def expand_tables(retrieved_docs):

#     all_tables = global_db.get_usable_table_names()

#     expanded_docs = []
#     seen = set()

#     for doc in retrieved_docs:

#         table = doc.metadata["table_name"]

#         if table not in seen:
#             expanded_docs.append(doc)
#             seen.add(table)

#         # expand related tables dynamically
#         related = discover_related_tables(table, all_tables)

#         for rel_table in related:

#             if rel_table not in seen:

#                 # create synthetic doc for downstream pipeline
#                 expanded_docs.append(
#                     type(doc)(
#                         page_content=doc.page_content,
#                         metadata={"table_name": rel_table}
#                     )
#                 )

#                 seen.add(rel_table)

#     return expanded_docs


# =====================================================
# INTENT: MANUAL + AUTO HYBRID SUPPORT
# =====================================================

def manual_table_search(keyword: str):
    """Fallback when embeddings miss correct table"""
    all_tables = global_db.get_usable_table_names()

    return [
        t for t in all_tables
        if keyword.lower() in t.lower()
    ]

# =====================================================
# MAIN PIPELINE
# =====================================================

def get_relevant_tables(user_query: str):

    ranked_tables = []

    # =====================================================
    # STEP 1: FAISS RETRIEVAL
    # =====================================================

    docs = retriever.invoke(user_query)

    # =====================================================
    # STEP 2: INTELLIGENCE EXPANSION (NEW LAYER)
    # =====================================================
    # docs = expand_tables(docs)
    
    all_schema_texts = []

    table_data = []

    all_runtime_schema = {}

    # =====================================================
    # PREPARE ALL SCHEMAS
    # =====================================================
    for doc in docs:

        table_name = doc.metadata["table_name"]
       
        schema_text, mapping_text,runtime_schema = get_clean_schema(
            engine=global_db._engine,
            tables=[table_name]
        )
        all_runtime_schema[table_name] = runtime_schema[table_name]


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

    for idx, table in enumerate(ranked_tables[:10]):

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
                            """
                    Select:
                    - number (1-10)
                    - full table name
                    - OR type: search <keyword>

                    Input: """).strip()

    approved_table = None

    # -----------------------------
    # CASE 1: SEARCH MODE
    # -----------------------------
    if selected.lower().startswith("search "):

        keyword = selected.replace("search ", "").strip()

        results = manual_table_search(keyword)

        print("\nManual Search Results:")

        for i, t in enumerate(results):
            print(f"{i+1}. {t}")

        return {
            "status": "MANUAL_SEARCH",
            "results": results,
            "ranked_tables": ranked_tables
        }


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

        return approved_table,ranked_tables,all_runtime_schema
    

    else:

        print("\nInvalid selection")

        return None


