#!/usr/bin/env bash
# cc-posttool.sh — PostToolUse hook for Write|Edit|MultiEdit (§3.3 / Pitfall #8)
#
# Reads the hook JSON on stdin, best-effort formats the touched file, and
# archives large artifacts to /tmp/cc-output/<session>/ as a redundant backup
# so a later overwrite / scrollback loss cannot destroy the only copy.
#
# Contract: ALWAYS exit 0 — formatting/archival is icing, it must never block
# the tool result (原则⑥ graceful degradation). No `-e`.
set -uo pipefail

IN=$(cat)
F=$(printf '%s' "$IN" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
# MultiEdit may carry edits[] without a top-level file_path → jq returns empty → skip.
[ -z "$F" ] || [ ! -f "$F" ] && exit 0

case "$F" in
  # .md deliberately excluded: avoid prettier rewriting SKILL.md / references
  # against the repo's own style.
  *.ts|*.tsx|*.js|*.jsx|*.json|*.css)
        command -v prettier >/dev/null 2>&1 && prettier --write "$F" >/dev/null 2>&1 ;;
  *.py)  command -v ruff >/dev/null 2>&1 && { ruff format "$F" >/dev/null 2>&1; ruff check --fix "$F" >/dev/null 2>&1; } ;;
  *.go)  command -v gofmt >/dev/null 2>&1 && gofmt -w "$F" >/dev/null 2>&1 ;;
  *.sh)  command -v shfmt >/dev/null 2>&1 && shfmt -w "$F" >/dev/null 2>&1 ;;
esac

# Large-artifact archival (applies to ANY extension, incl. .md — only formatting
# is extension-gated). $$ suffix guards against same-second overwrite.
SIZE=$(wc -c < "$F" 2>/dev/null | tr -d ' ')
SESS="${CLAUDE_SESSION_ID:-unknown}"
if [ "${SIZE:-0}" -gt 8192 ]; then
  AD="${CC_OUTPUT_ROOT:-/tmp/cc-output}/${SESS}"
  mkdir -p "$AD" 2>/dev/null
  cp "$F" "$AD/$(basename "$F").$(date +%s).$$" 2>/dev/null || true
fi
exit 0
