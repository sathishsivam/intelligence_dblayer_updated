# SCIL VALUE REGISTRY

def build_scil_value_registry(engine, table_name):

    import pandas as pd

    df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

    registry = {}

    for col in df.columns:

        values = df[col].dropna().astype(str).unique().tolist()

        if 1 < len(values) <= 50:

            # IMPORTANT: convert set → dict (your bug fix)
            normalized_map = {}

            for v in values:
                key = v.strip().lower()
                normalized_map[key] = v   # canonical original value

            registry[col] = normalized_map

    return registry


def resolve_value(column: str, value: str, scil_registry=None):

    if not value:
        return value

    value_norm = value.strip().lower()

    if scil_registry and column in scil_registry:

        mapping = scil_registry[column]

        # direct match
        if value_norm in mapping:
            return mapping[value_norm]

        # fuzzy match
        for k, v in mapping.items():
            if value_norm == k:
                return v

            if value_norm in k or k in value_norm:
                return v

    return value

