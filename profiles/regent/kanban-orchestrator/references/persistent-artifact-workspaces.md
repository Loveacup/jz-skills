# Persistent artifact workspaces for Kanban chains

Use this when one Kanban stage generates files that another stage must inspect or deliver: PDFs, screenshots, HTML reports, exported decks, audio/video, generated datasets, etc.

## Failure pattern

A render/build worker writes correct artifacts into a scratch or temporary workspace. The worker completes, but before the auditor/final-reviewer runs, cleanup removes the directory. Downstream cards then block with "artifact missing" even though the actual generation succeeded.

## Correct pattern

1. Before creating the chain, choose a durable workspace:
   - `~/.hermes/workspaces/<date-or-task-slug>/`
   - Example: `~/.hermes/workspaces/morning-news-20260526-mobile-v3/`
2. Put the workspace path in every stage's card body.
3. Require the producer to write final artifacts there, not under scratch.
4. Require completion summaries to include:
   - absolute workspace path
   - exact artifact filenames
   - quick verification facts (size/pages/checksums/sentinel checks as appropriate)
5. Downstream audit/final cards should read from that path and fail only if the expected durable files are missing.

## Recovery when scratch was already GC'd

Do not try to audit missing scratch files. Create a narrow rerender card targeting a persistent workspace, then chain audit/final-review to the rerender card. Mark the old audit/final cards blocked or superseded as audit trail.

## Rule of thumb

If the user-facing deliverable is a file, or if any later profile must open/render/inspect a file, scratch is not an acceptable handoff boundary. Use `~/.hermes/workspaces/` and write the path into Kanban summaries.