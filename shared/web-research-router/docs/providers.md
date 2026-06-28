# WRR v5.0 Provider 能力矩阵与路由规则

> v5.0：mode-based 路由 + 多引擎并行 + 跨源 RRF 融合（k=60）。`web_search` 入口先 `classify_intent(query)→mode`，
> 取该 mode 的引擎组合并行发射（`asyncio.gather`，单引擎失败隔离），源内评分后跨源 RRF 融合 + canonical URL 去重。
> 显式 `provider` 走单引擎（v4 兼容）；显式 `mode` 覆盖自动分类；主 mode 空结果回退 `recovery`。

## v5.0 引擎（7 个）

| Provider | Search | 评分 | 默认融合权重 | 触发/角色 | 状态 |
|----------|--------|------|------------|----------|------|
| **Exa** | ✅ | 源相关性 | 1.0 | 语义主力 | v4 既有 |
| **Brave** | ✅ | 源相关性 | 0.9 | 索引交叉 | v4 既有 |
| **SearXNG** | ✅ | 源相关性 | 0.1 | recovery/兜底 | v4 既有 |
| **GitHub** | ✅ repo+issue | 4 维（+maintenance）| 0.25 | `site:github.com`/源码 | v5 升级（GraphQL 批量活跃度 + issue_search） |
| **Community** | ✅ 多源聚合 | 三维 + 跨子源 RRF | 0.30（disc 0.35/platform 主力）| 社区站点/平台词 | v5 升级（`search_rrf` + canonical 去重） |
| **Academic** | ✅ OpenAlex/S2/arXiv | 4 维 velocity/authority/recency/relevance | 0.30（academic 1.0）| 论文/综述/survey | **v5 新增** |
| **Skill** | ✅ code search SKILL.md | 双层包级+单skill级 | 0.25 | 找 skill | **v5 新增** |

## 6 种 mode → 引擎组合（MODE_DISPATCH）

| Mode | 基础引擎组合 | 意图 |
|------|------------|------|
| discovery | exa + brave + community(0.35) | 广扫/有哪些/趋势 |
| grounding（默认）| exa + brave | 事实核验 |
| research | exa + brave + community(0.30) + academic(0.30) | 深度/综述/对比 |
| academic | academic(1.0) + exa + community(0.25) | 论文/methodology |
| platform | community(主力) + exa/brave | site:reddit/hn/zhihu + 平台词 |
| recovery | brave + exa + searxng | 死链/空结果兜底 |

触发词跨 mode 提升：`github`/`skill`/`academic`/`community` 命中即并入当前 mode 并行组（去重）。
config 落地：`wrr/config.py` 的 `MODE_DISPATCH`/`MODE_WEIGHTS`/`classify_intent`/`mode_engines`；融合 `wrr/engines/_fusion.py`；路由 `wrr/router.py:route_search_v5`。
输出 `details` 增量字段：`mode` / `fusion_method=rrf` / `weights` / 各结果 `source_tag`（envelope 与 v4 兼容）。

---

# WRR v4.0 Provider 能力矩阵（历史对照）

## 能力对比

| Provider | Search | Extract | Highlights | Similar | Citations | 备注 |
|----------|--------|---------|------------|---------|-----------|------|
| **Exa** | ✅ | ✅ | ✅ | ✅ | ✅ (via highlights) | 主引擎，Neural Search |
| **Brave** | ✅ | ✅ (简易) | ❌ | ❌ | ❌ | 降级备选 |
| **SearXNG** | ✅ | ❌ | ❌ | ❌ | ❌ | 最后降级 |
| **GitHub** | ✅ | ❌ | ❌ | ❌ | ❌ | 仓库搜索 + 三维评分，需 `GITHUB_TOKEN` |
| **Community** | ✅ | ❌ | ❌ | ❌ | ❌ | 社区聚合（OpenCLI 渠道 + last30days），结果带 `source_tag` |

## Exa 模式

| 模式 | 速度 | 质量 | 适用场景 |
|------|------|------|----------|
| `fast` | 最快 | 基础 | 事实查询 |
| `auto` | 平衡 | 标准 | 一般搜索 |
| `deep-lite` | 较慢 | 较高 | 研究查询 |
| `deep` | 最慢 | 最高 | 学术/技术深度 |

## 自动路由规则

基于查询关键词自动选择模式：
- 学术关键词 → `deep`
- 研究关键词 → `deep-lite`
- 事实关键词 → `fast`
- 其他 → `auto`

用户显式 `mode` 参数可覆盖自动路由。


## GitHub 引擎（P1 轻量版）

调用 GitHub Search API `/search/repositories`，对返回仓库按**三维综合评分**重排：

```
score = 0.40 * activity + 0.35 * popularity + 0.25 * freshness
```

| 维度 | 含义 | 计算 |
|------|------|------|
| `activity` | 最近 30 天 commit 速度 | 经 `/commits` 单仓 REST 实测（Link 头 `rel="last"` 页号），对数压缩；并发拉取、失败降级到 `open_issues_count` 代理 |
| `popularity` | 人气 | `log10(stars)` 归一 + fork/star 比例加成 |
| `freshness` | 新鲜度 | `pushed_at` 衰减：≤30 天=1.0，90 天=0.5，≥180 天=0（分段线性） |

### 触发方式
- 显式：`--provider github`（单引擎，禁用 fallback）
- 自动：查询含 `site:github.com` → 自动把 `github` 提到 fallback 链首
- fallback 链位置：`exa → brave → github → searxng`

### 认证与配置
- 需 `GITHUB_TOKEN` 环境变量（认证后 5000 req/hr；缺失时该引擎抛 `GITHUB_TOKEN not set`）
- 引擎超时：`ENGINE_TIMEOUT["github"] = 15s`
- 权重可调：`config.GITHUB_SCORE_WEIGHTS`
- 关闭实测活跃度（退化为单次 search、用 `open_issues` 代理）：`config.GITHUB_ACTIVITY_LOOKUP = False`

### CLI 示例
```bash
wrr-cli.py search "async http client" --provider github --count 5 --json
wrr-cli.py search "rust orm site:github.com"        # 自动触发 github
```

> 非目标（留 P2）：完整 5 维度评分 + 反作弊；GraphQL 批量查询（REST 已足够）。


## Community 引擎（Phase 1：社区聚合）

聚合层（非单一数据源）：多社区源**并行检索 → 统一评分 → 去重 → 排序**，结果统一为
`SearchResult` 并带 `source_tag` 标注来源。

源家族：

| 源 | 调用 | 字段（实测） | 状态 |
|----|------|------|------|
| reddit / twitter / xiaohongshu / v2ex | `opencli <chan> search <q> -f json --limit N` | reddit: score/comments/created_utc；xhs: likes/published_at | 经实测的快速核心，需 OpenCLI 浏览器桥连接（`opencli doctor`） |
| last30days_en / last30days_cn | `python3 last30days.py --emit json --quick <q>` | 解析 clusters（title/score/sources/representative_ids） | 重型研究 CLI，**默认按需启用**（见下） |

### 统一评分
```
score = 0.40*engagement + 0.35*recency + 0.25*quality
```
- engagement：点赞/分数对数压缩（按源 `eng_max` 归一）
- recency：≤24h=1.0 / ≤7d=0.7 / ≤30d=0.3 / 更旧=0（未知时间=0.5）
- quality：评论/互动比例（comments/engagement，20% → 1.0）

### 去重
URL 规范化（去 query/fragment/尾斜杠）相等，或标题 `\w+` 分词 Jaccard 相似度 > `COMMUNITY_DEDUP_THRESHOLD`（0.80）。

### 触发与源选择
- 显式：`--provider community`
- 自动：查询含 `site:reddit.com|news.ycombinator.com|twitter.com|x.com|zhihu.com|weibo.com` → 把 community 提到 fallback 链首
- fallback 链位置：`exa → brave → github → community → searxng`
- 源选择：`site:` 命中 → 精确子集；否则 → `COMMUNITY_DEFAULT_SOURCES`（reddit/twitter/xiaohongshu/v2ex）
- **last30days 门控**（重型，常超预算）：仅当 `site:news.ycombinator.com|zhihu.com|weibo.com`、研究意图关键词（trending/30天/最近/本周/this week），或 `config.COMMUNITY_INCLUDE_LAST30DAYS=True` 时启用

### 超时与容错
- 每源 `COMMUNITY_SOURCE_TIMEOUT=10s`、引擎 `COMMUNITY_TOTAL_TIMEOUT=15s`（注：经 WRR fallback 调用时，search 总预算 10s 为实际上限）
- 各源**独立失败**互不影响；全部失败才抛 `EngineError` 让链路降级到 searxng

### CLI 示例
```bash
wrr-cli.py search "python site:reddit.com" --provider community --json
wrr-cli.py search "rust async" --provider community
wrr-cli.py search "trending ai 最近" --provider community    # 触发 last30days
```

> 非目标（Phase 2）：动态源探测 / 薄源重试 / Weighted RRF / 社区内容深度抓取。

## Community 引擎

| 源 | 类型 | 触发条件 | 状态 |
|----|------|----------|------|
| Reddit | OpenCLI | `reddit` 关键词 / 默认 | 需 OpenCLI Extension |
| Twitter/X | OpenCLI | `twitter` 关键词 / 默认 | 需 OpenCLI Extension |
| 小红书 | OpenCLI | `小红书`/`xhs` 关键词 | 需 OpenCLI Extension |
| V2EX | OpenCLI | `v2ex` 关键词 | 需 OpenCLI Extension |
| last30days-en | Python CLI | `hackernews`/`hn` 关键词 | 已克隆 |
| last30days-cn | Python CLI | 中文社区关键词 | 已克隆 |

评分：engagement 40% + recency 35% + quality 25%
