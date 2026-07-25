# Contributing to PRESS

## Branches

Use scoped names such as `feat/foundation-contracts`, `feat/genblaze-b2`, `fix/health-contract`, or `docs/storage-lineage`.

## Commits

Use concise conventional commits: `feat(api): ...`, `feat(web): ...`, `test: ...`, `ci: ...`, `docs: ...`.

## Required checks

Before requesting review, run `make check` and the deterministic Playwright smoke test with both services running. Do not mark a command as passing unless it was executed against the current commit.

## Contract regeneration

Whenever a Pydantic request, response, enum, or OpenAPI-exposed record changes, run `pnpm contracts:generate`, review the schema and generated TypeScript diff, then run `pnpm contracts:check`.

Never edit `packages/contracts/src/generated/api.ts` by hand.

## PR evidence

Include exact commands and outcomes, current commit SHA, relevant API output, browser evidence, CI links, and security checks. Upload failure traces rather than paraphrasing them away.

## No fake completion

Fixtures must be labeled. A fixture is not proof of live source extraction, Genblaze generation, Backblaze B2 persistence, deployment, or a production product flow.
