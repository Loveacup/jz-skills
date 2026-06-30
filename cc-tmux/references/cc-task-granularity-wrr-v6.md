# CC task granularity and launch pattern — WRR v6 lesson

Context: WRR v6 P0 implementation initially looked like “CC unreliable”, but the user corrected that diagnosis: CC is reliable; failures usually mean bad delegation shape.

## Failure pattern observed

- Sending 5 large implementation packages in one CC turn caused prolonged THINKING / no write output.
- Long multi-line `send-keys` instructions can be swallowed/queued by the interactive UI.
- `-p` print mode is not appropriate for interactive coding tasks.
- High/xhigh effort can worsen overthinking on implementation work.

## Durable rule

Treat CC implementation failures as a **task-shaping problem first**, not a model reliability problem.

Use:
1. Start a clean tmux CC session.
2. Write the task to `/tmp/cc-task-<name>.md`.
3. Send one short single-line instruction: `Read /tmp/cc-task-<name>.md and implement only that task.`
4. Keep packages small: roughly ≤3 files or ≤10 lines of task description.
5. Use event marker / `cc-wait-marker.sh` for completion.
6. Audit the diff yourself; do not rely on self-report.

Codex exec can still be used for small one-shot patches, but do not encode “CC is unreliable” as the lesson. The lesson is correct CC invocation and task granularity.
