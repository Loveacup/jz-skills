---
name: video-analysis-engine
description: >
  Analyze one Bilibili, YouTube, or Douyin video into an evidence-grounded Markdown knowledge asset.
  Use when the user provides a single video/share link or asks 视频分析、视频总结、B站解析、YouTube分析、抖音视频解析、弹幕或评论分析.
  Routes platform acquisition through typed adapters, requires transcript evidence for formal publication, and runs shared writer/quality gates.
  DO NOT use for batch crawling, creator-page harvesting, feed monitoring, video editing, downloading without analysis, or transcript-only requests.
version: 4.3.8
author: Hermes Agent
license: MIT
---

# Video Analysis Engine v4

Turn one supported video into one readable, evidence-grounded knowledge asset. Platform acquisition varies; analysis, Writer and release quality do not.

## 🚨 Red Flags

| Temptation | Why it is wrong |
|---|---|
| “Metadata is enough to write the report” | Only `ready` evidence may enter the formal Writer. `metadata_only` is diagnostic, not publishable. |
| “The extractor returned comments, so they are facts” | Comments/danmaku are audience signals, never factual evidence without independent support. |
| “The quality scripts passed, so prose is good” | Engineering gates do not replace human readability review. Check skeleton residue, repetition, transcript dumps and unsupported claims. |
| “A short Douyin video deserves a weaker bar” | Short duration changes depth, not evidence integrity or prose quality. Do not pad. |
| “One URL worked, so batch is harmless” | Batch/creator-page/feed crawling is explicitly out of scope. |
| “Keep the old Bilibili scripts as a second implementation” | `bilibili-video-analyzer` is forwarding-only. The canonical implementation lives here. |
| “WRR was detected, so external research ran” | Capability/route detection is not execution. Current `fact_check_wrr.py` is dry-run claim extraction; require real WRR queries, fetched evidence and explicit execution status before claiming research. |
| “WRR is only for fact-checking” | Research must also clarify concepts and expand mechanisms, history, comparison, applications, prerequisites, counterexamples and further reading. Keep expansion evidence-grounded and video-anchored. |

## Decision Tree

```text
Input contains exactly one supported video?
├─ No match → stop: unsupported source
├─ Multiple platforms/URLs → stop: ambiguous; ask for one video
└─ One platform
   ├─ Bilibili → BilibiliAdapter / legacy collector migration path
   ├─ YouTube → YouTubeAdapter + metadata/transcript provider
   └─ Douyin → DouyinAdapter + yt-dlp metadata + optional H200 media ASR

EvidenceBundle.status?
├─ ready → shared analysis → Writer → quality gates → human QA → one final note
├─ metadata_only → show metadata/diagnosis only; do not publish formal report
├─ auth_required → request authorized access; do not expose credentials
└─ unavailable → report safe reason; do not invent evidence
```

## Core Contract

External consumers receive versioned `EvidenceBundle` only. Platform-private responses, cookies, headers, signed media URLs and raw API bodies must not cross the adapter seam.

Required states:

- `ready`: stable identity + metadata + transcript + provenance hash; formal Writer allowed.
- `metadata_only`: metadata exists, transcript/media evidence does not; Writer blocked.
- `auth_required`: authorized session is required; Writer blocked.
- `unavailable`: source cannot be resolved safely; Writer blocked.

Only `ready` is publishable. Validate with `scripts/evidence_contract.py`; never bypass `is_publishable()`.

## Workflow

1. **Resolve one source**
   - Accept one Bilibili BV/full/short link, one YouTube watch/short/youtu.be link, or one Douyin share/direct link.
   - Reject zero or multiple platform matches.
   - If a duplicate-link index returns an existing report, open that exact note and verify its source before asking whether to reuse, update or redo it. A file or cache hit does not establish that the user sent the link twice. If the user questions its origin, trace the prior run or conversation and distinguish receipt, generation and delivery evidence; do not guess why a message was repeated. Apply an already-explicit redo choice without asking again.
2. **Collect typed evidence**
   - Bilibili: official subtitle → PlayURL audio → H200 ASR → local fallback; comments/danmaku remain audience signals. Distinguish subtitle authentication from media authorization: if subtitles require a session but the view/rights and PlayURL checks permit complete public media, continue through verified audio ASR rather than requesting login solely for captions. A short-link redirect may reveal the canonical BV even when the destination page returns a challenge; verify that identity through the view API before declaring acquisition blocked. Use third-party summaries only for discovery or explicitly labeled comparison; they do not establish what the original video says. When asked to rerun the Bilibili workflow, resume original-source acquisition from the last verified artifact rather than presenting a web summary as completed video analysis.
   - YouTube: yt-dlp metadata plus transcript provider; comments are typed audience signals.
   - Douyin: controlled yt-dlp metadata; optional single-video media download → H200 ASR; no private signer code.
3. **Validate bundle and media completeness**
   - Require schema compatibility, stable identity, provenance, safe errors and no private payload leakage.
   - Formal analysis stops unless status is `ready`.
   - For Bilibili, do not equate HTTP 200, a playable file, or nonempty ASR with complete evidence. Compare view-API duration, downloaded-media `ffprobe` duration, browser `<video>.duration` when used, and maximum danmaku time as an anomaly signal. A mismatch above `max(5s, 2%)` is `truncated_media` and blocks the formal Writer. See `references/bilibili-media-duration-integrity.md`.
   - If the aggregate collector finishes metadata/comments/danmaku but stalls or exits before subtitle `RESULT_JSON`, do not rerun successful steps and do not treat silence as success. Follow `references/bilibili-collector-stall-local-asr-recovery.md`: preflight rights/duration → PlayURL audio → headered download → `ffprobe` integrity → local MLX ASR with preserved segment timestamps → rebuild evidence.
   - For multi-P Bilibili items with a description-linked original source, bind evidence to one explicit P before collecting. Compare target-P duration, original metadata and subtitle/media end before treating the original as evidence; preserve this scope in the final note. See `references/bilibili-multipart-original-source-and-writer-fallback.md`.
4. **Choose the analysis path before research, then ground with WRR**
   - Choose the reader-facing layout now. Long interviews and rejected template-like drafts default to `editorial`: load [Interview editorial workflow](references/interview-editorial-workflow.md) **before analysis or research**, starting with full-transcript coverage and faithful reconstruction. If the same task has repeatedly failed fidelity or narrative review, apply the workflow's pre-draft checkpoints before committing to full prose; final author self-review alone is not enough. Follow its coverage → research questions → claim verification + knowledge expansion → evidence synthesis → argument spine → narrative → source-to-draft editorial QA sequence, not merely its writing format. `layout` is separate from legacy depth `mode`; never invent a CLI mode named editorial.
   - Preserve the existing claim/evidence/warrant/boundary framework. Judge one independently testable proposition at a time: split capability, performance, version, historical popularity and identity claims instead of hiding their different evidence states behind one mixed verdict. Test the speaker's stated scope; local index writes do not refute a claim limited to not sending platform messages.
   - Provide reviewers with readable source passages or explicit access to the cited originals, not only a research summary and URLs. When preserving source receipts, never save the tool's truncated display as complete source: fetch bounded line ranges, concatenate them, and check line count plus the relevant parser, such as `ast.parse` for Python. Keep the receipt in the run workspace, not as another user-facing note.
   - Preserve the speaker's actual degree of certainty, including absolute claims and contradictions across timestamps; separate “speaker's claim”, “verified evidence” and “analyst's recommendation”. Distinguish asserted present measurements from future targets; missing measurement evidence does not authorize recasting the speaker's numerical assertion as a metaphor or wish. Preserve the substantive answer to a host's challenge, not just the challenge and the analyst's safer recommendation. Separate certainty about an event from speculation about its mechanism: an unverified accusation can still be the speaker's definite assertion, and external uncertainty must not silently lower that attributed certainty. Do not silently replace a risky assertion with sensible advice, because this misrepresents the source. If original evidence overturns an earlier summary, explicitly correct the affected interpretation.
   - Treat Verification and Knowledge Expansion as equal research lanes: verify claims **and** clarify entities/concepts, mechanisms, history, comparison, applications, prerequisites, counterexamples, limitations and further reading.
   - For every `ready` video, target a lightweight grounding pass plus trigger-driven expansion when ambiguity, freshness, P0/P1 claims, academic context, conflicts or high learning value justify it.
   - Current runtime warning: `fact_check_wrr.py` claim extraction and `external_research.available` do not prove WRR ran. For the current editorial path, execute WRR at the Hermes orchestration layer using the temporary claim/source ledger and manual editorial acceptance record defined in the workflow. Native typed ResearchPlan/ResearchBundle artifacts are not prerequisites for this path; never claim native engine research validation. Design documents and implementation lessons do not establish installed capability.
   - Use official/first-party sources to verify external product, API, paper, policy and numeric claims; use independent sources for corroboration and social sources only as audience/community signals.
   - **Academic-community-web strengthening:** when the user asks for an academic / community / all-web expansion or “一轮强化”, run three labeled lanes: (A) `research` for peer-reviewed originals, reviews, and exact sample/design limits; (B) `grounding` for primary or authoritative current facts and claim corrections; (C) `community` for lived-experience signals only. If the community lane times out, make one constrained `discovery` recovery query for public forum threads; label it `degraded_success` and never upgrade anecdotes into factual support. Record selected routes, actual engines, failed fallbacks and evidence boundaries in the temporary evidence record; only fixed-section reports place this material in §8.
   - For every imported source, map **claim → evidence → mechanism/warrant → applicability boundary**. Bind each quoted evaluation to the exact work, result or version its author discusses; a statement about the author's own work must not become an evaluation of a competing work. Preserve the design type, sample/context, and causal limit whenever it changes the conclusion; an abstract link alone is not a citation decoration.
   - Before freezing a research-dependent outline, check for corrections and substantive technical critiques of its load-bearing cases. Update the affected reasoning, not just the bibliography, because new evidence can change what the proposed verification mechanism actually establishes. Separate machine acceptance, faithful correspondence to the original problem, and human interpretability; none automatically proves the others. Scope criticism to the versions and claims actually examined rather than declaring the whole result refuted.
   - Search snippets are discovery metadata, never evidence. Knowledge expansion must remain anchored to video evidence/topics/entities and must not become unrelated padding.
   - **Visual strengthening:** when charts or analysis-chain reinforcement are requested, add at least one mechanism diagram (Mermaid flowchart or sequence) plus one decision matrix/table that compresses evidence—e.g. disclosure depth × reciprocity/capacity. Visuals must expose interaction paths and boundary conditions, not ornamentally restate headings.
   - **Fixed-section depth-mode discipline:** choose the report gate from evidence budget, not demanded volume. A richly sourced note may remain `condensed` when `full` would force unsupported padding; disclose this decision and still run `--claim-first` plus the publishable gate. If action-item gates accept only bullets/numbered lines, put `[E#]`, `[C#]`, or a timestamp inside each action item rather than relying on a surrounding table.
   - Engine-development instructions belong to **Developer Verification**, not this ordinary video-analysis run. Use the editorial ledger for the current orchestration path.
5. **Write adaptively**
   - Write using the layout and research workflow selected in step 4. Organize the prose around the reader's unresolved questions and evidence-supported explanatory judgments, not around successive speaker claims or source citations. Use those judgments to select and combine material across the video; do not postpone synthesis to chapter-end summaries while the body remains a topic catalogue. Coverage is a backstage safeguard: give important source positions a faithful destination or a justified omission, not a mandatory turn in the prose. Never use omission to hide a position that changes the article's interpretation of the speaker. Research must develop understanding, not become a repeated “speaker says → source corrects → caveat” paragraph recipe.
   - This layout routing takes precedence over fixed-heading instructions in older recovery/writer references; their acquisition and evidence rules remain applicable. Use the fixed §§0–8 layout only for a consumer that explicitly requires it or when the user requests that report format. Do not repeat insights in separate deep-dive, graph and action sections merely to satisfy headings. For editorial layout, use semantic chapters and the manual acceptance record in the linked workflow; legacy fixed-section scripts are not applicable and must not be reported as passed.
   - Prefer insight density over fixed length.
   - Let `--mode auto` choose from evidence budget: short/low-evidence inputs may become provider-free `sparse`; richer short/tutorial content remains `condensed`; interviews/keynotes remain `full`.
   - Sparse §§1/3/4/7 must stay deterministic, transcript-grounded, and exact-fidelity protected. Never pad sparse evidence to satisfy full-mode quotas.
   - Give material video quotations, disputed strong assertions and source-dependent synthesis a small number of real timestamp anchors with canonical video jump links where supported, or readable source/time references otherwise. Do not invent precise times from collapsed ASR or impose per-paragraph quotas; an internal coverage ledger cannot substitute for reader-accessible provenance.
   - Never dump long transcript blocks or inflate sparse social data.
   - A CLI Writer is not successful merely because it starts: require a real Markdown artifact, terminal result and gateable output. If it is silent/empty/partial, fail closed; do not retry the same OMP-backed writer path as generic prose generation. For manual evidence-writing fallback and final verification, see `references/bilibili-multipart-original-source-and-writer-fallback.md`.
6. **Run release gates**
   - Evidence readiness, source fidelity, provenance, privacy and editorial acceptance remain required for every layout. Layout changes never relax these requirements.
   - For fixed-section engine reports, run report structure, claim/evidence and publishable gates. For `editorial` layout, follow the coverage and evidence audit in `references/interview-editorial-workflow.md`; `verify_report.py` and `verify_publishable_report.py` currently recognize only the legacy layout. Do not claim automated publishable certification for editorial prose.
   - When optimizing this skill, keep the deliverable at the skill/workflow level: diagnose the failure and compare candidate mechanisms before repeatedly rewriting a full report. Use short, evidence-matched probes to expose tradeoffs, not to certify a candidate. Recommend a direction from actual outputs; do not ask AlexCai to choose internal method labels. Ask only when a concrete, evidenced product or scope tradeoff needs user judgment. Treat read-only research authorization as research, not permission to implement the candidate.
   - Changes to bundled engine code still require the blocking corpus and the Pi accepted-gold regression; a prose-only instruction/template edit requires linked-resource validation and a realistic task exercise, not unaffected engine tests.
7. **Human QA and save**
   - Read the actual delivered Markdown after any delivery layer injects metadata or runtime tables. Draft review does not validate later-generated content: check that injected costs cover only recorded calls, that unknowns remain unknown, and that “no degradation” does not contradict disclosed fallbacks. Judge source fidelity, research support, learning gain, argument progression and reader experience separately; passing the first two does not establish the others. A Writer `status=ok`, evidence gate, or publishable gate is not editorial acceptance. When the user rejects the prose as a topic-by-topic account, withdraw the affected narrative verdict even if independent reviewers passed it; retain unaffected factual checks instead of calling the whole result either good or worthless.
   - **Reject-and-rewrite threshold:** if the draft retains template instructions, mistakes route detection for completed WRR, imports unrelated theories or the user's private tool stack, dumps ASR, produces acronym/common-word “knowledge graphs,” or treats generation volume as retention/payment proof, rewrite from frozen evidence instead of polishing the skeleton.
   - Before finalizing a reposted tutorial or branded interview, compare the title/description's model version, speaker affiliation, numerical claims and promised mechanism with the actual transcript. Anchor material mismatches to source timestamps; treat uploader wording as attribution, not proof. Separate the title hook from the runtime's dominant subject, and distinguish feedback that revises one output from demonstrated changes to reusable prompts, tools, control logic or model parameters. Do not infer that a named product does not exist, that the speaker has a particular employer, or that sponsorship was undisclosed merely because the video does not establish it. For prepended introductions and original-source matching, follow `references/bilibili-multipart-original-source-and-writer-fallback.md`.
   - Keep social arithmetic explicit: platform total count, collected root comments, collected replies, and sampled danmaku are different quantities. Social data is audience signal only.
   - Fixed-section full-mode manual rewrites must preserve the deterministic report contract: §1 structured logic chain; §3 `### 💡 洞察`; §4 `### 模块 N`; §5 separate timestamped blockquote groups; §7 `### 独特价值` / `### 局限与偏见` / `### 可行动项`. The static gate counts `- ` bullets for value and limitation items.
   - For fixed-section reports after the final edit, run `verify_report.py <report> --mode <selected-mode> --claim-first` and `verify_publishable_report.py <report>`; use `full` only when that is the selected report mode. Inspect each gate's actual verdict and failed items, not just the shell exit code, because a combined command can hide an earlier failure. Repair missing analysis with substantive mechanisms or reasoning—not keyword stuffing—then rerun the affected gates. Scan for template residue, private paths, unsupported extrapolation, user-stack contamination, transcript dumping and broken wikilink stems.
   - If acquisition is slow or blocked, report the four decisive facts early: advertised duration, actual acquired duration, completed evidence steps, and whether any Vault note was written. Do not leave the user with silent tool work.
   - A partial transcript may support an explicitly time-bounded temporary summary only; never use metadata, comments or danmaku to fill missing media, and never save it as the unqualified formal note without explicit user direction.
   - If H200/Whisper returns one transcript chunk and timestamps collapse to `0:00`, follow `references/bilibili-single-chunk-asr-salvage.md`: supplement official metadata and rewrite instead of polishing the bad skeleton; preserve real timestamp uncertainty and use real file stems for wikilinks. Only fixed-section layout preserves the §§0–8/2.5 contract and reruns both legacy gates after an authorized final Vault edit. Editorial layout uses its manual evidence and semantic acceptance instead. If the aggregate `info` is null or no acquired media asset survives, use `references/bilibili-metadata-missing-duration-integrity.md` to reconstruct metadata through View API and verify duration through a temporary PlayURL audio probe before writing.
   - For the detailed branded-interview + WRR rewrite sequence, use `references/bilibili-branded-interview-wrr-rewrite-pattern.md`.
   - Resolve the Vault lifecycle route before writing: read its current control files, then use the ingest/gate workflow when required. A finished article may remain a `candidate` in staging; editorial acceptance does not authorize direct core writes or imply promotion. Legacy video-folder examples do not override current governance. Report the actual saved location and lifecycle state.
   - Save exactly one user-facing note unless source artifacts were explicitly requested. Run `qmd update && qmd embed` only after the last content/link edit, then query the title to verify retrieval.
   - Match evidentiary verbs to the acquired modality: audio ASR supports “the author says/describes”, not “the screen shows” or “the invoice was verified”. Inspect the relevant frames before making visual claims. For implementation case studies, distinguish reported cash spend from total operating cost, and repeated knowledge preparation from model-provider caching; plausible mechanisms do not establish the author's actual accounting or architecture.

## Configuration

Canonical ASR variables:

```text
VIDEO_ANALYSIS_ASR_ENDPOINT
VIDEO_ANALYSIS_ASR_LANGUAGE=zh|en|auto
VIDEO_ANALYSIS_ASR_PROVIDER=auto|h200_asr|whisper_cpp|mlx_whisper
VIDEO_ANALYSIS_ASR_MODEL
VIDEO_ANALYSIS_ASR_MODEL_PATH
```

`BILI_ASR_*` variables are temporary deprecated aliases. Do not expose endpoint values, credentials or local model paths in published reports.

## Developer Verification

### Research-engine changes only

These are development/audit invariants, not tasks or artifact requirements for an ordinary video-analysis run. First inspect the installed code; historical implementation lessons do not prove these interfaces exist in this checkout.

- Read `references/wrr-research-knowledge-expansion-design-20260713.md` for current-vs-target semantics and `references/wrr-artifact-slice-implementation-lessons.md` for S0–S4 lessons: final-ClaimBundle binding, late-writer correlation, capability/execution separation, all-mode ClaimBundle, semantic identity, one-shot provider, plan-bound replay and raw-only WRR orchestration.
- When implementing ResearchPlan, build it only after report assembly installs the final ClaimBundle. Tests must force initial/final hashes to differ and prove final binding through the real assembly path.
- Bounded fixture/release research allocates one primary candidate per in-scope claim before second independent candidates required by P0/P1. Do not raise caps, relax policy or slice away tail claims to hide budget pressure. Test tail P2/P3 coverage, P0/P1 independent corroboration and the source cap; the gate passes only when policy minima fit. See `references/bounded-research-fixture-scheduling.md`.


From this skill directory:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3.12 -m pytest -q -p no:cacheprovider tests
python3.12 -m py_compile scripts/evidence_contract.py scripts/platform_router.py scripts/adapters/*.py scripts/providers/*.py
python3 scripts/run_quality_gate.py --corpus-manifest references/p6r-corpus-manifest.json --lane blocking --json
```

Detailed legacy collector, Writer, gate and historical design records live under `references/`. Historical references may retain the old skill name as provenance; active commands and mappings must use `video-analysis-engine`.

## Correlated Multi-Video Synthesis (explicit user request only)

The engine remains **single-video at the evidence-run level**. However, when the user explicitly supplies a small set of closely related videos and asks for **one integrated final artifact**, do not reject the work merely because the final synthesis has multiple inputs:

1. Resolve and collect each video **independently** using the normal one-video adapter workflow; each must independently validate as `ready` before it can support the final report.
2. Do not create a formal standalone note for each source unless the user asked for those notes. Keep source bundles/transcripts as temporary evidence artifacts only.
3. Write exactly one integrated note only after all included sources are ready. Its metadata/evidence section must identify every canonical URL, duration, transcript provenance, and the role each source plays in the synthesis.
4. Never use one video's metadata, comments, or transcript to repair missing evidence for another. If any source is not `ready`, either omit it with an explicit boundary or stop for user direction.
5. Preserve per-video timestamp citations in the unified argument; distinguish a source's direct claim from the cross-video synthesis.
6. Treat this as a bounded synthesis, not playlist/channel/batch crawling. Default to two sources; ask before expanding beyond a small, user-defined set.

See `references/correlated-multi-video-synthesis.md` for the evidence and release sequence.

## Scope Boundaries

- One input video per **evidence run**; a small explicitly requested correlated set may produce one integrated note under the procedure above.
- No creator-page, profile, playlist, feed or batch crawling.
- No Feishu export in v4 initial release.
- No copied/private `a_bogus` implementation.
- No formal report without transcript evidence.
- No second core implementation under the old skill name.

## ✅ Verification Checklist

- [ ] Exactly one supported source and one canonical identity?
- [ ] `EvidenceBundle` validates and status is `ready` before Writer?
- [ ] Private payloads, credentials and signed URLs excluded?
- [ ] Claims trace to transcript or verified first-party sources?
- [ ] WRR capability, attempted execution, successful execution and validated evidence are reported as distinct states?
- [ ] Knowledge expansion adds source-grounded understanding—not unrelated padding—and remains anchored to video evidence/topics/entities?
- [ ] Search snippets and social signals are prevented from independently supporting factual claims?
- [ ] Applicable layout checks run with real output, editorial acceptance recorded, and inapplicable legacy checks explicitly distinguished? Engine-code changes additionally require blocking-corpus verification.
- [ ] Final Markdown manually checked for readability, skeleton residue and transcript dumping?
- [ ] Exactly one user-facing note saved, with no unauthorized batch/export side effects?
