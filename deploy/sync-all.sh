#!/bin/bash
# sync-all.sh — Deploy jz-skills to Hermes / Claude Code / pi
# Usage: ./deploy/sync-all.sh {hermes|cc|pi|all}
# Must be run from repo root.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Hermes profile runs may rewrite $HOME to
# ~/.hermes/profiles/<profile>/home. Deployment targets must use the real
# macOS user home, otherwise sync-all silently copies into a profile-home
# shadow tree and the live shared skill pool is left stale.
REAL_HOME="$(python3 - <<'PY'
import os, pwd
print(pwd.getpwuid(os.getuid()).pw_dir)
PY
)"

copy_skill_dir() {
  local src="$1"
  local dst="$2"
  local target="$dst/$(basename "$src")"
  if [ -d "$src" ]; then
    mkdir -p "$dst"
    rm -rf "$target"
    cp -r "$src" "$dst/"
  else
    echo "  ⚠️  skip missing: ${src#$REPO_ROOT/}"
  fi
}

# === Hermes ===
sync_hermes() {
  local base="$REAL_HOME/.hermes/skills"
  echo "→ Syncing to Hermes..."

  # Shared (cross-platform) skills
  mkdir -p "$base/governance" "$base/productivity"
  copy_skill_dir "$REPO_ROOT/shared/grill-with-docs"        "$base/governance"
  copy_skill_dir "$REPO_ROOT/shared/skill-authoring"        "$base/governance"
  copy_skill_dir "$REPO_ROOT/shared/pdf"                    "$base/productivity"
  copy_skill_dir "$REPO_ROOT/shared/strategic-insight-longform"  "$base/productivity"
  copy_skill_dir "$REPO_ROOT/shared/voice-to-markdown-workflow"  "$base/productivity"
  copy_skill_dir "$REPO_ROOT/shared/github"                   "$base"
  copy_skill_dir "$REPO_ROOT/shared/xhs-tech-writer"    "$base/hermes"

  # Hermes-specific skills
  mkdir -p "$base/research" "$base/productivity" "$base/governance" "$base/autonomous-ai-agents" "$base/devops" "$base/apple" "$base/hermes" "$base/social-media"
  copy_skill_dir "$REPO_ROOT/hermes/web-research-router"             "$base/research"
  copy_skill_dir "$REPO_ROOT/hermes/source-verification"            "$base/research"
  copy_skill_dir "$REPO_ROOT/hermes/tradingagents"                   "$base/research"

  copy_skill_dir "$REPO_ROOT/hermes/auto-diary"                      "$base"
  copy_skill_dir "$REPO_ROOT/hermes/bilibili-video-analyzer"         "$base"
  copy_skill_dir "$REPO_ROOT/hermes/xhs-crawler"                     "$base"
  copy_skill_dir "$REPO_ROOT/hermes/calendar-manager"               "$base"
  copy_skill_dir "$REPO_ROOT/hermes/cron-worker"                    "$base"
  copy_skill_dir "$REPO_ROOT/hermes/de-slop"                        "$base"
  copy_skill_dir "$REPO_ROOT/hermes/claude-code"                    "$base/autonomous-ai-agents"
  copy_skill_dir "$REPO_ROOT/hermes/cqi-plan-writer"                "$base/governance"
  copy_skill_dir "$REPO_ROOT/hermes/supermemory-hermes"              "$base/governance"
  copy_skill_dir "$REPO_ROOT/hermes/memory-hub"                      "$base/governance"   # Phase 1 记忆-日志回路（全局；暂不进 per-profile 循环，start narrow）
  copy_skill_dir "$REPO_ROOT/hermes/mac-doctor"                     "$base/apple"
  copy_skill_dir "$REPO_ROOT/hermes/tts-manager"                    "$base/hermes"
  copy_skill_dir "$REPO_ROOT/hermes/tech-support-email"             "$base/hermes"
  copy_skill_dir "$REPO_ROOT/hermes/news-assembly"                  "$base/productivity"
  copy_skill_dir "$REPO_ROOT/hermes/morning-news-briefing"           "$base/productivity"
  copy_skill_dir "$REPO_ROOT/hermes/telegram-topic-manager"         "$base/social-media"
  copy_skill_dir "$REPO_ROOT/hermes/dingtalk-message-monitor"      "$base/social-media"
  copy_skill_dir "$REPO_ROOT/hermes/surge-gateway"                 "$base/devops"

  # Sync to all profiles (skip profiles that use external_dirs to shared pool)
  echo "→ Syncing to profiles..."
  for prof in $(ls -d "$REAL_HOME"/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
    # Skip profiles that already get skills via external_dirs — don't create
    # redundant local copies that shadow the shared pool.
    local cfg="$REAL_HOME/.hermes/profiles/$prof/config.yaml"
    if [ -f "$cfg" ] && grep -q 'external_dirs:' "$cfg" 2>/dev/null; then
      if grep -A2 'external_dirs:' "$cfg" 2>/dev/null | grep -qv '\[\]'; then
        echo "  ⏭️  $prof (uses external_dirs)"
        continue
      fi
    fi
    local pd="$REAL_HOME/.hermes/profiles/$prof/skills"
    mkdir -p "$pd/research" "$pd/github" "$pd/governance" "$pd/productivity" "$pd/autonomous-ai-agents" "$pd/apple" "$pd/hermes" "$pd/social-media"
    copy_skill_dir "$REPO_ROOT/shared/grill-with-docs"        "$pd/governance"
    copy_skill_dir "$REPO_ROOT/shared/skill-authoring"        "$pd/governance"
    copy_skill_dir "$REPO_ROOT/shared/github"                "$pd"
    copy_skill_dir "$REPO_ROOT/shared/xhs-tech-writer"        "$pd/hermes"
    copy_skill_dir "$REPO_ROOT/hermes/web-research-router"             "$pd/research"
    copy_skill_dir "$REPO_ROOT/hermes/source-verification"            "$pd/research"
    copy_skill_dir "$REPO_ROOT/hermes/tradingagents"                   "$pd/research"
    copy_skill_dir "$REPO_ROOT/hermes/calendar-manager"               "$pd"
    copy_skill_dir "$REPO_ROOT/hermes/cron-worker"                    "$pd"
    copy_skill_dir "$REPO_ROOT/hermes/de-slop"                        "$pd"
    copy_skill_dir "$REPO_ROOT/hermes/claude-code"                    "$pd/autonomous-ai-agents"
    copy_skill_dir "$REPO_ROOT/hermes/cqi-plan-writer"                "$pd/governance"
    copy_skill_dir "$REPO_ROOT/hermes/supermemory-hermes"              "$pd/governance"
    copy_skill_dir "$REPO_ROOT/hermes/mac-doctor"                     "$pd/apple"
    copy_skill_dir "$REPO_ROOT/hermes/tts-manager"                    "$pd/hermes"
    copy_skill_dir "$REPO_ROOT/hermes/tech-support-email"             "$pd/hermes"
    copy_skill_dir "$REPO_ROOT/hermes/news-assembly"                  "$pd/productivity"
    copy_skill_dir "$REPO_ROOT/hermes/morning-news-briefing"           "$pd/productivity"
    copy_skill_dir "$REPO_ROOT/hermes/telegram-topic-manager"         "$pd/social-media"
    copy_skill_dir "$REPO_ROOT/hermes/dingtalk-message-monitor"      "$pd/social-media"
    copy_skill_dir "$REPO_ROOT/hermes/surge-gateway"                 "$pd/devops"
  done

  echo "  ✅ Hermes ($(ls -d "$REAL_HOME"/.hermes/profiles/*/ 2>/dev/null | wc -l | tr -d ' ') profiles)"
}

# === Claude Code ===
sync_cc() {
  local base="$REAL_HOME/.claude/skills"
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
  local base="${PI_SKILLS_DIR:-$REAL_HOME/.pi/skills}"
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
