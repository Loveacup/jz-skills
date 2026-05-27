# Auto-Diary Changelog

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
