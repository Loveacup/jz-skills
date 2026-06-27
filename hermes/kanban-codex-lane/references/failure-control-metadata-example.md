# Codex lane failure-control metadata example

Use when a Codex lane is killed, times out, is rejected, or is retried with a narrower prompt. The goal is to leave enough evidence for a reviewer and for the next run to avoid repeating the same failure.

## Control loop

```text
monitor → detect timeout/off-scope/stuck → kill → comment evidence → retry/block
```

Do not silently retry. Every kill or timeout should leave a concrete reason, elapsed time, last useful log excerpt, changed-file summary, kill reason, artifact paths, and next action.

## Example: timed out, then retried

```json
{
  "codex_lane": {
    "used": true,
    "mode": "exec",
    "worktree": "/tmp/kanban-phase0-codex-lane-doc-sample",
    "branch": "codex/phase0-failure-control-example-20260612",
    "command": "codex exec --sandbox workspace-write <prompt>",
    "result": "timed_out",
    "accepted_commits": [],
    "rejected_reason": "Killed after 12 minutes: no useful output and no relevant diff for the allowed files.",
    "failure_control": {
      "elapsed_seconds": 720,
      "trigger": "timeout_no_useful_output",
      "kill_reason": "Worker runtime budget nearly exhausted with no useful output and an empty diff.",
      "kill_action": "process.kill",
      "last_log_excerpt": "Last 40 lines showed repeated planning text and no file write.",
      "changed_files": [],
      "diff_stat": "empty",
      "artifact_paths": ["/tmp/kanban-phase0-codex-lane-doc-sample/codex.log"],
      "next_action": "retry_with_narrower_prompt",
      "retry_prompt_delta": "Ask only for references/failure-control-metadata-example.md; forbid SKILL.md edits on retry.",
      "retry_after_kill": {
        "previous_result": "timed_out",
        "evidence_paths": ["/tmp/kanban-phase0-codex-lane-doc-sample/codex.log"],
        "prompt_delta": "Narrow allowed files and require a readable diff or explicit no-change report."
      }
    },
    "tests_run": [
      {"command": "git -C /tmp/kanban-phase0-codex-lane-doc-sample status --short", "exit_code": 0, "owner": "hermes"}
    ],
    "artifacts": ["/tmp/kanban-phase0-codex-lane-doc-sample/codex.log"]
  }
}
```

## Example: rejected for off-scope edits

```json
{
  "codex_lane": {
    "used": true,
    "mode": "exec",
    "worktree": "/tmp/t_123-codex-lane",
    "branch": "codex/t_123/20260612050600",
    "command": "codex exec --sandbox workspace-write <prompt>",
    "result": "rejected",
    "accepted_commits": [],
    "rejected_reason": "Rejected: Codex modified files outside the allowed scope.",
    "failure_control": {
      "elapsed_seconds": 185,
      "trigger": "off_scope_file_change",
      "kill_reason": "Codex edited a file outside the allowed scope.",
      "kill_action": "process.kill",
      "last_log_excerpt": "Codex started broad cleanup despite prompt constraints.",
      "changed_files": [
        "SKILL.md",
        "../unrelated-skill/SKILL.md"
      ],
      "diff_stat": "2 files changed; one outside allowed scope",
      "artifact_paths": ["/tmp/t_123-codex-lane/rejected.diff"],
      "next_action": "block_for_review",
      "retry_prompt_delta": null
    },
    "tests_run": [],
    "artifacts": ["/tmp/t_123-codex-lane/rejected.diff"]
  }
}
```

## Reviewer checklist

- Does `rejected_reason` name the concrete failure, not just "bad output"?
- Are elapsed time, trigger, and changed files recorded?
- Is the kill reason explicit enough to explain why the lane was stopped?
- Is there enough log/diff evidence to reproduce the decision?
- If retried after kill, do `retry_prompt_delta` and `retry_after_kill.evidence_paths` explain what changed and where the prior evidence lives?
- If blocked, are artifact paths available for the reviewer?
