# Two-Phase Review → Polish Pattern

> 2026-05-31 · Session: 银杏汇小程序方案审查与优化

## When to use

When the user wants a document reviewed and then a clean, standalone deliverable produced from the review findings. Common for:
- Plan documents → reviewed version → clean delivery version
- Proposals → expert review → polished final draft
- Design specs → multi-lens audit → implementation-ready spec

## Pattern

### Phase 1: Agent Team Multi-Lens Review

1. Write context file to `/tmp/cc-{task}-review.md` with:
   - Source document path
   - 3 lens definitions (e.g., Product/UX, Technical Architecture, Governance/Compliance)
   - Per-lens scope & timeout (8 min)
   - Output language (Chinese)
   - Output path to Obsidian vault

2. Launch CC with agent team:
   ```
   Read /tmp/cc-{task}-review.md and execute the full agent team review.
   Start all 3 lens workers in parallel. Each worker timeout: 8 minutes max.
   Output language: Chinese. Output to <path>
   ```

3. Output format: Part A (review report) + Part B (optimized plan v2)

4. Expected cost: ~89k tokens total (workers: ~67k + leader: ~14k), ~9 minutes

### Phase 2: Single CC Polish (Clean Deliverable)

1. Write context file to `/tmp/cc-{task}-polish.md` with:
   - Path to Phase 1 output
   - Instructions to strip all review traces (no Part A, no severity markers, no comparison language)
   - Additional requirements (homepage design, permission matrix, etc.)
   - Output path for clean version

2. Launch CC without agent team (single CC, simpler task):
   ```
   Read /tmp/cc-{task}-polish.md and produce the optimized standalone plan document.
   ```

3. Output: clean, self-contained, directly deliverable document

4. Expected cost: ~12k tokens, ~3.5 minutes

## Key differences between phases

| Aspect | Phase 1 (Review) | Phase 2 (Polish) |
|--------|-----------------|-----------------|
| CC mode | Agent team (3 workers) | Single CC |
| Input | Raw plan document | Phase 1 review output |
| Output | Review report + v2 plan | Clean standalone deliverable |
| Tone | Critical, annotated (🔴🟡🟢) | Confident, decisive, self-contained |
| Tokens | ~89k | ~12k |
| Time | ~9 min | ~3.5 min |

## Context file template — Phase 2

```markdown
# Task: Produce clean deliverable

## Input file
`path/to/phase1-output.md` (contains Part A review + Part B v2 plan)

## Task
Based on Part B, produce a clean, standalone, directly deliverable document.

## Requirements
1. Strip all review traces: no Part A, no severity markers, no comparison language
2. Retain and strengthen all Part B content
3. Add any missing sections (homepage design, permission matrix, etc.)
4. Use decisive language: "Phase 1 implements X" not "X should be in Phase 1"
5. Output to specified path with Obsidian YAML frontmatter
```

## Pitfalls

- **Phase 2 must use a DIFFERENT context file** — pointing to Phase 1 output as input, not the original source
- **Phase 2 should NOT use agent team** — it's a simple extraction+polish task, single CC is faster and cheaper
- **Don't skip Phase 2** — the review output is too dense for direct delivery; a clean version is always needed
