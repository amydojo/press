from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from press_generation_api.api.models import (
    HealthResponse,
    NotImplementedDetail,
    NotImplementedResponse,
    VersionResponse,
)
from press_generation_api.config import get_settings
from press_generation_api.domain.models import CreatePressingRequest
from press_generation_api.logging import configure_logging, log_event
from press_generation_api.openapi import build_openapi

settings = get_settings()
logger = configure_logging()


class PressGenerationApi(FastAPI):
    def openapi(self) -> dict[str, Any]:
        return build_openapi(self)


app = PressGenerationApi(
    title="PRESS Generation API",
    version=settings.PRESS_VERSION,
    description=(
        "Typed service foundation for PRESS. Genblaze generation and Backblaze B2 "
        "persistence are explicitly deferred to PR 2."
    ),
)


@app.middleware("http")
async def request_context(request: Request, call_next: Any) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
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
                "version": settings.PRESS_VERSION,
                "environment": settings.PRESS_ENV,
                "request_id": request_id,
                "route": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )


@app.get("/healthz", response_model=HealthResponse, tags=["system"])
def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="press-generation-api",
        version=settings.PRESS_VERSION,
        environment=settings.PRESS_ENV,
        timestamp=datetime.now(UTC),
    )


@app.get("/version", response_model=VersionResponse, tags=["system"])
def version() -> VersionResponse:
    return VersionResponse(
        version=settings.PRESS_VERSION,
        commit_sha=settings.commit_sha,
        build_timestamp=settings.BUILD_TIMESTAMP,
    )


@app.post(
    "/v1/pressings",
    response_model=NotImplementedResponse,
    responses={501: {"model": NotImplementedResponse}},
    tags=["pressings"],
)
def create_pressing(_request: CreatePressingRequest) -> JSONResponse:
    body = NotImplementedResponse(
        detail=NotImplementedDetail(
            code="generation_not_implemented",
            message=(
                "PRESS validates the creation contract, but live generation and persistence "
                "are not implemented in the foundation PR."
            ),
            arrives_in="PR 2",
        )
    )
    return JSONResponse(status_code=501, content=body.model_dump(by_alias=True, mode="json"))
