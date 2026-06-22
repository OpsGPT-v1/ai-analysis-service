from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://opsgpt_user:opsgpt_password@opsgpt-db:5432/opsgpt_db"
    core_api_url: str = "http://core-api-service:8001"
    internal_api_key: str = "change-me-internal-key"
    correlation_window_minutes: int = 10
    ai_provider: str = "azure_foundry"
    azure_foundry_api_mode: str = "responses"
    azure_foundry_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices("AZURE_FOUNDRY_ENDPOINT", "FOUNDRY_ENDPOINT"),
    )
    azure_foundry_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("AZURE_FOUNDRY_API_KEY", "FOUNDRY_API_KEY"),
    )
    azure_foundry_model: str = Field(
        default="",
        validation_alias=AliasChoices("AZURE_FOUNDRY_MODEL", "FOUNDRY_MODEL_DEPLOYMENT"),
    )
    azure_foundry_api_version: str = Field(
        default="2025-04-01-preview",
        validation_alias=AliasChoices("AZURE_FOUNDRY_API_VERSION", "FOUNDRY_API_VERSION"),
    )
    azure_foundry_timeout_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices("AZURE_FOUNDRY_TIMEOUT_SECONDS", "FOUNDRY_TIMEOUT_SECONDS"),
    )
    azure_foundry_max_retries: int = Field(
        default=2,
        validation_alias=AliasChoices("AZURE_FOUNDRY_MAX_RETRIES", "FOUNDRY_MAX_RETRIES"),
    )
    azure_foundry_temperature: float = 0.2
    app_env: str = "development"
    cors_origins: str = "*"
    db_init_max_attempts: int = 30
    db_init_delay_seconds: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
