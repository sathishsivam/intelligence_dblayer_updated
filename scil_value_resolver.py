import re
import pandas as pd

# SCIL VALUE REGISTRY

# def build_scil_value_registry(engine, table_name):

#     import pandas as pd

#     df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

#     registry = {}

#     for col in df.columns:

#         values = df[col].dropna().astype(str).unique().tolist()

#         if 1 < len(values) <= 50:

#             # IMPORTANT: convert set → dict (your bug fix)
#             normalized_map = {}

#             for v in values:
#                 key = v.strip().lower()
#                 normalized_map[key] = v   # canonical original value

#             registry[col] = normalized_map

#     return registry


# def resolve_value(column: str, value: str, scil_registry=None):

#     if not value:
#         return value

#     # value_norm = value.strip().lower()
#     value_norm = (
#             str(value)
#             .strip()
#             .rstrip(".,;:!?")
#             .lower()
#     )
#     # Normalize multiple spaces
#     value_norm = re.sub(r"\s+", " ", value_norm)

#     # Remove spaces (Tamil Nadu -> tamilnadu)
#     value_key = value_norm.replace(" ", "")

   

#     if scil_registry and column in scil_registry:

#         mapping = scil_registry[column]

#         # direct match
#         if value_norm in mapping:
#             return mapping[value_norm]
        
#         if value_key in mapping:
#             return mapping[value_key]


#         # fuzzy match
#         for k, v in mapping.items():
#             if value_norm == k:
#                 return v

#             if value_norm in k or k in value_norm:
#                 return v

#     return value

def normalize_key(value: str):

    value = (
        str(value)
        .strip()
        .rstrip(".,;:!?")
        .lower()
    )

    value = re.sub(r"\s+", " ", value)

    return value


def build_scil_value_registry(engine, table_name):

    df = pd.read_sql(
        f"SELECT * FROM {table_name}",
        engine
    )

    registry = {}

    for col in df.columns:

        values = (
            df[col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        if 1 < len(values) <= 50:

            normalized_map = {}

            for value in values:

                canonical = value.strip()

                key = normalize_key(canonical)

                # Primary key
                normalized_map[key] = canonical

                # Without spaces
                normalized_map[key.replace(" ", "")] = canonical

                # Without hyphens
                normalized_map[key.replace("-", " ")] = canonical

                # Without underscores
                normalized_map[key.replace("_", " ")] = canonical

            registry[col] = normalized_map

    return registry



def resolve_value(column: str, value: str, scil_registry=None):

    if not value:
        return value

    value_norm = (
        str(value)
        .strip()
        .rstrip(".,;:!?")
        .lower()
    )

    # Normalize whitespace
    value_norm = re.sub(r"\s+", " ", value_norm)

    # Remove spaces (Tamil Nadu -> tamilnadu)
    value_key = value_norm.replace(" ", "")

    if scil_registry and column in scil_registry:

        mapping = scil_registry[column]
        print("="*120)
        print("COLUMN :", column)
        print("INPUT VALUE :", repr(value))
        print("NORMALIZED :", repr(value_norm))
        print("LOOKUP FOUND :", mapping.get(value_norm))
        print("ALL KEYS CONTAINING 'kar':")

        for k in mapping.keys():
            if "kar" in k:
                print(k)

        print("="*120)

        # -------------------------
        # 1. Direct lookup
        # -------------------------

        if value_norm in mapping:
            return mapping[value_norm]

        if value_key in mapping:
            return mapping[value_key]

        # -------------------------
        # 2. Fuzzy lookup
        # -------------------------

        for k, v in mapping.items():

            key_norm = (
                str(k)
                .strip()
                .rstrip(".,;:!?")
                .lower()
            )

            key_norm = re.sub(r"\s+", " ", key_norm)

            key_key = key_norm.replace(" ", "")

            # Exact
            if value_norm == key_norm:
                return v

            if value_key == key_key:
                return v

            # Partial
            if value_norm in key_norm:
                return v

            if key_norm in value_norm:
                return v

            if value_key in key_key:
                return v

            if key_key in value_key:
                return v
            
    print("=" * 80)
    print("COLUMN:", column)
    print("INPUT :", repr(value))
    print("NORMAL:", repr(value_norm))

    mapping = scil_registry.get(column) or {}

    print("FOUND :", mapping.get(value_norm))
    print("=" * 80)

    return value.strip()
