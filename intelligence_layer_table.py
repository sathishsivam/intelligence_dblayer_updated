from build_metadata import retriever
from scoretablewithphlowvalue import score_table
from columfrmtable import get_clean_schema
from db import global_db
import re

def get_relevant_tables(user_query: str):
    
    ranked_tables = []
    docs = retriever.invoke(user_query)

    tables = []
    seen = set()
    context_list=[]
    updated_cols=[]

    for doc in docs:
        table_name = doc.metadata["table_name"]
        schema_text=doc.page_content

        schema_text,mapping_text=get_clean_schema(engine=global_db._engine,tables=[table_name])
        print(schema_text)
        print(mapping_text)

        #result=score_table(query=user_query,schema_text=schema_text)
        result = score_table(
                    query=user_query,
                    schema_text=schema_text,
                    mapping_text=mapping_text
                )
        ranked_tables.append({
        "table": table_name,
        "score": result["score"],
        "matched_terms": result["matched_terms"]
    })

    ranked_tables = sorted(
    ranked_tables,
    key=lambda x: x["score"],
    reverse=True
        )

    # print(ranked_tables)
    
    # for table in ranked_tables:
    #     print(table)

    approved_table_name = present_ranked_tables(ranked_tables)
    print("\nApproved Table:\n")
    print(approved_table_name)

    return approved_table_name

    # return ranked_tables

    # for idx,table in enumerate(ranked_tables):
    #     print(f""" 
    #           {idx+1}.Table:{table['table']}
    #           Score:{table['score']}
    #           Matched Terms: {table['matched_terms']}
    #         """)

    # selected=int(input("Select the correct table number"))
    # approved_table=ranked_tables[selected-1]
    # print("\nApproved Table:")
    # print(approved_table)

def present_ranked_tables(ranked_tables):

    print("\nI found these potentially relevant tables:\n")

    for idx, table in enumerate(ranked_tables[:5]):

        confidence = "HIGH"

        if table["score"] < 100:
            confidence = "MEDIUM"

        if table["score"] < 50:
            confidence = "LOW"

        print(f"""
━━━━━━━━━━━━━━━━━━━━━━
Suggestion {idx + 1}

Table:
{table['table']}

Confidence:
{confidence}

Why this table?
Matched Terms:
{", ".join(table['matched_terms'])}
━━━━━━━━━━━━━━━━━━━━━━
""")

    approved = input(
        "\nSelect a table by number or table name: "
    )

    return approved
    
get_relevant_tables("find out Beneficiary Bank address and types columns")




