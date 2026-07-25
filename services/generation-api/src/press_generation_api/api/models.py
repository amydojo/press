from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ResponseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class HealthResponse(ResponseModel):
    status: Literal["ok"]
    service: Literal["press-generation-api"]
    version: str
    environment: str
    timestamp: datetime


class VersionResponse(ResponseModel):
    version: str
    commit_sha: str | None = None
    build_timestamp: str | None = None


class NotImplementedDetail(ResponseModel):
    code: Literal["generation_not_implemented"]
    message: str
    arrives_in: Literal["PR 2"]


class NotImplementedResponse(ResponseModel):
    detail: NotImplementedDetail
