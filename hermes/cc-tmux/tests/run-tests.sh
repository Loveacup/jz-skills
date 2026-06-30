#!/usr/bin/env bash
# run-tests.sh — cc-tmux unified test runner
# Aggregates all test-*.sh suites, reports PASS/FAIL at both assertion and file-exit-code level.
# Exit codes: 0 = all passed, 1 = ≥1 failure.

set -euo pipefail
cd "$(dirname "$0")"

FILES_PASS=0 FILES_FAIL=0
ASSERTS_PASS=0 ASSERTS_FAIL=0

echo "cc-tmux test runner — $(date)"
echo "================================"
echo ""

for t in test-*.sh; do
  out=$(bash "$t" 2>&1) && rc=$? || rc=$?
  # Extract assertion counts from "Results: N/M passed" or "N passed"
  ap=$(echo "$out" | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '[0-9]+' || echo "?")
  af=$(echo "$out" | grep -oE '[0-9]+ failed' | tail -1 | grep -oE '[0-9]+' || echo "0")
  [[ "$ap" == "?" ]] && ap="?"
  [[ "$af" == "?" ]] && af="0"

  if [[ "$rc" -eq 0 ]]; then
    echo "✅ $t — $ap passed"
    FILES_PASS=$((FILES_PASS + 1))
    [[ "$ap" =~ ^[0-9]+$ ]] && ASSERTS_PASS=$((ASSERTS_PASS + ap))
  else
    echo "❌ $t — exit=$rc, $ap passed, $af failed"
    FILES_FAIL=$((FILES_FAIL + 1))
    [[ "$ap" =~ ^[0-9]+$ ]] && ASSERTS_PASS=$((ASSERTS_PASS + ap))
    # Show tail on failure
    echo "   tail: $(echo "$out" | tail -3 | tr '\n' ' ')"
  fi
done

echo ""
echo "================================"
echo "Files:   $FILES_PASS passed, $FILES_FAIL failed"
echo "Asserts: $ASSERTS_PASS passed, $ASSERTS_FAIL failed"
echo ""

if [[ "$FILES_FAIL" -eq 0 ]]; then
  echo "✅ ALL $FILES_PASS/$FILES_PASS files passed"
  exit 0
else
  echo "❌ $FILES_FAIL file(s) failed"
  exit 1
fi
