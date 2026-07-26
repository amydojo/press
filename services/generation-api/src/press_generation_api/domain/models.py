from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator
from pydantic.alias_generators import to_camel
from pydantic.networks import AnyHttpUrl


def utc_now() -> datetime:
    return datetime.now(UTC)


class PressingStatus(StrEnum):
    DRAFT = "draft"
    PREPARING_SOURCE = "preparing_source"
    UNDERSTANDING_FRAGMENT = "understanding_fragment"
    CREATING_WORLD = "creating_world"
    RENDERING_PRESSING = "rendering_pressing"
    SAVING_PRESSING = "saving_pressing"
    RETRYING_GENERATION = "retrying_generation"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class ProgressStage(StrEnum):
    PREPARING_SOURCE = "preparing_source"
    UNDERSTANDING_FRAGMENT = "understanding_fragment"
    CREATING_MINIATURE_WORLD = "creating_miniature_world"
    RENDERING_PRESSING = "rendering_pressing"
    SAVING_PRESSING = "saving_pressing"
    RETRYING_GENERATION = "retrying_generation"
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


class ContentType(StrEnum):
    ARTICLE = "article"
    IMAGE = "image"
    POST = "post"
    MUSIC = "music"
    EXPERIMENTAL = "experimental"
    OTHER = "other"


class Density(StrEnum):
    QUIET = "quiet"
    BALANCED = "balanced"
    DENSE = "dense"


class AttemptStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class FailureCategory(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_SOURCE = "invalid_source"
    SOURCE_PREPARATION_FAILED = "source_preparation_failed"
    PROVIDER_AUTHENTICATION_FAILED = "provider_authentication_failed"
    PROVIDER_AUTHORIZATION_FAILED = "provider_authorization_failed"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_TIMED_OUT = "provider_timed_out"
    MODEL_OUTPUT_MALFORMED = "model_output_malformed"
    ASSET_VALIDATION_FAILED = "asset_validation_failed"
    STORAGE_AUTHENTICATION_FAILED = "storage_authentication_failed"
    STORAGE_AUTHORIZATION_FAILED = "storage_authorization_failed"
    STORAGE_BUCKET_MISSING = "storage_bucket_missing"
    STORAGE_OBJECT_MISSING = "storage_object_missing"
    STORAGE_TIMED_OUT = "storage_timed_out"
    STORAGE_RATE_LIMITED = "storage_rate_limited"
    STORAGE_INVALID_KEY = "storage_invalid_key"
    STORAGE_UPLOAD_FAILED = "storage_upload_failed"
    STORAGE_DOWNLOAD_FAILED = "storage_download_failed"
    STORAGE_PARTIAL_FINALIZATION_FAILED = "storage_partial_finalization_failed"
    STORAGE_FAILED = "storage_failed"
    RETRY_LIMIT_REACHED = "retry_limit_reached"
    CONFLICT = "conflict"
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
HexColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CreatePressingRequest(ApiModel):
    source_type: SourceType
    source_url: str | None = None
    source_upload_id: str | None = None
    source_title: str | None = Field(default=None, max_length=300)
    source_domain: str | None = Field(default=None, max_length=255)
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

        if self.source_type is SourceType.FIXTURE and (
            self.source_url is not None or self.source_upload_id is not None
        ):
            raise ValueError("Fixture sources require neither sourceUrl nor sourceUploadId")

        return self


class RetryRequest(ApiModel):
    reason: str | None = Field(default=None, max_length=300)


class SourceRecord(ApiModel):
    source_type: SourceType
    submitted_url: str | None = None
    canonical_url: str | None = None
    submitted_source_identity: str
    source_upload_id: str | None = None
    domain: str | None = None
    title: str | None = None
    captured_at: datetime = Field(default_factory=utc_now)
    content_type: str | None = None
    snapshot_key: str | None = None


class ImmutableAnchors(ApiModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )

    selected_fragment: NonEmptyExactText
    personal_note: PersonalNote
    submitted_source_identity: str
    confirmed_at: datetime = Field(default_factory=utc_now)


class GenerationUnderstanding(ApiModel):
    content_type: ContentType
    motif: str = Field(min_length=1, max_length=500)
    palette: list[HexColor] = Field(min_length=1, max_length=8)
    atmosphere: list[str] = Field(min_length=1, max_length=8)
    density: Density
    archetype: InternalArchetype
    generation_brief: str = Field(min_length=20, max_length=4000)

    @field_validator("atmosphere")
    @classmethod
    def validate_atmosphere(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("atmosphere entries cannot be blank")
        return values


class StoredAssetReference(ApiModel):
    key: str
    mime_type: str
    size_bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)


class ValidationResult(ApiModel):
    valid: bool
    checks: dict[str, bool]
    errors: list[str] = Field(default_factory=list)
    mime_type: str | None = None
    size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    retrieved_sha256: str | None = None
    validated_at: datetime = Field(default_factory=utc_now)


class FailureRecord(ApiModel):
    category: FailureCategory
    message: str
    retryable: bool
    occurred_at: datetime = Field(default_factory=utc_now)
    provider_code: str | None = None


class GenerationAttempt(ApiModel):
    run_id: str
    parent_run_id: str | None = None
    attempt_number: int = Field(ge=1, le=3)
    provider: str
    model: str
    status: AttemptStatus
    prompt_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameters: dict[str, Any]
    stage_timestamps: dict[str, datetime]
    asset: StoredAssetReference | None = None
    validation: ValidationResult | None = None
    retry_reason: str | None = None
    failure: FailureRecord | None = None
    genblaze_manifest: dict[str, Any] | None = None


class GenerationRunManifest(ApiModel):
    pressing_id: str
    run_id: str
    parent_run_id: str | None = None
    attempt_number: int
    provider: str
    model: str
    prompt_hash: str
    parameters: dict[str, Any]
    stage_timestamps: dict[str, datetime]
    output_key: str | None = None
    output_mime_type: str | None = None
    output_dimensions: tuple[int, int] | None = None
    output_sha256: str | None = None
    validation: ValidationResult | None = None
    retry_reason: str | None = None
    failure: FailureRecord | None = None
    final_status: AttemptStatus
    genblaze_manifest: dict[str, Any] | None = None


class ProgressEvent(ApiModel):
    sequence: int = Field(ge=1)
    stage: ProgressStage
    message: str
    pressing_status: PressingStatus
    timestamp: datetime = Field(default_factory=utc_now)
    run_id: str | None = None
    parent_run_id: str | None = None
    attempt_number: int | None = None


class ProvenanceRecord(ApiModel):
    pressing_id: str
    serial_number: str
    source_key: str
    fragment_key: str
    note_key: str
    final_asset_key: str
    final_metadata_key: str
    generation_run_id: str
    parent_run_id: str | None = None
    provider: str
    model: str
    prompt_hash: str
    asset_sha256: str
    generation_manifest_key: str
    evaluation_key: str
    created_at: datetime = Field(default_factory=utc_now)


class FinalizedPressingRecord(ApiModel):
    internal_archetype: InternalArchetype
    generation_run_id: str
    parent_run_id: str | None = None
    final_asset: StoredAssetReference
    metadata_key: str
    provenance_key: str
    finalized_at: datetime = Field(default_factory=utc_now)


class PressingRecord(ApiModel):
    id: str
    serial_number: str
    status: PressingStatus
    source: SourceRecord
    anchors: ImmutableAnchors
    understanding: GenerationUnderstanding | None = None
    attempts: list[GenerationAttempt] = Field(default_factory=list)
    final: FinalizedPressingRecord | None = None
    failure: FailureRecord | None = None
    progress_event_count: int = 0
    idempotency_key_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PressingAssetAccess(ApiModel):
    key: str
    url: str
    expires_in_seconds: int


class PressingResponse(ApiModel):
    pressing: PressingRecord
    final_asset_access: PressingAssetAccess | None = None


class ProgressResponse(ApiModel):
    pressing_id: str
    events: list[ProgressEvent]
    terminal: bool


class DeletePressingResponse(ApiModel):
    pressing_id: str
    status: PressingStatus
    tombstone_key: str
