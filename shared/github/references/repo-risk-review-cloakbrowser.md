# Repo risk-review pattern: CloakBrowser-style binary wrapper

Use this as a compact example when reviewing GitHub repos that are mostly open-source wrappers around opaque runtime artifacts.

## What was learned

CloakBrowser (`CloakHQ/CloakBrowser`) presents as a Playwright/Puppeteer drop-in stealth browser. The repo source is mostly Python/TypeScript wrapper code, while the core stealth behavior lives in a downloaded patched Chromium binary.

## Review checklist applied

- Gather metadata via GitHub API: stars/forks/issues, creation date, pushed date, default branch, topics, license, latest release.
- Read README claims, but label them as claims unless independently tested.
- Clone shallow for code inspection when README/API is insufficient.
- Inspect package manifests:
  - Python: `pyproject.toml`, dependencies, scripts, optional extras.
  - Node: `package.json`, exports, peer dependencies, npm version.
- Inspect binary management code:
  - cache path
  - download URLs
  - fallback URLs
  - checksum verification
  - auto-update behavior
  - env vars for disabling/pinning/overriding
- Read all license files, especially binary/model/data license files that differ from wrapper source license.
- Search recent issues for security reports and “still blocked/detected” reports.

## Key CloakBrowser findings

- Wrapper source license: MIT.
- Compiled Chromium binary: separate proprietary Binary License; free internal use, no redistribution, OEM/SaaS license required for browser-as-a-service style use.
- First run downloads a ~200MB+ binary to `~/.cloakbrowser` unless overridden.
- Primary download host: `https://cloakbrowser.dev`; fallback: GitHub Releases.
- SHA-256 checksum verification exists, but core Chromium patches are not source-auditable from this repo.
- Auto-update checks/downloads can run in background; use `CLOAKBROWSER_AUTO_UPDATE=false` to disable.
- Local binary override: `CLOAKBROWSER_BINARY_PATH`.
- Cache override: `CLOAKBROWSER_CACHE_DIR`.
- Good recommendation shape: “promising experimental fallback for authorized automation, but isolate it, pin versions/disable auto-update, and avoid sensitive credentials until trust is established.”

## Suggested wording

> This is best understood as an open-source wrapper plus a separately licensed, opaque patched Chromium binary. It may be worth testing for authorized browser automation, but do not treat it as a fully open-source, fully auditable browser stack.
