import pandas as pd


class DataProfiler:

    def profile(self, df: pd.DataFrame):

        profile = {

            "rows": len(df),

            "columns": list(df.columns),

            "column_types": {
                col: str(dtype)
                for col, dtype in df.dtypes.items()
            },

            "numeric_columns": df.select_dtypes(
                include=["number"]
            ).columns.tolist(),

            "categorical_columns": df.select_dtypes(
                include=["object", "category"]
            ).columns.tolist(),

            "datetime_columns": df.select_dtypes(
                include=["datetime64"]
            ).columns.tolist(),

            "unique_counts": {
                col: int(df[col].nunique())
                for col in df.columns
            },
            "null_counts": {
                col: int(df[col].isna().sum())
                for col in df.columns
             },

            "sample_values": {
                col: df[col].dropna().unique()[:5].tolist()
                for col in df.columns
            }
        }

        return profile