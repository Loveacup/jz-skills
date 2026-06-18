# WRR MCP 整合研究 — 2026-06-07 三方评估摘要

> 来源：CC agent team (4 agent) + 太子 (regent) 独立评估，Hermes 编排。
> 完整报告：`/tmp/wrr-consolidation-analysis.md` (374行, 31KB) · `/tmp/wrr-consolidation-regent-analysis.md` (341行, 20KB)
> 四份明细：`/tmp/wrr-agent-api.md` · `/tmp/wrr-agent-ops.md` · `/tmp/wrr-agent-arch.md` · `/tmp/wrr-agent-cost.md`
> 关联 CQI: `Obsidian: 02-Plan&CQI/web-research-router 持续质量改进计划.md` §线程E

## 结论

**方向 B (CLI 核心) + 薄 C shim + 模块化 engine-registry 架构**。分 3 阶段：阶段 0 即时止血 → 阶段 1 wrr-core+CLI → 阶段 2 薄 MCP shim(可选)。

## 杀手锏证据

1. **82 个 MCP 进程 / 1.56 GB**（npm exec 双层包装）。95% 纯浪费。历史峰值 1436 searxng / 2.5GB。
2. **`extension.ts` 已是方向 C 雏形** — Exa/Tavily/Brave 已收敛为统一 `web_search(query, provider)`，根本没用 npm MCP 包。当前堆积来自已被取代的旧 MCP 路径。
3. **token 税 334k/天** — MCP schema 每轮 1670 token，CLI 只消 ~120（省 99.96%）。
4. **配置 bug**：extension.ts 读 `BRAVE_SEARCH_API_KEY`，但 .env 叫 `BRAVE_API_KEY`。
5. **SearXNG 已损坏**：json 搜索恒等 5.02s（9 个上游全 timeout），须独立 ≤2s 超时 + 降级为抓取专用。

## 各搜索引擎 API 实测 (2026-06-07)

| 引擎 | 端点 | 搜索延迟 | 计费 | Rate limit |
|------|------|---------|------|-----------|
| Exa | POST api.exa.ai/search, x-api-key | 1.25s | $0.007/搜 | doc 未列 |
| Brave | GET api.search.brave.com, X-Subscription-Token | 0.77s | $5/1k | 1 req/s + 2000/月 |
| Tavily | POST api.tavily.com/search, Bearer | 2.23s | 1 credit/basic | 100-1000 RPM |
| SearXNG | GET 127.0.0.1:32080/search | json 5.02s | 免费 | 实例已损坏 |

## 四方评分对比

| 方向 | API层 | 运维层 | 架构层 | 成本层 | 均分 |
|------|:---:|:---:|:---:|:---:|:---:|
| A MCP合并 | 4.0 | 3.86 | 2.85 | 3.5 | 3.55 |
| **B CLI化** | **5.0** | **4.86** | 3.95 | **4.8** | **4.65** |
| C 混合 | 3.2 | 4.0 | **4.75** | 3.0 | 3.74 |

API/运维/成本三层推荐 B；架构层推荐 C。调和：B 核心 + 薄 C shim（共享引擎底座，双接口）。

## 模块化架构设计

```
wrr-core/
├── engine-registry.json     ← 声明式真源（加引擎=加1个JSON条目）
├── engines/                 ← 一引擎一 adapter 文件
└── core/                    ← 路由纯函数，零引擎知识

wrr-cli.py                   ← 主接口（高频无头：cron/晨报/regent）
薄 MCP shim                  ← 可选（交互式 session 需要时起）
```

硬约束：`grep -r "exa\|brave\|tavily\|searxng" core/` 必须为空。

## AnySearch 借鉴要点

| 可借鉴 | 不可借鉴 |
|--------|---------|
| constants.json 单一真源 | 单引擎 SaaS 黑盒 |
| doc 命令自举 | 4 CLI 各自硬编码不同域列表 |
| runtime.conf 缓存（引擎可用性） | Bash grep 抠 JSON |
| 4 运行时 fallback 可移植性 | 后端搜索质量不可见 |

反模式教训：AnySearch 的 domain 列表在 Python/Node/Bash 三个实现里各不一致，WRR 必须用 registry 统一。
