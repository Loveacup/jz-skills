# 📡 Relay Contract — cc-tmux v1.3

## 问题

v1.2 及之前，Hermes agent 在监控 CC 时经常：
- 跳过某些 monitor 运行（"没变化不用报"）
- 总结/合并多轮 📡 输出（"攒几轮一起报"）
- 改格式（自由发挥，不用模板）
- 不按 30-60s 节奏（"CC 在思考，没什么可报"）

根因：监控合规完全依赖 prose 建议，没有机械牙齿。

## 解决方案

v1.3 引入三层机械强制执行：

### 层 1：输出格式锁定

`cc-monitor.sh` stdout 被 `===📡 BEGIN (relay verbatim)===` 和 `===📡 END===` 包裹。Hermes agent 的职责简化为：

> **原样转发两个标记之间的内容到用户可见的 📡 块。不思考、不判断、不加工。**

机器元数据（`META session=...`）去 stderr，不污染 stdout。所以 "relay all of stdout" 永远是正确的。

### 层 2：心跳文件

每次 `cc-monitor.sh` 运行 → 写入 `/tmp/cc-heartbeat-<session>`：
```
EPOCH|RUNCOUNT|STATE|TOKENS|TOKCHG_EPOCH|SEQ
```

这是不可否认的审计记录。跳过一次 monitor = 心跳间隙 = `cc-finish.sh` 能检测到。

### 层 3：Hard Gate

`cc-finish.sh` 收尾时检查心跳新鲜度：
- 心跳 >120s 陈旧 → reject（exit 2），锁不释放、session 不杀
- 从未有心跳 → reject
- 只有 `--force` 能覆盖（但不能覆盖 ❯ 残留 gate）

## 反模式（禁止行为）

| ❌ 反模式 | ✅ 正确做法 |
|-----------|-----------|
| 跑 `cc-monitor.sh` 后不发 📡 | 必须原样转发 stdout |
| "CC 在思考，没什么可报" | 空闲也得报 "💤 idle" |
| 合并 2-3 轮一起报 | 每次 monitor 跑完立即转发 |
| 自由格式总结 | 只转发 `===📡 BEGIN===` 和 `===📡 END===` 之间的内容 |
| 把 stderr 的 META 行也 relay | META 行去 stderr，不是给用户的 |

## 审计输出

`cc-finish.sh --session <s> --target <t>` 输出：
```
📊 监控记录: 10 次抓屏 · 3 次状态转移 · 最大间隙 71s
   状态序列: NONE→TOOL
✓ 监控新鲜: 距最后一次 cc-monitor 12s（最后状态=TOOL, 共 10 次）
```

若存在间隙：
```
⚠️ 监控间隙: 距最后一次 cc-monitor 245s（>120s），最后状态=THINKING
⛔ 拒绝收尾：监控未达标。补跑一次 cc-monitor 再收尾，或加 --force 覆盖。
```

## 设计原则

遵循 cc-tmux 核心原则：**脚本做 gate，LLM 做决策。**
- 脚本判定"是否合规"（心跳新鲜度、状态转移次数）
- LLM 判定"怎么做"（如何 relay、何时补跑 monitor）
