# L3 / full-auto GOAL 闭环（OMP 等价实现）

OMP 没有 `/goal` 原语；L3/full-auto 闭环用 `async task` + `todo` + `gates.mjs` + `irc` 等价实现。

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
VERDICT_SCHEMA: { id, pass, anchor, blocking, next_action }
MODE: interactive|full-auto
```

## Verdict 结构

每条验收产出：

```json
{
  "id": "<acceptance item id>",
  "pass": true,
  "anchor": "exit 0 [eval js, line 12]",
  "blocking": false,
  "next_action": "pass"   // ← rebuild | escalate | pass
}
```

`next_action` 路由：
- `rebuild` → 回 ③Build
- `escalate` → 上报你（人审）
- `pass` → 下一项

Coordinator 读 `next_action` 路由，不自行改判。

## Escalation 预分流表

| 自核放行 (auto) | 上报人审 (escalation) |
|---|---|
| 措辞/范围微调、口径降格、可逆低风险 | 证伪某条宏观验收契约 |
| 单条验收 anchored 通过 | 需求与实现双方有据的直接矛盾 |
| 证据齐 + 判定可锚 | 命中 danger 清单 / 不可逆 / 发布 / 需外部信息 |

两护栏：
1. 打标拿不准 → 默认归人审
2. 审定结论是下游唯一指令源，coordinator 不得绕过自行改判

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
5. **状态外置**：使用 `.stdd/counters/` 和 `.stdd/beam3-control.md`，不依赖 session 内存。
6. **checkpoint / rewind / handoff**：长循环用 `checkpoint`（标 slice 边界供折叠报告）+ `rewind`（剪枝探索上下文、留精炼报告，缓解 U 型注意力衰减）；跨会话 L3 收尾用 `/handoff`（移交摘要 + 新会话）或 `/compact`；会话级分叉用 `/fork`/`/branch`/`/resume`。**`checkpoint`/`rewind` 默认 off，需 settings 启用**。

## Discover 触发示例

- 定时：`async task` 带 delay 或外部 cron 触发 OMP。
- API：webhook 接收后调用 `task`。
- 文件：`glob`/`grep` 检测到变更后启动 loop。

## 失败处理

| 情况 | 动作 |
|---|---|
| regen ≥ 3 | 停；输出审计报告；升级人工 |
| slice ≥ 2 | 停；重新拆分 Spec/Accept |
| auditor REJECTED | 回 Spawn；regen +1 |
| Accept 本身错误 | 回 Plan；slice +1 |
| 沉默/超时 | 标记失败；升级人工 |

## eval 编排式 full-auto（确定性更高）

在 `eval` cell 内用内置助手 `agent()`/`parallel()`/`pipeline()`/`completion()` 编排 verdict 路由：

```js
// 最小骨架（OMP eval js）
var { bumpCounter } = await import('./scripts/gates.mjs');

// spawn 执行者
var exec = await agent("<build assignment>", { agent: "task" });
// agent://<id> 产出自动可读

// spawn 审核者
var auditVerdict = await agent(
  `审核以下产出：${exec.output}\n对应契约：${verdict.contract}`,
  { agent: "reviewer", schema: verdictSchema }
);
// 多 slice 用 parallel([...])

// 按 verdict 路由
if (auditVerdict.next_action === 'rebuild') {
  // 再 agent() 重试
} else if (auditVerdict.next_action === 'escalate') {
  // 停升级
} else {
  // pass → 下一项
}
```

`agent()` / `parallel()` / `pipeline()` / `completion()` 是 OMP `eval` 内置助手（见 OMP 手册 §5）。
