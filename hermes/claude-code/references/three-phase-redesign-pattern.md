# Three-Phase Redesign Pattern — Hermes↔CC Architecture Overhaul

> 2026-06-02 实战验证：早新闻 + WRR 一体重构，14 文件改动，4 agent 并行，P0→P1a→P1b 全链部署。

## When to Use

Large-scale architecture redesign where:
- The current design is broken and needs root-cause analysis before any code changes
- Multiple files across different components (skill + dependency + references)
- Requires domain knowledge verification (not just code), e.g. testing API behavior
- Staged deployment: each phase independently deployable and verifiable

## The Three Phases

### Phase 1: Discussion (Hermes↔CC 双向拷问)
**Goal**: Align on design before touching any code.

1. Write a comprehensive context file to `/tmp/cc-context-{task}.md` (use file-passing, Pitfall #33)
2. Hermes and CC enter multi-round discussion using the Discussion Protocol (see SKILL.md § Discussion Protocol)
3. CC reads context → states its understanding → identifies tensions and contradictions
4. Hermes responds, CC refines → converge on a concrete plan
5. Deliverable: 15-20 bullet plan with prioritized phases (P0→P1→P2)

**Key for this phase**: CC should identify version drift and incorrect assumptions in the context file. The context file is a draft, not ground truth. CC's first job is to verify it.

### Phase 2: Scouting/Verification
**Goal**: Verify assumptions against real code and runtime state before coding.

1. CC reads actual deployed code (not just context file description)
2. CC tests assumptions empirically (e.g., curl APIs, grep files, check versions)
3. CC identifies version drift: SKILL.md vs references vs actual deployment
4. CC discovers the real root cause (often different from the hypothesized one)
5. CC recalibrates the plan based on findings
6. Deliverable: verified root cause + recalibrated execution scope

**Key for this phase**: The scouting phase often reduces work dramatically. In this session, it discovered that WRR was already at v3.9 (the "fix" was already done in SKILL.md) — the real problem was in references. This turned a "rewrite WRR" into "sync references to SKILL.md".

### Phase 3: Agent Team Execution
**Goal**: Execute the recalibrated plan in parallel.

1. CC scouts file structure → determines edit boundaries
2. CC deploys agent team with clear per-agent scope (按关注点拆，不按文件拆)
3. Leader handles cross-cutting concerns (SKILL.md drift, sync scripts)
4. Each phase deploys independently after verification
5. Acceptance tests: grep for old patterns, verify runtime == source

## Anti-Patterns from This Session

### Version Drift in Progressive Disclosure
**Problem**: SKILL.md (v3.9) says "SearXNG is fallback", but `references/research-modes.md` still says "SearXNG 默认起手". Agent reads the more specific reference file first → follows the wrong path.

**Detection**: After scouting, grep ALL references for the deprecated pattern, not just SKILL.md. 

**Fix**: Align references to SKILL.md before deploying.

### Socket Error Silent Data Loss
**Problem**: CC's Write tool reported success but socket disconnected mid-write → file not actually created. CC assumed it succeeded, had to be told to verify.

**Detection**: After any API/socket error, explicitly `stat` the target file to verify it was written.

### Watching CC Too Long Without Intervention
**Problem**: CC spent 4+ minutes "almost done thinking" on deployment logic. The thinking was real but the session was burning tokens.

**Mitigation**: If CC is "almost done" for >3min with no tool calls and no token growth, send `Enter` to trigger. If still stuck, break the task into smaller steps.

## Files Produced in This Session
- `~/code/jz-skills/hermes/news-assembly/SKILL.md` — new sub-skill
- `~/code/jz-skills/hermes-3S6M-profiles/regent/morning-news-briefing/SKILL.md` — slimmed
- `~/code/jz-skills/hermes/web-research-router/references/*.md` — 9 files aligned
- `~/code/jz-skills/hermes-3S6M-profiles/regent/morning-news-briefing/references/search-workflow.md` — rewritten
- `~/code/jz-skills/deploy/sync-all.sh` + `sync-back.sh` — added news-assembly mapping
