# Sparse-evidence publishing and real-sample QA

Use this when a short video has a valid `ready` EvidenceBundle but very little transcript evidence.

## Core failure mode

A formal artifact can satisfy structural gates while still being unusable. Fixed output quotas (for example, several 200–500-word sections from a single 146-character transcript segment) create an incentive for the writer to pad with unsupported mechanisms, comparisons, motives, or recommendations.

Treat these as three separate gates:

1. **Acquisition gate** — source resolves, transcript exists, EvidenceBundle is `ready`.
2. **Artifact gate** — the output is actually `PublishedMarkdown`; placeholders, broken sections and unresolved references are rejected.
3. **Human content gate** — the final prose is readable, proportionate to evidence and free of unsupported padding.

Passing gate 1 or 2 never implies gate 3.

## Fixture and real-writer discipline

- A fixture writer proves deterministic plumbing and structural validation only. Never use fixture prose as evidence of content quality.
- A model-backed writer can also pass structural gates while hallucinating. Read the complete final Markdown.
- Reject phrases or claims that introduce external agencies, products, architectures, motives, causal mechanisms, audience reactions, or user-stack mappings without supporting evidence. Typical examples are comparisons to NASA/ESA/SpaceX, Byzantine fault tolerance, propaganda intent, or arbitrary Obsidian/Hermes advice.
- Do not “clean up” a structurally valid but evidence-inflated report and then claim the pipeline is fixed. Fix the planning/gating contract first.

## Evidence-budget pattern

Prefer an explicit evidence budget over duration-only routing. A conservative initial policy is:

```text
no transcript                         → preanalysis / blocked
long video (for example >= 30 min)    → full contract unchanged
very short + sparse transcript        → sparse contract
otherwise                             → condensed contract
```

Candidate sparse signal (calibrate with corpus evidence before making permanent):

```text
duration <= 180 seconds
AND (transcript_chars <= 600 OR distinct transcript starts < 3)
```

The important invariant is not these exact numbers; it is that output depth must be bounded by evidence density.

### Requested mode vs effective mode

Keep two values explicit at orchestration surfaces:

- `requested_mode`: caller intent (`auto`, `full`, `condensed`, or `sparse`).
- `effective_mode`: the mode actually placed in `ReportPlan` and used by Writer plus gates.

`auto` may use the evidence budget. An explicit `full`/`condensed`/`sparse` request must override auto-classification before rendering, provider selection, and verification. Otherwise a short full-gate fixture can be silently routed through the deterministic sparse writer: provider calls fall to zero while the caller still verifies against full thresholds.

Tests must assert both the effective plan mode and provider call count. During staged implementation, focused C1 tests may pass while integration tests fail for this exact reason; do not claim the slice release-ready until orchestration propagates the requested mode end-to-end.

## Deterministic sparse report pattern

Keep the common §0–§8 `PublishedMarkdown` interface, but make sparse §3/§4/§7 deterministic and evidence-only:

- §3: one confirmed observation plus an explicit evidence boundary.
- §4: one evidence-scope module stating what can and cannot be inferred.
- §5: one real short quote is enough when only one reliable quote exists.
- §7: one value, one limitation and one conservative next step.
- §6 may use canonical title/description concepts only when each emitted concept is a verbatim source substring; metadata must not create actions or causal relations.
- Sparse deterministic sections must not call an LLM or require external research.

For a report-aware sparse fidelity gate, reconstruct deterministic §3/§4/§7 from the report evidence and compare normalized sections with the submitted Markdown. Extra padding must fail even if it contains a syntactically valid `[E1]` citation.

Do not weaken full/long-video gates to accommodate sparse videos.

## Metadata concept extraction safeguards

- Do not treat every 3–6 character Chinese phrase as a concept; promotional wrappers become false entities.
- Prefer conservative technical-suffix entities and explicit lifecycle groups.
- Strip common action/promo prefixes from a matched entity, then verify the emitted term is still a literal source substring.
- Compute metadata/transcript provenance from concepts, relations and actions that survive deduplication and `max_items`, not merely from candidate presence.
- Add a regression with more than five transcript candidates to prove metadata still reaches the final deterministic §6 renderer; writer-context `top_n` truncation must not silently remove it.

## Douyin browser-media fallback seam

When yt-dlp metadata succeeds but direct media acquisition fails while an authorized browser can play the video:

1. Browser recovery captures one current media request and produces a temporary local audio path.
2. Inject that operation through a narrow `media_fallback(url, tmpdir, timeout) -> Path` seam.
3. Accept only a regular, non-symlink file contained inside the provider-owned temporary directory.
4. Upload that local file to ASR; never persist or expose signed URLs, cookies or request headers.
5. Preserve the original sanitized yt-dlp failure if fallback also fails.
6. Verify with both unit tests and a live seam run: forced primary failure → fallback temp audio → real ASR → `EvidenceBundle ready`.

## Required real-sample evidence

Before deployment, record and inspect:

- targeted test output and exit code;
- complete suite result;
- release gate result;
- real source acquisition result;
- actual artifact type (`PublishedMarkdown`, not merely `ready` or a draft string);
- full final Markdown human QA.

If the artifact passes scripts but human QA fails, report `artifact contract PASS / human content QA FAIL`, do not save a formal Vault note, and continue at the planning/gate layer.
