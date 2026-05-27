# jz-skills · AI 智能体技能总控

<p align="center">
  <b>English</b> · <b>中文</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/skills-19-blue" alt="19 skills">
  <img src="https://img.shields.io/badge/profiles-4%20三省六部-orange" alt="4 profile types">
  <img src="https://img.shields.io/badge/platforms-Hermes%20%7C%20CC%20%7C%20pi-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/sync-bidirectional-green" alt="bidirectional sync">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="MIT license">
</p>

---

> **AI agent skills for Hermes (三省六部), Claude Code, and pi — one repo, three platforms.**
>
> **服务于 Hermes（三省六部多智能体体系）、Claude Code 和 pi 的 AI 智能体技能仓库 — 一处维护，三端同步。**

---

## Table of Contents · 目录

- [Structure · 结构](#structure--结构)
- [Quick Start · 快速开始](#quick-start--快速开始)
- [Sync Workflow · 同步流程](#sync-workflow--同步流程)
- [三省六部 Profile Skills](#三省六部-profile-skills)
- [Pi Skills · Windows 端技能](#pi-skills--windows-端技能)
- [Skill Format · 技能格式](#skill-format--技能格式)
- [Automation · 自动化](#automation--自动化)
- [Contributing · 贡献](#contributing--贡献)
- [License · 许可](#license--许可)

---

## Structure · 结构

```
jz-skills/
├── shared/                    ← 跨平台通用技能 (Cross-platform)
│   ├── web-research-router/        检索总控：Exa/Tavily/Brave/arXiv 路由
│   ├── github-code-explorer/       GitHub 源码四层探索 (L1→L4)
│   ├── grill-with-docs/            设计审查：对照 CONTEXT.md + ADR
│   └── skill-authoring/            Skill 合规增强层
│
├── hermes/                    ← Hermes 专属技能
│   ├── financial-research-agents/  三省六部金融研究
│   ├── tradingagents/              A股/市场交易分析
│   ├── llm-wiki/                   LLM 知识库构建
│   └── arxiv/                      学术论文检索
│
├── profiles/                  ← 三省六部 profile 专属技能
│   ├── gongbu/                     工部：基建运维 (disk-cleanup, health-check, monitoring)
│   ├── jiangzuojian/               将作监：Kanban 投送门闸 (delivery-gate)
│   ├── protocol/                   礼部：MD→PDF/EPUB 文档渲染 (md-to-pdf)
│   └── tester/                     刑部：代码审查工具集 (code-review-toolkit)
│
├── pi/                        ← Pi 专属技能 (Windows · 5 skills)
│   ├── web-research-router/        Pi 版检索总控 (TypeScript extension)
│   ├── pi-grill/                   主动歧义守护 v3.1 (compliance-reviewed)
│   ├── skill-creator/              合规优先 Skill 创作 v6.0
│   ├── pi-hermes-setup/            Pi ↔ Hermes 跨机器联动架构
│   └── recover-hindsight-mcp/      Hindsight MCP 连接恢复
│
├── cc/                        ← Claude Code 专属 (WIP)
│
└── deploy/
    ├── sync-all.sh                 部署：GitHub → 本地 agents
    └── sync-back.sh                回传：本地 agents → GitHub（含自动脱敏）
```

**19 skills total** — 4 shared · 4 Hermes · 6 profile-specific · 5 pi  
**共计 19 个技能** — 4 个跨平台通用 · 4 个 Hermes 专属 · 6 个三省六部 profile 专属 · 5 个 Pi 专属

---

## Quick Start · 快速开始

```bash
# Clone
git clone git@github.com:Loveacup/jz-skills.git ~/code/jz-skills

# Deploy to all platforms (Hermes + Claude Code + pi)
cd ~/code/jz-skills && ./deploy/sync-all.sh all

# Deploy to one platform only
./deploy/sync-all.sh hermes   # → ~/.hermes/skills/ + all profiles
./deploy/sync-all.sh cc        # → ~/.claude/skills/
./deploy/sync-all.sh pi        # → ~/.pi/skills/
```

> ⚠️ `sync-all.sh hermes` deploys shared + Hermes skills to **all** 16 profiles under `~/.hermes/profiles/` and profile-specific skills to their matching profiles only.

---

## Sync Workflow · 同步流程

jz-skills supports **bidirectional sync** between GitHub and your local agents.
jz-skills 支持 GitHub 与本地 agents 之间的**双向同步**。

```
 ┌─────────────────────────────────────────┐
 │      GitHub (source of truth · 真相源)   │
 │   github.com/Loveacup/jz-skills          │
 └────────────┬──────────────┬──────────────┘
              │ git pull     │ git pull
              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────┐
       │ Mac mini │   │  MacBook │   │  PC  │
       │ Hermes   │   │ CC       │   │  pi  │
       │ (三省六部)│   │          │   │      │
       └──────────┘   └──────────┘   └──────┘
```

### Push: Local → GitHub · 本地 → 远端

When you modify a skill directly in `~/.hermes/skills/` (via agent or manual edit):

```bash
# Preview what changed · 预览变更
./deploy/sync-back.sh --dry-run

# Apply with auto-sanitization · 应用（自动脱敏）
./deploy/sync-back.sh

# Review and push · 审查并推送
git diff
git commit -am "sync: <描述改动>"
git push
```

> 🧹 `sync-back.sh` auto-sanitizes: home paths → `~/`, emails → `<redacted>`, private IPs → `<redacted>`, API keys → `<redacted>`

### Pull: GitHub → Local · 远端 → 本地

```bash
git pull
./deploy/sync-all.sh hermes  # or: cc / pi / all
```

### Daily One-Liner · 日常一行

```bash
# Morning: pull latest · 早上拉最新
git pull && ./deploy/sync-all.sh hermes

# Evening: push changes · 晚上推变更
./deploy/sync-back.sh && git commit -am "daily sync" && git push
```

---

## 三省六部 Profile Skills

The `profiles/` directory contains skills that are **specific to one 三省六部 department profile** — they deploy only to that profile, not all 16.

| Profile · 部门 | Skill · 技能 | Purpose · 用途 |
|:---|:---|:---|
| **工部** `gongbu` | `disk-cleanup` | cron output 清理、缓存回收、日志轮转 |
| | `infra-health-check` | 系统/Gateway/磁盘/进程/config 健康巡检 |
| | `infra-monitoring` | 容器监控、端点检测、资源阈值告警 |
| **将作监** `jiangzuojian` | `delivery-gate` | Kanban send_message 投送门闸绕过策略 |
| **礼部** `protocol` | `md-to-pdf` | Markdown → PDF/EPUB 多格式渲染 (CJK) |
| **刑部** `tester` | `code-review-toolkit` | Lint / 安全审计 / 实体级 AI 审查 |

These deploy via `sync-all.sh` → `sync_profiles()` and sync back via `sync-back.sh` with profile-aware path resolution.

部署走 `sync-all.sh` 的 `sync_profiles()` 函数，回传走 `sync-back.sh` 的 profile 感知路径解析。

---

## Pi Skills · Windows 端技能

Pi (Windows) 维护 5 个专属技能，与 Hermes 共享 `shared/` 中的 4 个跨平台技能。Pi 技能严格遵循合规优先结构：Red Flags 反理性化表、决策树、验证清单。

Pi (Windows) maintains 5 platform-specific skills on top of 4 shared cross-platform skills. All Pi skills follow compliance-first structure: Red Flags table, decision tree, verification checklist.

| Skill · 技能 | Ver · 版本 | Purpose · 用途 |
|:---|:---|:---|
| **web-research-router** | v3.0-pi | Pi 版检索总控 — TypeScript SDK (`extension.ts`) 注册 `web_search`/`web_fetch`，路由 Exa/Tavily/Brave |
| **pi-grill** | v3.1 | 主动歧义守护 — 自动检测模糊/矛盾/缺失，一次一问逐层澄清。含 `references/` 渐进披露 |
| **skill-creator** | v6.0 | 合规优先 Skill 创作 — 9 步流程 + 6 维度评分 + 测试用例，确保 agent 真正遵循 |
| **pi-hermes-setup** | v1.1 | Pi ↔ Hermes 联动架构 — SSH 隧道 + MCP 配置 + 故障诊断决策树 |
| **recover-hindsight-mcp** | v1.1 | Hindsight MCP 恢复 — ECONNRESET 6 步修复 + SSH 隧道重建 + 配置同步 |

> Pi skills are authored by Pi itself and pushed to the repo via `git`. They deploy to `~/.pi/skills/` via `sync-all.sh pi`.
>
> Pi 技能由 Pi 自行创作并 push 到 repo。通过 `sync-all.sh pi` 部署到 `~/.pi/skills/`。

---

## Skill Format · 技能格式

All skills follow the [Agent Skills standard](https://skills.sh):

```
skill-name/
├── SKILL.md          ← YAML frontmatter + markdown body (required)
├── references/        ← Progressive disclosure docs (optional)
│   ├── api.md
│   └── workflow.md
├── scripts/           ← Runnable helpers (optional)
│   └── validate.py
├── templates/         ← Output templates (optional)
│   └── report.md.j2
└── assets/            ← Static assets (optional)
    └── logo.png
```

### SKILL.md frontmatter example · 示例

```yaml
---
name: my-skill
description: "What it does · 做什么"
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [research, github]
    related_skills: [other-skill]
---
```

---

## Automation · 自动化

| Script · 脚本 | Direction · 方向 | What it does · 功能 |
|:---|:---|:---|
| `deploy/sync-all.sh` | GitHub → agents | Deploy to Hermes/CC/pi + all 三省六部 profiles |
| `deploy/sync-back.sh` | agents → GitHub | Reverse sync with auto-sanitization of sensitive data |

### Sanitization rules · 脱敏规则

The following patterns are automatically stripped during `sync-back.sh`:
以下模式在 `sync-back.sh` 回传时自动脱敏：

| Pattern · 模式 | Replacement · 替换为 |
|:---|:---|
| `/Users/<name>/` paths | `~/` |
| Email addresses | `<email redacted>` |
| Private IPs (192.168.x, 10.x, 172.16-31.x) | `<internal IP redacted>` |
| API keys (gho_, sk-, sk-ant-, hf_) | `<API key redacted>` |

---

## Contributing · 贡献

1. Edit skills directly on your agent, or in the repo
2. Run `./deploy/sync-back.sh --dry-run` to preview
3. Run `./deploy/sync-back.sh` to sync back with sanitization
4. Commit and push
5. On other machines: `git pull && ./deploy/sync-all.sh <platform>`

---

1. 在 agent 或 repo 中直接编辑技能
2. `./deploy/sync-back.sh --dry-run` 预览变更
3. `./deploy/sync-back.sh` 回传（自动脱敏）
4. 提交并推送
5. 其他机器：`git pull && ./deploy/sync-all.sh <platform>`

---

## License · 许可

MIT — see [LICENSE](LICENSE) file for details.

MIT 许可 — 详见 [LICENSE](LICENSE) 文件。
