#!/usr/bin/env bash
# lib/portability.sh — cross-platform portability helpers for cc-tmux
#
# Zero-dependency, bash 3.2+ compatible. Source this in any script that
# needs mtime or other platform-sensitive operations.
#
# Usage:
#   source "$(dirname "$0")/lib/portability.sh"
#   mtime=$(get_mtime "/tmp/some-file")

# ── get_mtime ────────────────────────────────────────────────────────
# Returns the mtime (Unix epoch seconds) of a file, or 0 if the file
# does not exist or the mtime cannot be determined on any platform.
#
# Fallback chain: macOS/BSD stat → Linux/GNU stat → Perl → 0
get_mtime() {
  local f="$1"
  [[ ! -f "$f" ]] && { echo "0"; return 0; }
  local m
  # macOS / BSD
  m=$(stat -f %m "$f" 2>/dev/null) && { echo "$m"; return 0; }
  # Linux / GNU
  m=$(stat -c %Y "$f" 2>/dev/null) && { echo "$m"; return 0; }
  # Perl (any Unix — ultimate fallback)
  m=$(perl -e 'print((stat($ARGV[0]))[9])' "$f" 2>/dev/null) && { echo "$m"; return 0; }
  echo "0"
}
