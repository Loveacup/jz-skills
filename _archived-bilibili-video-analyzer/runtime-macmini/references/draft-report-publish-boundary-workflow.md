# DraftReport → PublishedMarkdown boundary workflow

Use this when changing the Bilibili video-analysis content engine, especially when skeleton/debug output risks being mistaken for a publishable Obsidian note.

## Durable pattern

Separate artifacts explicitly:

```text
AnalysisInput
→ analyze_video()
→ DraftReport                 # non-publishable, may contain skeleton/debug sections
→ assemble_draft_report_slice # fills selected draft_sections only
→ render_draft_markdown       # non-publishable preview for human/CI inspection
→ publish_markdown            # creates PublishedMarkdown only after publish gate passes
→ PublishedMarkdown           # only artifact allowed to become formal B站笔记_*.md
```

## Slice order that worked

1. **P0/P1 publish gate first**
   - Add a strict publishability verifier before improving writers.
   - Formal `B站笔记_*.md` outputs must fail closed if skeleton/debug content remains.
   - Keep the existing release gate as an engineering gate; do not rename it as content-quality approval.

2. **Artifact boundary second**
   - Introduce `DraftReport(publishable=False)` and `PublishedMarkdown(publishable=True)`.
   - Keep `render_markdown()` / `render_debug_markdown()` as legacy/debug string renderers.
   - Require `publish_markdown()` to run the publish gate before producing `PublishedMarkdown`.

3. **Writer slices third**
   - Add deterministic draft sections before broad LLM generation.
   - Good deterministic sections:
     - §1 logic chain table from transcript `logic_candidate` evidence.
     - §5 short highlight blockquotes from transcript `quote_candidate` evidence.
     - §6 conservative knowledge graph from transcript `knowledge_candidate` / `application_candidate` evidence only.
   - Route existing validated LLM writers (§3/§4/§7) into `DraftReport.draft_sections` only when an explicit provider is passed.
   - Provider default must remain `None` so unit tests and normal assembly do not network or spend tokens.
   - For §6, keep the extractor intentionally conservative: known verbatim concepts → Obsidian wikilinks, co-occurrence relation chains, and actionable/application bullets. Do not infer hidden entities, run NER, search the web, or call LLMs in this deterministic slice.

4. **Preview composer fourth**
   - Add `render_draft_markdown(draft)` as a non-publishable inspection surface.
   - It should overlay `draft_sections` onto report-plan order, keep unfilled sections as skeleton, keep §0/§8 Source Appendix visible, and emit an explicit marker such as:

```html
<!-- artifact_kind: draft_markdown_preview; publishable: false -->
```

## TDD acceptance shape

For each slice, write RED tests first:

- publish gate rejects skeleton/debug formal note paths;
- `DraftReport` is non-publishable and `PublishedMarkdown` only comes from publish-gated promotion;
- deterministic section writer produces structured bodies, not raw transcript dumps;
- §6 knowledge graph extractor filters to transcript `knowledge_candidate` / `application_candidate` evidence, emits `### 核心概念` / `### 关系链` / `### 可落库/可行动项`, uses `[[wikilinks]]`, and returns a skeleton placeholder on empty evidence;
- LLM section assembly only calls provider when explicitly passed;
- bad provider output degrades to placeholder + warning, never `PublishedMarkdown`;
- preview renderer does not mutate legacy `render_debug_markdown()` / `render_markdown()` behavior.

## OMP / audit checklist

Ask audit to verify from current diff and real command output:

- no default network/LLM call was introduced;
- legacy debug renderer remains compatible unless intentionally changed;
- formal save path still fail-closes through publish gate;
- targeted tests and release gate both pass;
- any `concern` audit result is either fixed or explicitly justified with extra diff/test evidence before commit;
- if OMP returns invalid/non-JSON output, reject that run as format failure and rerun a shorter JSON-only audit package; do not accept or cite the malformed audit.

## Pitfalls

- Do not improve prompts before adding a publish gate; better prompts cannot prevent skeleton from being saved as formal notes.
- Do not treat `verify_report.py` / coherence / OMP pass as publishability. They are engineering checks unless the publish gate is explicitly included.
- Do not make preview rendering return `PublishedMarkdown`; preview is for inspection only.
- Do not let provider-backed writer assembly run by default in deterministic tests.
