---
title: Video Analysis Engine — WRR Research & Knowledge Expansion Technical Spec
status: design-reviewed
version: 0.2.0
created: 2026-07-13
written_with: "[[writing-specs-designs]]"
---

# WRR Research & Knowledge Expansion Technical Spec

## 0. Status and scope

This document specifies a future research layer for `video-analysis-engine`. It is an L2 design source of truth, not implementation evidence.

**This Spec does not authorize implementation, runtime deployment, commit, or push.**

### Current-state evidence

The current engine does not execute WRR:

- `scripts/fact_check_wrr.py:6-9` explicitly limits itself to claim extraction and structured dry-run output.
- `scripts/generate_report.py:321-342` calls `extract_claims()` and `build_result(..., dry_run=True)`; verdicts remain `uncertain` and sources remain empty.
- `scripts/video_analysis_engine.py:415-437` detects whether a local WRR path exists, but reports `external_research.available=true` even when no search ran.
- `scripts/generate_report.py:345-379` still allows the legacy `results dict → AnalysisInput` path to bypass a canonical `EvidenceBundle` input.
- `ClaimBundle` is currently built during draft assembly for selected depth profiles rather than for every `ready` input.
- Existing publication gates validate Markdown/video evidence and sparse deterministic output, but not `[R#]`, `[S#]`, research hashes, research coverage, or knowledge-expansion projection.

## 1. Goals

1. Run a lightweight WRR grounding pass for every `ready` video, followed by signal-triggered expansion.
2. Make factual verification and knowledge expansion equal first-class research lanes.
3. Allow validated WRR research to enhance §§3/4/6/7 in sparse, condensed, and full reports.
4. Keep sparse projection provider-free, bounded, deterministic, and fidelity-rebuildable from frozen artifacts.
5. Separate video evidence, video claims, research planning, research evidence, adjudication, and report projection into immutable artifacts.
6. Preserve claim-sensitive fail-closed publication: safely removable research may degrade; unsafe unresolved dependencies block.
7. Preserve one user-facing Markdown note while retaining a private immutable research audit archive.
8. Use WRR routing modes and local-first behavior rather than bypassing WRR with raw search calls.

## 2. Non-goals

- Batch/creator/feed crawling.
- Replacing transcript evidence with web research.
- Silently correcting the original transcript or EvidenceBundle.
- Treating search snippets as evidence.
- Letting Writer/LLM decide factual verdicts from raw search results.
- Storing credentials, cookies, signed media URLs, private headers, raw provider payloads, or full browsing histories.
- Requiring live network access in deterministic unit/release tests.
- Producing an Obsidian sidecar next to the single formal note.
- Implementing a second search router inside the video engine.

## 3. Terminology

| Term | Meaning |
|---|---|
| `EvidenceBundle` | Immutable platform acquisition artifact: identity, metadata, transcript, audience signals, provenance, safe errors. |
| `ClaimBundle` | Immutable video-only claims derived deterministically from canonical video evidence. Produced for every `ready` mode. |
| `ResearchPlan` | Coverage-first plan describing verification and knowledge-expansion work, budget, queries, stop conditions, and input hashes. |
| `RawResearchRun` | Untrusted WRR adapter output: candidate sources, search diagnostics, extracted quote candidates, and proposed relations. |
| `ResearchBundle` | Validated/adjudicated peer artifact containing accepted sources, quotes, claim results, entity results, knowledge expansions, coverage, conflicts, and errors. |
| `ResearchProjectionPlan` | Immutable mode-specific selection of validated research objects for §§3/4/6/7. Contains no free-form research prose. |
| `Verification Lane` | Research that supports, contradicts, qualifies, or leaves unresolved a video-derived claim. |
| `Knowledge Expansion Lane` | Research that extends understanding through definitions, mechanisms, history, comparison, application, prerequisites, counterexamples, limitations, and further reading. |
| `[E#]` | User-visible video/local evidence citation. Internal identity remains canonical and section-independent. |
| `[R#]` | User-visible validated external factual/research source. |
| `[S#]` | User-visible social/community signal. Never independently supports a factual claim. |
| `C#` | User-visible video-derived claim. |
| `RC#` | User-visible validated research-derived claim. |
| `KX#` | User-visible knowledge-expansion unit composed only from validated research claims. |

User-visible IDs are deterministic display aliases. Internal references use stable content-derived UIDs.

## 4. Architecture

```text
Platform Adapter
  → EvidenceBundle
  → Analysis Bridge
  → AnalysisInput / EvidenceMap
  → deterministic ClaimBundle
  → ResearchPlanner
  → ResearchPlan
  → ResearchProvider seam
      ├─ HermesWRRAdapter (production)
      ├─ FixtureResearchProvider (CI)
      └─ ArchivedResearchProvider (replay)
  → RawResearchRun                         [untrusted]
  → ResearchValidator
  → ClaimAdjudicator
  → ResearchBundle                        [validated peer artifact]
  → ResearchProjector
  → ResearchProjectionPlan
  → deterministic/validated section writers
  → DraftReport
  → research-aware publication gates
  → PublishedMarkdown
  → private immutable archive + one Markdown note
```

### 4.1 Artifact ownership

| Artifact | Owner | May perform I/O | Mutable after creation |
|---|---|---:|---:|
| EvidenceBundle | platform acquisition | yes | no |
| ClaimBundle | video engine | no | no |
| ResearchPlan | ResearchPlanner | no | no |
| RawResearchRun | ResearchProvider adapter | yes | no |
| ResearchBundle | ResearchAssembler, consuming pure Validator/Adjudicator outputs | no | no |
| ResearchProjectionPlan | ResearchProjector | no | no |
| Research archive | ResearchArchive | yes | append immutable object or governed deletion only |
| DraftReport | report assembly | no | assembly-only |
| PublishedMarkdown | publication boundary | no | no |

### 4.2 Canonical input rule

Research cannot begin without a validated `ready` EvidenceBundle. The legacy `results dict → AnalysisInput` path must eventually compile through a canonical EvidenceBundle/bridge, not fabricate a hash from an arbitrary dict.

During migration, legacy inputs may run with research unavailable/off, but may not claim `executed=true` or produce `[R#]/[S#]/RC#/KX#`.

## 5. Identity and hashing

### 5.1 Internal IDs

Display aliases such as `C1` and `R1` are assigned after deterministic sorting. Cross-artifact references use stable UIDs:

```text
claim_uid  = sha256(claim_type | normalized_text | sorted canonical evidence locations)
source_uid = sha256(canonical_url | publisher_id | content_hash)
quote_uid  = sha256(source_uid | normalized locator | verbatim quote)
topic_uid  = sha256(normalized label | sorted anchor evidence UIDs)
rc_uid     = sha256(normalized statement | sorted accepted quote UIDs)
kx_uid     = sha256(topic_uid | expansion_type | sorted rc_uids)
```

A section-local `[E1]` is never a cross-artifact identity. Existing canonical evidence locations such as `3:E1` remain compatibility pointers until a source-segment UID is available.

### 5.2 Dual hashes

Each artifact with execution history uses two hashes:

- **semantic hash**: stable content used for equivalence, deterministic projection, and fidelity.
- **audit artifact hash**: full immutable artifact including timestamps, WRR version, execution trace, budget usage, stop reason, and safe errors.

Volatile fields such as IDs, wall-clock durations, and creation timestamps are excluded from semantic hashes.

Hash envelopes are normative:

| Hash | Included canonical envelope | Explicitly excluded |
|---|---|---|
| `ResearchPlan.plan_semantic_hash` | `schema_version`, `planner_version`, canonical `input`, capability fields excluding check time/reason prose, lanes, budget, entities, topics, claim requests, queries, expansion candidates, stop conditions | `plan_id`, `created_at`, the hash field itself, debug notes |
| `ResearchBundle.raw_hash` | canonical RawResearchRun candidates, route/fallback order, safe provider errors and referenced snapshot content hashes | `raw_hash` itself, local paths, secrets |
| `ResearchBundle.validated_semantic_hash` | schema/rule versions, input semantic hashes, projection-relevant status/disposition, validated sources/quotes/assessments, claim/entity results, RC/KX, coverage, conflicts and unresolved items | execution timing, provider latency, raw candidates, safe errors, bundle ID, timestamps, all hash fields |
| `ResearchBundle.audit_artifact_hash` | complete canonical persisted bundle, including `raw_hash`, execution trace, timestamps, WRR version, budget use, safe errors and `validated_semantic_hash` | `audit_artifact_hash` itself and any forbidden secret/private field |
| `ResearchProjectionPlan.projection_semantic_hash` | schema/projector/template versions, Evidence/Claim/Research validated semantic hashes, ReportPlan hash, report mode, section budgets, entries and omissions | projection ID, creation time, the hash field itself |
| source `content_hash` | exact normalized snapshot bytes after sanitization | path, filesystem metadata, fetch latency |

Whenever another artifact uses `research_bundle_hash`, that name means `ResearchBundle.validated_semantic_hash`; the audit hash must be named explicitly and may not drive report projection.

### 5.3 Canonical JSON

- UTF-8.
- Keys sorted lexicographically.
- No insignificant whitespace.
- UTC ISO-8601 timestamps.
- Confidence rounded to four decimals.
- URLs canonicalized.
- Schema-defined nulls retained; unknown fields rejected for major-version validation.
- Semantically unordered lists sorted by stable UID; execution traces retain order.

Sparse fidelity uses:

```text
EvidenceBundle semantic hash
+ ClaimBundle semantic hash
+ ResearchBundle validated semantic hash
+ ResearchProjectionPlan semantic hash
+ deterministic template version
```

It does not use the audit artifact hash.

## 6. ResearchPlan schema

```yaml
schema_version: research-plan/1.0
plan_id: rp_...
created_at: 2026-07-13T00:00:00Z
planner_version: research-planner/1
plan_semantic_hash: sha256:...

input:
  evidence_bundle_hash: sha256:...
  claim_bundle_hash: sha256:...
  canonical_id: ...
  platform: bilibili|youtube|douyin
  report_mode: sparse|condensed|full
  research_policy: auto|force|deep|off

capability_snapshot:
  available: true
  route: hermes_wrr
  checked_at: ...
  reason: ...

lanes:
  verification_enabled: true
  knowledge_expansion_enabled: true

budget:
  max_queries: 4
  max_fetches: 6
  max_sources: 6
  max_elapsed_seconds: 60
  cross_check_depth: 2
  knowledge_expansion:
    max_topics: 2
    max_units: 2
    max_research_claims: 4
  coverage_targets:
    p0: 1.0
    adopted_p1: 1.0
    p2: 0.5
  freshness_policy_id: default-v1

entities: []
topics: []
claims: []
queries: []
expansion_candidates: []
stop_conditions: {}
```

### 6.1 Entities

```yaml
- entity_uid: ent_...
  display_id: ENT1
  mention: ...
  evidence_uids: [...]
  entity_type: product|person|org|place|technology|paper|event|unknown
  ambiguity: 0.0
  temporal_sensitivity: stable|changing|current
  goals: [canonicalize, disambiguate, correct_asr, find_official_source]
  target_sections: ["6"]
  priority: 0
```

Entity results may propose ASR corrections but never mutate EvidenceBundle transcript text.

### 6.2 Topics and knowledge-expansion goals

```yaml
- topic_uid: topic_...
  display_id: T1
  label: ...
  anchor_evidence_uids: [...]
  entity_uids: [...]
  relevance: 0.95
  expansion_goals:
    - definition
    - mechanism
    - historical_context
    - comparison
    - application
    - prerequisite
    - counterexample
    - limitation
    - further_reading
  target_sections: ["3", "4", "6", "7"]
```

### 6.3 Claim research requests

The plan references ClaimBundle objects; it does not duplicate claim text/warrant/backing.

```yaml
- claim_uid: claim_...
  risk: P0|P1|P2|P3
  verification_goals: [verify, freshness, contextualize, compare]
  temporal_class: breaking|current|versioned|historical|stable
  required_source_relations: [first_party, independent]
  min_independent_publishers: 2
  target_sections: ["3", "4", "7"]
  required_for_publication: true
  priority: 95
```

### 6.4 Queries

```yaml
- query_uid: query_...
  display_id: Q1
  lane: verification|knowledge_expansion
  mode: discovery|grounding|research|academic|platform|recovery
  query: ...
  claim_uids: [...]
  entity_uids: [...]
  topic_uids: [...]
  expansion_dimensions: [mechanism]
  language: zh
  freshness_window_days: 30
  preferred_source_kinds: [official_docs, paper]
  preferred_authority_relations: [first_party, independent]
  priority: 95
  optional: false
  dedup_key: ...
```

One query may serve several claims/entities. Exact numerical/date verification should normally isolate one claim.

### 6.5 Knowledge-expansion candidate scoring

```yaml
- candidate_uid: kxc_...
  topic_uid: topic_...
  dimension: mechanism
  question: ...
  scores:
    relevance_to_video: 0.95
    knowledge_gap: 0.90
    learning_value: 0.88
    evidence_availability: 0.80
    novelty_vs_local_kb: 0.60
    actionability: 0.40
  total_score: 0.84
  selected: true
```

Initial weights:

```text
relevance_to_video 0.30
knowledge_gap 0.20
learning_value 0.20
evidence_availability 0.15
novelty_vs_local_kb 0.10
actionability 0.05
```

### 6.6 Initial budgets

| Mode | Queries | Fetches | Sources | Time | Topics | KX units | RC claims |
|---|---:|---:|---:|---:|---:|---:|---:|
| sparse | 4 | 6 | 6 | 60s | 2 | 2 | 4 |
| condensed | 8 | 12 | 10 | 120s | 3 | 5 | 10 |
| full | 16 | 24 | 20 | 240s | 5 | 10 | 20 |
| deep/P0 | coverage-first | 36 | 30 | 360s | adaptive | 16 | 32 |

These are hard ceilings, not quotas. Research stops early when coverage and expansion-value conditions are met.

## 7. ResearchProvider seam and WRR adapter

Conceptual interface:

```text
ResearchProvider.execute(plan: ResearchPlan) -> RawResearchRun
```

The Engine calls this interface exactly once per plan. It does not retry, select Exa/Brave directly, or shell out to WRR.

### 7.1 Production behavior

`HermesWRRAdapter` executes the plan through WRR:

- WRR local-first behavior remains owned by WRR.
- Each query declares a routing mode before execution.
- WRR owns thin-source retry, engine fallback, cross-checking, and route diagnostics.
- Adapter records bounded route trace and safe errors.
- Raw search snippets are candidate discovery metadata only.
- Only fetched/extracted source content may yield quote candidates.

Standalone CLI without an injected provider reports `capability unavailable`; it never silently claims automatic research succeeded.

### 7.2 Test and replay adapters

- `FixtureResearchProvider`: deterministic no-network fixtures for CI/release.
- `ArchivedResearchProvider`: replays an archived **RawResearchRun only**, then runs the normal Validator/Adjudicator path.

A separately named `ResearchArchiveLoader` may load a previously validated ResearchBundle for deterministic report reproduction. It is not a ResearchProvider. On every load it rechecks schema version, semantic/audit hashes, input-hash closure, source snapshot hashes, and reference closure before the bundle can reach projection.

Two non-production adapters make the seam concrete rather than hypothetical.

## 8. RawResearchRun and validation

`RawResearchRun` is untrusted input. It may contain:

- query execution summary;
- candidate source identities;
- candidate snapshots/quotes;
- proposed claim/entity/topic relations;
- provider confidence and rationale;
- retry/fallback trace;
- safe errors.

It may not contain secrets or private provider payloads.

`ResearchValidator` performs:

1. input hash and plan hash checks;
2. budget conformance;
3. URL/source identity normalization;
4. quote existence and hash verification against bounded/full snapshots;
5. snippet-only rejection;
6. freshness evaluation;
7. orthogonal source classification;
8. publisher independence grouping and syndication detection;
9. claim-specific suitability assessment;
10. social-source restrictions;
11. candidate relation validation;
12. reference closure and duplicate removal.

Rejected candidates remain in the audit artifact with reasons but never reach validated projection inputs.

## 9. ResearchBundle schema

```yaml
schema_version: research-bundle/1.0
bundle_id: rb_...
plan_id: rp_...
plan_semantic_hash: sha256:...
evidence_bundle_hash: sha256:...
claim_bundle_hash: sha256:...

attempted: true
executed: true
status: not_requested|unavailable|completed|partial|failed|blocked|invalid
publication_disposition: pass|degraded|block

started_at: ...
completed_at: ...
wrr_version: ...
validated_semantic_hash: sha256:...
audit_artifact_hash: sha256:...

execution: {}
raw_research: {}
validated_research: {}
coverage: {}
conflicts: []
unresolved: []
errors: []
```

### 9.1 Execution summary

```yaml
execution:
  policy: auto
  modes_used: [discovery, grounding]
  query_count: 3
  fetch_count: 5
  source_count: 4
  elapsed_ms: 42000
  budget_exhausted: false
  stop_reason: coverage_met|budget_exhausted|all_engines_failed|blocked
  route_trace: []
```

Execution fields affect the audit hash, not the validated semantic hash.

### 9.2 Orthogonal source model

```yaml
sources:
  - source_uid: src_...
    display_id: R1
    identity:
      canonical_url: ...
      domain: ...
      publisher_id: ...
      publisher_name: ...
      author: ...
      published_at: ...
      fetched_at: ...
    source_kind: official_docs|official_announcement|official_data|paper|government|journalism|industry_report|personal_blog|forum|social_post|video
    authority_relation: first_party|primary_research|regulator|independent|expert_commentary|community|unknown
    quality:
      peer_reviewed: null
      editorial_reviewed: true
      official_for_entity_uids: [...]
      named_authors: true
      original_reporting: true
      content_stability: stable|mutable|ephemeral
      access_status: full|partial|paywalled
    independence:
      group_id: ...
      derived_from_source_uids: []
      syndicated_from: null
    language: zh
    content_hash: sha256:...
    freshness_status: fresh|stale|timeless
    snapshot_ref: snapshot_...
```

The same publisher, syndicated copies, or translations of one report count as one independent group.

### 9.3 Quotes and tiered snapshots

```yaml
quotes:
  - quote_uid: quote_...
    display_id: R1Q1
    source_uid: src_...
    verbatim_quote: ...
    context_before: ...
    context_after: ...
    locator:
      heading: ...
      paragraph_index: 12
      page: null
      timestamp: null
    quote_hash: sha256:...
    claim_uids: [...]
    entity_uids: [...]
    topic_uids: [...]
```

Default context is bounded. Initial guidance:

| Risk | Quotes/source | Context | Normalized full snapshot |
|---|---:|---:|---|
| P0 | 5 | 1000 chars | required |
| P1 | 3 | 800 chars | required for mutable/conflicting sources |
| P2 | 2 | 500 chars | optional |
| P3/social | 3 | 300 chars | no |

Snapshots are content-addressed private artifacts. Search snippets never become quotes.

### 9.4 Claim-specific source assessments

```yaml
claim_source_assessments:
  - assessment_uid: csa_...
    claim_uid: claim_...
    source_uid: src_...
    quote_uids: [...]
    role: primary|corroborating|contextual|social
    suitability: strong|acceptable|weak|invalid
    proposed_relation: supports|contradicts|contextualizes|irrelevant
    proposed_confidence: 0.82
    validated_relation: supports|contradicts|contextualizes|irrelevant
    validation_reason: ...
```

Derived grade may be `A/B/C/D/X`, but it never replaces the underlying orthogonal fields.

### 9.5 Claim adjudication

```yaml
claim_results:
  - claim_uid: claim_...
    verdict: supported|contradicted|mixed|unresolved|stale
    confidence: 0.90
    supporting_quote_uids: [...]
    contradicting_quote_uids: [...]
    contextual_quote_uids: [...]
    independent_publisher_count: 2
    required_publisher_count: 2
    freshness_satisfied: true
    adjudication:
      rule_version: claim-adjudicator/1
      accepted_assessment_uids: [...]
      rejected_assessment_uids: [...]
      conflict_present: false
      coverage_passed: true
    publication_action: keep|qualify|drop|block
    qualifier: ...
    checked_at: ...
```

The Engine adjudicates deterministically from validated assessments. It does not use URL majority vote. Structured numbers/dates/versions are normalized and compared by rules. Semantic candidate relations require quote provenance and confidence thresholds; low-confidence or conflicting P0 results remain unresolved or blocked.

### 9.6 Entity results and ASR correction proposals

```yaml
entity_results:
  - entity_uid: ent_...
    canonical_name: ...
    entity_type: ...
    official_url: ...
    aliases: [...]
    asr_correction:
      original: ...
      proposed: ...
      confidence: 0.92
    source_uids: [...]
    status: resolved|ambiguous|unresolved
```

The report may display a correction proposal, but EvidenceBundle transcript remains unchanged.

### 9.7 Research-derived claims

```yaml
research_claims:
  - research_claim_uid: rc_...
    display_id: RC1
    statement: ...
    claim_type: external_observed
    quote_uids: [...]
    source_assessment_uids: [...]
    adjudication_status: accepted|qualified|dropped
    qualifier: ...
```

A research claim cannot exist without accepted quote/source assessments.

### 9.8 Knowledge-expansion units

```yaml
knowledge_expansions:
  - expansion_uid: kx_...
    display_id: KX1
    topic_uid: topic_...
    expansion_type: definition|mechanism|historical_context|comparison|application|prerequisite|counterexample|limitation|further_reading
    title: ...
    research_claim_uids: [...]
    source_uids: [...]
    confidence: 0.88
    scores:
      relevance: 0.95
      novelty: 0.70
      learning_value: 0.90
      actionability: 0.50
    boundary: ...
    target_sections: ["3", "4", "6", "7"]
    publication_action: keep|qualify|drop
```

KX units are first-class outputs, not fact-check annotations. They must remain anchored to video evidence topics/entities and may not introduce unbound “interesting facts.”

### 9.9 Coverage

```yaml
coverage:
  verification:
    p0_total: 1
    p0_resolved: 1
    adopted_p1_total: 2
    adopted_p1_resolved: 2
    p2_total: 4
    p2_resolved: 3
    p2_ratio: 0.75
  expansion:
    selected_topics: 2
    expanded_topics: 2
    selected_units: 2
    source_grounded_units: 2
    learning_value_passed: 2
    dimension_counts:
      mechanism: 1
      application: 1
  gate_passed: true
```

Verification and expansion coverage are never collapsed into one score.

## 10. Knowledge Expansion Lane

### 10.1 Dimension pool

Every plan may consider:

- definition;
- mechanism;
- historical context;
- comparison;
- application;
- prerequisite;
- counterexample;
- limitation;
- further reading.

The planner selects high-value dimensions; it does not mechanically fill all dimensions.

### 10.2 Value selection

Candidates must satisfy initial thresholds:

```text
relevance ≥ 0.70
learning value ≥ 0.65
source grounding required
not a duplicate of recent local knowledge unless it adds a meaningful delta
```

Local WRR results may reduce duplicate explanation and instead produce a link/delta suggestion.

### 10.3 Verification/expansion budget split

Default split:

- general video: verification 60%, expansion 40%;
- tutorial/course/interview/science: verification 40%, expansion 60%;
- news/policy/medical/financial/security: verification dominant.

The split is planning guidance; P0 verification is never sacrificed to reach an expansion quota.

## 11. ResearchProjectionPlan schema

```yaml
schema_version: research-projection/1.0
projection_id: rproj_...
created_at: ...
projector_version: research-projector/1
projection_semantic_hash: sha256:...

inputs:
  evidence_bundle_hash: sha256:...
  claim_bundle_hash: sha256:...
  research_bundle_hash: sha256:...
  report_plan_hash: sha256:...
  report_mode: sparse|condensed|full

section_budgets: {}
entries: []
omissions: []
```

### 11.1 Projection entry

```yaml
- entry_uid: projection_...
  target_section: "4"
  object_type: claim_result|research_claim|knowledge_expansion|entity_result|conflict
  object_uid: kx_...
  purpose: explain_mechanism
  priority: 92
  required_video_evidence_uids: [...]
  allowed_research_claim_uids: [...]
  allowed_quote_uids: [...]
  deterministic_template_id: sparse_mechanism_v1
  max_chars: 320
  citation_policy: inline_required
  optional: false
```

### 11.2 Sparse budgets

Initial sparse projection caps:

```yaml
"3": {max_research_items: 1, max_chars: 220}
"4": {max_research_items: 1, max_chars: 320}
"6": {max_entities: 3, max_edges: 2, max_chars: 260}
"7": {max_research_items: 1, max_chars: 180}
```

Sparse has at most two KX units and four RC claims across the report. A KX unit may support several sections, but deterministic templates must avoid repeated prose.

### 11.3 Sparse determinism definition

“Provider-free sparse” means:

- research execution occurs before projection and produces a frozen ResearchBundle;
- sparse projection/writing performs no network or LLM calls;
- identical EvidenceBundle + ClaimBundle + ResearchBundle + ProjectionPlan + template versions produce byte-identical §§3/4/6/7;
- WRR unavailable safely replays the current transcript-only baseline when publication policy permits degradation.

## 12. Publication status and gates

### 12.1 Research status

```text
not_requested
unavailable
completed
partial
failed
blocked
invalid
```

Capability, execution, and evidence are distinct:

```yaml
capability_available: true
attempted: true
executed: true
validated_evidence_count: 4
status: partial
```

A detected WRR path never implies evidence availability.

### 12.2 Publication outcomes

- **PASS**: coverage met, adopted claims resolved, references/hash/freshness valid.
- **DEGRADED**: research incomplete/failed, but all dependent unsafe assertions were dropped or explicitly qualified.
- **BLOCKED**: unresolved dependencies cannot be safely removed or qualified.

### 12.3 Required research gates

1. `P0_RESEARCH_ARTIFACT_INTEGRITY`
   - schema versions and all input/semantic hashes match.
2. `P0_RESEARCH_REFERENCE_INTEGRITY`
   - every `[R#]/[S#]/RC#/KX#` resolves through the projection and validated bundle.
3. `P0_RESEARCH_CLAIM_BINDING`
   - §§3/4/7 research text binds to video claim/topic/entity anchors.
4. `P0_RESEARCH_SOURCE_SUITABILITY`
   - source kind/authority/independence/suitability satisfy claim policy; social cannot independently support facts.
5. `P0_RESEARCH_FRESHNESS`
   - time-sensitive adopted claims use fresh evidence.
6. `P0_RESEARCH_CONFLICT`
   - unresolved conflicts are represented as conflicts; Writer cannot flatten them into one conclusion.
7. `P0_RESEARCH_COVERAGE`
   - adopted P0/P1 and configured P2/expansion thresholds are met or safely degraded.
8. `P0_RESEARCH_PROJECTION_FIDELITY`
   - final sections do not exceed permitted RC/KX/quotes/templates.
9. `P0_RESEARCH_ARCHIVE_INTEGRITY`
   - required immutable archive/snapshot hashes exist and match.

### 12.4 Claim-sensitive failure matrix

| Failure | Default action | Publish |
|---|---|---|
| WRR unavailable | remove research additions, mark failed | degraded if no unsafe adopted dependency |
| P2 no source | drop expansion | yes |
| P1 number/date unresolved | drop the factual adoption; a bounded “video claims X, not externally verified” provenance statement is allowed only outside summary/recommendation logic | conditional |
| P0 unresolved | no factual/action recommendation; quotation must remain purely attributable and non-actionable | blocked unless every downstream factual/action dependency is removed |
| source conflict | preserve both positions, but remove adopted P0/P1/current conclusion; if the report depends on choosing one side, block | degraded only when the remaining text is a non-conclusive conflict account |
| snippet-only | reject candidate | no evidence effect |
| social-only factual support | reject factual RC | conditional |
| stale mutable source | refresh or drop | block if adopted current claim depends on it |
| bundle/hash/reference invalid | reject bundle/projection | block formal publication |
| budget exhausted | status partial; use only validated items | conditional |
| Writer exceeds projection | fidelity fail | block |
| user requested force/deep verification but coverage misses | no silent degradation | block |

## 13. §8 and private archive

Markdown §8 contains only:

- research status/disposition;
- coverage summary;
- execution/fetched timestamp;
- `[R#]/[S#]` source summary;
- semantic bundle hash;
- unresolved/conflict summary.

The complete bundle is stored privately, initially under a configured archive root such as:

```text
.p6r-cache/research/bundles/{audit_artifact_hash}.json
.p6r-cache/research/sources/{content_hash}.txt
```

Archive rules:

- immutable and content-addressed;
- identical write is idempotent;
- different content at an existing hash is rejected;
- `expires_at` controls reuse, not deletion;
- no absolute private paths in Markdown;
- credentials/private payload fields rejected recursively;
- per-source and per-bundle size limits required;
- normalized full snapshots restricted to P0/mutable/conflicting sources;
- social snapshots contain only bounded public post/thread context;
- retention and cleanup require a later governance policy and are not implemented by this Spec.

Security and deletion contracts are mandatory before production snapshot archival:

- the configured archive root must resolve outside the source repository and Obsidian vault;
- every derived target is canonicalized and checked to remain under that root; absolute child paths, `..`, path traversal, and symlink escapes are rejected;
- directory/file permissions default to `0700/0600`; writes use a temporary file in the same directory, flush, then atomic exclusive publication without following symlinks;
- a hash collision or existing path with different bytes is a hard error, never an overwrite;
- canonical URLs are sanitized before persistence: credentials are forbidden, tracking parameters are removed, and signed/tokenized query parameters are stripped or replaced by a non-replayable fingerprint;
- recursive secret scanning covers headers, cookies, bearer tokens, provider payloads, private filesystem paths, and signed URLs;
- retention policy, per-kind TTL, maximum bytes, and user-requested deletion selectors (video canonical ID, source URL/domain, bundle ID) must exist before live full snapshots are enabled;
- governed deletion removes content rather than mutating it and writes a content-free tombstone (`hash`, selector, reason, `deleted_at`). “Immutable” means no in-place mutation while retained, not immunity from an authorized privacy deletion;
- archive reads enforce the same root/symlink/hash checks as writes; operating-system disk encryption may add at-rest protection but is not treated as an application guarantee.

## 14. CLI and policy surface

Proposed policy surface:

```text
--research-policy auto|force|deep|off
--research-provider injected|fixture|archive
--research-archive-dir <private path>
--research-bundle <archive JSON for replay>
```

Rules:

- `auto` is the user-facing default for Hermes skill runs.
- `force` blocks when required verification coverage is incomplete.
- `deep` enables higher research/expansion budgets and deep-loop criteria.
- `off` exists for debug/legacy/controlled CI only; it must not masquerade as successful research.
- deterministic release uses fixture/archive providers and no network.
- real network E2E is explicitly opt-in.

The exact CLI names remain provisional until interface review; semantics are fixed by this Spec.

## 15. Migration and compatibility

### S0 — Correct capability/execution semantics

Files (≤3):

- `scripts/video_analysis_engine.py`
- `tests/test_evidence_source_gate.py`
- `tests/test_writer_section_context.py`

Acceptance: capability may be available while executed/evidence remain false; §8 cannot claim research ran.

### S1 — Research contracts and canonical hashing

- `scripts/evidence_contract.py`
- new `scripts/research_contract.py`
- new `tests/test_research_contract.py`

Acceptance: schemas, validation, stable semantic/audit hashes, security rejection.

### S2 — Deterministic ClaimBundle for every ready mode

- `scripts/video_analysis_engine.py`
- `tests/test_depth_quality_contract.py`
- `tests/test_draft_report_boundary.py`

Acceptance: sparse/condensed/full produce byte-stable video-only ClaimBundle before research; no LLM.

### S3 — ResearchPlanner and ResearchProvider seam

- `scripts/research_contract.py`
- new `scripts/research_pipeline.py`
- new `tests/test_research_provider.py`

Acceptance: provider called once; fixture and archive adapters exist; Engine performs no retry/search routing.

### S4 — WRR adapter and main orchestration

- `scripts/fact_check_wrr.py` or replacement adapter module
- `scripts/generate_report.py`
- new `tests/test_research_pipeline.py`

Acceptance: raw WRR candidates cannot bypass validation; legacy dry-run path remains explicit/deprecated.

### S5 — Validator, adjudicator, archive

- `scripts/research_contract.py`
- new `scripts/research_archive.py`
- new `tests/test_research_archive.py`

Acceptance: source suitability, independence, snippets, freshness, conflicts, immutable archive.

### S6 — Projection and sparse/full rendering

- `scripts/video_analysis_engine.py`
- `tests/test_sparse_generate_integration.py`
- `tests/test_sparse_publishable_fidelity.py`

Acceptance: same validated bundle projects into multiple modes without mutating bundle; sparse remains deterministic/bounded.

### S7 — Research publication gates

- `scripts/verify_publishable_report.py`
- `tests/test_published_markdown_boundary.py`
- new `tests/test_research_publish_gate.py`

Acceptance: all P0 research gates are observable through the report-aware public publication interface.

### S8 — CLI, fixture release lane, summaries

- `scripts/run_quality_gate.py`
- `scripts/release_gate.py`
- `tests/test_release_gate.py`

Acceptance: deterministic full+sparse research fixtures; network-free default release; opt-in real lane.

### Compatibility rules

- Existing EvidenceBundle major version remains unchanged unless research fields are incorrectly nested into it; this Spec forbids nesting.
- Existing `EvidenceBundle.fact_checks` remains readable during migration but is deprecated as a research transport.
- Existing `/tmp/{bvid}_fact_checks.json` is accepted only as legacy untrusted input and cannot produce validated `[R#]` without provenance/hash migration.
- Existing Markdown-only publication API remains backward compatible but cannot claim research validation; report-aware API owns all new P0 gates.
- Existing no-research transcript-only reports remain renderable; formal publication disposition follows policy and must not report false research availability.

## 16. Test and acceptance matrix

| Scenario | Falsifiable expectation |
|---|---|
| capability exists, no execution | `executed=false`; no R/RC/KX; any Markdown research ref fails |
| provider unavailable | attempted bundle records unavailable; safe baseline may degrade |
| partial coverage | unverified adopted P1 blocks unless dropped/qualified |
| snippet-only | cannot create quote/source assessment/RC |
| source conflict | explicit conflict; flattened conclusion fails |
| stale current source | suitability/freshness fails |
| social-only | may create S/community observation; cannot create factual RC alone |
| independent URL duplicates | same publisher/syndication counts once |
| broken RC→R or KX→RC | reference integrity fails |
| one-bit hash mismatch | artifact invalid; formal publication blocked |
| sparse deterministic replay | byte-identical §§3/4/6/7; provider/network spy count zero |
| sparse budget overflow | bundle invalid or blocked, never silently accepted |
| expansion below value threshold | omitted with reason; not projected |
| bundle reuse across modes | ResearchBundle hashes unchanged across sparse/condensed/full projections |
| Engine retry ownership | provider call count exactly one; attempts only inside raw WRR trace |
| archive overwrite | same content idempotent; different content rejected |
| security payload | credential/header/cookie/signed URL markers rejected |
| deterministic CI | fixture/archive-only tests pass without network |
| real Bilibili E2E | actual WRR execution, archive, citation closure, human QA |
| real YouTube E2E | same |
| real Douyin E2E | media/ASR path plus WRR research, citation closure, human QA |

### Spec-level acceptance

- Three peer artifacts and ownership are unambiguous.
- Verification and Knowledge Expansion are equal lanes.
- Every ready mode has deterministic video-only ClaimBundle.
- Capability is not execution; execution is not validated evidence.
- Research snippets never become evidence.
- Source quality is orthogonal and claim-specific.
- Engine owns deterministic adjudication and publication policy.
- Sparse research enhancement is bounded, provider-free after bundle freeze, and replayable.
- The only retry owner is WRR.
- Every migration slice is independently falsifiable and limited to at most three files.

## 17. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Existing tests codify false `available=true` semantics | S0 changes semantics before adding new fields. |
| Claim IDs drift because `[E#]` is section-local | stable claim/evidence UIDs; display aliases assigned after deterministic sort. |
| Live research makes sparse nondeterministic | freeze ResearchBundle; deterministic projection uses semantic hashes. |
| Writer sees raw candidates | Writer receives only ResearchProjectionPlan + validated objects. |
| Research enriches into unrelated trivia | every KX anchored to video topic/entity/evidence and value-scored. |
| URL majority masquerades as corroboration | independence grouping and claim-specific suitability. |
| Quality gate passes while research gate is bypassed | report-aware public-interface tests and release summary assertions. |
| Full snapshots increase copyright/privacy/storage risk | tiered snapshots, size caps, private archive, no OB sidecar, later retention governance. |
| WRR failure causes search storms | one provider call; WRR owns retries/fallback; no Engine retries. |
| Legacy paths fabricate provenance | legacy inputs cannot produce validated research until canonical EvidenceBundle bridge exists. |

## 18. Open questions

These are intentionally deferred to interface/prototype review, not silently assumed:

1. Exact archive retention and pruning policy.
2. Maximum normalized snapshot size by source kind.
3. Calibration dataset and thresholds for semantic `supports/contradicts/contextualizes` relation validation.
4. Whether P0 semantic relations require a second independent evaluator in addition to deterministic policy.
5. Exact CLI spelling and whether standalone CLI supports live WRR or only injected/archive providers.
6. Whether canonical EvidenceBundle migration occurs before S1 or as a dedicated bridge slice.
7. Whether report-level research gates become mandatory for all formal paths immediately or through a shadow/canary phase.

## 19. Decision record

Locked on 2026-07-13 through user review:

- automatic base research + trigger expansion;
- coverage-first adaptive budget;
- WRR正文优先增强 §§3/4/6/7，包括 sparse；
- sparse remains deterministic and bounded;
- claim-sensitive fail-closed;
- ResearchBundle as peer artifact;
- deterministic ClaimBundle for all ready modes;
- private immutable archive with Markdown source/hash summary;
- tiered source snapshots;
- orthogonal source model;
- Engine deterministic adjudicator;
- first-class full-dimension Knowledge Expansion Lane selected by value scoring and mode caps;
- independent ResearchProjectionPlan;
- semantic + audit dual hashes.

Implementation requires a separate explicit authorization after this Spec is reviewed and accepted.

## 20. Review record

### Codex read-only architecture review

- Initial verdict: `concern`.
- Required fixes: explicit hash envelopes; single ResearchBundle owner; separate raw replay vs validated archive-loader seams; stricter P0/P1/current conflict degradation; complete archive security/deletion contract.
- All five fixes were incorporated into v0.2.0.
- Closure verdict: `pass`; `REQUIRED_FIXES: []`.

### OMP focused audit

- Evidence bundle: 60KB, one Spec file, five bounded criteria.
- Run was automatically fused at `33,994,786` raw bytes.
- Final monitor state: `rejected`, `stopReason=toolUse`, `evidence_count=0`, no valid JSON verdict.
- `omp-finish --reject` completed. This is an audit-tool failure, not a design pass or design blocker. The same bundle must not be retried without a materially changed audit method or evidence package.

### Hermes verification

- Required headings present; Markdown fences balanced.
- S0–S8 each list no more than three implementation files.
- No stale pre-fix ownership/replay/conflict wording remained.
- Knowledge Expansion remains first-class in schema, budget, coverage, projection, and acceptance criteria.
- No implementation code, runtime configuration, deployment, commit, or push was performed by this Spec task.
