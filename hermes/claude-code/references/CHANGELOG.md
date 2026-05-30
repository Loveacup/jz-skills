# Claude Code Skill — Changelog

> All notable changes to `claude-code` skill for Hermes Agent.

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
