#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# gate-verify.sh —— 结构验收 gate（委派包 / OMP 输出）
#
# 【基质无关】 不依赖 Hermes / omp 在线 / 本 skill 的 lib；纯参数进、退出码出、自包含。
#              JSONL 双层解析就地内联（只用 jq），任何 agent/编排基质可直接调。
#
# 职责：验证两类对象具备"最小可信结构"——
#   package 模式：委派包字段是否齐（task/scope/criterion/threshold/output）。
#   output  模式：OMP 的 --mode json 原始 JSONL 是否完整，且内层审计 JSON 有 severity、
#                 evidence 非空。evidence 为空是硬红线（不采信无证据的"完成"）。
#
# 参数：
#   --mode package|output   验收对象类型（必填）
#   --file <path>           待验文件：package=委派包 JSON；output=omp 原始 JSONL（--mode json 落盘）
#   --json                  （默认即 JSON 单行输出，此 flag 保留兼容）
#   -h|--help               打印本头注
#
# 退出码： 0 通过 · 1 结构错误（缺字段/非 JSON/无 severity/JSONL 不完整）· 3 参数错误
#          · 10 evidence 为空（硬拒绝，与 gate-danger 同语义，不可绕过）
# stdout： {"ok":bool,"reason":"...","missing_fields":[...]}（单行 JSON）
#
# 示例：
#   bash gate-verify.sh --mode package --file /tmp/omp-state-xxx.json
#   bash gate-verify.sh --mode output  --file /tmp/omp-raw-xxx.json   # 缺 evidence → exit 10
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

MODE=""; FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --file) FILE="$2"; shift 2 ;;
    --json) shift ;;                       # 始终 JSON 输出，flag 仅为兼容
    -h|--help) sed -n '2,33p' "$0"; exit 0 ;;
    *) echo "gate-verify: 未知参数 $1" >&2; exit 3 ;;
  esac
done
[[ "$MODE" == "package" || "$MODE" == "output" ]] || { echo "gate-verify: --mode 须 package|output" >&2; exit 3; }
[[ -n "$FILE" && -r "$FILE" ]] || { echo "gate-verify: 读不到 --file '$FILE'" >&2; exit 3; }

emit() { # <ok> <reason> <missing_json_array>
  printf '{"ok":%s,"reason":"%s","missing_fields":%s}\n' "$1" "${2//\"/\\\"}" "${3:-[]}"
}

# ════ package 模式：委派包字段完整性 ════════════════════════════════
if [[ "$MODE" == "package" ]]; then
  # 文件须是合法 JSON 对象
  if ! jq -e 'type=="object"' "$FILE" >/dev/null 2>&1; then
    emit false "委派包不是合法 JSON 对象"; exit 1
  fi
  # 一次性算出缺失字段数组（criterion 须为非空数组；output 须 json+evidence_required）
  set +e
  missing=$(jq -c '
    [ (if (.task_id // "")     =="" then "task_id" else empty end),
      (if (.mode // "")        =="" then "mode" else empty end),
      (if (.task // "")        =="" then "task" else empty end),
      (if (.scope|type)        !="object" then "scope" else empty end),
      (if (.criterion|type)!="array" or (.criterion|length)==0 then "criterion" else empty end),
      (if (.threshold.round_limit|type)!="number"  then "threshold.round_limit" else empty end),
      (if (.threshold.reject_limit|type)!="number" then "threshold.reject_limit" else empty end),
      (if (.output.format)         !="json" then "output.format" else empty end),
      (if (.output.evidence_required)!=true then "output.evidence_required" else empty end)
    ]' "$FILE" 2>/dev/null)
  set -e
  if [[ -z "$missing" ]]; then emit false "jq 解析委派包失败"; exit 1; fi
  n=$(printf '%s' "$missing" | jq 'length')
  if [[ "$n" -eq 0 ]]; then
    emit true "委派包字段齐全" "[]"; exit 0
  else
    emit false "委派包缺必填字段" "$missing"; exit 1
  fi
fi

# ════ output 模式：OMP JSONL 传输层 + 内层审计 JSON 应用层 ═══════════
# ── 传输层：非空 + 含终结事件 turn_end（grep 容忍 RPC 流式末尾未写完的行；不强求整文件
#    每行完整——shell -p raw 本就完整，rpc daemon raw 是流式，末尾可能有半行 agent_end）──
if [[ ! -s "$FILE" ]]; then emit false "OMP 输出为空" "[]"; exit 1; fi
if ! grep -q '"type":"turn_end"' "$FILE" 2>/dev/null; then
  emit false "OMP 输出无 turn_end 终结事件（未收尾/截断/超时/非 --mode json）" "[]"; exit 1
fi
# ── 应用层①：从 assistant 最终文本抠内层审计 JSON ──
# 逐行 select（-c 压单行，容忍 rpc 流式末行）→ tail 取最后一个 → jq -r 解码回多行文本。
final_text=$(jq -c 'select(.type=="message_end" and .message.role=="assistant")
                    | .message.content[]? | select(.type=="text") | .text' "$FILE" 2>/dev/null \
             | tail -1 | jq -r . 2>/dev/null)
if [[ -z "$final_text" ]]; then
  emit false "OMP 无 assistant 文本输出" "[]"; exit 1
fi
# fenced ```json 优先；否则首{…末}贪婪切片
inner=$(printf '%s' "$final_text" | awk '
  /^[[:space:]]*```[[:space:]]*[jJ][sS][oO][nN][[:space:]]*$/ {f=1; next}
  /^[[:space:]]*```[[:space:]]*$/ {if(f){exit}}
  f {print}')
if [[ -z "$inner" ]]; then
  inner=$(printf '%s' "$final_text" | perl -0777 -ne 'if (/(\{.*\})/s){print $1}' 2>/dev/null || true)
fi
if [[ -z "$inner" ]] || ! printf '%s' "$inner" | jq -e 'type=="object"' >/dev/null 2>&1; then
  emit false "OMP 文本中无合法审计 JSON（应输出 {severity,evidence,summary}）" "[]"; exit 1
fi
# ── 应用层②：severity 存在 ──
sev=$(printf '%s' "$inner" | jq -rc '.severity // empty')
if [[ -z "$sev" ]]; then
  emit false "审计 JSON 缺 severity 字段" '["severity"]'; exit 1
fi
# ── 应用层③：evidence 非空（硬红线 → exit 10）──
ev_len=$(printf '%s' "$inner" | jq -rc 'if (.evidence|type)=="array" then (.evidence|length) else -1 end')
if [[ "$ev_len" -le 0 ]]; then
  emit false "evidence 为空或非数组——不采信无证据的完成" '["evidence"]'; exit 10
fi
# ── 上下文守恒告警（非阻塞；只告警不拦截）──
raw_size=$(wc -c < "$FILE" | tr -d ' ')
raw_mb=$(echo "scale=1; $raw_size / 1048576" | bc)
if [[ $(echo "$raw_size > 1048576" | bc) -eq 1 ]]; then
  echo "⚠️  gate-verify: OMP raw 输出大小为 ${raw_mb}MB，超过 1MB 阈值" >&2
  echo "    → 不要将 raw 打进上下文！只提取 severity/summary/evidence 字段。" >&2
  echo "    → 完整 raw 路径：$FILE" >&2
fi
emit true "OMP 输出结构完整：severity=$sev, evidence=${ev_len} 条" "[]"
exit 0
