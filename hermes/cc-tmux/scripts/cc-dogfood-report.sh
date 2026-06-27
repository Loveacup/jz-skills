#!/usr/bin/env bash
set -euo pipefail

# cc-dogfood-report.sh — Read /tmp/cc-dogfood.jsonl, generate a friction summary
#                        when unreported records >= threshold (default 5).
#
# Usage:
#   cc-dogfood-report.sh                 # stdout: summary if >= 5 new records, else silent
#   cc-dogfood-report.sh --threshold N   # override threshold
#   cc-dogfood-report.sh --force         # generate even if < threshold
#   cc-dogfood-report.sh --reset         # mark all current records as reported (no summary)
#
# Paths are env-overridable (default to /tmp) so tests stay isolated:
#   CC_DOGFOOD_LOG    (default /tmp/cc-dogfood.jsonl)
#   CC_DOGFOOD_STATE  (default /tmp/cc-dogfood-state.json)

LOG="${CC_DOGFOOD_LOG:-/tmp/cc-dogfood.jsonl}"
STATE="${CC_DOGFOOD_STATE:-/tmp/cc-dogfood-state.json}"
THRESHOLD=5
FORCE=false
RESET=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --threshold) THRESHOLD="$2"; shift 2 ;;
    --force)     FORCE=true; shift ;;
    --reset)     RESET=true; shift ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# jsonl missing → nothing to do.
[[ -f "$LOG" ]] || exit 0

NOW_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Total non-blank records (blank lines skipped). `|| true` swallows grep's exit-1 on
# zero matches under set -e; default to 0 if the field comes back empty.
TOTAL=$(grep -cE '[^[:space:]]' "$LOG" 2>/dev/null || true); TOTAL=${TOTAL:-0}

# Already-reported count from state (default 0 if no/garbled state).
LAST=0
if [[ -f "$STATE" ]]; then
  LAST=$(grep -oE '"last_reported_count":[0-9]+' "$STATE" 2>/dev/null | grep -oE '[0-9]+' | head -1 || true)
  LAST=${LAST:-0}
fi

write_state() {
  printf '{"last_reported_count":%s,"last_reported_ts":"%s"}\n' "$TOTAL" "$NOW_TS" > "$STATE"
}

# --reset: mark everything reported, emit nothing.
if $RESET; then
  write_state
  exit 0
fi

NEW=$(( TOTAL - LAST ))
[[ "$NEW" -lt 0 ]] && NEW=0   # log truncated/rotated under us → treat as fresh start

# Below threshold and not forced → stay silent (data is still accumulating).
if [[ "$NEW" -lt "$THRESHOLD" ]] && ! $FORCE; then
  exit 0
fi

# Nothing new at all (e.g. --force on an empty delta) → nothing meaningful to report.
if [[ "$NEW" -eq 0 ]]; then
  write_state
  exit 0
fi

# Unreported slice = records after the first LAST non-blank lines.
RECORDS=$(grep -E '[^[:space:]]' "$LOG" 2>/dev/null | tail -n +"$((LAST + 1))" || true)

# ── Tally friction signals across the unreported slice ──
n=0 fric=0 rb=0 rd=0 gapblk=0 tdm=0 gapover=0
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  n=$((n + 1)); f=0
  case "$line" in *'"residue_danger":true'*)    rd=$((rd + 1)); f=1 ;; esac
  case "$line" in *'"residue_benign":true'*)     rb=$((rb + 1)); f=1 ;; esac
  case "$line" in *'"gap_blocked":true'*)        gapblk=$((gapblk + 1)); f=1 ;; esac
  # exit_code=10 is emitted inside the residue danger hard gate, before the
  # completion audit can set TURN_DONE_FRESH. Its default turn_done_missing=true
  # is a code-ordering artifact, not evidence that the Stop hook failed.
  case "$line" in
    *'"turn_done_missing":true'*)
      if [[ "$line" != *'"exit_code":10'* ]]; then
        tdm=$((tdm + 1)); f=1
      fi
      ;;
  esac
  g=$(printf '%s' "$line" | grep -oE '"monitor_gap_s":[0-9]+' | grep -oE '[0-9]+' | head -1 || true)
  if [[ -n "${g:-}" && "$g" -gt 120 ]]; then gapover=$((gapover + 1)); f=1; fi
  [[ "$f" -eq 1 ]] && fric=$((fric + 1))
done <<EOF
$RECORDS
EOF

# Friction percentage (integer).
pct=0; [[ "$n" -gt 0 ]] && pct=$(( fric * 100 / n ))

# Date range from ts fields (date portion only).
DATES=$(printf '%s\n' "$RECORDS" | grep -oE '"ts":"[0-9]{4}-[0-9]{2}-[0-9]{2}' | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}')
D_FROM=$(printf '%s\n' "$DATES" | sed '/^$/d' | head -1)
D_TO=$(printf '%s\n' "$DATES" | sed '/^$/d' | tail -1)
[[ -z "$D_FROM" ]] && D_FROM="?"
[[ -z "$D_TO"   ]] && D_TO="?"

# State-sequence distribution: "SEQ (N次), ..." sorted by frequency.
SEQ_DIST=$(printf '%s\n' "$RECORDS" \
  | grep -oE '"states":"[^"]*"' | sed -E 's/"states":"([^"]*)"/\1/' | sed '/^$/d' \
  | sort | uniq -c | sort -rn \
  | awk '{cnt=$1; $1=""; sub(/^ /,""); printf "%s (%d次), ", $0, cnt}' | sed 's/, $//')
[[ -z "$SEQ_DIST" ]] && SEQ_DIST="（无状态序列记录）"

flag(){ [[ "$1" -gt 0 ]] && echo "⚠️" || echo "✅"; }

# ── Render summary ──
{
  echo "📊 cc-tmux Dogfood 摘要 [${D_FROM} ~ ${D_TO}]"
  echo "  ${n} 次任务，${fric} 次有摩擦 (${pct}%)"
  echo ""
  echo "  信号明细:"
  echo "  · $(flag "$rb") 残留触发 (benign): ${rb} 次$([[ "$rb" -gt 0 ]] && echo " → cc-send 发后回读可能未一次过")"
  echo "  · $(flag "$gapover") 监控间隙 >120s: ${gapover} 次$([[ "$gapover" -gt 0 ]] && echo " → 心跳维护盲区")"
  echo "  · $(flag "$rd") 危险残留: ${rd} 次"
  echo "  · $(flag "$gapblk") 因间隙拒绝收尾: ${gapblk} 次"
  echo "  · $(flag "$tdm") turn-done 缺失: ${tdm} 次"
  echo ""
  echo "  状态序列分布: ${SEQ_DIST}"
  echo ""
  if [[ "$fric" -eq 0 ]]; then
    echo "  → 整体平稳，本批未见摩擦信号。"
  else
    note="  → 检出摩擦信号。"
    [[ "$rd"      -gt 0 ]] && note="${note} 危险残留出现——立即排查残留来源。"
    [[ "$rb"      -gt 0 ]] && note="${note} 残留触发需留意——若持续出现考虑排查 #5/#18。"
    [[ "$gapover" -gt 0 || "$gapblk" -gt 0 ]] && note="${note} 监控间隙偏大——检查心跳/cadence。"
    [[ "$tdm"     -gt 0 ]] && note="${note} turn-done 缺失——确认 Stop hook 已部署。"
    echo "$note"
  fi
}

# Mark everything reported.
write_state
exit 0
