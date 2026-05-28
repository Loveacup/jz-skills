# SearXNG Engine Diagnostics

> 2026-05-28 实测。SearXNG 注册 245 个引擎 ≠ 245 个都能用。每次环境变更后重新跑此诊断。

## 快速诊断脚本

```bash
# 逐引擎测试
for engine in bing qwant brave duckduckgo google startpage baidu 360search arxiv wikipedia; do
  result=$(curl -s "http://127.0.0.1:32080/search?q=test&format=json&engines=$engine" 2>&1 | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('results',[])))")
  printf "  %-15s %sr\n" "$engine:" "$result"
done
```

## 本环境实测（2026-05-28）

| 引擎 | 结果数 | 可用？ | 备注 |
|------|:--:|:--:|------|
| bing | 10 | ✅ | 主力引擎 |
| baidu | 9 | ✅ | 中文补强 |
| qwant | 10 | ⛔ | 引入 spam（lj.im 等），禁用 |
| arxiv | 10 | ⚠️ | 仅对泛 query 有结果，精确 query 常 0r |
| wikipedia | 1 | ⚠️ | 结果极少 |
| 360search | 3 | ⚠️ | 结果少 |
| brave | 0 | ❌ | — |
| duckduckgo | 0 | ❌ | — |
| google | 0 | ❌ | — |
| startpage | 0 | ❌ | — |
| bilibili | 0 | ❌ | — |
| google scholar | 异常 | ❌ | JSON 解析错误 |

## 推荐引擎组合

| 场景 | engines 参数 | language |
|------|-------------|----------|
| 英文搜索 | `bing` | `en` |
| 中文搜索 | `bing,baidu` | `zh-CN` |
| 学术搜索 | `bing` + Exa / arXiv MCP | `en` |

## 关键约束

- **必须设 `language` 参数**：不设 → 跨语言噪音（日文词典、游戏结果）
- **禁用 qwant**：引入垃圾域名
- **SearXNG HTTP 非 MCP**：用 `curl` + `format=json`，非 `mcp_searxng_*` 工具
- **无 URL read 引擎**：抓页面用 `mcp_exa_web_fetch_exa`
- **实例地址**：`http://127.0.0.1:32080`
