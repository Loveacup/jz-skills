---

name: xhs-crawler
description: >-
  type: routine
  小红书内容提取与深度分析。主力后端：XHS-Downloader（免登录，库直调子进程），备选：CDP 浏览器自动化 + xhshow 签名。
  支持链接提取、关键词搜索、创作者主页爬取。提取后生成 7 章节结构化知识资产报告。
  Triggers: 小红书, xhs, rednote, xiaohongshu, 获取小红书, 解析小红书, extract xhs, analyze xhs
metadata:
  {
    "openclaw": {
      "emoji": "📕",
      "requires": {
        "bins": ["python3"],
        "anyBins": ["python3.11", "python3.12", "python3"],
        "env": []
      }
    }
  }

---

# 小红书内容提取器 v6

小红书（XiaoHongShu/RedNote）全功能内容提取技能。**主力后端为 XHS-Downloader**（第三方开源工具，免登录提取），以**直接库调用 + 子进程**形式集成（非 HTTP API、非 MCP），原有 CDP/xhshow 方案隔离保留为备选兜底。

支持三种提取路径：

1. **XHS-Downloader 库直调（⭐ 主力）** — 经 `scripts/xhs_backend.py` 调用跑在独立 Python 3.12 venv 里的 runner 子进程，免 Cookie 提取作品元数据、统计、标签、图片 URL
2. **CDP 浏览器自动化（备选，`scripts/legacy/`）** — 需 Chrome CDP + 登录态，可补齐完整正文 + 评论 + 轮播图 OCR
3. **关键词搜索 + 创作者分析** — 通过 xhshow 签名 API（需 Cookie）

提取后由 agent 自身 LLM 能力按 `references/xhs-report-prompt.md` 模板生成知识资产报告。

> **架构**：skill 胶水层跑在 Hermes 默认 `python3`（3.9）；XHS-Downloader 因要求 ≥3.12 且依赖重，被隔离进自己的 uv venv，经子进程（stdin=url / stdout=JSON）调用。详见 `claude.md`。

## P0 约束（严格遵守）

### 强制输出检查清单
每份报告必须包含以下 7 个章节，缺一不可：
- [ ] 0. 元信息 (Meta) - AI 标题、一句话价值、作者、标签、互动数据
- [ ] 1. 逻辑流 (The Logic Chain) - 表层逻辑 + 底层逻辑
- [ ] 2. 评论深度分析 (Comments Intelligence) - 6 类情绪标注 + 高质量讨论
- [ ] 3. 核心洞察 (Key Insights) - 至少 2 个正向洞察 + 1 个反直觉点
- [ ] 4. 内容深度拆解 (Deep Dive) - 根据内容类型灵活组织
- [ ] 5. 高光时刻 (Highlights & Quotes) - 金句原文 + 上下文
- [ ] 6. 知识图谱与行动 (Knowledge Graph & Action) - 概念关联 + 行动清单 + 批判审视

### 数据获取 Fallback 策略

**链接提取时的降级链（按优先级）：**

1. **XHS-Downloader 库直调（首选）** — `python3 scripts/xhs_backend.py <链接>`（或 `from xhs_backend import fetch_note`），免 Cookie 即可获取标题/描述/标签/互动数据/图片 URL。**关键：胶水层永远显式传 `cookie=""` 空字符串触发免登录路径，传 null 或不传会失败（已固化在 `build_command` 里）。**
2. **XHS-Downloader 失败** → 尝试 CDP 模式补齐评论/OCR（`scripts/legacy/`，需 Chrome CDP + 登录态）
3. **CDP 模式失败** → 尝试纯 xhshow 签名 API（搜索/创作者，需 Cookie）
4. **全部失败** → 返回错误 + 已获取的部分数据（不中断流程）
5. **IP 风控（300012）** — 任何一步触发此错误，**立即止损**：停止所有尝试，向用户汇报已穷尽方案，提供三个选项：(A) 提供 Cookie 换 API 模式 (B) 换代理 IP (C) 手动复制内容。禁止继续轮换其他方案，每多试一次都是浪费 token。
6. **评论加载失败** → 标注"[评论数据不可用]"，保留其他章节
7. **OCR 失败** → 跳过 OCR，保留正文和评论文本内容
8. **轮播图为 0** → 分析无轮播图原因（单图笔记或提取失败）

**通用浏览器/爬虫工具定位：**
- 不要用 Crawl4AI、普通 web_extract、通用 browser-agent 替代本 skill 作为小红书主力；这些工具通常缺少小红书专用登录态、评论加载、轮播图 OCR、报告结构和数据完整性检查。
- 可用 agent-browser/Playwright MCP/现有 browser 工具作为**诊断和兜底**：检查页面是否登录、分享链接是否跳转、DOM 是否变化、评论/轮播图是否能手动展开、截图是否可 OCR。
- 通用爬虫只适合尝试公开落地页的 meta/少量文本，结果必须标注为 partial，不能声称完整提取。

### 数据引用规范

**✅ 正确示例：**
> "评论原文内容" —— 用户名（👍 123，情绪：赞同）

**❌ 错误示例：**
> 有网友评论说大概意思是...（禁止改写或概括）

**⚠️ 数据不足时标注：**
- `[数据不足]` - 正常情况但数据量少于预期
- `[获取失败]` - 技术错误导致数据缺失
- `[需要登录]` - 权限限制导致无法获取
- `[不支持]` - 功能限制（如私密笔记）

---

## 📋 完整执行检查清单（必须遵守）

每次提取必须按以下步骤执行，完成后逐项勾选：

### Step 1: 前置检查
- [ ] **浏览器状态检查**: Chrome CDP 端口 19222 可连接
- [ ] **登录态验证**: Chrome 中已登录小红书账号
- [ ] **环境变量确认**: `CHROME_CDP_URL` 配置正确

### Step 2: 数据提取（核心）
- [ ] **基础数据提取**: 标题、作者、正文内容
- [ ] **正文完整性检查**: 正文长度 > 50 字符，否则标记警告
- [ ] **标签提取**: 所有 #标签 已提取
- [ ] **互动数据**: 点赞、收藏、评论数
- [ ] **评论区加载**: 滚动加载直到无新增（最多15次）
- [ ] **评论去重**: 检查并去除重复评论
- [ ] **评论完整性检查**: 提取数量应接近页面显示的评论数

### Step 3: 轮播图 OCR（关键）
- [ ] **轮播图数量确认**: 检测笔记总页数（通常 10-12 张）
- [ ] **逐张截图**: 所有轮播图页面已截图
- [ ] **OCR 识别**: 每张截图已完成 OCR
- [ ] **OCR 结果合并**: 所有图片文字已合并到报告
- [ ] **截图即时删除**: 每完成一张 OCR，立即删除截图

### Step 4: 报告生成
- [ ] **7章节检查**: 0-6 章节全部完成
- [ ] **P0约束验证**: 元信息、逻辑流、评论分析、核心洞察齐全
- [ ] **数据引用规范**: 评论使用原文，禁止概括改写
- [ ] **批判性审视**: 包含独特价值和局限盲区分析

### Step 5: 临时文件清理（强制）
- [ ] **截图删除**: 所有 PNG 截图文件已删除
- [ ] **临时目录清理**: `/tmp/xhs_analyzer/` 下临时目录已删除
- [ ] **过程文件清理**: 中间 JSON/TXT 过程文件已清理
- [ ] **保留文件确认**: 仅保留最终报告和完整数据文件

### Step 6: 最终验证
- [ ] **文件大小检查**: 报告文件大于 5KB（确保内容完整）
- [ ] **正文完整性确认**: 正文长度合理（通常 100-5000 字符）
- [ ] **评论完整性确认**: 提取评论数与页面显示数量差异 < 50%
- [ ] **OCR 内容确认**: 报告中包含轮播图文字内容
- [ ] **保存路径确认**: 文件保存至 `~/Documents/Obsidian/AlexCai/00-Inbox/`
- [ ] **用户通知**: 告知用户提取完成和文件位置，报告任何完整性警告

---

### 隐私与安全红线

**严禁存储或输出：**
- 用户 Cookie、Session ID、Token
- 个人隐私信息（手机号、地址等）
- 小红书内部 API 响应中的敏感字段

**安全实践：**
- Cookie 仅存储在 `~/.xhs_cookie`，不输出到日志
- 报告中的用户 ID 使用昵称而非用户 ID
- 临时文件定期清理（见执行指南）

---

## 📊 数据完整性验证标准

### 正文完整性

| 指标 | 标准 | 警告阈值 |
|:---|:---|:---|
| **长度** | 通常 100-5000 字符 | < 50 字符 |
| **内容** | 包含完整句子和段落 | 只有片段或乱码 |
| **标签** | 至少包含 1 个 #标签 | 无标签 |

**正文提取失败的可能原因：**
1. 页面未完全加载 → 增加等待时间
2. 选择器不匹配 → 使用多选择器备选方案
3. 动态加载内容 → 滚动触发加载

### 评论完整性

| 指标 | 标准 | 警告阈值 |
|:---|:---|:---|
| **数量** | 接近页面显示的评论数 | < 显示数量的 50% |
| **去重** | 无重复评论 | 发现重复 |
| **内容** | 每条评论有用户名和正文 | 大量"匿名"或空内容 |

**评论提取不完整的可能原因：**
1. 滚动次数不足 → 增加滚动次数至无新增
2. "查看更多"未点击 → 自动检测并点击展开按钮
3. 登录态失效 → 检查 Chrome 登录状态

### 完整性自检脚本

```python
# 在提取完成后执行
completeness_check = {
    "content_length": len(content),
    "comments_count": len(comments),
    "expected_comments": expected_count,
    "content_warning": len(content) < 50,
    "comments_warning": len(comments) < expected_count * 0.5
}
```

---

## 前置要求

### ⭐ 主力前置：bootstrap XHS-Downloader（一次性）

```bash
# 幂等：自动 clone 到 .xhs-downloader/ 并用 uv 同步出 Python 3.12 venv（含全部依赖）
python3 {baseDir}/scripts/xhs_bootstrap.py

# 自检后端是否就绪
python3 {baseDir}/scripts/xhs_bootstrap.py doctor
```

依赖 `uv`（`brew install uv`）与可用的 Python 3.12（如 `/opt/homebrew/bin/python3.12`）。
clone 落点 `.xhs-downloader/` 已 gitignore，不入库；`git pull` 即可更新上游。

### legacy 前置（仅 CDP 兜底链路需要）

以下仅在需要评论 / 轮播图 OCR、启用 `scripts/legacy/` CDP 链路时才配置：

1. **xhshow 库已安装**：
   ```bash
   cd ~/.hermes/skills/xhs-crawler
   pip3 install -e .
   # 验证: python3 -c "from xhshow import Xhshow; print('OK')"
   ```
   **注意**：需要 Python 3.9+。如果 setup.py 要求 3.10+ 但系统只有 3.9，
   手动修改 `setup.py` 中的 `python_requires=">=3.9"` 后再安装。

2. **Playwright Chromium 已安装**：
   ```bash
   python3 -m playwright install chromium
   ```

3. **Chrome CDP 已启动**（链接提取模式必需）：

**Google Chrome + CDP（推荐）：**
1. 在 Chrome 中登录小红书
2. 启动 Chrome 带远程调试端口：
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=19222 \
     --no-first-run \
     --no-default-browser-check &
   ```
3. 验证：`curl http://127.0.0.1:19222/json/list`

**或 Comet 浏览器（备选）：**
```bash
/Applications/Comet.app/Contents/MacOS/Comet \
  --remote-debugging-port=19222 \
  --no-first-run \
  --no-default-browser-check
```
验证：`curl http://127.0.0.1:19222/json/list`

### Python 依赖

```bash
pip3 install -r {baseDir}/requirements.txt
python3 -m playwright install chromium
```

**xhshow 库安装：**
```bash
cd {baseDir}
pip3 install -e .
```

### Cookie（API 模式必需）

```bash
python3 {baseDir}/scripts/legacy/cookie_manager.py save 'web_session=xxx;a1=xxx'
```
从浏览器 DevTools → Application → Cookies 获取 `web_session` 和 `a1` 字段。

### 环境变量

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `CHROME_CDP_URL` | CDP 连接地址 | `http://127.0.0.1:19222` |
| `QWEN_API_URL` | Qwen3-VL OCR 地址 | `http://<internal IP redacted>:9998/v1/chat/completions` |
| `XHS_OUTPUT_DIR` | 报告输出目录 | `~/Documents/Obsidian/AlexCai/00-Inbox` |
| `XHS_PROXY` | HTTP 代理（可选） | 无 |

## 使用方法

### ⭐ 主力方案：XHS-Downloader 库直调（免 Cookie 提取）

**适用场景：** 快速获取笔记标题、描述、标签、互动数据、图片 URL。不需要登录态、Chrome CDP、Cookie。

**一次性准备**见上文「主力前置：bootstrap」。准备好后**无需启动任何服务器**，直接调用：

**命令行：**
```bash
python3 {baseDir}/scripts/xhs_backend.py "<小红书链接>"
# 输出报告输入契约 JSON：{status, report_input, message, stop_loss, url}
```

**库调用（推荐，便于 agent 编排）：**
```python
import sys; sys.path.insert(0, "{baseDir}/scripts")
from xhs_backend import fetch_note

out = fetch_note("<小红书链接>")        # cookie 默认 ""（免登录）
if out["status"] == "ok":
    data = out["report_input"]         # 已适配成报告模板输入契约
    # data["title"] / ["author"] / ["tags"] / ["content"] /
    # data["comments"](标注) / ["ocr_content"](标注) / ["stats"] / ["needs_cdp_fallback"]
```

**支持的链接格式（优先用带 `xsec_token` 的分享链 / 短链，免风控）：**
- `https://www.xiaohongshu.com/explore/<note_id>?xsec_token=...`
- `https://www.xiaohongshu.com/discovery/item/<note_id>?xsec_token=...`
- `https://xhslink.com/<short_code>`（短链，由后端自动解析）
- ⚠️ **裸 `explore/<note_id>`（无 token）易触发风控**——`prepare_url` 会原样保留 token，绝不削成裸 id。

**`fetch_note` 返回 `status` 分类：**

| status | 含义 | 处理 |
|---|---|---|
| `ok` | 成功，`report_input` 为适配后数据 | 进入报告生成 |
| `failed` | 后端未提取到数据 | 换带 token 的新链接 / 上 CDP 兜底 |
| `ip_risk` | IP 风控（300012），`stop_loss=True` | **立即止损**，按下方 Q7 上报用户 |
| `timeout` | runner 子进程超时 | 重试一次，仍失败则上报 |
| `invalid_url` | 非小红书链接 | 提示用户检查链接 |
| `error` | runner 异常 / 坏 JSON | 跑 `xhs_bootstrap.py doctor` 查后端是否就绪 |

**⚠️ 关键陷阱：`cookie` 必须是空字符串**
- `cookie=""`（空字符串）= 免登录提取成功 ✅
- `cookie=None` 或不传 = 失败 ❌
- 已固化在 `build_command`：胶水层永远显式传 `""`，无需手动处理。

**局限性（vs CDP 模式）——适配器一律输出标准标注而非杜撰：**
- ❌ 不能提取评论 → `[评论数据不足：...评论总数 N 条]`
- ❌ 不能提取轮播图 OCR → `[图片OCR不可用：...共 N 张...]`
- ❌ 图文正文常嵌在图里、可能不完整 → 正文后标注 `[正文可能不完整...]`
- ✅ 元信息/标签/互动数据足够；`report_input["needs_cdp_fallback"]` 为 True 时建议上 CDP 补评论/OCR

---

### 备选方案：CDP 兜底（评论 + 轮播图 OCR）

仅当 XHS-Downloader 主力路径已拿到元数据、但报告**必须**补齐评论或图文 OCR 时启用。
前提：Chrome CDP（端口 19222）+ 小红书登录态。详见 `scripts/legacy/README.md`。

```bash
python3 {baseDir}/scripts/legacy/xhs_extractor_v2.py "<小红书链接>"
python3 {baseDir}/scripts/legacy/xhs_extractor_v2.py "<小红书链接>" --no-ocr
```

**流程：** CDP 连接 Chrome（继承登录态）→ 滚动加载评论 → JS 注入提取正文/评论/标签/图片/互动 → 轮播图逐张截图 → Qwen3-VL OCR → 输出 JSON。

**输出 JSON 结构：**
```json
{
  "title": "笔记标题",
  "author": "作者名",
  "content": "正文内容",
  "tags": ["标签1", "标签2"],
  "comments": [{"user": "用户名", "text": "评论", "likes": "9", "time": "01-19"}],
  "images": ["图片URL"],
  "stats": {"likes": "822", "collects": "2081"},
  "carousel_ocr": [{"slide": 1, "text": "OCR文本"}],
  "full_content": "正文 + OCR 合并"
}
```

### 模式 2：关键词搜索（API）

```bash
python3 {baseDir}/scripts/xhs_api.py search "<关键词>"
```

调用 `search_notes(keyword)` → 返回笔记列表（标题、作者、链接、互动数据）。

### 模式 3：创作者分析（API）

```bash
python3 {baseDir}/scripts/xhs_api.py creator "<用户ID>"
```

调用 `get_creator_info()` + `get_creator_notes()` → 返回创作者资料和笔记列表。

## 报告生成

提取 JSON 后，agent 读取 `{baseDir}/references/xhs-report-prompt.md` 模板生成 7 章节知识资产报告：

| 章节 | 内容 |
|------|------|
| 元信息 | AI 标题、一句话价值、作者、标签、互动 |
| 逻辑流 | 表层逻辑 + 底层逻辑 |
| 评论分析 | 6 类标注 + 高质量讨论 |
| 核心洞察 | 正向洞察 + 反直觉点 |
| 内容主体 | 根据内容类型灵活组织 |
| 行动清单 | 立即执行 / 本周深入 / 长期跟踪 |
| 批判审视 | 独特价值 + 局限盲区 |

**重要：** 报告由 agent 的 LLM 能力直接生成，不调用外部 API。

## 深度扩展（可选）

基础报告生成后，**询问用户是否需要深度扩展**：

### 深度扩展流程

```
基础报告生成完成
  ↓
询问用户："是否需要深度扩展？"
  ↓
用户选择：是 / 否
  ↓
[是] → 启动多智能体深度搜索 → 扩展报告
[否] → 保存基础报告，流程结束
```

### 深度扩展内容

选择深度扩展后，系统将：

1. **调用 Librarian 智能体**进行多源深度搜索
2. **搜索维度**：
   - 官方文档和发布说明
   - 开发者社区讨论（Reddit, Hacker News, Twitter/X）
   - 类似工具对比分析
   - 行业趋势和预测
3. **扩展内容**：
   - 功能深度解析（技术机制、真实案例、量化数据）
   - 竞品详细对比（功能、定位、差异点）
   - 概念深度解析（起源、演变、争议点）
   - 引用来源标注（可追溯的链接和参考）
   - 未来展望与趋势预测

### 触发话术示例

**Agent 询问用户：**
> 基础报告已生成！📊
> 
> **是否需要深度扩展？** 深度扩展将：
> - 🔍 搜索相关官方文档和社区讨论
> - 📚 补充竞品对比和行业分析
> - 📈 增加量化数据和真实案例
> - 🔗 添加可追溯的引用来源
> 
> 预计增加 3000-5000 字，耗时 2-3 分钟。
> 
> 回复 **"是/Yes/Y"** 启动深度扩展，回复 **"否/No/N"** 或忽略则保存基础报告。

### 决策建议

| 场景 | 建议 |
|:---|:---|
| **高价值内容**（工具评测、方法论、行业洞察） | ✅ 推荐深度扩展 |
| **时效性强的热点** | ✅ 推荐深度扩展，补充最新动态 |
| **简单种草/避雷** | ❌ 基础报告即可 |
| **纯情感分享** | ❌ 基础报告即可 |
| **快速预览需求** | ❌ 先保存基础报告，后续可手动扩展 |

## 实时进度汇报

提取过程中脚本会输出带 emoji 的实时状态：

```
🚀 小红书提取器 v5
🔌 连接 Chrome CDP... ✓ 已连接
🌐 打开笔记... ✓ 页面加载完成
💬 加载评论区... ✓ 评论加载完成
📊 提取基础数据... ✓ 正文: 411 字, 评论: 6 条
🎠 提取轮播图... 🖼️ 第 1/10 张 ✓ OCR 1531 字
💾 原始数据保存... ✓
✅ 提取完成！
```

## 脚本清单

**主力链路（XHS-Downloader 库直调）：**

| 脚本 | 用途 | 用法 |
|------|------|------|
| `xhs_bootstrap.py` | 幂等准备 3.12 后端（clone + uv sync）/ doctor 自检 | `python3 {baseDir}/scripts/xhs_bootstrap.py [doctor]` |
| `xhs_backend.py` | 后端胶水：URL 规范化 + 子进程调用 + 分类 + 适配 | `python3 {baseDir}/scripts/xhs_backend.py <url>` |
| `xhs_downloader_runner.py` | 薄 runner（跑在 .venv 3.12，输出纯 JSON） | 由 `xhs_backend` 子进程调用 |
| `xhs_adapter.py` | 返回数据 → 报告模板输入契约（纯函数） | 由 `xhs_backend` 调用 |
| `parse_xhs_url.py` | URL 规范化 / 保留 xsec_token / note_id 提取 | 由 `xhs_backend` 调用 |

**搜索 / 创作者（xhshow 签名，需 Cookie）：**

| 脚本 | 用途 | 用法 |
|------|------|------|
| `xhs_api.py` | 关键词搜索 / 创作者分析 | `python3 {baseDir}/scripts/xhs_api.py <search\|creator> <arg>` |

**兜底（CDP，评论 + OCR）：** 见 `scripts/legacy/README.md`。

**测试：** `python3 -m pytest {baseDir}/tests/`（联网金丝雀默认跳过，`XHS_LIVE_TEST=1` 才跑）。

## 故障排除

### 常见问题速查 (FAQ)

#### Q0: XHS-Downloader 提取失败（`status=failed` / `error`）？

**排查步骤：**
1. **后端是否就绪** — `python3 {baseDir}/scripts/xhs_bootstrap.py doctor`；`ready:false` 则先跑 `xhs_bootstrap.py`
2. **链接是否带 token** — 优先用短链或带 `xsec_token` 的分享链；裸 `explore/<id>` 易被风控失败
3. **链接格式** — 确认是 `explore/`、`discovery/item/` 或 `xhslink.com/`
4. **IP 是否被封** — `status=ip_risk`（300012）见 Q7，**立即止损**
5. **更新上游** — `cd {baseDir}/.xhs-downloader && git pull && uv sync --no-dev`

**cookie 陷阱：** 胶水层已固化 `cookie=""`（`build_command`）；若手改 runner/backend 传了 `None` 会失败。

**Python 版本：** XHS-Downloader 需 ≥3.12，由 `.xhs-downloader/.venv`（uv 管理）满足，与 skill 胶水层的 `python3`(3.9) 互不影响。`uv` 未装则 `brew install uv`。

---

#### Q1: CDP 连接失败怎么办？
**症状：** `🔌 连接 Chrome CDP...` 后报错或超时

**排查步骤：**
1. 检查 Chrome 是否已启动远程调试：
   ```bash
   curl http://127.0.0.1:19222/json/list
   ```

2. 如果未运行，启动 Chrome（带 CDP）：
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=19222 \
     --no-first-run \
     --no-default-browser-check &
   ```

3. 或使用 Comet（备选）：
   ```bash
   /Applications/Comet.app/Contents/MacOS/Comet \
     --remote-debugging-port=19222 \
     --no-first-run \
     --no-default-browser-check &
   ```
   此时需设置环境变量：`export CHROME_CDP_URL=http://127.0.0.1:19222`

**预防措施：**
- 将 Chrome CDP 启动命令加入开机启动项
- 使用 cron job 保持 Chrome 运行

---

#### Q1b: xhshow 导入失败？
**症状：** `ModuleNotFoundError: No module named 'xhshow'` 或 `xhshow 库未安装`

**解决步骤：**
```bash
cd ~/.hermes/skills/xhs-crawler
# 检查 setup.py 是否存在
ls setup.py || echo "需要创建 setup.py"

# 创建最小 setup.py（如不存在）
cat > setup.py << 'EOF'
from setuptools import setup, find_packages
setup(name="xhshow", version="0.1.0", packages=find_packages(), python_requires=">=3.9")
EOF

# 安装
pip3 install -e .

# 验证
python3 -c "from xhshow import Xhshow; print('xhshow OK')"
```

**常见陷阱：**
- 系统 Python 是 3.9，但 setup.py 要求 `>=3.10` → 修改 setup.py 为 `>=3.9`
- 使用了 `--user` 安装但不在 PYTHONPATH → 使用 `pip3 install -e .`（开发模式）
- 在错误目录执行 → 必须在 `~/.hermes/skills/xhs-crawler/` 目录执行

---

#### Q2: 评论提取为 0 或很少？
**症状：** 评论区显示有大量评论，但提取结果只有 0-3 条

**原因分析：**
1. **滚动加载未完成** - 小红书使用懒加载，需要多次滚动
2. **DOM 结构变化** - 小红书更新了前端代码
3. **登录态失效** - 部分评论需要登录才能查看

**解决方案：**
1. 脚本已内置 5 次滚动，如仍不足可手动增加：
   ```bash
   # 修改 xhs_extractor.py 中的 scroll_times 参数
   python3 scripts/legacy/xhs_extractor_v2.py "<url>" --scroll-times 10
   ```
2. 检查 Chrome 中是否已登录小红书
3. 如 DOM 结构变化，需更新 `extractors.js`（⚠️ 谨慎操作）

**Fallback：**
- 评论不足时标注 `"[评论数据不足]"`，继续生成其他章节

---

#### Q3: OCR 失败或识别率低？
**症状：** 轮播图 OCR 返回空或乱码

**排查步骤：**
1. 检查 Qwen3-VL 服务状态：
   ```bash
   curl $QWEN_API_URL/../models
   # 应返回可用模型列表
   ```
2. 检查图片是否成功截图：
   ```bash
   ls -la /tmp/xhs_*.png
   ```
3. 跳过 OCR 快速验证：
   ```bash
   python3 scripts/legacy/xhs_extractor_v2.py "<url>" --no-ocr
   ```

**优化建议：**
- 确保 Qwen3-VL 服务在本地运行（默认端口 9998）
- 对于纯文字笔记，可直接使用 `--no-ocr` 提升速度

---

#### Q4: Cookie 失效如何更新？
**症状：** API 模式返回 401 或 "登录过期"

**解决步骤：**
1. 在 Chrome 中登录小红书
2. 打开 DevTools → Application → Cookies
3. 复制 `web_session` 和 `a1` 字段的值
4. 更新 Cookie：
   ```bash
   python3 scripts/legacy/cookie_manager.py save 'web_session=xxx;a1=xxx'
   ```

**自动化方案：**
- 使用 CDP 模式继承浏览器登录态，无需手动管理 Cookie

---

#### Q7: IP 被小红书封锁（错误 300012）？
**症状：** 浏览器导航到小红书后显示"安全限制"页面，错误码 300012，`error_msg=IP at risk`

**根因：** 小红书对非住宅代理 IP、数据中心 IP、或频繁访问的 IP 实施风控封锁。CDP 和 API 模式都会同时被封。

**处理流程（严格遵守）：**
1. ❌ **不要尝试换方案** — web_extract / browser_navigate / Tavily / CDP / API 全都会被同一个 IP 封锁，切换只是浪费 token
2. ✅ **立即止损** — 确认错误后直接向用户汇报，附上已穷尽的方案列表
3. ✅ **提供三个选项** — (A) 提供 Cookie（`web_session` + `a1`）用 API 模式 (B) 换代理 IP (C) 手动复制内容发过来
4. ⚠️ **禁止**手动写 CDP WebSocket 脚本、浏览器截图 OCR、或搜索笔记 ID 跨平台转载 — 这些都已验证无效

**预防措施：**
- 提前配置 Cookie 可绕过 IP 风控（API 模式对登录用户更宽松）
- 使用住宅代理（如 Bright Data / Oxylabs）

---

#### Q5: 提取速度慢如何优化？
**优化策略：**

| 瓶颈 | 优化方案 | 效果 |
|:---|:---|:---|
| OCR 耗时 | 使用 `--no-ocr` 跳过 | 提升 50-80% |
| 评论滚动 | 减少 `--scroll-times` | 线性减少时间 |
| 网络延迟 | 使用代理 `--proxy` | 视网络环境 |
| 并发提取 | 批量模式（待实现） | 大幅提升 |

---

#### Q6: 报告保存到哪里？
**默认路径：** `~/Documents/Obsidian/AlexCai/00-Inbox/`

**自定义路径：**
```bash
export XHS_OUTPUT_DIR="~/Documents/MyReports"
python3 scripts/legacy/xhs_extractor_v2.py "<url>"
```

**自动检测逻辑：**
1. 查找标准 Obsidian Vault 位置
2. 回退到 `~/clawd/00-Inbox/`
3. 确保目录存在，不存在则创建

---

### 错误代码速查

| 错误信息 | 原因 | 解决方案 |
|:---|:---|:---|
| `CDP Connection Error` | 浏览器未启动 | 启动 Chrome（或 Comet） |
| `TimeoutError` | 页面加载超时 | 检查网络，增加超时时间 |
| `JSONDecodeError` | 提取数据格式异常 | DOM 结构变化，需更新 extractors.js |
| `OCR Service Unavailable` | Qwen3-VL 未启动 | 启动 OCR 服务或使用 `--no-ocr` |
| `Cookie Expired` | 登录态失效 | 更新 Cookie 或使用 CDP 模式 |
| `Rate Limited` | 请求过快 | 增加延迟，降低并发 |
| `IP at risk (300012)` | 当前 IP 被小红书风控封锁 | 见 Fallback 策略：立即止损上报用户，禁止继续尝试其他方案。不要换方案魔改 CDP WebSocket 手写脚本。直接用 XHS-Downloader + `cookie:""` 重试 |
| `XHS-Downloader 失败 (empty cookie)` | cookie 参数传了 null 或未传 | 改为 `"cookie":""` 显式传空字符串 |

---

### 调试技巧

**1. 查看详细日志：**
```bash
python3 scripts/legacy/xhs_extractor_v2.py "<url>" --verbose
```

**2. 手动验证 CDP：**
```bash
# 检查 CDP 端点 (Chrome Extension)
curl http://127.0.0.1:18792/json/list | head -20

# 检查页面元素
# 在 Chrome 中打开笔记，Console 中运行 extractors.js 内容
```

**3. 测试 API 签名：**
```bash
python3 -c "from xhshow import Xhshow; print(Xhshow().sign_headers('GET', '/api/sns/web/v1/feed', ''))"
```

**4. 清理临时文件：**
```bash
rm -f /tmp/xhs_*.json /tmp/xhs_*.png /tmp/xhs_*.txt
```

---

## 参考文档

| 文档 | 用途 | 加载时机 |
|:---|:---|:---|
| `references/xhs-downloader-integration.md` | XHS-Downloader 部署手册、已验证工作流、样本数据 | 首次使用 XHS-Downloader 或遇到问题 |
| `references/execution-guide.md` | 详细执行步骤、依赖配置 | 首次使用或遇到问题 |
| `references/xhs-report-prompt.md` | 报告生成 LLM 模板 | 报告生成阶段 |
| `references/ARCHITECTURE.md` | 技术架构、错误处理工作流 | 调试/开发时 |
| `OPTIMIZATION.md` | 优化记录、已知问题 | 性能调优时 |

---

## 免责声明

仅供个人学习研究使用，请遵守小红书用户协议。

---

## 已知问题

- XHS-Downloader 免登录模式**拿不到评论与轮播图 OCR**（架构限制，非 bug）；需要这两类数据时用 `scripts/legacy/` CDP 兜底。
- 裸 `explore/<note_id>`（无 `xsec_token`）易触发风控；优先用短链或带 token 的分享链。
- `scripts/legacy/xhs_extractor_v2.py` CDP 模式在无登录态时超时（120s+），仅在有 Cookie 时作兜底。
- xhshow 库的签名算法依赖小红书前端加密逻辑，需定期更新。

---

## 更新日志

### 2026-06-10 v6.0.0 XHS-Downloader 库直调 TDD 重构版

**架构变更：**
- ✅ **主力后端改为「库直调 + 子进程」** — 弃用 HTTP API 模式，经 `xhs_backend.fetch_note` 调用跑在独立 Python 3.12 venv 的 runner 子进程（stdin=url / stdout=JSON）
- ✅ **双解释器模型** — skill 胶水层 3.9 兼容；XHS-Downloader 隔离进 uv venv(3.12)。子进程边界同时是版本隔离层与测试 mock 缝
- ✅ **幂等 bootstrap** — `xhs_bootstrap.py` 自动 clone 到 gitignored `.xhs-downloader/` 并 uv sync，含 doctor 自检
- ✅ **数据适配器** — `xhs_adapter.py` 映射返回数据为报告模板输入契约；缺失的评论/OCR 输出标准标注而非杜撰（P0）
- ✅ **URL 规范化保留 xsec_token** — `prepare_url` 绝不把带 token 的链接削成裸 id

**TDD：**
- ✅ 77 个单元测试（adapter / url / backend / bootstrap），严格先红后绿
- ✅ 联网金丝雀 `XHS_LIVE_TEST=1`（已验证笔记 `6a116dd8...`），默认跳过
- ✅ 实跑暴露并修复「库进度信息污染 stdout」bug（runner 重定向 stdout→stderr + classify 末行解析）

**旧代码：**
- ✅ CDP 链路（v2 + OCR + cookie_manager + extractors.js）隔离到 `scripts/legacy/`，留作评论/OCR 兜底
- ✅ 删除 `xhs_full_extractor.py`（语法错误）、`xhs_extractor.py`（v1，被 v2 取代）
- ✅ `claude.md` 从 v5 拉齐到双解释器架构

### 2026-06-10 v5.5.0 XHS-Downloader 集成版

**重大更新：**
- ✅ **XHS-Downloader 成为主力后端** — 免 Cookie 提取元数据、标签、互动数据、图片 URL
- ✅ **`cookie:""` 工作记录** — XHS-Downloader 传空字符串才能触发无登录路径
- ✅ **uv sync 作为安装方案** — 比 pip+venv 更可靠（解决 Python 3.12 venv ensurepip 问题）
- ✅ **Fallback 策略重排** — XHS-Downloader API → CDP → xhshow API
- ✅ **IP 风控处理文档** — 遇到 300012 立即止损，不要再轮换方案
- ✅ **已知问题记录** — xhs_full_extractor.py 语法错误、xhs_extractor_v2 超时

**修复问题：**
- ✅ **移除 OpenClaw 引用** - 更新为原生 Chrome CDP（端口 19222）
- ✅ **xhshow 安装文档** - 添加 setup.py 创建和 pip3 install -e . 步骤
- ✅ **Python 版本兼容** - 记录 3.9+ 降级安装方法
- ✅ **创建 xhs_extractor_v2.py** - 修复轮播图检测、App限制、降级处理
- ✅ **更新 SKILL.md** - 同步所有环境变量和端口配置

### 2026-02-23 v5.3.0 完整提取规范版

**新增功能：**
- ✅ **完整执行检查清单** - 6步骤22项检查点，确保每次提取完整
- ✅ **xhs_full_extractor.py** - 一键完整提取脚本（含OCR+自动清理）
- ✅ **即时清理机制** - 每完成一张OCR立即删除截图，避免磁盘堆积
- ✅ **详细执行指南** - 添加完整执行流程和故障排查速查表

**改进优化：**
- ✅ 浏览器从 Comet 迁移到 Google Chrome
- ✅ CDP 地址更新为 `http://127.0.0.1:19222`
- ✅ 环境变量名更新为 `CHROME_CDP_URL`
- ✅ 文档中添加完整的检查清单和使用示例

### 2026-02-06 v5.2.0 深度扩展可选版

**新增功能：**
- ✅ **深度扩展可选项** - 基础报告生成后询问用户是否深度扩展
- ✅ **多智能体协作流程** - 调用 Librarian 进行多源深度搜索
- ✅ **扩展内容规范** - 明确深度扩展的搜索维度和内容范围
- ✅ **用户决策指引** - 提供场景化的决策建议（何时推荐/不推荐）

**改进优化：**
- ✅ 修复 `xhs_extractor.py` SyntaxWarning（转义序列问题）
- ✅ 重构 `xhs_carousel_ocr.py` 支持本地文件夹路径
- ✅ 添加 Issue 追踪文档（`ISSUES/issue-002-carousel-ocr-problems.md`）

### 2026-02-06 v5.1.0 重构优化版

**新增功能：**
- ✅ **P0 约束章节** - 添加强制输出检查清单和数据获取 Fallback 策略
- ✅ **扩展故障排除** - FAQ 格式，包含 6 个常见问题及解决方案
- ✅ **数据引用规范** - 明确评论引用格式和数据不足标注规范
- ✅ **隐私安全红线** - 明确禁止存储的敏感信息类型
- ✅ **错误代码速查表** - 快速定位问题原因
- ✅ **参考文档索引** - 清晰说明各 references 文件的用途和加载时机

**架构改进：**
- ✅ 完善渐进式披露结构（SKILL.md → references/execution-guide.md）
- ✅ 添加数据契约验证规范
- ✅ 明确错误处理工作流

**待实现（参见 OPTIMIZATION.md）：**
- 🔄 断点续传功能（ResumableCrawler）
- 🔄 自适应延迟机制
- 🔄 批量提取模式

### 2026-02-04 v5.0.0 初始版本

**核心功能：**
- ✅ 链接提取模式（CDP + Playwright）
- ✅ 关键词搜索模式（API + xhshow 签名）
- ✅ 创作者分析模式
- ✅ 轮播图 OCR（Qwen3-VL）
- ✅ 7 章节报告生成

**技术特性：**
- ✅ 混合架构（CDP + API）
- ✅ 实时进度汇报（emoji 前缀）
- ✅ Cookie 管理器
- ✅ URL 解析器

---

## 📋 优化记录

**已知问题与待实现功能：** 参见 `OPTIMIZATION.md`
