# 2pdf Skill

一站式 PDF 处理技能，为 Claude Code / Codex / Cursor / Hermes 提供完整的 PDF 文档处理能力。

> **源仓库**: [Loveacup/jz-skills](https://github.com/Loveacup/jz-skills) · 路径 `shared/2pdf`
> **更新方式**: `git pull` 拉取最新后跑 `python3 scripts/md2pdf_chrome.py --setup`（**排版引擎**：幂等，自动补齐环境与 vendor 资源，不安装 Marker）；结构化解析引擎单独跑 `python3.12 scripts/marker_runner.py setup`。mac 端部署走 `deploy/sync-all.sh`，Windows 端 pull 后直接各自 setup 即可。

## 核心功能

**Markdown → PDF**
将 Obsidian 风格 Markdown 转换为专业排版的 PDF。通过 Chrome headless 渲染，完美支持中日韩文字、Mermaid 图表、26 种 Callout 样式。内置 Relay 工作流，自动分析文档结构并优化排版。

**PDF 文档操作**
合并、拆分、旋转页面、提取文本与表格、添加水印、密码保护。

**表单处理**
读取 PDF 表单字段并自动填写。

**OCR 识别**
扫描件文字提取。

**结构化解析（Marker）**
PDF / 图片 / DOCX / PPTX / XLSX / HTML / EPUB → 保留版面结构的 Markdown / JSON / HTML / chunks；复杂表格、公式、扫描件 OCR、批量、Python 扩展、本地 GUI / HTTP 接口。独立 venv `~/.venvs/2pdf-marker`（Python ≥3.10），与排版引擎互不影响。

## 选哪条执行链

|任务|执行链|
|---|---|
|Markdown / Obsidian → 排版 PDF/PNG/HTML/公众号|`scripts/md2pdf_chrome.py`（排版引擎）|
|合并/拆分/旋转/水印/加密、简单文字表格提取、简单 OCR|`references/pdf-operations.md`|
|填写 PDF 表单|`references/forms.md`|
|文档 → 结构化 Markdown/JSON/HTML/chunks|`scripts/marker_runner.py` + `references/marker.md`|
|批量、LLM 增强、Python API、GUI、HTTP|`references/marker-advanced.md`|

## 目录结构

```
pdf/
├── SKILL.md                    # 技能定义与工作流指南
├── scripts/
│   ├── md2pdf_chrome.py        # Markdown→PDF 主脚本（排版引擎）
│   ├── md2pdf_browser.py       # Markdown→PDF（Playwright，支持页眉页脚）
│   ├── marker_runner.py        # 结构化解析引擎入口（独立 venv，启动上游 Marker）
│   ├── requirements-marker.txt # Marker 精确版本
│   └── ...                     # PDF 表单处理脚本
└── references/
    ├── pdf-operations.md       # 合并/拆分/提取/创建 代码示例
    ├── md2pdf-details.md       # 排版、字号、Mermaid、Callout 详解
    ├── forms.md                # 表单填写指南
    ├── marker.md               # 结构化解析：安装、常规解析、产物验收
    ├── marker-advanced.md      # 批量、LLM、Python 扩展、GUI/HTTP
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

# 报告 frontmatter 属性卡、署名块与首页/图表页预览
python scripts/md2pdf_chrome.py report.md output.pdf "报告标题" \
  --properties --byline --preview ./preview --verify

# 结构化解析（首次先建独立环境；需 Python ≥3.10）
python3.12 scripts/marker_runner.py setup            # PDF/图片基础链
python3.12 scripts/marker_runner.py setup --full     # 追加 Office/HTML/EPUB
python3 scripts/marker_runner.py preflight
python3 scripts/marker_runner.py single -- in.pdf --output_format markdown --output_dir ./out
```
排版参数以 [SKILL.md 的 Markdown 参数表](SKILL.md#output-formats--resilience) 为准；结构化解析参数与验收见 [references/marker.md](references/marker.md)。

## 环境要求

排版引擎：
- Python 3 + `markdown` 库（`--setup` 自动建 `~/.venvs/pdf-skill`）
- Google Chrome 或 Playwright Chromium
- 可选：`pypdf`、`pdfplumber`、`reportlab`（PDF 操作）

结构化解析引擎（独立，按需安装）：
- Python ≥3.10,<4（例如 Homebrew `python3.12`），`marker_runner.py setup` 自建 `~/.venvs/2pdf-marker`
- 首次转换会下载模型；OCR/公式在非 NVIDIA 机器上由 Surya 自动拉起 `llama-server`（llama.cpp）
- Office/HTML/EPUB 需 `setup --full` 与 WeasyPrint 原生库（pango 等）
- 模型权重许可与代码许可不同，见 `references/marker.md`

## 作者

AlexCai
