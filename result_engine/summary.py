class SummaryEngine:

    def generate(self, df, execution):

        if df.empty:
            return {
                "headline": "No Data",
                "description": "No records found."
            }

        first = df.iloc[0]

        return {
            "headline": "Analysis Summary",
            "description": (
                f"{first.iloc[0]} has the highest "
                f"{first.iloc[1]} records."
            )
        }