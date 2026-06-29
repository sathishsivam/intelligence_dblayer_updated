
import re
from difflib import SequenceMatcher
from .scil_value_resolver import resolve_value
# =====================================================
# NORMALIZATION
# =====================================================
def normalize(text: str):
    return re.sub(r"\s+", " ", text).strip().lower()


# =====================================================
# SCIL VALUE RESOLUTION
# =====================================================
def resolve_value(column: str, value: str, enum_index=None):

    if not value:
        return value

    value_norm = value.strip().lower()

    if not enum_index:
        return value.strip()

    mapping = enum_index.get(column)

    if not mapping:
        return value.strip()

    # -------------------------
    # dict-based SCIL
    # -------------------------
    if isinstance(mapping, dict):

        if value_norm in mapping:
            return mapping[value_norm]

        for k, v in mapping.items():
            if value_norm == k:
                return v
            if value_norm in k:
                return v

    # -------------------------
    # set/list fallback safety
    # -------------------------
    elif isinstance(mapping, (set, list)):

        for v in mapping:
            v_str = str(v)
            if value_norm == v_str.lower():
                return v_str
            if value_norm in v_str.lower():
                return v_str

    return value.strip()


def sql_intent_parser(query: str, resolved_columns=None, scil_registry=None):

    query = query.lower()
    filters = []

    if "for" in query or "where" in query:

        filter_part = query.split("for")[-1] if "for" in query else query.split("where")[-1]

        if " is " in filter_part:

            left, right = filter_part.split(" is ", 1)

            left = left.strip()
            value = right.strip().rstrip(".,;:!?")

            if resolved_columns:

                for col in resolved_columns:

                    if left.replace(" ", "_") in col.lower():

                        # 🔥 SCIL FIX HERE
                        final_value = resolve_value(col, value, scil_registry)

                        filters.append({
                            "column": col,
                            "operator": "=",
                            "value": final_value
                        })

    return {"filters": filters}

