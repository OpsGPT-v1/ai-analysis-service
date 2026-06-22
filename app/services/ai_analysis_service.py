from typing import Any

from app.ai_clients.ai_client_factory import get_ai_client
from app.services.prompt_builder_service import build_incident_prompts


class AIAnalysisService:
    async def analyze_alerts(self, alerts: list[dict[str, Any]]) -> dict[str, Any]:
        system_prompt, user_prompt = build_incident_prompts(alerts)
        return await get_ai_client().analyze_incident(system_prompt, user_prompt)
