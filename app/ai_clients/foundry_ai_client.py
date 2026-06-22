"""Compatibility imports for the original Foundry client module."""

from app.ai_clients.azure_foundry_client import (
    AIProviderConfigError,
    AIProviderRequestError,
    AIProviderResponseParseError,
    AzureFoundryClient,
    azure_foundry_configured,
)

FoundryAIClient = AzureFoundryClient
AIConfigurationError = AIProviderConfigError
InvalidAIResponseError = AIProviderResponseParseError


def foundry_configured() -> bool:
    return azure_foundry_configured()
