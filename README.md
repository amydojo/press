# PRESS

**Keep what made you stop.**

PRESS turns an internet encounter into a collectible digital object called a pressing. A bookmark saves the page. A pressing preserves the exact selected fragment, the exact personal note, a generated miniature world, a stable serial, and the lineage needed to prove how it was made.

## Current implementation status

PR 2 implements the backend engine and durable memory defined by Issues #3 and #4:

* FastAPI remains the Pydantic and OpenAPI contract authority
* one deterministic fictional fixture can pass through structured source understanding and image generation
* the live adapter uses Genblaze behind a provider boundary
* generated assets are decoded, measured, checked for trivial blank output, uploaded, retrieved, and checksum verified
* retry is bounded to three attempts with primary, corrected retry, and optional fallback model behavior
* source records, immutable anchors, each attempt, validation, events, final metadata, provenance, and assets use stable private Backblaze B2 object keys
* create, retry, and finalization are idempotent
* completed pressings reconstruct after API process replacement without local memory
* final assets are returned through short lived private access URLs that are never stored
* deletion removes the pressing prefix and writes a separate tombstone, with non atomic behavior documented

The repository still does not implement live URL extraction, screenshot upload, the collectible shell, archive UI, authentication, sharing, final motion, or production release. Those remain PR 3 through PR 5 scope.

## Architecture

```text
apps/web/                    Next.js presentation and diagnostics
services/generation-api/     FastAPI domain, orchestration, storage, and repository authority
packages/contracts/          OpenAPI generated TypeScript contracts
fixtures/demo-source/        fictional deterministic input fixture
scripts/                     security and repository checks
docs/architecture/           ADRs and system context
docs/evidence/               evidence policy and sanitized PR artifacts
.github/workflows/           CI plus protected live sponsor verification
```

Architecture decisions:

* [ADR 0001: monorepo structure](docs/architecture/ADR-0001-monorepo-structure.md)
* [ADR 0002: API contract source of truth](docs/architecture/ADR-0002-api-contract-source-of-truth.md)
* [ADR 0003: sponsor backbone execution model](docs/architecture/ADR-0003-sponsor-backbone.md)
* [System context](docs/architecture/system-context.md)

## Runtime flow

```text
Normalize source
→ persist immutable anchors
→ understand encounter with a strict schema
→ select scene, relic, or signal
→ build a privacy safe generation brief
→ generate an internal world through Genblaze
→ validate bytes, MIME, dimensions, blank output, and metadata
→ upload and retrieve from private B2
→ retry or fall back when bounded policy allows
→ persist attempt lineage, final metadata, provenance, and progress
→ return ready with temporary private asset access
```

Progress is available through persistent polling. The required stages are preparing source, understanding fragment, creating miniature world, rendering pressing, saving pressing, retrying generation, ready, and failed.

## Execution model

FastAPI schedules processing as an in process background task. Durable checkpoints and events survive process replacement. Completed pressing reconstruction is verified from B2 alone.

This PR does not claim crash safe in flight work. An external queue, lease ownership, and distributed serial allocator remain later production hardening.

## Required tools

* Node.js 22.16.0
* pnpm 10.14.0 through Corepack
* Python 3.13.5
* uv 0.10.0 or compatible

## Local fixture setup

```bash
corepack enable
pnpm install --frozen-lockfile
uv sync --project services/generation-api --frozen
cp .env.example .env
pnpm dev
```

Fixture mode is enabled by default for development and tests. It creates deterministic PNG bytes and an explicitly labeled fixture manifest. It is not proof of live generation or live storage.

## Live sponsor setup

Install the exact verified sponsor package set after the normal locked environment:

```bash
uv pip install \
  --python services/generation-api/.venv/bin/python \
  --requirement services/generation-api/requirements-live.txt
```

The live package boundary is pinned to:

* `genblaze-core==0.3.7`
* `genblaze-openai==0.3.3`
* `genblaze-s3==0.3.6`

Configure a least privilege Backblaze application key limited to the private PRESS bucket. Do not use a master application key. Do not make the bucket public.

## Environment variables

`.env.example` contains blank or fake values only.

| Variable | Boundary | Purpose |
| --- | --- | --- |
| `PRESS_ENV` | server | development, test, preview, or production |
| `PRESS_VERSION` | server and diagnostics | runtime version |
| `API_BASE_URL` | Next.js server | FastAPI base URL |
| `NEXT_PUBLIC_APP_URL` | browser safe | public web origin only |
| `GENBLAZE_PROVIDER` | API server | provider selector, currently `openai` |
| `GENBLAZE_PROVIDER_API_KEY` | API server secret | provider credential |
| `GENBLAZE_UNDERSTANDING_MODEL` | API server | structured understanding model |
| `GENBLAZE_PRIMARY_MODEL` | API server | primary image model |
| `GENBLAZE_FALLBACK_MODEL` | API server | optional final fallback model |
| `GENERATION_TIMEOUT_SECONDS` | API server | bounded provider timeout |
| `MAX_GENERATION_ATTEMPTS` | API server | hard maximum, one through three |
| `B2_KEY_ID` | API server secret | application key ID |
| `B2_APPLICATION_KEY` | API server secret | application key secret |
| `B2_BUCKET_NAME` | API server | private bucket |
| `B2_ENDPOINT` | API server | HTTPS S3 compatible endpoint |
| `B2_REGION` | API server | B2 region |
| `B2_PRESIGNED_URL_LIFETIME_SECONDS` | API server | short lived private access |
| `FIXTURE_MODE` | API server | deterministic non live provider boundary |
| `LIVE_INTEGRATION_TEST` | protected verification | explicit live test opt in |
| `LIVE_FORCE_RETRY_ONCE` | protected verification | one intentional real recovery probe |

`DEMO_MODE` remains accepted as a compatibility alias for `FIXTURE_MODE`. Sponsor credentials must never use a `NEXT_PUBLIC_` prefix.

## API

* `POST /v1/pressings` creates an idempotent pressing and schedules processing
* `GET /v1/pressings` lists durable records
* `GET /v1/pressings/{id}` reconstructs a durable record and derives temporary asset access when ready
* `GET /v1/pressings/{id}/events` returns ordered persisted progress
* `POST /v1/pressings/{id}/retry` creates one bounded retry request
* `DELETE /v1/pressings/{id}` deletes the pressing prefix and records a tombstone
* `GET /healthz` and `GET /version` preserve system diagnostics

Errors use stable typed bodies for invalid input, conflict, retry limit, provider authentication, authorization, rate limit, timeout, malformed output, asset validation, storage failures, and internal failures. Stack traces and raw SDK responses are not public API data.

## B2 object tree

```text
pressings/{pressing-id}/
  source/
    source.json
    fragment.json
    note.json
  generations/{run-id}/
    understanding.json
    asset.png | asset.jpg | asset.webp
    manifest.json
    evaluation.json
  events/
    progress.jsonl
  state/
    current.json
  final/
    internal-world.png
    metadata.json
    provenance.json
```

Idempotency records, the serial counter, and deletion tombstones live outside the pressing prefix. Signed URLs never appear in canonical records.

## Retry policy

1. primary provider and model
2. corrected brief or transient retry on the primary model
3. configured fallback model when present, otherwise a final corrected primary attempt

Every attempt gets a unique run ID and directory. The pressing ID, serial, selected fragment, personal note, submitted source identity, and prior attempts never change.

## Verification

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm contracts:check
pnpm e2e
```

The normal CI path is secret free. It runs web checks, Python formatting, lint, strict type checking, API tests, OpenAPI drift, generated TypeScript type checking, Playwright smoke, client bundle credential inspection, and gitleaks.

The manual `Live sponsor verification` workflow is the only workflow that consumes sponsor secrets. It uses the deterministic fixture as input, performs live Genblaze understanding and generation, forces one bounded validation retry, persists complete lineage to private B2, and reconstructs the pressing in a new Python process. Its sanitized JSON report is uploaded as a workflow artifact.

## Security and privacy

* provider and B2 credentials are server only
* the bucket remains private and is never listed publicly
* object keys are server constructed and reject traversal, absolute paths, unsafe segments, unsupported MIME types, and oversized payloads
* routine logs omit full selected fragments, full personal notes, source assets, API keys, authorization headers, and signed URLs
* stable object keys are canonical; signed URLs are temporary derived responses
* source fetching is not implemented in PR 2, so no unrestricted URL fetch exists
* client bundle scanning uses sentinel secrets

## Known limitations

* in flight work is process bound and not crash safe
* serial allocation is safe for this single service process and persisted across restarts, but not yet a distributed compare and swap allocator
* B2 prefix deletion is not atomic
* the generation API has not been claimed as a production Vercel deployment
* final shell rendering, capture UI, archive UI, and browser product flow remain PR 3

## Live completion gate

Code, non secret tests, contracts, documentation, and the protected verifier can be completed without credentials. The PR remains draft until a protected live run proves a real provider asset, real private B2 lineage, one bounded recovery route, and process restart reconstruction. Missing credentials are never pasted into chat, source, logs, or a pull request.

## Next PR

PR 3 is the functional product slice and closes Issues #2, #6, and #8. It adds source capture, the pressing renderer, durable keep, archive, reopen, and source return. PR 3 does not begin on this branch.

## License

MIT. Third party dependencies retain their own licenses.
