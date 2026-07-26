from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from press_generation_api.domain.models import FailureCategory


class ResponseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class HealthResponse(ResponseModel):
    status: Literal["ok"]
    service: Literal["press-generation-api"]
    version: str
    environment: str
    timestamp: datetime
    live_provider_configured: bool
    durable_storage_configured: bool


class VersionResponse(ResponseModel):
    version: str
    commit_sha: str | None = None
    build_timestamp: str | None = None
    sponsor_backbone: Literal["pr-2"] = "pr-2"


class ErrorDetail(ResponseModel):
    code: FailureCategory
    message: str
    retryable: bool
    request_id: str | None = None


class ErrorResponse(ResponseModel):
    detail: ErrorDetail
