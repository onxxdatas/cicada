import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Test(Base):
    __tablename__ = "tests"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    target_url = Column(String, nullable=False)
    method = Column(String, nullable=False, default="GET")
    headers = Column(JSONB, nullable=False, default=dict)
    body = Column(Text, nullable=True)
    vus = Column(Integer, nullable=False, default=10)
    # stages: list of {"duration": "30s", "target": 20}
    stages = Column(JSONB, nullable=False, default=list)
    # thresholds: list of {"metric": "http_req_duration", "expression": "p(95)<500"}
    thresholds = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=_now)

    runs = relationship("Run", back_populates="test", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    test_id = Column(UUID(as_uuid=False), ForeignKey("tests.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending|running|passed|failed|error
    container_id = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    summary = Column(JSONB, nullable=True)  # final k6 summary metrics
    timeline = Column(JSONB, nullable=False, default=list)  # per-second aggregated points
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    test = relationship("Test", back_populates="runs")
