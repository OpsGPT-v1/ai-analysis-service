from app.ai_clients.azure_foundry_client import AIProviderConfigError, AzureFoundryClient
from app.ai_clients.base_ai_client import AIClient
from app.core.config import settings


def get_ai_client() -> AIClient:
    provider = settings.ai_provider.strip().lower()
    if provider in {"azure_foundry", "foundry"}:
        return AzureFoundryClient()
    raise AIProviderConfigError(f"Unsupported AI provider: {settings.ai_provider}")
