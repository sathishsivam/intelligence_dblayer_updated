from .columnprofiler import detect_type

def build_scil(table_name, df):

    scil = {}

    for column in df.columns:

        values = df[column].dropna().astype(str).tolist()[:500]

        col_type = detect_type(values)

        scil[column] = {
            "semantic_type": col_type,
            "sample_values": list(set(values[:10])),
        }

    return {
        "table": table_name,
        "columns": scil
    }

