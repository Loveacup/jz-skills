# Codebase Inspection with pygount

Analyze repositories for LOC, language statistical, file counts, and code-vs-comment ratios.

## Prerequisites

```bash
pip install --break-system-packages pygount 2>/dev/null || pip install pygount
```

## Basic Summary

```bash
cd /path/to/repo
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
  .
```

**IMPORTANT:** Always use `--folders-to-skip` or pygount will crawl dependency dirs and hang.

## Common Exclusions

```bash
# Python
--folders-to-skip=".git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache"

# JS/TS
--folders-to-skip=".git,node_modules,dist,build,.next,.cache,.turbo,coverage"

# General
--folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party"
```

## Filter by Language

```bash
pygount --suffix=py --format=summary .
pygount --suffix=py,yaml,yml --format=summary .
```

## File-by-File Output

```bash
pygount --folders-to-skip=".git,node_modules,venv" .
pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
```

## Output Formats

```bash
pygount --format=summary .   # summary table (recommended)
pygount --format=json .      # JSON for programmatic use
```

## Interpreting Results

| Column | Meaning |
|--------|---------|
| Language | Detected programming language |
| Files | Number of files |
| Code | Lines of executable/declarative code |
| Comment | Comment/documentation lines |
| % | Percentage of total |

Pseudo-languages:
- `__empty__` — empty files
- `__binary__` — binary files (images, compiled)
- `__generated__` — auto-generated files
- `__duplicate__` — identical content
- `__unknown__` — unrecognized types

## Pitfalls

1. **Always exclude .git, node_modules, venv** — without `--folders-to-skip`, pygount may hang.
2. **Markdown shows 0 code lines** — all content classified as comments (expected).
3. **JSON files show low code counts** — use `wc -l` for accurate JSON line counts.
4. **Large monorepos** — use `--suffix` to target specific languages.
