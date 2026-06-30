# Dogfood 埋点系统 · 设计笔记

> v1.27.0 新增。每次 cc-finish 自动埋点，累计 5 条触发摩擦摘要。

## 设计原则

- **不依赖 Hermes 记得**——cc-finish.sh 收尾时自动写记录，零额外操作
- **累计触发而非定时触发**——低频使用时不浪费，高频使用时自然触发
- **静默积累，到点才报**——<5 条时一句话不打扰用户

## 数据流

```
cc-finish.sh（收尾时自动）
  → emit_dogfood() → >> /tmp/cc-dogfood.jsonl
  → Hermes 调 cc-dogfood-report.sh
  → 累计 ≥5 条？→ 📊 摘要 → 否则静默
```

## 埋点字段

| 字段 | 含义 | 来源 |
|------|------|------|
| `ts` | UTC 时间戳 | cc-finish |
| `session` | tmux session 名 | cc-finish |
| `target` | lock target | cc-finish |
| `residue_danger` | ❯残留命中危险模式 | cc-finish §1 (exit 10) |
| `residue_benign` | ❯残留非危险 | cc-finish §1 |
| `monitor_gap_s` | 最大心跳间隙 | cc-finish §3 |
| `gap_blocked` | 因间隙拒绝收尾 | cc-finish §4 (exit 2) |
| `turn_done_missing` | 无完成信号 | cc-finish §2 |
| `states` | 状态序列 | cc-finish §3 |
| `exit_code` | 最终退出码 | cc-finish |

## 摘要信号映射

| 信号 | 阈值 | → 排查建议 |
|------|:--:|------|
| `residue_benign` | >0 | Pitfall #5/#18 —— cc-send 发后回读 |
| `monitor_gap_s` | >120s | 心跳维护盲区 |
| `residue_danger` | >0 | 立即排查残留来源 |
| `gap_blocked` | >0 | 监控间隙 > 心跳/cadence |
| `turn_done_missing` | >0 | Stop hook 是否已部署 |

## 测试隔离

`CC_DOGFOOD_LOG` / `CC_DOGFOOD_STATE` 环境变量可覆盖默认路径，测试完全不碰真实 dogfood 历史。
