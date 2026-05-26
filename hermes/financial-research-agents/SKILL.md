---
name: financial-research-agents
description: "三省六部金融研究 skill — 通过 Kanban 多 profile 体系安全调度 AI 金融研究，从监国承旨到史馆归档的全链路工作流。"
version: 2.0.0
author: 史馆归档
platforms: [linux, macos]
metadata:
  hermes:
    tags: [finance, research, trading, multi-agent, kanban, three-provinces]
    related_skills: [tradingagents, kanban-orchestrator, kanban-worker]
---

# 三省六部金融研究 — Financial Research Agents

> 改造自 v1.0.0（原始单体 Hermes skill），升级为三省六部/Kanban 多 profile 协作体系。

## 定位

本 skill 不是单兵作战的金融分析工具，而是 **三省六部体系下调度金融研究的规程**。当监国（主频道）或用户提出金融/股票/市场分析请求时，按此流程分解为 Kanban 多 profile 任务链。

核心三原则：

1. **研究仅限研究**（research-only），不输出投资建议，不自动交易。
2. **多 profile 协作**：通过 Kanban 分派给中书/门下/六部/御史/史馆各 profile，非单 agent 执行。
3. **执行层在 tradingagents skill**：具体的 TradingAgents 安装、配置、运行、报告生成归属 `tradingagents` skill，本 skill 在其上层编排。

### 🚨 Red Flags: DO NOT SKIP THE GOVERNANCE CHAIN

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll just run the analysis myself" | This skill orchestrates via Kanban. Single-agent execution bypasses 门下 review and 御史 audit. |
| "The ticker is obvious, no need to confirm" | Ambiguous symbols (e.g., 苹果 vs AAPL) cause wrong analysis. Confirm scope before dispatching. |
| "I'll skip the audit for a quick result" | Without 御史 verification, errors propagate silently. Every run needs audit evidence. |
| "Let me just grab the raw output and summarize" | Raw TradingAgents output needs structured report conversion. Don't dump logs at the user. |

## 触发条件

当用户提出以下请求时，应当触发本 skill 启动三省六部流程：

- 「分析 / 研究 / 看看 XXX 这支股票」
- 「XXX 最近怎么样」「特斯拉财报怎么看」
- 「跑一下 TradingAgents 分析 XXX」
- 「写一份 XXX 的金融研究报告」
- 「比较 / 追踪一下 XXX 和 YYY」

不要触发：简单的股价查询（直接用市场数据源）、已归档报告的检索（走 qmd 搜索）。

## 三省六部流程全链路

### 流程编码：FS-001

```
监国承旨 → 中书拟制 → 门下封驳 → 尚书派工
    → 六部/外部框架施行 → 御史稽核
    → 门下复核 → 史馆归档 → 监国复命
```

#### 1. 监国承旨（主频道/用户）

- 接收用户金融研究请求。
- 确认标的（ticker/代码）、分析维度（市场/新闻/基本面/技术）、日期范围、深度偏好。
- 禁止在承旨阶段猜测投资意图或提供倾向性判断。

**输出**：Kanban 任务书（task body），含 ticker、日期、分析维度、安全边界说明。

**任务书模板**（简版）：

```yaml
type: financial-research
ticker: NVDA
date: 2026-01-15
dimensions: [market, news, fundamentals]
depth: 1  # debate rounds; default 1, max 3
provider: openrouter
model: anthropic/claude-sonnet-4
output_language: Chinese
special_instructions: ""
risk_boundary: research-only, no trade execution
```

#### 2. 中书拟制（orchestrator/profile 拟制角色）

- 接收任务书，分解为子任务。
- 确定需要几个分析师维度（默认：market、news、fundamentals）。
- 核定深度消耗与成本预算，避免默认开启深度分析。
- 生成 Kanban 子任务卡片。

**典型分解**（一次简单分析）：

| 任务 | 负责 profile | 说明 |
|------|-------------|------|
| 数据采集 | 对应 worker | 调用 tradingagents skill 取数据 |
| 分析师报告 | 对应 worker | 运行指定分析师维度的分析 |
| 摘要生成 | 对应 worker | 将原始输出压缩为用户摘要 |
| 御史稽核 | auditor profile | 验证研究边界合规 |
| 史馆归档 | archivist | 沉淀报告到知识库 |

#### 3. 门下封驳（reviewer profile）

- 审查任务书的可行性：ticker 是否可解析、维度是否合理、深度是否可控。
- 检查安全边界声明是否完备。
- 若发现不足，驳回中书修改（kanban_block + 原因说明）。
- 若通过，放行至尚书派工。

#### 4. 尚书派工（dispatcher / kanban system）

- 自动将 Kanban 子任务分派到各 profile。
- 任务之间的依赖关系（如摘要依赖全部分析师完成）通过 `parents` 字段控制。
- 并行任务（多个分析师维度）同时分派。

#### 5. 六部/外部框架施行（worker profile / tradingagents）

- 执行层调用 `tradingagents` skill 的实际分析逻辑。
- **必须在隔离 venv 中运行**（详见下文「执行隔离」）。
- 禁止直接在 Hermes 主 venv 安装 TradingAgents/LangGraph 等重型依赖。
- 输出原始分析结果保存至磁盘，路径：`~/.tradingagents/reports/YYYYMMDD-HHMMSS-TICKER.md`

**默认输出形状**（worker 回奏给尚书的中式摘要）：

```
标的: NVDA
分析日期: 2026-01-15
框架: TradingAgents / provider / model
分析师维度: market, news, fundamentals
核心判断: BULLISH / BEARISH / NEUTRAL / 无法判断
核心理由:
- (理由1)
- (理由2)
主要风险:
- (风险1)
- (风险2)
完整报告: /path/to/report.md
声明: 研究仅供参考，不构成投资建议。
```

#### 6. 御史稽核（auditor profile）

验证以下事项：

- ✅ **安全边界**：输出不含交易指令、不含投资建议表述、不含自动化执行代码。
- ✅ **声明完整**：附有研究非投资建议的声明。
- ✅ **数据来源标注**：说明使用哪些数据源（yfinance / Alpha Vantage / akshare 等）以及局限性。
- ✅ **报告可复现**：保存了完整的 config 与运行参数。
- ✅ **未泄露 API key**：报告中不含原始密钥。

问题严重等级：

- **阻断**（Blocking）：报告中含买入/卖出建议、交易执行代码、暴露的密钥 → 拦截报告，通知尚书重新执行。
- **警告**（Warning）：缺少声明、数据来源模糊 → 补充后放行。
- **可通过**（Pass）：合规 → 放行至门下复核。

#### 7. 门下复核（reviewer profile）

- 二次审查报告质量：数据是否充分、分析师逻辑是否自洽、风险是否有遗漏。
- 若不符合质量要求，退回六部/worker 重新执行（追加子任务）。
- 若通过，通知史馆归档。

#### 8. 史馆归档（archivist — 本 profile）

- 将最终报告写回知识库。
- 归档路径：Obsidian `40-Archives/20_Areas_Archive/`
- 文件名：`financial-research_TICKER_DATE.md`
- qmd 索引刷新，保证后续可检索。
- 归档后通知监国复命。

**归档内容必须包含**：

- YAML frontmatter（tags、date、ticker、provider、decision）
- 完整分析报告
- 审计摘要（御史审核结果）
- 研究声明
- 存档路径与 qmd 检索路径

#### 9. 监国复命

- 向用户（主频道）返回精简摘要，含核心判断、风险、报告路径。
- 摘要格式同「默认输出形状」，省略调试与审计细节。

## 执行隔离

所有 TradingAgents 相关执行必须在隔离 venv 中完成：

```bash
# 隔离 venv 路径
~/.tradingagents/.venv

# 激活方式
source ~/.tradingagents/.venv/bin/activate

# 或（推荐）使用 uv 直接指向
uv run --directory ~/projects/TradingAgents --with-editable . python wrapper.py
```

**隔离原则**：

- TradingAgents 及其 LangGraph/LangChain 依赖安装在项目 venv 中，不污染 Hermes 主 venv。
- 数据缓存（yfinance、akshare 等）统一存放在 `~/.tradingagents/cache/`。
- 报告输出统一存放在 `~/.tradingagents/reports/`。
- 每次运行前检查 `~/.tradingagents/.venv` 是否存在，不存在则提示安装。

**运行验证**（验收标准）：

```bash
cd ~/projects/TradingAgents
source ~/.tradingagents/.venv/bin/activate
python -c "from tradingagents.graph.trading_graph import TradingAgentsGraph; from tradingagents.default_config import DEFAULT_CONFIG; print('OK')"
```

## A-Share 中国市场支持

详见 `tradingagents` skill 的 A-Share 章节。简要原则：

- A 股分析优先使用独立的 A-share prefetch 脚本（`tradingagents skill 的 templates/ashare_prefetch.py`）采集东财/Tencent/BaoStock 数据。
- 若 TradingAgents 无法解析 A 股 ticker，则将 prefetch 数据直接用于报告，不强行运行 TradingAgents。
- 模糊股票名称（如「东方精密」对 002611 vs 002384）需向用户澄清后执行。

## 安全性约束 — 硬性边界

以下行为 **严格禁止**：

1. ❌ 输出任何形式的买入/卖出/持仓建议
2. ❌ 调用交易执行 API 或 broker SDK
3. ❌ 自动执行任何订单或调仓
4. ❌ 在报告中省略「研究仅供参考」声明
5. ❌ 将未经验证的数据源当作权威数据
6. ❌ 在非隔离环境中安装 TradingAgents 依赖
7. ❌ 在报告中包含原始 API key 或 secrets

违反以上任一条，史馆应拒绝归档，并向御史台/监国报告违规。

关于投资建议的合规表述：

- ✅ 「模型倾向买入」— 可陈述原始输出
- ✅ 「市场分析师认为…」— 可转述
- ❌ 「建议买入 XXX」— 不可
- ❌ 「可以考虑在此价位建仓」— 不可
- ✅ 「这不是投资建议，请咨询持牌顾问」— 必须附在最后

## 报告归档规范

### Obsidian 归档格式

```markdown
---
tags: [financial-research, archive, TICKER]
date: YYYY-MM-DD
ticker: NVDA
provider: openrouter
model: anthropic/claude-sonnet-4
decision: BULLISH / BEARISH / NEUTRAL
audit: passed / passed_with_warning
---

# 金融研究报告：TICKER

## 分析摘要
...

## 核心理由
...

## 主要风险
...

## 数据源与局限性
...

## 审计摘要
- 安全边界：✅
- 声明完整：✅
- 数据来源标注：✅
- 报告可复现：✅
- API key 泄露检查：✅

## 研究声明
本研究由 AI 框架 TradingAgents 自动生成，仅供参考，不构成投资建议。
数据可能存在延迟与不准确，LLM 输出可能产生幻觉。任何投资决策请咨询持牌顾问。
```

### qmd 索引更新

归档后执行：

```bash
cd ~/obsidian/vault
qmd update
```

## 限速与成本控制

| 维度 | 默认值 | 上限 |
|------|--------|------|
| 分析师维度数 | 3（market, news, fundamentals） | 6 |
| 辩论轮次 | 1 | 3 |
| 风险评估轮次 | 1 | 2 |
| 深度模型 | provider 默认 | 用户指定 |
| 快速模型 | provider 默认小型模型 | 用户指定 |

超出默认值的深度分析前应通知用户预估消耗（时间 + token 成本）。

## 已知限制

1. **数据延迟**：yfinance 数据可能延迟 15 分钟以上。A 股 Tencent 实时报价约 3 秒延迟。
2. **LLM 幻觉风险**：多 agent 辩论可能强化错误共识。每个分析师维度输出需要交叉验证。
3. **TradingAgents 版本漂移**：上游库的 constructor 参数名可能变化（`selected_analyst_keys` vs `selected_analysts`），wrapper 需在安装后验证。
4. **中国市场局限**：上游 TradingAgents 数据路由主要为美股设计，A 股分析需通过 prefetch 补充。
5. **长运行时间**：深度多 agent 分析可能持续数分钟至数十分钟，建议后台运行 + 通知模式。

## References

本 skill 目录下的引用文件：

- `references/tradingagents-source-review.md` — TradingAgents 源码审查笔记
- `templates/run_tradingagents.py` — 非交互式 TradingAgents Python wrapper 模板

关联 skill：

- `tradingagents` — 具体安装/配置/运行 TradingAgents 的详细操作技能
- `kanban-orchestrator` — 三省六部 Kanban 编排规程
- `kanban-worker` — Kanban 工作单元执行规则

## 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0.0 | 2026-05-20 | 三省六部多 profile 改造：全链路流程、执行隔离、御史稽核、史馆归档、安全性约束 |
| 1.0.0 | — | 原始版本：单体 Hermes skill，直接操作 TradingAgents |

---

## ✅ Verification Checklist (RUN BEFORE DISPATCHING)

- [ ] Did I confirm the ticker/scope with the user (not assume)?
- [ ] Did I remind the user this is research-only, not investment advice?
- [ ] Did I dispatch via Kanban (中书→门下→尚书→六部) not single-agent?
- [ ] Did I ensure 御史 audit step is NOT skipped?
- [ ] Did I ensure 史馆 archive step is planned?

**If any box is unchecked, go back.**

---

## Deployment & Sync

After ANY update to this SKILL.md:
1. Sync to ALL Hermes profiles (dynamic discovery):
   ```bash
   for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
     dst=~/.hermes/profiles/$prof/skills/research/financial-research-agents
     [ -d "$dst" ] && cp -r "$dst" ~/.hermes/profiles/$prof/backups/financial-research-agents-$(date +%Y%m%d_%H%M%S)
     rm -rf "$dst"
     cp -r ~/.hermes/skills/research/financial-research-agents "$dst"
   done
   ```
2. `qmd update`
