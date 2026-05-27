---
name: web-research-router
description: "Pi 专用的多引擎搜索路由。通过 web_search/web_fetch 工具路由到 Exa/Tavily/Brave，自动选引擎+交叉验证。当用户需要搜索、检索、查找、调研、核实、找资料时使用。不要用于读取本地文件、编辑代码、或不涉及外部信息检索的任务。"
version: 3.0.0-pi
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  tags: [search, research, router, exa, tavily, brave, pi-extension]
---

# web-research-router (Pi Edition)

Pi 的多引擎搜索路由 — 通过 TypeScript 扩展注册 `web_search` / `web_fetch` 两个 MCP 工具，底层路由到 Exa / Tavily / Brave。

---

## 🚨 Red Flags: 搜索前必读

| 借口 | 为什么不行 |
|------|-----------|
| "这查询很简单，直接 `web_search` 就行" | 必须指定 provider 参数路由。不指定=随机引擎=不可靠 |
| "我已经知道答案了" | 训练数据有时效性。API 版本/价格/日期会变 |
| "skill 已经加载了，够了" | 加载≠执行。看菜单≠吃了饭 |
| "等会再交叉验证" | 延迟验证=永不验证。重要事实必须≥2引擎 |

---

## 🔀 决策树

### Step 1: 本地记忆优先

```
memory_search → session_search → Obsidian vault
    ↓ 无结果？
Step 2
```

### Step 2: 判断意图，选模式

| 意图 | 模式 | 主引擎 | 交叉验证 |
|------|------|--------|----------|
| 找/有没有/搜一下 | discovery | Exa | Brave |
| 核实/确认/真的吗 | grounding | Tavily | Brave |
| 调研/对比/分析 | research | Exa | Brave + fetch |
| 论文/文献/SOTA | academic | Exa | Brave |
| 看源码/GitHub | GitHub | Exa → gh CLI | 见 github-code-explorer |

### Step 3: 执行 — 必须指定 provider

```python
# ✅ 正确
web_search(query="...", provider="exa")
web_fetch(url="...", provider="exa")

# ❌ 错误 — 不指定 provider
web_search(query="...")
```

### Step 4: 输出 Source Map

每次研究任务输出：Mode → Query → sources → Confirmed/Inferences/Conflicts

---

## Pi 工具速查

| 工具 | 参数 | 说明 |
|------|------|------|
| `web_search` | query, max_results(1-20), provider(exa/tavily/brave) | 多引擎搜索 |
| `web_fetch` | url, provider(exa/tavily/brave), max_characters | 提取页面内容 |

> 扩展代码: [extension.ts](extension.ts) — Pi SDK 实现，注册工具+路由逻辑

---

## 引擎选择速查

| 引擎 | 适用 | 不适用 |
|------|------|--------|
| Exa | 学术/技术/发现/找项目 | 实时新闻、中文社交 |
| Tavily | 事实核实/新闻/实时 | 学术论文深度搜索 |
| Brave | 通用/交叉验证/广度 | 深度学术语义搜索 |

---

## 配置

需要环境变量（在 `~/.pi/agent/.env` 或系统环境变量）：

```
EXA_API_KEY=...
TAVILY_API_KEY=...
BRAVE_SEARCH_API_KEY=...
```

---

## 验证清单

- [ ] 搜索前检查了本地记忆（memory_search）
- [ ] 选对了模式和引擎
- [ ] 重要事实 ≥2 引擎交叉验证
- [ ] 输出了 Source Map
- [ ] 所有事实有来源支撑（非训练数据）
