# CC-Driven Obsidian Vault Restructuring with Wikilink Preservation

2026-06-16: Verified — restructured 10 → 8 files in `goal方法论/`, renaming all files, merging application cluster, and updating every wikilink across the entire vault.

## When to Use

- Renaming multiple vault files while keeping all `[[wikilinks]]` intact
- Merging related documents into consolidated files
- Renaming directories that are referenced across the vault
- Any multi-file restructuring where broken links are unacceptable

## Pattern: CC reads → analyzes → executes → Hermes audits

### Phase 1: Write the context file

Give CC a detailed `/tmp/cc-context-<task>.md` with:

1. **Current directory path** (absolute)
2. **Old → new mapping table** for every file and directory
3. **Merge instructions** — exactly which files combine, what structure the merged file should have
4. **Wikilink update map** — every `[[old_name]]` → `[[new_name]]` pair
5. **Special instructions** — e.g. "don't change aliases that still resolve"

Example mapping table:
```markdown
| 旧 | 新 |
|----|-----|
| `01_方法论主文-承重墙与goal生命周期.md` | `01_承重墙与goal生命周期.md` |
| `SOUL 委派审核_应用指令_20260616.md` | 并入 `06_SOUL委派审核.md` |
```

### Phase 2: CC's analysis (3-5 min with xhigh)

CC will:
1. `ls -la` + `wc -l *.md` — inventory
2. Read all files, extract frontmatter and headings
3. Scan all wikilinks across files (`grep -n '\[\['`)
4. Search vault-wide for external references to target files
5. Present findings before executing

### Phase 3: CC's execution (3-5 min)

CC does:
1. **Rename directory** first (`mv old new`)
2. **Rename files** via `mv`
3. **Wikilink replacement**: `perl -i -pe` on all affected files
4. **Merge files**: read sources → write combined file → delete originals
5. **Sync 00_总览**: update mermaid diagrams, counts, related fields, § sections

### Phase 4: Hermes post-CC audit

After CC finishes:
1. Verify file count (`ls -1 | wc -l`)
2. Scan for residual old filenames: `grep -rn 'old_pattern' vault/ --include="*.md"`
3. Check bare wikilinks are zero; aliased references (`[[old|...]]`) are OK
4. Fix missed references
5. Add missing aliases (e.g. new directory name as alias on 00)

## Critical Pitfall: Perl UTF-8 Encoding

**Symptom:** `perl -i -pe` with `-CSD` flag doesn't match Chinese wikilinks — replacement silently fails but files remain uncorrupted (UTF-8 round-trip preserved).

**Root cause:** `-CSD` decodes file as UTF-8 characters but pattern stays bytes → mismatch on multi-byte Chinese characters.

**Fix:** Pure byte mode (omit `-CSD`):
```bash
# ❌ Broken for Chinese
perl -CSD -i -pe 's/\[\[旧中文名\]\]/\[\[新名\]\]/g' *.md

# ✅ Works for all UTF-8
perl -i -pe 's/\[\[旧名\]\]/\[\[新名\]\]/g' *.md
```

**Verification:** Always run `grep -rn '\[\[旧名\]\]' vault/ --include="*.md"` after replacement. Zero bare links expected; aliased references are deliberate.

## Non-Trivial CC Behaviors

1. **Proactively finds external vault references** — scans entire vault for files linking to renamed targets (diary, weekly reports, planning docs)
2. **Distinguishes aliases from bare links** — `[[总览\|...]]` left alone; `[[裸链接]]` updated
3. **Suggests improvements** — e.g. "add `goal方法论` alias to 00 so bare directory links resolve"
4. **monitor blind spot is normal** — `cc-monitor.sh` reports IDLE while CC actively works for 10+ min; always supplement with `tmux capture-pane`
