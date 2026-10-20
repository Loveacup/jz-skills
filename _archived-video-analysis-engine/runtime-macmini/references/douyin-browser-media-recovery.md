# Douyin browser-media recovery path

Use this recovery when a single public Douyin video plays in the user's authorized browser session but `yt-dlp` repeatedly returns `auth_required` / “Fresh cookies needed”, including after valid same-browser cookies. This is a **single-video evidence recovery path**, not a signer implementation or crawling method.

## Decision

Do not copy or hand-maintain `a_bogus`/private signing code. Keep shared core browser-agnostic:

```text
Authorized browser page
→ capture current-tab media request in memory
→ download one audio/media asset into a 0700 TemporaryDirectory
→ immediately discard signed URL, cookies, headers and raw network event
→ inject local media Path into Douyin media/ASR provider
→ H200 ASR
→ EvidenceBundle ready
→ Writer + publish gate
```

The core provider should accept an injected `MediaResolver(url, tmpdir, timeout) -> Path`; OpenCLI/CDP/browser orchestration remains outside shared core.

## Recovery procedure

1. Confirm the page itself is playable and has one stable canonical video identity.
2. If the Browser Bridge is disconnected, update/restart the bridge tooling using its official supported path, then restart Chrome only when already authorized to do so.
3. Bind the current tab and read only safe DOM metadata: canonical id, title, author, description and duration.
4. Start network follow **before** reloading; historical requests usually are not available after binding.
5. Reload once, verify the `<video>` element reaches a playable state, then select one successful media/audio request.
6. Do not print or persist the signed URL. Download directly to a user-only temp directory and verify with `ffprobe` (codec, duration, size).
7. Send the local file to H200. Persist only transcript text/hash and safe metadata.
8. Build and validate `EvidenceBundle`; only `status=ready` may enter Writer.
9. Run all the way to `publish_markdown()`. `EvidenceBundle ready` alone is not E2E success.

## Provider seam requirements

- Default yt-dlp behavior remains unchanged when no fallback is injected.
- Fallback runs only after explicit media-download timeout, non-zero exit or no output.
- Returned path must exist, be a regular non-symlink file and resolve inside the provider-owned temp directory.
- Reject outside paths and symlink escapes before H200.
- Resolver exceptions are replaced with a fixed safe error; never include raw exception text.
- MIME derives from a fixed extension map; unknown suffix uses `application/octet-stream`.
- The adapter's existing generic error taxonomy should not be silently described as more precise than it is.

## Mandatory privacy gate

Never persist or include in repo, fixtures, JSON evidence bundles, provenance, Markdown, logs or audit packages:

- signed CDN media URLs
- cookies or authorization/request headers
- full browser network events or response bodies
- private ASR endpoint values
- resolver raw exception text

The only durable provenance is the canonical public video URL plus content hashes.

## Real-sample quality trap

Sparse short-video ASR can still produce a valid `ready` bundle but fail `PublishedMarkdown` because deterministic sections remain skeletons. A common case is §6 knowledge graph ignoring clear concepts present in canonical title/description. Fix evidence coverage conservatively:

- allow only title/description phrases that occur verbatim;
- filter packaging words, durations, pure numbers and sentence fragments;
- metadata concepts may express co-occurrence, not invented causality or actions;
- if no reliable concept remains, keep the skeleton and fail closed;
- never weaken `P0_NO_SKELETON` merely to publish.

## Acceptance

A live recovery is complete only when all are true:

- media duration plausibly matches page duration;
- H200 returns non-empty topic-matching text;
- `EvidenceBundle.status == ready` and validates;
- signed/private material is absent from bundle/provenance/output;
- `publish_markdown()` returns `PublishedMarkdown`;
- publishable, report-depth and full release gates pass;
- final Markdown receives human readability QA.
