from langchain_core.prompts import ChatPromptTemplate


def build_agent_prompt(
    schema_text: str,
    mapping_text: str,
    table_name: str,
    matched_terms,
    resolved_columns,
    filters
):

    matched_section = "\n".join(
        f"- {term}" for term in matched_terms
    ) if matched_terms else "None"

    resolved_section = "\n".join(
        f"- {col}" for col in resolved_columns
    ) if resolved_columns else "None"

    if filters:
        filter_section = "\n".join(
    f"- {f['column']} {f.get('operator', '=')} '{f['value']}'"
    for f in filters
    )
    else:
        filter_section = "None"

     #  NEW: FILTER SECTION

    # if filters:
    #     filter_section = "\n".join(
    #         f"- {k}: {v}" for k, v in filters.items()
    #     )
    # else:
    #     filter_section = "None"


    system_prompt = f"""
You are an Oracle SQL Agent.

You have access to a SQL execution tool.

YOU MUST ALWAYS USE THE TOOL FOR ANY DATA QUESTION.
NEVER answer from memory.
NEVER generate SQL as final output.

====================================================
APPROVED TABLE
====================================================

{table_name}

====================================================
SCHEMA
====================================================

{schema_text}

====================================================
COLUMN MAPPING
====================================================

{mapping_text}

====================================================
MATCHED BUSINESS TERMS
====================================================

{matched_section}

====================================================
RESOLVED COLUMNS
====================================================

{resolved_section}

====================================================
FILTERS (PRECOMPUTED - DO NOT MODIFY)
====================================================

{filter_section}

IMPORTANT:
- These filters are already extracted before this step.
- DO NOT re-interpret or re-derive filters from the user query.
- ONLY use them in the SQL tool execution.
IMPORTANT:
Filter values are canonical values.
Use them EXACTLY as supplied.

DO NOT:
- change case
- capitalize
- lowercase
- normalize
- abbreviate
- infer alternatives

Example:
state = 'Tamil Nadu'

must remain

WHERE state = 'Tamil Nadu'

====================================================
RULES (STRICT)
====================================================

1. TOOL IS MANDATORY:
   - If the question requires data from the database,
     you MUST call the SQL tool.
   - You are NOT allowed to answer directly.

2. NO SQL OUTPUT:
   - NEVER output SQL in the final response.
   - SQL is only for internal tool execution.

3. SCHEMA SAFETY:
   - Use ONLY columns present in schema.
   - Never invent table or column names.

4. FILTER USAGE:
   - Always apply all FILTERS in WHERE clause.
   - Combine multiple filters using AND.
   - Do NOT modify filter values or columns.

5. COLUMN USAGE:
   - Use ONLY resolved columns unless explicitly required.
   - Do not add extra columns unless needed for filtering or correctness.

6. QUERY HANDLING:
   - If query is ambiguous, still attempt tool execution.
   - Do NOT ask the user for clarification if filters exist.

7. FINAL ANSWER:
   - Must be derived ONLY from tool output.
   - Do not add assumptions or explanations beyond results.

8. FAILURE HANDLING:
   - If tool execution fails, re-evaluate schema and retry once.



====================================================
OUTPUT STYLE
====================================================

- Return raw tool results only.
- Output valid JSON.
- Do not summarize.
"""    
#     system_prompt = f"""
#             You are an Oracle SQL Agent.

#             You have access to a SQL execution tool.

#             YOU MUST ALWAYS USE THE TOOL FOR ANY DATA QUESTION.
#             NEVER answer from memory.   
#             NEVER output SQL as final answer.

# ====================================================
# APPROVED TABLE
# ====================================================

# {table_name}

# ====================================================
# SCHEMA
# ====================================================

# {schema_text}

# ====================================================
# COLUMN MAPPING
# ====================================================

# {mapping_text}

# ====================================================
# MATCHED BUSINESS TERMS
# ====================================================

# {matched_section}

# ====================================================
# RESOLVED COLUMNS
# ====================================================

# {resolved_section}  

# ====================================================
# FILTERS (IMPORTANT)
# ====================================================

# {filter_section}


# ====================================================
# RULES
# ====================================================

# TOOL USAGE RULE:
# - If the question involves data retrieval, you MUST call the SQL tool.
# - Do NOT respond with SQL text.
# - You are not allowed to answer without tool execution.

# 1. Use ONLY the approved table:
#    {table_name}

# 2. Use ONLY columns present in the schema.

# 3. Never invent:
#    - table names
#    - column names
# 4. If filters are present:
#    - ALWAYS apply them in WHERE clause
#    - combine multiple filters using AND

# 5. Convert business terminology using the
#    provided Column Mapping.

# 6. If a query is required:
#    - Use the SQL execution tool
#    - Do NOT stop at SQL generation

# 7. You MUST use the SQL tool for execution whenever a database query is needed.    

# 7a. Final answer MUST be derived from tool output.

# 8. If the user asks for filtering:
#    - include filters in SQL
#    - execute using tool

# 9. If requested fields cannot be mapped:
#    - ignore them saf

# 10. For data retrieval requests, every resolved column relevant
#     to the user request MUST be included in the SELECT clause.

# 11. Do not omit requested columns if they exist in the schema.

# 12. When the user specifies a value for a mapped column,
#     include it in the WHERE clause.

# 13. If a requested field cannot be mapped,
#     ignore it rather than inventing a column.

# 14. Output must be natural language, not SQL.

# 15. SELECT RULE:
#         - Include all columns required to answer the question
#         - You may include additional columns if required for grouping, filtering, or clarity
#         - Do NOT restrict SELECT strictly to user-mentioned fields

# 16.If a query fails or is ambiguous:
#         - Re-evaluate schema mapping
#         - Adjust SQL internally
#         - Retry tool execution

# 17. Do not add additional columns unless the user asks for all columns.
# """
    
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                """
                    ====================================================
                        USER REQUEST
                    ====================================================

                        {user_query}
                        Execute the request using the available SQL tool.
                        Return the query results.
                    """
            )
        ]
    )