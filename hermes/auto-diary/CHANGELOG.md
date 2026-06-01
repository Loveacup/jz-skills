# Auto-Diary Changelog

## v3.4.0 (2026-06-01)
- 🔴 **质量事故复盘**：5 月全月日记批量重写翻车（缺 callout、三问缩写、CC 未分组、底部拍扁）。根因不是"凭记忆"，是**无机器校验闭环**。
- ✅ **重写 `verify_diary_compliance.py` v2.0**：修复"传单文件即 NotADirectoryError"崩溃；从"标题存在性扫描"升级为深度结构校验——新增三问三条齐全、CC 三组拆分、各体系 info callout、底部 `---` 分隔、abstract 速览四要素、禁折叠 callout 共 6 项。3 篇达标日记(05-29/30/31)回归全 PASS、不误报。
- 🔧 **修 SKILL.md 三处自相矛盾**：①"8 sections" → 10 sections（verify 查 13 项）；②删除"每周一 12:00 自动周报"幽灵描述（实际无此 cron，周报纯手动）；③`references/changelog.md` 悬空引用 → `CHANGELOG.md`。
- 🔧 **cron prompt v3.4 闭环**：写前先 `Read` 已有日记（合并安全）→ 写入 → 跑 verify → FAIL 重写直到 PASS。修正 CC 数据路径为 `ai_logs.claude_overview.*`。
- ⚠️ **已知 bug 记录**：`collect_data.py` 的 `existing_content`/`obsidian_sync` 恒为 `None`（硬编码），合并逻辑依赖 prompt 显式 Read 兜底。
- 🔀 **版本对齐**：部署端 v3.3 回流 git（此前 git 落后于生产）；确认两版 `collect_data.py` 输出 md5 一致、功能等价。

## v3.3.0 (2026-06-01)
- 🔴 新增红旗："NEVER write from memory" —— 凭记忆写日记导致全月重写。写任何日记前必须加载 `diary-format.md` 逐段对照。
- ✅ 新增 `references/batch-generation-pitfall.md`：批量脚本生成 = 垃圾，必须逐天 LLM 加工。

## v3.2.0
- 💻 CC 三组分类：🤝 Agent Team 协作 / 💻 独立对话 / 🤖 程序调用，基于 CC 元数据(entrypoint + parentUuid)。

## v1.0.1 (2026-02-02)
- 🔧 修复天气获取：添加 User-Agent header 和更长超时，解决 wttr.in 请求被拒绝问题
- 🔧 修复 AI 日志噪声：过滤系统指令（SYSTEM DIRECTIVE、system-reminder 等），仅保留有效对话摘要
- 🔧 修复 cron job 配置：改用 `clawdbot cron edit/add` CLI 命令配置，避免 gateway 内存回写覆盖手动编辑

## v1.0.0 (2026-02-02)
- ✅ 初始版本，基于 skill-creator 方法论创建
- ✅ Python 数据采集脚本 (`collect_data.py`)：天气、AI 对话日志、知识库变更监测、已有日记内容
- ✅ 知识库变更监测：扫描 Obsidian vault 当天新建/修改的笔记，区分类型+标题+摘要
- ✅ 两个工作流：每日日记 (23:00) + 每周周报 (周一 12:00)
- ✅ 格式规范：diary-format.md + weekly-format.md（渐进式披露）
- ✅ 合并策略：existing_content 不为 null 时保留用户已写内容
- ✅ Cron job 配置：替代原有内联 prompt，简化为 skill 调用
- ✅ HEARTBEAT.md 日记任务迁移重定向
