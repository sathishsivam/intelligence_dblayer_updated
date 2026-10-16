from .aggregation import AggregationEngine
from .visualization import VisualizationEngine
from .summary import SummaryEngine


class ResultService:

    def __init__(self):

        self.aggregation = AggregationEngine()
        self.visualization = VisualizationEngine()
        self.summary = SummaryEngine()

    def execute(self, dataframe, execution):

        aggregated = self.aggregation.execute(
            dataframe,
            execution
        )

        chart = self.visualization.render(
            aggregated,
            execution
        )

        summary = self.summary.generate(
            aggregated,
            execution
        )

        return {

            "table": aggregated.to_dict("records"),

            "chart": chart,

            "summary": summary
        }