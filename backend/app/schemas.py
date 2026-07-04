from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Stage(BaseModel):
    duration: str = Field(..., examples=["30s", "1m"])
    target: int = Field(..., ge=0)


class Threshold(BaseModel):
    metric: str = Field(..., examples=["http_req_duration", "http_req_failed"])
    expression: str = Field(..., examples=["p(95)<500", "rate<0.01"])


class TestCreate(BaseModel):
    name: str
    target_url: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    vus: int = Field(10, ge=1, le=2000)
    stages: list[Stage] = Field(default_factory=list)
    thresholds: list[Threshold] = Field(default_factory=list)


class TestOut(BaseModel):
    id: str
    name: str
    target_url: str
    method: str
    headers: dict[str, Any]
    body: Optional[str]
    vus: int
    stages: list[dict]
    thresholds: list[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class RunOut(BaseModel):
    id: str
    test_id: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    summary: Optional[dict]
    timeline: list[dict]
    error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class RunTrigger(BaseModel):
    pass
