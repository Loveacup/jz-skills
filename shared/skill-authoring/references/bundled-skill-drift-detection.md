# Bundled Skill Drift Detection

## Problem

A skill shipped with Hermes (in `hermes-agent/skills/`) was locally modified — by a governance system, manual edit, or profile sync — and now diverges from upstream. Version numbers can be bumped, so version comparison alone is unreliable. The skill loads and triggers normally, but its content is stale/wrong.

## Detection Recipe

For any skill that lives in both `~/.hermes/skills/` (installed) and `~/.hermes/hermes-agent/skills/` (repo copy), run this comparison:

```bash
cd ~/.hermes/hermes-agent
git fetch --prune --tags origin main

# Compare installed vs upstream (not local repo — local repo may also be behind)
# Step 1: sha256 of installed file
INSTALLED_SHA=$(python3 -c "import hashlib; print(hashlib.sha256(open('/Users/$(whoami)/.hermes/skills/devops/<skill>/SKILL.md','rb').read()).hexdigest()[:16])")

# Step 2: sha256 of upstream origin/main version
UPSTREAM_SHA=$(git show origin/main:skills/devops/<skill>/SKILL.md | python3 -c "import sys,hashlib; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:16])")

# Step 3: compare
if [ "$INSTALLED_SHA" != "$UPSTREAM_SHA" ]; then
  echo "DRIFT DETECTED"
  # Check stale governance residues
  grep -c 'stale governance references' ~/.hermes/skills/devops/<skill>/SKILL.md
else
  echo "CLEAN — matches upstream"
fi
```

Python one-liner for multi-skill audit:

```python
from pathlib import Path
import hashlib, re, subprocess

skills = {
    'kanban-worker': 'skills/devops/kanban-worker/SKILL.md',
    'kanban-orchestrator': 'skills/devops/kanban-orchestrator/SKILL.md',
}

for name, relpath in skills.items():
    installed = Path.home() / '.hermes' / 'skills' / 'devops' / name / 'SKILL.md'
    txt = installed.read_bytes() if installed.exists() else b''
    installed_sha = hashlib.sha256(txt).hexdigest()[:16]

    upstream_txt = subprocess.check_output(
        ['git', 'show', f'origin/main:{relpath}'],
        cwd=Path.home() / '.hermes' / 'hermes-agent'
    )
    upstream_sha = hashlib.sha256(upstream_txt).hexdigest()[:16]

    stale_hits = sum(len(re.findall(x, txt.decode(errors='ignore'), re.I))
                     for x in ['stale governance references', '尚书省', '中书省', '门下'])

    status = '✓ CLEAN' if installed_sha == upstream_sha else f'✗ DRIFT (stale hits: {stale_hits})'
    print(f'{name}: installed={installed_sha} upstream={upstream_sha} → {status}')
```

## Fix

If drift detected and residues found:

1. **Backup** the tainted version: `cp SKILL.md SKILL.md.tainted-backup`
2. **Replace** with upstream: `git show origin/main:<path> > SKILL.md`
3. **Verify** sha256 matches upstream
4. **Sync** repo copy too: `cp SKILL.md ~/.hermes/hermes-agent/<path>`

## Case Study

kanban-orchestrator (2026-06-03):
- Installed: v3.6.0, sha16 `488cd6ae2764af1f`, 66 stale governance references hits
- Upstream: v3.0.0, sha16 `7701634fb6117722`, 0 hits
- Root cause: the old governance system modified the skill, bumped version, added ~400 lines of stale role references, task routing rules, and governance enforcement. The governance system was later decommissioned but the modified skill was never rolled back.
- Fix: replaced with `git show origin/main:skills/devops/kanban-orchestrator/SKILL.md`, verified clean.
