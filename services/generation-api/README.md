# PRESS generation API

FastAPI is the Pydantic and OpenAPI authority for the PRESS sponsor backbone.

## Implemented in PR 2

The service now owns:

* immutable source, fragment, note, attempt, validation, progress, final metadata, and provenance contracts
* structured Genblaze source understanding followed by Genblaze image generation
* a bounded three attempt primary, corrected retry, and optional fallback model policy
* image decoding, dimensions, size, blank output, checksum, durable upload, and retrieval validation
* a private Backblaze B2 adapter through the S3 compatible `genblaze-s3` connector
* durable pressing reconstruction from stable object keys after process replacement
* idempotent create, retry, and finalization operations
* short lived presigned GET access without persisting signed URLs
* service level deletion with an explicit non atomic tombstone workflow
* persistent polling at `GET /v1/pressings/{id}/events`

Fixture mode is deterministic test infrastructure. It is never presented as live Genblaze or B2 evidence.

## Live setup

Install the normal locked development environment first, then add the exact sponsor packages:

```bash
uv sync --project services/generation-api --frozen
uv pip install \
  --python services/generation-api/.venv/bin/python \
  --requirement services/generation-api/requirements-live.txt
```

Configure the server only variables shown in the repository `.env.example`. A live run requires the complete Genblaze and B2 groups. Partial configuration fails clearly.

## Live verification

The protected verifier uses the fictional deterministic fixture as input, but it performs real source understanding, real image generation, real private B2 persistence, one intentionally forced validation retry, and reconstruction in a new Python process:

```bash
FIXTURE_MODE=false \
LIVE_INTEGRATION_TEST=true \
LIVE_FORCE_RETRY_ONCE=true \
uv run --project services/generation-api --no-sync \
python services/generation-api/scripts/verify_live_sponsor_backbone.py
```

The report contains hashes instead of the full human fragment and note, stable B2 object keys instead of signed URLs, and no credentials.

## Execution boundary

Processing is scheduled as an in process FastAPI background task. Progress is persisted and completed pressings survive process replacement. PR 2 does not claim crash safe in flight execution. A production queue and lease based recovery remain later hardening work.
