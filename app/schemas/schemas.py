from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NormalizedAlertInput(BaseModel):
    alert_id: str
    project_id: str | None = None
    source: str = "prometheus_alertmanager"
    source_type: str = "prometheus_alertmanager"
    service_name: str = "unknown-service"
    alert_name: str = "UnknownAlert"
    alert_type: str = "custom"
    severity: str = "warning"
    message: str = "Prometheus alert received"
    description: str | None = None
    environment: str = "production"
    namespace: str | None = None
    cluster: str | None = None
    pod: str | None = None
    deployment: str | None = None
    instance: str | None = None
    job: str | None = None
    status: str = "firing"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    generator_url: str | None = None
    fingerprint: str | None = None
    labels: dict[str, Any] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)
    raw_alert: dict[str, Any] | None = None


class AnalysisAlertsRequest(BaseModel):
    alerts: list[NormalizedAlertInput]


class AnalysisProcessResponse(BaseModel):
    status: str
    processed_count: int
    duplicate_count: int
    incident_count: int
    failed_count: int


class AnalysisResultRead(BaseModel):
    id: int
    incident_id: str | None
    correlation_id: str
    ai_summary: str | None
    root_cause: str | None
    supporting_evidence: list[Any] | None
    confidence_score: float | None
    recommended_fix: dict[str, Any] | None
    raw_ai_response: Any | None
    analysis_status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
