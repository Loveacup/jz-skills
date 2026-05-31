# Agent Team Multi-Lens Review Pattern

> 2026-05-31 established: CC agent team with 3 parallel lens workers for deep plan/design review.

## When to use

Use when reviewing a plan, design, absorption analysis, or architecture decision that benefits from multiple independent perspectives. NOT for simple code review or single-aspect tasks.

## Pattern

### Step 1: Write context file

Write a self-contained markdown task file to `~/.hermes/tmp/cc-{task-slug}.md`. Must contain:

- **Task description**: what to review, what to produce
- **Background**: all context the workers need (project details, existing architecture, the plan being reviewed)
- **Lens definitions**: 2-3 lens roles, each with specific scope and expertise
- **Constraints**: output path, format requirements, timeout per worker, language

### Step 2: Define lens roles

| Lens count | When to use | Example lenses |
|-----------|-------------|----------------|
| 2 | Simple review | Architecture + UX |
| 3 | Complex review (recommended) | Architecture & Engineering, Content & UX, Compliance & Governance |
| 4+ | Very broad review | Split architecture into sub-lenses (API, Data, Security) |

Each lens needs:
- Clear scope boundary (what it covers, what it doesn't)
- Domain-specific instructions (what to look for, what to ignore)
- Worker timeout (8min max for deep analysis, 5min for focused)

### Step 3: Launch all workers in parallel

In the CC tmux session, send a single command that:
- Reads the context file
- Starts all lens workers simultaneously
- Sets per-worker timeout

Example command:
```
Read ~/.hermes/tmp/cc-skill-absorption-review.md and execute the full agent team review. Start all 3 lens workers in parallel. Each worker timeout: 8 minutes max. Output to /path/to/output.md
```

### Step 4: Monitor with full progress reporting

Follow Post-Send Protocol from claude-code SKILL.md. Each polling cycle report:

```
📡 CC Agent Team [Xmin]
  ⚡ Leader: <status> · <token count>
  ├─ 🔵 worker-1: <elapsed> · <tool uses> · <tokens>
  │   └─ <current action description>
  ├─ 🔵 worker-2: <elapsed> · <tool uses> · <tokens>
  └─ 🔵 worker-3: <elapsed> · <tool uses> · <tokens>
```

### Step 5: Leader synthesis phase

When workers return, leader enters synthesis. Key signals:
- Worker count drops → workers completed and returned
- Leader token count jumps significantly → processing worker output
- Leader flowing for 3-5+ minutes → deep synthesis in progress (normal for 3-lens review)

Do NOT interrupt during synthesis. The leader is combining independent findings and resolving conflicts.

### Step 6: Verify output

After leader completes:
- Check output file exists at specified path
- Read and verify it covers all lenses
- Report to user with key findings summary
- Clean up tmux session

## Worker timeout strategy

- **<5min**: focused, single-aspect workers (code review, specific audit)
- **8min**: deep analysis workers (architecture review, compliance audit) — RECOMMENDED
- **>8min**: only for very broad research tasks with explicit user approval

Workers that timeout get flagged in the report. Leader synthesizes from completed workers only.

## Cost characteristics

Two data points from real sessions:

### Deep analysis (multi-tool workers)
From 2026-05-31 session (3 lenses, 127-skill library absorption review):
- Lens 1 (Architecture): 34,852 tokens
- Lens 2 (UX): 46,111 tokens
- Lens 3 (Compliance): 33,125 tokens
- Leader synthesis: ~24,000+ tokens
- Total: ~138,000+ tokens
- Wall time: ~14 minutes

### Read-then-analyze (single-tool workers)
From 2026-05-31 session (3 lenses, 1913-line plan document review):
- Lens 1 (Product UX): 21.9k tokens
- Lens 2 (Tech Architecture): 22.3k tokens
- Lens 3 (Governance): 22.7k tokens
- Leader synthesis: ~13.8k tokens
- Total: ~89,000 tokens
- Wall time: ~9 minutes
- Output: 648 lines (37KB)

**Pattern insight:** When workers only need to Read + analyze (no multi-tool chains), they complete in ~2-3min each and leader synthesis dominates (~5min). Deep multi-tool workers (code search, file traversal, etc.) drive much higher token counts and wall time. Budget accordingly.

## Pitfalls

- **Worker thinking ≠ stalling**: Workers with unchanged tool count for 2-3 minutes may be deep-thinking, not stalled. Only flag as stalled if no tool change for >5 minutes AND no token increase.
- **Lens count vs cost**: Each additional lens adds ~30-50K tokens. 2 lenses sufficient for most reviews, 3 for governance/compliance-heavy tasks.
- **Context file quality**: Workers only know what's in the context file. Missing background → incomplete reviews.
- **Output format**: Workers default to English regardless of user language preference. Specify output language explicitly in context file if needed.
