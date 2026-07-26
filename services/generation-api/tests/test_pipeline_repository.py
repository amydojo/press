from __future__ import annotations

from threading import Thread

import pytest

from conftest import ScriptedProvider
from press_generation_api.config import Settings
from press_generation_api.domain.models import (
    CreatePressingRequest,
    FailureCategory,
    GenerationUnderstanding,
    PressingStatus,
    SourceType,
)
from press_generation_api.errors import PressingConflictError, PressingNotFoundError
from press_generation_api.media import create_fixture_png
from press_generation_api.pipeline import PressingPipeline, validate_image_bytes
from press_generation_api.providers import ProviderError
from press_generation_api.repository import PressingRepository
from press_generation_api.storage import InMemoryObjectStore


def request() -> CreatePressingRequest:
    return CreatePressingRequest(
        source_type=SourceType.FIXTURE,
        selected_fragment="The exact fragment must remain exactly this.",
        personal_note="I stopped because it felt strangely physical.",
    )


def run_pipeline(
    settings: Settings,
    provider: ScriptedProvider,
    store: InMemoryObjectStore | None = None,
) -> tuple[PressingRepository, str]:
    resolved_store = store or InMemoryObjectStore()
    repository = PressingRepository(resolved_store, max_attempts=settings.MAX_GENERATION_ATTEMPTS)
    record, created = repository.create_draft(request(), idempotency_key="create-1")
    assert created
    PressingPipeline(repository, provider, settings).run(record.id)
    return repository, record.id


def test_successful_pipeline_persists_complete_tree_and_anchors(
    settings: Settings, scripted_provider: ScriptedProvider
) -> None:
    store = InMemoryObjectStore()
    repository, pressing_id = run_pipeline(settings, scripted_provider, store)
    record = repository.get_by_id(pressing_id)
    assert record.status is PressingStatus.READY
    assert record.anchors.selected_fragment == "The exact fragment must remain exactly this."
    assert record.anchors.personal_note == "I stopped because it felt strangely physical."
    assert record.final is not None
    keys = store.list_keys(f"pressings/{pressing_id}/")
    assert repository.object_key(pressing_id, "source/source.json") in keys
    assert repository.object_key(pressing_id, "source/fragment.json") in keys
    assert repository.object_key(pressing_id, "source/note.json") in keys
    assert repository.object_key(pressing_id, "events/progress.jsonl") in keys
    assert repository.object_key(pressing_id, "final/metadata.json") in keys
    assert repository.object_key(pressing_id, "final/provenance.json") in keys
    assert record.attempts[0].asset is not None
    assert record.attempts[0].asset.key in keys
    assert repository.create_presigned_asset_access(pressing_id, expires_in=120)


def test_process_restart_reconstructs_same_pressing(
    settings: Settings, scripted_provider: ScriptedProvider
) -> None:
    store = InMemoryObjectStore()
    repository, pressing_id = run_pipeline(settings, scripted_provider, store)
    before = repository.get_by_id(pressing_id)
    restarted = PressingRepository(store, max_attempts=3)
    after = restarted.get_by_id(pressing_id)
    assert after == before
    assert after.final is not None
    assert restarted.get_object_bytes(after.final.final_asset.key)


def test_provider_timeout_then_success_preserves_parent_lineage(
    settings: Settings,
    understanding: GenerationUnderstanding,
    provider_failure_timeout: ProviderError,
) -> None:
    provider = ScriptedProvider(
        understanding=understanding,
        generate_outcomes=[provider_failure_timeout, create_fixture_png()],
    )
    repository, pressing_id = run_pipeline(settings, provider)
    record = repository.get_by_id(pressing_id)
    assert record.status is PressingStatus.READY
    assert len(record.attempts) == 2
    assert record.attempts[1].parent_run_id == record.attempts[0].run_id
    assert record.attempts[0].failure is not None
    assert record.attempts[0].failure.category is FailureCategory.PROVIDER_TIMED_OUT
    stages = [event.stage.value for event in repository.get_events(pressing_id)]
    assert "retrying_generation" in stages
    assert stages[-1] == "ready"


def test_malformed_understanding_then_corrected_retry(
    settings: Settings, understanding: GenerationUnderstanding
) -> None:
    malformed = ProviderError(
        FailureCategory.MODEL_OUTPUT_MALFORMED,
        "malformed structured output",
        True,
    )
    provider = ScriptedProvider(
        understanding=understanding,
        understand_outcomes=[malformed, understanding],
    )
    repository, pressing_id = run_pipeline(settings, provider)
    record = repository.get_by_id(pressing_id)
    assert record.status is PressingStatus.READY
    assert len(record.attempts) == 2
    assert record.attempts[0].failure is not None
    assert record.attempts[0].failure.category is FailureCategory.MODEL_OUTPUT_MALFORMED


def test_invalid_asset_then_corrected_retry(
    settings: Settings, understanding: GenerationUnderstanding
) -> None:
    provider = ScriptedProvider(
        understanding=understanding,
        generate_outcomes=[b"not-an-image", create_fixture_png()],
    )
    repository, pressing_id = run_pipeline(settings, provider)
    record = repository.get_by_id(pressing_id)
    assert record.status is PressingStatus.READY
    assert len(record.attempts) == 2
    assert record.attempts[0].validation is not None
    assert not record.attempts[0].validation.valid
    assert record.attempts[0].failure is not None
    assert record.attempts[0].failure.category is FailureCategory.ASSET_VALIDATION_FAILED


def test_primary_failures_use_configured_fallback_model(
    settings: Settings,
    understanding: GenerationUnderstanding,
    provider_failure_timeout: ProviderError,
) -> None:
    provider = ScriptedProvider(
        understanding=understanding,
        generate_outcomes=[
            provider_failure_timeout,
            provider_failure_timeout,
            create_fixture_png(),
        ],
    )
    repository, pressing_id = run_pipeline(settings, provider)
    record = repository.get_by_id(pressing_id)
    assert record.status is PressingStatus.READY
    assert provider.models == [
        settings.GENBLAZE_PRIMARY_MODEL,
        settings.GENBLAZE_PRIMARY_MODEL,
        settings.GENBLAZE_FALLBACK_MODEL,
    ]
    assert len({attempt.run_id for attempt in record.attempts}) == 3


def test_retry_limit_reached_is_terminal(
    settings: Settings,
    understanding: GenerationUnderstanding,
    provider_failure_timeout: ProviderError,
) -> None:
    provider = ScriptedProvider(
        understanding=understanding,
        generate_outcomes=[
            provider_failure_timeout,
            provider_failure_timeout,
            provider_failure_timeout,
        ],
    )
    repository, pressing_id = run_pipeline(settings, provider)
    record = repository.get_by_id(pressing_id)
    assert record.status is PressingStatus.FAILED
    assert len(record.attempts) == 3
    assert record.failure is not None
    assert record.failure.category is FailureCategory.PROVIDER_TIMED_OUT


class AssetFailingStore(InMemoryObjectStore):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        if "/asset." in key and not self.failed:
            self.failed = True
            from press_generation_api.errors import map_storage_exception

            raise map_storage_exception(RuntimeError("forced upload failure"), operation="put")
        return super().put_bytes(key, data, content_type=content_type, metadata=metadata)


def test_storage_failure_after_generation_recovers_on_next_attempt(
    settings: Settings, scripted_provider: ScriptedProvider
) -> None:
    store = AssetFailingStore()
    repository, pressing_id = run_pipeline(settings, scripted_provider, store)
    record = repository.get_by_id(pressing_id)
    assert record.status is PressingStatus.READY
    assert len(record.attempts) == 2
    assert record.attempts[0].failure is not None
    assert record.attempts[0].failure.category is FailureCategory.STORAGE_UPLOAD_FAILED


def test_idempotent_create_and_serial_survive_restart(settings: Settings) -> None:
    store = InMemoryObjectStore()
    repo = PressingRepository(store)
    first, created = repo.create_draft(request(), idempotency_key="same")
    assert created
    duplicate, created = repo.create_draft(request(), idempotency_key="same")
    assert not created
    assert duplicate.id == first.id
    restarted = PressingRepository(store)
    second, created = restarted.create_draft(request(), idempotency_key="different")
    assert created
    assert first.serial_number == "P-0001"
    assert second.serial_number == "P-0002"


def test_concurrent_serial_allocation_is_unique() -> None:
    store = InMemoryObjectStore()
    repo = PressingRepository(store)
    serials: list[str] = []

    def create(index: int) -> None:
        record, _ = repo.create_draft(request(), idempotency_key=f"key-{index}")
        serials.append(record.serial_number)

    threads = [Thread(target=create, args=(index,)) for index in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(serials) == 12
    assert len(set(serials)) == 12


def test_delete_removes_prefix_and_leaves_tombstone(
    settings: Settings, scripted_provider: ScriptedProvider
) -> None:
    store = InMemoryObjectStore()
    repository, pressing_id = run_pipeline(settings, scripted_provider, store)
    result = repository.delete(pressing_id)
    assert result.status is PressingStatus.DELETED
    assert store.list_keys(f"pressings/{pressing_id}/") == []
    assert store.head(result.tombstone_key) is not None
    with pytest.raises(PressingNotFoundError):
        repository.get_by_id(pressing_id)


def test_ready_pressing_rejects_retry(
    settings: Settings, scripted_provider: ScriptedProvider
) -> None:
    repository, pressing_id = run_pipeline(settings, scripted_provider)
    with pytest.raises(PressingConflictError):
        repository.begin_retry(pressing_id, idempotency_key="retry")


def test_image_validation_rejects_blank_and_undersized(settings: Settings) -> None:
    blank = b"not-an-image"
    result = validate_image_bytes(blank, settings)
    assert not result.valid
    assert not result.checks["fileDecodes"]
