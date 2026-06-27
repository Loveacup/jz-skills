# xhs-crawler 开发参考

小红书内容提取 skill。**v6 架构：XHS-Downloader 库直调（子进程）为主力**，CDP 浏览器自动化 + xhshow 签名隔离为备选兜底，agent LLM 能力生成报告。

## 核心架构：双解释器 + 子进程边界

```
skill 胶水层 (Hermes 默认 python3 / 3.9)
  scripts/xhs_backend.py   ── prepare_url → build_command → subprocess → classify → adapt
        │  subprocess: stdin=url(argv) / stdout=JSON
        ▼
XHS-Downloader .venv/bin/python (3.12 + 全依赖, uv 管理)
  scripts/xhs_downloader_runner.py  ── from source import XHS → extract() → print JSON
        ▲
  .xhs-downloader/  ← bootstrap 自动 clone（gitignored）
```

**为什么是子进程而非直接 import：**
- `from source import XHS` 会连带导入 textual / fastapi / fastmcp / uvicorn（`source/__init__` + `app.py` 顶层导入），且 XHS-Downloader 强制 Python ≥3.12，而 Hermes 默认 `python3` 是 3.9 → 无法在胶水层进程内直接 import。
- 子进程边界把「Python 版本隔离」和「测试 mock 缝」合二为一：单元测试注入 `runner_fn` 即可完全避开真实子进程/网络。

## 目录结构

```
xhs-crawler/
├── SKILL.md                  # 技能文档（OpenClaw 规范）
├── claude.md                 # 本文件（开发参考）
├── conftest.py               # 注册 integration marker
├── scripts/
│   ├── xhs_bootstrap.py          # 幂等 clone + uv sync + doctor
│   ├── xhs_backend.py            # 后端胶水：编排 + 分类（主入口 fetch_note）
│   ├── xhs_downloader_runner.py  # 薄 runner，跑在 .venv(3.12)
│   ├── xhs_adapter.py            # 返回数据 → 报告模板输入契约（纯函数）
│   ├── parse_xhs_url.py          # prepare_url（保留 token）/ extract_note_id
│   ├── xhs_api.py                # xhshow 搜索/创作者（需 Cookie）
│   └── legacy/                   # CDP 兜底（评论 + OCR），见其 README
│       ├── xhs_extractor_v2.py
│       ├── xhs_carousel_ocr.py
│       ├── cookie_manager.py
│       ├── extractors.js
│       └── config.py / progress.py / validators.py
├── xhshow/                    # XHS 签名库（纯 Python，勿改内部）
├── references/
│   ├── xhs-report-prompt.md       # 报告生成 LLM 模板（输入契约见第 3 节）
│   ├── xhs-downloader-integration.md  # 部署手册 + 样本数据
│   └── ARCHITECTURE.md
├── tests/
│   ├── test_xhs_adapter.py    # 适配器契约（TDD 主战场）
│   ├── test_xhs_url.py        # prepare_url（保留 token）
│   ├── test_xhs_backend.py    # subprocess 边界分类（注入 runner_fn）
│   ├── test_xhs_bootstrap.py  # 纯助手 + doctor
│   ├── test_xhs_integration.py# 联网金丝雀（默认跳过）
│   └── test_parse_url.py / test_xhs_api.py / test_xhshow_sign.py
└── .xhs-downloader/           # gitignored：bootstrap clone + uv venv(3.12)
```

## 数据流（主力路径）

1. `fetch_note(raw_url)` → `prepare_url` 规范化（**保留 xsec_token**，短链透传）
2. `build_command(url, cookie="")` → `[venv-python, runner, url, ""]`（cookie 永远空字符串）
3. 子进程跑 runner：`XHS(cookie="", download_record=False, record_data=False, ...).extract(url, download=False)`
   - 注意 `extract()` 返回 `list[dict]`，runner 取 `results[0]`
   - runner 把库的进度信息重定向到 stderr，stdout 只留 JSON
4. `classify(rc, stdout, stderr)` → status ∈ {ok, failed, ip_risk, error}（只解析 stdout 末行 JSON）
5. ok 时 `adapt_to_report_input(data, url)` → 报告模板输入契约

## 报告输入契约（adapter 产出）

映射到 `references/xhs-report-prompt.md` 第 3 节：`title/author/tags/url/content/ocr_content/comments`，
外加 `note_id/author_id/note_type/publish_time/stats/image_urls/backend/needs_cdp_fallback`。

**缺失字段输出标准标注而非杜撰（P0）：**
- 评论 → `[评论数据不足：...评论总数 N 条]`
- OCR → `[图片OCR不可用：...共 N 张...]`
- 图文正文 → 追加 `[正文可能不完整...]`

## 三个关键坑（已在代码核实）

1. **`extract()` 返回 `list[dict]` 不是 dict**；MCP/API 路径才是单 dict。runner 取首条。
2. **裸 `explore/<id>`（无 xsec_token）触发风控失败**；短链/带 token 链接才稳。`prepare_url` 绝不削 token。
3. **库进度信息打到 stdout**，会污染 JSON。runner 重定向 stdout→stderr + classify 取末行 JSON（双保险）。

## 开发约定

- **胶水层目标 Python 3.9**（Hermes 部署默认）→ 用 `from __future__ import annotations`，不用 3.10+ 运行期语法。runner 例外（跑在 3.12 venv）。
- **TDD 先红后绿**：先写失败测试再实现。适配器/URL/backend 全部纯函数或可注入，无网络。
- **联网测试隔离**：`@pytest.mark.integration` + `XHS_LIVE_TEST=1` 才跑，默认跳过。
- **不改 XHS-Downloader 内部**：经子进程 `from source import XHS` 调用；上游更新走 `cd .xhs-downloader && git pull && uv sync`。
- **xhshow/ 内部加密逻辑勿改**，仅通过 `Xhshow` 类公共接口调用。
- **报告生成**：不调用外部 LLM API，由 agent 自身能力按模板生成。

## 常用命令

```bash
python3 scripts/xhs_bootstrap.py            # 准备后端
python3 scripts/xhs_bootstrap.py doctor     # 自检就绪
python3 scripts/xhs_backend.py "<链接>"      # 提取（命令行）
python3 -m pytest tests/                    # 单元测试（金丝雀跳过）
XHS_LIVE_TEST=1 python3 -m pytest tests/test_xhs_integration.py  # 联网金丝雀
```
