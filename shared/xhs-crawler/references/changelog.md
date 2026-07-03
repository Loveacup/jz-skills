# xhs-crawler 更新日志

<!-- 从 SKILL.md 拆出 -->

### 2026-07-03 v6.1.0 任务路由 + 瘦身

- ✅ **任务路由** — OpenCLI 设为采样/feed/search/热帖首选；XHS-Downloader 保持单篇深度报告首选；legacy CDP 保持评论/OCR 补齐；Browser-Harness 新增为 UI/DOM/debug fallback
- ✅ **SKILL.md 瘦身** — 故障排除和历史日志拆到 `references/troubleshooting.md` 和本文件
- ✅ **OpenCLI 口径约束** — feed=个人推荐流采样、search=关键词局部热度、多关键词聚类≠官方热榜
- ✅ **Browser-Harness** 限定为诊断 fallback，仅产出 partial/debug evidence

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

**待实现：**
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
