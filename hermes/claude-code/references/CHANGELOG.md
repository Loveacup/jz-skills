# Claude Code Skill — Changelog

> All notable changes to `claude-code` skill for Hermes Agent.

---

## v4.0.0 (2026-06-02) — Discussion Protocol + Debt Cleanup + Architecture

### Added
- **🔥 讨论协议章节（Discussion Protocol）** — Hermes↔CC 双向拷问：grill pattern（逐问 / 带推荐答案 / 先查事实）+ 多轮辩证立场更新 + 共识终止条件 + 讨论简报模板。吸收自 `mattpocock/skills` 的 grill-me/grill-with-docs 与 Du et al. 2023 multiagent debate、Wang et al. 2023 self-consistency
- **References 收编** — home-and-sandbox / cc-agent-team-document-audit / hermes-research-to-cc-strategic-insight / claude-octopus-upstream / literary-rewrite-pattern 5 个孤儿纳入 References 表

### Changed
- **🏗️ 废除共享 longterm session** — Decision Tree、Session 命名表、Core Rule #1、决策矩阵全面改为「默认每次新建独立 `hermes-cc-{agent}-{ts}`，不复用」；跨会话上下文走 `/tmp/cc-context-{task}.md`。占用检测保留作安全网
- **占用检测统一** — Rule #0 与 Multi-Agent 段统一为含 `✻/✶/✽/✳` 思考态的单一权威逻辑
- **Pitfall 编号重排** — 消除重复的两个 ★23（「自动恢复旧会话」重编为 #27），#18–#27 连续无重复

### Fixed
- **Pitfall #2 HOME 回归** — 修正 `HOME=~`→`HOME=/Users/alexcai`（字面绝对路径，profile override 下 `~` 会失效），并标注 sync 脱敏豁免
- **2 个坏链接** — 新建 `post-deploy-verification-pattern.md` + `cc-agent-team-parallel-implementation.md`
- **teammate-mode 去重** — 删除孤儿 `teammate-mode-verified.md`（`tmux-verified` 子集）

### Execution
- CC agent team：2 个 background subagent（搜索 grill+论文 / references 清债，sonnet）+ leader 串行改 SKILL.md（opus）。按关注点拆，SKILL.md 单文件由 leader 独占避免写冲突

---

## v3.5.2 (2026-06-01) — Session Hijack + Permission Form Pitfalls

### Added
- **Pitfall #25** — Session 被另一 agent 的 /clear 劫持：共享 session 竞争写入导致任务覆盖，修复方案：专用 session 名 `hermes-cc-{task}`
- **Pitfall #26** — CC 权限表单 tmux 不可靠：复选框/单选框 Tab/Enter/Down 失效，解法：Escape + 纯文本决策消息
- **Pitfall #27** — CC 自动恢复旧会话：workdir 有 `.claude/` 时 `claude` 默认 resume，需 `--new-session` 干净启动
- **`references/post-deploy-verification-pattern.md`** — 新建：部署后 Python subprocess curl 验证模式（POST→sleep→GET→检查 artifact 字段）+ token 脱敏陷阱 + artifact dict 写入规范
- **`references/cc-agent-team-parallel-implementation.md`** — 新建：并行实施模式 Leader-wiring 策略、context 文件模板、schema 验证集成

### Changed
- **Pitfall #16** — 压缩为交叉引用「见 #9」，消除与 #9 的重复
- **Pitfall #17** — 压缩为交叉引用「见 #11」，消除与 #11 的重复

---

## v3.5.1 (2026-06-01) — Fake-Idle Detection Enhancement

### Added
- **Pitfall #24** — CC 假空闲：`❯` 可见但深度思考中（`✻/✶/✽/✳` 思考态）；与 #25 组成完整劫持攻击链

### Changed
- **Pitfall #18** 占用检测增强 — 除 `●` 工具调用检测外，新增 `✻/✶/✽/✳/Sublimating/Zigzagging/Billowing/…` 思考态检测；完整空闲条件扩展为 5 项同时满足

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
