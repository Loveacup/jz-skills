# Kanban clearance artifact delivery

When a Kanban chain reaches zero active tasks and a final-result is available, the clearance reporter must deliver the actual artifact, not only a status summary or result JSON path.

## Durable lesson

The user considers "board cleared" without the final artifact attached to be a failed delivery. If a final task/result mentions a PDF, HTML, image, audio, or other file, the cron report must include a literal `MEDIA:/absolute/path` line so Telegram delivers it natively.

## Implementation pattern

1. The pre-run clearance script should extract absolute existing file paths from task `result`, `summary`, `latest_run_summary`, and similar fields.
2. Include extracted paths in agent-mode JSON as `artifact_paths` per task.
3. The cron prompt must explicitly instruct the agent to append one `MEDIA:<absolute_path>` line per artifact, preserving the full absolute path.
4. Verification requires an end-to-end run: inspect the generated cron output markdown and scheduler log for delivery, not just script dry-run success.
5. Avoid brittle providers for critical completion reports; if the report must be proactive, prefer the profile's stable main provider/model over experimental or transiently unreliable models.

## Acceptance checklist

- `active_count == 0` and latest final-result is unreported.
- Report summarizes completed tasks briefly.
- Report includes the result inbox path.
- Report includes `MEDIA:/absolute/path/to/final-artifact.pdf` when an artifact exists.
- Scheduler log shows the job delivered to the intended target.
- State file records the latest final-result as reported only after successful run.
