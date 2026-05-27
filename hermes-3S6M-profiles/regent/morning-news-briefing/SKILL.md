---
name: morning-news-briefing
description: |
  每日早新闻简报 v2.0 — 多源并行检索（≥50 家来源）、按板块汇编、手机版 PDF 交付。
  五大板块：中东/美国/中国/国际/市场。每条新闻 ≥2 个独立来源，带可验证 URL。
  默认输出 430×932px 视口手机版 PDF（浅色 newsletter 风格，#fffdf8 / #1b1a17 / #b47a32）。

  Use when: user says 早新闻 / 新闻简报 / 今日要闻 / morning news / 生成早报.
  DO NOT use for: single-topic deep dives, non-news content, A4 reports (unless explicitly requested).
version: 2.0.0
author: Hermes Agent — regent profile (v2.0 compliance review)
---

# 早新闻简报 v2.0

每日多源并行检索 → 五板块汇编 → 手机版 PDF 交付。

## 🚨 Red Flags: Don't Ship a Broken Briefing

| Excuse | Why it's wrong |
|--------|---------------|
| "I'll use yesterday's template, same style" | Style continuity gate: must reference last accepted baseline. Free-form styling = broken brand. |
| "Only 30 sources today, that's close enough" | ≥50 sources mandatory (中国 ≥15, 美国 ≥10, 国际 ≥8). Every article ≥2 independent sources. |
| "The analysis is thin today, I'll pad it" | ≥4 analysis items, each 前提→推理→结论. No hedging ("一方面…另一方面…"). |
| "I'll just check text.find() for sentinels" | Full PyMuPDF extraction required. 7 sentinel checks all mandatory before delivery. |
| "The PDF is at the workspace path, user can find it" | Deliver the PDF file directly. Never reply with just a file path. |

## 🔀 Decision Tree

```
"早新闻" / "morning news" triggered?
├── Step 1: Parallel search — 5 sections via 5 sub-agents (delegate_task)
│   Use web_search + web_extract across 50+ Chinese/US/international sources
├── Step 2: Assemble — merge + deduplicate + annotate sources (S01–SNN)
├── Step 3: Render — mobile PDF (base style from last accepted variant)
├── Step 4: Verify — PyMuPDF full extraction, 7 sentinels
└── Step 5: Deliver — send PDF file directly
```

## Default Delivery

**Mobile PDF** (430×932px viewport, 242×518pt PDF, single-column, card-style news).

Style baseline: newsletter/editorial — cream `#fffdf8`, dark gray `#1b1a17`/`#202124`, bronze `#b47a32`. Must reuse last accepted variant; no free-form color experimentation. Current baseline reference: `references/pdf-layout-accepted-variants.md`

## Sections (Fixed)

1. 🔥 **头条/中东** — Iran, Hormuz, UAE
2. 🇺🇸 **美国** — domestic, economy, Congress, tech
3. 🇨🇳 **中国** — politics, economy, tech, diplomacy, society
4. 🌍 **国际** — Russia-Ukraine, Asia-Pacific, Africa, LatAm
5. 📊 **市场** — oil, equities, forex

## Source Requirements

- **Total ≥50 outlets** (中国 ≥15, 美国 ≥10, international ≥8)
- **Every article ≥2 independent sources** with verifiable URLs
- Chinese: 新华社, 中新网, 人民日报, 央视, 环球时报, 财新, 澎湃, 界面, 证券时报, 第一财经, 21世纪经济报道, 经济观察报, 北京商报, 每日经济新闻, China Daily, 联合报, 中时
- US: NYT, WSJ, Washington Post, AP News, CNN, Axios, Politico, CNBC, ABC News, Bloomberg
- International: BBC, Al Jazeera, Reuters, CBC, France 24, Guardian, Le Monde, DW

## Content Structure (7 Sentinels — Missing Any = Rework)

| # | Sentinel | Requirement |
|---|----------|------------|
| 1 | **Executive Summary** | Standalone card on first page, 3-5 bullet points after cover title |
| 2 | **News Articles** | ~20 items, 2-4 sentences core info + `📡 来源` per item |
| 3 | **🔍 Analysis** | Premise→Reasoning→Conclusion, ≥4 items, no hedging |
| 4 | **📌 Daily Summary** | Standalone card, core tension one-liner + key trends |
| 5 | **Source Ledger** | S01–Snn numbered list, outlet name + verifiable URL, no bare numbers |
| 6 | **Alex Cai** | Cover/header attribution, not just footer |
| 7 | **Date** | Current date, format: 2026年5月27日 |

## Format Gate (Mobile PDF 8 Commandments)

1. Source format: in-card `来源：S01 媒体名 · S02 媒体名`; appendix S01–SNN ledger
2. All 7 sentinels verified via PyMuPDF full extraction (not just `text.find()`)
3. Cover attribution: Alex Cai on cover/header (not just end-of-document footer)
4. Right margin ≥16px (12px crowds card borders to page edge)
5. Visual PNG spot-check: cover/analysis/summary/sources pages
6. Executive summary bullets: 3-5 distinct items (not dense paragraph)
7. Avoid orphans: no page break immediately after heading
8. Source list: numbered lines S01–SNN (not concatenated paragraph)

Full details: `references/mobile-pdf-layout-eight-commandments.md`

## Quality Standards

- Data precision: CPI/employment/GDP cite original sources (BLS, 国家统计局)
- Timeliness: label dates (17日)(18日), exclude >3-day-old news
- URLs accessible, non-aggregated, non-fabricated

## Style Continuity

- Before rendering: locate last accepted baseline variant
- Reference baseline explicitly: "replicate this style"
- No free-form new colors/layouts
- Audit: compare palette, dark pixel ratio, newsletter elements
- Gate: `references/style-continuity-gate.md`

## Anti-Patterns

- Using old template/color scheme
- Hedging analysis with "on one hand… on the other…"
- Compressing news items to reduce page count
- Spot-checking only 8 sources or checking status without artifact
- Replying with file path instead of delivering PDF directly

## References

| File | Content |
|------|---------|
| `references/pdf-layout-accepted-variants.md` | Accepted A4 + Mobile CSS baselines |
| `references/mobile-pdf-layout-eight-commandments.md` | 8-commandment verification checklist |
| `references/mobile-pdf-visual-qa-lessons.md` | Visual QA lessons learned |
| `references/style-continuity-gate.md` | Style continuity enforcement gate |
| `references/mobile-pdf-format-continuity-2026-05-26.md` | Format continuity rework process |
| `references/dailybrief-lessons.md` | Daily brief operational lessons |
| `references/morning-news-url-quality-lessons.md` | URL quality enforcement lessons |

## ✅ Verification Checklist (Before Delivery)

- [ ] All 7 sentinels verified via PyMuPDF full-text extraction?
- [ ] ≥50 sources used (中国 ≥15, 美国 ≥10, 国际 ≥8)?
- [ ] Every news item has ≥2 independent sources?
- [ ] Analysis section: ≥4 items, each 前提→推理→结论, no hedging?
- [ ] Source ledger: S01–SNN numbered with outlet names + verifiable URLs?
- [ ] "Alex Cai" on cover/header?
- [ ] Visual PNG spot-check on 4 key pages passed?
- [ ] PDF file delivered directly (not just path)?

---

## Deployment & Sync

This is a **regent profile** skill. After ANY update:

```bash
cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: morning-news-briefing" && git push
```
