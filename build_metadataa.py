from .db import global_db

from langchain_core.documents import Document
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

import re
from collections import defaultdict

# ------------------------------------------------------------
# STEP 1: Load tables from DB
# ------------------------------------------------------------

tables = global_db.get_usable_table_names()

docs = []

print("\nAvailable Tables:")
for t in tables:
    print(" -", t)

# ------------------------------------------------------------
# STEP 2: Build embedding documents (NO hardcoding logic)
# ------------------------------------------------------------

for table in tables:
    try:
        schema = global_db.get_table_info([table])

        # IMPORTANT: keep raw schema + table name
        content = f"""
TABLE_NAME:
{table}

SCHEMA:
{schema}
"""

        docs.append(
            Document(
                page_content=content,
                metadata={
                    "table_name": table,
                    "schema": schema
                }
            )
        )

    except Exception as e:
        print(f"Error processing {table}: {e}")

# ------------------------------------------------------------
# STEP 3: Create embeddings + FAISS index
# ------------------------------------------------------------

embedding = OllamaEmbeddings(model="nomic-embed-text")

vectorstore = FAISS.from_documents(
    documents=docs,
    embedding=embedding
)

retriever = vectorstore.as_retriever(
    search_kwargs={"k": 5}
)

# ------------------------------------------------------------
# STEP 4: Token-based table similarity (NO suffix rules)
# ------------------------------------------------------------

def tokenize(name: str):
    return set(
        token.lower()
        for token in re.split(r"[_\W]+", name)
        if token
    )

def table_similarity(a: str, b: str) -> float:
    ta = tokenize(a)
    tb = tokenize(b)

    if not ta or not tb:
        return 0.0

    return len(ta & tb) / len(ta | tb)

# ------------------------------------------------------------
# STEP 5: Discover related tables dynamically
# ------------------------------------------------------------

def discover_related_tables(table_name, all_tables, threshold=0.5):
    related = []

    for candidate in all_tables:

        if candidate == table_name:
            continue

        score = table_similarity(table_name, candidate)

        if score >= threshold:
            related.append((candidate, score))

    # sort best matches first
    related.sort(key=lambda x: x[1], reverse=True)

    return related

# ------------------------------------------------------------
# STEP 6: Expand retrieved candidates
# ------------------------------------------------------------

def expand_candidates(retrieved_docs):
    all_tables = global_db.get_usable_table_names()

    expanded = {}

    for doc in retrieved_docs:

        table = doc.metadata["table_name"]

        expanded[table] = {
            "source": "embedding"
        }

        related = discover_related_tables(table, all_tables)

        for rel_table, score in related:

            if rel_table not in expanded:

                expanded[rel_table] = {
                    "source": "schema_similarity",
                    "score": round(score, 3)
                }

    return expanded

# ------------------------------------------------------------
# STEP 7: Main retrieval function (USED IN OUR AGENT)
# ------------------------------------------------------------

def retrieve_tables(user_query: str):

    # Step 7.1: FAISS retrieval
    retrieved_docs = retriever.invoke(user_query)

    print("\nFAISS Retrieved Tables:")
    for d in retrieved_docs:
        print(" -", d.metadata["table_name"])

    # Step 7.2: Expand candidates
    expanded = expand_candidates(retrieved_docs)

    print("\nExpanded Candidate Tables:")
    for table, meta in expanded.items():
        print(f" - {table} ({meta})")

    return expanded

# ------------------------------------------------------------
# STEP 8: Example usage
# ------------------------------------------------------------

if __name__ == "__main__":

    query = "active customers by channel"

    candidates = retrieve_tables(query)