# Sonnet high effort 启动失败

## 问题

Sonnet 模型（claude-sonnet-4-5-20250929）配 `--effort high` 启动后 pane 空白，任务不消费。

## 根因

Sonnet 不支持 `--effort high`（或该参数与 Sonnet 4.5 不兼容），导致初始化异常进入不可交互状态。

## 症状

- `cc-start.sh` exit 0（tmux session 创建成功）
- pane 几乎空白，只有 ❯ 提示符
- 无 CC spinner 或启动输出
- `cc-send.sh` 发送的任务不被消费

## 解决方案

**模型-effort 兼容性矩阵**：

| 模型 | effort 支持 | 推荐配置 |
|------|-------------|----------|
| Opus (claude-opus-4-8) | ✅ high/xhigh/max | 默认 high |
| Sonnet (claude-sonnet-4-5) | ❌ high | medium 或不传 |

**修复步骤**：
1. kill session
2. 换 Opus 或调 effort 重试

## 预防

- R8b 决策指南补充模型-effort 兼容性
- `cc-start.sh` 后必抓屏确认 spinner 出现，不只是 exit 0
