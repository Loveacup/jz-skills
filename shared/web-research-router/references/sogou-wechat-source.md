# Sogou WeChat Search Source

> 🆕 v1.0 (2026-06-02) — weixin-search-mcp v0.2.1 verified.
> WRR 微信内容搜索源：搜索 + 解密 + 抓取完整链路。

## Engine Status

| Engine | Type | Status | Cost |
|--------|------|--------|------|
| **weixin-search-mcp** (PyPI) | MCP server | ✅ 已验证 | Free (no API key) |
| Scrapling CLI stealthy-fetch | CLI tool | ✅ 已验证（张睿 2026-06-01） | Free (local Chromium) |

## Two-Phase Architecture

```
Query → weixin-search-mcp
           ├── sogou_weixin_search(query) → 10 articles (title + encrypted link)
           ├── get_real_url_from_sogou(link) → real mp.weixin.qq.com URL
           │
           └── Content fetch (dual path):
               ├── Path A: get_article_content(real_url) → plain text
               │   Risk: hardcoded Cookie may expire
               └── Path B: scrapling extract stealthy-fetch real_url → Markdown
                   Risk: requires Chromium (`scrapling install`)
```

## Installation

```bash
# Path A: weixin-search-mcp
uv pip install --python 3.12 weixin-search-mcp

# Path B: Scrapling CLI
pip install "scrapling[all]"
scrapling install  # downloads Chromium
```

## Quick Usage

### Search + decrypt

```python
from weixin_search_mcp.tools.weixin_search import sogou_weixin_search, get_real_url_from_sogou

results = sogou_weixin_search("AI大模型", page=1)
# → [{title, link, real_url, publish_time, page}, ...]
```

### Fetch content (Path A)

```python
from weixin_search_mcp.tools.weixin_search import get_article_content
content = get_article_content(real_url, referer=sogou_link)
```

### Fetch content (Path B — CLI)

```bash
scrapling extract stealthy-fetch \
  "https://mp.weixin.qq.com/s/..." \
  article.md \
  --ai-targeted --headless
```

## WRR Integration

| Mode | Trigger | Engine Priority |
|------|---------|----------------|
| **discovery** | query 含 微信/公众号/订阅号 | weixin-search-mcp → Exa/Brave |
| **grounding** | 微信文章 claim 验证 | weixin-search-mcp → article content |
| **research** | 中文深度调研需公众号视角 | weixin-search-mcp → Scrapling fallback |

## source_map Fields

```json
{
  "via": "weixin-search-mcp",
  "stability": "volatile",
  "fallback": "scrapling-cli",
  "fetchable": true,
  "fetch_method": "scrapling extract stealthy-fetch"
}
```

## Risks

1. **Cookie expiry** — weixin-search-mcp hardcodes Cookie in source; may break anytime
2. **Rate limiting** — Sogou detects high-frequency requests; keep ≤1 req/s
3. **Scrapling CLI not installed** — needs `pip install scrapling[all] && scrapling install` before use
4. **No API key rotation** — single Cookie, no fallback if blocked

## 🔬 Why Scrapling Failed Before (Root Cause)

> 2026-05-31 tests failed; 2026-06-01 Zhang Rui succeeded. Same tool, different access path.

| Dimension | Failed Test (05-31) | Success (06-01 Zhang Rui) |
|-----------|---------------------|---------------------------|
| **Entry URL** | Sogou encrypted `/link?url=...` | Direct `mp.weixin.qq.com/s/...` |
| **Anti-bot layer** | Sogou 302 redirect → antispider | WeChat UA/Referer check |
| **Bypass method** | None (bare HTTP) | `stealthy-fetch` + Google referer + headless |
| **Invocation** | Python `Fetcher.get()` / `StealthyFetcher.fetch()` | CLI `scrapling extract stealthy-fetch` |
| **Result** | ❌ antispider at redirect stage | ✅ HTTP 200, ~1s, 3.2KB Markdown |

**Key insight:** Scrapling CAN bypass WeChat's anti-bot (UA + Referer), but CANNOT bypass Sogou's encrypted-link antispider. The fix is NOT a different Scrapling config — it's using `weixin-search-mcp` to decrypt the Sogou link FIRST, then feeding the real `mp.weixin.qq.com` URL to Scrapling CLI.

## GitHub Project Landscape (2026-06-02)

Only **one** viable 2026 project for the full pipeline:

| Project | Stars | Status | Pipeline |
|---------|-------|--------|----------|
| **fancyboi999/weixin_search_mcp** | 76 | ✅ Active (v0.2.1, 2026-03) | Search + Decrypt + Content |
| chyroc/WechatSogou | 1.8k | ❌ Dead (Werkzeug compat) | Search only |
| iberryful/weixin_sogou | 753 | ❌ Abandoned (2015) | Search only |
| jaryee/wechat_sogou_crawl | 230 | ⚠️ Stale (2023) | Search only |
| reveever/go-weixin-sogou | 10 | ✅ Active (2026-04) | Go; Search + Account |
| ptbsare/sogou-weixin-mcp-server | 15 | ⚠️ 6 commits | Search only, no decrypt |

## Monitoring

- Weekly smoke test: `sogou_weixin_search("测试")` → expect ≥5 results
- Alert: Telegram notification if smoke test fails 3 consecutive days
- Fallback: disable weixin-search-mcp, mark WeChat source as unavailable

## References

- [weixin-search-mcp GitHub](https://github.com/fancyboi999/weixin_search_mcp) ⭐76
- [weixin-search-mcp PyPI](https://pypi.org/project/weixin-search-mcp/) v0.2.1
- [weixin.sogou.com](https://weixin.sogou.com) — Sogou WeChat search homepage
- [Scrapling skill](/devops/scrapling) — CLI stealthy-fetch for WeChat content
- WRR CQI Plan: `02-Plan/web-research-router 持续质量改进计划.md` §2.2
