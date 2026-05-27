# 主动交付架构（Path B）

解决"看板清空后太子不主动复命"的结构性缺口。

## 问题

Telegram 请求-响应模式下，监国太子只在父皇发消息时运行。看板清空时，watchdog 推送机械文本，coordinator 输出 batch-cleared 摘要，但太子不会主动合成奏报——父皇需先发言才能触发。

## 架构

```
看板清空
  ↓ ≤5min
coordinator poll 检测 → 写 final-results JSON + kanban-clearance-trigger
  ↓ ≤2min
kanban-clearance-reporter cron (agent mode, kimi-k2.6)
  ├─ 检测 trigger 文件
  ├─ 存在 → 删除 trigger + 查板 + 合成奏报 + send_message → Telegram
  └─ 不存在 → 静默退出（零 LLM 成本）
```

## 组件

| 组件 | 频率 | 类型 | 作用 |
|------|------|------|------|
| kanban-watchdog | 1min | 纯脚本 | 状态感知 + Delivery Bridge |
| kanban-coordinator-poll | 5min | 纯脚本 + agent 子进程 | 自动恢复 + 批次清空检测 + trigger |
| kanban-clearance-reporter | 2min | agent mode | 读取 trigger → 主动奏报 |

## 关键约束

- clearance-reporter 只跑 2-3 轮迭代，0.2-0.3 USD 预算
- trigger 文件确保 LLM 只在清空时跑（月均十几次）
- clearance-check 脚本用绝对路径规避 sandbox HOME 重定向
- reporter 用 `deliver=local`，通过 send_message 主动推送

## 部署检查

```bash
# cron 健康
hermes cron list | grep -E 'kanban|clearance'
# trigger 机制测试：手动 touch → 等 2min → 查 Telegram
touch ~/.hermes/profiles/regent/state/kanban-clearance-trigger
```
