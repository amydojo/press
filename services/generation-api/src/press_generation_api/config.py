from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server-only runtime configuration.

    Sponsor credentials are optional in PR 1. If any B2 value is supplied, the
    complete B2 group must be supplied so a partial configuration cannot look ready.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PRESS_ENV: Literal["development", "test", "preview", "production"] = "development"
    PRESS_VERSION: str = "0.1.0"
    GIT_COMMIT_SHA: str | None = None
    BUILD_TIMESTAMP: str | None = None
    VERCEL_GIT_COMMIT_SHA: str | None = None

    B2_KEY_ID: SecretStr | None = None
    B2_APPLICATION_KEY: SecretStr | None = None
    B2_BUCKET_NAME: str | None = None
    B2_ENDPOINT: str | None = None
    GENBLAZE_PROVIDER_API_KEY: SecretStr | None = None
    DEMO_MODE: bool = True

    @model_validator(mode="after")
    def validate_b2_group(self) -> "Settings":
        values = [
            self.B2_KEY_ID,
            self.B2_APPLICATION_KEY,
            self.B2_BUCKET_NAME,
            self.B2_ENDPOINT,
        ]
        if any(value is not None and value != "" for value in values) and not all(
            value is not None and value != "" for value in values
        ):
            raise ValueError("B2 configuration must be supplied as a complete server-only group")
        return self

    @property
    def commit_sha(self) -> str | None:
        return self.GIT_COMMIT_SHA or self.VERCEL_GIT_COMMIT_SHA


@lru_cache
def get_settings() -> Settings:
    return Settings()
