#!/usr/bin/env bash
# cccmux 占用检测 — 读 cmux 的 hook lifecycle 元数据,而非 grep tmux 屏上的 emoji。
# 唯一权威脚本。输出每个 CC 会话的 workspace / surface / cwd / lifecycle / pid。
#
# 与 tmux 版的区别:tmux 版靠 capture-pane 抓 ●/✻/❯ 文本启发式判忙闲;
# cmux 把每个 CC 会话的生命周期结构化落盘在 ~/.cmuxterm/claude-hook-sessions.json,
# 直接读 agentLifecycle 字段即可,准确且不打断会话。
#
# lifecycle 取值(实测):running(忙) / idle(空闲) / needsInput(等决策点) / unknown
# fail-open:文件缺失或解析失败 → 打印告警但 exit 0,不 block。

set -uo pipefail
HOOK_FILE="${CMUX_HOOK_SESSIONS:-$HOME/.cmuxterm/claude-hook-sessions.json}"

if [[ ! -f "$HOOK_FILE" ]]; then
  echo "⚠️ 找不到 $HOOK_FILE — cmux 未在跑或无 CC 会话。视为「无占用」,可新建。"
  exit 0
fi

python3 - "$HOOK_FILE" <<'PY' 2>/dev/null || { echo "⚠️ 解析 hook 文件失败 — fail-open,视为无占用。"; exit 0; }
import json, sys, time
f = sys.argv[1]
with open(f) as fp:
    d = json.load(fp)
sessions = d.get("sessions", {})
active = d.get("activeSessionsByWorkspace", {})
active_ids = {v.get("sessionId") for v in active.values() if isinstance(v, dict)}

busy = thinking = idle = 0
rows = []
now = time.time()
for sid, s in sessions.items():
    if not isinstance(s, dict):
        continue
    life = s.get("agentLifecycle", "unknown")
    cwd  = s.get("cwd", "?")
    ws   = s.get("workspaceId", "?")
    surf = s.get("surfaceId", "?")
    pid  = s.get("pid", "?")
    upd  = s.get("updatedAt", 0) or 0
    age  = int(now - upd) if upd else -1
    mark = "🟢ACTIVE" if sid in active_ids else "       "
    if life == "running":      busy += 1
    elif life == "needsInput": thinking += 1
    elif life == "idle":       idle += 1
    rows.append((life, mark, sid[:8], pid, ws[:8], surf[:8], age, cwd))

# 忙碌/等输入的排前面
order = {"running": 0, "needsInput": 1, "idle": 2, "unknown": 3}
rows.sort(key=lambda r: order.get(r[0], 9))

print(f"{'LIFECYCLE':<11}{'':<8}{'session':<9}{'pid':<7}{'ws':<9}{'surface':<9}{'age(s)':<8}cwd")
for life, mark, sid, pid, ws, surf, age, cwd in rows:
    icon = {"running":"🔴","needsInput":"🟡","idle":"💤","unknown":"⚪"}.get(life,"⚪")
    print(f"{icon} {life:<9}{mark} {sid:<9}{str(pid):<7}{ws:<9}{surf:<9}{str(age):<8}{cwd}")

print()
if busy or thinking:
    print(f"⛔ 有占用:{busy} 个 running、{thinking} 个 needsInput → 先汇报用户再决定等待/新建独立 workspace。")
    sys.exit(0)  # 仍 exit 0;由调用方据输出决策,脚本只做检测不 block
else:
    print(f"✅ 无 running/needsInput(idle={idle}) → 可新建独立 workspace 启动新 team。")
PY
exit 0
