# WRR Research & Knowledge Expansion — design decisions (2026-07-13)

## Why this reference exists

The current engine has `fact_check_wrr.py` and an `external_research.available` signal, but those do **not** prove that WRR search ran:

- `fact_check_wrr.py` currently extracts claims and emits dry-run/`uncertain` results with no sources.
- `external_research.available=true` currently means a route/capability was detected, not that research was executed or validated.

Never describe either signal as completed external research.

## Required research value

WRR is not only a fact-checker. Video research should serve two equal lanes:

1. **Verification Lane**
   - clarify entities, terminology and suspected ASR proper nouns;
   - verify dates, numbers, rankings, versions, prices, policies and current status;
   - cross-check causal, technical, scientific and high-risk claims;
   - preserve conflicts instead of forcing one answer.

2. **Knowledge Expansion Lane**
   - definition;
   - mechanism;
   - historical context;
   - comparison;
   - application;
   - prerequisite knowledge;
   - counterexample and limitation;
   - further reading.

Expansion must remain anchored to the video's evidence, topic or entities. It must be source-grounded and must not become unrelated encyclopedia padding.

## Search policy

Target behavior:

```text
every ready video
→ lightweight automatic grounding pass
→ trigger-driven expansion for ambiguity, freshness, P0/P1 claims, academic context, conflicts or learning value
```

Use coverage-first adaptive budgets rather than blindly consuming a fixed query count. Search stops when adopted high-risk/current claims are resolved and high-value expansion candidates are covered, or when the hard mode budget is reached.

## Current orchestration fallback

Until typed `ResearchPlan / ResearchBundle / ResearchProjectionPlan` artifacts are implemented in the engine:

1. The orchestrating Hermes agent may execute WRR at the agent layer.
2. Load `web-research-router`, choose the route mode before searching, and follow local-first routing.
3. Keep fetched quotes, URLs, dates and source roles explicit.
4. Label the result as agent-layer external research; do not claim the engine natively validated or archived it.
5. Do not mix raw search snippets into transcript evidence or silently alter the transcript.
6. If research cannot be completed, remove dependent assertions or state only that “the video claims X; external verification is unresolved.”

## Target artifact boundary

```text
EvidenceBundle
→ deterministic video-only ClaimBundle
→ ResearchPlan
→ WRR RawResearchRun (untrusted)
→ Validator + deterministic Adjudicator
→ ResearchBundle (validated peer artifact)
→ ResearchProjectionPlan
→ §§3/4/6/7 + research-aware publication gates
```

Key rules:

- `ResearchBundle` is a peer artifact and never mutates EvidenceBundle or ClaimBundle.
- WRR owns retries and engine fallback; the video engine calls the ResearchProvider seam once.
- `[E#]` = video evidence; `[R#]` = validated research source; `[S#]` = social signal.
- `C#` = video claim; `RC#` = validated research-derived claim; `KX#` = knowledge-expansion unit.
- Social sources cannot independently support factual claims.
- Search snippets are discovery metadata, never evidence.
- Sparse research execution happens before projection; projection/writing remains provider-free, deterministic and bounded from frozen artifacts.
- Capability, attempted execution, execution, validated evidence count and publication disposition are distinct fields.

## Canonical design source

The full reviewed technical Spec lives in the source repository at:

`shared/video-analysis-engine/references/wrr-research-knowledge-expansion-spec-20260713.md`

It defines schemas, dual hashes, archive/security rules, failure matrix, migration slices and acceptance tests. It is design-reviewed but not implemented; do not present target behavior as current runtime fact.
