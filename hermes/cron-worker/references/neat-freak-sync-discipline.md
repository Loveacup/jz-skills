# 洁癖后清理规范（neat-freak 范式吸收）

> 来源：[[Khazix Skills 深度分析]] § neat-freak。每次本 skill 完成一个 milestone（迁移 / 重构 / 大批量写入）后强制走一遍三层同步。
> 吸收日期：Khazix neat-freak 范式吸收 v1, 2026-05-31

## 三层知识架构（受众分层）
| 层 | 受众 | 典型位置 |
|---|---|---|
| Agent 记忆 | Agent 自己跨会话复用 | `~/.claude/projects/<...>/memory/`, `AGENTS.md`, `.opencode/` |
| 项目根 `CLAUDE.md` | 当前项目里的 AI | 项目约定、红线、命令速查 |
| `docs/` + `README.md` | 其他人（人类同事、未来接手的 AI） | 接入指南、架构图、运维手册 |

## 核心心法
1. **规则手册 ≠ 变更日志**——判断「下次 AI 没看到这条会不会犯错？」
2. **减优于加 / 合并优于追加 / 删除优于保留**
3. **净涨幅 ≤ 30 行红线**——单次同步净增 > 30 行必先精简
4. **绝对时间**（"上周" → "2026-05-24"）
5. **指针不重复**——SKILL.md 不抄 reference 全文

## 五步流程（post-task sync）
1. 尺寸体检：`wc -l` 检查 SKILL.md、CLAUDE.md
2. 盘点现状：`ls references/`
3. 变更影响矩阵：本次改动涉及哪些下游文档需要同步
4. 实际修改：遵循"减优于加"
5. 双组自检：尺寸（防膨胀）+ 完整性（防漏改）

## 在本 skill 的具体触发点
- 每次 schema 变更 / 字段重命名 → 同步 references/ + 调用方文档
- 每次新增/废弃 API 端点 → 同步 SKILL.md 工作流章节
- 每次 milestone（完成一次大批量任务）→ 复盘是否有过期 reference 该删
