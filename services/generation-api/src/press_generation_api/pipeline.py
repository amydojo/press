from __future__ import annotations

import hashlib
from contextlib import suppress
from typing import Any
from uuid import uuid4

from press_generation_api.config import Settings
from press_generation_api.domain.models import (
    AttemptStatus,
    FailureCategory,
    FailureRecord,
    GenerationAttempt,
    GenerationUnderstanding,
    PressingRecord,
    PressingStatus,
    ProgressStage,
    ProvenanceRecord,
    StoredAssetReference,
    ValidationResult,
    utc_now,
)
from press_generation_api.errors import PressError, StorageOperationError
from press_generation_api.media import validate_image_bytes
from press_generation_api.providers import GenerationProvider, ProviderError
from press_generation_api.repository import PressingRepository


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_generation_brief(understanding: GenerationUnderstanding, *, correction: int) -> str:
    correction_text = ""
    if correction:
        correction_text = (
            " Correction pass: simplify the focal subject, strengthen thumbnail legibility, "
            "and remove any lettering, labels, screens, interface chrome, or attribution."
        )
    return (
        "Create one square internal-world image for a small translucent collectible object. "
        f"Archetype: {understanding.archetype.value}. Motif: {understanding.motif}. "
        f"Atmosphere: {', '.join(understanding.atmosphere)}. "
        f"Palette guidance: {', '.join(understanding.palette)}. "
        f"Compositional density: {understanding.density.value}. "
        f"Creative brief: {understanding.generation_brief}. "
        "Use a clear focal subject and tactile material depth. Avoid generic purple AI gradients, "
        "fake application UI, source attribution, logos, and all readable text. The human note and "
        "selected fragment live outside the image and must not appear as lettering."
        + correction_text
    )


class PressingPipeline:
    def __init__(
        self,
        repository: PressingRepository,
        provider: GenerationProvider,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._settings = settings

    @staticmethod
    def _failure_from_exception(exc: Exception) -> FailureRecord:
        if isinstance(exc, ProviderError):
            return FailureRecord(
                category=exc.category,
                message=exc.message,
                retryable=exc.retryable,
                provider_code=exc.provider_code,
            )
        if isinstance(exc, PressError):
            return FailureRecord(
                category=exc.category,
                message=exc.public_message,
                retryable=exc.retryable,
            )
        return FailureRecord(
            category=FailureCategory.UNKNOWN_INTERNAL_ERROR,
            message="The pressing pipeline failed unexpectedly",
            retryable=False,
        )

    def _model_for_attempt(self, attempt_number: int) -> str:
        if attempt_number >= 3 and self._settings.GENBLAZE_FALLBACK_MODEL:
            return self._settings.GENBLAZE_FALLBACK_MODEL
        return self._settings.GENBLAZE_PRIMARY_MODEL

    def run(self, pressing_id: str) -> PressingRecord:
        record = self._repository.get_by_id(pressing_id)
        starting_attempt = len(record.attempts) + 1
        parent_run_id = record.attempts[-1].run_id if record.attempts else None
        if record.status is PressingStatus.DRAFT:
            self._repository.append_progress_event(
                pressing_id,
                stage=ProgressStage.PREPARING_SOURCE,
                message="Preparing source",
                status=PressingStatus.PREPARING_SOURCE,
            )
        for attempt_number in range(starting_attempt, self._settings.MAX_GENERATION_ATTEMPTS + 1):
            run_id = str(uuid4())
            model = self._model_for_attempt(attempt_number)
            correction = max(0, attempt_number - 1)
            stage_timestamps: dict[str, Any] = {"startedAt": utc_now()}
            base_hash = hashlib.sha256(
                (
                    record.anchors.submitted_source_identity
                    + record.anchors.selected_fragment
                    + record.anchors.personal_note
                    + str(attempt_number)
                ).encode("utf-8")
            ).hexdigest()
            brief = ""
            provider_manifest: dict[str, Any] | None = None
            validation: ValidationResult | None = None
            parameters: dict[str, Any] = {
                "attemptNumber": attempt_number,
                "correctionPass": correction,
            }
            try:
                self._repository.append_progress_event(
                    pressing_id,
                    stage=ProgressStage.UNDERSTANDING_FRAGMENT,
                    message="Understanding fragment",
                    status=PressingStatus.UNDERSTANDING_FRAGMENT,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    attempt_number=attempt_number,
                )
                stage_timestamps["understandingStartedAt"] = utc_now()
                understanding = self._provider.understand(
                    source=record.source,
                    anchors=record.anchors,
                )
                stage_timestamps["understandingCompletedAt"] = utc_now()
                self._repository.save_understanding(pressing_id, run_id, understanding)
                brief = build_generation_brief(understanding, correction=correction)
                prompt_hash = hashlib.sha256(brief.encode("utf-8")).hexdigest()

                self._repository.append_progress_event(
                    pressing_id,
                    stage=ProgressStage.CREATING_MINIATURE_WORLD,
                    message="Creating miniature world",
                    status=PressingStatus.CREATING_WORLD,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    attempt_number=attempt_number,
                )
                stage_timestamps["generationStartedAt"] = utc_now()
                generated = self._provider.generate(
                    brief=brief,
                    model=model,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                )
                stage_timestamps["generationCompletedAt"] = utc_now()
                provider_manifest = generated.manifest
                parameters.update(generated.parameters)
                parameters["providerRunId"] = generated.provider_run_id

                self._repository.append_progress_event(
                    pressing_id,
                    stage=ProgressStage.RENDERING_PRESSING,
                    message="Rendering pressing",
                    status=PressingStatus.RENDERING_PRESSING,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    attempt_number=attempt_number,
                )
                local_validation = validate_image_bytes(generated.data, self._settings)
                validation = local_validation
                if self._settings.LIVE_FORCE_RETRY_ONCE and attempt_number == 1:
                    local_validation = local_validation.model_copy(
                        update={
                            "valid": False,
                            "errors": [*local_validation.errors, "forced live retry probe"],
                            "checks": {**local_validation.checks, "forcedRetryProbe": False},
                        }
                    )
                    validation = local_validation
                if not local_validation.valid:
                    raise ProviderError(
                        FailureCategory.ASSET_VALIDATION_FAILED,
                        "; ".join(local_validation.errors),
                        True,
                    )
                assert local_validation.sha256 is not None
                assert local_validation.mime_type is not None
                asset_key = self._repository.store_attempt_asset(
                    pressing_id,
                    run_id,
                    generated.data,
                    mime_type=local_validation.mime_type,
                    sha256=local_validation.sha256,
                )
                stored_bytes = self._repository.get_object_bytes(asset_key)
                retrieved_sha = sha256_bytes(stored_bytes)
                checks = {
                    **local_validation.checks,
                    "durablyUploaded": self._repository.object_exists(asset_key),
                    "retrievedChecksumMatches": retrieved_sha == local_validation.sha256,
                }
                validation = local_validation.model_copy(
                    update={
                        "valid": all(checks.values()),
                        "checks": checks,
                        "retrieved_sha256": retrieved_sha,
                    }
                )
                if not validation.valid:
                    raise ProviderError(
                        FailureCategory.ASSET_VALIDATION_FAILED,
                        "The durable asset round-trip failed validation",
                        True,
                    )
                assert validation.mime_type is not None
                assert validation.sha256 is not None
                asset = StoredAssetReference(
                    key=asset_key,
                    mime_type=validation.mime_type,
                    size_bytes=len(generated.data),
                    sha256=validation.sha256,
                    width=validation.width,
                    height=validation.height,
                )
                stage_timestamps["validatedAt"] = utc_now()
                attempt = GenerationAttempt(
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    attempt_number=attempt_number,
                    provider=generated.provider,
                    model=generated.model,
                    status=AttemptStatus.SUCCEEDED,
                    prompt_hash=prompt_hash,
                    parameters=parameters,
                    stage_timestamps=stage_timestamps,
                    asset=asset,
                    validation=validation,
                    retry_reason="corrected generation pass" if correction else None,
                    genblaze_manifest=provider_manifest,
                )
                self._repository.save_attempt(
                    pressing_id,
                    attempt,
                    manifest_payload={"genblazeRunId": generated.provider_run_id},
                )
                self._repository.append_progress_event(
                    pressing_id,
                    stage=ProgressStage.SAVING_PRESSING,
                    message="Saving pressing",
                    status=PressingStatus.SAVING_PRESSING,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    attempt_number=attempt_number,
                )
                provenance = ProvenanceRecord(
                    pressing_id=record.id,
                    serial_number=record.serial_number,
                    source_key=self._repository.object_key(pressing_id, "source/source.json"),
                    fragment_key=self._repository.object_key(pressing_id, "source/fragment.json"),
                    note_key=self._repository.object_key(pressing_id, "source/note.json"),
                    final_asset_key=self._repository.object_key(
                        pressing_id, "final/internal-world.png"
                    ),
                    final_metadata_key=self._repository.object_key(
                        pressing_id, "final/metadata.json"
                    ),
                    generation_run_id=run_id,
                    parent_run_id=parent_run_id,
                    provider=attempt.provider,
                    model=attempt.model,
                    prompt_hash=attempt.prompt_hash,
                    asset_sha256=asset.sha256,
                    generation_manifest_key=self._repository.object_key(
                        pressing_id, f"generations/{run_id}/manifest.json"
                    ),
                    evaluation_key=self._repository.object_key(
                        pressing_id, f"generations/{run_id}/evaluation.json"
                    ),
                )
                final = self._repository.finalize(
                    pressing_id,
                    attempt=attempt,
                    provenance=provenance,
                    idempotency_key=f"finalize:{pressing_id}:{run_id}",
                )
                self._repository.append_progress_event(
                    pressing_id,
                    stage=ProgressStage.READY,
                    message="Ready",
                    status=PressingStatus.READY,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    attempt_number=attempt_number,
                )
                return self._repository.get_by_id(final.id)
            except Exception as exc:
                failure = self._failure_from_exception(exc)
                prompt_hash = (
                    hashlib.sha256(brief.encode("utf-8")).hexdigest() if brief else base_hash
                )
                attempt = GenerationAttempt(
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    attempt_number=attempt_number,
                    provider=self._provider.name,
                    model=model,
                    status=AttemptStatus.FAILED,
                    prompt_hash=prompt_hash,
                    parameters=parameters,
                    stage_timestamps={**stage_timestamps, "failedAt": utc_now()},
                    validation=validation,
                    retry_reason=failure.message if failure.retryable else None,
                    failure=failure,
                    genblaze_manifest=provider_manifest,
                )
                with suppress(StorageOperationError):
                    self._repository.save_attempt(
                        pressing_id,
                        attempt,
                        manifest_payload={"failureCategory": failure.category.value},
                    )
                if failure.retryable and attempt_number < self._settings.MAX_GENERATION_ATTEMPTS:
                    self._repository.append_progress_event(
                        pressing_id,
                        stage=ProgressStage.RETRYING_GENERATION,
                        message="Retrying generation",
                        status=PressingStatus.RETRYING_GENERATION,
                        run_id=run_id,
                        parent_run_id=parent_run_id,
                        attempt_number=attempt_number,
                    )
                    parent_run_id = run_id
                    record = self._repository.get_by_id(pressing_id)
                    continue
                self._repository.mark_failed(pressing_id, failure)
                self._repository.append_progress_event(
                    pressing_id,
                    stage=ProgressStage.FAILED,
                    message=failure.message,
                    status=PressingStatus.FAILED,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    attempt_number=attempt_number,
                )
                return self._repository.get_by_id(pressing_id)
        failure = FailureRecord(
            category=FailureCategory.RETRY_LIMIT_REACHED,
            message="The pressing reached its bounded retry limit",
            retryable=False,
        )
        self._repository.mark_failed(pressing_id, failure)
        return self._repository.get_by_id(pressing_id)
