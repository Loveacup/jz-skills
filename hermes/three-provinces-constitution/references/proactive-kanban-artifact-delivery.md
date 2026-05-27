# Proactive Kanban completion delivery

This reference records a governance-level correction: a Kanban chain that has reached zero active cards is not fully closed until the user receives the final artifact, when one exists.

## Rule

When a final-result or final card contains an artifact path (PDF, HTML, image, audio, video, archive), the completion report must include a literal `MEDIA:/absolute/path` line. Reporting only "done", only a JSON result path, or only a local file path is insufficient.

## Why

The user explicitly objected when the clearance reporter ran but did not proactively bring the final PDF into the conversation. For this user, proactive completion means: summarize + attach final deliverable.

## Checks

- Confirm board state (`active_count == 0`) and identify the latest final-result.
- Extract artifact paths from task result/summary fields.
- Verify each extracted path exists before attaching.
- Ensure the report output includes `MEDIA:` lines unchanged.
- Verify scheduler delivery log after cron runs.

## Related implementation note

See `kanban-orchestrator/references/kanban-clearance-artifact-delivery.md` for script/prompt implementation details.
