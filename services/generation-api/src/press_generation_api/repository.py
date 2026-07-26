from __future__ import annotations

import hashlib
from threading import RLock
from typing import TypeVar
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel

from press_generation_api.domain.models import (
    AttemptStatus,
    CreatePressingRequest,
    DeletePressingResponse,
    FailureCategory,
    FailureRecord,
    FinalizedPressingRecord,
    GenerationAttempt,
    GenerationUnderstanding,
    ImmutableAnchors,
    PressingRecord,
    PressingStatus,
    ProgressEvent,
    ProgressStage,
    ProvenanceRecord,
    SourceRecord,
    SourceType,
    StoredAssetReference,
    utc_now,
)
from press_generation_api.domain.state_machine import transition
from press_generation_api.errors import (
    PressingConflictError,
    PressingNotFoundError,
    RetryLimitReachedError,
    StorageOperationError,
)
from press_generation_api.storage import ObjectStore, json_bytes, parse_json

T = TypeVar("T", bound=BaseModel)


class PressingRepository:
    """Durable PRESS repository whose source of truth is object storage."""

    _serial_lock = RLock()

    def __init__(self, store: ObjectStore, *, max_attempts: int = 3) -> None:
        self._store = store
        self._max_attempts = max_attempts
        self._lock = RLock()

    @staticmethod
    def _prefix(pressing_id: str) -> str:
        return f"pressings/{pressing_id}"

    @classmethod
    def _key(cls, pressing_id: str, suffix: str) -> str:
        return f"{cls._prefix(pressing_id)}/{suffix}"

    def _put_model(self, key: str, value: BaseModel) -> str:
        return self._store.put_bytes(
            key,
            json_bytes(value.model_dump(by_alias=True, mode="json")),
            content_type="application/json",
            metadata={"press-record-type": type(value).__name__},
        )

    def _get_model(self, key: str, model: type[T]) -> T:
        return model.model_validate(parse_json(self._store.get_bytes(key)))

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _request_fingerprint(request: CreatePressingRequest) -> str:
        payload = request.model_dump_json(by_alias=True, exclude_none=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _allocate_serial(self) -> str:
        key = "system/serial-counter.json"
        with self._serial_lock:
            head = self._store.head(key)
            current = 0
            if head is not None:
                payload = parse_json(self._store.get_bytes(key))
                current = int(payload["lastSerial"])
            next_value = current + 1
            self._store.put_bytes(
                key,
                json_bytes({"lastSerial": next_value, "updatedAt": utc_now()}),
                content_type="application/json",
            )
            return f"P-{next_value:04d}"

    @staticmethod
    def _normalize_source(request: CreatePressingRequest) -> tuple[SourceRecord, ImmutableAnchors]:
        if request.source_type is SourceType.URL:
            assert request.source_url is not None
            submitted = request.source_url.strip()
            parsed = urlparse(submitted)
            identity = submitted
            domain = request.source_domain or parsed.hostname
            source = SourceRecord(
                source_type=request.source_type,
                submitted_url=submitted,
                canonical_url=submitted,
                submitted_source_identity=identity,
                domain=domain,
                title=request.source_title,
            )
        elif request.source_type is SourceType.SCREENSHOT:
            assert request.source_upload_id is not None
            identity = f"upload:{request.source_upload_id}"
            source = SourceRecord(
                source_type=request.source_type,
                submitted_source_identity=identity,
                source_upload_id=request.source_upload_id,
                domain=request.source_domain,
                title=request.source_title,
            )
        else:
            identity = "fixture:demo-source:v1"
            source = SourceRecord(
                source_type=request.source_type,
                submitted_source_identity=identity,
                domain=request.source_domain or "demo.press.local",
                title=request.source_title or "Designing with rhythm",
                content_type="text/html",
            )
        anchors = ImmutableAnchors(
            selected_fragment=request.selected_fragment,
            personal_note=request.personal_note,
            submitted_source_identity=identity,
        )
        return source, anchors

    def create_draft(
        self, request: CreatePressingRequest, *, idempotency_key: str | None = None
    ) -> tuple[PressingRecord, bool]:
        fingerprint = self._request_fingerprint(request)
        resolved_key = (
            idempotency_key.strip() if idempotency_key and idempotency_key.strip() else fingerprint
        )
        key_hash = self._hash(resolved_key)
        idempotency_object = f"idempotency/create/{key_hash}.json"
        with self._lock:
            existing = self._store.head(idempotency_object)
            if existing is not None:
                payload = parse_json(self._store.get_bytes(idempotency_object))
                if payload["requestFingerprint"] != fingerprint:
                    raise PressingConflictError(
                        "The idempotency key was already used for a different pressing request"
                    )
                return self.get_by_id(str(payload["pressingId"])), False

            pressing_id = str(uuid4())
            source, anchors = self._normalize_source(request)
            record = PressingRecord(
                id=pressing_id,
                serial_number=self._allocate_serial(),
                status=PressingStatus.DRAFT,
                source=source,
                anchors=anchors,
                idempotency_key_hash=key_hash,
            )
            self._put_model(self._key(pressing_id, "source/source.json"), source)
            self._store.put_bytes(
                self._key(pressing_id, "source/fragment.json"),
                json_bytes(
                    {
                        "text": anchors.selected_fragment,
                        "selectionMethod": "selected",
                        "confirmedAt": anchors.confirmed_at,
                    }
                ),
                content_type="application/json",
            )
            self._store.put_bytes(
                self._key(pressing_id, "source/note.json"),
                json_bytes({"text": anchors.personal_note, "confirmedAt": anchors.confirmed_at}),
                content_type="application/json",
            )
            self._put_model(self._key(pressing_id, "state/current.json"), record)
            self._store.put_bytes(
                idempotency_object,
                json_bytes(
                    {
                        "pressingId": pressing_id,
                        "requestFingerprint": fingerprint,
                        "createdAt": record.created_at,
                    }
                ),
                content_type="application/json",
            )
            return record, True

    def get_by_id(self, pressing_id: str) -> PressingRecord:
        tombstone = f"tombstones/{pressing_id}.json"
        if self._store.head(tombstone) is not None:
            raise PressingNotFoundError(pressing_id)
        key = self._key(pressing_id, "state/current.json")
        if self._store.head(key) is None:
            raise PressingNotFoundError(pressing_id)
        return self._get_model(key, PressingRecord)

    def list_pressings(self) -> list[PressingRecord]:
        keys = [
            key
            for key in self._store.list_keys("pressings/")
            if key.endswith("/state/current.json")
        ]
        return sorted(
            (self._get_model(key, PressingRecord) for key in keys),
            key=lambda record: record.created_at,
            reverse=True,
        )

    def _save_current(self, record: PressingRecord) -> PressingRecord:
        updated = record.model_copy(update={"updated_at": utc_now()})
        self._put_model(self._key(record.id, "state/current.json"), updated)
        return updated

    def update_status(self, pressing_id: str, status: PressingStatus) -> PressingRecord:
        with self._lock:
            record = self.get_by_id(pressing_id)
            transition(record.status, status)
            return self._save_current(record.model_copy(update={"status": status}))

    def append_progress_event(
        self,
        pressing_id: str,
        *,
        stage: ProgressStage,
        message: str,
        status: PressingStatus,
        run_id: str | None = None,
        parent_run_id: str | None = None,
        attempt_number: int | None = None,
    ) -> ProgressEvent:
        with self._lock:
            record = self.get_by_id(pressing_id)
            events = self.get_events(pressing_id)
            if events:
                previous = events[-1]
                if (
                    previous.stage is stage
                    and previous.pressing_status is status
                    and previous.run_id == run_id
                    and previous.attempt_number == attempt_number
                ):
                    return previous
            event = ProgressEvent(
                sequence=len(events) + 1,
                stage=stage,
                message=message,
                pressing_status=status,
                run_id=run_id,
                parent_run_id=parent_run_id,
                attempt_number=attempt_number,
            )
            line = event.model_dump_json(by_alias=True) + "\n"
            events_key = self._key(pressing_id, "events/progress.jsonl")
            previous_bytes = b""
            if self._store.head(events_key) is not None:
                previous_bytes = self._store.get_bytes(events_key)
            self._store.put_bytes(
                events_key,
                previous_bytes + line.encode("utf-8"),
                content_type="application/x-ndjson",
            )
            next_record = record.model_copy(
                update={"status": status, "progress_event_count": event.sequence}
            )
            self._save_current(next_record)
            return event

    def get_events(self, pressing_id: str) -> list[ProgressEvent]:
        self.get_by_id(pressing_id)
        key = self._key(pressing_id, "events/progress.jsonl")
        if self._store.head(key) is None:
            return []
        raw = self._store.get_bytes(key).decode("utf-8")
        return [ProgressEvent.model_validate_json(line) for line in raw.splitlines() if line]

    def save_understanding(
        self, pressing_id: str, run_id: str, understanding: GenerationUnderstanding
    ) -> PressingRecord:
        with self._lock:
            record = self.get_by_id(pressing_id)
            self._put_model(
                self._key(pressing_id, f"generations/{run_id}/understanding.json"),
                understanding,
            )
            return self._save_current(record.model_copy(update={"understanding": understanding}))

    def save_attempt(
        self,
        pressing_id: str,
        attempt: GenerationAttempt,
        *,
        manifest_payload: dict[str, object],
    ) -> PressingRecord:
        with self._lock:
            record = self.get_by_id(pressing_id)
            manifest_key = self._key(pressing_id, f"generations/{attempt.run_id}/manifest.json")
            if self._store.head(manifest_key) is not None:
                existing = GenerationAttempt.model_validate(
                    parse_json(self._store.get_bytes(manifest_key))["attempt"]
                )
                if existing != attempt:
                    raise PressingConflictError("A generation run cannot be overwritten")
                return record
            evaluation_key = self._key(pressing_id, f"generations/{attempt.run_id}/evaluation.json")
            if attempt.validation is not None:
                self._put_model(evaluation_key, attempt.validation)
            self._store.put_bytes(
                manifest_key,
                json_bytes(
                    {"attempt": attempt.model_dump(by_alias=True, mode="json"), **manifest_payload}
                ),
                content_type="application/json",
            )
            attempts = [*record.attempts, attempt]
            return self._save_current(record.model_copy(update={"attempts": attempts}))

    def store_attempt_asset(
        self,
        pressing_id: str,
        run_id: str,
        data: bytes,
        *,
        mime_type: str,
        sha256: str,
    ) -> str:
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[mime_type]
        key = self._key(pressing_id, f"generations/{run_id}/asset.{extension}")
        self._store.put_bytes(
            key,
            data,
            content_type=mime_type,
            metadata={"sha256": sha256, "pressing-id": pressing_id, "run-id": run_id},
        )
        return key

    def finalize(
        self,
        pressing_id: str,
        *,
        attempt: GenerationAttempt,
        provenance: ProvenanceRecord,
        idempotency_key: str,
    ) -> PressingRecord:
        with self._lock:
            record = self.get_by_id(pressing_id)
            finalization_hash = self._hash(idempotency_key)
            idempotency_object = f"idempotency/finalize/{pressing_id}/{finalization_hash}.json"
            if self._store.head(idempotency_object) is not None:
                return record
            if record.final is not None:
                return record
            if attempt.status is not AttemptStatus.SUCCEEDED or attempt.asset is None:
                raise PressingConflictError("Only a validated successful attempt can be finalized")

            source_bytes = self._store.get_bytes(attempt.asset.key)
            final_key = self._key(pressing_id, "final/internal-world.png")
            self._store.put_bytes(
                final_key,
                source_bytes,
                content_type=attempt.asset.mime_type,
                metadata={"sha256": attempt.asset.sha256, "generation-run-id": attempt.run_id},
            )
            final_asset = StoredAssetReference(
                key=final_key,
                mime_type=attempt.asset.mime_type,
                size_bytes=attempt.asset.size_bytes,
                sha256=attempt.asset.sha256,
                width=attempt.asset.width,
                height=attempt.asset.height,
            )
            metadata_key = self._key(pressing_id, "final/metadata.json")
            provenance_key = self._key(pressing_id, "final/provenance.json")
            if record.understanding is None:
                raise PressingConflictError("Understanding is required before finalization")
            finalized = FinalizedPressingRecord(
                internal_archetype=record.understanding.archetype,
                generation_run_id=attempt.run_id,
                parent_run_id=attempt.parent_run_id,
                final_asset=final_asset,
                metadata_key=metadata_key,
                provenance_key=provenance_key,
            )
            metadata = {
                "pressingId": record.id,
                "serialNumber": record.serial_number,
                "status": PressingStatus.READY.value,
                "internalArchetype": record.understanding.archetype.value,
                "sourceDomain": record.source.domain,
                "selectedFragment": record.anchors.selected_fragment,
                "personalNote": record.anchors.personal_note,
                "generationRunId": attempt.run_id,
                "parentRunId": attempt.parent_run_id,
                "createdAt": record.created_at,
                "assetKeys": {"internalWorld": final_key},
            }
            self._store.put_bytes(
                metadata_key, json_bytes(metadata), content_type="application/json"
            )
            self._put_model(
                provenance_key, provenance.model_copy(update={"final_asset_key": final_key})
            )
            next_record = record.model_copy(
                update={
                    "status": PressingStatus.READY,
                    "final": finalized,
                    "failure": None,
                }
            )
            saved = self._save_current(next_record)
            self._store.put_bytes(
                idempotency_object,
                json_bytes({"pressingId": pressing_id, "runId": attempt.run_id}),
                content_type="application/json",
            )
            return saved

    def mark_failed(self, pressing_id: str, failure: FailureRecord) -> PressingRecord:
        with self._lock:
            record = self.get_by_id(pressing_id)
            return self._save_current(
                record.model_copy(update={"status": PressingStatus.FAILED, "failure": failure})
            )

    def begin_retry(self, pressing_id: str, *, idempotency_key: str) -> tuple[PressingRecord, bool]:
        with self._lock:
            record = self.get_by_id(pressing_id)
            if record.status is PressingStatus.READY:
                raise PressingConflictError("A ready pressing cannot be retried")
            if len(record.attempts) >= self._max_attempts:
                raise RetryLimitReachedError()
            key_hash = self._hash(idempotency_key)
            key = f"idempotency/retry/{pressing_id}/{key_hash}.json"
            if self._store.head(key) is not None:
                return record, False
            self._store.put_bytes(
                key,
                json_bytes({"pressingId": pressing_id, "attemptCount": len(record.attempts)}),
                content_type="application/json",
            )
            return self._save_current(
                record.model_copy(
                    update={"status": PressingStatus.RETRYING_GENERATION, "failure": None}
                )
            ), True

    def create_presigned_asset_access(self, pressing_id: str, *, expires_in: int) -> str:
        record = self.get_by_id(pressing_id)
        if record.final is None:
            raise PressingConflictError("The pressing has no finalized asset")
        return self._store.presign_get(record.final.final_asset.key, expires_in=expires_in)

    def get_object_bytes(self, key: str) -> bytes:
        return self._store.get_bytes(key)

    def object_exists(self, key: str) -> bool:
        return self._store.head(key) is not None

    def list_object_keys(self, prefix: str) -> list[str]:
        return self._store.list_keys(prefix)

    @classmethod
    def object_key(cls, pressing_id: str, suffix: str) -> str:
        return cls._key(pressing_id, suffix)

    def delete(self, pressing_id: str) -> DeletePressingResponse:
        with self._lock:
            record = self.get_by_id(pressing_id)
            prefix = self._prefix(pressing_id) + "/"
            keys = self._store.list_keys(prefix)
            tombstone_key = f"tombstones/{pressing_id}.json"
            tombstone = {
                "pressingId": pressing_id,
                "serialNumber": record.serial_number,
                "deletedAt": utc_now(),
                "deletedObjectCount": len(keys),
            }
            try:
                self._store.delete_keys(keys)
                self._store.put_bytes(
                    tombstone_key,
                    json_bytes(tombstone),
                    content_type="application/json",
                )
            except StorageOperationError:
                raise
            except Exception as exc:
                raise StorageOperationError(
                    category=FailureCategory.STORAGE_PARTIAL_FINALIZATION_FAILED,
                    public_message="Pressing deletion was only partially completed",
                    retryable=True,
                ) from exc
            return DeletePressingResponse(
                pressing_id=pressing_id,
                status=PressingStatus.DELETED,
                tombstone_key=tombstone_key,
            )
