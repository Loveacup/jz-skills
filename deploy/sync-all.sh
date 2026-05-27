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

  # Hermes-specific skills
  mkdir -p "$base/research" "$base/productivity" "$base/governance"
  cp -r "$REPO_ROOT/hermes/web-research-router"             "$base/research/"
  cp -r "$REPO_ROOT/hermes/github-code-explorer"            "$base/github/"
  cp -r "$REPO_ROOT/hermes/tradingagents"                   "$base/research/"
  cp -r "$REPO_ROOT/hermes/llm-wiki"                        "$base/research/"
  cp -r "$REPO_ROOT/hermes/arxiv"                           "$base/research/"
  cp -r "$REPO_ROOT/hermes/auto-diary"                      "$base/"
  cp -r "$REPO_ROOT/hermes/bilibili-video-analyzer"         "$base/"
  cp -r "$REPO_ROOT/hermes/xhs-crawler"                     "$base/"

  # Sync to all profiles
  echo "→ Syncing to profiles..."
  for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
    local pd=~/.hermes/profiles/$prof/skills
    mkdir -p "$pd/research" "$pd/github" "$pd/governance" "$pd/productivity"
    cp -r "$REPO_ROOT/shared/grill-with-docs"        "$pd/governance/"
    cp -r "$REPO_ROOT/shared/skill-authoring"        "$pd/governance/"
    cp -r "$REPO_ROOT/hermes/web-research-router"             "$pd/research/"
    cp -r "$REPO_ROOT/hermes/github-code-explorer"            "$pd/github/"
    cp -r "$REPO_ROOT/hermes/tradingagents"                   "$pd/research/"
    cp -r "$REPO_ROOT/hermes/llm-wiki"                        "$pd/research/"
    cp -r "$REPO_ROOT/hermes/arxiv"                           "$pd/research/"
    cp -r "$REPO_ROOT/hermes-3S6M-profiles/common/three-provinces-constitution"  "$pd/governance/"
    cp -r "$REPO_ROOT/hermes-3S6M-profiles/common/financial-research-agents"     "$pd/research/"
  done

  echo "  ✅ Hermes ($(ls -d ~/.hermes/profiles/*/ 2>/dev/null | wc -l | tr -d ' ') profiles)"
}

# === Profile-specific skills ===
sync_profiles() {
  echo "→ Syncing profile-specific skills..."
  local pd

  # regent (监国太子)
  pd=~/.hermes/profiles/regent/skills
  mkdir -p "$pd"
  for skill in kanban-orchestrator kanban-worker kanban-gate 6m-smoke-test morning-news-briefing; do
    [ -d "$REPO_ROOT/hermes-3S6M-profiles/regent/$skill" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/regent/$skill" "$pd/"
  done

  # gongbu (工部)
  pd=~/.hermes/profiles/gongbu/skills
  for skill in disk-cleanup infra-health-check infra-monitoring surge-gateway agent-observability; do
    [ -d "$REPO_ROOT/hermes-3S6M-profiles/gongbu/$skill" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/gongbu/$skill" "$pd/"
  done

  # tester (刑部)
  pd=~/.hermes/profiles/tester/skills
  for skill in code-review-toolkit agent-security-audit; do
    [ -d "$REPO_ROOT/hermes-3S6M-profiles/tester/$skill" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/tester/$skill" "$pd/"
  done

  # jiangzuojian (将作监)
  pd=~/.hermes/profiles/jiangzuojian/skills
  for skill in delivery-gate specialist-engineer; do
    [ -d "$REPO_ROOT/hermes-3S6M-profiles/jiangzuojian/$skill" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/jiangzuojian/$skill" "$pd/"
  done

  # protocol (礼部)
  pd=~/.hermes/profiles/protocol/skills
  [ -d "$REPO_ROOT/hermes-3S6M-profiles/protocol/md-to-pdf" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/protocol/md-to-pdf" "$pd/"

  # auditor (御史台)
  pd=~/.hermes/profiles/auditor/skills
  [ -d "$REPO_ROOT/hermes-3S6M-profiles/auditor/agent-audit-evaluation" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/auditor/agent-audit-evaluation" "$pd/"

  # archivist (史馆)
  pd=~/.hermes/profiles/archivist/skills
  [ -d "$REPO_ROOT/hermes-3S6M-profiles/archivist/agent-memory-manager" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/archivist/agent-memory-manager" "$pd/"

  # shangshu (尚书省)
  pd=~/.hermes/profiles/shangshu/skills
  [ -d "$REPO_ROOT/hermes-3S6M-profiles/shangshu/a2a-protocol" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/shangshu/a2a-protocol" "$pd/"

  # budget (户部)
  pd=~/.hermes/profiles/budget/skills
  [ -d "$REPO_ROOT/hermes-3S6M-profiles/budget/agent-cost-manager" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/budget/agent-cost-manager" "$pd/"

  # registry (吏部)
  pd=~/.hermes/profiles/registry/skills
  [ -d "$REPO_ROOT/hermes-3S6M-profiles/registry/agent-registry" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/registry/agent-registry" "$pd/"

  # hanlinyuan (翰林院)
  pd=~/.hermes/profiles/hanlinyuan/skills
  [ -d "$REPO_ROOT/hermes-3S6M-profiles/hanlinyuan/deep-research-agent" ] && cp -r "$REPO_ROOT/hermes-3S6M-profiles/hanlinyuan/deep-research-agent" "$pd/"

  echo "  ✅ Profile skills (11 departments)"
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
