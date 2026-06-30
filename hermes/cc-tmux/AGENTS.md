# AGENTS.md · cc-tmux 架构权威参考

> **Canonical 架构参考。在本代码库工作前先读这里。**
> 分工：**本文件 = 实现/架构权威**；需求/设计权威在 OB（见文末）。
> 当前：v1.40.0 · 测试 24/24 文件、230/230 断言 · 健康分 0.96+。

## 是什么

cc-tmux = Hermes ↔ Claude Code 的 tmux-based 编排层。**Thin skill**：脚本做 enforcement，prose 只说调哪个脚本。核心赌注 = 把每 turn 义务从 80+ 砍到 ~10（curse of instructions），让「合规 = 最省事」。

## Core Principles（不可动摇）

1. **脚本做 gate，LLM 做决策** —— "能不能做"由代码判，"怎么做"由 LLM 判。
2. **文件系统是通信通道** —— `/tmp` 下心跳 / turn-done marker / freeze 告警。可 `cat` 可审计、零依赖。
   - ⚠️ 演进中：iii Hub 轨（轨2）可能突破此条（改 `call()` 网络通信），**待 Alex 拍 D-iii-3**，未拍板前文件系统仍是唯一通道。
3. **义务最小化** —— 节律义务搬到 hook 事件 + watcher，LLM 不背定时器。

## 四组件基座 + 轨1 扩展（R1/R3/R4/R9a · v1.14-v1.22 全部落地）

| 脚本 | 职责 | 版本 |
|------|------|------|
| `cc-start.sh` | 启动 + 占用锁 + 全量扫描 + 僵尸清理 + `--topic` 复用 | v1.22.0 |
| `cc-send.sh` | 发送 + 存活验证 | — |
| `cc-send-robust.sh` | send-keys 健壮封装（回读+重试） | v1.14.0 |
| `cc-monitor.sh` | 6 状态机 + esc 金标准 + cc-status fast-path + last_tool 插值规范化 + 回归测试 | v1.15.0/18.0/28.0 |
| `cc-finish.sh` | 7 步安全门 + topic-map 清理 | v1.22.0 |
| `cc-wait-marker.sh` | fswatch 事件驱动等待 + startup gate 防 IDLE/residual 空等（低层原语） | v1.38.0 |
| `cc-wait-decision.sh` | Hermes-facing wait 决策层：rc4/timeout 后采证并输出 JSON action | v1.39.0 |
| `cc-watcher.sh` | 守护探针（缩职责） | v1.18.0 |
| `cc-usage.sh` | 用量管理 pre/post | v1.16.0 |
| `cc-gc.sh` | Session GC scan/gc/suggest | v1.17.0 |
| `cc-topic-map.sh` | Topic↔Session 复用注册表 | v1.22.0 |
| `cc-dogfood-report.sh` | 收尾摩擦 JSONL 累积 + 阈值摘要 | v1.27.0 |
| `hooks/cc-status-writer.sh` | Hook→状态文件原子写 | v1.18.0 |
| `cc-route.sh` | 消息路由：Hermes 收消息时判排队/转发/中断 | v1.30.0 |
| `cc-active-sessions.sh` | 活跃 CC session 枚举 + 状态总览 | v1.31.0 |

## 三段协议（in-turn wait 全程可见 · cc-tmux 独有优势 · 不该砍）

> 这是 cc-tmux 相对开源编排项目的核心差异化——多数项目只做编排，不做 Hermes↔CC 讨论可见性。**路线 A（保 tmux）正是为守住它**（headless 模式会牺牲它）。

- **节点①** 发任务前讨论：等 CC 读完 → 看理解 → 偏了先纠正再开干（context 末尾须含「先复述」约定）。
- **节点②** 中间状态汇报：wait 超时 → 抓屏 + 📡 块 + Hermes 判断，**不静默**；判断走偏 → 先汇报等确认，**不在判断环节直接 C-c**。
- **节点③** 完成后讨论：turn-done → 读产物 → 讨论达标/遗漏 → 带 Hermes 判断用 📡 汇报。
- 全程 **📡 Progress Reporting**（5 模板 ⓪Pre-Send/①进度/②异常/③等待/④完成）。

## Gate 独立性（基质无关红线）

- `scripts/gate/{gate-verify,gate-danger,gate-counter}.sh` —— **零 tmux 耦合、零 import iii-sdk**，遇第 2 消费者可整组搬走。
- 客观验收(命令/退出码/产物) + 危险拦截 + 退回计数，由 gate 裁；主观半由 auditor 角色裁。
- 未来 iii review-worker（轨2 iii-P3）会调用它们，但 **gate 本身永不依赖 iii**。

## 统一路线图（三轨 · 全文见 `/tmp/cc-unified-roadmap.md`）

**决策基础**：D-iii-1=路线 A(保 tmux) · D-iii-2=解耦(P0 bash 先) · D-iii-3=§8 先不管 · 第三轨=认。

- **轨1 内核轨**（✅ 全部落地·bash·零依赖）：`P0-1 send-keys 封装 (v1.14.0) → P0-4 状态金标准 (v1.15.0) → P0-2 cc-usage (v1.16.0) → P0-3 cc-gc (v1.17.0) → P1-1 hook 成状态权威 (v1.18.0) → P1-2 fswatch (v1.19.0)`。测试 80→127。
- **轨2 iii Hub 轨**（远期·赌多 Agent·pre-1.0 隔离）：`iii-P0 HelloWorld → iii-P1 复用官方 worker → iii-P2 自写 cc-worker🚧§8 → iii-P3 review-worker → iii-P4 全 Hub`。覆盖 R5/R6/R8a。
- **轨3 Hermes 侧智能轨**（并行）：R2.1 澄清式交接 ✅ (v1.20.0) · R8b CC 配置 ✅ 部分 (v1.21.0) · R9b 会话复用 ✅ (v1.22.0) · **R10 消息路由 ✅ (v1.30.0)** · R8a 路由归 iii · R8d3 WRR 升级（远期）。

## 不该动（红线 · 防颠覆误伤）

1. 上述 Core Principles + 四组件基座 + 三段协议 + gate 独立性。
2. 不引重型框架（crewAI/langgraph 与「驱动 CLI 进程」场景正交，抄协议可以、抄实现是负债）。

## 工作约定（coding agent）

- **TDD 红线**：实现类先写测试 → 确认失败 → 写代码 → 确认通过。当前 **229/229**。
- **Hook/脚本是单一真源**：改 `hooks/`/`templates/settings.runtime.json` → 下个 CC 启动经 `--settings` 自动生效，零 cp/jq/重启。
- **杀 session 必须用户确认**（`cc-finish.sh --kill-session` 永不自动）。
- **改完同步 deploy**：`~/.hermes/skills/autonomous-ai-agents/cc-tmux/`，`md5` 校验 parity。

## 关键文件

- `SKILL.md` — 操作手册（红线 / 决策树 / 4 步流程 / Pitfalls / R4c checkpoint）。
- `scripts/` — 核心脚本 + cc-send-robust/cc-usage/cc-gc/cc-topic-map/cc-dogfood-report/eval + `gate/`。`tests/` — 24 文件 229/229。`references/` — 设计依据 / Hook 事实 / 事件驱动 / R2.1 澄清协议 / R8b 配置指南 / R4c smoke 流程 等。

## 需求与设计权威（在 OB，非本库）

`~/Documents/Obsidian/AlexCai/20-Areas/20_技术项目/cc-tmux Skill 与 Agent 协作/`
- `10_cc-tmux核心/CC-TMUX核心需求.md` — **PRD（R1-R9 需求权威）**
- `10_cc-tmux核心/CC-TMUX核心构架.md` — 架构设计
- `AGENTS.md`（该目录）— 文档库工作契约
