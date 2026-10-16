from .rules import ResultRules


class ResultIntelligenceEngine:

    def analyze(self, query, dataframe, profile):

        decision = ResultRules.evaluate(

            dataframe,

            profile

        )

        decision["query"] = query

        decision["rows"] = len(dataframe)

        decision["columns"] = len(dataframe.columns)

        return decision