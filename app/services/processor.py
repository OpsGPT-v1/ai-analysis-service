import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AnalysisAlert, AnalysisLog, AnalysisResult, CorrelationGroup
from app.schemas.schemas import NormalizedAlertInput
from app.services.ai_analysis_service import AIAnalysisService
from app.services.core_client import create_core_incident, update_core_incident_analysis


SEVERITY_RANK = {"informational": 1, "warning": 2, "critical": 3}


def highest_severity(current: str, incoming: str) -> str:
    return incoming if SEVERITY_RANK.get(incoming, 0) > SEVERITY_RANK.get(current, 0) else current


def correlation_id() -> str:
    return f"COR-{uuid.uuid4().hex[:12].upper()}"


def incident_id() -> str:
    return f"INC-{uuid.uuid4().hex[:12].upper()}"


def window_start() -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=settings.correlation_window_minutes)


def find_duplicate(db: Session, payload: NormalizedAlertInput) -> AnalysisAlert | None:
    query = db.query(AnalysisAlert).filter(AnalysisAlert.received_at >= window_start())
    if payload.fingerprint:
        fingerprint_match = query.filter(AnalysisAlert.fingerprint == payload.fingerprint).first()
        if fingerprint_match:
            return fingerprint_match

    alert_id_match = query.filter(AnalysisAlert.alert_id == payload.alert_id).first()
    if alert_id_match:
        return alert_id_match

    same_target = query.filter(
        AnalysisAlert.project_id == payload.project_id,
        AnalysisAlert.alert_name == payload.alert_name,
        AnalysisAlert.service_name == payload.service_name,
        or_(AnalysisAlert.pod == payload.pod, AnalysisAlert.instance == payload.instance),
    ).first()
    return same_target


def get_or_create_group(db: Session, alert: AnalysisAlert) -> CorrelationGroup:
    group = (
        db.query(CorrelationGroup)
        .filter(
            CorrelationGroup.updated_at >= window_start(),
            CorrelationGroup.status == "open",
            CorrelationGroup.project_id == alert.project_id,
            CorrelationGroup.service_name == alert.service_name,
            CorrelationGroup.namespace == alert.namespace,
            CorrelationGroup.cluster == alert.cluster,
            CorrelationGroup.environment == alert.environment,
        )
        .order_by(CorrelationGroup.updated_at.desc())
        .first()
    )
    if not group:
        group = CorrelationGroup(
            correlation_id=correlation_id(),
            project_id=alert.project_id,
            service_name=alert.service_name,
            namespace=alert.namespace,
            cluster=alert.cluster,
            environment=alert.environment,
            severity=alert.severity,
            status="open",
            related_alert_ids=[alert.alert_id],
        )
        db.add(group)
        db.flush()
        return group

    related = list(group.related_alert_ids or [])
    if alert.alert_id not in related:
        related.append(alert.alert_id)
    group.related_alert_ids = related
    group.severity = highest_severity(group.severity, alert.severity)
    return group


def should_create_incident(group: CorrelationGroup, alert: AnalysisAlert) -> bool:
    if group.incident_id:
        return False
    if alert.severity == "critical":
        return True
    return len(group.related_alert_ids or []) >= 2


def to_analysis_alert(payload: NormalizedAlertInput, is_duplicate: bool) -> AnalysisAlert:
    return AnalysisAlert(
        alert_id=payload.alert_id,
        project_id=payload.project_id,
        source_type=payload.source_type,
        service_name=payload.service_name,
        alert_name=payload.alert_name,
        alert_type=payload.alert_type,
        severity=payload.severity,
        message=payload.message,
        description=payload.description,
        environment=payload.environment,
        namespace=payload.namespace,
        cluster=payload.cluster,
        pod=payload.pod,
        deployment=payload.deployment,
        instance=payload.instance,
        job=payload.job,
        status=payload.status,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        generator_url=payload.generator_url,
        fingerprint=payload.fingerprint,
        labels=payload.labels,
        annotations=payload.annotations,
        is_duplicate=is_duplicate,
    )


def alert_context(alerts: list[AnalysisAlert]) -> list[dict[str, Any]]:
    return [
        {
            "alert_id": alert.alert_id,
            "project_id": alert.project_id,
            "alert_type": alert.alert_type,
            "source_type": alert.source_type,
            "alert_name": alert.alert_name,
            "severity": alert.severity,
            "service_name": alert.service_name,
            "environment": alert.environment,
            "namespace": alert.namespace,
            "cluster": alert.cluster,
            "pod": alert.pod,
            "deployment": alert.deployment,
            "instance": alert.instance,
            "job": alert.job,
            "message": alert.message,
            "description": alert.description,
            "status": alert.status,
            "starts_at": alert.starts_at,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "generator_url": alert.generator_url,
        }
        for alert in alerts
    ]


async def create_incident_and_run_analysis(db: Session, group: CorrelationGroup, trigger_alert: AnalysisAlert) -> bool:
    new_incident_id = incident_id()
    core_payload = {
        "incident_id": new_incident_id,
        "project_id": group.project_id,
        "title": f"{trigger_alert.alert_name} on {trigger_alert.service_name}",
        "service_name": trigger_alert.service_name,
        "severity": group.severity,
        "status": "open",
        "related_alert_ids": group.related_alert_ids,
        "source_type": "prometheus_alertmanager",
        "namespace": trigger_alert.namespace,
        "cluster": trigger_alert.cluster,
    }
    created = await create_core_incident(core_payload)
    if not created:
        db.add(
            AnalysisResult(
                incident_id=None,
                correlation_id=group.correlation_id,
                analysis_status="failed",
                error_message="Core API unavailable; incident could not be created",
            )
        )
        return False

    group.incident_id = created.get("incident_id", new_incident_id)
    db.flush()

    related_alerts = db.query(AnalysisAlert).filter(AnalysisAlert.alert_id.in_(group.related_alert_ids)).all()
    ai_analysis_service = AIAnalysisService()
    try:
        ai_output = await ai_analysis_service.analyze_alerts(
            alert_context(related_alerts or [trigger_alert])
        )
    except Exception as exc:
        db.add(
            AnalysisResult(
                incident_id=group.incident_id,
                correlation_id=group.correlation_id,
                raw_ai_response=getattr(exc, "raw_response", None),
                analysis_status="failed",
                error_message=str(exc),
            )
        )
        db.add(
            AnalysisLog(
                correlation_id=group.correlation_id,
                alert_id=trigger_alert.alert_id,
                event_type="ai_analysis_failed",
                message=str(exc),
            )
        )
        return True

    update_payload = {
        "ai_summary": ai_output.get("incident_summary"),
        "root_cause": ai_output.get("root_cause"),
        "supporting_evidence": ai_output.get("supporting_evidence"),
        "confidence_score": ai_output.get("confidence_score"),
        "recommended_fix": ai_output.get("recommended_fix"),
    }
    updated = await update_core_incident_analysis(group.incident_id, update_payload)
    status = "completed" if updated else "failed"
    error_message = None if updated else "Core API analysis update failed"
    db.add(
        AnalysisResult(
            incident_id=group.incident_id,
            correlation_id=group.correlation_id,
            ai_summary=update_payload["ai_summary"],
            root_cause=update_payload["root_cause"],
            supporting_evidence=update_payload["supporting_evidence"],
            confidence_score=update_payload["confidence_score"],
            recommended_fix=update_payload["recommended_fix"],
            raw_ai_response=ai_output,
            analysis_status=status,
            error_message=error_message,
        )
    )
    db.add(
        AnalysisLog(
            correlation_id=group.correlation_id,
            alert_id=trigger_alert.alert_id,
            event_type="ai_analysis_completed" if updated else "ai_analysis_update_failed",
            message="Foundry analysis processed",
        )
    )
    return True


async def process_alerts(db: Session, alerts: list[NormalizedAlertInput]) -> dict[str, int]:
    processed = 0
    duplicates = 0
    incidents = 0
    failed = 0

    for payload in alerts:
        duplicate = find_duplicate(db, payload)
        alert = to_analysis_alert(payload, is_duplicate=duplicate is not None)
        db.add(alert)
        db.flush()

        if duplicate:
            duplicates += 1
            db.add(
                AnalysisLog(
                    alert_id=alert.alert_id,
                    event_type="duplicate_alert_detected",
                    message="Duplicate alert stored but not correlated into a new incident",
                )
            )
            processed += 1
            continue

        group = get_or_create_group(db, alert)
        db.add(
            AnalysisLog(
                correlation_id=group.correlation_id,
                alert_id=alert.alert_id,
                event_type="alert_correlated",
                message=f"Alert correlated into {group.correlation_id}",
            )
        )
        if should_create_incident(group, alert):
            created = await create_incident_and_run_analysis(db, group, alert)
            if created:
                incidents += 1
            else:
                failed += 1
        processed += 1

    db.commit()
    return {"processed": processed, "duplicates": duplicates, "incidents": incidents, "failed": failed}
