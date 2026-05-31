# Claude Code Skill — Changelog

> All notable changes to `claude-code` skill for Hermes Agent.

---

## v3.5.0 (2026-05-31) — Effort Routing + Agent Team Enhancement

### Added
- **🧭 Smart Effort Routing** — signal-based decision tree replacing simple "策略建议"; default floor = `high`
- **🧩 Agent Count & Splitting Principles** — "let CC decide count, break by concern not by file"
- **🚦 Execution Mode Selection** — single CC vs Agent Team vs parallel multi-CC decision table
- **⚙️ Effort Practical Config** — CLI flag mapping, `/effort` pitfalls, cost ratios (max≈3×high)

### Changed
- **Core Rule #2** enhanced — agent count self-determined, concern-based splitting
- **`## 🧠 Model & Effort Level`** section restructured: startup → five levels → in-session switch → smart routing → practical config

### Execution
- 3 parallel agents drafting independent content blocks → Leader serialized integration to avoid file conflicts
- Opus 4.8 max effort · 10m40s · ↓42.5k tokens

---

## v3.4.0 (2026-05-31) — Opus 4.8 + Model & Effort

### Added
- **`## 🧠 Model & Effort Level`** — Opus 4.8 support, five effort levels (`low`–`max`), `/effort` in-session switching
- **`references/two-phase-review-polish.md`** — 两阶段审查→优化模式: Phase 1 agent team review → Phase 2 single CC polished output
- **`references/taste-skill-mobile-prototype.md`** — CC + taste-skill 移动端原型图快速生成

### Changed
- Version bump 3.3.0 → 3.4.0
- References table updated with two new patterns

---

## v3.3.0 (2026-05-30) — Stability Optimization

### Added
- **Rule #0: 🛑 占用检测** — mandatory CC occupancy scan before every invocation
- **Multi-Agent Coordination Protocol** (§ 🤝) — occupancy detection, decision matrix, session naming convention
- **Enhanced Progress Reporting** — `references/progress-reporting-enhanced.md` with visual state emojis, worker tree, token tracking
- **Session isolation rules** — per-agent `hermes-cc-{profile}-{ts}` naming, independent workdirs

### Changed
- **Decision tree redesigned** — removed print mode branch; only tmux + agent team
- **Core Rules rewritten** — 10 stability-first rules (was 10 mixed-mode rules)
- **Pitfalls compressed** — 60+ lines of verbose pitfalls → 16-line compact table with one-liner fixes
- **SKILL.md slimmed** — 402 → 290 lines (-28%)
- **Bypass permissions** — simplified from 16 lines to 3

### Removed
- Print Mode - One-Shot Tasks section
- PR Review Pattern section
- Old Interactive Mode example (Shift-Tab / hermes-claude-longterm)
- Smoke test connectivity script (kept basic version check)
- Verbose pitfall explanations (moved to references)

### Fixed
- **Pitfall #18** — revised from "daemon singleton" theory to verified "session sharing" root cause, with `--session-id UUID` validation
- **Workdir isolation** — confirmed that same workdir CC auto-resumes session (2026-05-30 test)

---

## v3.2.0 (2026-05-29) — Session Isolation

### Added
- `--session-id` UUID print-mode isolation (verified with 2x test)
- `--fork-session` for interactive mode branching
- `--dangerously-skip-permissions` bypass documentation
- CC session storage mechanism: `~/.claude/projects/<hash>/<uuid>.jsonl`

### Fixed
- HOME override for profile isolation (`HOME=/Users/alexcai`)
- TCC sandbox fallback (`cp` to `/tmp/`)

---

## v3.1.0 (2026-05-28) — Initial Stability

### Added
- Worker stall detection (fake-dead vs truly-dead)
- Fact-Forcing Gate recognition
- Progress reporting protocol (📡 30-60s polling)
- Agent team context file standards
- Schema persistence verification pattern
- Multi-round `/clear` protocol

### References Created
- `worker-stall-detection.md`
- `worker-true-stall-no-disk-output.md`
- `cc-agent-team-content-research.md`
- `cc-agent-team-parallel-implementation.md`
- `post-deploy-verification-pattern.md`
- `cc-session-isolation.md`
- `home-and-sandbox.md`
