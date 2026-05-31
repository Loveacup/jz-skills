---
name: xhs-crawler
description: |
  小红书内容提取与深度分析。支持链接提取、关键词搜索、创作者主页爬取。
  通过 CDP 自动化提取正文、评论、轮播图 OCR，生成结构化知识资产报告。
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

# 小红书内容提取器 v5

小红书（XiaoHongShu/RedNote）全功能内容提取技能。支持三种模式：

1. **链接提取** — 发送小红书链接，通过 CDP 自动提取正文、评论、轮播图 OCR，输出结构化 JSON
2. **关键词搜索** — 通过 API 按关键词搜索笔记列表
3. **创作者分析** — 获取创作者主页信息和笔记列表

提取后由 agent 自身 LLM 能力按 `references/xhs-report-prompt.md` 模板生成知识资产报告。

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

**链接提取失败时的降级链：**
1. **CDP 提取失败** → 尝试 API 模式（`xhs_api.py`）获取基础数据
2. **API 模式失败** → 返回错误 + 已获取的部分数据（不中断流程）
3. **评论加载失败** → 标注"[评论数据不可用]"，保留其他章节
4. **OCR 失败** → 跳过 OCR，保留正文和评论文本内容
5. **轮播图为 0** → 分析无轮播图原因（单图笔记或提取失败）

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

### 安装检查清单

首次使用或遇到问题时，按此顺序检查：

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
python3 {baseDir}/scripts/cookie_manager.py save 'web_session=xxx;a1=xxx'
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

### 推荐：完整提取（含OCR和自动清理）

**一键提取所有内容（正文+评论+完整OCR+自动清理）：**

```bash
python3 {baseDir}/scripts/xhs_full_extractor.py "<小红书链接>"
```

**示例：**
```bash
python3 {baseDir}/scripts/xhs_full_extractor.py "http://xhslink.com/xxxxx"
```

**功能：**
- ✅ 基础数据提取（标题、作者、正文、标签）
- ✅ 评论区滚动加载和去重
- ✅ **完整轮播图OCR**（12张图全部识别）
- ✅ **即时清理**（每完成一张OCR立即删除截图）
- ✅ 生成 JSON + 文本格式输出
- ✅ 最终临时文件清理

**打印检查清单：**
```bash
python3 {baseDir}/scripts/xhs_full_extractor.py --checklist
```

---

### 模式 1：链接提取（CDP - 基础版）

**触发：** 直接发送小红书分享链接

```
http://xhslink.com/xxxxx
```

**流程：**
1. CDP 连接 Chrome → 导航到笔记页面（继承登录态）
2. 滚动加载评论区（5 次滚动）
3. JS 注入提取正文、评论、标签、图片 URL、互动数据
4. 轮播图逐张截图 → Qwen3-VL OCR（可通过 `--no-ocr` 跳过）
5. 输出 JSON 数据到 stdout

**命令行：**
```bash
python3 {baseDir}/scripts/xhs_extractor.py "<小红书链接>"
python3 {baseDir}/scripts/xhs_extractor.py "<小红书链接>" --no-ocr
```

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

| 脚本 | 用途 | 用法 | 推荐度 |
|------|------|------|:------:|
| `xhs_extractor_v2.py` | CDP 提取器（修复版） | `python3 {baseDir}/scripts/xhs_extractor_v2.py <url>` | ⭐⭐⭐ |
| `xhs_full_extractor.py` | 完整提取（含OCR+清理） | `python3 {baseDir}/scripts/xhs_full_extractor.py <url>` | ⭐⭐⭐ |
| `xhs_extractor.py` | CDP 提取器（原版） | `python3 {baseDir}/scripts/xhs_extractor.py <url>` | ⭐⭐ |
| `xhs_api.py` | 纯 API 客户端 | `python3 {baseDir}/scripts/xhs_api.py <url>` | ⭐⭐ |
| `xhs_carousel_ocr.py` | 轮播图 OCR | 由 xhs_extractor 调用 | - |
| `cookie_manager.py` | Cookie 管理 | `python3 {baseDir}/scripts/cookie_manager.py show` | - |
| `parse_xhs_url.py` | URL 解析 | `python3 {baseDir}/scripts/parse_xhs_url.py <url>` | - |
| `extractors.js` | 浏览器端 JS | 由 xhs_extractor 注入 | - |

## 故障排除

### 常见问题速查 (FAQ)

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
   python3 scripts/xhs_extractor.py "<url>" --scroll-times 10
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
   python3 scripts/xhs_extractor.py "<url>" --no-ocr
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
   python3 scripts/cookie_manager.py save 'web_session=xxx;a1=xxx'
   ```

**自动化方案：**
- 使用 CDP 模式继承浏览器登录态，无需手动管理 Cookie

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
python3 scripts/xhs_extractor.py "<url>"
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

---

### 调试技巧

**1. 查看详细日志：**
```bash
python3 scripts/xhs_extractor.py "<url>" --verbose
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
| `references/execution-guide.md` | 详细执行步骤、依赖配置 | 首次使用或遇到问题 |
| `references/xhs-report-prompt.md` | 报告生成 LLM 模板 | 报告生成阶段 |
| `references/ARCHITECTURE.md` | 技术架构、错误处理工作流 | 调试/开发时 |
| `OPTIMIZATION.md` | 优化记录、已知问题 | 性能调优时 |

---

## 免责声明

仅供个人学习研究使用，请遵守小红书用户协议。

---

## 更新日志

### 2026-05-14 v5.4.0 Hermes 迁移修复版

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
