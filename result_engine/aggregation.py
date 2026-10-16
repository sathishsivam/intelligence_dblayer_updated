import pandas as pd


class AggregationEngine:

    def execute(self, df: pd.DataFrame, execution: dict):

        if execution is None:
            return df

        group_by = execution.get("group_by")
        aggregation = execution.get("aggregation")
        metric = execution.get("metric")
        sort = execution.get("sort", "desc")
        limit = execution.get("limit")

        # -------------------------------------
        # COUNT
        # -------------------------------------
        if aggregation == "count":

            if metric == "*" or metric is None:

                result = (
                    df.groupby(group_by)
                    .size()
                    .reset_index(name="count")
                )

            else:

                result = (
                    df.groupby(group_by)[metric]
                    .count()
                    .reset_index(name="count")
                )

        # -------------------------------------
        # SUM
        # -------------------------------------
        elif aggregation == "sum":

            result = (
                df.groupby(group_by)[metric]
                .sum()
                .reset_index()
            )

        # -------------------------------------
        # AVG
        # -------------------------------------
        elif aggregation in ["avg", "mean"]:

            result = (
                df.groupby(group_by)[metric]
                .mean()
                .reset_index()
            )

        # -------------------------------------
        # MAX
        # -------------------------------------
        elif aggregation == "max":

            if group_by:

                result = (
                    df.groupby(group_by)[metric]
                    .max()
                    .reset_index()
                )

            else:

                result = pd.DataFrame({
                    metric: [df[metric].max()]
                })

        # -------------------------------------
        # MIN
        # -------------------------------------
        elif aggregation == "min":

            if group_by:

                result = (
                    df.groupby(group_by)[metric]
                    .min()
                    .reset_index()
                )

            else:

                result = pd.DataFrame({
                    metric: [df[metric].min()]
                })

        # -------------------------------------
        # DISTINCT
        # -------------------------------------
        elif aggregation == "unique":

            result = (
                df.groupby(group_by)[metric]
                .nunique()
                .reset_index()
            )

        else:

            result = df.copy()

        # -------------------------------------
        # SORT
        # -------------------------------------

        if len(result.columns) > 1:

            value_col = result.columns[-1]

            result = result.sort_values(
                value_col,
                ascending=(sort == "asc")
            )

        # -------------------------------------
        # LIMIT
        # -------------------------------------

        if limit:

            result = result.head(limit)

        return result.reset_index(drop=True)
    