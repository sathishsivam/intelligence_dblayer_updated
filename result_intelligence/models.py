from enum import Enum
from pydantic import BaseModel


class ResultAction(str, Enum):
    TABLE = "table"
    CHART = "chart"
    SUMMARY = "summary"
    DOWNLOAD = "download"
    KPI = "kpi"


class ResultDecision(BaseModel):

    status: str

    action: str | None = None

    recommended: str | None = None

    options: list[str] = []

    reason: str = ""