# Skill Origin Classification — Methodology

How to classify local skills by origin: official (shipped with Hermes), self-made (jz-skills), or auto-generated (Hermes Agent during operation).

## The Pitfall: `.bundled_manifest` Is Not Authoritative

`~/.hermes/skills/.bundled_manifest` is a local snapshot of hash→skill mappings. It can be:
- Stale (not updated after `hermes update`)
- Incomplete (fewer entries than the actual Hermes source tree)
- Out of sync with the installed Hermes Agent version

**DO NOT use `.bundled_manifest` as the sole source of truth for "what skills are official."**

## Correct Methodology: Compare Against Hermes Source Repository

### Three Directories to Compare

| Directory | Contents | Authoritative? |
|:---|:---|:---|
| `~/.hermes/hermes-agent/skills/` | Core skills shipped with every Hermes install | ✅ Yes |
| `~/.hermes/hermes-agent/optional-skills/` | Optional skills, installed on demand | ✅ Yes |
| `~/.hermes/skills/` | All locally-installed skills (core + optional + self-made) | ❌ Mixed |

### Step-by-Step Classification

#### 1. Extract skill names from Hermes repository

```bash
# Extract `name:` field from all SKILL.md frontmatter in the Hermes source
find ~/.hermes/hermes-agent/skills ~/.hermes/hermes-agent/optional-skills \
  -name 'SKILL.md' -type f -exec sed -n '/^---$/,/^---$/s/^name: *//p' {} \; | sort -u
```

This gives the ground truth list of "official" skill names.

#### 2. Extract skill names from local install

```bash
find ~/.hermes/skills -name 'SKILL.md' -type f \
  -not -path '*/.archive/*' -not -path '*/.hub/*' -not -path '*/_lifecycle/*' \
  -exec sed -n '/^---$/,/^---$/s/^name: *//p' {} \; | sort -u
```

#### 3. Diff to classify

```python
official = set(repo_names)
local = set(local_names)

shared = official & local       # Installed from Hermes repo
local_only = local - official   # Self-made / auto-generated
repo_only = official - local    # Available but not installed
```

#### 4. Further classify local-only skills

For local-only skills, check the SKILL.md `author:` field:
- `author: Hermes Agent` → auto-generated/adapted during operation
- No `author:` or custom author → check `~/code/jz-skills/` for presence → self-made (jz-skills)
- Third-party author (e.g., JimLiu, SHL0MS, dodo-reach) → community skill adopted locally

### Edge Cases

- **Skill in jz-skills AND Hermes repo:** Alex customized an official skill. Check `sync-back.sh` PAIR entries. Examples: `arxiv`, `obsidian`.
- **Skill in jz-skills AND auto-generated:** The skill was auto-generated, then Alex adopted it into jz-skills. Example: `news-assembly`.
- **Skill with same name but different content:** Check SHA256 of the SKILL.md against the Hermes source. Use `references/bundled-skill-drift-detection.md` methodology.

## Quick Verification Command

One-liner to classify all skills at once:

```bash
# Requires jq. Lists every local skill with origin classification.
python3 -c "
import os, json, subprocess

def get_skills(path):
    result = subprocess.run(['find', path, '-name', 'SKILL.md', '-type', 'f'], 
                          capture_output=True, text=True)
    skills = {}
    for f in result.stdout.strip().split('\n'):
        if not f: continue
        name = subprocess.run(['sed', '-n', '/^---$/,/^---$/s/^name: *//p', f],
                            capture_output=True, text=True).stdout.strip()
        author = subprocess.run(['sed', '-n', '/^---$/,/^---$/s/^author: *//p', f],
                              capture_output=True, text=True).stdout.strip()
        skills[name] = {'path': f, 'author': author}
    return skills

repo = get_skills(os.path.expanduser('~/.hermes/hermes-agent/skills'))
repo.update(get_skills(os.path.expanduser('~/.hermes/hermes-agent/optional-skills')))
local = get_skills(os.path.expanduser('~/.hermes/skills'))

for name in sorted(local):
    origin = 'OFFICIAL' if name in repo else 'SELF-MADE'
    author = local[name]['author']
    print(f'{origin:12s} | {name:40s} | {author}')
" | sort
```

## Usage in Skill Audit Sessions

When the user asks "which skills are mine vs official," do NOT:
- ❌ Rely on `.bundled_manifest`
- ❌ Judge by file modification dates
- ❌ Guess based on Chinese vs English descriptions

DO:
- ✅ Compare against `~/.hermes/hermes-agent/skills/` and `optional-skills/`
- ✅ Use `name:` frontmatter field for matching (directory names != skill names for nested mlops skills)
- ✅ Present the three-way split: official / self-made (jz-skills) / auto-generated (Hermes Agent)

## Case Study: 2026-06-07 Audit

- `.bundled_manifest`: 60 entries → misleading, far fewer than actual Hermes core (74)
- Hermes source repo: 170 total (74 core + 95 optional + 1 plugin)
- Alex's local: 152 skills (85 from Hermes + 67 local-only)
- Local-only breakdown: 33 in jz-skills + 34 Hermes auto-generated
- 85 Hermes skills available but not installed
