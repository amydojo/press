from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse

from press_generation_api.api.models import ErrorDetail, ErrorResponse, HealthResponse, VersionResponse
from press_generation_api.config import Settings, get_settings
from press_generation_api.domain.models import (
    CreatePressingRequest,
    DeletePressingResponse,
    PressingResponse,
    ProgressResponse,
    RetryRequest,
)
from press_generation_api.errors import LiveConfigurationError, PressError
from press_generation_api.logging import configure_logging, log_event
from press_generation_api.openapi import build_openapi
from press_generation_api.pipeline import PressingPipeline
from press_generation_api.providers import (
    FixtureGenerationProvider,
    GenblazeOpenAIProvider,
    GenerationProvider,
)
from press_generation_api.repository import PressingRepository
from press_generation_api.service import PressingService
from press_generation_api.storage import GenblazeB2ObjectStore, InMemoryObjectStore, ObjectStore

logger = configure_logging()


class PressGenerationApi(FastAPI):
    def openapi(self) -> dict[str, Any]:
        return build_openapi(self)


def build_service(
    settings: Settings,
    *,
    store: ObjectStore | None = None,
    provider: GenerationProvider | None = None,
) -> PressingService:
    if settings.PRESS_ENV in {"preview", "production"}:
        try:
            settings.require_live_configuration()
        except ValueError as exc:
            raise LiveConfigurationError(str(exc)) from exc
    resolved_store = store
    if resolved_store is None:
        resolved_store = (
            GenblazeB2ObjectStore(settings)
            if settings.b2_configured
            else InMemoryObjectStore(
                max_bytes=max(settings.MAX_SOURCE_BYTES, settings.MAX_GENERATED_ASSET_BYTES)
            )
        )
    resolved_provider = provider
    if resolved_provider is None:
        if settings.live_provider_configured:
            resolved_provider = GenblazeOpenAIProvider(settings)
        elif settings.FIXTURE_MODE and settings.PRESS_ENV in {"development", "test"}:
            resolved_provider = FixtureGenerationProvider()
        else:
            raise LiveConfigurationError(
                "GENBLAZE_PROVIDER_API_KEY is required when fixture mode is disabled"
            )
    repository = PressingRepository(
        resolved_store,
        max_attempts=settings.MAX_GENERATION_ATTEMPTS,
    )
    pipeline = PressingPipeline(repository, resolved_provider, settings)
    return PressingService(repository, pipeline, settings)


def create_app(
    settings: Settings | None = None,
    *,
    store: ObjectStore | None = None,
    provider: GenerationProvider | None = None,
) -> PressGenerationApi:
    runtime_settings = settings or get_settings()
    service = build_service(runtime_settings, store=store, provider=provider)
    api = PressGenerationApi(
        title="PRESS Generation API",
        version=runtime_settings.PRESS_VERSION,
        description=(
            "PR 2 sponsor backbone for PRESS: validated Genblaze orchestration, bounded recovery, "
            "private Backblaze B2 persistence, durable reconstruction, and honest progress."
        ),
    )
    api.state.service = service
    api.state.settings = runtime_settings

    @api.exception_handler(PressError)
    async def handle_press_error(request: Request, exc: PressError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        body = ErrorResponse(
            detail=ErrorDetail(
                code=exc.category,
                message=exc.public_message,
                retryable=exc.retryable,
                request_id=request_id,
            )
        )
        return JSONResponse(
            status_code=int(exc.status_code),
            content=body.model_dump(by_alias=True, mode="json"),
        )

    @api.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            duration_ms = round((perf_counter() - started) * 1000, 2)
            log_event(
                logger,
                {
                    "service": "press-generation-api",
                    "version": runtime_settings.PRESS_VERSION,
                    "environment": runtime_settings.PRESS_ENV,
                    "request_id": request_id,
                    "route": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )

    @api.get("/healthz", response_model=HealthResponse, tags=["system"])
    def healthz() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="press-generation-api",
            version=runtime_settings.PRESS_VERSION,
            environment=runtime_settings.PRESS_ENV,
            timestamp=datetime.now(UTC),
            live_provider_configured=runtime_settings.live_provider_configured,
            durable_storage_configured=runtime_settings.b2_configured,
        )

    @api.get("/version", response_model=VersionResponse, tags=["system"])
    def version() -> VersionResponse:
        return VersionResponse(
            version=runtime_settings.PRESS_VERSION,
            commit_sha=runtime_settings.commit_sha,
            build_timestamp=runtime_settings.BUILD_TIMESTAMP,
        )

    @api.post(
        "/v1/pressings",
        response_model=PressingResponse,
        status_code=202,
        responses={200: {"model": PressingResponse}, 409: {"model": ErrorResponse}},
        tags=["pressings"],
    )
    def create_pressing(
        request: CreatePressingRequest,
        response: Response,
        background_tasks: BackgroundTasks,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> PressingResponse:
        result, created = service.create(
            request,
            idempotency_key=idempotency_key,
            background_tasks=background_tasks,
        )
        response.status_code = 202 if created else 200
        return result

    @api.get(
        "/v1/pressings",
        response_model=list[PressingResponse],
        tags=["pressings"],
    )
    def list_pressings() -> list[PressingResponse]:
        return service.list()

    @api.get(
        "/v1/pressings/{pressing_id}",
        response_model=PressingResponse,
        responses={404: {"model": ErrorResponse}},
        tags=["pressings"],
    )
    def get_pressing(pressing_id: str) -> PressingResponse:
        return service.get(pressing_id)

    @api.get(
        "/v1/pressings/{pressing_id}/events",
        response_model=ProgressResponse,
        responses={404: {"model": ErrorResponse}},
        tags=["pressings"],
    )
    def get_pressing_events(pressing_id: str) -> ProgressResponse:
        return service.events(pressing_id)

    @api.post(
        "/v1/pressings/{pressing_id}/retry",
        response_model=PressingResponse,
        status_code=202,
        responses={200: {"model": PressingResponse}, 409: {"model": ErrorResponse}},
        tags=["pressings"],
    )
    def retry_pressing(
        pressing_id: str,
        request: RetryRequest,
        response: Response,
        background_tasks: BackgroundTasks,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> PressingResponse:
        result, created = service.retry(
            pressing_id,
            request,
            idempotency_key=idempotency_key,
            background_tasks=background_tasks,
        )
        response.status_code = 202 if created else 200
        return result

    @api.delete(
        "/v1/pressings/{pressing_id}",
        response_model=DeletePressingResponse,
        responses={404: {"model": ErrorResponse}},
        tags=["pressings"],
    )
    def delete_pressing(pressing_id: str) -> DeletePressingResponse:
        return service.delete(pressing_id)

    return api


app = create_app()
