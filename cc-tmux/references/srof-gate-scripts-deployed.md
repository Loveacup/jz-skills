# SROF Gate Scripts Deployed (2026-06-28)

SROF v1.1 reference implementation has been deployed as working shell scripts.
This implements the `scripts/gate/` architecture described in cc-tmux §5.5.

## Shared Library (`$SROF_LIB` = `jz-skills/shared/srof/lib/`)

Matrix-independent — zero tmux/iii/Hermes coupling. On 2nd consumer → promote to independent skill.

| Script | Lines | Gate Family | Key Primitives |
|--------|-------|-------------|----------------|
| `gate-check.sh` | 68 | precondition + class-(a) re-query | `command_exists`, `env_exists`, `file_exists`, `version_gte`, `port_free`, `http_ok`, `status_json`, `lock_free` |
| `gate-verify.sh` | 41 | class-(b) last-result | `exit_code:N`, `result_json:.path==value` — reads `$SROF_RUN_RESULT` |
| `gate-danger.sh` | 40 | safety (only `block` emitter) | `remote_delete`, `rm_rf`, `force_push`, `kill_pane` |
| `gate-counter.sh` | 25 | measurement | `retries:STEP`, `sessions_active`, `age_seconds:FILE` |
| `srof-run.sh` | 29 | actuator-runner | Runs `run:`, writes `$SROF_RUN_RESULT` atomically |
| `srof-lock` | 24 | build-time | `setup.yaml` → `setup.lock.json` + `source_sha256` (yq→jq projection) |

## Skill-Local (cc-tmux)

| Script | Lines | Role |
|--------|-------|------|
| `scripts/gate/setup.sh` | 145 | Headless degraded-mode engine (`--auto`). Full prereq phase + retry-to-policy + halt-on-broken-gate + BLOCKED_ON_INPUT persistence + §5.5 state write |

## Verification (2026-06-28)

All 7 scripts pass `bash -n` syntax check.
Smoke-tested pipeline confirms the P0-1 contract closure:

```
$ gate-check.sh command_exists:bash     → {"verdict":"pass"}
$ gate-danger.sh rm_rf:/etc             → {"verdict":"block","authority":"human"}
$ srof-run.sh test-step -c 'echo ok'    → writes $SROF_RUN_RESULT
$ gate-verify.sh exit_code:0            → {"verdict":"pass"}
```

## GitHub

Commit `8602c01` — `jz-skills/shared/srof/lib/` + `hermes/cc-tmux/scripts/gate/setup.sh`

## Relation to cc-tmux Gate Architecture

These gates fulfill cc-tmux §5.5's design: "matrix-independent, zero tmux coupling, on 2nd consumer → promote to independent skill." The gate scripts referenced in the Audit section (§5.0-5.5) now have real implementations:

- `gate-verify.sh` — objective verification (commands/exit codes/artifacts)
- `gate-danger.sh` — dangerous operation interception
- `gate-counter.sh` — termination counter (discussion rounds/rejection rounds)

Note: cc-tmux's existing `scripts/gate/` directory may also contain local wrappers that delegate to `$SROF_LIB`. The library scripts themselves are the canonical implementations.
