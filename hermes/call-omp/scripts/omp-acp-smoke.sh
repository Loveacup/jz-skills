#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# omp-acp-smoke.sh —— OD-OMP-1 ACP 真实探针（real manual probe）
#
# 【真实探针，仅产出证据】本脚本拉起 `omp acp` over stdio，发一条最小 prompt，
#   收集完整 stdio 交互、时间轴、进程信息，写入证据目录。**不改默认 ACP 通道行为、
#   不判定是否启用 ACP**——只记录真实观测。
#
# 裁决（status）三态：
#   compatible_smoke_passed     — `omp acp` 真实启动、回复有效、stderr 无严重错误
#   started_but_protocol_incompatible  — 启动但协议不符（如无 "ready" / 首消息格式错误）
#   failed_to_start_or_timeout  — 进程启动失败、崩溃或超时
#
# 证据目录输出（--out <dir>）：
#   summary.json      —— 裁决状态、耗时、字节数、退出码
#   result.md         —— 人类可读报告
#   stdin.ndjson      —— 发给 `omp acp` 的全部输入（NDJSON）
#   stdout.ndjson     —— 从 `omp acp` 收到的全部输出（NDJSON）
#   stderr.log        —— stderr 抓取（可能含进度/警告，非致命）
#   timeline.ndjson   —— 时间轴事件（spawn/stdin_sent/stdout_line/exit）
#   process.json      —— 进程元信息（omp 路径、版本、pid、退出码）
#
# 参数：
#   --out <dir>             证据目录（缺省：/tmp/omp-acp-smoke-XXXXXX）
#   --timeout <秒>          超时秒数（缺省 30）
#   --mock-pass             测试模式：伪造 compatible_smoke_passed（不启 omp）
#   --mock-incompatible     测试模式：伪造 started_but_protocol_incompatible
#   --mock-timeout          测试模式：伪造 failed_to_start_or_timeout
#   -h|--help               打印本头注
#
# 退出码： 0=compatible_smoke_passed · 2=started_but_protocol_incompatible ·
#         3=failed_to_start_or_timeout · 1=参数错误或内部异常
# ─────────────────────────────────────────────────────────────────
set -uo pipefail

TIMEOUT=30; OUT=""; MOCK=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)      OUT="${2:-}"; shift 2 ;;
    --timeout)  TIMEOUT="${2:-30}"; shift 2 ;;
    --mock-pass)         MOCK="pass"; shift ;;
    --mock-incompatible) MOCK="incompatible"; shift ;;
    --mock-timeout)      MOCK="timeout"; shift ;;
    -h|--help)  sed -n '2,35p' "$0"; exit 0 ;;
    *) echo "omp-acp-smoke: 未知参数 $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$OUT" ]]; then
  OUT="$(mktemp -d "${TMPDIR:-/tmp}/omp-acp-smoke.XXXXXX")" || { echo "omp-acp-smoke: 无法建临时 --out" >&2; exit 1; }
fi
mkdir -p "$OUT" || { echo "omp-acp-smoke: 无法创建 --out '$OUT'" >&2; exit 1; }
OUT="$(cd "$OUT" && pwd)"

STDIN_F="$OUT/stdin.ndjson"
STDOUT_F="$OUT/stdout.ndjson"
STDERR_F="$OUT/stderr.log"
TIMELINE_F="$OUT/timeline.ndjson"
PROCESS_F="$OUT/process.json"
SUMMARY_F="$OUT/summary.json"
RESULT_F="$OUT/result.md"

> "$STDIN_F"; > "$STDOUT_F"; > "$STDERR_F"; > "$TIMELINE_F"; > "$PROCESS_F"; > "$SUMMARY_F"; > "$RESULT_F"

timeline() { printf '{"ts":%d,"event":"%s"%s}\n' "$(date +%s)" "$1" "${2:+,$2}" >> "$TIMELINE_F"; }

# ── Mock 模式（零 token 测试路径）─────────────────────────────────
if [[ -n "$MOCK" ]]; then
  timeline "mock_mode_entered" "\"mock\":\"$MOCK\""
  OMP_VER="mock-v16.3.2"; OMP_PATH="/mock/omp"
  STATUS=""; RC=0
  case "$MOCK" in
    pass)
      STATUS="compatible_smoke_passed"; REASON="mock_pass"
      INIT=true; SESS=true; PROMPT=true
      echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1}}' > "$STDIN_F"
      printf '%s\n' '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":1,"agentInfo":{"name":"mock-omp"}}}' '{"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"mock","update":{"type":"message","content":"smoke-ok"}}}' > "$STDOUT_F"
      echo "mock stderr: no errors" > "$STDERR_F"
      RC=0
      ;;
    incompatible)
      STATUS="started_but_protocol_incompatible"; REASON="mock_incompatible"
      INIT=false; SESS=false; PROMPT=false
      echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1}}' > "$STDIN_F"
      echo '{"unknown_protocol":"old_acp_version"}' > "$STDOUT_F"
      echo "mock stderr: incompatible protocol" > "$STDERR_F"
      RC=2
      ;;
    timeout)
      STATUS="failed_to_start_or_timeout"; REASON="mock_timeout"
      INIT=false; SESS=false; PROMPT=false
      echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1}}' > "$STDIN_F"
      echo "mock stderr: timeout exceeded" > "$STDERR_F"
      RC=3
      ;;
  esac
  cat > "$PROCESS_F" <<JSON
{"omp_path":"$OMP_PATH","version":"$OMP_VER","pid":null,"exit_code":$RC}
JSON
  cat > "$SUMMARY_F" <<JSON
{"status":"$STATUS","reason":"$REASON","initialize_ok":$INIT,"session_observed":$SESS,"prompt_or_update_observed":$PROMPT,"elapsed_sec":0,"stdin_bytes":$(wc -c < "$STDIN_F" | tr -d ' '),"stdout_bytes":$(wc -c < "$STDOUT_F" | tr -d ' '),"stderr_bytes":$(wc -c < "$STDERR_F" | tr -d ' '),"exit_code":$RC,"mock":"$MOCK"}
JSON
  cat > "$RESULT_F" <<MD
# OMP ACP Smoke — Mock 模式

**status**: $STATUS
**mock**: $MOCK
**exit_code**: $RC

证据文件已生成（mock 数据，未启动真实 omp）。
MD
  exit $RC
fi

# ── 真实模式：查找 omp 二进制 ────────────────────────────────────
OMP_BIN="${OMP_BIN:-}"
if [[ -z "$OMP_BIN" ]]; then
  if command -v omp >/dev/null 2>&1; then OMP_BIN="$(command -v omp)"
  elif [[ -x /opt/homebrew/bin/omp ]]; then OMP_BIN="/opt/homebrew/bin/omp"
  elif [[ -x /usr/local/bin/omp ]]; then OMP_BIN="/usr/local/bin/omp"
  else
    timeline "omp_not_found"
    STATUS="failed_to_start_or_timeout"
    cat > "$SUMMARY_F" <<JSON
{"status":"$STATUS","elapsed_sec":0,"stdin_bytes":0,"stdout_bytes":0,"stderr_bytes":0,"exit_code":3,"error":"omp binary not found"}
JSON
    cat > "$RESULT_F" <<MD
# OMP ACP Smoke — 失败

**status**: $STATUS
**error**: omp 二进制未找到（尝试 PATH / /opt/homebrew/bin/omp / /usr/local/bin/omp）

无法继续探测。
MD
    exit 3
  fi
fi
[[ -x "$OMP_BIN" ]] || { echo "omp-acp-smoke: OMP_BIN='$OMP_BIN' 不可执行" >&2; exit 1; }

OMP_VER="$("$OMP_BIN" --version 2>&1 | head -1 || echo "unknown")"
timeline "omp_found" "\"path\":\"$OMP_BIN\",\"version\":\"$OMP_VER\""

# ── 准备最小 ACP JSON-RPC 序列（OD-OMP-1）────────────────────────
# 目标不是让 OMP 完成真实任务，而是记录它对最小 ACP 事件模型的真实响应。
# 若 OMP 的 ACP 方言不同，探针应产出 incompatible/failed 证据，而不是假装兼容。
cat > "$STDIN_F" <<'JSONRPC'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientInfo":{"name":"call-omp-acp-smoke","version":"0.1.0"},"capabilities":{}}}
{"jsonrpc":"2.0","method":"initialized","params":{}}
{"jsonrpc":"2.0","id":2,"method":"session/new","params":{"cwd":".","mcpServers":[]}}
{"jsonrpc":"2.0","id":3,"method":"session/prompt","params":{"sessionId":"call-omp-smoke-session","prompt":[{"type":"text","text":"Reply with exactly: smoke-ok. Do not add thinking, do not add commentary."}]}}
JSONRPC

# ── 启动 `omp acp` + 超时护栏 ─────────────────────────────────────
START_TS=$(date +%s)
timeline "omp_acp_spawn"

# 写一个 Perl 超时封装（macOS 无 timeout 命令）
TIMEOUT_WRAP=$(mktemp "${TMPDIR:-/tmp}/omp-acp-timeout.XXXXXX.pl")
cat > "$TIMEOUT_WRAP" <<'PERL'
use strict; use warnings;
my ($timeout, $cmd) = @ARGV;
$SIG{ALRM} = sub { kill 'TERM', -$$; exit 124; };
alarm $timeout;
exec @ARGV[1..$#ARGV];
PERL
chmod +x "$TIMEOUT_WRAP"

OMP_RC=0; OMP_PID=""
(
  # 向 omp acp 的 stdin 写入 prompt，stdout/stderr 分流
  perl "$TIMEOUT_WRAP" "$TIMEOUT" "$OMP_BIN" acp < "$STDIN_F" > "$STDOUT_F" 2> "$STDERR_F"
) & OMP_PID=$!

timeline "omp_acp_pid" "\"pid\":$OMP_PID"

# 等待进程结束或超时
wait $OMP_PID || OMP_RC=$?
END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))

rm -f "$TIMEOUT_WRAP"

timeline "omp_acp_exit" "\"exit_code\":$OMP_RC,\"elapsed_sec\":$ELAPSED"

cat > "$PROCESS_F" <<JSON
{"omp_path":"$OMP_BIN","version":"$OMP_VER","pid":$OMP_PID,"exit_code":$OMP_RC}
JSON

# ── 裁决状态 ──────────────────────────────────────────────────────
STDIN_BYTES=$(wc -c < "$STDIN_F" | tr -d ' ')
STDOUT_BYTES=$(wc -c < "$STDOUT_F" | tr -d ' ')
STDERR_BYTES=$(wc -c < "$STDERR_F" | tr -d ' ')

STATUS=""
FINAL_RC=0
REASON=""
INITIALIZE_OK=false
SESSION_OBSERVED=false
PROMPT_OR_UPDATE_OBSERVED=false

if grep -q '"id"[[:space:]]*:[[:space:]]*1' "$STDOUT_F" && grep -q '"protocolVersion"[[:space:]]*:[[:space:]]*1' "$STDOUT_F"; then
  INITIALIZE_OK=true
fi
if grep -qE '"method"[[:space:]]*:[[:space:]]*"session/(new|list|load|resume|close)"|"sessionId"' "$STDOUT_F"; then
  SESSION_OBSERVED=true
fi
if grep -qE '"method"[[:space:]]*:[[:space:]]*"session/update"|"id"[[:space:]]*:[[:space:]]*3|smoke-ok' "$STDOUT_F"; then
  PROMPT_OR_UPDATE_OBSERVED=true
fi

# 超时 / 非零退出
if [[ "$OMP_RC" -eq 124 ]]; then
  STATUS="failed_to_start_or_timeout"; FINAL_RC=3; REASON="timeout"
elif [[ "$OMP_RC" -ne 0 ]]; then
  STATUS="failed_to_start_or_timeout"; FINAL_RC=3; REASON="nonzero_exit"
elif [[ "$STDOUT_BYTES" -eq 0 ]]; then
  STATUS="failed_to_start_or_timeout"; FINAL_RC=3; REASON="zero_stdout"
elif [[ "$INITIALIZE_OK" == true && "$SESSION_OBSERVED" == true && "$PROMPT_OR_UPDATE_OBSERVED" == true ]]; then
  STATUS="compatible_smoke_passed"; FINAL_RC=0; REASON="initialize_session_prompt_observed"
elif [[ "$INITIALIZE_OK" == true ]]; then
  STATUS="started_but_protocol_incompatible"; FINAL_RC=2; REASON="initialize_ok_but_session_prompt_unobserved"
else
  STATUS="started_but_protocol_incompatible"; FINAL_RC=2; REASON="initialize_response_missing_or_invalid"
fi

timeline "verdict" "\"status\":\"$STATUS\",\"reason\":\"$REASON\",\"initialize_ok\":$INITIALIZE_OK,\"session_observed\":$SESSION_OBSERVED,\"prompt_or_update_observed\":$PROMPT_OR_UPDATE_OBSERVED"

# ── 写 summary.json ───────────────────────────────────────────────
cat > "$SUMMARY_F" <<JSON
{"status":"$STATUS","reason":"$REASON","initialize_ok":$INITIALIZE_OK,"session_observed":$SESSION_OBSERVED,"prompt_or_update_observed":$PROMPT_OR_UPDATE_OBSERVED,"elapsed_sec":$ELAPSED,"stdin_bytes":$STDIN_BYTES,"stdout_bytes":$STDOUT_BYTES,"stderr_bytes":$STDERR_BYTES,"exit_code":$OMP_RC}
JSON

# ── 写 result.md ──────────────────────────────────────────────────
cat > "$RESULT_F" <<MD
# OMP ACP Smoke Probe — OD-OMP-1

**status**: $STATUS
**elapsed**: ${ELAPSED}s
**omp**: $OMP_BIN
**version**: $OMP_VER
**exit_code**: $OMP_RC

## 字节数
- stdin: $STDIN_BYTES
- stdout: $STDOUT_BYTES
- stderr: $STDERR_BYTES

## 证据文件
- \`stdin.ndjson\` — 发送的 ACP prompt
- \`stdout.ndjson\` — OMP 返回的 NDJSON 流
- \`stderr.log\` — stderr 捕获
- \`timeline.ndjson\` — 时间轴事件
- \`process.json\` — 进程元信息

## 裁决说明
- **compatible_smoke_passed**: initialize / session / prompt 或 update 均有可观测响应
- **started_but_protocol_incompatible**: `omp acp` 启动并返回 JSON-RPC，但未满足完整 OD-OMP-1 序列
- **failed_to_start_or_timeout**: 进程失败、超时(${TIMEOUT}s)、或 stdout 为空

## 观测布尔
- initialize_ok: $INITIALIZE_OK
- session_observed: $SESSION_OBSERVED
- prompt_or_update_observed: $PROMPT_OR_UPDATE_OBSERVED
- reason: $REASON

---
探测完成。本探针**不改 call-omp 默认通道**，只记录真实观测。
MD

exit $FINAL_RC
