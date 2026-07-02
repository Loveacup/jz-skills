# Mobile PDF Layout · 移动版 PDF 布局

> **Read when:** 需要生成手机竖屏 PDF（早新闻、简报、推送卡片）时；或需要 430×932px 规格参考时。

## 规格

| 属性 | 值 | 说明 |
|------|-----|------|
| CSS 视口 | 430×932px | iPhone 14 Pro Max 竖屏 |
| PDF 页面 | ~242×518pt | Playwright 自动计算 |
| 正文字号 | 15px | 手机可读 |
| 标题字号 | 20px | H1 正文标题 |
| 摘要字号 | 13px | H4 / 副标题 |
| 行高 | 1.8 | CJK 防重叠 |
| 卡片间距 | ≥12px | |

## 配色（newsletter 风格）

| 角色 | 色值 | 用途 |
|------|------|------|
| 背景 | `#fffdf8` | 奶油底 |
| 正文 | `#1b1a17` | 深灰 |
| 强调 | `#b47a32` | 古铜金 |
| 二级标题 | `#b47a32` | H2 用 |
| 引用 | `#faf6ef` 底 | blockquote |

## 使用

```bash
python scripts/md2pdf_chrome.py morning-news.md output.pdf \
  --page-size 430x932 --theme newsletter
```

## 页码

`--page-size 430x932` 自动适配页脚 `— N / M —` 格式，字号 9px #888。

## 集成

- **早新闻 morning-news-briefing v4.0** → `--page-size 430x932 --theme newsletter`
- **简报/推送** → 同 newsletter 风格
- 默认（A4）保持不变，显式传 `--page-size` 才切移动版

## 从 md-to-pdf 吸收

本文件源自 `hermes-3S6M-profiles/protocol/md-to-pdf`（已归档）的移动版规格。原 skill 仅 62 行规格文档，无实现代码。`shared/pdf` 现已完全覆盖其全部能力：
- Mobile PDF → `--page-size 430x932` ✅
- Newsletter 风格 → `scripts/themes/newsletter.css` ✅
- A4 PDF → 默认 ✅
- EPUB → 未实现（原 skill 也未实现，仅提及）
