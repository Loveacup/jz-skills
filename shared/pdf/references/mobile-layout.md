# Mobile PDF Layout · 移动版 PDF 布局

> **Read when:** 需要生成手机竖屏 PDF（早新闻、简报、推送卡片）时；或需要 430×932px 规格参考时。

## 规格

| 属性 | 值 | 说明 |
|------|-----|------|
| CSS 视口 | 430×932px | iPhone 14 Pro Max 竖屏 |
| PDF 页面 | ~242×518pt | Playwright 自动计算 |
| 正文字号 | 16px | 手机可读最小标准 |
| 标题字号 | 22px | H1 正文标题 |
| 摘要字号 | 14px | H4 / 副标题 |
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

## 代码块 & 表格（窄页自适应，2026-06-01 优化）

窄页（430px，正文区 ≈338px）下代码块和表格是质量重灾区。三项核心修复：

1. **代码块文字隐形 → 已修。** 基础模板的 `pre code.hljs { color:#ecf0f1 !important }`（深色主题用的近白色）在 newsletter 奶油底上几乎不可见，导致 ```` ```text ```` 这类无语法高亮的纯文本块整块"消失"。newsletter.css 现以 `pre code, pre code.hljs { color:#1b1a17 !important }` 覆盖。**新建浅色主题时务必照抄此覆盖**（academic/dark 已有各自覆盖，minimalist/warm-academic 仍有此隐患）。
2. **ASCII 树状图被打散 → 已修。** 87 字符宽的对齐图（`│├──└──`）被 `white-space:pre-wrap` 强制换行后对齐结构崩坏。`md2pdf_chrome.py` 的 JS 现对每个 `<pre>` 改用 `white-space:pre`（不换行）+ 按最宽行**等比缩小字号**至刚好容纳（下限 7px），保留对齐；仅当 7px 仍超宽才回退到 `pre-wrap`。`pre code { font-size:inherit }` 是缩放生效的前提。
3. **英文单词被拆断 + 表格溢出 → 已修。** `overflow-wrap:anywhere` 会把列 min-content 算成 1 字符、饿死标签列（`wechatsogou` → `wech/atso/gou`）。改用 `overflow-wrap:break-word`（保留整词宽度）；JS 再按 token 长度细分（>18 字符的 URL 允许 anywhere、短标识符保持整词），并按**父容器宽度**判断溢出后逐级缩小字号（下限 8px），末位才整体 anywhere 兜底。

> 注意：代码块多的窄页表格会自动缩到 ~8px 以容纳全部内容（不截断优先于字号）。普通表格不受影响，维持 13/11/10px。

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
