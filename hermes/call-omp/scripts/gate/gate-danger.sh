#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# gate-danger.sh —— 危险操作 / 越界 / 凭据夹带 拦截 gate
#
# 【基质无关】 不依赖 Hermes / omp 在线；纯参数进、退出码出、自包含。
#
# 职责：两类对象的危险面拦截——
#   package 模式：① 危险任务（mode∈clean/deep-clean/sql，或 risk.dangerous_modes 非空，
#                   或 risk.level=high）必须带 scope；② clean/deep-clean/sql 必须带 rollback；
#                ③ 全文扫描破坏性命令与夹带凭据。
#   prompt  模式：纯文本扫描破坏性命令与夹带凭据。
#
# 危险模式来自 danger-patterns.txt（可 --patterns-file 覆盖）。凭据模式内联，
# 命中只标记 "sensitive:credential-like" 绝不回显原文（防二次泄露——SOUL 安全红线）。
#
# 参数：
#   --mode package|prompt   对象类型（必填）
#   --file <path>           package JSON 或 prompt 文本文件
#   --scan-text "<text>"    prompt 模式直接传文本（与 --file 二选一）
#   --patterns-file <path>  覆盖内置破坏性命令模式
#   -h|--help               打印本头注
#
# 退出码： 0 通过 · 10 拦截（人工红线，不可自动放行）· 3 参数错误
# stdout： {"ok":bool,"reason":"...","dangerous_modes":[...],"blocked":bool}
#
# 示例：
#   bash gate-danger.sh --mode package --file /tmp/omp-pkg.json   # clean 无 rollback → exit 10
#   bash gate-danger.sh --mode prompt  --scan-text "rm -rf /data" # → exit 10
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

MODE=""; FILE=""; SCAN_TEXT=""; PATTERNS_FILE=""
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)          MODE="$2"; shift 2 ;;
    --file)          FILE="$2"; shift 2 ;;
    --scan-text)     SCAN_TEXT="$2"; shift 2 ;;
    --patterns-file) PATTERNS_FILE="$2"; shift 2 ;;
    -h|--help)       sed -n '2,37p' "$0"; exit 0 ;;
    *) echo "gate-danger: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ "$MODE" == "package" || "$MODE" == "prompt" ]] || { echo "gate-danger: --mode 须 package|prompt" >&2; exit 3; }
PATTERNS_FILE="${PATTERNS_FILE:-$SELF_DIR/danger-patterns.txt}"

# ── 内联凭据模式（命中只标记，不回显）──────────────────────────────
SENSITIVE=(
  '-----BEGIN[[:space:]][A-Z ]*PRIVATE KEY-----'
  '\bsk-[A-Za-z0-9]{20,}'
  '\bgh[pousr]_[A-Za-z0-9]{20,}'
  '\bxox[baprs]-[A-Za-z0-9-]{10,}'
  '\bAKIA[0-9A-Z]{16}\b'
  '(api[_-]?key|secret|access[_-]?token|password|passwd|client[_-]?secret)[[:space:]]*[:=][[:space:]]*[^[:space:]"'"'"']{6,}'
  '(^|[[:space:]/])\.env([[:space:]/:]|$)'
)

HITS=()          # 破坏性命令命中（含模式片段）
SENS_HIT=0       # 凭据命中标志（只标记）
DMODES=()        # 检测到的危险模式名

scan_destructive() { # <content>
  local content="$1" pat
  while IFS= read -r pat; do
    [[ -z "$pat" || "$pat" =~ ^[[:space:]]*# ]] && continue
    if printf '%s' "$content" | grep -Eiq -- "$pat"; then HITS+=("$pat"); fi
  done < "$PATTERNS_FILE"
}
scan_sensitive() { # <content>
  local content="$1" pat
  for pat in "${SENSITIVE[@]}"; do
    if printf '%s' "$content" | grep -Eiq -- "$pat"; then SENS_HIT=1; return; fi
  done
}
arr_json() { # args → JSON 数组（去重，过滤空串；bash 3.2 安全）
  local items=() x
  for x in "$@"; do [[ -n "$x" ]] && items+=("$x"); done
  [[ ${#items[@]} -eq 0 ]] && { echo "[]"; return; }
  printf '%s\n' "${items[@]}" | jq -R . | jq -sc 'unique'
}
emit() { # <ok> <reason> <dmodes_json> <blocked>
  printf '{"ok":%s,"reason":"%s","dangerous_modes":%s,"blocked":%s}\n' \
    "$1" "${2//\"/\\\"}" "${3:-[]}" "$4"
}

REASONS=()

if [[ "$MODE" == "package" ]]; then
  [[ -n "$FILE" && -r "$FILE" ]] || { echo "gate-danger: package 模式需可读 --file" >&2; exit 3; }
  jq -e 'type=="object"' "$FILE" >/dev/null 2>&1 || { echo "gate-danger: 委派包非合法 JSON" >&2; exit 3; }

  pkg_mode=$(jq -rc '.mode // ""' "$FILE")
  level=$(jq -rc '.risk.level // ""' "$FILE")
  decl_dmodes=()
  while IFS= read -r _dm; do [[ -n "$_dm" ]] && decl_dmodes+=("$_dm"); done \
    < <(jq -rc '.risk.dangerous_modes[]? // empty' "$FILE" 2>/dev/null || true)

  is_gov_danger=0
  case "$pkg_mode" in
    govern:clean|govern:deep-clean|govern:sql)
      is_gov_danger=1
      DMODES+=("${pkg_mode#govern:}")
      ;;
  esac
  [[ ${#decl_dmodes[@]} -gt 0 ]] && DMODES+=("${decl_dmodes[@]}")
  has_danger=0
  { [[ "$is_gov_danger" -eq 1 ]] || [[ ${#decl_dmodes[@]} -gt 0 ]] || [[ "$level" == "high" ]]; } && has_danger=1

  # ① 任意危险任务必须有 scope；三种 govern 写模式还必须 high + rollback。
  if [[ "$has_danger" -eq 1 ]]; then
    scope_ok=$(jq -rc '
      def nonblank: type=="string" and (gsub("[[:space:]]";"")|length)>0;
      if (((.scope.allowed_paths // []) | any(nonblank)) or ((.scope.cwd // "") | nonblank)) then "1" else "0" end' "$FILE")
    [[ "$scope_ok" == "1" ]] || REASONS+=("危险任务缺 scope（allowed_paths/cwd 均空）")
  fi
  if [[ "$is_gov_danger" -eq 1 ]]; then
    rb=$(jq -rc '(.risk.rollback // .rollback // "") | if type=="string" then gsub("^[[:space:]]+|[[:space:]]+$";"") else "" end' "$FILE")
    [[ -n "$rb" ]] || REASONS+=("$pkg_mode 模式缺 rollback 描述")
    [[ "$level" == "high" ]] || REASONS+=("$pkg_mode 模式 risk.level 须为 high")
  fi
  # ③ 全文扫描破坏性命令 + 凭据
  # Structural mode declarations such as govern:deep-clean are not prompt content.
  # Scan the executable/task payload while excluding the mode fields that the gate already handles explicitly.
  content=$(jq -rc 'del(.mode, .risk.dangerous_modes)' "$FILE")
  scan_destructive "$content"
  scan_sensitive "$content"
else
  # prompt 模式
  if [[ -n "$FILE" ]]; then
    [[ -r "$FILE" ]] || { echo "gate-danger: 读不到 --file '$FILE'" >&2; exit 3; }
    content=$(cat "$FILE")
  elif [[ -n "$SCAN_TEXT" ]]; then
    content="$SCAN_TEXT"
  else
    echo "gate-danger: prompt 模式需 --file 或 --scan-text" >&2; exit 3
  fi
  scan_destructive "$content"
  scan_sensitive "$content"
fi

# ── 汇总裁决 ──
[[ ${#HITS[@]} -gt 0 ]] && REASONS+=("命中破坏性命令模式 ${#HITS[@]} 处")
[[ "$SENS_HIT" -eq 1 ]] && { REASONS+=("夹带疑似凭据 sensitive:credential-like"); DMODES+=("credential-leak"); }

dm_json=$(arr_json "${DMODES[@]:-}")
if [[ ${#REASONS[@]} -gt 0 ]]; then
  reason=$(IFS='; '; echo "${REASONS[*]}")
  emit false "$reason" "$dm_json" true
  exit 10
fi
emit true "无危险命中" "$dm_json" false
exit 0
