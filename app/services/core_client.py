import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def headers() -> dict[str, str]:
    return {"X-Internal-API-Key": settings.internal_api_key}


async def create_core_incident(payload: dict[str, Any]) -> dict[str, Any] | None:
    url = f"{settings.core_api_url.rstrip('/')}/internal/incidents"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers(), json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.warning("Core incident creation failed: %s", exc.__class__.__name__)
        return None


async def update_core_incident_analysis(incident_id: str, payload: dict[str, Any]) -> bool:
    url = f"{settings.core_api_url.rstrip('/')}/internal/incidents/{incident_id}/analysis"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.patch(url, headers=headers(), json=payload)
            response.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("Core incident analysis update failed: %s", exc.__class__.__name__)
        return False
