# Jz-Plugin × ECC Roadmap Pattern (2026-06-05)

Use this reference when the user asks to use Claude Code to optimize a roadmap / architecture document by reading local docs, source code, and external project references.

## Trigger example

User asks: “直接拉起 CC，优化 jz-plugin 路线图文档（看源码，整理思路，吸收 ECC 的优点）”.

## Pattern

1. **Load governing skills first**: `claude-code`, the relevant document/vault skill (`obsidian`), and source-reading/research skills when the task includes external code.
2. **Respect existing CC occupancy**: scan all tmux sessions for `●` and thinking glyphs (`✻/✶/✽/✳`). If busy, ask whether to wait or create an isolated session. If user chooses isolation, create a fresh `hermes-cc-{task}-{ts}` session in a neutral `/tmp/<task>` workdir.
3. **Write a context file** under `/tmp/cc-context-<task>.md` rather than sending a long inline prompt. Include:
   - exact target document path(s)
   - “edit only these files” boundaries
   - source clone paths and HEADs
   - relevant Obsidian/source paths already known
   - red lines (e.g. do not install external project hooks; do not touch live skills)
   - request for discussion brief + changed files + verification evidence
   - optional CQI handoff path if relevant
4. **Let CC do evidence collection before editing**: instruct it to read local OB docs, source code, key files from the external project, and light web/docs research if the user asked for “多讨论 / 网络 / 论文”.
5. **Monitor visibly**: after every `capture-pane`, send the full `📡 CC Agent Team` progress block. Long xhigh/max thinking is normal if tokens keep increasing.
6. **Verify after CC reports done**:
   - read the target document from disk
   - check expected new sections/keywords with search
   - parse any `/tmp/cc-cqi-events-*.jsonl` handoff if produced
   - inspect final CC pane for residual input
7. **Residual input guard**: if CC leaves a suggested next action in the `❯` input line (e.g. “A 对齐上游标准，开始 P2 manifest 骨架”), treat it as unapproved text, not authorization. Try `C-u`/`Escape`; if it remains and the phase is complete, kill the isolated tmux session rather than risk Enter executing it.

## Good deliverable shape

- One optimized class-level roadmap / architecture document, not a pile of side notes.
- A concise user-facing summary: files changed, what changed, verified evidence, and the one real decision point left.
- If CC created CQI handoff, leave it in `/tmp` and explicitly say whether it was ingested or only validated.

## Session lesson

The useful update was not “ECC is good”. The reusable technique is: **use CC as a discussion+evidence+rewrite engine for a single authoritative roadmap, while Hermes enforces boundaries, progress visibility, and disk verification.**
