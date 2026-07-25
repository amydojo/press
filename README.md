# PRESS

**Keep what made you stop.**

PRESS is a mobile-first generative media product that turns an internet encounter into a collectible digital object called a pressing. A bookmark saves the page. A pressing is designed to preserve the exact fragment, the exact personal note, a generated miniature world, and its complete lineage.

## Current implementation status

This repository currently contains PR 1 foundation work only:

- Next.js web application with `/` and truthful `/system` diagnostics
- FastAPI generation service with health, version, and explicit `501` create behavior
- validated pressing domain model and exhaustive lifecycle transition tests
- deterministic OpenAPI export and generated TypeScript API contracts
- fictional local demo source fixture
- local development commands, CI, security boundaries, and architecture documentation

It does **not** yet generate media, persist to Backblaze B2, extract URLs, accept screenshots, render a collectible pressing, maintain an archive, authenticate users, deploy production services, or present final visual design.

## Product promise

The complete flow is:

```text
Landing
→ Capture source
→ Confirm exact fragment
→ Record exact personal note
→ Run a real Genblaze pipeline
→ Store complete lineage in Backblaze B2
→ Reveal a toy-adjacent pressing
→ Tilt and flip it
→ Keep it
→ Refresh
→ Reopen it from the archive
→ Return to the original source
```

## Five-PR roadmap

1. Foundation and typed contracts. Closes Issue #1.
2. Sponsor backbone: Genblaze orchestration, progress, retry and fallback, B2 persistence, and record reconstruction. Closes Issues #3 and #4.
3. Functional slice: source capture, pressing shell, keep, archive, reopen, and source return. Closes Issues #2, #6, and #8.
4. Product character: visual system, chamber choreography, tilt, flip, keep, and reduced motion. Closes Issues #5 and #7.
5. Release proof: accessibility, resilience, performance, deployment, live verification, and submission evidence. Closes Issues #9 and #10.

See the [master roadmap](https://github.com/amydojo/press/issues/11) and [foundation issue](https://github.com/amydojo/press/issues/1).

## Repository architecture

```text
apps/web/                    Next.js presentation and server API gateway
services/generation-api/     FastAPI domain and future generation/storage authority
packages/contracts/          generated TypeScript API types and fixture parser
packages/config/             shared strict TypeScript policy
fixtures/demo-source/        fictional deterministic local source
scripts/                     repository verification scripts
docs/architecture/           ADRs and system context
docs/evidence/               evidence policy and future authentic artifacts
.github/workflows/            CI, contract, E2E, and secret scanning
```

Architecture decisions:

- [ADR 0001: monorepo structure](docs/architecture/ADR-0001-monorepo-structure.md)
- [ADR 0002: API contract source of truth](docs/architecture/ADR-0002-api-contract-source-of-truth.md)
- [System context](docs/architecture/system-context.md)

## Required tools

- Node.js 22.16.0
- pnpm 10.14.0 through Corepack
- Python 3.13.5
- uv 0.10.0 or compatible

## Local setup

```bash
corepack enable
pnpm install --frozen-lockfile
uv sync --project services/generation-api --frozen
cp .env.example .env
pnpm dev
```

`pnpm dev` starts the Next.js web app at `http://localhost:3000` and the FastAPI service at `http://localhost:8000`.

## Canonical commands

```bash
pnpm dev
pnpm dev:web
pnpm dev:api
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm contracts:generate
pnpm contracts:check
pnpm e2e
```

Equivalent Make targets are `make install`, `make dev`, `make test`, and `make check`. The pnpm workflow is canonical; Make is a thin convenience layer, not a competing toolchain.

## Contract generation

Pydantic and FastAPI are the API contract source of truth.

```bash
pnpm contracts:generate
```

This exports `services/generation-api/openapi.json` and generates `packages/contracts/src/generated/api.ts`. Generated TypeScript is never hand edited.

```bash
pnpm contracts:check
```

This regenerates both files and fails if Git detects drift. CI also type checks the generated package.

## Environment variables

`.env.example` contains fake or blank values only.

| Variable | Runtime | PR 1 status |
| --- | --- | --- |
| `PRESS_ENV` | web server and API | used |
| `PRESS_VERSION` | web server and API | used |
| `API_BASE_URL` | Next.js server only | used |
| `NEXT_PUBLIC_APP_URL` | browser-safe public URL | reserved |
| `B2_KEY_ID` | API server only | unused until PR 2 |
| `B2_APPLICATION_KEY` | API server only | unused until PR 2 |
| `B2_BUCKET_NAME` | API server only | unused until PR 2 |
| `B2_ENDPOINT` | API server only | unused until PR 2 |
| `GENBLAZE_PROVIDER_API_KEY` | API server only | unused until PR 2 |
| `DEMO_MODE` | API server | explicit fixture boundary |

Sponsor credentials must never use `NEXT_PUBLIC_*`. Partial B2 configuration fails startup validation. No secret values are logged.

## Deterministic demo fixture disclosure

`fixtures/demo-source` is fictional local material. It exists for deterministic tests and recordings. It is not a live URL fetch and cannot be presented as evidence of source extraction. Live source support arrives later.

## Tests and checks

Web tests cover product identity, environment validation, healthy, unreachable, and malformed diagnostics, plus typed health-response parsing. API tests cover diagnostics, exact anchor preservation, source requirements, note length boundaries, explicit `501` behavior, and every allowed and rejected lifecycle transition. Playwright runs a mobile smoke test against both live local services and fails on browser console errors.

CI also regenerates contracts, scans Git history for secrets, and inspects the built client bundle for server-only variable names and sentinel values.

## Current limitations

The create route validates the real request contract but always returns an explicit structured `501 Not Implemented`. This is intentional. The foundation does not claim live generation, storage, extraction, rendering, archive, authentication, deployment, or final product polish.

## Next PR

PR 2 will implement Issues #3 and #4: real Genblaze orchestration, honest progress events, bounded retry and fallback, Backblaze B2 persistence, immutable run manifests, and complete pressing record reconstruction after restart.

## License

MIT. The hackathon submission requirements call for an accessible GitHub repository and setup instructions but do not mandate a different repository license. Third-party dependencies retain their own licenses.
