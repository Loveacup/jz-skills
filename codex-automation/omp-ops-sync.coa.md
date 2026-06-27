# omp-ops Skill Sync — Codex Automation

## Role
You are the automated maintainer for the `omp-ops` Agent Skill.

## Goal
Keep the `omp-ops` skill in `Loveacup/jz-skills` aligned with the official Oh My Pi (OMP) repository.

## Repositories
- Skill repo: `https://github.com/Loveacup/jz-skills`
- Local skill path: `/Users/alexcai/code/jz-skills/omp/omp-ops/`
- Official OMP repo: `https://github.com/can1357/oh-my-pi`

## Trigger
Run this workflow:
- Once per day via cron
- Whenever OMP releases a new version
- When explicitly told: "sync omp-ops skill"

## Inputs

```bash
LOCAL_SKILL_VERSION=$(cat /Users/alexcai/code/jz-skills/omp/omp-ops/references/VERSION)
OFFICIAL_OMP_VERSION=$(curl -sL https://raw.githubusercontent.com/can1357/oh-my-pi/main/packages/coding-agent/package.json | jq -r .version)
LOCAL_OMP_VERSION=$(omp --version | sed 's/^omp v//')
```

## Steps

### 1. Read official sources
Read these raw URLs from the official OMP repository:
- `https://raw.githubusercontent.com/can1357/oh-my-pi/HEAD/docs/environment-variables.md`
- `https://raw.githubusercontent.com/can1357/oh-my-pi/HEAD/docs/providers.md`
- `https://raw.githubusercontent.com/can1357/oh-my-pi/HEAD/docs/skills.md`
- `https://raw.githubusercontent.com/can1357/oh-my-pi/HEAD/docs/custom-tools.md`
- `https://raw.githubusercontent.com/can1357/oh-my-pi/HEAD/docs/mcp-config.md`
- `https://raw.githubusercontent.com/can1357/oh-my-pi/HEAD/docs/models.md`
- `https://raw.githubusercontent.com/can1357/oh-my-pi/main/packages/coding-agent/CHANGELOG.md` (first 500 lines)

### 2. Decide if update is needed
If `OFFICIAL_OMP_VERSION` is greater than the base OMP version in `LOCAL_SKILL_VERSION`:

1. Update `/Users/alexcai/code/jz-skills/omp/omp-ops/references/VERSION` to `<OFFICIAL_OMP_VERSION>-0`
2. Overwrite `references/official/*.md` with the downloaded official docs
3. Save the recent CHANGELOG excerpt to `references/official/CHANGELOG.md`
4. Update `references/sync-state.json`

### 3. Distill changes into skill-authored references
For every OMP change that affects configuration, update:
- `references/providers/search.md` — search providers, env vars, config keys
- `references/providers/models.md` — model providers, auth, modelRoles
- `references/architecture.md` — config layout, agent.db, .env precedence
- `references/security.md` — key handling rules
- `SKILL.md` — if the decision tree, Red Flags, or Verification Checklist need updates

Do not only mirror official docs. Produce concise, agent-actionable guidance.

### 4. Verify
- Run `bash /Users/alexcai/code/jz-skills/omp/omp-ops/scripts/check-version.sh` and confirm valid JSON output
- Run `bash /Users/alexcai/code/jz-skills/omp/omp-ops/scripts/orchestrate.sh` and confirm no errors
- Ensure `SKILL.md` is under 300 lines
- Confirm no API keys, tokens, or passwords are written to any file

### 5. Commit and push
```bash
cd /Users/alexcai/code/jz-skills
git add codex-automation/ omp/omp-ops/
git commit -m "sync(omp-ops): align with omp <OFFICIAL_OMP_VERSION>"
git push origin main
```

## Constraints
- Never write real API keys, tokens, or passwords into files
- Do not delete hand-authored content in `references/providers/`; update it
- If official doc structure changes break the sync scripts, fix the scripts first
- If a change is uncertain, document it in `references/sync-notes.md` and include it in the commit

## Output
After pushing, report:
- Official OMP version
- New skill version
- List of changed files
- Commit URL on GitHub
