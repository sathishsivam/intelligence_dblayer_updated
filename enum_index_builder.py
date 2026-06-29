import pandas as pd
from .db import global_db
import pandas as pd
from .db import global_db

def build_enum_index(engine, table_name):

    df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

    enum_index = {}

    for col in df.columns:

        values = df[col].dropna().astype(str).unique().tolist()

        # heuristic: enum-like column
        if 1 < len(values) <= 50:

            # 🔥 convert SET → DICT (SCIL compliant)
            enum_index[col] = {
                v.strip().lower(): v.strip()
                for v in values
            }

    print(type(enum_index.get("state")))

    return enum_index