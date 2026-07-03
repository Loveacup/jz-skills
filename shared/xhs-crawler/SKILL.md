---

name: xhs-crawler
description: >-
  type: routine
  小红书内容提取与深度分析。任务路由：OpenCLI（采样/feed/search/热帖首选）；XHS-Downloader（单笔记深度报告，免登录库直调子进程）；legacy CDP（评论/OCR补齐）；Browser-Harness（UI/DOM诊断fallback）。
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

小红书（XiaoHongShu/RedNote）内容提取与趋势采样技能。后端按任务类型路由：
- **OpenCLI** 是采样 / feed / 热帖估算 / 趋势 / 关键词搜索的首选路径，读取已登录 Chrome 会话并返回结构化列表。
- **XHS-Downloader** 仍是单篇笔记深度提取与 7 章节报告的首选路径，负责元信息、正文、标签、互动数据、图片 URL 和报告输入契约（第三方开源工具，免登录提取，以**库调用 + 子进程**形式集成，非 HTTP API、非 MCP）。
- **legacy CDP** 仍用于深度报告中必须补齐的评论与轮播图 OCR（需 Chrome CDP + 登录态）。
- **Browser-Harness** 只用于 OpenCLI adapter 覆盖不到的 UI/DOM/debug 缺口；结果必须标注 partial/debug evidence，不能冒充完整提取。

提取后由 agent 自身 LLM 能力按 `references/xhs-report-prompt.md` 模板生成知识资产报告。

> **架构**：skill 胶水层跑在 Hermes 默认 `python3`（3.9）；XHS-Downloader 因要求 ≥3.12 且依赖重，被隔离进自己的 uv venv，经子进程（stdin=url / stdout=JSON）调用。详见 `claude.md`。

## 任务路由

1. **采样 / 热帖 / 趋势 / feed / search → OpenCLI**
   - `opencli xiaohongshu feed/search` 返回 `{id,title,type,author,likes,url}`。
   - 输出口径必须标注：feed 是个人推荐流采样；search 是关键词局部热度；多关键词聚类也不是官方全站热榜。
2. **单篇笔记深度提取 / 7 章节报告 → XHS-Downloader**
   - 保持 `scripts/xhs_backend.py` 与 `cookie=""` 空字符串约束。
   - 评论/OCR 不足时标注，不杜撰。
3. **深度报告补评论 / OCR → legacy CDP**
   - 仅在需要评论或轮播图 OCR 时启用。
4. **UI/DOM/debug 缺口 → Browser-Harness**
   - 先 `browser-harness --doctor`，再检查页面/截图/DOM/网络。
   - 只产出诊断证据或 partial 数据；能沉淀成稳定流程时再回到 OpenCLI adapter。

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

**采样 / search 降级链：**

1. **OpenCLI adapter**：`feed` / `search` with `--site-session persistent`。
2. **OpenCLI browser diagnostics**：`opencli doctor`、`opencli browser <session> ...` 仅当 adapter 报错需要 bridge/DOM/network 证据时使用。
3. **Browser-Harness**：仅当 OpenCLI browser 无法暴露所需 UI/DOM 状态或 agent 需要可视化 CDP 检查时使用。
4. **Stop 或返回 partial evidence**。不要默默切换到无关的通用爬虫。

**单篇深度提取降级链：**

1. **XHS-Downloader** `xhs_backend.py`（首选）— `python3 scripts/xhs_backend.py <链接>`（或 `from xhs_backend import fetch_note`），免 Cookie 即可获取标题/描述/标签/互动数据/图片 URL。**关键：胶水层永远显式传 `cookie=""` 空字符串触发免登录路径，传 null 或不传会失败（已固化在 `build_command` 里）。**
2. **ok 且报告不需评论/OCR**：生成报告，标准 missing-data 标注。
3. **ok 但需要评论/OCR**：legacy CDP fallback。
4. **XHS-Downloader 失败**：优先带 tokenized 分享链/短链，再尝试 legacy CDP（如有意义）。
5. **IP 风控 300012**：**立即止损**；停止所有尝试，向用户汇报已穷尽方案，提供三个选项：(A) 提供 Cookie 换 API 模式 (B) 换代理 IP (C) 手动复制内容。禁止继续轮换其他方案，每多试一次都是浪费 token。
6. **invalid_url**：ask for valid XHS URL。
7. **legacy CDP 因登录/CDP 失败**：标注不可用或询问用户恢复登录/CDP。
8. **Browser-Harness 仅用于诊断页面状态**，不能声称完整提取。

**通用浏览器/爬虫工具定位：**
- 不要用 Crawl4AI、普通 web_extract、通用 browser-agent 替代本 skill 作为小红书主力；这些工具通常缺少小红书专用登录态、评论加载、轮播图 OCR、报告结构和数据完整性检查。
- 可用 agent-browser/Playwright MCP/Browser-Harness 作为**诊断和兜底**：检查页面是否登录、分享链接是否跳转、DOM 是否变化、评论/轮播图是否能手动展开、截图是否可 OCR。
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

### OpenCLI：采样 / feed / 热帖 / search（⭐ 首选）

**适用场景：** 用户问”小红书今天热门是什么””看热帖””看首页推荐流/某关键词热帖/趋势”。此类任务优先用 OpenCLI 读取小红书 hydrated store，字段稳定、输出结构化，不要直接用通用 DOM 抓取作为主路径。

**前置体检：**
```bash
opencli --version
opencli doctor
opencli list -f json
opencli xiaohongshu --help
opencli xiaohongshu whoami -f yaml --window foreground --site-session persistent
```
预期证据：version ≥ v1.8.5；doctor green for browser bridge；xiaohongshu command help 列出 `feed` 和 `search`。

**Feed 采样（个人首页推荐流，不是全站热榜）：**
```bash
opencli xiaohongshu feed --limit 3 -f yaml --window foreground --site-session persistent
opencli xiaohongshu feed --limit 30 -f json --window foreground --site-session persistent
```
输出字段通常含：`id / title / type / author / likes / url`。报告为”个人推荐流采样”，不是官方热榜。

**关键词搜索 / 趋势采样：**
```bash
opencli xiaohongshu search “AI Agent” --limit 20 -f json --window foreground --site-session persistent
opencli xiaohongshu search “杭州” --limit 20 -f json --window foreground --site-session persistent
opencli xiaohongshu search “影视飓风 100小时” --limit 20 -f json --window foreground --site-session persistent
```
后处理指引（agent）：按 `id` 或规范化 `url` 去重；解析 `likes`（如 `1.3万`）；按点赞与主题重复频率排序；聚类重复标题/主题；标注证据为关键词局部采样。

**关键口径：** 小红书网页版没有稳定公开的全站热榜。所谓”热帖”只能是采样估算：
- `feed` = 个人首页推荐流
- `search <query>` = 关键词局部热度
- 多关键词/多频道聚类 = 更接近趋势，但仍非官方榜单

**Pitfall：不要把隔离浏览器误当主 Chrome。** 如果之前用过 `browser-harness-isolated` 或自启 `--user-data-dir=...isolated-chrome-profile`，先确认并停掉隔离 Chrome，再声明”主 Chrome 登录态”。可用以下检查思路：确认 OpenCLI `whoami.logged_in=true`；若用 browser-harness，确认 daemon log/DevTools endpoint 指向主 Chrome 而非 `9223` isolated profile。用户纠正”这个没登录用户的 Chrome”时，立即重验浏览器来源，不要辩解。

### legacy CDP 兜底（评论 + 轮播图 OCR）

仅当 XHS-Downloader 主力路径已拿到元数据、但报告**必须**补齐评论或图文 OCR 时启用。
前提：Chrome CDP（端口 19222）+ 小红书登录态。详见 `scripts/legacy/README.md`。

```bash
cd /Users/alexcai/.hermes/skills/xhs-crawler
python3 scripts/legacy/xhs_extractor_v2.py "<小红书链接>"
python3 scripts/legacy/xhs_extractor_v2.py "<小红书链接>" --no-ocr
```

**流程：** CDP 连接 Chrome（继承登录态）→ 滚动加载评论 → JS 注入提取正文/评论/标签/图片/互动 → 轮播图逐张截图 → Qwen3-VL OCR → 输出 JSON。

预期证据：JSON 包含 title/author/content/tags/comments/images/stats/carousel_ocr/full_content，或明确的 login/CDP/OCR failure。评论和 OCR 缺口必须标注，不能杜撰。

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

### OpenCLI browser 诊断 fallback

仅当 adapter 失败或需要 schema/DOM/debug 证据时使用：

```bash
opencli doctor
opencli browser xhs-debug bind
opencli browser xhs-debug state
opencli browser xhs-debug network --filter "note,title"
opencli browser xhs-debug screenshot /tmp/xhs-opencli-debug.png
opencli browser xhs-debug unbind
```

或 owned session：

```bash
opencli browser xhs-debug open "https://www.xiaohongshu.com"
opencli browser xhs-debug state
opencli browser xhs-debug close
```

预期证据：结构化 browser envelope，`error.code` when failing，`matches_n`/`match_level` for interactions，network keys or screenshot path when relevant。

### Browser-Harness fallback

仅在 OpenCLI adapter/browser 路径不足以用于 UI/DOM/visual 诊断之后使用：

```bash
browser-harness --doctor
browser-harness <<'PY'
print(page_info())
PY
```

如果主 Chrome 握手失败或有意需要干净隔离 profile：

```bash
browser-harness-isolated <<'PY'
print(page_info())
PY
```

页面检查（agent 已有真实 tab/session）：

```bash
browser-harness <<'PY'
print(page_info())
capture_screenshot()
print(js("""(() => ({url: location.href, title: document.title, text: document.body.innerText.slice(0, 1000)}))()"""))
PY
```

预期证据：page URL/title，screenshot when visual diagnosis matters，targeted DOM result。如使用 isolated profile，须说明不是登录态主 Chrome session。

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

**External CLI surfaces（外部命令行表面，非 scripts/ 内脚本）：**

| 表面 | 用途 | 用法示例 |
|------|------|----------|
| OpenCLI xiaohongshu | feed/search 采样 | `opencli xiaohongshu feed --limit 30 -f json --window foreground --site-session persistent` |
| OpenCLI browser | adapter 失败时的诊断 | `opencli doctor`、`opencli browser <session> state/network/screenshot` |
| Browser-Harness | UI/DOM/visual 诊断 fallback | `browser-harness --doctor`、`browser-harness <<'PY' ...` |

**测试：** `python3 -m pytest {baseDir}/tests/`（联网金丝雀默认跳过，`XHS_LIVE_TEST=1` 才跑）。

## 故障排除

常用排障速查。**完整 FAQ、错误代码速查表、调试技巧 → `references/troubleshooting.md`**。

| 症状 | 先看 |
|---|---|
| XHS-Downloader 提取失败 | `references/troubleshooting.md` §Q0 |
| CDP 连接失败 | §Q1 |
| 评论/OCCR 不足 | §Q2 / §Q3 |
| IP 风控 300012 | §Q7（立即止损！） |
| OpenCLI feed/search 失败 | §Q8 |
| Browser-Harness 连不上 | §Q9 |

---

## 参考文档

| 文档 | 用途 | 加载时机 |
|:---|:---|:---|
| `references/xhs-downloader-integration.md` | XHS-Downloader 部署手册、已验证工作流、样本数据 | 首次使用 XHS-Downloader 或遇到问题 |
| `references/execution-guide.md` | 详细执行步骤、依赖配置 | 首次使用或遇到问题 |
| `references/xhs-report-prompt.md` | 报告生成 LLM 模板 | 报告生成阶段 |
| `references/ARCHITECTURE.md` | 技术架构、错误处理工作流 | 调试/开发时 |
| `references/troubleshooting.md` | 完整 FAQ、错误代码速查、调试技巧 | 排障时 |
| `references/changelog.md` | 版本更新日志 | 了解变更历史时 |
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

最新变更 → `references/changelog.md`。

### 2026-07-03 v6.1.0 任务路由 + 瘦身

- ✅ **任务路由** — OpenCLI 设为采样/feed/search/热帖首选；XHS-Downloader 保持单篇深度报告首选；legacy CDP 保持评论/OCR 补齐；Browser-Harness 新增为 UI/DOM/debug fallback
- ✅ **SKILL.md 瘦身** — 故障排除拆到 `references/troubleshooting.md`、历史日志拆到 `references/changelog.md`
