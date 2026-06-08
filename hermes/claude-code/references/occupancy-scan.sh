#!/usr/bin/env bash
# occupancy-scan.sh — CC 占用检测（每次调 CC 前必须执行）
# 从 SKILL.md § Multi-Agent Coordination Protocol 下沉（v4.1.2 slim）。唯一权威脚本。
#
# 用法: bash references/occupancy-scan.sh
# 输出: 每个 tmux session 的 BUSY / THINKING / IDLE 状态
#   ⚠️ BUSY     有 ● 活跃工具调用 — CC 正在工作
#   🧠 THINKING 有 ✻/✶/✽/✳ 思考态 — CC 深度思考旧任务，不可打扰
#   ✅ IDLE     底部 ❯ — CC 等待输入（仍默认新建独立 session，不复用）
#
# 决策: 有 ● 或 ✻ → 必须汇报用户后等确认；全空闲 / 用户确认 → 新建 hermes-cc-{agent}-{ts}

for s in $(tmux list-sessions -F '#{session_name}' 2>/dev/null); do
  pane=$(tmux capture-pane -t "$s" -p -S -8 2>/dev/null)

  # 检测 ● 活跃工具调用（CC 正在工作）
  if echo "$pane" | grep -q '●'; then
    tool=$(echo "$pane" | grep '●' | tail -1 | sed 's/.*● //' | head -c 60)
    echo "⚠️ BUSY: $s — $tool"
  fi

  # 检测 ✻/✶/✽/✳ 思考状态（CC 深度思考中，不是空闲）
  if echo "$pane" | grep -qE '✻|✶|✽|✳|Sublimating|Zigzagging|Billowing|Crunched|Wandering|Swooping|Cooking'; then
    echo "🧠 THINKING: $s — CC 在深度思考旧任务，不可打扰"
  fi

  # 检测 ❯ 空闲（CC 等待输入）
  if echo "$pane" | tail -1 | grep -q '❯'; then
    echo "✅ IDLE: $s — CC 空闲，可复用"
  fi
done
