import asyncio
import logging
from typing import Any

import httpx

from app.ai_clients.base_ai_client import AIClient
from app.core.config import settings
from app.utils.json_parser import JSONExtractionError, extract_json_object

logger = logging.getLogger(__name__)


class AIProviderConfigError(RuntimeError):
    pass


class AIProviderRequestError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AIProviderResponseParseError(RuntimeError):
    def __init__(self, message: str, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response


def azure_foundry_configured() -> bool:
    return all(
        (
            settings.azure_foundry_endpoint,
            settings.azure_foundry_api_key,
            settings.azure_foundry_model,
        )
    )


class AzureFoundryClient(AIClient):
    async def analyze_incident(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self._validate_configuration()
        mode = settings.azure_foundry_api_mode.strip().lower()

        if mode == "responses":
            response = await self._request_responses_api(system_prompt, user_prompt)
            content = self._extract_responses_content(response)
        elif mode == "chat_completions":
            response = await self._request_chat_completions_api(system_prompt, user_prompt)
            content = self._extract_chat_content(response)
        else:
            raise AIProviderConfigError(
                "Azure Foundry API mode must be either responses or chat_completions"
            )

        return self._parse_and_validate(content)

    @staticmethod
    def _base_endpoint() -> str:
        endpoint = settings.azure_foundry_endpoint.rstrip("/")
        suffix = "/openai/v1"
        return endpoint[: -len(suffix)] if endpoint.endswith(suffix) else endpoint

    @staticmethod
    def _validate_configuration() -> None:
        required = {
            "AZURE_FOUNDRY_ENDPOINT": settings.azure_foundry_endpoint,
            "AZURE_FOUNDRY_API_KEY": settings.azure_foundry_api_key,
            "AZURE_FOUNDRY_MODEL": settings.azure_foundry_model,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise AIProviderConfigError(
                f"Azure Foundry configuration is missing: {', '.join(missing)}"
            )

    async def _request_responses_api(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "model": settings.azure_foundry_model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.azure_foundry_temperature,
        }
        return await self._post_json(
            url=f"{self._base_endpoint()}/openai/v1/responses",
            params=None,
            payload=payload,
        )

    async def _request_chat_completions_api(
        self, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        url = (
            f"{self._base_endpoint()}/openai/deployments/"
            f"{settings.azure_foundry_model}/chat/completions"
        )
        params = {"api-version": settings.azure_foundry_api_version}
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.azure_foundry_temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            return await self._post_json(url=url, params=params, payload=payload)
        except AIProviderRequestError as exc:
            if exc.status_code not in {400, 422}:
                raise
            logger.warning("Retrying Azure Foundry chat completion without response_format")
            fallback_payload = dict(payload)
            fallback_payload.pop("response_format")
            return await self._post_json(
                url=url,
                params=params,
                payload=fallback_payload,
                max_retries=0,
            )

    async def _post_json(
        self,
        *,
        url: str,
        params: dict[str, str] | None,
        payload: dict[str, Any],
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "api-key": settings.azure_foundry_api_key}
        retries = settings.azure_foundry_max_retries if max_retries is None else max_retries
        attempts = max(1, retries + 1)
        last_error: Exception | None = None
        last_status_code: int | None = None

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.azure_foundry_timeout_seconds)
        ) as client:
            for attempt in range(1, attempts + 1):
                try:
                    response = await client.post(url, params=params, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("Azure Foundry returned a non-object JSON response")
                    return data
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    last_status_code = exc.response.status_code
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = exc

                logger.warning(
                    "Azure Foundry request attempt %s failed: %s",
                    attempt,
                    last_error.__class__.__name__,
                )
                if attempt < attempts:
                    await asyncio.sleep(min(0.5 * attempt, 2.0))

        raise AIProviderRequestError(
            "Azure Foundry request failed after "
            f"{attempts} attempt(s): {last_error.__class__.__name__ if last_error else 'unknown'}",
            status_code=last_status_code,
        )

    @classmethod
    def _extract_responses_content(cls, response: dict[str, Any]) -> str:
        output_text = response.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        content = cls._find_text(response.get("output"))
        if content:
            return content
        raise AIProviderResponseParseError("Azure Foundry Responses API returned no output text")

    @classmethod
    def _extract_chat_content(cls, response: dict[str, Any]) -> str:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise AIProviderResponseParseError("Azure Foundry chat response did not contain choices")
        message = choices[0].get("message")
        content = cls._find_text(message.get("content") if isinstance(message, dict) else None)
        if content:
            return content
        raise AIProviderResponseParseError("Azure Foundry chat response returned no message content")

    @classmethod
    def _find_text(cls, value: Any) -> str | None:
        if isinstance(value, str):
            return value.strip() or None
        if isinstance(value, list):
            for item in value:
                text = cls._find_text(item)
                if text:
                    return text
        if isinstance(value, dict):
            for key in ("output_text", "text", "content"):
                if key in value:
                    text = cls._find_text(value[key])
                    if text:
                        return text
        return None

    @staticmethod
    def _parse_and_validate(content: str) -> dict[str, Any]:
        try:
            parsed = extract_json_object(content)
        except JSONExtractionError as exc:
            raise AIProviderResponseParseError(str(exc), content) from exc

        try:
            AzureFoundryClient._validate_output(parsed)
        except ValueError as exc:
            raise AIProviderResponseParseError(f"AI response failed validation: {exc}", content) from exc
        return parsed

    @staticmethod
    def _validate_output(parsed: dict[str, Any]) -> None:
        required = {
            "incident_summary",
            "root_cause",
            "supporting_evidence",
            "confidence_score",
            "recommended_fix",
        }
        missing = sorted(required.difference(parsed))
        if missing:
            raise ValueError(f"missing required fields: {', '.join(missing)}")
        if not isinstance(parsed["incident_summary"], str):
            raise ValueError("incident_summary must be a string")
        if not isinstance(parsed["root_cause"], str):
            raise ValueError("root_cause must be a string")
        evidence = parsed["supporting_evidence"]
        if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
            raise ValueError("supporting_evidence must be a list of strings")
        confidence = parsed["confidence_score"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence_score must be a number between 0 and 100")
        if not 0 <= confidence <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        recommended_fix = parsed["recommended_fix"]
        if not isinstance(recommended_fix, dict):
            raise ValueError("recommended_fix must be an object")
        for field in ("immediate_actions", "long_term_actions", "runbook_suggestions"):
            value = recommended_fix.get(field)
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"recommended_fix.{field} must be a list of strings")
