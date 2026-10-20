#!/usr/bin/env bash
# cc-start.sh — Claude Code tmux session starter with occupancy lock + session scan.
# Usage: cc-start.sh --target <name> --effort <high|xhigh|max> --task <desc>
#                    [--model <model>] [--agent <name>] [--ack-active]
# Output: session name on stdout (e.g., "hermes-cc-default-jz-skills-0615-2130")
#
# Exit codes:
#   0  started OK
#   1  usage / environment error
#   2  BUSY  — this target's lock is held by a LIVE session (genuine collision)
#   3  OTHER active CC session(s) detected — relay report to user, re-run with
#      --ack-active once the user confirms it's safe to start alongside them
#
# v1.3: before claiming the lock we (a) scan ALL tmux sessions for live CC
# sessions and report active ones, and (b) auto-clean a zombie lock whose
# recorded session is dead (force-killed CC no longer wedges the target).

set -euo pipefail
source "$(dirname "$0")/lib/portability.sh"

# ── Parse args ──────────────────────────────────────────────
TARGET="" EFFORT="high" TASK="" MODEL="claude-opus-4-8" AGENT="default" ACK_ACTIVE=false TOPIC=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --effort) EFFORT="$2"; shift 2 ;;
    --task)   TASK="$2"; shift 2 ;;
    --model)  MODEL="$2"; shift 2 ;;
    --agent)  AGENT="$2"; shift 2 ;;
    --topic)  TOPIC="$2"; shift 2 ;;   # R9b: 若提供，启动前查 topic→session 映射尝试复用
    --ack-active) ACK_ACTIVE=true; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# R9b: all tmux calls go through tmuxc so CC_TOPIC_TMUX can inject a stub for hermetic
# tests (default = real tmux → zero behavior change). Same pattern as cc-gc's CC_GC_TMUX.
# shellcheck disable=SC2086
tmuxc() { ${CC_TOPIC_TMUX:-tmux} "$@"; }

if [[ -z "$TARGET" || -z "$TASK" ]]; then
  echo "Usage: cc-start.sh --target <name> --task <desc> [--effort high|xhigh|max] [--model ...] [--agent ...] [--ack-active]" >&2
  exit 1
fi
case "$EFFORT" in
  high|xhigh|max) ;;
  *) echo "Invalid effort: $EFFORT (must be high, xhigh, or max)" >&2; exit 1 ;;
esac

# ── Validate --target chars (reject spaces and special chars that break lock/session names)
if [[ "$TARGET" != "${TARGET//[^a-zA-Z0-9._-]/}" ]]; then
  echo "❌ Invalid --target: '$TARGET' — contains characters outside [a-zA-Z0-9._-]. Use hyphens/underscores/dots only." >&2
  exit 1
fi

# ── §3.8 #7: HERMES_HOME / HOME redirection self-check ────────
# Pure read-only, runs BEFORE any lock/scan. Turns a mysterious runtime failure
# (HOME redirected by a profile → skill scripts unfindable) into an explicit
# startup diagnosis. SKILL_ROOT is env-overridable only for test injection.
SKILL_ROOT="${CC_TMUX_SKILL_ROOT:-/Users/$(id -un)/.hermes/skills/autonomous-ai-agents/cc-tmux}"
if [[ ! -d "$SKILL_ROOT/scripts" ]]; then
  echo "❌ 找不到 $SKILL_ROOT/scripts — 可能 HERMES_HOME/HOME 被 profile 重定向" >&2
  echo "   检查: echo \$HOME; echo \${HERMES_HOME}。修法: 绝对路径调用，或命令前加 HOME=/Users/$(id -un)" >&2
  exit 1
fi

TSLUG=$(echo "$TARGET" | tr '/' '-')
USER_HOME=$(eval echo ~$(id -un))
LOCKDIR="/tmp/cc-lock-${TARGET}"

# ── Classify a session's CC state from its pane ──────────────
classify() {
  local s="$1" pane last3 prompt content
  pane=$(tmuxc capture-pane -t "$s" -p -S -20 2>/dev/null || echo "")
  [[ -z "$pane" ]] && { echo "EMPTY"; return; }
  if printf '%s' "$pane" | grep -qE 'Waiting for [0-9]+ background agent'; then echo "WAITING_AGENTS"; return; fi
  last3=$(printf '%s\n' "$pane" | grep -v '^[[:space:]]*$' | tail -3)
  prompt=$(printf '%s\n' "$last3" | grep '❯' | tail -1 || true)
  if [[ -n "$prompt" ]]; then
    content=$(printf '%s' "$prompt" | sed -E 's/^[[:space:]│╎┃|]*❯[[:space:]]*//; s/[[:space:]│╎┃|]*$//')
    [[ -z "$content" ]] && { echo "IDLE"; return; }
  fi
  if printf '%s' "$pane" | grep -qE '⏺|●'; then echo "TOOL"; return; fi
  if printf '%s' "$pane" | grep -qE '[✻✳✶✢✽]'; then echo "THINKING"; return; fi
  if printf '%s' "$pane" | grep -q 'bypass permissions on'; then echo "IDLE"; return; fi
  echo "UNKNOWN"
}
is_cc_session() { # name matches hermes-cc-* OR pane shows the bypass banner
  local s="$1"
  [[ "$s" == hermes-cc-* ]] && return 0
  tmuxc capture-pane -t "$s" -p -S -20 2>/dev/null | grep -q 'bypass permissions on'
}

# ── R9b: --topic 复用（查 topic→session 映射，可复用则短路，绕过新建+锁）──
# 子进程 cc-topic-map.sh 自动继承 CC_TOPIC_MAP_FILE / CC_TOPIC_TMUX 环境变量（hermetic）。
TOPIC_MAP="$SKILL_ROOT/scripts/cc-topic-map.sh"
if [[ -n "$TOPIC" ]]; then
  MAPPED=$(bash "$TOPIC_MAP" get "$TOPIC" 2>/dev/null || echo "")
  if [[ -n "$MAPPED" ]]; then
    if tmuxc has-session -t "$MAPPED" 2>/dev/null; then
      RST=$(classify "$MAPPED")
      # P1-1 cc-status 权威覆盖：COMPLETED/IDLE 视为可复用空闲态
      SF="/tmp/cc-status-${MAPPED}.json"
      if [[ -f "$SF" ]] && command -v jq >/dev/null 2>&1; then
        CST=$(jq -r '.state // ""' "$SF" 2>/dev/null || echo "")
        [[ "$CST" == "COMPLETED" || "$CST" == "IDLE" ]] && RST="IDLE"
      fi
      # 心跳新鲜度（默认 2h，与 R9d IDLE>2h 对齐）
      HBF="/tmp/cc-heartbeat-${MAPPED}"; FRESH=false; HBAGE=999999
      if [[ -f "$HBF" ]]; then
        HBAGE=$(( $(date +%s) - $(get_mtime "$HBF") ))
        [[ "$HBAGE" -lt "${CC_TOPIC_FRESH_S:-7200}" ]] && FRESH=true
      fi
      if [[ "$RST" == "IDLE" && "$FRESH" == true ]]; then
        echo "♻️  R9b 复用 topic=$TOPIC 的 session: ${MAPPED}（state=IDLE，心跳新鲜 ${HBAGE}s）" >&2
        echo "$MAPPED"   # stdout: 复用 session 名，对调用方透明
        exit 0
      fi
      echo "ℹ️  R9b topic=$TOPIC 的 session $MAPPED 状态=$RST / 心跳陈旧 → 不复用，新建（不打断旧 session）" >&2
      # 落到下方新建流程；映射在新建成功后覆盖
    else
      echo "🧹 R9b topic=$TOPIC 映射的 session $MAPPED 已死 → unset，新建" >&2
      bash "$TOPIC_MAP" unset "$TOPIC" 2>/dev/null || true
    fi
  fi
fi

# ── Scan ALL tmux sessions for live CC sessions ──────────────
ALL_SESSIONS=$(tmuxc list-sessions -F '#{session_name}' 2>/dev/null || true)
OTHERS_REPORT=""; OTHERS_ACTIVE=0
if [[ -n "$ALL_SESSIONS" ]]; then
  while IFS= read -r s; do
    [[ -z "$s" ]] && continue
    is_cc_session "$s" || continue
    # skip sessions belonging to THIS target — the lock governs those
    [[ "$s" == *"-${TSLUG}-"* ]] && continue
    st=$(classify "$s")
    OTHERS_REPORT="${OTHERS_REPORT}  · ${s} — ${st}"$'\n'
    case "$st" in TOOL|THINKING|WAITING_AGENTS) OTHERS_ACTIVE=$((OTHERS_ACTIVE + 1)) ;; esac
  done <<< "$ALL_SESSIONS"
fi

# ── Handle THIS target's lock: BUSY vs zombie ────────────────
if [[ -d "$LOCKDIR" ]]; then
  LSESS=$(cat "$LOCKDIR/session" 2>/dev/null || echo "")
  if [[ -n "$LSESS" ]] && tmuxc has-session -t "$LSESS" 2>/dev/null; then
    LST=$(classify "$LSESS")
    echo "⛔ BUSY: target '$TARGET' 被存活 session 占用" >&2
    echo "⛔   session=$LSESS  state=$LST  lock=$LOCKDIR" >&2
    echo "⛔   → 等它结束，或换 --target / cc-finish 那个 session 后再起" >&2
    exit 2
  else
    echo "🧹 清理僵尸锁: ${LOCKDIR}（记录的 session '${LSESS:-?}' 已不存在）" >&2
    rm -rf "$LOCKDIR"
  fi
fi

# ── Soft gate: other active CC sessions need user ack ────────
if [[ "$OTHERS_ACTIVE" -gt 0 && "$ACK_ACTIVE" != true ]]; then
  echo "===📋 BEGIN cc-start 扫描报告 (relay verbatim)==="
  echo "⚠️  检测到 ${OTHERS_ACTIVE} 个活跃的其它 CC session（非本 target '${TARGET}'）："
  printf '%s' "$OTHERS_REPORT"
  echo "  → 这些 CC 正在干活。确认可并行启动? 让用户确认后重跑并加 --ack-active；"
  echo "    否则先 cc-finish 收尾上一个再起。"
  echo "  📋 可粘贴: cc-start.sh --target $TARGET --effort $EFFORT --agent $AGENT --task '<原任务>' --ack-active"
  echo "===📋 END==="
  exit 3
fi

# ── Verify claude binary ────────────────────────────────────
if ! command -v claude &>/dev/null; then
  echo "❌ claude not found in PATH" >&2
  exit 1
fi

# ── Claim lock atomically (mkdir) ────────────────────────────
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  # Raced between zombie-clean and now, or a live holder appeared
  LSESS=$(cat "$LOCKDIR/session" 2>/dev/null || echo "?")
  echo "⛔ BUSY: target '$TARGET' 锁刚被抢占 (session=$LSESS)" >&2
  exit 2
fi

# ── Session naming (includes target to prevent parallel collision) ──
TS=$(date +%m%d-%H%M)
SESSION="hermes-cc-${AGENT}-${TSLUG}-${TS}"
# Guard against same-minute same-agent same-target collision
if tmuxc has-session -t "$SESSION" 2>/dev/null; then
  SESSION="${SESSION}-$$"
fi

# ── Start tmux session ───────────────────────────────────────
if ! HOME="$USER_HOME" tmuxc new-session -d -s "$SESSION" -c /tmp 2>/dev/null; then
  echo "❌ tmuxc new-session 失败: $SESSION" >&2
  rm -rf "$LOCKDIR"   # roll back the lock so the target isn't wedged
  exit 1
fi

# Record lock metadata (bidirectional ref + STALE detection inputs)
echo "$$" > "$LOCKDIR/script_pid"
echo "$(date -u +%Y-%m-%dT%H:%M:%S)" > "$LOCKDIR/created"
echo "$SESSION" > "$LOCKDIR/session"
TMUX_PID=$(tmuxc display-message -t "$SESSION" -p '#{pid}' 2>/dev/null || echo "?")
echo "$TMUX_PID" > "$LOCKDIR/tmux_pid"

# R9b: 新建成功 → 写/覆盖 topic→session 映射（下次同 topic 任务可复用本 session）
if [[ -n "$TOPIC" ]]; then
  bash "$TOPIC_MAP" set "$TOPIC" "$SESSION" 2>/dev/null || true
fi

# Send the claude command.
# §D-4: inject CC_TMUX_SESSION=<tmux session name> into the launched claude's env so
# the in-CC hooks key per-session state (cc-output/, cc-state log, expect, rewake
# counter) by the SAME tmux name that cc-monitor/cc-send/cc-finish use — unifying the
# state bus and letting cc-finish clean everything. Absent it, hooks degrade to the
# CC UUID (no regression). `VAR=val claude …` sets the launched process environment.
#
# §Phase-1 (2026-06-17) deployment auto-sync: instead of pre-merging hooks into the
# global ~/.claude/settings.json (manual cp+jq, needs restart, fires for EVERY CC,
# and R1-verified to DOUBLE-FIRE alongside --settings), inject the skill's own hook
# config at launch via `--settings <runtime template>` and export CC_TMUX_HOOK_DIR so
# the template's script-path hooks self-locate in the skill dir. Net effect: the skill
# is the single source of truth, every fresh CC auto-picks the latest hooks, zero
# cp/jq/restart. R2 verified $CC_TMUX_HOOK_DIR expands in the hook shell at fire time.
HOOKDIR="$SKILL_ROOT/hooks"
RUNTIME_SETTINGS="$SKILL_ROOT/templates/settings.runtime.json"
tmuxc send-keys -t "$SESSION" \
  "HOME=\"$USER_HOME\" CC_TMUX_SESSION=\"$SESSION\" CC_TMUX_HOOK_DIR=\"$HOOKDIR\" CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY=1 claude --allow-dangerously-skip-permissions --model ${MODEL} --effort ${EFFORT} --settings \"$RUNTIME_SETTINGS\"" Enter

# ── §Phase-2: launch the resident watcher daemon ─────────────
# The ONE deterministic poller. It refreshes nothing itself — it only probes
# (cc-monitor --force-capture) when the hook-driven heartbeat goes stale, to tell a long
# think from a freeze (the one signal no hook can read). This moves the monitoring
# cadence OFF the LLM onto a守时 shell loop. It self-retires when the session dies;
# cc-finish --kill-session also kills it via the PID recorded here. nohup so it outlives
# this cc-start process. Failure to spawn must NOT break startup (best-effort).
nohup bash "$SKILL_ROOT/scripts/cc-watcher.sh" --watch "$SESSION" \
      >"/tmp/cc-watch-${SESSION}.log" 2>&1 &
echo "$!" > "$LOCKDIR/watcher_pid" 2>/dev/null || true

# ── Output session info ─────────────────────────────────────
echo "$SESSION"   # stdout: session name for consumption by other scripts

# Lock is intentionally NOT released here — it tracks the tmux session lifecycle;
# only cc-finish.sh --release-lock releases it (or cc-start auto-cleans it as a
# zombie next time if the session has died).
