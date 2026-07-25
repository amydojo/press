from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator
from pydantic.networks import AnyHttpUrl
from pydantic.alias_generators import to_camel


class PressingStatus(StrEnum):
    DRAFT = "draft"
    PREPARING_SOURCE = "preparing_source"
    UNDERSTANDING_FRAGMENT = "understanding_fragment"
    CREATING_WORLD = "creating_world"
    RENDERING_PRESSING = "rendering_pressing"
    SAVING_PRESSING = "saving_pressing"
    READY = "ready"
    FAILED = "failed"


class SourceType(StrEnum):
    URL = "url"
    SCREENSHOT = "screenshot"
    FIXTURE = "fixture"


class InternalArchetype(StrEnum):
    SCENE = "scene"
    RELIC = "relic"
    SIGNAL = "signal"


class FailureCategory(StrEnum):
    INVALID_SOURCE = "invalid_source"
    SOURCE_PREPARATION_FAILED = "source_preparation_failed"
    PROVIDER_AUTHENTICATION_FAILED = "provider_authentication_failed"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_TIMED_OUT = "provider_timed_out"
    MODEL_OUTPUT_MALFORMED = "model_output_malformed"
    ASSET_VALIDATION_FAILED = "asset_validation_failed"
    STORAGE_FAILED = "storage_failed"
    UNKNOWN_INTERNAL_ERROR = "unknown_internal_error"


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        use_enum_values=False,
    )


NonEmptyExactText = Annotated[str, Field(min_length=1)]
PersonalNote = Annotated[str, Field(min_length=1, max_length=120)]


class CreatePressingRequest(ApiModel):
    source_type: SourceType
    source_url: str | None = None
    source_upload_id: str | None = None
    selected_fragment: NonEmptyExactText
    personal_note: PersonalNote

    @model_validator(mode="after")
    def validate_exact_anchors_and_source(self) -> Self:
        if not self.selected_fragment.strip():
            raise ValueError("selectedFragment cannot be empty")
        if not self.personal_note.strip():
            raise ValueError("personalNote cannot be empty")

        if self.source_type is SourceType.URL:
            if self.source_url is None or not self.source_url.strip():
                raise ValueError("URL sources require sourceUrl")
            TypeAdapter(AnyHttpUrl).validate_python(self.source_url.strip())
            if self.source_upload_id is not None:
                raise ValueError("URL sources cannot include sourceUploadId")

        if self.source_type is SourceType.SCREENSHOT:
            if self.source_upload_id is None or not self.source_upload_id.strip():
                raise ValueError("Screenshot sources require sourceUploadId")
            if self.source_url is not None:
                raise ValueError("Screenshot sources cannot include sourceUrl")

        if self.source_type is SourceType.FIXTURE:
            if self.source_url is not None or self.source_upload_id is not None:
                raise ValueError("Fixture sources require neither sourceUrl nor sourceUploadId")

        return self


class PressingRecord(ApiModel):
    id: str
    serial_number: str
    status: PressingStatus
    source_type: SourceType
    source_url: str | None = None
    source_domain: str | None = None
    source_title: str | None = None
    selected_fragment: str
    personal_note: str
    internal_archetype: InternalArchetype | None = None
    generation_provider: str | None = None
    generation_model: str | None = None
    generation_run_id: str | None = None
    parent_run_id: str | None = None
    front_asset_url: str | None = None
    back_asset_url: str | None = None
    thumbnail_url: str | None = None
    failure_category: FailureCategory | None = None
    failure_message: str | None = None
    created_at: datetime
    updated_at: datetime
