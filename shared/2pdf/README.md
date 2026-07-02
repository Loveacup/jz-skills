# 2pdf Skill

一站式 PDF 处理技能，为 Claude Code / Codex / Cursor / Hermes 提供完整的 PDF 文档处理能力。

> **源仓库**: [Loveacup/jz-skills](https://github.com/Loveacup/jz-skills) · 路径 `shared/2pdf`
> **更新方式**: `git pull` 拉取最新后跑 `python3 scripts/md2pdf_chrome.py --setup`（幂等，自动补齐环境与 vendor 资源）；mac 端部署走 `deploy/sync-all.sh`，Windows 端 pull 后直接 `--setup` 即可。

## 核心功能

**Markdown → PDF**
将 Obsidian 风格 Markdown 转换为专业排版的 PDF。通过 Chrome headless 渲染，完美支持中日韩文字、Mermaid 图表、26 种 Callout 样式。内置 Relay 工作流，自动分析文档结构并优化排版。

**PDF 文档操作**
合并、拆分、旋转页面、提取文本与表格、添加水印、密码保护。

**表单处理**
读取 PDF 表单字段并自动填写。

**OCR 识别**
扫描件文字提取。

## 目录结构

```
pdf/
├── SKILL.md                    # 技能定义与工作流指南
├── scripts/
│   ├── md2pdf_chrome.py        # Markdown→PDF 主脚本（Chrome headless）
│   ├── md2pdf_browser.py       # Markdown→PDF（Playwright，支持页眉页脚）
│   └── ...                     # PDF 表单处理脚本
└── references/
    ├── pdf-operations.md       # 合并/拆分/提取/创建 代码示例
    ├── md2pdf-details.md       # 排版、字号、Mermaid、Callout 详解
    ├── forms.md                # 表单填写指南
    └── advanced.md             # pypdfium2、pdf-lib、疑难排查
```

## 快速使用

```bash
# Markdown 转 PDF
python scripts/md2pdf_chrome.py report.md

# 指定输出路径和页眉
python scripts/md2pdf_chrome.py report.md output.pdf "报告标题"

# 智能排版：密集章节缩小字号，尾部变更记录用更小字号
python scripts/md2pdf_chrome.py doc.md --sm "开发路线图" --xs-after "变更历史"
```

## 环境要求

- Python 3 + `markdown` 库
- Google Chrome（macOS 路径：`/Applications/Google Chrome.app/`）
- 可选：`pypdf`、`pdfplumber`、`reportlab`（PDF 操作）
- 可选：Playwright（页眉页脚版本）

## 作者

AlexCai
