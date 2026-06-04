# Obsidian 三省六部知识库核查陷阱

用于核查 `20-Areas/10_AI实践/三省六部_Hermes/` 是否需要更新时参考。

## 尚书省强制插入规则必须作为核查项

制度源 `three-provinces-constitution` 已规定：多步骤 Kanban 链必须采用：

`planner → reviewer → SHANGSHU → [engineer/auditor/archivist...] → final reviewer`

核查 Obsidian 三省六部文档时，必须搜索是否体现“尚书省协调卡 / 强制插入 / SHANGSHU / 尚书省不可替代”等制度语义。若 Obsidian 0 处体现，应列为 HIGH 更新项；否则未来只读知识库的人会继续漏掉尚书省。

## task ID 不是简单 yes/no 泄漏

搜索 `t_[a-f0-9]{8}` 时，不要只报告“有/无”。应分类：

- 合法审计追溯：`30_审计/` 中为了复盘链路引用 task chain，可保留，但应避免成为主制度入口的阅读负担。
- 可疑泄漏：`10_制度/` 活文档、`40_归档/` 架构正文、README 导航中出现测试 task ID，通常应改为语义化事件名或归档路径。
- 历史实施记录：`20_实施/` 中如为版本落地证据，可保留；如只是临时测试卡，应清理或脚注化。

门下复核应要求执行方给出“数量 + 路径 + 分类结论”，而不是声称 0 命中。

## 旧路径需分历史/活文档

`~/.hermes/notes/`、旧 profile 路径、旧 agent-registry 版本引用不能一概替换：

- 历史归档/吸收记录中的原始路径可保留；
- 活文档、README、当前名册、当前路线图中的旧路径或旧版本号应更新或加“历史路径”说明；
- 若同一事实已有 Obsidian 新目录与 `~/.hermes/notes/` 双轨并存，应说明 canonical 位置。

## Kanban worker skill 装载陷阱

不同 profile 的 skills 是独立副本。创建 Kanban 任务时用 `--skill three-provinces-constitution` 可能在 planner/reviewer 等 profile 下失败（Unknown skill），导致 worker 崩溃。稳妥做法：

1. 若必须强制 `--skill`，先确认目标 profile 拥有该 skill；
2. 否则在任务 body 中给出制度文件绝对路径，让 worker 直接 `read_file`；
3. 或先同步 skill 到目标 profile，再派工；
4. 失败链保留为故障证据，重建不强制 skill 的 v2/v3 链。
