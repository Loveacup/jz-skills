# Bulk Text Replacement in Skill Files

Use when you need to apply the same set of find-and-replace operations across multiple skill files — e.g., cleaning stale terminology, updating outdated references, or mass-renaming concepts.

## Pattern: Python dict-driven bulk sed

```python
from pathlib import Path
import re

base = Path.home() / '.hermes' / 'skills'

fixes = {
    "category/skill-name/SKILL.md": [
        (r'old term pattern', 'new term'),
        (r'another stale reference \(context\)', 'updated reference (context)'),
    ],
    "category/skill-name/references/some-doc.md": [
        (r'三省六部 specific thing', 'generic thing'),
    ],
}

for relpath, replacements in fixes.items():
    fp = base / relpath
    if not fp.exists():
        continue
    txt = fp.read_text()
    orig = txt
    for pattern, repl in replacements:
        txt = re.sub(pattern, repl, txt)
    if txt != orig:
        fp.write_text(txt)
```

## Key rules

1. **Use `re.sub` for regex patterns**, `str.replace` for literal strings
2. **Check `txt != orig`** before writing — skip unchanged files
3. **Target specific files**, not wildcard globs — accidental matches on unrelated content (e.g., "predict" matching "predicts" in ML papers) are hard to undo
4. **Backup first** if replacing critical content: `cp $file $file.bak`
5. **Run in rounds**: first pass catches bulk, verify with `grep -rn`, then second pass targets stragglers

## Anti-patterns

- **Wildcard globbing** (`grep -rl | xargs sed`) — hits `.venv/`, backup files, unrelated binaries
- **Single-pass-and-done** — always verify with a final scan; stragglers are guaranteed
- **Editing bundled skill files** — use `git show origin/main:path` to replace, don't hand-edit

## Real session: decommissioned governance system cleanup (2026-06-03)

Applied 3 rounds across ~50 files:
- Round 1: 13 files (first pass)
- Round 2: 32 files (stragglers)
- Round 3-4: ~5 files (edge cases in YAML frontmatter tags, inline parens)

Key lesson: YAML frontmatter `tags:` fields and inline parenthetical annotations survive regex rounds because they're formatted differently. Check those manually.
