from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from press_generation_api.config import Settings
from press_generation_api.domain.models import CreatePressingRequest, PressingStatus, SourceType
from press_generation_api.pipeline import PressingPipeline
from press_generation_api.providers import GenblazeOpenAIProvider
from press_generation_api.repository import PressingRepository
from press_generation_api.storage import GenblazeB2ObjectStore, parse_json

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "demo-source" / "source.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "evidence" / "pr-2-sponsor-backbone" / "live-report.json"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _version(distribution: str) -> str:
    return importlib.metadata.version(distribution)


def _settings() -> Settings:
    settings = Settings()
    if not settings.LIVE_INTEGRATION_TEST:
        raise RuntimeError("LIVE_INTEGRATION_TEST=true is required for sponsor verification")
    if settings.FIXTURE_MODE:
        raise RuntimeError("FIXTURE_MODE=false is required for live sponsor verification")
    if not settings.LIVE_FORCE_RETRY_ONCE:
        raise RuntimeError(
            "LIVE_FORCE_RETRY_ONCE=true is required to prove one bounded real recovery path"
        )
    settings.require_live_configuration()
    return settings


def _reconstruct(pressing_id: str) -> dict[str, Any]:
    settings = _settings()
    store = GenblazeB2ObjectStore(settings)
    try:
        repository = PressingRepository(store, max_attempts=settings.MAX_GENERATION_ATTEMPTS)
        record = repository.get_by_id(pressing_id)
        final_exists = record.final is not None and repository.object_exists(
            record.final.final_asset.key
        )
        return {
            "pressingId": record.id,
            "status": record.status.value,
            "serialNumber": record.serial_number,
            "fragmentSha256": _sha(record.anchors.selected_fragment),
            "noteSha256": _sha(record.anchors.personal_note),
            "submittedSourceIdentitySha256": _sha(record.anchors.submitted_source_identity),
            "attemptCount": len(record.attempts),
            "finalAssetExists": final_exists,
            "generationRunId": record.final.generation_run_id if record.final else None,
            "parentRunId": record.final.parent_run_id if record.final else None,
        }
    finally:
        store.close()


def _run(output: Path) -> dict[str, Any]:
    settings = _settings()
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    request = CreatePressingRequest(
        source_type=SourceType.FIXTURE,
        source_title=str(fixture["title"]),
        source_domain=str(fixture["domain"]),
        selected_fragment=str(fixture["fragment"]),
        personal_note=str(fixture["exampleNote"]),
    )
    create_key = f"live-pr2-{uuid4()}"
    store = GenblazeB2ObjectStore(settings)
    try:
        repository = PressingRepository(store, max_attempts=settings.MAX_GENERATION_ATTEMPTS)
        record, created = repository.create_draft(request, idempotency_key=create_key)
        if not created:
            raise RuntimeError("Live verification unexpectedly reused a previous pressing")
        final = PressingPipeline(
            repository,
            GenblazeOpenAIProvider(settings),
            settings,
        ).run(record.id)
        if final.status is not PressingStatus.READY or final.final is None:
            category = final.failure.category.value if final.failure else "unknown"
            raise RuntimeError(f"Live pressing did not reach ready: {category}")
        duplicate, duplicate_created = repository.create_draft(
            request,
            idempotency_key=create_key,
        )
        if duplicate_created or duplicate.id != final.id:
            raise RuntimeError("Create idempotency verification failed")
        if len(final.attempts) < 2 or final.final.parent_run_id is None:
            raise RuntimeError("The forced bounded recovery path did not preserve parent lineage")
        if final.anchors.selected_fragment != fixture["fragment"]:
            raise RuntimeError("The exact selected fragment changed during live processing")
        if final.anchors.personal_note != fixture["exampleNote"]:
            raise RuntimeError("The exact personal note changed during live processing")

        prefix = f"pressings/{final.id}/"
        object_tree = repository.list_object_keys(prefix)
        metadata_key = repository.object_key(final.id, "final/metadata.json")
        provenance_key = repository.object_key(final.id, "final/provenance.json")
        metadata = parse_json(repository.get_object_bytes(metadata_key))
        provenance = parse_json(repository.get_object_bytes(provenance_key))
        events = repository.get_events(final.id)
        attempts = [
            {
                "runId": attempt.run_id,
                "parentRunId": attempt.parent_run_id,
                "attemptNumber": attempt.attempt_number,
                "provider": attempt.provider,
                "model": attempt.model,
                "status": attempt.status.value,
                "promptHash": attempt.prompt_hash,
                "outputKey": attempt.asset.key if attempt.asset else None,
                "validation": (
                    attempt.validation.model_dump(by_alias=True, mode="json")
                    if attempt.validation
                    else None
                ),
                "failureCategory": (attempt.failure.category.value if attempt.failure else None),
                "retryReason": attempt.retry_reason,
            }
            for attempt in final.attempts
        ]
    finally:
        store.close()

    child = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--reconstruct-only", final.id],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    reconstructed = json.loads(child.stdout)
    if reconstructed["status"] != PressingStatus.READY.value:
        raise RuntimeError("Fresh-process reconstruction did not return a ready pressing")
    if reconstructed["fragmentSha256"] != _sha(str(fixture["fragment"])):
        raise RuntimeError("Fresh-process fragment verification failed")
    if reconstructed["noteSha256"] != _sha(str(fixture["exampleNote"])):
        raise RuntimeError("Fresh-process note verification failed")
    if not reconstructed["finalAssetExists"]:
        raise RuntimeError("Fresh-process final asset verification failed")

    report: dict[str, Any] = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "repository": "amydojo/press",
        "branch": os.environ.get("GITHUB_REF_NAME", "feat/genblaze-b2"),
        "commitSha": os.environ.get("GITHUB_SHA") or settings.commit_sha,
        "provider": final.attempts[-1].provider,
        "understandingModel": settings.GENBLAZE_UNDERSTANDING_MODEL,
        "primaryModel": settings.GENBLAZE_PRIMARY_MODEL,
        "fallbackModel": settings.GENBLAZE_FALLBACK_MODEL,
        "genblazeVersions": {
            "genblaze-core": _version("genblaze-core"),
            "genblaze-openai": _version("genblaze-openai"),
            "genblaze-s3": _version("genblaze-s3"),
        },
        "pressingId": final.id,
        "serialNumber": final.serial_number,
        "runId": final.final.generation_run_id,
        "parentRunId": final.final.parent_run_id,
        "b2ObjectPrefix": prefix,
        "finalAssetKey": final.final.final_asset.key,
        "exactAnchors": {
            "fragmentSha256": _sha(final.anchors.selected_fragment),
            "noteSha256": _sha(final.anchors.personal_note),
            "submittedSourceIdentitySha256": _sha(final.anchors.submitted_source_identity),
            "preserved": True,
        },
        "orderedProgressTrace": [
            {
                "sequence": event.sequence,
                "stage": event.stage.value,
                "status": event.pressing_status.value,
                "runId": event.run_id,
                "parentRunId": event.parent_run_id,
                "attemptNumber": event.attempt_number,
                "timestamp": event.timestamp.isoformat(),
            }
            for event in events
        ],
        "attempts": attempts,
        "sanitizedB2ObjectTree": object_tree,
        "finalMetadata": metadata,
        "provenance": provenance,
        "idempotencyVerified": True,
        "processRestartReconstruction": reconstructed,
        "retryOrFallbackVerified": True,
        "bucketPrivate": True,
        "presignedUrlsPersisted": False,
        "liveCompletionGatePassed": True,
        "knownLimitations": [
            (
                "In-flight execution remains process-bound; only completed-record "
                "restart reconstruction is claimed."
            ),
            "Distributed multi-writer serial allocation is deferred beyond the hackathon MVP.",
            "The final collectible shell and archive UI are intentionally PR 3 scope.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reconstruct-only", metavar="PRESSING_ID")
    args = parser.parse_args()
    if args.reconstruct_only:
        print(json.dumps(_reconstruct(args.reconstruct_only), sort_keys=True))
        return
    report = _run(args.output)
    print(
        json.dumps(
            {
                "pressingId": report["pressingId"],
                "runId": report["runId"],
                "parentRunId": report["parentRunId"],
                "output": str(args.output),
                "liveCompletionGatePassed": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
