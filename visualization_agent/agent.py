from langchain_ollama import ChatOllama
import json


class VisualizationAgent:

    def __init__(self):

        self.llm = ChatOllama(
            model="qwen3:4b",
            temperature=0,
            num_ctx=8192
        )

    def invoke(self, query, sql, dataframe, profile):

        sample_rows = dataframe.head(20).to_dict("records")
        columns = dataframe.columns.tolist()

        prompt = f"""
                        You are an Enterprise BI Visualization Agent.

                        Analyze the following information and recommend the most appropriate visualization.

                        User Query:
                        {query}

                        SQL Query:
                        {sql}

                        Data Profile:
                        {json.dumps(profile, indent=2)}

                        Sample Rows:
                        {json.dumps(sample_rows, indent=2)}

                        Instructions:
                        Choose:
                            - Bar → categorical + numeric
                            - Line → date + numeric
                            - Pie → category proportions
                            - Scatter → two numeric columns
                            - Histogram → single numeric column
                            - Table → no suitable chart
                        
                        Available Columns:
                                {json.dumps(columns, indent=2)}
                            Use only existing columns.

                        1. Recommend the best chart.
                        2. Never invent column names.
                        3. Use only columns that exist.
                        4. Return ONLY valid JSON.

                        Required JSON format:

                        {{
                        "chart_type": "",
                        "title": "",
                        "x_axis": "",
                        "y_axis": "",
                        "aggregation": "",
                        "sort": "",
                        "legend": "",
                        "reason": ""
                        }}
        """

        response = self.llm.invoke(prompt)
        viz = json.loads(response.content)
        return viz