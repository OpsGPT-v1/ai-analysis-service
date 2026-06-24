# OpsGPT AI Analysis Service

The **AI Analysis Service** is the intelligence correlation engine of the platform. It clusters incoming normalized alerts into correlation groups, decides when to trigger formal incident tickets in the system of record, pulls context for AI processing, calls Azure AI Foundry endpoints to determine incident root cause, and generates structured remediation recommendations.

---

## Correlation Engine & Incident Creation Logic

The correlation engine processes alerts sequentially and aggregates them into groups to prevent "alert fatigue" and help responders view related events collectively:

### 1. Sliding Window & Grouping Keys
*   **Temporal Window**: Alerts are grouped if they occur within a sliding time window (default: `10 minutes`) defined by `correlation_window_minutes`.
*   **Correlation Keys**: Alerts must share identical values across the following fields to join an active open `CorrelationGroup`:
    - `project_id`
    - `service_name`
    - `namespace`
    - `cluster`
    - `environment`
*   **Duplicate Elimination**: If an incoming alert matches an existing alert's `fingerprint`, `alert_id`, or target properties (project, name, service, and pod/instance) within the active window, it is flagged as `is_duplicate` and logged without triggering new analysis cascades.

### 2. Incident Trigger Criteria
An incident is formally generated in the `core-api-service` database when an active group satisfies either condition:
1.  **Critical Threshold**: A new alert with `severity: critical` enters the correlation group.
2.  **Volume Threshold**: The group accumulates **two or more** distinct normalized alerts (of any severity).

---

## Azure AI Foundry Integration

Once an incident is triggered, the service runs an automated diagnostic check via **Azure OpenAI** on the Azure AI Foundry platform.

```mermaid
graph TD
    Trigger[Incident Triggered] -->|1. Build Context JSON| Prompter[Prompt Builder]
    Prompter -->|2. Generate Prompt System/User| Factory[AI Client Factory]
    Factory -->|3. Call Foundry Endpoint| Client[Azure Foundry AI Client]
    Client -->|4. Request Analysis| Azure[Azure OpenAI Instance / gpt-4o-mini]
    Azure -->|5. Return valid JSON| Client
    Client -->|6. Write Back| CoreAPI[Core API Service]
```

### 1. Prompt Construction
The `prompt_builder_service` extracts relevant fields from the primary and secondary alerts in the group, and nests them alongside a strict output schema.
*   **Instruction Constraints**: The model is instructed to prevent hallucination, use only provided evidence, and lower the `confidence_score` dynamically if the evidence is weak.

### 2. Analysis Output Schema
The LLM response is parsed into the following structured schema:
```json
{
  "incident_summary": "Slightly verbose overview of the service degradation",
  "root_cause": "The identified underlying issue",
  "supporting_evidence": ["Evidence point 1", "Evidence point 2"],
  "confidence_score": 0.85,
  "recommended_fix": {
    "immediate_actions": ["Mitigation action 1"],
    "long_term_actions": ["Resolution action 1"],
    "runbook_suggestions": ["Runbook links/titles"]
  }
}
```

---

## API Endpoints Reference

### 1. Analysis Operations (`/api/analysis`)

| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/analysis/alerts` | None | Receives normalized alert lists. Evaluates duplicates, joins groups, triggers AI diagnostics, and writes incident updates. |
| `POST` | `/analysis/correlate`| None | Alias for `/analysis/alerts`. |
| `GET` | `/analysis/incidents/{incident_id}` | None | Retrieves historical AI correlation analysis logs for a target incident. |

---

## Key Configurations & Environment Variables

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://opsgpt_user:opsgpt_password@opsgpt-db:5432/opsgpt_db` | Connection string to PostgreSQL database. |
| `CORE_API_URL` | `http://core-api-service:8001` | Connection endpoint for Core API writes. |
| `INTERNAL_API_KEY` | `change-me-internal-key` | Secret key used to authorize internal requests to Core API. |
| `CORRELATION_WINDOW_MINUTES`| `10` | The sliding window size in minutes. |
| `AI_PROVIDER` | `azure_foundry` | Selected AI driver name. |
| `AZURE_FOUNDRY_ENDPOINT` | `""` | The URL of your Azure AI Foundry OpenAI resource. |
| `AZURE_FOUNDRY_API_KEY` | `""` | API authentication credential for Azure. |
| `AZURE_FOUNDRY_MODEL` | `""` | The deployment name of the OpenAI model (e.g. `gpt-4o-mini`). |
| `AZURE_FOUNDRY_API_VERSION`| `2025-04-01-preview` | API preview version constraint. |
| `AZURE_FOUNDRY_TEMPERATURE`| `0.2` | Creativity level (lowered to enforce precision). |
| `CORS_ORIGINS` | `*` | Allowed CORS origins list. |
