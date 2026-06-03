# Kanban v0.15 Swarm 集成规范

Interactive 模式（手动触发）下的多 Agent 早新闻流水线。基于 Hermes Kanban plugin v0.15。

> **仅 Interactive 模式适用**。Cron 模式无 gateway dispatcher，Kanban swarm 不可用，改用 shell background jobs（见 SKILL.md Mode A）。

---

## 一、实测 CLI 语法 (v0.15)

⚠️ **以下为 v0.15 实测语法，与 SKILL.md 中的概念示例不同**。SKILL.md Mode B 写的 `--workers 4 --worker-model deepseek-v4-pro` 是简化示意；实际 flag 如下：

```bash
hermes kanban swarm \
  --goal "目标描述" \
  --worker PROFILE:TITLE[:SKILL,SKILL] \   # 可重复，每个 --worker 一个并行 worker
  --verifier VERIFIER_PROFILE \            # 验证节点
  --synthesizer SYNTHESIZER_PROFILE        # 合成/交付节点
```

### 关键纠正（避免踩坑）

| 误区 | 实测真相 |
|------|---------|
| `--workers 4`（数量 flag） | ❌ 不存在。每个并行 worker 用一个独立的 `--worker PROFILE:TITLE` 声明 |
| `--worker-profile` / `--worker-title` | ❌ 不存在。格式是单 flag `--worker PROFILE:TITLE[:SKILL,SKILL]` |
| `--worker-model deepseek-v4-pro` | ❌ 没有 per-flag model override。**Model 由 profile 的 `config.yaml` 控制** |
| `--verifier-model claude-sonnet-4` | ❌ 同上。verifier 的 model 写在 verifier profile 的 config.yaml |
| Hermes 有原生 kanban SKILL | ❌ Kanban 是 **plugin**，不是 skill。Agent 通过 `kanban_*` 工具族操作板子 |

### model override 的正确做法

既然没有 CLI flag，per-task model 差异化通过 **profile 分层**实现：

```yaml
# 各 worker profile 的 config.yaml 设便宜模型（搜索任务）
# profiles/news-lane-zh/config.yaml
model: deepseek-v4-pro

# verifier profile 设强模型（审计任务）
# profiles/news-verifier/config.yaml
model: claude-sonnet-4
```

---

## 二、早新闻 Swarm 拓扑

```
Root (Blackboard): "生成 {date} 早新闻简报"
  ├── Worker 1 (lane-zh):     Brave → Tavily, ≥12 中文源    → lane-zh.json
  ├── Worker 2 (lane-en):     Exa → Tavily + Brave, ≥15 英文源 → lane-en.json
  ├── Worker 3 (lane-mix+tech): Brave+Exa → Tavily, 市场+科技   → lane-mixed.json + lane-tech.json
  └── Worker 4 (assembly):    读全部 lane JSON → 去重 → 结构化为 v4.0 格式 → assembled + markdown
        ↓ (parent dependency: assembly 必须先完成)
  Verifier: 7-sentinel 审计 + anti-hedging grep + source count
        ↓
  Synthesizer: Render PDFs (mobile + A4) + TTS + Deliver
```

> Worker 1-3 并行；Worker 4 (assembly) 依赖 1-3 全部完成；Verifier 依赖 assembly；Synthesizer 依赖 Verifier 通过。**渲染绝不可早于 assembly**（SKILL.md Core Rule #3）。

---

## 三、一键启动命令

```bash
hermes kanban swarm \
  --goal "生成 {date} 早新闻简报：四路搜索 → 汇编去重 → 7-sentinel 审计 → 渲染 mobile+A4 PDF → TTS → 交付" \
  --worker news-lane-zh:"Lane ZH 中文搜索":morning-news-briefing \
  --worker news-lane-en:"Lane EN 英文搜索":morning-news-briefing \
  --worker news-lane-mixtech:"Lane Mixed+Tech 市场科技":morning-news-briefing \
  --worker news-assembly:"汇编去重 + de-slop + source-verification":morning-news-briefing,de-slop \
  --verifier news-verifier \
  --synthesizer news-synthesizer
```

> profile 名仅为示意，按实际 roster 调整。每个 worker profile 都挂载 `morning-news-briefing` skill 以读取 lane 定义。

---

## 四、Kanban Board 配置

```yaml
# kanban board 配置
auto_decompose: false   # ⚠️ 关键：关闭自动分解，避免 quota 风险（见 §七）
max_spawn: 5            # 上限 5 个并发 agent（4 worker + 1 verifier/synthesizer 滚动）
dispatcher_tick: 60s    # dispatcher 每 60s 轮询 roster，认领待办卡
```

| 配置项 | 值 | 理由 |
|--------|-----|------|
| `auto_decompose` | **false** | 默认 `true` 会让 dispatcher 自动拆任务、无限 spawn → quota 爆炸。早新闻拓扑固定，手动声明 worker 即可 |
| `max_spawn` | 5 | 4 路 worker + 1 滚动槽（verifier→synthesizer 串行复用）。硬上限防失控 |
| dispatcher | 嵌入 gateway | **需 gateway 运行**。gateway 未起 → swarm 无法 dispatch（这正是 cron 模式不能用 swarm 的原因） |

---

## 五、Worker 任务描述（从 SKILL.md v4.0 提取）

每个 worker 的 task context 直接引用 lane 定义。详细查询模板见 `references/search-workflow.md`。

### Worker 1 — Lane ZH
```
goal: 搜索中国媒体今日要闻，覆盖政治/经济/科技/外交/社会
主引擎 Brave → 校验 Tavily
≥12 源 → ~/.hermes/workspaces/morning-news-{date}/search/lane-zh.json
结构: { date, lane:"zh", engine_used, articles:[{title,url,source,snippet,category,cross_checked}] }
完成后: kanban_comment("lane-zh done, N articles") + kanban_complete
```

### Worker 2 — Lane EN
```
goal: 搜索英文主流媒体，覆盖美国政治/经济/国际地缘
主引擎 Exa (discovery) → 校验 Tavily → 补充 Brave (breaking)
提取 mcp_exa_web_fetch_exa 5-8 篇
≥15 源 → lane-en.json (lane:"en")
```

### Worker 3 — Lane Mixed + Tech
```
goal: 搜索市场数据（油价/美股/外汇/加密货币）+ 科技新闻（AI/芯片/互联网）
Mixed: Brave 快讯 + Exa 趋势 → Tavily 价格三源比对(±2%取中位, 加密取均值)
       → lane-mixed.json (lane:"mixed", 含 market_data 数组)
Tech:  Exa 深度发现 + Brave 补充 → Tavily 校验
       → lane-tech.json (lane:"tech")
两路各 ≥12 源
```

### Worker 4 — Assembly
```
goal: 读取四路 lane JSON → 去重 → 结构化为 v4.0 markdown 格式
依赖: Worker 1-3 全部 kanban_complete (parent dependency)
去重规则: URL 规范化 + 标题语义近似；同事件合并保留双源 [sN]；不同事件不得 fusion
输出层次:
  - 📰 今日要闻: ≥15 独立条目, 按板块分组（去重后保留独立性！）
  - 🔍 深度分析: 5-8 条 前提→推理→结论 + 趋势 + 为什么重要
  - 📌 今日总结: 核心张力 + 前瞻
  - 📰 来源清单: S01-SNN
再跑 de-slop (citation-protected) + source-verification (关键声明 2-path evidence)
→ search/assembled-{date}.json + morning-news-{date}.md
```

---

## 六、Verifier 检查清单（7 Sentinels）

Verifier profile 对 assembly 产物（两版 PDF + markdown）逐项核验。任一未过 → `kanban_comment` 退回 assembly，不放行 synthesizer。

| # | Sentinel | 检查方法 |
|---|----------|---------|
| 1 | 执行摘要 | 首页 3-5 bullet points |
| 2 | 📰 今日要闻 | **≥15 独立新闻条目**（来源计数以 S01-SNN 为准），按板块分组。⚠️ 最易失败项 |
| 3 | 🔍 深度分析 | 5-8 items，每条 前提→推理→结论 + 趋势 + 为什么重要 |
| 4 | 📌 今日总结 | 独立卡片 + 核心张力一句话 |
| 5 | 来源清单 | S01–SNN 编号 + outlet 名 + 可验证 URL |
| 6 | Alex Cai | 封面/页眉署名 |
| 7 | 日期 | YYYY年M月D日 格式，当日 |

**附加硬检查**：
- **anti-hedging grep**：`一方面|另一方面|可能|或许|似乎` 任一命中 → REJECT
- **source count**：📰 来源清单总数 ≥15（不达标退回 assembly 补搜）
- **CSS diff-check**：两版偏离 baseline <5%
- **PyMuPDF 全文提取**：两版 PDF 全量提取后逐 sentinel 核验

---

## 七、Artifact 交付

Synthesizer 完成渲染+TTS 后，用 `kanban_complete(artifacts=[...])` 提交产物，Kanban 自动分发到 Telegram。

```
kanban_complete(
  artifacts=[
    "~/.hermes/workspaces/morning-news-{date}/output/morning-news-{date}-mobile.pdf",
    "~/.hermes/workspaces/morning-news-{date}/output/morning-news-{date}-a4.pdf",
    "~/.hermes/workspaces/morning-news-{date}/output/morning-news-{date}.mp3"
  ]
)
```

> TTS mp3 不可达时（CosyVoice down）只交付两版 PDF，并 `kanban_comment("TTS skipped — text_to_speech unavailable")`。不静默省略（SKILL.md Core Rule #8）。

---

## 八、Cron vs Kanban Swarm 对照

| 维度 | Cron (Mode A) | Kanban Swarm (Mode B) |
|------|---------------|----------------------|
| 触发 | scheduler (daily 08:00) | 手动/Interactive |
| 并行方式 | shell background jobs + `wait` | dispatcher 认领 + 并行 worker |
| gateway | 不需要 | **必需**（dispatcher 嵌入 gateway） |
| 任务编排 | 单线程顺序 pipeline | Blackboard + parent dependency |
| Per-task model | 单 profile model | profile 分层（worker 廉价 / verifier 强） |
| Artifact 交付 | 脚本直接发 Telegram | `kanban_complete(artifacts=[...])` 自动分发 |
| 审计追踪 | 日志文件 | 每 worker run 落 `task_runs` |
| 崩溃恢复 | 无（整 job 失败） | zombie 检测 + auto-reclaim |
| 适用 | 无人值守定时 | 需要可观测/可干预的高质量产出 |

---

## 九、Quota 风险提示 ⚠️

| 风险 | 后果 | 缓解 |
|------|------|------|
| `auto_decompose: true`（默认） | dispatcher 自动拆任务，无界 spawn → API quota 爆炸 | **设 `auto_decompose: false`**，手动声明固定 4 worker |
| 无 `max_spawn` 上限 | worker 连锁 spawn 子任务 | 设 `max_spawn: 5` 硬上限 |
| verifier 用强模型 + 多轮退回 | 每次退回 assembly 重跑 → token 翻倍 | verifier 一次性出全部 sentinel 失败项；assembly 一轮修齐 |
| Exa fetch 全文 × 多篇 | fetch token 量大 | 仅对 5-8 篇高信号正文 fetch，不全量 |
| gateway 未运行就发 swarm | 命令挂起/失败 | 启动前确认 gateway 运行；否则降级 Cron 模式 |

> 历史教训：默认 auto_decompose 在一次跑中拆出数十个子任务，几分钟耗尽 quota。早新闻拓扑固定且已知 → **永远手动声明 worker，关闭 auto_decompose**。
