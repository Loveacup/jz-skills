# L3 无人值守 GOAL 闭环

OMP 没有 `/goal` 原语；L3 闭环用 `async task` + `todo` + `gates.mjs` + `irc` 等价实现。

## GOAL 最小模板

```yaml
GOAL: <一句话目标>
ACCEPT:
  - <可证伪项 1>
  - <可证伪项 2>
REJECT_IF:
  - <任何一项触发即失败>
STOP_AFTER:
  regen: 3
  slice: 2
AUDITOR: reviewer   # 或 oracle / 可选 stdd-auditor
ESCALATE: 升级人工（计数器满、 auditor 无法判定、REJECT_IF 命中）
```

## Loop 入口 Discover 适配器

```text
Discover：识别触发条件（时间/API/事件）
  |
  v
Plan：生成 Spec + Accept，等待 approve
  |
  v
Spawn：async task executor（ Build ）
  |
  v
Gate：gates.mjs 客观验证 + auditor 主观审计
  |
  v--- FAIL --- back to Plan/Spawn （计数器 +1）
  |
  v--- PASS --- 收尾 + memory 回写
```

## 关键约束

1. **强制独立 auditor**：executor 不能审自己；auditor 无 edit/write。
2. **计数器硬顶**：regen 满 3 或 slice 满 2 必须停。
3. **irc turn-done**：executor 完成时发 `irc send`；coordinator 用 `irc wait` 接收。
4. **沉默即失败**：约定时间内无 irc 完成信号 → 视为失败，升级人工。
5. **状态外置**：使用 `.stdd/counters/` 和 `.stdd/L3-control.md`，不依赖 session 内存。

## Discover 触发示例

- 定时：`async task` 带 delay 或外部 cron 触发 OMP。
- API：webhook 接收后调用 `task`。
- 文件：`glob`/`grep` 检测到变更后启动 loop。（OMP 16.2.0+ 工具名）

## 失败处理

| 情况 | 动作 |
|---|---|
| regen ≥ 3 | 停；输出审计报告；升级人工 |
| slice ≥ 2 | 停；重新拆分 Spec/Accept |
| auditor REJECTED | 回 Spawn；regen +1 |
| Accept 本身错误 | 回 Plan；slice +1 |
| 沉默/超时 | 标记失败；升级人工 |
