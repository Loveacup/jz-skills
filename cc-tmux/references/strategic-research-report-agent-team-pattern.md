# Strategic Research Report Agent Team Pattern

Use this when the user asks for a high-quality strategic/deep research report with an explicit pipeline such as `WRR → Codex planning → CC agent team → Obsidian`.

## Trigger

- User asks for a deep market/industry/local-government research report.
- User explicitly wants WRR grounding, Codex planning, and CC/agent-team execution.
- Final artifact must be a polished Markdown note in Obsidian, not just a chat summary.

## Proven workflow

1. **WRR foundation first**
   - Treat the task as `research` mode, not quick discovery.
   - Collect and label sources into: official facts, search-summary leads, strategy inferences, and to-verify gaps.
   - Build a compact `/tmp/<topic>-research-pack.md` with source IDs and extracted facts.

2. **Codex planning-only pass**
   - Give Codex the research pack and ask for a planning-only output to `/tmp/<topic>-codex-plan.md`.
   - Codex should define: final report outline, worker split, each worker's task package, quality gates, risk/blank-spot list.
   - Verify the plan exists and contains the requested sections before spawning CC.

3. **CC agent team split**
   - Use small, role-specific task files under `/tmp/` and one-line tmux prompts: `请读取 /tmp/task-X.md 并严格执行，直接写目标文件。`
   - For a 3-worker strategic report, a good split is:
     - **A — policy/regulation/market mechanism**:制度、监管、赛道优先级。
     - **B — industry/spatial/customer map**:产业、区域、客户与渠道地图。
     - **C — product/sales/action plan**:产品体系、BD打法、12个月计划、风险。
   - Require each worker to write `/tmp/<topic>-cc-A.md` and a `/tmp/<topic>-cc-A.done` marker (same for B/C). Do not rely on pane scrollback for long outputs.
   - If C may start before A/B finish, tell it to read A/B if present but be self-contained if absent.

4. **Hermes final synthesis**
   - Read all worker outputs; do not paste them wholesale.
   - Merge into a decision-driven report: conclusion first, then evidence, then action implications.
   - Preserve source IDs and label official facts vs search-summary leads vs inferences.
   - Include at least: core conclusion, source table, market/industry base, policy mechanism, spatial/customer map, segment priority, products, channels, 12-month plan, risks, next evidence gaps, source links.

5. **Obsidian save and verification**
   - Save to the vault's `00-Inbox/` unless the user named another folder.
   - Respect vault frontmatter/format from `CLAUDE.md` or `AGENTS.md` when present.
   - Verify: file exists, frontmatter OK, key numbers/claims present, required sections present, and CC sessions are cleaned up.

## Quality gates

- Do **not** let the reference material's city/industry logic leak into the target city. Use the reference only as structure unless evidence matches.
- Any search result not fully fetched should be marked as a lead / needs verification.
- Distinguish strategy inference from official fact.
- Final deliverable should be directly usable by BD/strategy teams, not a policy digest.
- For external-facing reports, keep a P0 evidence-gap list for procurement, tender, competitor, named-customer, and budget confirmation.

## Notes from 2026-07-01 Bozhou case

- Three-worker CC team worked well for a municipal market report when each worker had a narrow, file-output task.
- CC done markers plus file size checks were enough for orchestration; Hermes still had to read and synthesize.
- The final report was saved to `00-Inbox/亳州市水土保持市场拓展深度研究.md` and verified by line count, frontmatter, key numbers, and section checks.
