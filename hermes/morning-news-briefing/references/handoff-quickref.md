# 交接协议快捷参考（Handoff Quick Reference）

完整规范见 `shared/handoff_schema.md`。

## 子 agent 产出必含 YAML

```yaml
task_id: [string]
stage: [六部 | 分析 | 史馆]
artifacts: [{path, type, summary}]
integrity_signals: {sources_count: N, cross_check_done: bool}
boundary_violation: false
state: {status, last_event, previous_status, checkpoint_data, resume_from}
error_report: null              # 或 {error_type, root_cause, suggested_fix}
concession_log:                 # 仅分析类
  total_challenges: N
  total_concessions: N
  consecutive_concessions: N    # 必须 ≤1
```

## 校验要点

| 检查 | 规则 |
|------|------|
| 交接字段 | 缺 → 退回重做 |
| boundary_violation | true → 自动退回上一阶段 |
| consecutive_concessions | >1 → 反骑墙预警，退回 |
| error_report 超长 | >500 字 → 退回压缩 |
| state 与 Kanban 不一致 | → 御史标记异常 |

## SOUL 进奏规矩速查

| # | 条款 | 关键词 |
|---|------|--------|
| 1 | 无触发词 | 父皇直说 |
| 2 | 承旨必复 | 确认无差 |
| 3 | 太子不亲操 | 复杂任务派工 |
| 4 | 先奏后行 | 方案先呈 |
| 5 | 绑定依赖 | parent 绑定 |
| 6 | 节制六部 | 横向必有 task_id |
| 7 | 限递归深 | 默认两层 |
| 8 | 验收有凭 | diff/log/证据 |
| 9 | 交接必验 | handoff 字段 |
| 10 | 错误压缩 | ≤500字三字段 |
| 11 | 状态管理 | (state,event)→new_state |
| 12 | 中断恢复 | >5min checkpoint |
