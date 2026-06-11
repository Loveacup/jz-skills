---
name: obsidian
description: Read, search, create, edit, sync, and link notes in an Obsidian vault. Use when the task needs vault path resolution, file IO, Obsidian CLI, Bases (.base files), plugin development, Defuddle web extraction, or qmd indexing. Pair with obsidian-md-ac when writing rich Obsidian Markdown, Mermaid diagrams, or Canvas content. Do NOT use as the formatting authority for Obsidian syntax or diagrams.
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    related_skills: [obsidian-md-ac, qmd]
    tags: [obsidian, vault, note-taking, cli, bases, plugin-dev]
---

# Obsidian Vault

Use this skill for Obsidian vault work: reading, listing, searching, creating notes, appending content, vault sync, CLI interaction, plugin development, Bases (.base files), and web content extraction. Use `obsidian-md-ac` for the content rules when a note needs Obsidian-specific formatting, wikilinks, callouts, Mermaid, or Canvas.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll just use filesystem tools directly" | Must resolve vault path first + iCloud hydration may be needed |
| "The file is empty" | Check for iCloud dataless placeholder before concluding empty |
| "I'll read the file with cat" | Use `read_file` — line numbers, pagination, fallback suggestions |
| "I know where this note lives" | Context may be stale. Always verify with `search_files` before writing |
| "obsidian-md-ac can create the note by itself" | It defines content syntax; this skill owns vault path, IO, sync, and links |

## Boundary Decision

| User asks for... | Load |
|---|---|
| Find/read/write/append notes, resolve vault path, sync, qmd refresh | `obsidian` |
| Obsidian Markdown syntax, callouts, wikilinks, Mermaid, Canvas, note beautification | `obsidian-md-ac` |
| Save a polished note into the vault | Both: draft/format with `obsidian-md-ac`, write/verify with `obsidian` |
| Generic Markdown not intended for Obsidian | Neither unless the user mentions a vault or Obsidian syntax |

## Vault path

Use a known or resolved vault path before calling file tools.
The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `~/.hermes/.env`. If it is unset, use `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

### iCloud / dataless Obsidian files

If a note exists but reads as empty or file access returns macOS errors such as `Resource deadlock avoided`, check whether the file is an iCloud dataless placeholder (`ls -lO@` may show `dataless`). Do not conclude the note is empty. Hydrate it first, then retry reading:

```bash
brctl download '/absolute/path/to/note.md'
open -a Obsidian --args --vault '/absolute/path/to/vault'
```

After a short wait, read the file again. Capture the durable lesson as "hydrate iCloud placeholder before reading," not as a claim that the file/tool is broken.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. If the content needs Obsidian syntax, callouts, wikilinks, Mermaid, Canvas, or beautification, load `obsidian-md-ac` first for formatting decisions, then use this skill for the vault write and verification.

### ⚠️ Verify path before writing — do NOT trust memory or context alone

When a file path is mentioned in conversation context (e.g. a summary from a prior session, a user's offhand reference), **always verify with `search_files(target="files")` before writing**. Context summaries can be stale or incorrect. Common failure mode: assuming a file lives under a subfolder like `三省六部_Hermes/10_制度/` when it actually lives in the flat `00-Inbox/` directory. One `search_files` call before `write_file` saves a misplaced file. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Save conversation artifacts to Inbox and return a link

When the user asks to save a plan, draft, or conversation-derived artifact to the Obsidian inbox:

1. Resolve the vault path first. Prefer `OBSIDIAN_VAULT_PATH`; if the documented fallback `~/Documents/Obsidian Vault` is missing, look for real vaults under likely roots such as `~/Documents/Obsidian/*/.obsidian` and use the user's active vault (for this setup, commonly `~/Documents/Obsidian/<VaultName>`). Do not hardcode this if discovery shows a different vault.
2. Use the vault's `CLAUDE.md` / local conventions if present. For <VaultName>'s vault: `00-Inbox/` is flat, notes need YAML frontmatter, Chinese filenames are fine, and `00-Inbox` is the correct raw capture target.
3. Create the note with `write_file` under `00-Inbox/`, using a concise descriptive filename plus date, e.g. `00-Inbox/主题_YYYYMMDD.md`.
4. Verify by reading back the first lines of the file.
5. If qmd is configured for the vault, refresh searchability after material updates: `qmd update -c <vault-collection>` then `qmd embed -c <vault-collection>`. Do not fail the save if qmd is unavailable or a collection is not configured.
6. Return both the filesystem path and an Obsidian URI: `obsidian://open?vault=<VaultName>&file=<urlencoded relative path>`.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Obsidian version / update checks

When asked whether Obsidian needs an update, do **not** rely only on `/Applications/Obsidian.app/Contents/Info.plist` or Spotlight `kMDItemVersion`. On macOS, Obsidian can run a newer downloaded `obsidian-<version>.asar` from `~/Library/Application Support/obsidian/` while the installer / app bundle still reports an older version. This creates outputs like `1.12.7 (installer 1.9.14)`.

Preferred check:

```bash
/Applications/Obsidian.app/Contents/MacOS/obsidian version 2>&1
```

Interpretation:

- `X.Y.Z (installer A.B.C)` means the **running app package** is `X.Y.Z`, while the installed wrapper / Electron launcher is `A.B.C`.
- If `X.Y.Z` is current but installer is old, tell the user Obsidian itself is updated, but downloading the latest installer may improve CLI/Electron support and remove the warning.
- The official Obsidian CLI can control vault/app features, but it does not update the desktop installer itself; use the official download/installer for that.

## Obsidian CLI

Use the `obsidian` CLI to interact with a running Obsidian instance for operations the filesystem approach can't do: daily notes, tasks, backlinks, tags, property operations, and plugin development.

Quick reference:

```bash
obsidian read file="My Note"
obsidian create name="New Note" content="# Hello" template="Template" silent
obsidian daily:read / daily:append content="- [ ] task"
obsidian search query="term" limit=10
obsidian property:set name="status" value="done" file="My Note"
obsidian tasks daily todo
obsidian backlinks file="My Note"
```

For plugin development (reload → errors → screenshot → console):

```bash
obsidian plugin:reload id=my-plugin
obsidian dev:errors
obsidian dev:screenshot path=screenshot.png
obsidian dev:console level=error
```

Full reference: `references/obsidian-cli.md`

## Obsidian Bases (.base files)

Create database-like views of vault notes with filters, formulas, and summaries. Supported view types: `table`, `cards`, `list`, `map`.

Provide a `.base` YAML schema with `filters`, `formulas`, `properties`, `summaries`, and `views` sections. Always validate YAML syntax and check that referenced properties/formulas exist.

Full reference with schema, formula syntax, view types, and complete examples: `references/obsidian-bases.md`

## Web content extraction (Defuddle)

Extract clean markdown from web pages using Defuddle CLI. Prefer this when the user provides a URL to save to vault as a note — it strips navigation and clutter, reducing token usage.

```bash
npm install -g defuddle  # if not installed
defuddle parse <url> --md
defuddle parse <url> --md -o content.md
```

## Obsidian Sync

When working with notes that may have been modified on other devices, ensure Obsidian is running so the official Obsidian Sync service can sync changes.

**Trigger sync programmatically:**
```python
# ~/.hermes/skills/auto-diary/scripts/obsidian_sync.py
import subprocess

def sync_obsidian():
    result = subprocess.run(["pgrep", "-x", "Obsidian"], capture_output=True)
    if result.returncode == 0:
        return {"status": "already_running", "message": "Obsidian sync active"}
    
    subprocess.Popen(
        ["open", "-a", "Obsidian", "--args", "--vault", vault_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return {"status": "launched", "message": "Obsidian started, sync connecting"}
```

**Open note via URI:**
```bash
open "obsidian://open?vault=VaultName&file=path/to/note.md"
```

## qmd 集成（推荐用于大型知识库）

对于包含数百+笔记的 vault，使用 qmd 进行高效搜索而非遍历文件：

```bash
# 1. 将 Obsidian vault 添加为 qmd 集合
qmd collection add ~/Documents/Obsidian/<VaultName> --name <vault-collection>

# 2. 生成向量嵌入
qmd embed -c <vault-collection>

# 3. 搜索（BM25/向量/混合）
qmd search "关键词" -c <vault-collection> -n 5
qmd vsearch "概念查询" -c <vault-collection> -n 3
qmd query "自然语言问题" -c <vault-collection> -n 3

# 4. 通过 docid 获取完整内容
qmd get "#abc123"
```

After materially updating notes that the user expects to become part of the searchable knowledge base, also refresh the qmd index and embeddings:

```bash
qmd update -c <vault-collection>
qmd embed -c <vault-collection>
```

Pair this with the Obsidian Sync check above so the note is both synced and searchable. Do not put transient run logs or temporary task IDs into long-term memory; keep durable architecture/procedure updates in Obsidian or skills.

When making backups before rewriting large notes, store backups outside the vault (for example `~/.hermes/backups/obsidian/`) unless the user explicitly wants them as vault artifacts. Backups inside the vault are indexed by qmd and can pollute future search results as duplicate sources; if this happens, move the backup out and run `qmd update` again.

**qmd 优势**: 96% token 减少，只返回相关片段而非完整文件。详见 `qmd` skill。

---

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Vault path resolved to concrete absolute path (no `$OBSIDIAN_VAULT_PATH`)?
- [ ] iCloud dataless check done before concluding a file is empty?
- [ ] File path verified with `search_files` before `write_file` (not trusting context alone)?
- [ ] For Bases or Canvas: YAML/JSON validated + referenced properties exist?
- [ ] Backups stored OUTSIDE vault unless user explicitly wants them inside?
- [ ] qmd index refreshed after material note updates?

**Every box must honestly pass before returning results. If unchecked, go back.**
