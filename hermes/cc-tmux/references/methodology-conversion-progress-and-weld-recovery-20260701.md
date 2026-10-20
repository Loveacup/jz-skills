# 方法论转化任务：进度汇报 + 焊接收尾恢复案例（2026-07-01）

## 场景

用户要求：对 Obsidian Inbox 中的 YouTube 视频笔记，拉起 CC/cctmux 组建 agent team，先用战略洞察类 skill 做方法论转化，再用 research-fortification 做 additive-first 扩展焊接。

执行方式：
- CC Leader session：`cc-methodology-chicago-writing`
- 任务文件：`/tmp/cc-task-methodology-chicago-writing.md`
- 过程文件：`/tmp/cc-methodology-draft.md`、`/tmp/cc-methodology-diag.md`
- 最终文件：`00-Inbox/方法论_读者价值写作_20260701.md`

## 触发的问题

1. CC agent team 的后台 worker 长时间处于 `WAITING_AGENTS`，但 `/tmp/cc-methodology-draft.md` 和 `/tmp/cc-methodology-diag.md` 已经持续更新。
2. Hermes 没有按用户偏好及时汇报阶段性进度，用户中途提醒：“进度呢，你要汇报啊”。
3. 第一条 Leader session 已完成诊断并派出焊接 worker，但焊接 worker token 长时间冻结；直接等待会造成长时间无响应。

## 可复用处理模式

### 1. 长任务必须按“状态变化/产物出现”汇报

当 CC 任务超过 2-3 分钟，尤其出现 `WAITING_AGENTS`、`THINKING > 5min`、或 `/tmp` 产物文件已生成/增大时，Hermes 应主动发简短进度，而不是等最终交付。

推荐进度块：

```md
进度：CC 已完成 X，正在做 Y。
- 已有产物：/tmp/xxx.md（N KB）
- 当前状态：WAITING_AGENTS / THINKING
- 下一步：等 Z 完成；若 N 分钟无变化，我会收窄任务/另起小 session 收尾。
```

要求：只在有实质变化时汇报；不要刷屏。用户明确要求“进度呢”时，下一次可发消息机会应立即补进度。

### 2. 后台 worker 卡住时先看产物，不先判死

如果 monitor 显示：
- `WAITING_AGENTS`
- worker token 长时间不变
- `/tmp` 中已有 draft/diag 等阶段产物

先读/检查产物状态：
- 文件是否存在
- mtime/size 是否增长
- 是否包含可继续工作的足够信息

如果阶段产物已满足，不必等待原 worker 完美收尾。

### 3. 收尾失败时另起“小粒度 weld-only session”

当大 Leader session 已产出 draft + diag，但最后焊接 worker 卡住，可另起干净小 session，只给 3 个输入和 1 个输出目标：

```md
读取：
- /tmp/cc-methodology-draft.md
- /tmp/cc-methodology-diag.md
- 原始基底文档

只做一件事：按 research-fortification additive-first 焊入诊断软处，写最终 Obsidian 文档，并写 done marker。
```

本案例中，小 session `cc-methodology-weld-only` 成功写出最终文档与 marker。

### 4. 验收仍由 Hermes 做

CC marker 不是最终真相。Hermes 需要重新验证：
- 目标文件存在、行数/字节数合理
- YAML frontmatter 符合当前 vault `AGENTS.md`（status/type/priority/tags 前缀等）
- 有焊接台账
- 无 `TODO` / `骨架占位` / `待填充`
- 源文件未被改动

本案例中，CC 初稿 YAML 使用了不符合 vault 的 tag 前缀（`类型/`、`领域/`），Hermes 事后修正为 `type/`、`status/`、`src/`、`topic/`。

## 经验结论

- CC agent team 适合方法论转化 + 研究加固，但最后的焊接写作容易成为长上下文/后台 worker 卡点。
- “大 team 产阶段成果 + 小 session 收尾”是可靠恢复路径。
- 进度汇报是用户体验红线：对长任务，Hermes 需要在实质状态变化时主动报，不要让用户来催。