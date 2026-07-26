from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed server-only configuration for PRESS PR 2."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PRESS_ENV: Literal["development", "test", "preview", "production"] = "development"
    PRESS_VERSION: str = "0.2.0"
    GIT_COMMIT_SHA: str | None = None
    BUILD_TIMESTAMP: str | None = None
    VERCEL_GIT_COMMIT_SHA: str | None = None

    GENBLAZE_PROVIDER: Literal["openai"] = "openai"
    GENBLAZE_PROVIDER_API_KEY: SecretStr | None = None
    GENBLAZE_UNDERSTANDING_MODEL: str = "gpt-4.1-mini"
    GENBLAZE_PRIMARY_MODEL: str = "gpt-image-1"
    GENBLAZE_FALLBACK_MODEL: str | None = "gpt-image-1-mini"
    GENBLAZE_IMAGE_SIZE: str = "1024x1024"
    GENBLAZE_IMAGE_QUALITY: str = "medium"
    GENERATION_TIMEOUT_SECONDS: float = Field(default=120.0, gt=0, le=600)
    MAX_GENERATION_ATTEMPTS: int = Field(default=3, ge=1, le=3)

    B2_KEY_ID: SecretStr | None = None
    B2_APPLICATION_KEY: SecretStr | None = None
    B2_BUCKET_NAME: str | None = None
    B2_ENDPOINT: str | None = None
    B2_REGION: str | None = "us-west-004"
    B2_PRESIGNED_URL_LIFETIME_SECONDS: int = Field(default=900, ge=60, le=3600)
    B2_CONNECT_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0, le=120)
    B2_READ_TIMEOUT_SECONDS: float = Field(default=300.0, gt=0, le=900)
    B2_SDK_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=5)
    MAX_SOURCE_BYTES: int = Field(default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)
    MAX_GENERATED_ASSET_BYTES: int = Field(
        default=25 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024
    )
    MIN_IMAGE_EDGE: int = Field(default=512, ge=64, le=2048)
    MAX_IMAGE_EDGE: int = Field(default=4096, ge=512, le=8192)

    FIXTURE_MODE: bool = Field(
        default=True, validation_alias=AliasChoices("FIXTURE_MODE", "DEMO_MODE")
    )
    LIVE_INTEGRATION_TEST: bool = False
    LIVE_FORCE_RETRY_ONCE: bool = False

    @model_validator(mode="after")
    def validate_groups(self) -> Self:
        b2_values = (
            self.B2_KEY_ID,
            self.B2_APPLICATION_KEY,
            self.B2_BUCKET_NAME,
            self.B2_ENDPOINT,
            self.B2_REGION,
        )
        any_b2 = any(value is not None and value != "" for value in b2_values[:4])
        all_b2 = all(value is not None and value != "" for value in b2_values)
        if any_b2 and not all_b2:
            raise ValueError(
                "B2 configuration must be supplied as a complete server-only group: "
                "B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME, B2_ENDPOINT, and B2_REGION"
            )
        if self.B2_ENDPOINT is not None:
            parsed = urlparse(self.B2_ENDPOINT)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("B2_ENDPOINT must be an absolute HTTPS endpoint")
        if self.MIN_IMAGE_EDGE > self.MAX_IMAGE_EDGE:
            raise ValueError("MIN_IMAGE_EDGE cannot exceed MAX_IMAGE_EDGE")
        return self

    @property
    def commit_sha(self) -> str | None:
        return self.GIT_COMMIT_SHA or self.VERCEL_GIT_COMMIT_SHA

    @property
    def live_provider_configured(self) -> bool:
        return self.GENBLAZE_PROVIDER_API_KEY is not None

    @property
    def b2_configured(self) -> bool:
        return all(
            value is not None
            for value in (
                self.B2_KEY_ID,
                self.B2_APPLICATION_KEY,
                self.B2_BUCKET_NAME,
                self.B2_ENDPOINT,
                self.B2_REGION,
            )
        )

    def require_live_configuration(self) -> None:
        missing: list[str] = []
        if self.GENBLAZE_PROVIDER_API_KEY is None:
            missing.append("GENBLAZE_PROVIDER_API_KEY")
        for name in (
            "B2_KEY_ID",
            "B2_APPLICATION_KEY",
            "B2_BUCKET_NAME",
            "B2_ENDPOINT",
            "B2_REGION",
        ):
            if getattr(self, name) is None:
                missing.append(name)
        if missing:
            raise ValueError("Missing live configuration: " + ", ".join(missing))


@lru_cache
def get_settings() -> Settings:
    return Settings()
