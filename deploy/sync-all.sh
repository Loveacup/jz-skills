#!/bin/bash
# sync-all.sh — Deploy jz-skills to Hermes / Claude Code / pi
# Usage: ./deploy/sync-all.sh {hermes|cc|pi|all}
# Must be run from repo root.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# === Hermes ===
sync_hermes() {
  local base=~/.hermes/skills
  echo "→ Syncing to Hermes..."

  # Shared (cross-platform) skills
  mkdir -p "$base/governance" "$base/productivity"
  cp -r "$REPO_ROOT/shared/grill-with-docs"        "$base/governance/"
  cp -r "$REPO_ROOT/shared/skill-authoring"        "$base/governance/"
  cp -r "$REPO_ROOT/shared/pdf"                    "$base/productivity/"
  cp -r "$REPO_ROOT/shared/strategic-insight-longform"  "$base/productivity/"
  cp -r "$REPO_ROOT/shared/voice-to-markdown-workflow"  "$base/productivity/"
  cp -r "$REPO_ROOT/shared/github/"                   "$base/github/"
  cp -r "$REPO_ROOT/shared/xhs-tech-writer"    "$base/hermes/"

  # Hermes-specific skills
  mkdir -p "$base/research" "$base/productivity" "$base/governance" "$base/autonomous-ai-agents" "$base/devops" "$base/apple" "$base/hermes"
  cp -r "$REPO_ROOT/hermes/web-research-router"             "$base/research/"
  cp -r "$REPO_ROOT/hermes/source-verification"            "$base/research/"
  cp -r "$REPO_ROOT/hermes/tradingagents"                   "$base/research/"

  cp -r "$REPO_ROOT/hermes/arxiv"                           "$base/research/"
  cp -r "$REPO_ROOT/hermes/auto-diary"                      "$base/"
  cp -r "$REPO_ROOT/hermes/bilibili-video-analyzer"         "$base/"
  cp -r "$REPO_ROOT/hermes/xhs-crawler"                     "$base/"
  cp -r "$REPO_ROOT/hermes/calendar-manager"               "$base/"
  cp -r "$REPO_ROOT/hermes/cron-worker"                    "$base/"
  cp -r "$REPO_ROOT/hermes/de-slop"                        "$base/"
  cp -r "$REPO_ROOT/hermes/claude-code"                    "$base/autonomous-ai-agents/"
  cp -r "$REPO_ROOT/hermes/supermemory-hermes"              "$base/governance/"
  cp -r "$REPO_ROOT/hermes/mac-doctor"                     "$base/apple/"
  cp -r "$REPO_ROOT/hermes/tts-manager"                    "$base/hermes/"
  cp -r "$REPO_ROOT/hermes/tech-support-email"             "$base/hermes/"
  cp -r "$REPO_ROOT/hermes/news-assembly"                  "$base/productivity/"
  cp -r "$REPO_ROOT/hermes/morning-news-briefing"           "$base/productivity/"

  # Sync to all profiles
  echo "→ Syncing to profiles..."
  for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
    local pd=~/.hermes/profiles/$prof/skills
    mkdir -p "$pd/research" "$pd/github" "$pd/governance" "$pd/productivity" "$pd/autonomous-ai-agents" "$pd/apple" "$pd/hermes"
    cp -r "$REPO_ROOT/shared/grill-with-docs"        "$pd/governance/"
    cp -r "$REPO_ROOT/shared/skill-authoring"        "$pd/governance/"
    cp -r "$REPO_ROOT/shared/github/"                "$pd/github/"
    cp -r "$REPO_ROOT/shared/xhs-tech-writer"        "$pd/hermes/"
    cp -r "$REPO_ROOT/hermes/web-research-router"             "$pd/research/"
    cp -r "$REPO_ROOT/hermes/source-verification"            "$pd/research/"
    cp -r "$REPO_ROOT/hermes/tradingagents"                   "$pd/research/"
    cp -r "$REPO_ROOT/hermes/arxiv"                           "$pd/research/"
    cp -r "$REPO_ROOT/hermes/calendar-manager"               "$pd/"
    cp -r "$REPO_ROOT/hermes/cron-worker"                    "$pd/"
    cp -r "$REPO_ROOT/hermes/de-slop"                        "$pd/"
    cp -r "$REPO_ROOT/hermes/claude-code"                    "$pd/autonomous-ai-agents/"
    cp -r "$REPO_ROOT/hermes/supermemory-hermes"              "$pd/governance/"
    cp -r "$REPO_ROOT/hermes/mac-doctor"                     "$pd/apple/"
    cp -r "$REPO_ROOT/hermes/tts-manager"                    "$pd/hermes/"
    cp -r "$REPO_ROOT/hermes/tech-support-email"             "$pd/hermes/"
    cp -r "$REPO_ROOT/hermes/news-assembly"                  "$pd/productivity/"
    cp -r "$REPO_ROOT/hermes/morning-news-briefing"           "$pd/productivity/"
  done

  echo "  ✅ Hermes ($(ls -d ~/.hermes/profiles/*/ 2>/dev/null | wc -l | tr -d ' ') profiles)"
}

# === Claude Code ===
sync_cc() {
  local base=~/.claude/skills
  mkdir -p "$base"
  echo "→ Syncing to Claude Code..."

  cp -r "$REPO_ROOT/shared/grill-with-docs/SKILL.md"      "$base/grill-with-docs.md"
  cp -r "$REPO_ROOT/shared/skill-authoring/SKILL.md"      "$base/skill-authoring.md"

  if [ -d "$REPO_ROOT/cc" ] && [ "$(ls -A "$REPO_ROOT/cc" 2>/dev/null)" ]; then
    for skill in "$REPO_ROOT/cc"/*/; do
      name=$(basename "$skill")
      cp -r "$skill" "$base/$name"
    done
  fi

  echo "  ✅ Claude Code"
}

# === pi ===
sync_pi() {
  local base="${PI_SKILLS_DIR:-~/.pi/skills}"
  mkdir -p "$base"
  echo "→ Syncing to pi ($base)..."

  cp -r "$REPO_ROOT/shared/grill-with-docs"  "$base/"
  cp -r "$REPO_ROOT/shared/skill-authoring"  "$base/"

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
    ;;
  cc)     sync_cc ;;
  pi)     sync_pi ;;
  all)
    sync_hermes
    sync_cc
    sync_pi
    ;;
  *)
    echo "Usage: $0 {hermes|cc|pi|all}"
    exit 1
    ;;
esac
