# Reused artifact mtime follow-up pattern

Use this when a CC session already produced `/tmp/<result>.md`, then you send a follow-up task that should update the same artifact.

## Problem

`cc-wait-decision.sh --expect /tmp/<result>.md` can report `artifact_satisfied_no_marker` because the artifact exists from the previous turn, especially when the command uses the default `after=0`. That is not proof the follow-up ran.

## Correct handling

1. Capture the artifact mtime before sending the follow-up:
   ```bash
   before=$(stat -f %m /tmp/result.md 2>/dev/null || echo 0)
   ```
2. Send one single-line follow-up instruction that points to a `/tmp/*.md` task file.
3. If `cc-wait-decision` reports artifact satisfied, compare current mtime to `before` and inspect `git diff --name-only` for the expected follow-up file.
4. Only accept the artifact when either:
   - mtime is newer than `before`, and
   - expected diff/artifact content is present.
5. If the follow-up task text remains visible in the input box, press Enter once only if it is clearly the freshly sent single-line task; do not resend.

## Why this matters

In WRR v6.1 Package B, the initial CC result file existed before a follow-up parity-test update. `cc-wait-decision` initially treated the old result as satisfying the expectation. Tracking mtime and diff showed the follow-up had not completed yet; later the mtime updated and `test_registry_bridge.py` appeared in the diff.
