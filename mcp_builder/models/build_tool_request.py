from pydantic import BaseModel


class BuildToolRequest(BaseModel):
    base_url: str
    path: str
    method: str
