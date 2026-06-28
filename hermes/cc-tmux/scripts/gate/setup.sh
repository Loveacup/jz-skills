#!/usr/bin/env bash
# setup.sh --auto — HEADLESS provisioning runner = DEGRADED-MODE ENGINE SUBSTITUTE (§3.4).
# With no LLM in the loop, this script inherits the engine's duties: prerequisite phase,
# retry-to-policy, safe-default-on-broken-gate, persisted BLOCKED_ON_INPUT, and the full
# §5.5 state write. §1.2's "scripts are only sensors/actuators" is relaxed HERE BY
# CONSTRUCTION and bounded to this one file.
# Usage: setup.sh --auto
# Location: $SKILL_DIR/scripts/setup.sh (skill-local)
set -uo pipefail

[ "${1:-}" = "--auto" ] || { echo '{"error":"headless-only; interactive setup is LLM-driven (§3.3)"}'; exit 2; }

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"; SKILL="$(basename "$SKILL_DIR")"
YAML="$SKILL_DIR/setup.yaml"; LOCK_JSON="$SKILL_DIR/setup.lock.json"; STATE="$SKILL_DIR/.state/provisioning.json"
RUNROOT="${XDG_RUNTIME_DIR:-/tmp}/srof/$SKILL"
export SROF_RUN_RESULT="$RUNROOT/result.json" SROF_RUNTIME_JSON="$RUNROOT/runtime.json" SROF_SKILL="$SKILL"
: "${SROF_LIB:?set SROF_LIB}"
mkdir -p "$RUNROOT" "$SKILL_DIR/.state"

sha256() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' || sha256sum "$1" 2>/dev/null | awk '{print $1}'; }
now()     { date -u +%FT%TZ; }
write_state() { local tmp="$STATE.tmp.$$"; printf '%s\n' "$1" > "$tmp"; mv -f "$tmp" "$STATE"; }   # atomic (P2-2)

# ---------- P1-4: refuse on lock/source drift ----------
if [ -f "$YAML" ]; then
  want="$(jq -r '.source_sha256 // empty' "$LOCK_JSON")"; have="$(sha256 "$YAML")"
  if [ -n "$want" ] && [ "$have" != "$want" ]; then
    write_state "$(jq -n --arg s "$SKILL" '{skill:$s,state:"BROKEN",reason:"setup.lock.json stale vs setup.yaml",fix:"regenerate with srof-lock"}')"
    echo '{"state":"BROKEN","reason":"lock drift; run srof-lock"}'; exit 23
  fi
fi

# ---------- P2-1: crash-safe provisioning lock (mkdir + PID-liveness reclaim) ----------
LOCK="$RUNROOT/provision.lock"
acquire() {
  if mkdir "$LOCK" 2>/dev/null; then echo $$ > "$LOCK/owner.pid"; return 0; fi
  local owner; owner="$(cat "$LOCK/owner.pid" 2>/dev/null)"
  if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then return 1; fi      # alive → really held
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null && { echo $$ > "$LOCK/owner.pid"; return 0; }  # dead → reclaim
  return 1
}
acquire || { echo '{"state":"PROVISIONING","reason":"another live run holds the lock"}'; exit 21; }
trap 'rm -rf "$LOCK"' EXIT

# ---------- gate caller: local→central by PRESENCE, BROKEN-aware (P0-2c) ----------
# echoes verdict; returns 0 if gate determined (exit 0), 3 if gate BROKEN (exit≠0 / non-pass/fail/block).
GATE() {  # GATE <family> <target>
  local fam="$1" tgt="$2" g out rc v
  if [ -x "$SKILL_DIR/scripts/$fam.sh" ]; then g="$SKILL_DIR/scripts/$fam.sh"; else g="$SROF_LIB/$fam.sh"; fi
  out="$("$g" "$tgt")"; rc=$?
  if [ "$rc" -ne 0 ]; then echo unknown; return 3; fi                         # broken gate (exit≠0)
  v="$(jq -r '.verdict' <<<"$out" 2>/dev/null)"
  case "$v" in pass|fail|block) echo "$v"; return 0 ;; *) echo unknown; return 3 ;; esac
}
verify_dispatch() {  # route by class (§6.5)
  case "$1" in exit_code:*|result_json:*) GATE gate-verify "$1" ;; *) GATE gate-check "$1" ;; esac
}
halt_broken() {
  write_state "$(jq -n --arg s "$SKILL" --arg r "$1" '{skill:$s,state:"BROKEN",reason:$r}')"
  printf '{"state":"BROKEN","reason":"%s"}\n' "$1"; exit 22
}
park_blocked() {  # PERSIST before exit 20 (P1-3)
  local id="$1" fix="$2" ts; ts="$(now)"
  write_state "$(jq -n --arg s "$SKILL" --arg id "$id" --arg fix "$fix" --arg ts "$ts" \
    '{skill:$s,state:"BLOCKED_ON_INPUT",need:$id,fix:$fix,since:$ts}')"
  printf '{"state":"BLOCKED_ON_INPUT","need":"%s","fix":"%s","since":"%s"}\n' "$id" "$fix" "$ts"; exit 20
}
# headless secret seeding: env → vault → (else fail). Writes umask-077 file, echoes its PATH (§3.7, P2-4).
seed_secret() {  # seed_secret <step-json> ; echoes path on success, returns 1 otherwise
  local sj="$1" envvar key f val
  envvar="$(jq -r '.input.env // empty' <<<"$sj")"; key="$(jq -r '.input.key // .id' <<<"$sj")"
  f="$(umask 077; mktemp "$RUNROOT/secret.XXXXXX")"
  if [ -n "$envvar" ] && [ -n "${!envvar:-}" ]; then printf '%s' "${!envvar}" > "$f"; echo "$f"; return 0; fi
  if [ -n "${SROF_VAULT_GET:-}" ] && val="$("$SROF_VAULT_GET" "$key" 2>/dev/null)" && [ -n "$val" ]; then
    printf '%s' "$val" > "$f"; echo "$f"; return 0; fi
  rm -f "$f"; return 1
}

# ---------- (a) PREREQUISITE PHASE (P0-2a) ----------
for i in $(seq 0 $(( $(jq '.prerequisites|length' "$LOCK_JSON") - 1 ))); do
  chk="$(jq -r ".prerequisites[$i].check" "$LOCK_JSON")"
  v="$(GATE gate-check "$chk")" || halt_broken "prerequisite gate broken: $chk"
  case "$v" in
    pass) : ;;
    fail) write_state "$(jq -n --arg s "$SKILL" --arg n "$chk" '{skill:$s,state:"BROKEN",reason:("prerequisite unmet: "+$n)}')"
          printf '{"state":"BROKEN","need":"%s","reason":"prerequisite unmet"}\n' "$chk"; exit 22 ;;
    *)    halt_broken "prerequisite blocked/undeterminable: $chk" ;;
  esac
done

# ---------- (b)(c) STEP LOOP with retry-to-policy + safe defaults ----------
MAXR="$(jq -r '.on_failure.max_retries // 0' "$LOCK_JSON")"     # threshold from DATA (P0-2b, §4.3)
declare -a DONE
for i in $(seq 0 $(( $(jq '.steps|length' "$LOCK_JSON") - 1 ))); do
  step="$(jq -c ".steps[$i]" "$LOCK_JSON")"
  id="$(jq -r '.id' <<<"$step")"; kind="$(jq -r '.kind' <<<"$step")"
  when="$(jq -r '.when // empty' <<<"$step")"; verify="$(jq -r '.verify // empty' <<<"$step")"
  run="$(jq -r '.run // empty' <<<"$step")"

  # idempotency guard: when PASS → skip, FAIL → run, broken → halt (P1-1 + P0-2c)
  if [ -n "$when" ]; then
    wv="$(GATE gate-check "$when")" || halt_broken "when-gate broken on '$id': $when"
    if [ "$wv" = pass ]; then DONE+=("$id"); continue; fi
  fi

  # headless cannot satisfy human steps it can't seed → PERSIST + park (P1-3)
  case "$kind" in
    auto) : ;;
    input)
      if seeded="$(seed_secret "$step")"; then export SROF_INPUT_FILE="$seeded"
      else park_blocked "$id" "run interactively, or seed env/SROF_VAULT_GET, then re-enter"; fi ;;
    confirm) park_blocked "$id" "needs human authorization; run interactively" ;;
    *) halt_broken "unknown kind '$kind' on step '$id'" ;;
  esac

  # actuate + verify, retry a FAIL up to MAXR; broken/block → halt (safe default §6.3)
  attempt=0
  while :; do
    "$SKILL_DIR/scripts/srof-run.sh" "$id" -c "$run"           # writes $SROF_RUN_RESULT (§6.8)
    if [ -z "$verify" ]; then break; fi
    vv="$(verify_dispatch "$verify")" || vv=unknown
    case "$vv" in
      pass) break ;;
      fail)
        attempt=$((attempt+1))
        rtmp="$SROF_RUNTIME_JSON.tmp.$$"
        jq -n --arg id "$id" --argjson n "$attempt" '{retries:{($id):$n}}' > "$rtmp" 2>/dev/null && mv -f "$rtmp" "$SROF_RUNTIME_JSON" 2>/dev/null || true
        [ "$attempt" -gt "$MAXR" ] && halt_broken "step '$id' failed verify after $MAXR retries" ;;
      *) halt_broken "verify broken/blocked on '$id': $verify ($vv)" ;;     # unknown|block → halt
    esac
  done
  DONE+=("$id"); unset SROF_INPUT_FILE
done

# ---------- (d) FULL §5.5 STATE WRITE incl. steps{} memoization map (P0-2d) ----------
steps_obj='{}'; ts="$(now)"
for sid in "${DONE[@]}"; do
  steps_obj="$(jq -c --arg id "$sid" --arg at "$ts" \
    '. + {($id):{status:"done",memoized:true,last_verify:"pass",at:$at}}' <<<"$steps_obj")"
done
prev="$(jq -r '.run_count // 0' "$STATE" 2>/dev/null || echo 0)"
write_state "$(jq -n --arg s "$SKILL" --arg v "$(jq -r .version "$LOCK_JSON")" --arg ts "$ts" \
  --argjson steps "$steps_obj" --argjson rc "$((prev+1))" \
  '{skill:$s,manifest_version:$v,state:"PROVISIONED",state_since:$ts,steps:$steps,run_count:$rc}')"
echo '{"state":"PROVISIONED"}'
