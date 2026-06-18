# last30days 源码深度分析 — WRR 可吸收机制

> **来源**：[mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) v3.3.2 · 43K ⭐ · 58 模块 · 1012 测试
> **分析日期**：2026-06-17 · **执行**：小黄（Hermes default）
> **产出**：5 项可偷机制 + 4 项不偷清单 + 与 CQI §十四 对照

## 一、项目定位

last30days 是一台**多源并行检索 + LLM 规划 + 加权融合排序**的 Python 引擎。核心差异：

| 维度 | last30days | WRR |
|------|-----------|-----|
| 问题 | 现在大家**在说什么/赌什么** | 什么是**真的、可引用** |
| 排序信号 | engagement（点赞/upvote/赔率/播放） | source_tier + confidence + evidence_status |
| 反幻觉 | 广度替代验证，无交叉验证 | 逐字提取 + Exa/Brave 双索引 cross-check |
| 源空间 | Reddit/X/YouTube/TikTok/HN/Polymarket/GitHub/Threads/Bluesky/Pinterest/TruthSocial | Exa/Brave/Tavily/web_search/SearXNG + Agent-Reach 11 通道 |
| 执行体 | Python 引擎（model 仅做 planner） | prompt 路由树（model 即执行体） |

**不可合并**：源空间重叠但方法论相反——engagement-first vs authority-first。

## 二、5 项可偷机制（按价值排序）

### ① `resolve.py` — 预搜索实体解析 ⭐⭐⭐⭐⭐

**定位**：Step 0.6 — 搜索发动前自动解析相关社区/handle/repo。

**实现方式**（纯正则 + 频率统计，零 LLM 依赖）：
```python
# 4 路并行 web search → 正则提取
queries = {
    "subreddit": f"{topic} subreddit reddit",       # → r/ 模式匹配
    "news":      f"{topic} news {current_month}",    # → 当前事件摘要
    "x_handle":  f"{topic} X twitter handle",        # → @ + URL 频率计数
    "github":    f"{topic} github profile site:github.com",  # → URL 模式
}
# 轻量：ThreadPoolExecutor(max_workers=3)，纯正则无 LLM
```

**WRR 集成方案**：在 Step 0 和 Step 2 之间插 Step 0.6：
- 跑一次 web_search + Exa 搜索 topic
- 用正则提取 subreddit / X handle / GitHub repo
- 喂给后续 platform mode（用户不用手动指名平台）

**关键教训**：
- 正则优先于 LLM——`_extract_x_handle()` 用频率计数而非语义理解
- URL 匹配权重高于文本匹配（`url_pattern` matches ×3 vs text matches ×1）
- 过滤通用 handle（twitter/x/search/home 等）
- GitHub repo 集成后缀规范化（`-action → canonical`、`-sdk → canonical`）

### ② 三阶段检索管线 ⭐⭐⭐⭐

```
Phase 1: planner → subqueries → 多源并行 fan-out
Phase 2: 从 Phase 1 结果抽实体 → 定向 supplemental search（Bird CLI 搜 handle）
Phase 3: post-rerank enrichment（GitHub star 数注入）
```

**WRR 集成方案**：deep-research-loop 加 Phase 2 回路：
- SECTION 阶段产出 facts.jsonl 后
- 从中抽取实体（handle/subreddit/repo）
- 定向补搜 → 新的事实 → 回写 facts.jsonl
- REFLECT 判断是否需再补

### ③ `available_sources()` — 分层动态源检测 ⭐⭐⭐

**不在路由表硬编码**，而是运行时判定：

```
Layer 1: 免配置 → Reddit public JSON / HN / Polymarket（始终在线）
Layer 2: API key → ScrapeCreators / Brave / Exa / Serper（检查 env var）
Layer 3: CLI 可用 → yt-dlp / gh / digg-pp-cli（检查 PATH）
Layer 4: 排除列表 → EXCLUDE_SOURCES（用户显式关掉某源）
```

**WRR 集成方案**：`engine-registry.json`（CQI §四）的 `enabled` 字段从静态 → **运行时动态**：
- 引擎启动时跑 `available_sources()` → 生成当次 session 的可用引擎列表
- 不在路由表写死"这个能用那个不能用"

### ④ Weighted RRF 融合 ⭐⭐⭐

WRR 的 `dedup_rrf.py` 是所有源统一权重。last30days 的 `weighted_rrf()` 支持 **per-subquery 权重**：
- 主要 handle 搜索 → weight 1.0
- 相关 handle 搜索 → weight 0.3
- 薄源重试结果 → weight 0.5

**WRR 集成方案**：`dedup_rrf.py` 加 `--weights` 参数，30 行改动。

### ⑤ 薄源重试 ⭐⭐⭐

某源返回 <3 条结果时，用**简化版 core-subject query** 重试同一源：
```python
core = query.extract_core_subject(topic, max_words=3)  # "Kanye West"
# 原始 query: "Kanye West album sales Billboard performance 2026"
# 重试 query: "Kanye West"
```

**WRR 集成方案**：fallback 逻辑加一个分支——不只「切引擎」，还「简化 query 重试同一引擎」。

## 三、4 项不偷清单

| 机制 | 原因 |
|------|------|
| Fun judge / Best Takes | 娱乐化评分，污染 WRR authority-first |
| Engagement-only scoring | 与「engagement 不抬升 source_tier」红线冲突（CQI §14.6） |
| ELI5 mode / HTML briefs | 输出格式偏好不同，不适用 Telegram 场景 |
| ScrapeCreators / Bird CLI 依赖 | WRR 已有 Agent-Reach + Exa/Brave/Tavily |

## 四、与 CQI §十四 对照

CQI 已识别 4 项 steal，代码级 review 后**全部确认成立且优先级正确**：

| CQI steal | 代码验证 | 新增发现 |
|-----------|---------|---------|
| ① Step 0.6 实体解析 | ✅ `resolve.py` 87 行纯正则，ThreadPoolExecutor(max_workers=3) | 实现方式是**纯正则非 LLM**——极轻量 |
| ② grounding adapter | ✅ `grounding.py` 多后端（Brave/Exa/Serper/Parallel） | WRR 已有 engine-registry 可承载 |
| ③ live-API-number-wins | ✅ `github.py` star 实时注入 Phase 3 | 确认：star 在 rerank 之后注入，不参与排序 |
| ④ social lane | ✅ `available_sources()` 分层检测 | 比 Agent-Reach doctor 更细粒度 |

**新增发现（CQI 未提）**：
- **⑤ 薄源重试**：简化 query 重试模式——实用价值高
- Weighted RRF 是 RRF 的自然增强——非独立 steal 而是 steal ④ 的子项

## 五、对标 WRR 的差距

| WRR 当前 | last30days 对应 | 差距 |
|---------|----------------|------|
| Step 0 本地四步（无预搜索） | `resolve.py` 4 路 web search + 正则提取 | **缺了 Step 0.6** |
| deep-loop plan→section→reflect→merge | Phase 1 → Phase 2 → Phase 3 | **缺了 Phase 2 supplemental** |
| 路由表硬编码引擎可用性 | `available_sources()` 分层动态检测 | engine-registry 可承载但未实现动态 |
| dedup_rrf.py 统一权重 | `weighted_rrf()` per-subquery 权重 | **缺了 weighted 模式** |
| fallback = 切下一个引擎 | fallback = 简化 query 重试同一引擎 | **缺了薄源重试** |

## 六、关联

- → [[web-research-router 持续质量改进计划#十四、线程 E：last30days|CQI §十四线程 E]] — CQI 级集成评估
- → [[#四、模块化引擎注册架构|CQI §四]] — engine-registry.json 与 `available_sources()` 的对应
- ⊕ [[Agent-Reach 源码分析(WRR)#八、实施记录|Agent-Reach 实施记录]] — platform mode 集成
- ⊕ [[web-research-router_v3.10_platform-mode集成报告_20260617|v3.10 实施报告]] — 同批产出的报告
