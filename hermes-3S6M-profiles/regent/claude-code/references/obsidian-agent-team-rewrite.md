# Obsidian note restructuring with Claude Code agent team

Use this when the user asks Claude Code / agent team to improve a large Obsidian note, methodology document, workflow design, or wiki page.

## Pattern from session

1. Resolve the concrete vault path and target note path.
2. Read the target note and nearby related notes/search snippets first; identify whether the issue is structure, bloat, stale operational detail, or unclear workflow.
3. Back up the original note **outside the vault** (for example `~/.hermes/backups/obsidian/`) so qmd/Obsidian search does not index the backup as a duplicate source.
4. Write a temporary task brief under `~/.hermes/tmp/` with:
   - target file path;
   - user goals;
   - hard constraints (frontmatter, language, no tables, line budget, must-keep concepts);
   - requested team roles;
   - verification checklist.
5. Use Claude Code dynamic agents via `--agents` when appropriate. Example roles that worked well:
   - `information-architect`: evergreen-note structure, hierarchy, linkability;
   - `workflow-critic`: executable workflow, anti-overengineering;
   - `editor`: Chinese compression, deduplication, readable Markdown without tables.
6. Run Claude Code with bounded permissions, e.g. `--permission-mode acceptEdits --allowedTools 'Read,Edit,Write,LS' --max-turns 20 --output-format json` from the vault root.
7. Verify the artifact yourself:
   - frontmatter preserved;
   - line count / byte count dropped as intended;
   - no Markdown tables if Telegram/mobile readability matters;
   - required terms/conclusions still present;
   - headings are coherent;
   - Claude Code report says agents were actually invoked, not merely described.
8. If the note is part of qmd-searchable knowledge, run `qmd update -c <collection>` and `qmd embed -c <collection>` after edits.
9. If an accidental backup was created inside the vault, move it outside and refresh qmd again to remove it from the index.

## Prompt constraints that produced a good result

- “适当简化，不要写成百科大全；变成可执行、可维护、适合作为知识库常青方法论的主文档。”
- “不要使用 Markdown 表格；改用 bullet list。”
- “保留核心概念 X/Y/Z，删除或压缩过期/低价值流水账、过细清单、易过期模型矩阵。”
- “控制在约 300-500 行。”
- “若内容应拆分，只在末尾列出建议，不要擅自创建新文件。”

## Executive decision-brief variant

When the user asks to turn a detailed Obsidian methodology / strategy note into a “给决策者看的版本”, create a **new brief note** rather than overwriting the source unless explicitly asked. This is a distinct transformation from summarization:

- Reframe technical/operational content into decision language: proceed / pause / stop, budget gates, risk exposure, resource commitment, owner accountability, and executive approvals.
- Start with a “30 秒短结论” that gives the recommendation before the rationale.
- Keep the original deep note as the source of truth and link to it; the executive brief should avoid reproducing implementation detail.
- Use dynamic Claude Code agents that match the decision lenses, for example: strategy/CEO, CFO/risk, growth/pricing, compliance, and executive editor.
- Include at least one Go/No-Go gate table, a roadmap table, and a compact KPI dashboard when the topic involves investment or rollout decisions.
- Verify with keyword checks for the decision concepts the user requested, not only Markdown syntax. If a required phrase is missing because the writer used an abbreviation (for example AHR but not Account Health), patch the brief so both executive and technical readers can search it.

## Verification note

For Telegram delivery, report in bullets and include changed file path, backup path if any, qmd refresh status, and what was preserved/removed. Avoid tables in the final user-facing summary when the task itself emphasized mobile/Telegram readability.
