# Agent SkillHub Workflow

Use this for centralized SkillHub work in `/Users/alexcai/.agents`. The goal is to keep day-to-day skill authoring light while preserving governance evidence.

## Directory Semantics

| Path | Meaning |
|---|---|
| `/Users/alexcai/.agents/skills` | Entry / landing zone. Temporary and untrusted until classified. |
| `/Users/alexcai/.agents/shared` | Reviewed cross-CLI shared canonical pool. |
| `/Users/alexcai/.agents/pools/*` | Specialized canonical pools. |
| `/Users/alexcai/.agents/归档` | Cold archive; no runtime should load from here. |
| `/Users/alexcai/.agents/external-skill-links` | External runtime-native source evidence only. |

## New Skill

1. Classify intended audience: shared, content, hermes-ops, claude-native, hyperframes, or entry-only.
2. Create or modify the skill in the canonical target, not in a runtime directory.
3. Keep `SKILL.md` concise; move depth to `references/`.
4. Update `skill-sources.md`, `.skill-lock.json` if GitHub-backed, and `skill-function-tags.tsv`.
5. Write an audit under `/Users/alexcai/.agents/audits/YYYY-MM-DD/`.
6. Repoint runtime only if explicitly requested.

## GitHub Import

1. Clone or fetch the upstream repo to `/private/tmp`.
2. Identify all `SKILL.md` directories.
3. Classify each skill by function and risk.
4. If a local canonical copy already exists and differs, do not overwrite. Mark `upstream-merge-candidate`.
5. Copy only new reviewed skills to the chosen pool.
6. Update `.skill-lock.json`, `skill-sources.md`, and tags.
7. Scan for obvious real credentials; variable names and placeholders are not secrets.
8. Record the upstream commit and validation in an audit.

## Existing Skill Modification

1. Compare active canonical and source repo copy.
2. If source is dirty or canonical is richer, do not overwrite blindly.
3. Apply narrow edits to both source and active canonical when both are intended to stay aligned.
4. Preserve user/local modifications unless Alex explicitly asks to replace them.
5. Verify line count, referenced files, and no broken internal links.

## Runtime Exposure

Runtime exposure is a separate action from authoring.

- Do not point runtime at `.agents/skills`, `.agents/归档`, source repos, or `external-skill-links`.
- Runtime symlinks should point to `.agents/shared` or `.agents/pools/*`.
- Repointing runtime is L3 unless the task explicitly authorizes it.

## Obsidian Writeback

Do not dump execution logs into the architecture document.

| Change | Writeback |
|---|---|
| Run or validation | `monitor_log` |
| Evidence | `evidence_index` |
| Architecture/function change | `architecture_changelog` |
| Tag change | `function_tags_index` |

Resolve actual paths through `/Users/alexcai/.agents/config/agent-skills/docs.yml`.

## Final Verification

Run the smallest relevant checks:

```bash
python3 -m json.tool /Users/alexcai/.agents/.skill-lock.json
python3 - <<'PY'
from pathlib import Path
rows = Path('/Users/alexcai/.agents/skill-function-tags.tsv').read_text().splitlines()
print(len(rows) - 1)
PY
```

If runtime changed, also run active symlink scans and the relevant CLI skill list.
