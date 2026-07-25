from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from press_generation_api.domain.models import PressingRecord


def _add_model_schema(components: dict[str, Any], model: type[BaseModel]) -> None:
    schema = model.model_json_schema(by_alias=True, ref_template="#/components/schemas/{model}")
    definitions = schema.pop("$defs", {})
    components.update(definitions)
    components[model.__name__] = schema


def build_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    _add_model_schema(components, PressingRecord)
    app.openapi_schema = schema
    return schema
