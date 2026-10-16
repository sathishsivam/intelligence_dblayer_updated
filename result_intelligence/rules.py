class ResultRules:

    @staticmethod
    def evaluate(query, df, profile):

        rows = len(df)

        cols = len(df.columns)

        numeric = len(profile["numeric_columns"])

        categorical = len(profile["categorical_columns"])

        datetime = len(profile["datetime_columns"])

        q = query.lower()

        if any(word in q for word in [
            "count",
            "sum",
            "average",
            "avg",
            "group by",
            "trend",
            "monthly",
            "yearly",
            "compare",
            "top",
            "highest"
        ]):
            return {
                "status": "AUTO",
                "action": "chart"
            }

        if numeric >= 1 and categorical >= 1 and cols <= 6:
            return {
                "status": "AUTO",
                "action": "chart"
            }

        if numeric == 0:
            return {
                "status": "HITL",
                "recommended": "table",
                "options": ["table", "summary"]
            }

        return {
            "status": "HITL",
            "recommended": "chart",
            "options": ["chart", "table", "summary"]
        }