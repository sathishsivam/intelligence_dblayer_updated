from pydantic import BaseModel, ConfigDict
from typing import Optional


class ExecutionPlan(BaseModel):

    group_by: Optional[str] = None
    aggregation: Optional[str] = None
    metric: Optional[str] = None
    sort: Optional[str] = "desc"
    limit: Optional[int] = 10

# Visualization Models
# ----------------------------------------

class VisualizationOption(BaseModel):

    id: str
    label: str


class Visualization(BaseModel):

    enabled: bool = True
    default: str
    supported: list[VisualizationOption]


class InsightOption(BaseModel):

    id: str
    title: str
    description: str
    type: str

    execution: Optional[ExecutionPlan] = None
    visualization: Optional[Visualization] = None
    
    model_config = ConfigDict(
        extra="ignore"
    )