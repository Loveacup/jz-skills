---
name: md-to-pdf
description: 礼部 Markdown→PDF 渲染 — 基于 md-bookify(MCP) + any2pdf(CJK) + mdPress 模式，手机版/桌面版/EPUB 多格式输出
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [protocol, pdf, markdown, document-generation]
    source: [danielefavi/md-bookify, lovstudio/any2pdf, yeasy/mdPress]
---

# 礼部 Markdown→PDF 渲染

参考项目：
- **danielefavi/md-bookify** — MCP server，MD→PDF/EPUB，专为 AI agent 设计
- **lovstudio/any2pdf** — MD→专业排版 PDF，CJK 支持，一个 Python 文件
- **yeasy/mdPress** — MD→PDF/Site/HTML/ePub，一键多格式

## 输出格式

| 格式 | 命令示例 | 用途 |
|------|---------|------|
| 手机 PDF | 430×932px CSS, 242×518pt PDF | 早新闻、简报、推送 |
| A4 PDF | A4 210×297mm | 报告、文档、存档 |
| EPUB | 自适应 | 电子书阅读器 |
| HTML | 单文件 | 邮件/分享 |

## 手机版 PDF 规格

```
视口: 430px × 932px (CSS)
页尺寸: ~242×518pt (PDF)
字号: 正文 15px, 标题 20px, 摘要 13px
配色: #fffdf8 背景, #1b1a17 正文, #b47a32 强调
页脚: Alex Cai · 页码 · 日期
```

## 样式预设

- `newsletter` — 早新闻手机版（当前基准）
- `academic` — 学术报告，Palatino+宋体
- `minimalist` — 极简，低对比度
- `warm-academic` — 暖色调学术风

## MCP 工具接口

agent 可通过 MCP 调用渲染：
```json
{
  "tool": "convert_markdown_to_pdf",
  "input": "report.md",
  "output": "report.pdf",
  "style": "newsletter",
  "format": "mobile"
}
```

## 集成

- 早新闻 → `newsletter` mobile PDF
- 金融报告 → `academic` A4 PDF  
- 制度文档 → `minimalist` A4 PDF
