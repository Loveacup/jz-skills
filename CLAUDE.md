# CLAUDE.md — jz-skills

> Governance file for Claude Code operating in this repo.
> 当 Claude Code 在本仓库中工作时，必须遵守以下规则。

---

## 🏛️ What This Repo Is · 这是什么仓库

AI agent skill hub — 60 skills across 4 layers, deployed to Hermes (三省六部 15-profile system), Claude Code, and pi (Windows).

```
jz-skills/
├── shared/   🌐 Cross-platform (16) — synced to all 3 platforms
├── hermes/   ⚙️ Hermes (15) — Hermes-specific, not deployed to CC or pi
├── hermes-3S6M-profiles/ 🏯 三省六部 (23) — profile-specific, 15 departments
├── pi/       🪟 Pi / Windows (6) — pi-specific, not deployed to Hermes or CC
├── cc/       🤖 Claude Code (1+) — CC-native skills, flat SKILL.md format
└── deploy/   🔄 Sync scripts — bidirectional Hermes ↔ repo ↔ CC/pi
```

---

## 📦 Skill Structure · 技能目录规范

Every skill directory follows this layout:

```
{skill-name}/
├── SKILL.md              # Required. YAML frontmatter + markdown body
├── README.md             # Optional. Human-facing overview
├── CHANGELOG.md          # Optional. Version history
├── references/           # Optional. Linked docs (api.md, formats.md, etc.)
├── scripts/              # Optional. Runnable scripts
├── templates/            # Optional. Output templates
└── assets/               # Optional. Images, fonts, etc.
```

**YAML frontmatter** in every SKILL.md:

```yaml
---
name: skill-name           # lowercase, hyphens, max 64 chars
description: |             # 1-3 lines. Bilingual OK.
  What this skill does. Triggers: keyword1, keyword2.
  DO NOT use for: anti-trigger1, anti-trigger2.
version: X.Y.Z             # SemVer
author: Author Name
license: MIT
---
```

**Naming:** lowercase, hyphens (`-`) only. No underscores, no camelCase, no spaces.

---

## 🌐 Cross-Platform Rules · 跨平台规则

Skills in `shared/` MUST be platform-agnostic:
- No hardcoded paths to `~/.hermes/`, `~/.claude/`, or `C:\`
- No platform-specific CLI tools unless the skill provides platform detection
- If a skill is inherently platform-specific, it belongs in `hermes/`, `pi/`, or `cc/`

Skills in `hermes/` MAY reference Hermes-specific paths and tools.

---

## ✍️ Skill Authoring · 技能创作

All skill creation and major edits MUST follow [skill-authoring v3.0](shared/skill-authoring/):
- 11-step workflow: Capture → Grill → Progressive disclosure → Anti-rationalization → Rule positioning → Checklist → 7-dim scoring → Test cases → Deployment-grounded audit → Failure classification → Revision
- Any skill that hasn't gone through this pipeline is a draft

---

## 📝 Commit Conventions · 提交规范

Bilingual conventional commits — English + Chinese separated by `/`:

```
type(scope): English description / 中文描述
```

Types: `feat` `fix` `docs` `refactor` `chore` `config` `v` `archive`

| Type | When to use · 使用场景 |
|:---|:---|
| `feat(skill)` | New skill or major version bump / 新技能或大版本 |
| `fix(skill)` | Bug fix / 修 bug |
| `docs` | README, comments, diagrams / 文档 |
| `refactor(skill)` | Internal restructure, no behavior change / 重构 |
| `chore` | Sync, deploy, cleanup / 杂务 |
| `config` | Cron config, deploy scripts / 配置 |
| `v` | Pure version bump with changelog / 纯版本号 |

Examples from history:
```
feat(auto-diary): v3.5 周/月/年报聚合金字塔 + cron + 校验
fix(auto-diary): ~ expansion bug causing 0 vault changes
docs: re-rank active skills by full-history commit count (12→12→10→9→7→6→5)
```

---

## 🔄 Sync Workflow · 同步流程

### Push (Hermes → repo)
```bash
./deploy/sync-back.sh --dry-run                 # Preview all runtime drift
./deploy/sync-back.sh --apply --only shared/x   # Apply one reviewed scope
./deploy/skill-drift-summary.sh                 # Summarize commit risk
git diff
```
`sync-back.sh` is report-only by default. Runtime → repo writeback must be scoped with `--only <repo-path>` unless Alex explicitly approves `--force-all`. It auto-sanitizes scoped writeback: `$HOME` → `~/`, emails → redacted, private IPs → redacted, API keys → redacted.

Do not batch unrelated runtime drift into the current commit. If `--dry-run` shows multiple drifted skills, review them separately.

### Pull (repo → Hermes/CC/pi)
```bash
git pull && ./deploy/sync-all.sh <platform>
# platform: hermes | cc | pi | all
```

### When adding a new skill
1. Create the skill directory + SKILL.md in the correct platform layer
2. Add the sync mapping to BOTH `sync-all.sh` (deploy path) and `sync-back.sh` (reverse path)
3. Run `sync-all.sh hermes` to deploy → test → `sync-back.sh` to pull back sanitized

---

## 🚫 DON'T · 禁止事项

1. **Don't add CLAUDE.md in skill subdirectories.** One CLAUDE.md at repo root is sufficient.
2. **Don't break existing sync mappings.** If you rename or move a skill, update both `deploy/sync-all.sh` and `deploy/sync-back.sh`.
3. **Don't commit secrets.** `sync-back.sh` sanitizes, but if you bypass it, check manually.
4. **Don't change the 4-layer structure** without updating README and sync scripts.
5. **Don't use underscores in skill names.** Hyphens only.
6. **Don't create skills without YAML frontmatter.** Even a draft needs `name` and `version`.
7. **Don't remove a skill without archiving.** Rename to `_archived-{name}/` if deprecating.
8. **Don't write platform-specific code in `shared/`.** That's what `hermes/` and `pi/` are for.

---

## 🧠 When Claude Code Is Operating Here · CC 在此仓库工作时

- **Use `skill-authoring` for any skill work.** Load the skill before making changes.
- **Prefer agent team for multi-file changes.** This repo has 60 skills with cross-references — a single-CC session can miss cascading impacts.
- **Run `deploy/skill-drift-summary.sh` before committing** to catch cross-skill drift, critical deletions, and sensitive additions.
- **Run `sync-back.sh --dry-run` before scoped runtime writeback** to see what's changed from the live Hermes deployment.
- **Test sync before pushing** if you changed sync mappings: `./deploy/sync-all.sh hermes && ./deploy/sync-back.sh --dry-run`.
- **Bilingual commits are mandatory.** Single-language commits will be rejected on review.
- **Don't touch `hermes-3S6M-profiles/`** unless explicitly asked — these are tightly coupled to the 三省六部 governance system and profile `config.yaml` files in `~/.hermes/profiles/`.
