from typing import Optional
from pydantic import BaseModel


class AnalysisPlan(BaseModel):

    group_by: Optional[str] = None

    aggregation: Optional[str] = None

    metric: Optional[str] = None

    sort: Optional[str] = "desc"

    limit: Optional[int] = 10

    chart: Optional[str] = "bar"


class AnalysisRequest(BaseModel):

    session_id: str

    analysis_id: str