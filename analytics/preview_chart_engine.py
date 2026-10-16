import plotly.express as px


class PreviewChartEngine:

    def generate(self, df, execution):

        group_by = execution.get("group_by")
        aggregation = execution.get("aggregation")
        metric = execution.get("metric")
        limit = execution.get("limit", 10)
        chart = execution.get("chart", "bar")

        # ----------------------------------
        # Aggregate Data
        # ----------------------------------

        if aggregation == "count":

            result = (
                df.groupby(group_by)
                .size()
                .reset_index(name="count")
            )

            y = "count"

        elif aggregation == "sum":

            result = (
                df.groupby(group_by)[metric]
                .sum()
                .reset_index()
            )

            y = metric

        elif aggregation == "avg":

            result = (
                df.groupby(group_by)[metric]
                .mean()
                .reset_index()
            )

            y = metric

        elif aggregation == "max":

            result = (
                df.groupby(group_by)[metric]
                .max()
                .reset_index()
            )

            y = metric

        elif aggregation == "min":

            result = (
                df.groupby(group_by)[metric]
                .min()
                .reset_index()
            )

            y = metric

        else:

            raise Exception(f"Unsupported aggregation: {aggregation}")

        result = result.sort_values(
            by=y,
            ascending=False
        ).head(limit)

        # ----------------------------------
        # Generate Plotly Chart
        # ----------------------------------

        title = f"{aggregation.title()} of {metric} by {group_by}"

        if chart == "bar":

            fig = px.bar(
                result,
                x=group_by,
                y=y,
                text=y,
                title=title
            )

        elif chart == "pie":

            fig = px.pie(
                result,
                names=group_by,
                values=y,
                title=title
            )

        elif chart == "line":

            fig = px.line(
                result,
                x=group_by,
                y=y,
                markers=True,
                title=title
            )

        elif chart == "scatter":

            fig = px.scatter(
                result,
                x=group_by,
                y=y,
                title=title
            )

        else:

            fig = px.bar(
                result,
                x=group_by,
                y=y,
                title=title
            )

        fig.update_layout(
            template="plotly_white",
            height=450
        )

        return fig.to_json()
