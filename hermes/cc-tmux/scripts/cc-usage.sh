#!/usr/bin/env bash
# cc-usage.sh — CC 用量管理（PRD R8c）：任务前后查用量、算本轮消耗、提醒敲 /usage
#
# Usage:
#   cc-usage.sh --mode pre  --task "<简述>" [--effort high|medium|low] [--session <s>]
#   cc-usage.sh --mode post [--session <s>]
#
# pre  → 跑 ccusage 取当前累计 totals，写基线 /tmp/cc-usage-baseline-<session>.json，提醒 /usage
# post → 跑 ccusage 取当前 totals，读基线算 delta（本轮近似消耗），清基线，提醒 /usage
#
# 设计边界（references/usage-reporting-pattern.md 方案 3）：
#   · ccusage 只有「累计消耗」，没有「剩余额度」——只有 Anthropic 服务端知道。
#     故本脚本【不伪造】剩余/预测数字，只报实测累计/delta + 始终提醒用户敲 /usage。
#   · 不代用户做暂停决策——只提醒。
#   · ccusage 不可用/超时/非 JSON → 降级文案 + exit 0（绝不打断任务流）；pre 仍写最小基线。
#
# 可移植性 / 可测性：
#   · macOS 无 `timeout`（只有可选 gtimeout）——内置 run_bounded() 三级回退，脚本不依赖 timeout。
#   · CC_USAGE_CMD 覆盖 ccusage 调用（默认 "npx --yes ccusage@latest"）；测试注入 stub → 零网络。
#   · CC_USAGE_TIMEOUT_S 调用上限（默认 90s）。
#
# 机器断言行（stderr，非给用户 relay）：
#   USAGE_META mode=.. session=.. ccusage_ok=.. [baseline=found|missing] [deltaTokens=.. deltaCost=..]

set -euo pipefail

MODE="" TASK="" EFFORT="" SESSION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)    [[ $# -ge 2 ]] || { echo "❌ cc-usage: --mode requires a value" >&2; exit 2; }; MODE="$2"; shift 2 ;;
    --task)    [[ $# -ge 2 ]] || { echo "❌ cc-usage: --task requires a value" >&2; exit 2; }; TASK="$2"; shift 2 ;;
    --effort)  [[ $# -ge 2 ]] || { echo "❌ cc-usage: --effort requires a value" >&2; exit 2; }; EFFORT="$2"; shift 2 ;;
    --session) [[ $# -ge 2 ]] || { echo "❌ cc-usage: --session requires a value" >&2; exit 2; }; SESSION="$2"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0" >&2; exit 0 ;;
    *) echo "❌ cc-usage: unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ "$MODE" != "pre" && "$MODE" != "post" ]]; then
  echo "❌ cc-usage: --mode must be 'pre' or 'post' (got: '${MODE:-}')" >&2
  exit 2
fi

SESSION="${SESSION:-${CC_TMUX_SESSION:-default}}"   # D-4 键统一：默认随 CC_TMUX_SESSION
BASELINE="/tmp/cc-usage-baseline-${SESSION}.json"
CC_USAGE_CMD="${CC_USAGE_CMD:-npx --yes ccusage@latest}"
BOUND="${CC_USAGE_TIMEOUT_S:-90}"
ISO=$(date -u +%Y-%m-%dT%H:%M:%S)

# ── run_bounded <secs> <cmd...> — 可移植有界执行（macOS 无 timeout 时三级回退）──
run_bounded() {
  local secs="$1"; shift
  if command -v gtimeout >/dev/null 2>&1; then gtimeout "$secs" "$@"; return $?; fi
  if command -v timeout  >/dev/null 2>&1; then timeout  "$secs" "$@"; return $?; fi
  # 纯 bash 回退：后台跑 + 轮询 + 超时 kill
  local tmpf pid i=0 rc
  tmpf=$(mktemp)
  "$@" >"$tmpf" 2>/dev/null &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    if [[ "$i" -ge "$secs" ]]; then
      kill -TERM "$pid" 2>/dev/null || true; sleep 1; kill -KILL "$pid" 2>/dev/null || true
      cat "$tmpf"; rm -f "$tmpf"; return 124
    fi
    sleep 1; i=$((i+1))
  done
  wait "$pid" 2>/dev/null; rc=$?
  cat "$tmpf"; rm -f "$tmpf"; return "$rc"
}

# ── fetch_usage — 跑 ccusage，解析 .totals.{totalTokens,totalCost}；任何失败 → OK=false ──
# 设置全局 USAGE_OK / USAGE_TOK / USAGE_COST
fetch_usage() {
  local out tok cost
  # shellcheck disable=SC2086  # CC_USAGE_CMD 需词分割（"npx --yes ccusage@latest"）
  out=$(run_bounded "$BOUND" $CC_USAGE_CMD --json 2>/dev/null) || true
  if tok=$(printf '%s' "$out"  | jq -er '.totals.totalTokens' 2>/dev/null) \
     && cost=$(printf '%s' "$out" | jq -er '.totals.totalCost' 2>/dev/null) \
     && [[ "$tok" =~ ^[0-9]+$ ]]; then
    USAGE_OK=true;  USAGE_TOK="$tok";  USAGE_COST="$cost"
  else
    USAGE_OK=false; USAGE_TOK=0;       USAGE_COST=0
  fi
}

# humanize a raw token count: 12.3k / 4.5M / 5.4B (累计常达十亿级)
humik() { awk -v n="$1" 'BEGIN{
  if(n+0>=1e9) printf "%.1fB", n/1e9;
  else if(n+0>=1e6) printf "%.1fM", n/1e6;
  else if(n+0>=1000) printf "%.1fk", n/1000;
  else printf "%d", n }'; }

# 预计算可选后缀（避免 ${VAR:+…} 内嵌全角括号在 set -u 下的多字节解析坑）
TASK_SFX="";   [[ -n "$TASK" ]]   && TASK_SFX="（${TASK}）"          || true
EFFORT_SFX=""; [[ -n "$EFFORT" ]] && EFFORT_SFX=" · effort=${EFFORT}" || true

# ════════════════════════════════════════════════════════════════════════════
fetch_usage

if [[ "$MODE" == "pre" ]]; then
  # 写基线（jq -n 安全构造，task 字符串自动转义；ccusage 挂了也写最小基线供 post 不崩）
  jq -n \
    --arg session "$SESSION" --arg ts "$ISO" --arg task "$TASK" --arg effort "$EFFORT" \
    --argjson tok "${USAGE_TOK:-0}" --argjson cost "${USAGE_COST:-0}" --argjson ok "$USAGE_OK" \
    '{session:$session, ts:$ts, mode:"pre", task:$task, effort:$effort,
      totalTokens:$tok, totalCost:$cost, ccusage_ok:$ok}' > "$BASELINE"

  echo "USAGE_META mode=pre session=$SESSION ccusage_ok=$USAGE_OK totalTokens=$USAGE_TOK totalCost=$USAGE_COST baseline=$BASELINE" >&2

  echo "===📡 BEGIN (relay verbatim)==="
  echo "📊 用量·任务前${TASK_SFX}${EFFORT_SFX}"
  if [[ "$USAGE_OK" == true ]]; then
    echo "  · 当前累计（ccusage 估算）: $(humik "$USAGE_TOK") tokens · \$$(printf '%.2f' "$USAGE_COST")"
  else
    echo "  · ⚠️ ccusage 暂不可用（超时/未安装/输出异常）——本轮消耗将无法估算"
  fi
  echo "  · ℹ️ ccusage 只有累计消耗、没有剩余额度 → 请方便时敲 /usage 取真实剩余"
  echo "===📡 END==="
  exit 0
fi

# ── post ──
if [[ -s "$BASELINE" ]] && jq -e . "$BASELINE" >/dev/null 2>&1; then
  PREV_TOK=$(jq -er '.totalTokens' "$BASELINE" 2>/dev/null || echo 0)
  PREV_COST=$(jq -er '.totalCost'  "$BASELINE" 2>/dev/null || echo 0)
  PREV_OK=$(jq -er '.ccusage_ok'   "$BASELINE" 2>/dev/null || echo false)
  PREV_TASK=$(jq -er '.task // ""'  "$BASELINE" 2>/dev/null || echo "")
  [[ "$PREV_TOK" =~ ^[0-9]+$ ]] || PREV_TOK=0
  PREV_TASK_SFX=""; [[ -n "$PREV_TASK" ]] && PREV_TASK_SFX="（${PREV_TASK}）" || true

  if [[ "$USAGE_OK" == true && "$PREV_OK" == true ]]; then
    DELTA_TOK=$((USAGE_TOK - PREV_TOK)); [[ "$DELTA_TOK" -lt 0 ]] && DELTA_TOK=0
    DELTA_COST=$(awk -v a="$USAGE_COST" -v b="$PREV_COST" 'BEGIN{d=a-b; if(d<0)d=0; printf "%.4f", d}')
    echo "USAGE_META mode=post session=$SESSION ccusage_ok=true baseline=found deltaTokens=$DELTA_TOK deltaCost=$DELTA_COST" >&2
    echo "===📡 BEGIN (relay verbatim)==="
    echo "📊 用量·任务后${PREV_TASK_SFX}"
    echo "  · 本轮消耗（近似，期间若有并行 CC 活动会偏高）: $(humik "$DELTA_TOK") tokens · \$$(printf '%.4f' "$DELTA_COST")"
    echo "  · 累计: $(humik "$USAGE_TOK") tokens · \$$(printf '%.2f' "$USAGE_COST")"
    echo "  · ℹ️ 剩余额度请敲 /usage 确认（ccusage 无此数据）"
    echo "===📡 END==="
  else
    # ccusage 本轮或基线侧不可用 → 报不出 delta，降级
    echo "USAGE_META mode=post session=$SESSION ccusage_ok=$USAGE_OK baseline=found deltaTokens=NA deltaCost=NA" >&2
    echo "===📡 BEGIN (relay verbatim)==="
    echo "📊 用量·任务后${PREV_TASK_SFX}"
    echo "  · ⚠️ ccusage 不可用（本轮或任务前）→ 无法算本轮 delta"
    echo "  · ℹ️ 请敲 /usage 看真实用量"
    echo "===📡 END==="
  fi
  rm -f "$BASELINE"
else
  # 无基线（pre 没跑过 / 文件损坏）→ 优雅降级
  echo "USAGE_META mode=post session=$SESSION ccusage_ok=$USAGE_OK baseline=missing deltaTokens=NA deltaCost=NA" >&2
  echo "===📡 BEGIN (relay verbatim)==="
  echo "📊 用量·任务后"
  echo "  · ⚠️ 没找到任务前基线（/tmp/cc-usage-baseline-${SESSION}.json）→ 无法算本轮 delta"
  if [[ "$USAGE_OK" == true ]]; then
    echo "  · 当前累计: $(humik "$USAGE_TOK") tokens · \$$(printf '%.2f' "$USAGE_COST")"
  fi
  echo "  · ℹ️ 下次任务前先跑 --mode pre 建基线；剩余额度敲 /usage"
  echo "===📡 END==="
fi
exit 0
