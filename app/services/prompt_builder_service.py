import json
from typing import Any


SYSTEM_PROMPT = (
    "You are OpsGPT, an AI incident analysis assistant for DevOps/SRE teams. "
    "Return valid JSON only."
)

_ALERT_FIELDS = (
    "project_id",
    "alert_id",
    "alert_name",
    "alert_type",
    "severity",
    "service_name",
    "message",
    "description",
    "environment",
    "namespace",
    "cluster",
    "pod",
    "deployment",
    "instance",
    "job",
    "status",
    "starts_at",
    "generator_url",
    "labels",
    "annotations",
)

_OUTPUT_SCHEMA = {
    "incident_summary": "string",
    "root_cause": "string",
    "supporting_evidence": ["string"],
    "confidence_score": 0,
    "recommended_fix": {
        "immediate_actions": ["string"],
        "long_term_actions": ["string"],
        "runbook_suggestions": ["string"],
    },
}


def build_incident_prompts(alerts: list[dict[str, Any]]) -> tuple[str, str]:
    if not alerts:
        raise ValueError("At least one normalized alert is required for AI analysis")

    normalized_alerts = [{field: alert.get(field) for field in _ALERT_FIELDS} for alert in alerts]
    context = {
        "project_id": normalized_alerts[0]["project_id"],
        "primary_alert": normalized_alerts[0],
        "related_alerts": normalized_alerts[1:],
        "required_output_schema": _OUTPUT_SCHEMA,
    }
    user_prompt = (
        "Analyze the normalized Prometheus Alertmanager incident context below. Use only the supplied "
        "evidence and do not invent unsupported root causes. If evidence is weak, lower confidence_score. "
        "Provide immediate and long-term remediation actions and runbook suggestions. Return only one JSON "
        "object matching required_output_schema; do not use markdown.\n\n"
        f"Incident context:\n{json.dumps(context, indent=2, default=str)}"
    )
    return SYSTEM_PROMPT, user_prompt
