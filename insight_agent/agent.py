from langchain_ollama import ChatOllama

from .prompt import SYSTEM_PROMPT

from .parser import parse_response
from ..serializer import make_json_serializable
import json


class InsightAgent:

    def __init__(self):

        self.llm = ChatOllama(

            model="qwen3:4b",

            temperature=0,

            num_ctx=8192
        )

    def invoke(self,query,sql,profile,dataframe):
        columns = list(dataframe.columns)
        profile_json = json.dumps(profile, indent=2)
        sample_json = json.dumps(
                         dataframe.head(20).to_dict("records"),
                         indent=2,
                         default=str
                        )
        # sample_rows = make_json_serializable(dataframe.head(20).to_dict("records"))

        prompt = f"""
                        {SYSTEM_PROMPT}

                        Original Query:
                        {query}

                        Executed SQL:
                        {sql}
                        Available Columns:
                        {columns}

                        Dataset Profile:
                        {profile_json}

                        Sample Rows:
                        {sample_json}
                        
                    """
        print("=" * 80)
        print("Prompt from Insight_agent agent file")
        print(prompt)
        print("=" * 80)

        response = self.llm.invoke(prompt)
        print("+" * 80)
        print("LLM Resp from Insight Agent",response.content)
        print("+" * 80)
        return parse_response(response)