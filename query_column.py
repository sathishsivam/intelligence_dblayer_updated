import re
# =========================
# Helper: Extract Column Names
# =========================
def extract_columns_from_query(query: str):
    match = re.search(r"SELECT(.*?)FROM", query, re.IGNORECASE | re.DOTALL)

    if not match:
        return None

    cols_part = match.group(1)

    cols = [col.strip() for col in cols_part.split(",")]

    cleaned_cols = []
    for col in cols:
        col = col.replace("`", "")

        if " as " in col.lower():
            col = col.split(" as ")[-1].strip()

        cleaned_cols.append(col)

    return cleaned_cols
