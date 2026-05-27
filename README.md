# jz-skills · AI 智能体技能总控

<p align="center">
  <b>English</b> · <b>中文</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/skills-41-blue" alt="41 skills">
  <img src="https://img.shields.io/badge/profiles-15%20三省六部-orange" alt="15 profiles">
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
- [三省六部多智能体体系](#三省六部多智能体体系)
- [三省六部 Governance Skills · 治理技能](#三省六部-governance-skills--治理技能)
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
│   ├── grill-with-docs/            设计审查：对照 CONTEXT.md + ADR
│   ├── skill-authoring/            Skill 合规增强层
│   ├── pdf/                        PDF 处理：OCR、提取、编辑
│   ├── strategic-insight-longform/  战略洞察长文
│   └── voice-to-markdown-workflow/  语音转Markdown
│
├── hermes/                    ← Hermes 专属技能 (非三省六部)
│   ├── web-research-router/        检索总控：Exa/Tavily/Brave/arXiv 路由
│   ├── github-code-explorer/       GitHub 源码四层探索 (L1→L4)
│   ├── tradingagents/               A股/市场交易分析
│   ├── llm-wiki/                    LLM 知识库构建
│   ├── arxiv/                       学术论文检索
│   ├── auto-diary/                   自动化日记生成
│   ├── bilibili-video-analyzer/     B站视频分析
│   └── xhs-crawler/                 小红书爬虫
│
├── hermes-3S6M-profiles/     ← 三省六部 profile 专属技能
│   ├── common/         三省六部全部门通用
│   │   ├── three-provinces-constitution/ 治理宪章 v3.0
│   │   └── financial-research-agents/    金融研究
│   ├── regent/         监国太子
│   │   ├── kanban-orchestrator/        多 Agent 编排派工
│   │   ├── kanban-worker/              Kanban Worker 手册
│   │   ├── kanban-gate/                制度硬拦截闸门
│   │   ├── 6m-smoke-test/              六部运转冒烟测试
│   │   └── morning-news-briefing/      早间新闻简报
│   ├── gongbu/         工部
│   │   ├── disk-cleanup/              磁盘清理与缓存回收
│   │   ├── infra-health-check/        系统健康巡检
│   │   ├── infra-monitoring/          基础设施监控
│   │   ├── surge-gateway/             Surge 家庭网关管控
│   │   └── agent-observability/       多Agent可观测性(OTel)
│   ├── tester/         刑部
│   │   ├── code-review-toolkit/       代码审查工具集
│   │   └── agent-security-audit/      安全审计(49条OWASP)
│   ├── jiangzuojian/   将作监
│   │   ├── delivery-gate/             投送门闸
│   │   └── specialist-engineer/       外聘专家(8阶段管道)
│   ├── protocol/       礼部
│   │   └── md-to-pdf/                 MD→PDF 渲染
│   ├── auditor/        御史台
│   │   └── agent-audit-evaluation/    独立稽核(7维审计)
│   ├── archivist/      史馆
│   │   └── agent-memory-manager/      长期记忆管理
│   ├── shangshu/       尚书省
│   │   └── a2a-protocol/              A2A互通协议
│   ├── budget/         户部
│   │   └── agent-cost-manager/        API成本管控
│   ├── registry/       吏部
│   │   └── agent-registry/            Agent注册发现
│   └── hanlinyuan/     翰林院
│       └── deep-research-agent/       深度研究
│
├── pi/                        ← Pi 专属技能 (Windows · 5 skills)
│   ├── web-research-router/        Pi 版检索总控 (TypeScript)
│   ├── pi-grill/                   主动歧义守护 v3.1
│   ├── skill-creator/              合规优先 Skill 创作 v6.0
│   ├── pi-hermes-setup/            Pi ↔ Hermes 联动架构
│   └── recover-hindsight-mcp/      Hindsight MCP 恢复
│
├── cc/                        ← Claude Code 专属 (WIP)
│
└── deploy/
    ├── sync-all.sh                 部署：GitHub → 本地 agents
    └── sync-back.sh                回传：本地 agents → GitHub（含自动脱敏）
```

**41 skills total** — 5 shared · 8 Hermes · 23 3S6M-profile · 5 pi  \
**共计 41 个技能** — 5 个跨平台通用 · 8 个 Hermes 专属 · 23 个三省六部 profile · 5 个 Pi

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

## 三省六部多智能体体系

**监国三省六部制 Agent 架构 (Regent 3S6M Architecture)** — 面向复杂任务的多 Agent 治理体系，借鉴唐代三省六部制分权思想。

> 用户授权，监国统筹；中书拟案，门下封驳，尚书派工；六部分职，御史监察，史馆留痕。

**核心切分**：中书能想不能干、门下能驳不能干、尚书能派不能改目标、六部能办不能越权、御史能查不参与执行、史馆能记不制造事实、监国能统筹但重大事项请示用户。

### 部门 · 15 Profiles

| 三省 · 3 Departments | Profile | 职能 |
|:---|:---|:---|
| 中书省 | `planner` | 拟制方案 |
| 门下省 | `reviewer` | 封驳审核 |
| 尚书省 | `shangshu` | 派工调度 |

| 六部 · 6 Ministries | Profile | 职能 |
|:---|:---|:---|
| 兵部 | `engineer` | 代码实现、架构、重构 |
| 工部 | `gongbu` | 基础设施、部署、监控 |
| 户部 | `budget` | 数据搜索、统计、报表 |
| 礼部 | `protocol` | 文档编制、PDF 渲染 |
| 刑部 | `tester` | 代码审查、测试、安全 |
| 吏部 | `registry` | Agent 管理、培训 |

| 独立机构 · Independent | Profile | 职能 |
|:---|:---|:---|
| 监国太子 | `regent` | 总揽仲裁 |
| 御史台 | `auditor` | 独立审计 |
| 史馆 | `archivist` | 全程归档 |
| 将作监 | `jiangzuojian` | 外聘工程专家 |
| 翰林院 | `hanlinyuan` | 知识研究 |

> v0.13 · 15/15 profiles active · 六部冒 smoke test 全线闭环 (16min) · [架构方案 →](https://github.com/Loveacup/jz-skills)

---

## 三省六部 Governance Skills · 治理技能

Core governance skills for the Regent (监国太子) and the Three-Provinces-Six-Ministries system. These skills define the constitution, enforcement, orchestration, and testing of the multi-agent governance model.

三省六部体系核心治理技能 — 定义多 Agent 治理模型的宪章、执行、编排与测试。

| Skill · 技能 | Ver | Purpose · 用途 |
|:---|:---|:---|
| **three-provinces-constitution** | v3.0 | 三省六部通用治理宪章 — 任务路由(L0-L3)、plan-preview触发、封驳/返修分离、escalation规则、handoff schema v2 |
| **6m-smoke-test** | v1.0 | 六部运转冒烟测试 — 中书→门下→尚书→六部→史馆 端到端闭环验证，含 P0/P1/P2 修复流程 |
| **kanban-orchestrator** | v3.5 | 多 Agent 编排与派工 — 反理性化陷阱表、分解 playbook、尚书省强制插入、6+ 次皇帝纠正教训 |
| **kanban-worker** | v2.0 | Kanban Worker 手册 — 工作空间处理、handoff metadata 格式、retry 诊断、do-not 清单 |
| **kanban-gate** | v1.0 | 制度硬拦截闸门 — 五层权限校验(权限矩阵→状态机→高风险拦截→数据清洗→审计日志)，CLI+plugin 双闸 |
| **surge-gateway** | v1.0 | Surge 家庭网关管控 — 安全分级(只读/高影响/危险)、设备清册三角定位、分流规则、WoL/SSH |
| **agent-security-audit** | v1.0 | 刑部 Agent 安全审计 — 49条OWASP规则、注入检测、污点分析、MCP配置审计 (基于 agent-audit) |
| **a2a-protocol** | v1.0 | 尚书省 A2A 互通协议 — Agent Card 能力发现、流式任务委派、跨 profile 结构化交付 (基于 Google A2A) |
| **agent-observability** | v1.0 | 工部多 Agent 可观测性 — 分布式追踪、Span 级成本归因、信号异常检测、实时看板 (基于 Laminar/Opik) |
| **agent-memory-manager** | v1.0 | 史馆长期记忆管理 — 事实提取/去重/时间衰减/知识图谱/多 Agent 98% 召回 (基于 ICM/mnem) |
| **agent-audit-evaluation** | v1.0 | 御史台独立稽核 — 7维审计框架、YAML测试套件、Welch t-test回归检测、证据收集与结构化报告 (基于 OpenAgentBench/agenteval) |
| **agent-cost-manager** | v1.0 | 户部 API 成本管控 — 硬预算熔断、per-agent成本归因、2,600+模型定价、异常检测与优化建议 (基于 AgentBudget 101⭐) |
| **agent-registry** | v1.0 | 吏部 Agent 注册发现 — 协议无关(A2A+MCP+ACP)、心跳监控、动态组队、人才库管理 (基于 agentregistry 245⭐) |
| **deep-research-agent** | v1.0 | 翰林院深度研究 — 层级任务图、证据链合成、迭代深化(2,048+工具调用)、文献综述 (基于 KResearch 336⭐ ICLR'26) |
| **specialist-engineer** | v1.0 | 将作监外聘专家 — 8阶段聘用管道、对抗审查闸门、Bayesian信任账本、多模型路由 (基于 Nexus Hyper Agent Team) | — 事实提取/去重/时间衰减/知识图谱/多 Agent 98% 召回 (基于 ICM/mnem) |

---

## 三省六部 Profile Skills

The `hermes-3S6M-profiles/` directory contains skills that are **specific to one 三省六部 department profile** — they deploy only to that profile, not all 16.

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
