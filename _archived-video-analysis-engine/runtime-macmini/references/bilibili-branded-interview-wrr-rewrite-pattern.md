# Branded interview + WRR rewrite pattern

Use this when a long-form video opens with a broad industry claim but spends most of its runtime promoting one product or platform.

## Failure pattern

A technically valid Writer draft may still be unusable when it:

- preserves `_目的：..._` or other template instructions;
- treats `external_research.available` / `wrr_local detected` as completed research;
- imports unrelated theories, the user's tool stack, or generic knowledge-graph terms;
- reports generation volume as proof of retention, reuse, payment, or ecosystem health;
- paraphrases long ASR chunks instead of making a claim/evidence/boundary argument;
- follows the fixed §§0–8 headings only nominally, so release gates cannot identify §1 logic, §3 insights, §4 modules, §5 quotes, or §7 actions.

Reject this draft rather than polishing it locally.

## Rewrite sequence

1. **Establish source integrity**
   - Compare platform/API duration and browser player duration.
   - Verify the ASR reaches the closing segment; record transcription corrections for product names and technical terms.
   - State social sample boundaries separately: total platform count vs actually collected roots/replies.
2. **Identify the real editorial frame**
   - Separate the title's hook from the runtime's dominant subject.
   - For product-led interviews, describe the product-promotional structure without asserting an undisclosed sponsorship unless independently proven.
3. **Run WRR at the orchestration layer**
   - Choose the mode before searching (`grounding` for valuation, dates, funding, product-scale claims).
   - Complete local-first checks, entity grounding, Exa + Brave cross-check, then fetch first-party pages.
   - Preserve four distinct states: capability detected, execution attempted, execution succeeded, evidence validated.
4. **Adjudicate claims**
   - Confirm dates/numbers from first-party sources.
   - Downgrade causal stories (for example, "valuation rose because of coding") when evidence supports only correlation or one contributing factor.
   - Treat product generation counts as supply metrics, not retention or economic proof.
5. **Rewrite to the formal contract**
   - §1: table/mermaid/timeline logic chain.
   - §2 and §2.5: danmaku/comments as audience signals with sample boundaries.
   - §3: at least 3 `### 💡 洞察` subsections, each claim + evidence + boundary.
   - §4: at least 3 `### 模块 N` subsections; deepen only with source-grounded mechanisms.
   - §5: at least 5 separate blockquote groups with timestamps when full evidence supports them.
   - §6: meaningful concepts and relations; no acronym/common-word dump.
   - §7: `### 独特价值`, `### 局限与偏见`, `### 可行动项`; use `- ` bullets for value/limitations because the deterministic gate counts bullet items.
   - §8: video evidence, WRR sources, execution status, and unresolved gaps.
6. **Run both gates and human QA**
   - `verify_report.py --mode full`
   - `verify_publishable_report.py`
   - Scan for template residue, private paths, unsupported extrapolation, user-stack contamination, transcript dumping, and broken wikilink stems.
7. **Index only after the final edit**
   - Run `qmd update && qmd embed`, then query the note title to verify retrieval.

## Durable interpretation rule

For "ordinary person opportunity" videos, rank conclusions by certainty:

1. current personal productivity / lower prototyping cost;
2. emerging leverage for domain experts;
3. uncertain creator-platform opportunity;
4. subsidies or "everyone can make money" as non-durable until retention and payment data exist.
