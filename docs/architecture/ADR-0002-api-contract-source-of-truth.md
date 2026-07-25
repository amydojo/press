# ADR 0002: FastAPI OpenAPI is the API contract source of truth

- Status: Accepted
- Date: 2026-07-24

## Context

PRESS needs identical request, response, enum, and record shapes in Python and TypeScript. Maintaining unrelated handwritten definitions would allow silent drift at exactly the boundary where generated assets and provenance must remain trustworthy.

## Decision

Pydantic models define API contracts. FastAPI exports a deterministic `openapi.json`. `openapi-typescript` generates `packages/contracts/src/generated/api.ts` from that schema.

Use:

```bash
pnpm contracts:generate
pnpm contracts:check
```

Generated files are checked in and marked as generated. CI regenerates both files and fails when the working tree changes. The contracts package is type checked separately.

## Runtime validation

Generated TypeScript types provide compile-time safety. Boundary responses are also parsed at runtime with narrow Zod schemas before they reach presentation components. Runtime validators are intentionally limited to live boundaries rather than duplicating the complete domain model by hand.

## Tradeoffs and limitations

OpenAPI describes transport contracts, not every internal invariant. Lifecycle transition rules remain executable domain code in Python and are exhaustively tested. Code generation adds a tool step, but the drift check makes contract changes explicit in review.
