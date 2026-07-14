# shellcheck shell=bash
# ─────────────────────────────────────────────────────────────────
# omp-lib.sh —— omp skill 共享函数库（source 进各脚本，不单独执行）
#
# 【零运行时耦合】只依赖 bash 3.2+ / jq / coreutils；不依赖 Hermes、不依赖 omp 在线。
# 【单一约定源】所有 /tmp 路径、原子写、时间戳、JSONL 双层提取都在此定义，
#               各脚本一律走这里，杜绝"状态文件路径在 5 个脚本里各拼一遍"的漂移。
#
# 用法：
#   source "$(dirname "$0")/lib/omp-lib.sh"
#
# 可注入环境变量（测试隔离 / 真实运行均零改动）：
#   OMP_BIN      omp 可执行名（默认 "omp"）——测试可注入 mock 脚本路径
#   OMP_TMPDIR   状态文件基目录（默认 "/tmp"）——测试可指向临时目录
# ─────────────────────────────────────────────────────────────────

OMP_BIN="${OMP_BIN:-omp}"
OMP_TMPDIR="${OMP_TMPDIR:-/tmp}"

# ── get_mtime <file> ─ 文件 mtime（epoch 秒），不存在/取不到 → 0 ─────
# Fallback 链：macOS/BSD stat → Linux/GNU stat → Perl → 0（照搬 cc-tmux portability）
get_mtime() {
  local f="$1"
  [[ ! -f "$f" ]] && { echo "0"; return 0; }
  local m
  m=$(stat -f %m "$f" 2>/dev/null) && { echo "$m"; return 0; }
  m=$(stat -c %Y "$f" 2>/dev/null) && { echo "$m"; return 0; }
  m=$(perl -e 'print((stat($ARGV[0]))[9])' "$f" 2>/dev/null) && { echo "$m"; return 0; }
  echo "0"
}

# ── now_iso ─ 当前 UTC 时间戳（ISO8601） ────────────────────────────
now_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# ── now_epoch ─ 当前 epoch 秒 ──────────────────────────────────────
now_epoch() { date +%s; }

# ── task_id / 路径约定（全部基于 OMP_TMPDIR，单一来源）──────────────
validate_task_id() {
  local id="${1:-}"
  [[ -n "$id" && ${#id} -le 128 && "$id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]
}
require_task_id() {
  validate_task_id "${1:-}" || { echo "call-omp: 非法 task_id（须匹配 [A-Za-z0-9][A-Za-z0-9._-]{0,127}）" >&2; return 3; }
}
state_path()    { require_task_id "$1" || return; echo "$OMP_TMPDIR/omp-state-$1.json"; }
raw_path()      { require_task_id "$1" || return; echo "$OMP_TMPDIR/omp-raw-$1.json"; }     # omp --mode json 原始 JSONL
prompt_path()   { require_task_id "$1" || return; echo "$OMP_TMPDIR/omp-prompt-$1.txt"; }   # 渲染后的 prompt（落盘，避免命令行超长）
counter_path()  { require_task_id "$1" || return; echo "$OMP_TMPDIR/omp-counter-$1.json"; }
archive_dir()   { require_task_id "$1" || return; echo "$OMP_TMPDIR/omp-archive/$1"; }

# ── omp_available ─ omp CLI 是否可用（0=可用，非 0=不可用）──────────
# 不假设 omp 已装；channel 降级判断的唯一入口。
omp_available() { command -v "$OMP_BIN" >/dev/null 2>&1; }

# ── atomic_write <target_file> ─ 从 stdin 原子写入目标文件 ──────────
# 写临时文件再 mv（同分区 mv 原子）——防撕裂读。串行调用足够；
# 若未来并发复用须补 flock（与 cc-tmux gate-counter 同注脚）。
atomic_write() {
  local target="$1" tmp
  tmp="${target}.$$.tmp"
  cat > "$tmp"
  mv -f "$tmp" "$target"
}

# ── run_omp_timed <max_seconds> <args...> ─ 带硬超时跑 omp ──────────
# macOS 无 `timeout`（GNU coreutils only）；用 perl alarm 做外层硬杀，
# 同时调用方应另传 omp 内置 --max-time 作内层自停（双保险）。
# 外层余量 = max_seconds + 30s，给 omp 自己的 --max-time 先生效的机会。
# 返回 omp 退出码；perl 不存在时降级为无外层超时直跑（仍有 omp --max-time）。
run_omp_timed() {
  local secs="$1"; shift
  if command -v perl >/dev/null 2>&1; then
    perl -e 'alarm shift; exec @ARGV or exit 127' "$((secs + 30))" "$OMP_BIN" "$@"
  else
    "$OMP_BIN" "$@"
  fi
}

# ══ omp JSONL（--mode json）解析：传输层 ════════════════════════════
# omp --mode json 输出 NDJSON 事件流，不是单个 JSON 对象。
# 事件序列：session → agent_start → turn_start → message_start/update/end
#           → turn_end（权威终结，含 stopReason/usage）→ agent_end。

# jsonl_parsable <raw_file> ─ 非空且整体可被 jq 解析？（0=是）
jsonl_parsable() {
  [[ -s "$1" ]] || return 1
  jq . "$1" >/dev/null 2>&1
}

# jsonl_has_turn_end <raw_file> ─ 含权威终结事件？（0=是）
jsonl_has_turn_end() {
  jq -e 'select(.type=="turn_end")' "$1" >/dev/null 2>&1
}

# jsonl_stop_reason <raw_file> ─ 末轮 stopReason（stop=正常；空=未取到）
jsonl_stop_reason() {
  jq -rc 'select(.type=="turn_end") | .message.stopReason // empty' "$1" 2>/dev/null | tail -1
}

# jsonl_final_text <raw_file> ─ assistant 最终文本（排除 thinking 块）
# 这是 OMP 的"应用层载荷"，内层审计 JSON 就藏在这里面。
# 两条取文路径（按优先级）：
#   ① message_end.message.content[].text —— shell / rpc v16.2.2 权威终结形态。
#   ② text_delta 流兜底 —— OMP v16.2.x 部分构建只发 assistantMessageEvent.type=text_delta
#      流式增量、无 message_end 汇总块时，按行拼接所有 delta 还原最终文本。
jsonl_final_text() {
  local raw="$1" t
  # ① 逐行 select（-c 把多行 text 压成单行 JSON 字符串，容忍 RPC 流式末尾未写完的行；
  #    -rs slurp 会因末行不完整而整体失败），tail 取最后一个，再 jq -r 解码回多行文本。
  t=$(jq -c 'select(.type=="message_end" and .message.role=="assistant")
             | .message.content[]? | select(.type=="text") | .text' "$raw" 2>/dev/null \
      | tail -1 | jq -r . 2>/dev/null)
  if [[ -n "$t" ]]; then printf '%s' "$t"; return 0; fi
  # ② text_delta 兜底：grep 预筛只处理 delta 行 + 逐行 jq（容忍流式末行不完整），按序拼接。
  #    兼容两种壳：{"assistantMessageEvent":{"type":"text_delta","delta":…}} 与顶层 {"type":"text_delta","text":…}。
  t=$(grep '"text_delta"' "$raw" 2>/dev/null | while IFS= read -r line; do
        printf '%s' "$line" | jq -rj 'if (.assistantMessageEvent.type=="text_delta") then (.assistantMessageEvent.delta // .assistantMessageEvent.text // "")
                                      elif (.type=="text_delta") then (.text // "") else empty end' 2>/dev/null
      done)
  printf '%s' "$t"
}

# jsonl_usage <raw_file> ─ 末轮 token 用量摘要（紧凑 JSON，监控展示用）
jsonl_usage() {
  jq -rc 'select(.type=="turn_end") | .message.usage // empty' "$1" 2>/dev/null | tail -1
}

# ══ 内层审计 JSON：应用层 ═══════════════════════════════════════════
# OMP 不原生输出 severity/evidence/summary——靠 templates/ 的 system-prompt
# 要求 OMP 把审计结论写成严格 JSON。它通常被包在 markdown ```json ... ``` 围栏里，
# 或直接是裸 JSON。下面从 assistant 最终文本里把那块 JSON 抠出来。

# extract_inner_json <text> ─ 从自由文本里提取第一个完整 JSON 对象
# 策略：① 优先 ```json fenced 块 ② 退化为首个 { 到末个 } 的跨行切片。
# 输出抠出的 JSON 串（未必合法，交 jq 二次校验）；找不到 → 空。
extract_inner_json() {
  local text="$1" fenced
  # ① fenced ```json ... ```
  fenced=$(printf '%s' "$text" | awk '
    /^[[:space:]]*```[[:space:]]*[jJ][sS][oO][nN][[:space:]]*$/ {f=1; next}
    /^[[:space:]]*```[[:space:]]*$/ {if(f){exit}}
    f {print}
  ')
  if [[ -n "$fenced" ]]; then printf '%s' "$fenced"; return 0; fi
  # ② 首 { … 末 }（贪婪跨行）——交给 jq 校验合法性
  printf '%s' "$text" | perl -0777 -ne 'if (/(\{.*\})/s) { print $1 }' 2>/dev/null
}

# inner_json_valid <json_str> ─ 是合法 JSON 对象？（0=是）
inner_json_valid() {
  printf '%s' "$1" | jq -e 'type=="object"' >/dev/null 2>&1
}

# ── 稳健判决提取 ────────────────────────────────────────────────────
# 背景：extract_inner_json 只取"首个 fenced 块 / 首{…末}贪婪切片"，遇到
#   ① prose 里多个 fenced 块（前一个是陈旧/非法草稿，末一个才是终稿）
#   ② 多个裸对象混在自由文本里
# 会选错块或跨对象拼出非法 JSON。extract_verdict_json 改为「枚举全部候选、取最后一个
# 合法判决对象」。extract_inner_json 保持不变（向后兼容 + 退化兜底报错用）。

# _json_objects_nul（stdin=文本）─ 输出文本中所有 top-level 平衡花括号对象，NUL 分隔
# JSON 字符串感知：跳过字符串内的 {}/引号，正确处理反斜杠转义，故不会被 "summary":"a } b" 骗到。
# 同时覆盖 ```json fenced 内 JSON 与裸 JSON（围栏反引号非花括号，不影响配平）。
_json_objects_nul() {
  perl -0777 -ne '
    my $s=$_; my $d=0; my $st=-1; my $in=0; my $es=0;
    for my $i (0..length($s)-1){ my $c=substr($s,$i,1);
      if($in){ if($es){$es=0} elsif($c eq "\\"){$es=1} elsif($c eq "\""){$in=0} next }
      if($c eq "\""){$in=1; next}
      if($c eq "{"){ $st=$i if $d==0; $d++ }
      elsif($c eq "}"){ if($d>0){$d--; if($d==0 && $st>=0){ print substr($s,$st,$i-$st+1),"\0"; $st=-1 }} }
    }' 2>/dev/null
}

# verdict_valid <json_str> ─ 是合法审计判决对象？（0=是）
# 判据：severity∈{nit,concern,blocker,pass}、summary 为非空字符串、evidence 为数组。
# 注意：evidence 空数组仍算"结构合法判决"——空证据红线由 gate/monitor 现有逻辑判（exit 10），
#       这里不并入，否则空证据判决会被跳过、退化到更旧的对象，反而绕过 evidence 硬拦截。
verdict_valid() {
  printf '%s' "$1" | jq -e '
    type=="object"
    and ((.severity? // "") | test("^(nit|concern|blocker|pass)$"))
    and ((.summary?  // "") | (type=="string" and length>0))
    and ((.evidence?)       | type=="array")' >/dev/null 2>&1
}

# extract_verdict_json <text> ─ 从自由文本取"最后一个合法判决对象"（0=取到并打印，1=无）
# 枚举全部候选对象，逐个 verdict_valid 校验，保留最后一个通过的（多草稿 → 终稿语义）。
extract_verdict_json() {
  local last="" obj
  while IFS= read -r -d '' obj; do
    [[ -n "$obj" ]] || continue
    if verdict_valid "$obj"; then last="$obj"; fi
  done < <(printf '%s' "$1" | _json_objects_nul)
  [[ -n "$last" ]] || return 1
  printf '%s' "$last"
}

# extract_last_json_object <text> ─ 取最后一个 top-level JSON 对象（不校验判决语义）
# 无合法判决时的退化兜底：让 monitor/gate 拿到"最像判决"的那个块来给出精确错误
# （缺 severity / severity 非法 / summary 缺失 / evidence 空），而非笼统"无 JSON"。
extract_last_json_object() {
  local last="" obj
  while IFS= read -r -d '' obj; do
    [[ -n "$obj" ]] && last="$obj"
  done < <(printf '%s' "$1" | _json_objects_nul)
  [[ -n "$last" ]] || return 1
  printf '%s' "$last"
}

# ── die <msg> / warn <msg> ─ 统一错误/告警到 stderr ────────────────
die()  { echo "omp: $*" >&2; exit 1; }
warn() { echo "omp: $*" >&2; }

# ══ RPC 通道（omp --mode rpc 持续连接）═══════════════════════════════
# 协议（v16.2.2 实测，见 references/omp-rpc-acp-notes.md）：
#   启动：omp --mode rpc <flags> → stdout 输出 {"type":"ready"} 后等 stdin。
#   发指令：stdin 写一行 {"type":"prompt","message":"<文本>"}（对 .message 做
#           startsWith('/') 分流 slash/prompt；普通文本即一次 prompt turn）。
#   响应：stdout 每 turn 的 JSONL（turn_start..turn_end/agent_end），持续连接多 turn 复用。
# fifo 写端要靠 holder 进程（sleep）保持打开，否则 daemon 读到 EOF 自退。

fifo_path()   { require_task_id "$1" || return; echo "$OMP_TMPDIR/omp-rpc-$1.fifo"; }

# rpc_daemon_alive <pid> ─ daemon 进程存活？（0=活）
rpc_daemon_alive() { [[ -n "${1:-}" && "${1:-}" != "null" ]] && kill -0 "$1" 2>/dev/null; }

# rpc_wait_ready <raw> [max_tries] ─ 轮询 raw 出现 ready 事件（0=ready，1=超时）
# 每次 0.25s，默认 60 次 = 15s（omp rpc 冷启动通常 2-5s）。脚本内 sleep，非交互安全。
rpc_wait_ready() {
  local raw="$1" tries="${2:-60}" i=0
  while [[ $i -lt $tries ]]; do
    [[ -f "$raw" ]] && grep -q '"type":"ready"' "$raw" 2>/dev/null && return 0
    sleep 0.25; i=$((i + 1))
  done
  return 1
}

# rpc_turn_done <raw> <start_line> ─ start_line 之后是否出现非 toolUse 的终态 turn_end（0=本轮结束）
# RPC 一个 prompt 常产生多 turn：中间 toolUse turn（stopReason=toolUse，content 含 toolCall）
# + 最终文本 turn（正常为 stop；也可能 maxTokens/aborted/error）。toolUse 继续等待，其余交给 monitor fail-closed。
rpc_turn_done() {
  local raw="$1" start="${2:-0}"
  [[ -f "$raw" ]] || return 1
  tail -n "+$((start + 1))" "$raw" 2>/dev/null \
    | jq -rc 'select(.type=="turn_end")|(.message.stopReason // .stopReason // empty)' 2>/dev/null \
    | grep -Ev '^(toolUse)?$' >/dev/null
}

# rpc_stop <task_id> <daemon_pid> <holder_pid> ─ 关 daemon+holder、删 fifo（幂等）
rpc_stop() {
  local id="$1" dpid="${2:-}" hpid="${3:-}"
  [[ -n "$dpid" && "$dpid" != "null" ]] && kill "$dpid" 2>/dev/null || true
  [[ -n "$hpid" && "$hpid" != "null" ]] && kill "$hpid" 2>/dev/null || true
  rm -f "$(fifo_path "$id")" 2>/dev/null || true
}
