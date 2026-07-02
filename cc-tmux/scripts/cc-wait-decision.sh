#!/usr/bin/env bash
# cc-wait-decision.sh — Hermes-facing decision wrapper around cc-wait-marker.sh
#
# Purpose:
#   cc-wait-marker.sh is a low-level primitive: wait for a turn-done marker, or
#   fail-fast with rc=4 when startup gate refuses to wait on an apparently
#   unsubmitted task. rc=4 is NOT a final verdict. This wrapper turns rc=4/rc=1
#   into a structured decision by collecting monitor, pane, freeze, and artifact
#   evidence.
#
# Usage:
#   cc-wait-decision.sh --session <tmux-session-name> [--after <unix_ts>]
#     [--timeout <secs>] [--expect <glob>]... [--diag-dir <dir>] [--pretty]
#     [--sent-line "<text>"]
#
# Exit codes (summary — see decision.state for semantics):
#   0 = marker_done | artifact_satisfied_no_marker
#   1 = wait_timeout_unresolved
#   2 = usage_error
#   3 = infra_error | session_dead
#   4 = not_started_retryable
#   5 = active_no_resend
#   6 = frozen_needs_confirm | prompt_text_needs_clear | ambiguous_manual_check

set -euo pipefail
source "$(dirname "$0")/lib/portability.sh"

SESSION="" AFTER=0 TIMEOUT=21600 DIAG_DIR="" PRETTY=0
EXPECTS=()
SENT_LINE=""

usage() {
  cat >&2 <<'EOF'
Usage: cc-wait-decision.sh --session <tmux-session-name> [--after <unix_ts>] [--timeout <secs>]
  [--expect <glob>]... [--diag-dir <dir>] [--pretty]

Wraps cc-wait-marker.sh. On wait-marker rc=4/1, collects cc-monitor,
tmux capture-pane, freeze marker, and expected artifact evidence, then emits
JSON with a Hermes action decision.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) [[ $# -ge 2 ]] || { echo "--session requires value" >&2; exit 2; }; SESSION="$2"; shift 2 ;;
    --after)   [[ $# -ge 2 ]] || { echo "--after requires value" >&2; exit 2; }; AFTER="$2"; shift 2 ;;
    --timeout) [[ $# -ge 2 ]] || { echo "--timeout requires value" >&2; exit 2; }; TIMEOUT="$2"; shift 2 ;;
    --expect)  [[ $# -ge 2 ]] || { echo "--expect requires value" >&2; exit 2; }; EXPECTS+=("$2"); shift 2 ;;
    --diag-dir) [[ $# -ge 2 ]] || { echo "--diag-dir requires value" >&2; exit 2; }; DIAG_DIR="$2"; shift 2 ;;
    --sent-line) [[ $# -ge 2 ]] || { echo "--sent-line requires value" >&2; exit 2; }; SENT_LINE="$2"; shift 2 ;;
    --pretty) PRETTY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$SESSION" ]]; then
  echo "❌ cc-wait-decision: --session is required" >&2
  usage
  exit 2
fi
[[ "$AFTER" =~ ^[0-9]+$ ]] || { echo "❌ --after must be a non-negative integer" >&2; exit 2; }
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || { echo "❌ --timeout must be a non-negative integer" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WAIT_MARKER="${CC_WAIT_DECISION_WAIT_MARKER:-$SCRIPT_DIR/cc-wait-marker.sh}"
MONITOR="${CC_WAIT_DECISION_MONITOR:-$SCRIPT_DIR/cc-monitor.sh}"
TMUX="${CC_WAIT_DECISION_TMUX:-tmux}"
TMP="${CC_WAIT_DECISION_TMPDIR:-/tmp}"
NOW="${CC_WAIT_DECISION_NOW:-$(date +%s)}"
ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
MARKER="/private/tmp/cc-turn-done-${SESSION}"
FREEZE_F="$TMP/cc-freeze-${SESSION}"
STATUS_F="$TMP/cc-status-${SESSION}.json"
HB_F="$TMP/cc-heartbeat-${SESSION}"
EXPECT_F="$TMP/cc-expect-${SESSION}"

if [[ -z "$DIAG_DIR" ]]; then
  DIAG_DIR="$(mktemp -d "${TMP%/}/cc-wait-decision-${SESSION}.XXXXXX")"
else
  mkdir -p "$DIAG_DIR"
fi
WAIT_OUT="$DIAG_DIR/wait-marker.out"
WAIT_ERR="$DIAG_DIR/wait-marker.err"
MON_OUT="$DIAG_DIR/monitor.out"
MON_ERR="$DIAG_DIR/monitor.err"
PANE_F="$DIAG_DIR/pane.txt"
ART_F="$DIAG_DIR/artifacts.tsv"
EXPECT_LIST="$DIAG_DIR/expect-patterns.txt"

# Merge explicit --expect and persisted /tmp/cc-expect-<session>.
: > "$EXPECT_LIST"
for ((i=0; i<${#EXPECTS[@]}; i++)); do printf '%s\n' "${EXPECTS[$i]}" >> "$EXPECT_LIST"; done
if [[ -f "$EXPECT_F" ]]; then
  while IFS= read -r line; do [[ -n "$line" ]] && printf '%s\n' "$line" >> "$EXPECT_LIST"; done < "$EXPECT_F"
fi

WAIT_RC=0
bash "$WAIT_MARKER" --session "$SESSION" --after "$AFTER" --timeout "$TIMEOUT" >"$WAIT_OUT" 2>"$WAIT_ERR" || WAIT_RC=$?

# Always collect bounded diagnostics for rc!=0; rc=0 gets lightweight evidence only.
MON_RC=0
if [[ "$WAIT_RC" -ne 0 ]]; then
  bash "$MONITOR" --session "$SESSION" --force-capture >"$MON_OUT" 2>"$MON_ERR" || MON_RC=$?
  "$TMUX" capture-pane -t "$SESSION" -p -S -40 >"$PANE_F" 2>/dev/null || : > "$PANE_F"
else
  : > "$MON_OUT"; : > "$MON_ERR"; : > "$PANE_F"
fi

# Artifact collection: pattern<TAB>status<TAB>path<TAB>mtime
: > "$ART_F"
while IFS= read -r pat; do
  [[ -z "$pat" ]] && continue
  matched=0
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    matched=1
    mt=$(get_mtime "$path" 2>/dev/null || echo 0)
    status="present"
    [[ "$mt" =~ ^[0-9]+$ ]] && [[ "$mt" -gt "$AFTER" ]] && status="present_newer_than_after"
    printf '%s\t%s\t%s\t%s\n' "$pat" "$status" "$path" "$mt" >> "$ART_F"
  done < <(compgen -G "$pat" 2>/dev/null || true)
  [[ "$matched" -eq 0 ]] && printf '%s\tmissing\t\t0\n' "$pat" >> "$ART_F"
done < "$EXPECT_LIST"

export SESSION AFTER TIMEOUT NOW ISO MARKER FREEZE_F STATUS_F HB_F WAIT_RC MON_RC PRETTY
export WAIT_OUT WAIT_ERR MON_OUT MON_ERR PANE_F ART_F DIAG_DIR TMP
export CC_WAIT_DECISION_SENT_LINE="$SENT_LINE"

PY_OUT=$(python3 <<'PY'
import json, os, re, sys, hashlib
from pathlib import Path

session=os.environ['SESSION']; after=int(os.environ['AFTER']); timeout=int(os.environ['TIMEOUT'])
now=int(os.environ['NOW']); wait_rc=int(os.environ['WAIT_RC']); mon_rc=int(os.environ['MON_RC'])
marker=os.environ['MARKER']; freeze_f=Path(os.environ['FREEZE_F']); status_f=Path(os.environ['STATUS_F']); hb_f=Path(os.environ['HB_F'])
wait_out=Path(os.environ['WAIT_OUT']).read_text(errors='replace') if Path(os.environ['WAIT_OUT']).exists() else ''
wait_err=Path(os.environ['WAIT_ERR']).read_text(errors='replace') if Path(os.environ['WAIT_ERR']).exists() else ''
mon_out=Path(os.environ['MON_OUT']).read_text(errors='replace') if Path(os.environ['MON_OUT']).exists() else ''
mon_err=Path(os.environ['MON_ERR']).read_text(errors='replace') if Path(os.environ['MON_ERR']).exists() else ''
pane=Path(os.environ['PANE_F']).read_text(errors='replace') if Path(os.environ['PANE_F']).exists() else ''
art_path=Path(os.environ['ART_F'])

# monitor state: prefer the just-run cc-monitor META/stdout, then fresh-ish cc-status, then heartbeat.
# Do NOT blindly prefer cc-status: cc-monitor --force-capture writes heartbeat/state-log,
# not cc-status, so cc-status can be stale and would cause false active_no_resend.
monitor_state='unknown'; heartbeat_age=None; freeze=freeze_f.exists()
if monitor_state == 'unknown':
    m=re.search(r'state=([A-Z_]+)', mon_err)
    if m: monitor_state=m.group(1)
if monitor_state == 'unknown':
    m=re.search(r'状态权威: ([A-Z_]+)', mon_out)
    if m: monitor_state=m.group(1)
if monitor_state == 'unknown' and status_f.exists():
    try:
        status_age = now - int(status_f.stat().st_mtime)
        if status_age <= int(os.environ.get('CC_WAIT_DECISION_STATUS_MAX_AGE', '20')):
            d=json.loads(status_f.read_text(errors='replace'))
            monitor_state=d.get('state') or monitor_state
    except Exception:
        pass
if monitor_state == 'unknown' and hb_f.exists():
    try:
        parts=hb_f.read_text(errors='replace').split('|')
        if len(parts) >= 3:
            monitor_state=parts[2] or monitor_state
            heartbeat_age=max(0, now-int(parts[0])) if parts[0].isdigit() else None
    except Exception:
        pass
# Pane signals + prompt classification (v1.40: additive prompt signals).
signals=[]
P_SENT=os.environ.get('CC_WAIT_DECISION_SENT_LINE', '').strip()
active_re=re.compile(r'(esc to interrupt|Thinking|Reading|Edit|Write|Tool|Spelunking|⏺|●|✻|✳|✶|✢|✽)')
if 'Press up to edit queued' in pane: signals.append('queue')
lines=[ln for ln in pane.splitlines() if ln.strip()]
prompt_lines=[ln for ln in lines[-6:] if '❯' in ln]
residual=False; clean_idle=False
prompt_kind='none'; prompt_text=''; safe_to_submit=False; matched_sent_line=False

def normalize_msg(s):
    s=s.replace('\u00a0', ' ')
    s=re.sub(r'[│╎┃|]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def path_anchor(s):
    m=re.search(r'(/private/tmp|/tmp|/Users/\S+|\.{1,2}/)\S+', s)
    return m.group(0) if m else ''

def lead_before_anchor(s, anchor):
    before=s.split(anchor, 1)[0] if anchor else ''
    parts=normalize_msg(before).split()
    return ' '.join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else '')

def is_fresh_sent_line(content, sent):
    if not content or not sent:
        return False
    c=normalize_msg(content)
    s=normalize_msg(sent)
    if c == s:
        return True
    anchor=path_anchor(s)
    if not anchor or anchor not in c:
        return False
    lead=lead_before_anchor(s, anchor)
    if not lead:
        return False
    return re.search(r'(^|\s)' + re.escape(lead) + r'(\s|$)', c, re.IGNORECASE) is not None

if prompt_lines:
    tail_window=lines[-6:]
    prompt_idx=max(i for i, ln in enumerate(tail_window) if '❯' in ln)
    prompt_block=tail_window[prompt_idx:]
    prompt_block[0]=re.sub(r'^[\s│╎┃|]*❯\s*', '', prompt_block[0]).strip(' │╎┃|')
    # Empty prompt is consumed/idle. Do not append later tty echo as wrapped text.
    if prompt_block[0]:
        content='\n'.join(prompt_block).strip(' │╎┃|')
    else:
        content=''
    if content:
        residual=True; signals.append('prompt_text_present'); prompt_text=content
        # v1.40: classify prompt text
        if is_fresh_sent_line(content, P_SENT):
            prompt_kind='fresh_sent_line'
            matched_sent_line=True; safe_to_submit=True
            signals.append('prompt_text_fresh_sent_line')
        elif content.strip():
            # Heuristic: text containing typical CC-prediction patterns (/command, file paths, task-continuation)
            prediction_heuristic = bool(re.search(r'^/[a-z]|^(read|read|analyze|review|check|fix|implement|update|create|write|generate|run|test|deploy|commit|push|continue)\b', content, re.IGNORECASE))
            if prediction_heuristic:
                prompt_kind='prediction_candidate'
                signals.append('prompt_text_prediction_candidate')
            else:
                prompt_kind='stale_or_unknown'
                signals.append('prompt_text_stale_or_unknown')
            safe_to_submit=False
        else:
            prompt_kind='stale_or_unknown'; signals.append('prompt_text_stale_or_unknown'); safe_to_submit=False
    else:
        clean_idle=True; signals.append('idle_prompt'); prompt_kind='empty'
if not prompt_lines:
    prompt_kind='none'
if active_re.search('\n'.join(lines[-8:])):
    if clean_idle:
        signals.append('old_scrollback_active_ignored')
    else:
        signals.append('active_pane')
# Prompt sub-object for v2 schema
prompt_obj={
    'present': bool(prompt_lines),
    'text_excerpt': prompt_text[:200] if prompt_text else '',
    'text_hash': hashlib.sha256(prompt_text.encode()).hexdigest()[:16] if prompt_text else '',
    'kind': prompt_kind,
    'safe_to_submit': safe_to_submit,
    'matched_sent_line': matched_sent_line
}

artifacts=[]; all_newer=False; any_newer=False; any_missing=False
if art_path.exists() and art_path.stat().st_size:
    grouped={}
    for line in art_path.read_text(errors='replace').splitlines():
        pat,status,path,mtime=(line.split('\t')+['','','',''])[:4]
        g=grouped.setdefault(pat, {'pattern':pat, 'matches':[], 'status':'missing'})
        if status == 'missing':
            any_missing=True
        else:
            m={'path':path, 'mtime':int(mtime) if str(mtime).isdigit() else 0}
            g['matches'].append(m)
            if status == 'present_newer_than_after':
                any_newer=True; g['status']='present_newer_than_after'
            elif g['status'] == 'missing':
                g['status']='present'
    artifacts=list(grouped.values())
    all_newer=bool(artifacts) and all(a['status']=='present_newer_than_after' for a in artifacts)

active_states={'TOOL','THINKING','WAITING_AGENTS','ACTIVE','ACTIVE_HOOK','RECEIVED','COMPACTING','STARTING','BLOCKED'}
terminal_states={'GONE','SHELL','ERROR'}

state='ambiguous_manual_check'; action='manual_check'; exit_code=6; safe=False; terminal=False; reason='default_ambiguous'
S_SUBMIT=safe_to_submit; S_RESEND=False
if wait_rc == 0:
    state='marker_done'; action='read_marker_and_artifacts'; exit_code=0; safe=False; terminal=True; reason='wait_marker_rc0'
elif wait_rc == 2:
    state='usage_error'; action='fix_arguments'; exit_code=2; terminal=True; reason='wait_marker_usage_error'
elif freeze:
    state='frozen_needs_confirm'; action='ask_before_interrupt'; exit_code=6; terminal=False; reason='freeze_marker_exists'
elif all_newer:
    state='artifact_satisfied_no_marker'; action='read_artifacts'; exit_code=0; terminal=True; reason='all_expected_artifacts_newer_than_after'
elif monitor_state in terminal_states:
    state='session_dead'; action='inspect_or_finish'; exit_code=3; terminal=True; reason=f'monitor_state={monitor_state}'
elif monitor_state in active_states or ('active_pane' in signals and not clean_idle and not residual and 'queue' not in signals):
    state='active_no_resend'; action='monitor_and_check_artifacts'; exit_code=5; terminal=False; reason=f'monitor_state={monitor_state}' if monitor_state!='unknown' else 'pane_active_signal'
elif 'queue' in signals:
    state='not_started_retryable'; action='escape_clear_then_resend_single_line'; exit_code=4; safe=True; terminal=False; reason='queue_banner'
elif residual:
    # v1.40: prompt text classification
    if matched_sent_line:
        state='not_started_retryable'; action='clear_or_auto_enter_only_if_fresh_task_line'; exit_code=4; safe=True; terminal=False; reason='fresh_sent_line_residual'
        S_RESEND=True
    else:
        state='prompt_text_needs_clear'; action='clear_prompt_or_manual_confirm'; exit_code=6; terminal=False; reason=f'prompt_text_{prompt_kind}'
elif clean_idle and wait_rc == 4:
    state='not_started_retryable'; action='resend_path_only_instruction'; exit_code=4; safe=True; terminal=False; reason='clean_idle_no_artifact_progress'
    S_RESEND=True
elif wait_rc == 1:
    state='wait_timeout_unresolved'; action='manual_check_or_continue_monitor'; exit_code=1; terminal=False; reason='timeout_no_active_evidence'
elif wait_rc in (3,127):
    state='infra_error'; action='inspect_tooling'; exit_code=3; terminal=True; reason=f'wait_marker_rc={wait_rc}'
elif wait_rc == 4:
    state='not_started_retryable'; action='manual_check_then_resend_if_clean'; exit_code=4; safe=True; terminal=False; reason='startup_gate_no_active_evidence'
    S_RESEND=True

obj={
  'schema':'cc-wait-decision.v2',
  'session':session,
  'timestamp':os.environ['ISO'],
  'after':after,
  'timeout':timeout,
  'diag_dir':os.environ['DIAG_DIR'],
  'wait_marker':{
    'exit_code':wait_rc,
    'marker_path':marker,
    'stdout': wait_out[-4000:],
    'stderr_summary': ' | '.join([ln.strip() for ln in wait_err.splitlines() if ln.strip()])[-1200:]
  },
  'decision':{
    'state':state,
    'action':action,
    'safe_to_resend':S_RESEND,
    'safe_to_submit_prompt':S_SUBMIT,
    'terminal':terminal,
    'reason':reason
  },
  'monitor':{
    'exit_code':mon_rc,
    'state':monitor_state,
    'heartbeat_age_s':heartbeat_age,
    'freeze':freeze
  },
  'pane':{
    'signals':sorted(set(signals)),
    'prompt':prompt_obj,
    'tail_excerpt':'\n'.join(lines[-12:])[-2000:]
  },
  'artifacts':artifacts
}
print(json.dumps(obj, ensure_ascii=False, indent=2 if os.environ.get('PRETTY') == '1' else None))
print(f'__EXIT_CODE__={exit_code}', file=sys.stderr)
PY
)

printf '%s\n' "$PY_OUT"
# Recompute exit from the emitted JSON in a tiny, explicit way (avoid parsing stderr).
EXIT_CODE=$(printf '%s' "$PY_OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); s=d["decision"]["state"]; print({"marker_done":0,"artifact_satisfied_no_marker":0,"wait_timeout_unresolved":1,"usage_error":2,"infra_error":3,"session_dead":3,"not_started_retryable":4,"active_no_resend":5,"frozen_needs_confirm":6,"ambiguous_manual_check":6,"prompt_text_needs_clear":6}.get(s,6))')
exit "$EXIT_CODE"
