# cc-monitor set -u + CJK parameter expansion pitfall

## Trigger

Use when `cc-monitor.sh` crashes in the status fast path with an error shaped like:

```text
line 109: HLT�: unbound variable
```

or any shell script under `set -euo pipefail` crashes with a strange variable name ending in mojibake around CJK punctuation.

## Root cause

Bash parameter expansion can misparse an unbraced variable inside an alternate-value expansion when it is adjacent to multibyte/CJK punctuation.

Bad pattern observed in `cc-monitor.sh`:

```bash
${HLT:+（last_tool=$HLT）}
```

Under `set -u`, Bash treated the inner `$HLT` plus following full-width `）` bytes as a different variable name (`HLT�`), causing an unbound-variable abort even though `HLT` was set.

## Fix pattern

Always brace variables inside nested/alternate parameter expansions, especially near non-ASCII punctuation:

```bash
${HLT:+（last_tool=${HLT}）}
```

General rule:

```bash
${VAR:+text ${VAR} text}
${VAR:-default containing ${OTHER}}
```

## Test pattern

A regression test must check all three things, not only parsed state from stderr:

1. command exit code is `0`;
2. stdout contains the expected substituted text, e.g. `last_tool=Write`;
3. stderr does **not** contain `unbound variable`.

The previous false-green test only grepped `META state=COMPLETED` from stderr and ignored the non-zero exit caused after `persist()`. That let the monitor crash while tests still appeared green.

## Session evidence

During an R4c real smoke test, `cc-monitor.sh` crashed while CC itself was healthy. The correct operational response was to fallback to `tmux capture-pane`, report "monitor failed, judging from pane evidence", and then fix `cc-monitor.sh` with a red-green test.
