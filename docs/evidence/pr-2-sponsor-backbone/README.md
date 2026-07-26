# PR 2 sponsor backbone evidence

This directory holds sanitized, reproducible evidence for the Genblaze and Backblaze B2 backbone.

## Committed evidence status

* Branch: `feat/genblaze-b2`
* Pull request: #33
* Deterministic fixture: `fixtures/demo-source/source.json`
* Non secret API suite: generated from the final branch head and reported in the pull request
* Live report: generated only by the protected `Live sponsor verification` workflow and uploaded as a workflow artifact

No credential, authorization header, full personal note, full selected fragment, or signed URL belongs in this directory.

## Live evidence contract

`live-report.json` is produced by `services/generation-api/scripts/verify_live_sponsor_backbone.py`. It includes:

1. provider, model, and exact Genblaze package versions
2. pressing ID, serial, run ID, and parent run ID
3. ordered durable progress trace
4. sanitized attempt manifests and asset validation
5. stable private B2 object keys
6. final metadata and provenance
7. idempotency proof
8. fresh process reconstruction proof
9. bounded recovery proof
10. explicit known limitations

The file is not committed until a real protected run produces it. A fixture only report never satisfies the live completion gate.
