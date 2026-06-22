from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisAlert(Base):
    __tablename__ = "analysis_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    source_type: Mapped[str] = mapped_column(String(80), default="prometheus_alertmanager", nullable=False)
    service_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    alert_name: Mapped[str] = mapped_column(String(200), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str] = mapped_column(String(80), nullable=False)
    namespace: Mapped[str | None] = mapped_column(String(160), nullable=True)
    cluster: Mapped[str | None] = mapped_column(String(160), nullable=True)
    pod: Mapped[str | None] = mapped_column(String(200), nullable=True)
    deployment: Mapped[str | None] = mapped_column(String(200), nullable=True)
    instance: Mapped[str | None] = mapped_column(String(200), nullable=True)
    job: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generator_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    labels: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    annotations: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CorrelationGroup(Base):
    __tablename__ = "analysis_correlation_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    service_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    namespace: Mapped[str | None] = mapped_column(String(160), nullable=True)
    cluster: Mapped[str | None] = mapped_column(String(160), nullable=True)
    environment: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="open", nullable=False)
    related_alert_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    incident_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    supporting_evidence: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_fix: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_ai_response: Mapped[dict | list | str | None] = mapped_column(JSONB, nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AnalysisLog(Base):
    __tablename__ = "analysis_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alert_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
