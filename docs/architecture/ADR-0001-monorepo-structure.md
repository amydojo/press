# ADR 0001: Simple monorepo with explicit service boundaries

- Status: Accepted
- Date: 2026-07-24

## Context

PRESS needs a mobile-first web experience and a Python generation service. Future work will add Genblaze orchestration, Backblaze B2 persistence, source preparation, progress events, and an archive without placing provider credentials or pipeline logic in React components.

## Decision

Use a pnpm workspace with these boundaries:

- `apps/web`: Next.js App Router presentation and server-side API gateway
- `services/generation-api`: FastAPI domain, generation, storage, and lifecycle authority
- `packages/contracts`: generated TypeScript API contracts and a typed local fixture contract
- `packages/config`: shared TypeScript compiler policy
- `fixtures/demo-source`: fictional deterministic source material
- `docs`: architecture and evidence

The web and generation service remain separate processes. Browser code calls a Next.js internal route. That server route calls FastAPI with a server-only base URL and propagates a request ID.

## Future integrations

PR 2 will add Genblaze and Backblaze B2 behind adapters in the generation service. The state machine and pressing record already provide the seam. PR 3 will add source preparation and must implement URL allowlisting, DNS and redirect checks, response size and content limits, and screenshot upload validation.

## Alternatives considered

A single Next.js application with Python subprocesses was rejected because it blurs runtime ownership and deployment constraints. A heavier monorepo orchestrator was rejected because PRESS does not yet need remote caching or a task graph beyond explicit scripts. A shared handwritten TypeScript and Python domain model was rejected because drift would be easy to hide.

## Consequences

The repository has two dependency systems and two runtimes. Local setup is slightly heavier, but credential boundaries, deployment choices, and ownership are clear. Contract generation and CI drift checks are mandatory whenever API models change.
