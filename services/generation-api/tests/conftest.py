from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from press_generation_api.config import Settings
from press_generation_api.domain.models import (
    GenerationUnderstanding,
    ImmutableAnchors,
    SourceRecord,
)
from press_generation_api.media import create_fixture_png
from press_generation_api.providers import (
    GenerationProvider,
    ProviderError,
    ProviderGenerationResult,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(PRESS_ENV="test", FIXTURE_MODE=True, MAX_GENERATION_ATTEMPTS=3)


@pytest.fixture
def understanding() -> GenerationUnderstanding:
    return GenerationUnderstanding(
        content_type="article",
        motif="a folded paper relic",
        palette=["#F0E9DD", "#4B5550", "#C66E52"],
        atmosphere=["quiet", "tactile"],
        density="balanced",
        archetype="relic",
        generation_brief="A single tactile relic held in a restrained miniature world.",
    )


@dataclass
class ScriptedProvider(GenerationProvider):
    understanding: GenerationUnderstanding
    understand_outcomes: list[GenerationUnderstanding | Exception] = field(default_factory=list)
    generate_outcomes: list[bytes | Exception] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    name: str = "scripted"

    def understand(
        self,
        *,
        source: SourceRecord,
        anchors: ImmutableAnchors,
    ) -> GenerationUnderstanding:
        del source, anchors
        if self.understand_outcomes:
            outcome = self.understand_outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return self.understanding

    def generate(
        self,
        *,
        brief: str,
        model: str,
        run_id: str,
        parent_run_id: str | None,
    ) -> ProviderGenerationResult:
        del brief
        self.models.append(model)
        outcome: bytes | Exception = (
            self.generate_outcomes.pop(0) if self.generate_outcomes else create_fixture_png()
        )
        if isinstance(outcome, Exception):
            raise outcome
        return ProviderGenerationResult(
            data=outcome,
            mime_type="image/png",
            provider=self.name,
            model=model,
            provider_run_id=f"provider-{run_id}",
            manifest={"runId": run_id, "parentRunId": parent_run_id, "provider": self.name},
            parameters={"size": "1024x1024"},
        )


@pytest.fixture
def scripted_provider(understanding: GenerationUnderstanding) -> ScriptedProvider:
    return ScriptedProvider(understanding=understanding)


@pytest.fixture
def provider_failure_timeout() -> ProviderError:
    from press_generation_api.domain.models import FailureCategory

    return ProviderError(
        FailureCategory.PROVIDER_TIMED_OUT,
        "provider timed out",
        True,
        "timeout",
    )


@pytest.fixture
def client() -> TestClient:
    from press_generation_api.main import create_app

    return TestClient(create_app(Settings(PRESS_ENV="test", FIXTURE_MODE=True)))
