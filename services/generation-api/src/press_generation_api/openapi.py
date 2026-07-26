from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def build_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["info"]["x-press-contract"] = "pydantic-first"
    schema["info"]["x-press-roadmap-pr"] = "PR 2"
    app.openapi_schema = schema
    return schema
