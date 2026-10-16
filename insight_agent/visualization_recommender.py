import pandas as pd


class VisualizationRecommender:

    def recommend(self, dataframe, insight):

        if not insight:
            return insight

        if "options" not in insight:
            return insight

        for option in insight["options"]:

            if option.get("type") != "aggregation":
                continue

            execution = option.get("execution", {})

            group_by = execution.get("group_by")

            aggregation = execution.get("aggregation", "count")

            rule_based = self._recommend(
                 dataframe,
                 group_by,
                 aggregation
                )

            if "visualization" not in option:
                option["visualization"] = rule_based
            else:
                option["visualization"] = self._merge(
                    option["visualization"],
                    rule_based
                )

        return insight

    # ---------------------------------------------------

    def _recommend(self, df, group_by, aggregation):

        default = "bar"

        supported = ["bar"]

        if group_by in df.columns:

            dtype = df[group_by].dtype

            # ------------------------------------
            # Date / Time
            # ------------------------------------

            if pd.api.types.is_datetime64_any_dtype(dtype):

                default = "line"

                supported = [
                    "line",
                    "bar",
                    "area"
                ]

            # ------------------------------------
            # Numeric
            # ------------------------------------

            elif pd.api.types.is_numeric_dtype(dtype):

                default = "scatter"

                supported = [
                    "scatter",
                    "line",
                    "bar"
                ]

            # ------------------------------------
            # Category
            # ------------------------------------

            else:

                if aggregation == "count":

                    default = "bar"

                    supported = [
                        "bar",
                        "pie",
                        "line"
                    ]

                elif aggregation in ("sum", "avg"):

                    default = "bar"

                    supported = [
                        "bar",
                        "line",
                        "area"
                    ]

                else:

                    default = "bar"

                    supported = [
                        "bar"
                    ]

        return {

            "enabled": True,

            "default": default,

            "supported": [

                {
                    "id": c,
                    "label": c.title() + " Chart"
                }

                for c in supported

            ]
        }
    
    # ---------------------------------------------------
    # Merge LLM visualization with rule-based recommendation
    # ---------------------------------------------------

    def _merge(self, llm_vis, rule_vis):

        supported = {}

        # Keep LLM recommendations first
        for chart in llm_vis.get("supported", []):
            supported[chart["id"]] = chart

        # Add missing charts from rule engine
        for chart in rule_vis.get("supported", []):
            supported.setdefault(chart["id"], chart)

        return {

            "enabled": True,

            "default": llm_vis.get(
                "default",
                rule_vis["default"]
            ),

            "supported": list(supported.values())

        }