# Deployment Workflow — jz-skills

Full bidirectional sync workflow for the jz-skills git repo. This reference covers sanitization rules, platform-specific paths, and the complete push/pull cycle.

---

## Architecture

```
 ┌─────────────────────────────────────┐
 │        GitHub (source of truth)     │
 │    github.com/Loveacup/jz-skills    │
 └──────────┬──────────────┬───────────┘
            │ git pull     │ git pull
            ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │ Mac mini │   │  MacBook │   │ Windows  │
     │          │   │          │   │          │
     │ Hermes   │   │ CC       │   │ pi       │
     │ sync-all │   │ sync-all │   │ sync-all │
     └──────────┘   └──────────┘   └──────────┘
```

---

## Platform-Specific Skill Paths

| Platform | Skill directory | Structure |
|----------|----------------|-----------|
| Hermes | `~/.hermes/skills/<category>/<name>/` | Nested by category |
| Claude Code | `~/.claude/skills/<name>.md` or `<name>/SKILL.md` | Flat or nested |
| pi | `~/.pi/skills/<name>/` | Flat |

---

## Script Reference

### `deploy/sync-all.sh` — Forward Sync (repo → local agents)

```bash
./deploy/sync-all.sh hermes   # Deploy to Hermes + all 15 profiles
./deploy/sync-all.sh cc       # Deploy to Claude Code
./deploy/sync-all.sh pi       # Deploy to pi
./deploy/sync-all.sh all      # Deploy to all three
```

Maps shared skills to their platform-specific paths:
- `shared/web-research-router` → `research/web-research-router` (Hermes)
- `shared/github-code-explorer` → `github/github-code-explorer` (Hermes)
- `shared/grill-with-docs` → `governance/grill-with-docs` (Hermes)
- `shared/skill-authoring` → `governance/skill-authoring` (Hermes)

Hermes-specific skills are also deployed to all 15 profiles with dynamic discovery.

### `deploy/sync-back.sh` — Reverse Sync (local agents → repo)

```bash
./deploy/sync-back.sh --dry-run   # Preview what changed
./deploy/sync-back.sh              # Apply changes (Hermes → repo)
```

Compares `~/.hermes/skills/` against `jz-skills/` for all 8 custom skills. Only copies files that differ. Use `--dry-run` first to review.

---

## Sanitization Checklist

**Run before EVERY `git push` to a public repo:**

```bash
# Check for sensitive patterns
grep -rIn --include="*.md" --include="*.sh" --include="*.py" \
  -E "(/Users/[a-z]+/|gho_|sk-|192\.168|@foxmail|\.local$)" . \
  | grep -v .git/ | grep -v __pycache__/
```

### Sensitive Patterns to Remove

| Pattern | Example | Fix |
|---------|---------|-----|
| `/Users/<name>/` absolute paths | `~/.hermes/` | `~/` |
| GitHub account in tool docs | `logged in as Loveacup` | `logged in via gh CLI` |
| Token scopes | `token scopes: repo, read:org` | Remove entirely |
| Email addresses | `<email redacted>` | Remove or anonymize |
| Internal IPs | `<internal IP redacted>` | Remove or generalize |
| Hostnames with `.local` | `AlexdeMac-mini-7994.local` | Remove |

### Safe to Keep (Public Info)

- GitHub repo URLs: `github.com/Loveacup/jz-skills`
- Public company names: `TauricResearch`, `Anthropic`
- Generic warnings about secrets: `"Don't paste API keys"` ← this is a security rule, not a leak

---

## Daily Workflow

### Before Work (pull latest)
```bash
cd ~/code/jz-skills
git pull
./deploy/sync-all.sh hermes
```

### After Work (push changes)
```bash
cd ~/code/jz-skills
./deploy/sync-back.sh --dry-run
./deploy/sync-back.sh
git diff
git commit -am "daily sync: <summary>"
# Sanitization check
grep -rIn -E "(/Users/[a-z]+/|gho_|sk-|192\.168|@foxmail)" . | grep -v .git/ | grep -v __pycache__/ || true
git push
```

### On Other Machines
```bash
cd ~/code/jz-skills
git pull
./deploy/sync-all.sh cc      # or hermes / pi / all
```

---

## Authoring Workflow

When creating or updating a skill:

1. Edit files in `~/code/jz-skills/shared/<name>/` or `~/code/jz-skills/hermes/<name>/`
2. `./deploy/sync-all.sh hermes` — test locally
3. Verify the skill works in a Hermes session
4. `./deploy/sync-back.sh --dry-run` — check if Hermes agent made modifications
5. If agent modified: `./deploy/sync-back.sh` → `git diff` → review
6. `git commit && git push`
7. On other machines: `git pull && ./deploy/sync-all.sh <platform>`
