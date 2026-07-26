# ADR 0003 · Sponsor backbone execution model

- Status: accepted for PR 2
- Date: 2026-07-26
- Scope: Issues #3 and #4

## Context

PRESS must prove one real Genblaze image generation and complete Backblaze B2 reconstruction without pretending that an in-process request handler is a crash-safe job system. PR 1 established FastAPI as the Pydantic and OpenAPI authority.

## Decision

### Genblaze boundary

The API owns a `GenerationProvider` port. The live adapter uses the released Genblaze packages and OpenAI connector. Structured source understanding is requested through the connector and validated by PRESS before it can influence image generation. The image stage runs through a Genblaze `Pipeline` with `DalleProvider`, preserving the Genblaze run manifest alongside the PRESS attempt manifest.

The initial provider is OpenAI through `genblaze-openai`. The primary and optional fallback model are server configuration. The pipeline never places the selected fragment or personal note into routine logs or generated image text.

### Durable storage boundary

The API owns an `ObjectStore` port. The live adapter wraps `genblaze-s3` against a private Backblaze B2 S3-compatible endpoint. Stable object keys are canonical. Presigned URLs are derived per response and are never stored.

A pressing is reconstructed from `pressings/{pressing-id}/state/current.json` plus immutable source records, attempt manifests, final metadata, provenance, and persisted progress events. Process memory is only an optimization.

### Execution and progress

PR 2 uses bounded in-process background execution with durable checkpoints and persistent polling at `GET /v1/pressings/{id}/events`. Completed records survive process replacement. In-flight work is not claimed to be crash-safe: an interrupted non-terminal run is detected on reconstruction and exposed as a recoverable failure.

### Retry and lineage

Maximum generation attempts default to three. Attempt one uses the primary model. Attempt two applies a corrected brief or transient retry. Attempt three uses the configured fallback model when present, otherwise a final corrected primary attempt. Every attempt has a unique run directory and `parent_run_id`; attempts never overwrite each other. Human anchors and the pressing serial never change.

### Idempotency and serials

Create, retry, and finalization use stable idempotency records in B2. Serial allocation is serialized within the service and persisted in B2; it survives restart. Distributed multi-writer serial allocation remains a documented post-MVP hardening item.

### Deletion

Deletion removes the pressing prefix and writes a tombstone under a separate tombstone prefix. B2 deletion is not atomic, so partial failure is reported with a stable storage error rather than hidden.

## Consequences

- PR 2 proves durable completed-record reconstruction without claiming a production job queue.
- Live secrets remain server-only.
- PR 3 can consume the OpenAPI contract without owning pipeline or storage logic.
- A later deployment may replace the execution coordinator without changing the domain, provider, repository, or storage interfaces.
