# PR 5 · Release proof matrix

This document is the source of truth for what PRESS has actually verified. Empty boxes are intentionally not claims.

## Release identity

- Branch: `feat/release-proof`
- Base: `feat/visual-system-motion`
- Expected web commit: replace with the final PR 5 head after verification
- Expected API commit: replace with the final PR 5 head after verification

## Deployment

- [ ] Final PR 5 head is deployed to the web preview alias
- [ ] Final PR 5 head is deployed to the API target
- [ ] Web `/` returns 200
- [ ] Web `/press/new` returns 200
- [ ] Web `/pressings` loads against the configured API
- [ ] API `/healthz` returns 200
- [ ] API `/version` reports the expected release version

## Browser matrix

| Mode | Viewport or setting | Result | Evidence |
| --- | --- | --- | --- |
| Desktop | Current Chromium, 1440 × 900 | Pending | Pending |
| Mobile | iPhone-sized, 390 × 844 | Pending | Pending |
| Fresh session | Empty storage and cache | Pending | Pending |
| Keyboard only | No pointer interaction | Pending | Pending |
| Reduced motion | `prefers-reduced-motion: reduce` | Pending | Pending |
| Slow network | Browser throttling | Pending | Pending |

## Product journeys

- [ ] Deterministic fixture completes Capture → Generate → Reveal → Archive → Reopen
- [ ] Exact fragment survives round trip unchanged
- [ ] Exact personal note survives round trip unchanged
- [ ] Screenshot fallback completes
- [ ] Refresh during generation restores honest status
- [ ] Refresh after save reconstructs the pressing
- [ ] Front and back remain keyboard accessible
- [ ] View source opens safely
- [ ] One recoverable failure preserves human anchors

## Sponsor proof

These gates cannot be checked using mocked credentials.

- [ ] Real Genblaze-orchestrated generation completed
- [ ] Provider and model recorded
- [ ] Run lineage recorded
- [ ] At least one retry or fallback path verified
- [ ] Real private Backblaze B2 write completed
- [ ] Source, attempts, final asset, metadata, and provenance stored
- [ ] Completed pressing reconstructed after process restart
- [ ] Sanitized B2 object tree captured

## Automated gates

- [ ] Web lint
- [ ] Web TypeScript
- [ ] Web unit and integration tests
- [ ] Web production build
- [ ] Python formatting
- [ ] Python lint
- [ ] Python static typing
- [ ] Python tests
- [ ] Contract drift
- [ ] Deterministic E2E smoke
- [ ] Accessibility smoke
- [ ] Secret scan

## Security review

- [ ] No provider or B2 secrets in client bundles
- [ ] No private notes or screenshot contents in public logs
- [ ] Upload MIME and size validated server-side
- [ ] URL retrieval blocks internal-network targets
- [ ] External source links use safe `rel` values
- [ ] B2 key is least privilege
- [ ] CORS is deliberately configured

## Performance

- [ ] Landing mobile LCP measured
- [ ] Capture mobile LCP measured
- [ ] Archive thumbnails avoid full-resolution detail assets
- [ ] No avoidable layout shift from media
- [ ] Pointer tilt avoids React state churn per frame
- [ ] Results and environment documented

## Submission assets

- [ ] Product screenshots
- [ ] Real press progress screenshot
- [ ] Retry or fallback screenshot
- [ ] Front and back screenshots
- [ ] Archive after refresh screenshot
- [ ] Reduced-motion screenshot or video
- [ ] Mobile and desktop screenshots
- [ ] Genblaze evidence
- [ ] B2 evidence
- [ ] Passing CI evidence
- [ ] Demo video under the challenge limit
- [ ] Submission copy names exact providers and models

## Current known blockers

1. PR 4's public branch alias has served a successful earlier commit but has not yet proven the final PR 4 head because Vercel rate-limited later builds.
2. Live Genblaze and B2 proof remain blocked until the GitHub environment secrets are configured.
3. Final production URLs and authentic evidence cannot be declared until the corresponding deployed commit SHAs are independently matched.
