# Security policy

## Reporting

Please report vulnerabilities privately through GitHub Security Advisories for this repository. Do not include credentials, private source material, personal notes, or screenshots in a public issue.

## PR 1 boundaries

- B2 and provider variables are server-only and never use the `NEXT_PUBLIC_` prefix.
- Environment parsing is centralized in the web server and FastAPI service.
- API logs contain operational metadata only. Personal notes, selected fragments, screenshots, and secrets are excluded.
- No unrestricted URL fetch exists.
- Client bundles are scanned for secret variable names and sentinel values in CI.
- Gitleaks runs in pull-request CI.

## Required controls before live source extraction

PR 3 must treat URL capture as an SSRF boundary. It must include scheme restrictions, host and IP validation, private-network denial, DNS rebinding defenses, redirect revalidation, timeouts, response-size limits, content-type allowlists, and safe parsing. Screenshot uploads must have authenticated object ownership, content validation, size limits, and malware-aware handling before production use.

## Dependency maintenance

Dependabot checks npm, Python, and GitHub Actions dependencies weekly. Security updates should be reviewed and merged through the same test and contract gates as feature work.
