#!/bin/bash
# sync-shared.sh — Deploy shared skills to a target platform
# Usage: ./deploy/sync-hermes.sh | sync-cc.sh | sync-pi.sh
# Must be run from repo root.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# === Hermes ===
sync_hermes() {
  local base=~/.hermes/skills
  echo "→ Syncing to Hermes..."

  # Map shared skills to their Hermes category paths
  cp -r "$REPO_ROOT/shared/web-research-router"    "$base/research/"
  cp -r "$REPO_ROOT/shared/github-code-explorer"   "$base/github/"
  cp -r "$REPO_ROOT/shared/grill-with-docs"        "$base/governance/"
  cp -r "$REPO_ROOT/shared/skill-authoring"        "$base/governance/"

  # Hermes-specific skills
  cp -r "$REPO_ROOT/hermes/financial-research-agents" "$base/research/"
  cp -r "$REPO_ROOT/hermes/tradingagents"             "$base/research/"
  cp -r "$REPO_ROOT/hermes/llm-wiki"                  "$base/research/"
  cp -r "$REPO_ROOT/hermes/arxiv"                     "$base/research/"

  # Sync to all profiles
  echo "→ Syncing to profiles..."
  for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
    local pd=~/.hermes/profiles/$prof/skills
    mkdir -p "$pd/research" "$pd/github" "$pd/governance"
    cp -r "$REPO_ROOT/shared/web-research-router"    "$pd/research/"
    cp -r "$REPO_ROOT/shared/github-code-explorer"   "$pd/github/"
    cp -r "$REPO_ROOT/shared/grill-with-docs"        "$pd/governance/"
    cp -r "$REPO_ROOT/shared/skill-authoring"        "$pd/governance/"
    cp -r "$REPO_ROOT/hermes/financial-research-agents" "$pd/research/"
    cp -r "$REPO_ROOT/hermes/tradingagents"             "$pd/research/"
    cp -r "$REPO_ROOT/hermes/llm-wiki"                  "$pd/research/"
    cp -r "$REPO_ROOT/hermes/arxiv"                     "$pd/research/"
  done

  echo "  ✅ Hermes ($(ls -d ~/.hermes/profiles/*/ 2>/dev/null | wc -l | tr -d ' ') profiles)"
}

# === Claude Code ===
sync_cc() {
  local base=~/.claude/skills
  mkdir -p "$base"
  echo "→ Syncing to Claude Code..."

  cp -r "$REPO_ROOT/shared/web-research-router/SKILL.md"  "$base/web-research-router.md"
  cp -r "$REPO_ROOT/shared/github-code-explorer/SKILL.md" "$base/github-code-explorer.md"
  cp -r "$REPO_ROOT/shared/grill-with-docs/SKILL.md"      "$base/grill-with-docs.md"
  cp -r "$REPO_ROOT/shared/skill-authoring/SKILL.md"      "$base/skill-authoring.md"

  # CC-specific skills (if any in cc/)
  if [ -d "$REPO_ROOT/cc" ] && [ "$(ls -A "$REPO_ROOT/cc" 2>/dev/null)" ]; then
    for skill in "$REPO_ROOT/cc"/*/; do
      name=$(basename "$skill")
      cp -r "$skill" "$base/$name"
    done
  fi

  echo "  ✅ Claude Code"
}

# === Profile-specific skills ===
sync_profiles() {
  echo "→ Syncing profile-specific skills..."
  local pd

  # gongbu skills
  pd=~/.hermes/profiles/gongbu/skills
  [ -d "$REPO_ROOT/profiles/gongbu/disk-cleanup" ] && cp -r "$REPO_ROOT/profiles/gongbu/disk-cleanup" "$pd/"
  [ -d "$REPO_ROOT/profiles/gongbu/infra-health-check" ] && cp -r "$REPO_ROOT/profiles/gongbu/infra-health-check" "$pd/"
  [ -d "$REPO_ROOT/profiles/gongbu/infra-monitoring" ] && cp -r "$REPO_ROOT/profiles/gongbu/infra-monitoring" "$pd/"

  # jiangzuojian skills
  pd=~/.hermes/profiles/jiangzuojian/skills
  [ -d "$REPO_ROOT/profiles/jiangzuojian/delivery-gate" ] && cp -r "$REPO_ROOT/profiles/jiangzuojian/delivery-gate" "$pd/"

  # protocol skills
  pd=~/.hermes/profiles/protocol/skills
  [ -d "$REPO_ROOT/profiles/protocol/md-to-pdf" ] && cp -r "$REPO_ROOT/profiles/protocol/md-to-pdf" "$pd/"

  # tester skills
  pd=~/.hermes/profiles/tester/skills
  [ -d "$REPO_ROOT/profiles/tester/code-review-toolkit" ] && cp -r "$REPO_ROOT/profiles/tester/code-review-toolkit" "$pd/"

  echo "  ✅ Profile skills (gongbu, jiangzuojian, protocol, tester)"
}

# === pi ===
sync_pi() {
  local base="${PI_SKILLS_DIR:-~/.pi/skills}"
  mkdir -p "$base"
  echo "→ Syncing to pi ($base)..."

  cp -r "$REPO_ROOT/shared/web-research-router"  "$base/"
  cp -r "$REPO_ROOT/shared/github-code-explorer" "$base/"

  # pi-specific skills
  if [ -d "$REPO_ROOT/pi" ] && [ "$(ls -A "$REPO_ROOT/pi" 2>/dev/null)" ]; then
    for skill in "$REPO_ROOT/pi"/*/; do
      name=$(basename "$skill")
      cp -r "$skill" "$base/$name"
    done
  fi

  echo "  ✅ pi"
}

# === Main ===
case "${1:-all}" in
  hermes)
    sync_hermes
    sync_profiles
    ;;
  cc)     sync_cc ;;
  pi)     sync_pi ;;
  all)
    sync_hermes
    sync_cc
    sync_pi
    sync_profiles
    ;;
  *)
    echo "Usage: $0 {hermes|cc|pi|all}"
    exit 1
    ;;
esac
