# Deployment & Sync · 部署与同步

After ANY update to this skill:

1. Sync to ALL Hermes profiles (dynamic discovery):
   ```bash
   for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
     dst=~/.hermes/profiles/$prof/skills/research/web-research-router
     [ -d "$dst" ] && cp -r "$dst" ~/.hermes/profiles/$prof/backups/web-research-router-$(date +%Y%m%d_%H%M%S)
     rm -rf "$dst"
     cp -r ~/.hermes/skills/research/web-research-router "$dst"
   done
   ```
2. Update Obsidian doc: `00-Inbox/工具制作_Hermes检索总控与GitHub源码探索_三省六部体系_20260526.md`
3. `qmd update`
4. Spot-check 2-3 profiles for SKILL.md presence.
