# /usage 用量汇报模式

> 2026-06-16 发现。CC 无法自己执行 `/usage`——它是 CLI 内置交互命令，不是 tool 也不是 shell 命令。

## 根因

`/usage` 是 CC 的 CLI 内置 slash 命令，只能在交互式 TUI 中由用户手敲。CC agent 的 Bash/任何工具都无法执行它。执行后进入全屏 TUI 面板，CC 不会自己退出（→ Pitfall #10）。

## 三种方案

| 方案 | CC 能自理？ | 有剩余额度？ | 成本 |
|------|:--:|:--:|------|
| 1. 用户敲 /usage，CC 读屏汇报 | ❌（依赖用户） | ✅ | 用户每次配合 |
| 2. `npx ccusage` 估算 | ✅ | ❌（只有消耗） | 首次下载慢，对 452M transcript 慢 |
| 3. 两者结合 | ✅（自动）+ 用户补 | ✅ | 推荐 |

## 方案 3 实现（推荐）

### CC 侧

每次任务边界（子任务开始/结束）：
```bash
# 估算消耗（npx ccusage 基于本地 transcript）
# schema 校正：顶层仅 {daily, totals}，token/cost 在 .totals 下（2026-06-22 cc-usage.sh 落地时实测核实，旧写法 .totalTokens 为空）
npx ccusage --json 2>/dev/null | jq '{tokens: .totals.totalTokens, cost: .totals.totalCost}' 2>/dev/null || echo '{"status":"ccusage not available"}'

# P0-2 已封装为脚本：scripts/cc-usage.sh --mode pre|post（自带可移植 timeout + 基线 delta + 降级）
```

然后在会话中汇报："📊 本阶段消耗估算: XXk tokens · 请方便时敲 /usage 补真实额度"

### Hermes 侧

每次 `cc-monitor.sh` 跑完后，如果看到 CC 提示 "请敲 /usage"，即转发给用户。

### 已知限制

- `npx ccusage` 首次需从 npm 下载（~几秒），后续用缓存
- 大 transcript（本 session 的 452M `.jsonl`）解析慢，首跑可能 30-60s
- 没有剩余额度——只有 Anthropic 服务端知道订阅限额
- `~/.claude/` 下没有可直接读的订阅额度文件（2026-06-16 实测确认）

## 降级

若 `npx ccusage` 不可用：
- CC 在任务边界从 transcript JSONL 自己估算（读最近消息的 token count 字段累加）
- 精度较低但零依赖
- 每次都提示用户敲 `/usage` 补真实值
