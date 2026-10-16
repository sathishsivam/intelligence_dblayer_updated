
import re
from difflib import SequenceMatcher
from .scil_value_resolver import resolve_value
# # =====================================================
# # NORMALIZATION
# # =====================================================
# def normalize(text: str):
#     return re.sub(r"\s+", " ", text).strip().lower()


# # =====================================================
# # SCIL VALUE RESOLUTION
# # =====================================================
# def resolve_value(column: str, value: str, enum_index=None):

#     if not value:
#         return value

#     value_norm = value.strip().lower()

#     if not enum_index:
#         return value.strip()

#     mapping = enum_index.get(column)

#     if not mapping:
#         return value.strip()

#     # -------------------------
#     # dict-based SCIL
#     # -------------------------
#     if isinstance(mapping, dict):

#         if value_norm in mapping:
#             return mapping[value_norm]

#         for k, v in mapping.items():
#             if value_norm == k:
#                 return v
#             if value_norm in k:
#                 return v

#     # -------------------------
#     # set/list fallback safety
#     # -------------------------
#     elif isinstance(mapping, (set, list)):

#         for v in mapping:
#             v_str = str(v)
#             if value_norm == v_str.lower():
#                 return v_str
#             if value_norm in v_str.lower():
#                 return v_str

#     return value.strip()


# # def sql_intent_parser(query: str, resolved_columns=None, scil_registry=None):

# #     query = query.lower()
# #     filters = []

# #     if "for" in query or "where" in query:

# #         filter_part = query.split("for")[-1] if "for" in query else query.split("where")[-1]

# #         if " is " in filter_part:

# #             left, right = filter_part.split(" is ", 1)

# #             left = left.strip()
# #             value_text = right.strip().rstrip(".,;:!?")
# #             # detect multiple values
# #             values = re.split(r"\s+(?:and|or|,)\s+", value_text)

# #             values = [v.strip() for v in values if v.strip()]

# #             if resolved_columns:

# #                 for col in resolved_columns:

# #                     if left.replace(" ", "_") in col.lower():

# #                         # 🔥 SCIL FIX HERE
# #                         final_value = resolve_value(col, values, scil_registry)

# #                         filters.append({
# #                             "column": col,
# #                             "operator": "=",
# #                             "value": final_value
# #                         })

# #     return {"filters": filters}

# import re


# def sql_intent_parser(query: str,resolved_columns=None,scil_registry=None):

#     query = query.lower()

#     filters = []

#     if "for" in query or "where" in query:

#         filter_part = (
#             query.split("for", 1)[1]
#             if "for" in query
#             else query.split("where", 1)[1]
#         )

#         if " is " in filter_part:

#             left, right = filter_part.split(" is ", 1)

#             left = left.strip()

#             value_text = right.strip().rstrip(".,;:!?")

#             values = re.split(
#                 r"\s*(?:and|or|,)\s*",
#                 value_text
#             )

#             values = [
#                 v.strip()
#                 for v in values
#                 if v.strip()
#             ]

#             if resolved_columns:

#                 for col in resolved_columns:

#                     if left.replace(" ", "_") in col.lower():

#                         # Resolve every value using SCIL
#                         resolved_values = [

#                             resolve_value(
#                                 col,
#                                 value,
#                                 scil_registry
#                             )

#                             for value in values
#                         ]

#                         # Single value
#                         if len(resolved_values) == 1:

#                             filters.append({

#                                 "column": col,

#                                 "operator": "=",

#                                 "value": resolved_values[0]

#                             })

#                         # Multiple values
#                         else:

#                             filters.append({

#                                 "column": col,

#                                 "operator": "IN",

#                                 "values": resolved_values

#                             })

#     return {
#         "filters": filters
#     }


# =====================================================
# NORMALIZATION
# =====================================================

def normalize(text: str):

    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip().lower()


# =====================================================
# SCIL VALUE RESOLUTION
# =====================================================

def resolve_value(column, value, enum_index=None):

    if value is None:
        return value

    value_norm = str(value).strip().lower()

    if not enum_index:
        return value

    mapping = enum_index.get(column)

    if not mapping:
        return value

    if isinstance(mapping, dict):

        if value_norm in mapping:
            return mapping[value_norm]

        for k, v in mapping.items():

            if value_norm == k.lower():
                return v

            if value_norm in k.lower():
                return v

    elif isinstance(mapping, (set, list)):

        for item in mapping:

            if value_norm == str(item).lower():
                return item

            if value_norm in str(item).lower():
                return item

    return value


# =====================================================
# COLUMN MATCHER
# =====================================================

def find_matching_column(left, resolved_columns):

    left = normalize(left)

    for col in resolved_columns:

        candidate = normalize(col.replace("_", " "))

        if left == candidate:
            return col

    # fuzzy fallback

    best = None
    score = 0

    for col in resolved_columns:

        candidate = normalize(col.replace("_", " "))

        s = SequenceMatcher(None, left, candidate).ratio()

        if s > score:
            score = s
            best = col

    if score >= 0.85:
        return best

    return None


# =====================================================
# FILTER PARSER
# =====================================================

def sql_intent_parser(
        query,
        resolved_columns=None,
        scil_registry=None
):

    query_lower = query.lower()

    filters = []

    if "where" in query_lower:

        filter_text = query_lower.split("where", 1)[1]

    elif "for" in query_lower:

        filter_text = query_lower.split("for", 1)[1]

    else:

        return {
            "filters": [],
            "filter_count": 0,
            "has_multi_value": False
        }

    patterns = [

        ("NOT IN", r"(.+?)\s+not\s+in\s+(.+)"),

        ("IN", r"(.+?)\s+in\s+(.+)"),

        ("BETWEEN", r"(.+?)\s+between\s+(.+?)\s+and\s+(.+)"),

        (">=", r"(.+?)\s*>=\s*(.+)"),

        ("<=", r"(.+?)\s*<=\s*(.+)"),

        (">", r"(.+?)\s*>\s*(.+)"),

        ("<", r"(.+?)\s*<\s*(.+)"),

        ("!=", r"(.+?)\s+(?:is\s+not|!=|not)\s+(.+)"),

        ("LIKE", r"(.+?)\s+contains\s+(.+)"),

        ("=", r"(.+?)\s+(?:is|equals|=)\s+(.+)")

    ]

    for operator, pattern in patterns:

        m = re.match(pattern, filter_text)

        if not m:
            continue

        column_name = m.group(1).strip()

        column = find_matching_column(
            column_name,
            resolved_columns or []
        )

        if not column:
            break

        # --------------------------
        # BETWEEN
        # --------------------------

        if operator == "BETWEEN":

            values = [

                resolve_value(
                    column,
                    m.group(2).strip(),
                    scil_registry
                ),

                resolve_value(
                    column,
                    m.group(3).strip(),
                    scil_registry
                )

            ]

            filters.append({

                "column": column,

                "operator": "BETWEEN",

                "values": values

            })

            break

        # --------------------------
        # IN / NOT IN
        # --------------------------

        if operator in ("IN", "NOT IN"):

            values = re.split(
                r"\s*(?:,|and|or)\s*",
                m.group(2)
            )

            values = [

                resolve_value(
                    column,
                    value.strip(),
                    scil_registry
                )

                for value in values

                if value.strip()
            ]

            values = list(dict.fromkeys(values))

            filters.append({

                "column": column,

                "operator": operator,

                "values": values

            })

            break

        # --------------------------
        # LIKE
        # --------------------------

        if operator == "LIKE":

            value = resolve_value(
                column,
                m.group(2).strip(),
                scil_registry
            )

            filters.append({

                "column": column,

                "operator": "LIKE",

                "value": f"%{value}%"

            })

            break

        # --------------------------
        # Standard operators
        # --------------------------

        # value = resolve_value(
        #     column,
        #     m.group(2).strip(),
        #     scil_registry
        # )

        # filters.append({

        #     "column": column,

        #     "operator": operator,

        #     "value": value

        # })

        # break
        value_text = m.group(2).strip()

        # Split values by AND / OR / comma
        values = re.split(
            r"\s*(?:and|or|,)\s*",
            value_text
        )

        values = [v.strip() for v in values if v.strip()]

        # Resolve SCIL values
        resolved_values = [
            resolve_value(column, v, scil_registry)
            for v in values
        ]

        # If multiple values are supplied with "=" or "is",
        # automatically convert to an IN filter.
        if len(resolved_values) > 1:

            filters.append({

                "column": column,

                "operator": "IN",

                "values": resolved_values

            })

        else:

            filters.append({

                "column": column,

                "operator": operator,

                "value": resolved_values[0]

            })

            break

    return {

        "filters": filters,

        "filter_count": len(filters),

        "has_multi_value": any(

            f["operator"] in ("IN", "NOT IN")

            for f in filters

        )

    }