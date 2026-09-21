#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# gate-verify.sh —— 结构验收 gate（委派包 / OMP 输出）
#
# 【基质无关】 不依赖 Hermes / omp 在线 / 本 skill 的 lib；纯参数进、退出码出、自包含。
#              JSONL 双层解析 + 稳健判决提取就地内联（只用 jq / perl），任何 agent/编排基质可直接调。
#              稳健提取与 lib/omp-lib.sh:extract_verdict_json 同语义，为保持自包含刻意内联复制。
#
# 职责：验证两类对象具备"最小可信结构"——
#   package 模式：委派包字段是否齐（task/scope/criterion/threshold/output），且
#                 channel∈{shell,rpc,acp}、mode∈枚举、auditor.independence_level∈
#                 {bundle_only,independent_readonly}；bundle_only 须带 evidence_bundle.path。
#                 execute 模式豁免 criterion（通用执行任务无需可裁决验收条件）。
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

emit() { # <ok:true|false> <reason:string> <missing_fields:json-array>
  # 用 jq 做安全 JSON 编码：reason 可含换行/反斜杠/引号/Unicode，一律正确转义；
  # 输出恒为「单个合法 JSON 对象 + 换行」。不再用字符串插值拼 JSON（旧版仅转义双引号，
  # 遇 reason 含换行会产出两行/非法 JSON，违反单行 stdout 契约）。
  jq -cn --argjson ok "$1" --arg reason "$2" --argjson mf "${3:-[]}" \
    '{ok:$ok,reason:$reason,missing_fields:$mf}'
}

# ════ package 模式：委派包字段完整性 ════════════════════════════════
if [[ "$MODE" == "package" ]]; then
  # 文件须是合法 JSON 对象
  if ! jq -e 'type=="object"' "$FILE" >/dev/null 2>&1; then
    emit false "委派包不是合法 JSON 对象"; exit 1
  fi
  # 一次性算出缺失/非法字段数组：
  #   - criterion 须为非空数组（execute 模式豁免——通用执行任务无需可裁决 criterion）
  #   - channel（可选）须 shell|rpc|acp；mode 须在枚举内；
  #     auditor.independence_level（可选）须 bundle_only|independent_readonly；
  #     bundle_only 必须带 .evidence_bundle.path（否则审计者无离线证据基座）。
  #   - output 须 json + evidence_required
  set +e
  missing=$(jq -c '
    [ (if ((.task_id // "") | test("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$") | not) then "task_id(invalid)" else empty end),
      (if (.mode // "")        =="" then "mode" else empty end),
      (if (.task // "")        =="" then "task" else empty end),
      (if (.scope|type)        !="object" then "scope" else empty end),
      (if (.mode // "audit" | test("^execute")) then empty elif (.criterion|type)!="array" or (.criterion|length)==0 then "criterion" else empty end),
      (if ((.channel // "shell") | test("^(shell|rpc|acp)$")|not) then "channel(invalid)" else empty end),
      (if (.mode // "")=="" then empty elif (.mode | test("^(audit|execute|govern:(inspect|clean|deep-clean|evidence|sql))$")) then empty else "mode(invalid)" end),
      (if ((.auditor.independence_level // "independent_readonly") | test("^(bundle_only|independent_readonly)$")|not) then "auditor.independence_level(invalid)" else empty end),
      (if ((.auditor.independence_level // "")=="bundle_only") and ((.evidence_bundle.path // "")=="") then "evidence_bundle.path" else empty end),
      (if (.threshold.round_limit|type)!="number"  then "threshold.round_limit" else empty end),
      (if (.threshold.reject_limit|type)!="number" then "threshold.reject_limit" else empty end),
      (if (.output.format)         !="json" then "output.format" else empty end),
      (if (.output.evidence_required)!=true then "output.evidence_required" else empty end)
    ]' "$FILE" 2>/dev/null)
  set -e
  if [[ -z "$missing" ]]; then emit false "jq 解析委派包失败"; exit 1; fi
  n=$(printf '%s' "$missing" | jq 'length')
  if [[ "$n" -eq 0 ]]; then
    CAP_VALIDATOR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/resolve-capability-grant.py"
    if jq -e 'has("capability_grant")' "$FILE" >/dev/null 2>&1; then
      set +e
      capout=$(python3 "$CAP_VALIDATOR" --file "$FILE" --phase structure 2>/dev/null); caprc=$?
      set -e
      if [[ "$caprc" -ne 0 ]]; then
        capreason=$(printf '%s' "$capout" | jq -r '.reason // "capability_grant invalid"' 2>/dev/null || echo "capability_grant invalid")
        emit false "$capreason" '["capability_grant"]'; exit 1
      fi
    fi
    emit true "委派包字段齐全" "[]"; exit 0
  else
    emit false "委派包缺必填字段或字段值非法" "$missing"; exit 1
  fi
fi

# ════ output 模式：OMP JSONL 传输层 + 内层审计 JSON 应用层 ═══════════
# ── 传输层：非空 + 含终结事件 turn_end（grep 容忍 RPC 流式末尾未写完的行；不强求整文件
#    每行完整——shell -p raw 本就完整，rpc daemon raw 是流式，末尾可能有半行 agent_end）──
if [[ ! -s "$FILE" ]]; then emit false "OMP 输出为空" "[]"; exit 1; fi
if ! grep -q '"type":"turn_end"' "$FILE" 2>/dev/null; then
  emit false "OMP 输出无 turn_end 终结事件（未收尾/截断/超时/非 --mode json）" "[]"; exit 1
fi
last_stop=$(jq -r 'select(.type=="turn_end") | (.message.stopReason // .stopReason // "")' "$FILE" 2>/dev/null | tail -1)
if [[ "$last_stop" != "stop" ]]; then
  emit false "OMP 最后 stopReason=${last_stop:-unknown}（须 stop）" "[]"; exit 1
fi
# ── 应用层①：从 assistant 最终文本抠内层审计 JSON ──
# 逐行 select（-c 压单行，容忍 rpc 流式末行）→ tail 取最后一个 → jq -r 解码回多行文本。
final_text=$(jq -c 'select(.type=="message_end" and .message.role=="assistant")
                    | .message.content[]? | select(.type=="text") | .text' "$FILE" 2>/dev/null \
             | tail -1 | jq -r . 2>/dev/null)
# text_delta 兜底：v16.2.x 只发 assistantMessageEvent.type=text_delta 流、无 message_end 汇总块时，
# grep 预筛 delta 行 + 逐行 jq（容忍流式末行不完整）按序拼接还原最终文本。
if [[ -z "$final_text" ]]; then
  final_text=$(grep '"text_delta"' "$FILE" 2>/dev/null | while IFS= read -r _line; do
      printf '%s' "$_line" | jq -rj 'if (.assistantMessageEvent.type=="text_delta") then (.assistantMessageEvent.delta // .assistantMessageEvent.text // "")
                                    elif (.type=="text_delta") then (.text // "") else empty end' 2>/dev/null
    done)
fi
if [[ -z "$final_text" ]]; then
  emit false "OMP 无 assistant 文本输出" "[]"; exit 1
fi
# 稳健提取（与 omp-lib.sh extract_verdict_json 同语义，此处就地内联以保持 gate-verify 自包含）：
# 枚举文本中全部 top-level 平衡花括号对象（JSON 字符串感知），取「最后一个合法判决」
# （severity∈集合 / summary 非空 / evidence 为数组）；无合法判决则退化取最后一个对象，
# 使下方 severity/evidence 校验给出精确错误。这解决"多 fenced 块 / 多裸对象取错块"的脆弱性。
inner=""; _last_obj=""; _cand=""
while IFS= read -r -d '' _cand; do
  [[ -n "$_cand" ]] || continue
  _last_obj="$_cand"
  if printf '%s' "$_cand" | jq -e '
      type=="object"
      and ((.severity? // "") | test("^(nit|concern|blocker|pass)$"))
      and ((.summary?  // "") | (type=="string" and length>0))
      and ((.evidence?)       | type=="array")' >/dev/null 2>&1; then
    inner="$_cand"
  fi
done < <(printf '%s' "$final_text" | perl -0777 -ne '
  my $s=$_; my $d=0; my $st=-1; my $in=0; my $es=0;
  for my $i (0..length($s)-1){ my $c=substr($s,$i,1);
    if($in){ if($es){$es=0} elsif($c eq "\\"){$es=1} elsif($c eq "\""){$in=0} next }
    if($c eq "\""){$in=1; next}
    if($c eq "{"){ $st=$i if $d==0; $d++ }
    elsif($c eq "}"){ if($d>0){$d--; if($d==0 && $st>=0){ print substr($s,$st,$i-$st+1),"\0"; $st=-1 }} }
  }' 2>/dev/null)
[[ -z "$inner" ]] && inner="$_last_obj"
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
# ── 应用层④0：v1 外层判决契约标记（P1C1 · 仅 marker 出现时生效）───────
# 显式版本标记 required_actions_contract 收窄"外层判决"歧义，且不误伤历史 raw：
#   缺标记       → legacy 路径不变（下方 P1A 加性块只在 required_actions 出现时校验，不新增要求）。
#   标记≠精确 v1 → 结构化 gate 错误 exit 1（未知/坏版本一律拒）。
#   标记==精确 v1→ 外层键收窄到 allowlist；required_actions 必填；下方 severity 一致性强校验。
V1_MARKER="call-omp.required_actions.v1"
is_v1=0
if printf '%s' "$inner" | jq -e 'has("required_actions_contract")' >/dev/null 2>&1; then
  marker=$(printf '%s' "$inner" | jq -rc '.required_actions_contract')
  if [[ "$marker" != "$V1_MARKER" ]]; then
    emit false "required_actions_contract 非法：须为 '$V1_MARKER'（得 '${marker}'）" '["required_actions_contract"]'; exit 1
  fi
  is_v1=1
  # v1 外层键 allowlist：只允许显式契约字段；任何 allowlist 之外的顶层键即拒
  # （confidence 属显式字段，放行；不算未知键）。
  extra=$(printf '%s' "$inner" | jq -c '[keys_unsorted[] | select(. as $k | ["severity","summary","evidence","reject_instruction","confidence","required_actions_contract","required_actions"]|index($k)|not)]')
  if [[ "$extra" != "[]" ]]; then
    emit false "v1 外层判决含 allowlist 之外的顶层键：${extra}" "$extra"; exit 1
  fi
  # v1 required_actions 必填（区别于 legacy 的"缺字段=豁免"）。
  if ! printf '%s' "$inner" | jq -e 'has("required_actions")' >/dev/null 2>&1; then
    emit false "v1 外层判决缺 required_actions（v1 必填）" '["required_actions"]'; exit 1
  fi
fi

# ── 应用层④：required_actions 加性契约（P1A · 仅在字段出现时生效）──
# 缺字段 → 保持既有行为（legacy 兼容，不新增任何要求）。
# 出现 → 须过 schema 校验（枚举/上限一律由 contracts/required-actions.schema.json 派生）；
#        且 severity==pass 时不得携带非空动作（pass 无 required action）；
#        v1 判决额外要求非 pass severity 至少 1 个动作（P1C1）。
if printf '%s' "$inner" | jq -e 'has("required_actions")' >/dev/null 2>&1; then
  ra_compact=$(printf '%s' "$inner" | jq -c '.required_actions')
  # 校验器对畸形输入合法退出 1；在全局 set -e 下 `ra_out=$(...)` 赋值会随之中断，
  # 使承诺的结构化 emit false 无从执行。故显式局部关 errexit，稳妥捕获 stdout 与退出码；
  # stderr（含潜在 traceback）丢到 /dev/null，绝不并入 stdout 污染结构化输出。
  set +e
  ra_out=$("${PYTHON:-python3}" "$(dirname "$0")/../required-actions-validate.py" --json "$ra_compact" 2>/dev/null)
  ra_rc=$?
  set -e
  if [[ "$ra_rc" -ne 0 ]]; then
    ra_reason=$(printf '%s' "$ra_out" | jq -rc '.reason // empty' 2>/dev/null)
    [[ -n "$ra_reason" ]] || ra_reason="校验器拒绝（rc=${ra_rc}）"
    emit false "required_actions 契约不合法：${ra_reason}" '["required_actions"]'; exit 1
  fi
  ra_len=$(printf '%s' "$inner" | jq -rc 'if (.required_actions|type)=="array" then (.required_actions|length) else -1 end')
  if [[ "$sev" == "pass" && "$ra_len" -gt 0 ]]; then
    emit false "severity=pass 却携带 ${ra_len} 个 required_actions（pass 无 required action）" '["required_actions"]'; exit 1
  fi
  # v1 严格闸：非 pass severity 必须至少 1 个动作（legacy 无此强制）。
  if [[ "$is_v1" -eq 1 && "$sev" != "pass" && "$ra_len" -lt 1 ]]; then
    emit false "v1 非 pass severity=$sev 须至少 1 个 required_actions（得 ${ra_len}）" '["required_actions"]'; exit 1
  fi
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
