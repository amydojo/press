from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol
from urllib.parse import unquote, urlparse

from press_generation_api.config import Settings
from press_generation_api.domain.models import (
    FailureCategory,
    GenerationUnderstanding,
    ImmutableAnchors,
    SourceRecord,
)


@dataclass(frozen=True, slots=True)
class ProviderError(Exception):
    category: FailureCategory
    message: str
    retryable: bool
    provider_code: str | None = None

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class ProviderGenerationResult:
    data: bytes
    mime_type: str
    provider: str
    model: str
    provider_run_id: str
    manifest: dict[str, Any]
    parameters: dict[str, Any]


class GenerationProvider(Protocol):
    name: str

    def understand(
        self,
        *,
        source: SourceRecord,
        anchors: ImmutableAnchors,
    ) -> GenerationUnderstanding: ...

    def generate(
        self,
        *,
        brief: str,
        model: str,
        run_id: str,
        parent_run_id: str | None,
    ) -> ProviderGenerationResult: ...


def _map_provider_exception(exc: Exception) -> ProviderError:
    text = str(exc).lower()
    code = str(getattr(exc, "error_code", "")) or None
    combined = f"{type(exc).__name__.lower()} {text} {code or ''}"
    if any(token in combined for token in ("authentication", "invalid_api_key", "401")):
        return ProviderError(
            FailureCategory.PROVIDER_AUTHENTICATION_FAILED,
            "The generation provider rejected its credentials",
            False,
            code,
        )
    if any(token in combined for token in ("permission", "authorization", "403")):
        return ProviderError(
            FailureCategory.PROVIDER_AUTHORIZATION_FAILED,
            "The generation provider denied this operation",
            False,
            code,
        )
    if any(token in combined for token in ("rate", "429", "throttl")):
        return ProviderError(
            FailureCategory.PROVIDER_RATE_LIMITED,
            "The generation provider is rate limited",
            True,
            code,
        )
    if any(token in combined for token in ("timeout", "timed out")):
        return ProviderError(
            FailureCategory.PROVIDER_TIMED_OUT,
            "The generation provider timed out",
            True,
            code,
        )
    return ProviderError(
        FailureCategory.UNKNOWN_INTERNAL_ERROR,
        "The generation provider failed",
        True,
        code,
    )


class GenblazeOpenAIProvider:
    """Live Genblaze adapter for structured understanding and image generation."""

    name = "openai"

    def __init__(self, settings: Settings) -> None:
        if settings.GENBLAZE_PROVIDER_API_KEY is None:
            raise ValueError("GENBLAZE_PROVIDER_API_KEY is required for live generation")
        self._api_key = settings.GENBLAZE_PROVIDER_API_KEY.get_secret_value()
        self._understanding_model = settings.GENBLAZE_UNDERSTANDING_MODEL
        self._timeout = settings.GENERATION_TIMEOUT_SECONDS
        self._size = settings.GENBLAZE_IMAGE_SIZE
        self._quality = settings.GENBLAZE_IMAGE_QUALITY

    @staticmethod
    def _understanding_prompt(source: SourceRecord, anchors: ImmutableAnchors) -> str:
        payload = {
            "sourceType": source.source_type.value,
            "sourceDomain": source.domain,
            "sourceTitle": source.title,
            "selectedFragment": anchors.selected_fragment,
            "personalNote": anchors.personal_note,
        }
        return (
            "Return one JSON object only. Analyze this internet encounter as creative signals, "
            "not as factual authority. Use exactly these keys and allowed values: "
            "content_type(article|image|post|music|experimental|other), motif(string), "
            "palette(array of #RRGGBB), atmosphere(array of strings), "
            "density(quiet|balanced|dense), archetype(scene|relic|signal), "
            "generation_brief(string). Do not rewrite or quote the personal note in the brief. "
            "Do not instruct the image model to render text or application UI. Input: "
            + json.dumps(payload, ensure_ascii=False)
        )

    def understand(
        self,
        *,
        source: SourceRecord,
        anchors: ImmutableAnchors,
    ) -> GenerationUnderstanding:
        try:
            from genblaze_openai import chat  # type: ignore[import-not-found]

            response = chat(
                model=self._understanding_model,
                prompt=self._understanding_prompt(source, anchors),
                system=(
                    "You are PRESS's restrained art director. Output strict JSON only. "
                    "Never mutate human-confirmed text."
                ),
                api_key=self._api_key,
                temperature=0.2,
                max_tokens=900,
                response_format={"type": "json_object"},
                timeout=self._timeout,
            )
            text = str(getattr(response, "text", response))
            return GenerationUnderstanding.model_validate_json(text)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderError(
                FailureCategory.MODEL_OUTPUT_MALFORMED,
                "Structured source understanding was malformed",
                True,
            ) from exc
        except Exception as exc:
            raise _map_provider_exception(exc) from exc

    @staticmethod
    def _asset_bytes(asset_url: str) -> bytes:
        parsed = urlparse(asset_url)
        if parsed.scheme != "file":
            raise ProviderError(
                FailureCategory.ASSET_VALIDATION_FAILED,
                "Genblaze did not materialize a durable local image asset",
                True,
            )
        return Path(unquote(parsed.path)).read_bytes()

    def generate(
        self,
        *,
        brief: str,
        model: str,
        run_id: str,
        parent_run_id: str | None,
    ) -> ProviderGenerationResult:
        try:
            from genblaze_core import Modality, Pipeline  # type: ignore[import-not-found]
            from genblaze_openai import DalleProvider  # type: ignore[import-not-found]

            with TemporaryDirectory(prefix="press-genblaze-") as output_dir:
                provider = DalleProvider(
                    api_key=self._api_key,
                    http_timeout=self._timeout,
                    output_dir=output_dir,
                )
                result = (
                    Pipeline(f"press-{run_id}", project_id="press")
                    .step(
                        provider,
                        model=model,
                        prompt=brief,
                        modality=Modality.IMAGE,
                        size=self._size,
                        quality=self._quality,
                        n=1,
                    )
                    .run(timeout=self._timeout, max_retries=0)
                )
                if hasattr(result, "run") and hasattr(result, "manifest"):
                    run = result.run
                    manifest = result.manifest
                else:
                    run, manifest = result
                step = run.steps[0]
                if not step.assets:
                    raise ProviderError(
                        FailureCategory.ASSET_VALIDATION_FAILED,
                        "Genblaze returned no image asset",
                        True,
                    )
                asset = step.assets[0]
                data = self._asset_bytes(str(asset.url))
                manifest_payload = manifest.model_dump(mode="json", by_alias=True)
                parameters = {
                    "size": self._size,
                    "quality": self._quality,
                    "n": 1,
                    "pressRunId": run_id,
                    "parentRunId": parent_run_id,
                }
                return ProviderGenerationResult(
                    data=data,
                    mime_type=str(getattr(asset, "mime_type", None) or "image/png"),
                    provider="openai-dalle",
                    model=model,
                    provider_run_id=str(run.run_id),
                    manifest=manifest_payload,
                    parameters=parameters,
                )
        except ProviderError:
            raise
        except Exception as exc:
            raise _map_provider_exception(exc) from exc


class FixtureGenerationProvider:
    """Clearly labeled deterministic provider for tests and local fixture mode only."""

    name = "fixture"

    def understand(
        self,
        *,
        source: SourceRecord,
        anchors: ImmutableAnchors,
    ) -> GenerationUnderstanding:
        del source, anchors
        return GenerationUnderstanding(
            content_type="article",
            motif="a small paper fragment held between translucent geological layers",
            palette=["#EDE7DC", "#62706A", "#C1735C"],
            atmosphere=["quiet", "archival", "tactile"],
            density="balanced",
            archetype="relic",
            generation_brief=(
                "A restrained miniature relic that feels pressed from an internet encounter, "
                "with one clear object and no visible lettering."
            ),
        )

    def generate(
        self,
        *,
        brief: str,
        model: str,
        run_id: str,
        parent_run_id: str | None,
    ) -> ProviderGenerationResult:
        from press_generation_api.media import create_fixture_png

        del brief
        data = create_fixture_png()
        manifest = {
            "fixture": True,
            "provider": "fixture",
            "model": model,
            "runId": run_id,
            "parentRunId": parent_run_id,
        }
        return ProviderGenerationResult(
            data=data,
            mime_type="image/png",
            provider="fixture",
            model=model,
            provider_run_id=f"fixture-{run_id}",
            manifest=manifest,
            parameters={"size": "1024x1024", "fixture": True},
        )
