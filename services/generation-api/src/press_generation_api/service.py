from __future__ import annotations

import hashlib

from fastapi import BackgroundTasks

from press_generation_api.config import Settings
from press_generation_api.domain.models import (
    CreatePressingRequest,
    DeletePressingResponse,
    PressingAssetAccess,
    PressingResponse,
    PressingStatus,
    ProgressResponse,
    RetryRequest,
)
from press_generation_api.pipeline import PressingPipeline
from press_generation_api.repository import PressingRepository


class PressingService:
    def __init__(
        self,
        repository: PressingRepository,
        pipeline: PressingPipeline,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.settings = settings

    def create(
        self,
        request: CreatePressingRequest,
        *,
        idempotency_key: str | None,
        background_tasks: BackgroundTasks,
    ) -> tuple[PressingResponse, bool]:
        record, created = self.repository.create_draft(request, idempotency_key=idempotency_key)
        if created:
            background_tasks.add_task(self.pipeline.run, record.id)
        return PressingResponse(pressing=record), created

    def get(self, pressing_id: str) -> PressingResponse:
        record = self.repository.get_by_id(pressing_id)
        access = None
        if record.status is PressingStatus.READY and record.final is not None:
            expires = self.settings.B2_PRESIGNED_URL_LIFETIME_SECONDS
            access = PressingAssetAccess(
                key=record.final.final_asset.key,
                url=self.repository.create_presigned_asset_access(
                    pressing_id,
                    expires_in=expires,
                ),
                expires_in_seconds=expires,
            )
        return PressingResponse(pressing=record, final_asset_access=access)

    def list(self) -> list[PressingResponse]:
        return [PressingResponse(pressing=record) for record in self.repository.list_pressings()]

    def events(self, pressing_id: str) -> ProgressResponse:
        record = self.repository.get_by_id(pressing_id)
        events = self.repository.get_events(pressing_id)
        return ProgressResponse(
            pressing_id=pressing_id,
            events=events,
            terminal=record.status in {PressingStatus.READY, PressingStatus.FAILED},
        )

    def retry(
        self,
        pressing_id: str,
        request: RetryRequest,
        *,
        idempotency_key: str | None,
        background_tasks: BackgroundTasks,
    ) -> tuple[PressingResponse, bool]:
        resolved = (
            idempotency_key
            or hashlib.sha256(f"{pressing_id}:{request.reason or ''}".encode()).hexdigest()
        )
        record, created = self.repository.begin_retry(pressing_id, idempotency_key=resolved)
        if created:
            background_tasks.add_task(self.pipeline.run, pressing_id)
        return PressingResponse(pressing=record), created

    def delete(self, pressing_id: str) -> DeletePressingResponse:
        return self.repository.delete(pressing_id)
