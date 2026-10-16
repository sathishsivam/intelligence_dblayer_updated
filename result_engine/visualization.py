import json

import plotly.express as px
import plotly.io as pio
from ..serializer import make_json_serializable


class VisualizationEngine:

    def render(self, df, execution):

        chart = execution.get("chart", "bar")
        group_by = execution.get("group_by")
        metric = execution.get("metric")
        aggregation = execution.get("aggregation")

        x = df.columns[0]
        y = df.columns[1]

        title = f"{aggregation.title()} of {metric} by {group_by}"

        if chart == "bar":

            fig = px.bar(
                df,
                x=x,
                y=y,
                text=y,
                title=title
            )

        elif chart == "pie":

            fig = px.pie(
                df,
                names=x,
                values=y,
                title=title
            )

        elif chart == "line":

            fig = px.line(
                df,
                x=x,
                y=y,
                markers=True,
                title=title
            )

        elif chart == "scatter":

            fig = px.scatter(
                df,
                x=x,
                y=y,
                title=title
            )

        else:

            fig = px.bar(
                df,
                x=x,
                y=y,
                title=title
            )

        fig.update_layout(
            template="plotly_white",
            height=550,
            xaxis_title=x,
            yaxis_title=y
        )

        # ---------------------------------------------------
        # Convert Plotly Figure -> JSON-safe Python dict
        # ---------------------------------------------------

        # chart = json.loads(
        #     pio.to_json(fig,pretty=False,engine="json")
        # )
        chart_dict=fig.to_dict()
        # Final safety
        chart_dict = make_json_serializable(chart_dict)

        return chart_dict
