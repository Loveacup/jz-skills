---
name: xhs-crawler
description: |
  小红书内容提取与深度分析。支持链接提取（默认 CloakBrowser）、关键词搜索、创作者主页爬取。
  通过 CDP/CloakBrowser 自动化提取正文、评论、轮播图 OCR（DeepSeek-OCR-2），
  生成 7 章节结构化 Obsidian 知识资产报告。

  Use when: user provides 小红书 link, or says 小红书 / xhs / rednote / xiaohongshu / 解析小红书 / extract xhs.

  DO NOT use for: non-小红书 content, generic web scraping, simple URL previews.
version: 2.0.0
author: OpenClaw → Hermes (v2.0 compliance review, slimmed from 813 lines)
---

# 小红书内容提取器 v5 → v2.0

三种模式：链接提取（默认 CloakBrowser 反检测）、关键词搜索、创作者分析。
提取后由 agent LLM 按 `references/xhs-report-prompt.md` 生成知识资产报告。

## 🚨 Red Flags: Don't Ship a Broken Extraction

| Excuse | Why it's wrong |
|--------|---------------|
| "I'll just use web_extract, it's faster" | Generic tools lack 小红书 login state, comment loading, carousel OCR. Use CloakBrowser mode. |
| "Only 3 comments, I'll skip the analysis section" | Even sparse data gets analyzed. Mark with `[数据不足]` annotation, don't skip the section. |
| "The text looks complete, I'll skip OCR" | Carousel images often contain critical content not in the text body. OCR is mandatory. |
| "I'll paraphrase the comments instead of quoting" | 🔴 Use exact quotes with attribution. Never rewrite or summarize user comments. |
| "I'll save to the generic clawd path" | Output MUST go to Obsidian `00-Inbox/`. Wrong path = lost report. |

## 🔀 Decision Tree

```
Received 小红书 request?
├── Link extraction → CloakBrowser mode (default, anti-detection, persistent login)
│   ├── Step 1: Pre-check (CDP port, login state, env vars)
│   ├── Step 2: Data extraction (title, author, body, tags, interactions)
│   ├── Step 3: Carousel OCR (screenshot → DeepSeek-OCR-2 → merge)
│   ├── Step 4: Comment loading (scroll until no new, max 15 scrolls, dedup)
│   ├── Step 5: Report generation (7 mandatory sections + data citation standards)
│   └── Step 6: Cleanup + verify (delete temp files, size check >5KB)
├── Keyword search → xhs_api.py (xhshow signing)
├── Creator analysis → xhs_api.py (profile + note list)
└── Fallback: CDP mode → API mode → partial data (never fail silently)
```

## P0 Constraints (Mandatory)

### Output: 7 Required Sections

| # | Section | Requirement |
|---|---------|------------|
| 0 | Meta | AI title, one-line value, author, tags, interaction data |
| 1 | Logic Chain | Surface logic + underlying logic |
| 2 | Comments Intelligence | 6 emotion labels + quality discussion excerpts |
| 3 | Key Insights | ≥2 positive insights + 1 counter-intuitive point |
| 4 | Deep Dive | Flexible organization by content type |
| 5 | Highlights & Quotes | Verbatim quotes with context |
| 6 | Knowledge Graph & Action | Concept mapping + action items + critical review |

### Data Citation Standards

- ✅ `"评论原文" —— 用户名（👍 123，情绪：赞同）`
- ❌ `有网友说大概意思是...`（禁止改写或概括）
- ⚠️ Annotations: `[数据不足]` / `[获取失败]` / `[需要登录]` / `[不支持]`

### Privacy Red Lines

- **NEVER** store or output: cookies, session IDs, tokens, phone numbers, addresses
- Cookies only in `~/.xhs_cookie`, never in logs
- Use nicknames not user IDs in reports

## CloakBrowser Mode (Default)

```bash
python3 scripts/xhs_cloak_extractor.py "<url>"
```

Anti-detection (webdriver=false, persistent login, ~1 year cookie validity). Carousel uses direct CDN download + DeepSeek-OCR-2. See `references/cloakbrowser-mode.md` for full details.

## Other Modes

| Mode | Command | Use case |
|------|---------|----------|
| Link (CDP fallback) | `python3 scripts/xhs_extractor.py "<url>"` | When CloakBrowser unavailable |
| Keyword search | `python3 scripts/xhs_api.py search "<keyword>"` | Topic discovery |
| Creator analysis | `python3 scripts/xhs_api.py creator "<user_id>"` | Creator profiling |

## Data Integrity

| Metric | Standard | Warning threshold |
|--------|----------|-------------------|
| Content length | 100-5000 chars | < 50 chars |
| Comment count | Close to page display | < 50% of displayed |
| Report size | > 5 KB | < 5 KB |

Detailed standards and self-check script: `references/data-integrity.md`

## Scripts

| Script | Function |
|--------|----------|
| `xhs_cloak_extractor.py` ⭐ | CloakBrowser mode (default, anti-detection) |
| `xhs_extractor.py` | CDP mode (Playwright fallback) |
| `xhs_api.py` | API client (xhshow signing for search/creator) |
| `xhs_carousel_ocr.py` | Carousel OCR (DeepSeek-OCR-2) |
| `cookie_manager.py` | Cookie management (~/.xhs_cookie) |

Architecture: `references/ARCHITECTURE.md` | CloakBrowser details: `references/cloakbrowser-mode.md`

## ✅ Verification Checklist

- [ ] All 7 mandatory sections present?
- [ ] Comments use exact quotes with attribution (no paraphrasing)?
- [ ] Carousel OCR completed (not skipped)?
- [ ] Report size > 5 KB?
- [ ] Output saved to Obsidian `00-Inbox/` (not clawd path)?
- [ ] Temporary files (PNG/JSON/TXT) cleaned from `/tmp/xhs_analyzer/`?
- [ ] No cookies/sessions/tokens in output or logs?

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: xhs-crawler" && git push`
