# CC prediction text after artifact completion（2026-06-30）

## Symptom

After CC has actually completed the task and written the expected artifact, `cc-wait-decision.sh` may return:

```json
{
  "decision": {"state": "artifact_satisfied_no_marker", "action": "read_artifacts"},
  "pane": {
    "signals": ["active_pane", "prompt_text_prediction_candidate", "prompt_text_present"],
    "prompt": {"text_excerpt": "commit this", "kind": "prediction_candidate"}
  }
}
```

The pane can show a tempting command/prediction such as:

```text
❯ commit this
```

This is not an instruction from the user and not proof that CC needs another turn.

## Correct handling

1. If the expected artifact exists and `decision.state == artifact_satisfied_no_marker`, read the artifact and audit the actual repo state.
2. Do **not** press Enter on `prompt_text_prediction_candidate` text such as `commit this`.
3. Do **not** let CC commit/push unless the user explicitly asked CC to own that side effect.
4. Delegator/Hermes should own final verification, `git diff/status`, commit, push, and OB closeout.
5. If the prediction text is stale or risky, leave it alone or clear it only if it blocks later work; never treat it as a task continuation.

## Why

In P2-B5 `bilibili-video-analyzer`, CC completed implementation, wrote `/tmp/cc-bili-p2b5-done.md`, and reported tests passing. The pane then displayed `commit this` as a prediction candidate. Hermes ignored it, independently audited the diff, ran tests, used OMP for review, then performed the commit/push itself. This avoided accidentally delegating an external side effect to CC after the implementation task was already complete.
