# xhs-crawler 开发参考

小红书内容提取 Clawdbot skill。v5 混合架构：CDP 浏览器自动化用于富内容提取，xhshow 纯算法签名用于 API 调用（搜索/创作者），agent LLM 能力生成报告。

## 目录结构

```
xhs-crawler/
├── SKILL.md              # 技能文档（OpenClaw 规范）
├── claude.md             # 本文件（开发参考）
├── .env.example          # 环境变量模板
├── .gitignore
├── requirements.txt
├── scripts/
│   ├── xhs_extractor.py      # 主提取器（CDP + Playwright）
│   ├── xhs_api.py             # API 客户端（xhshow 签名）
│   ├── xhs_carousel_ocr.py   # 轮播图 OCR（Qwen3-VL）
│   ├── cookie_manager.py     # Cookie 存取（~/.xhs_cookie）
│   ├── parse_xhs_url.py      # URL/短链解析
│   └── extractors.js         # 浏览器端 JS 提取逻辑
├── xhshow/                    # XHS 签名库（纯 Python）
│   ├── client.py              # 公共接口：Xhshow 类
│   └── ...                    # 加密核心（勿修改）
├── references/
│   ├── xhs-report-prompt.md   # 报告生成 LLM 模板
│   └── ARCHITECTURE.md        # 架构设计文档
└── tests/
    ├── test_parse_url.py
    ├── test_xhs_api.py
    └── test_xhshow_sign.py
```

## 开发约定

- **异步 I/O**：所有网络/浏览器操作使用 `async/await`
- **进度汇报**：用 `print()` + emoji 前缀实时反馈（🔌🌐💬📊🎠🖼️💾✅）
- **环境变量**：所有外部配置通过 `.env` 或环境变量，不硬编码路径
- **错误处理**：优雅降级（部分失败 → 继续处理其余 → 最后保存已有数据）
- **文件删除**：使用 `trash` 而非 `rm`

## 环境变量（.env）

```bash
CHROME_CDP_URL=ws://127.0.0.1:18792/cdp      # Chrome CDP 端点（OpenClaw Extension）
QWEN_API_URL=http://<internal IP redacted>:9998/v1/chat/completions  # OCR 服务
XHS_OUTPUT_DIR=~/Documents/Obsidian/AlexCai/00-Inbox   # 报告输出
XHS_PROXY=                                  # HTTP 代理（可选）
```

## 关键技术说明

- **xhshow 要求 Python 3.10+**：使用 `X | Y` 联合类型语法（PEP 604）
- **extractors.js 极其脆弱** — 依赖小红书 DOM 结构，**不要修改**除非确认 DOM 变化
- **xhshow/ 内部加密逻辑** — **不要修改**，仅通过 `Xhshow` 类公共接口调用
- **xhshow 签名接口**：`sign_headers(method, uri, cookies, params=, payload=)` → 返回 `{x-s, x-s-common, x-t, x-b3-traceid, x-xray-traceid}`
- **Cookie 存储**：`~/.xhs_cookie`，需要 `web_session` 和 `a1` 字段
- **报告生成**：不调用外部 LLM API，由 Clawdbot agent 自身能力按模板生成
