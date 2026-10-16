from .agent import InsightAgent
from .visualization_recommender import VisualizationRecommender


class InsightService:

    def __init__(self):
        self.agent = InsightAgent()
        self.visualizer = VisualizationRecommender()

    def recommend(
        self,
        query,
        sql,
        dataframe,
        profile,
    ):

        insight = self.agent.invoke(
            query=query,
            sql=sql,
            dataframe=dataframe,
            profile=profile,
        )

        print("\n================ AGENT OUTPUT ================")
        print(type(insight))
        print(insight)
        print("=============================================\n")

        recommendation = self.visualizer.recommend(
            dataframe,
            insight,
        )

        print("\n========== VISUALIZER OUTPUT ==========")
        print(type(recommendation))
        print(recommendation)
        print("=======================================\n")

        return recommendation