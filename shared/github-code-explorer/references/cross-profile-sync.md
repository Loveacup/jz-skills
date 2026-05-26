# Cross-Profile Sync for github-code-explorer

When `github-code-explorer` is created or updated, it must be deployed to all
三省六部 profiles. The default profile copy is authoritative; profile-local
copies are independent and must be explicitly synced.

## Target profiles

```
hermes profile list
→ 16 named profiles: archivist, auditor, budget, dispatcher, emergency,
  engineer, hanlinyuan, jiangzuojian, planner, protocol, regent, registry,
  reviewer, security, shangshu, tester
```

The default profile (`~/.hermes/skills/`) does NOT automatically propagate to
`~/.hermes/profiles/<name>/skills/`. Each profile has its own isolated skill tree.

## Sync script

```python
from pathlib import Path
import shutil
from datetime import datetime

profiles_root = Path('/Users/alexcai/.hermes/profiles')
skill_src = Path('/Users/alexcai/.hermes/skills/github/github-code-explorer')
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')

for prof in sorted(p for p in profiles_root.iterdir() if p.is_dir()):
    dest = prof / 'skills/github/github-code-explorer'
    if dest.exists():
        backup = prof / 'backups' / f'github-code-explorer-{stamp}'
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dest, backup)
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_src, dest)
    # Ensure scripts executable
    for py_file in dest.rglob('*.py'):
        py_file.chmod(0o755)
```

## Verification

```python
from pathlib import Path

profiles_root = Path('/Users/alexcai/.hermes/profiles')
missing = []
for prof in sorted(p for p in profiles_root.iterdir() if p.is_dir()):
    skill = prof / 'skills/github/github-code-explorer/SKILL.md'
    if not skill.exists():
        missing.append(prof.name)

assert not missing, f"Missing profiles: {missing}"
print(f"All {len(list(profiles_root.iterdir()))} profiles verified")
```

## Note

If `web-research-router` is also updated (it integrates `github-code-explorer`),
sync it too using the same pattern — see
`web-research-router`'s `references/cross-profile-governance-deployment.md`
for the joint deployment pattern.
