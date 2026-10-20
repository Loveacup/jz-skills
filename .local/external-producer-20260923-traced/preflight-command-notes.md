# Command accounting

`commands.jsonl` is the exact argv/time/exit/stdout/stderr record for capture.py subprocesses and the Git executable-configuration probe. `capture.py` preserves the exact snapshot implementation. Shell/tool exploratory calls before the command recorder existed are retained in the Orca/Codex session, not copied wholesale here. This bundle is not a complete raw command transcript; checklist COMMANDS-01 is BLOCKED.

Exploratory command sequence (read-only; no scenario invocation):

1. `pwd`; `cat CLAUDE.md`; read trace contract and orchestration/orca-cli SKILL.md; `rg -n 'call-omp|probe' /Users/alexcai/.codex/memories/MEMORY.md`.
2. `command -v orca qmd`; read only ORCA_CLI_COMMAND and ORCA_DEV_REPO_ROOT presence/value (both unset); read coordinator baseline and governance AGENTS.md; `rg --files hermes/call-omp`; `cat .git`. Baseline tool output was truncated; subsequent Python parses selected keys instead.
3. `orca skills get orchestration`; `qmd search 'call-omp trace' -n 3`; Python parsed baseline key names.
4. `orca orchestration check --terminal term_6d7bc890-d51e-43c6-978d-83946b1ebe8d --json`; `sed -n '1,230p' hermes/call-omp/scripts/omp-send.sh`; `sed -n '1,180p' hermes/call-omp/tests/test_execute_lifecycle.py`; `/usr/bin/id -u`; erroneous `/usr/bin/dtrace -l -n 'syscall::open*:entry'`; `/usr/bin/csrutil status`.
5. Correct `/usr/sbin/dtrace -l -n 'syscall::open*:entry'`; `command -v fs_usage dtruss opensnoop vmmap`; Python read local/global Git config scanning dangerous settings; `sed -n '1,140p' hermes/call-omp/scripts/lib/omp-lib.sh`; `rg -n 'OMP_BIN|no-extensions|no-session|no-skills' hermes/call-omp/scripts/omp-send.sh`.
6. Dispatched `orca orchestration ask` with supplied task capability, question about failed observer/baseline gaps and whether to record blocked receipts; returned direction preserved separately. The capability value is intentionally not reproduced here.
7. Coordinator checks at natural checkpoints; Python inspected output directory nonexistence and Git config; created private output root and capture.py with apply_patch.
8. `python3 .local/external-producer-20260923-traced/capture.py producer-initial`; same script `probe`; read ask response; read probe records/hook filenames.
9. Exact Git config scan in commands.jsonl; bound pre-commit bytes; generated git-preflight.json.
10. `python3 .local/external-producer-20260923-traced/capture.py producer-final`; Python generated baseline comparison, direction, three receipts and checklist; apply_patch wrote report and these notes.
11. Final Python readback verifies JSON, count/HEAD/source identity assertions, private modes and file hashes; final Orca inbox check and exactly one worker_done with outcome failed.

All inline Python writes target only this evidence root. No Git status/commit or OMP invocation occurred. Final lifecycle send remains in Orca's durable run record; this document does not pre-claim delivery success.
