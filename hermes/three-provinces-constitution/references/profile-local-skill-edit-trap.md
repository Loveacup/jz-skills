# Profile-local skill edit trap

Skills are profile-local in Hermes. A Kanban worker running under `--assignee archivist` or another specialist profile may update only that profile's skill copy, not the default skill library and not the current regent profile.

## Symptom

A worker reports that a skill was updated and even passes its own review, but the user-facing/default channel still loads the old version.

## Required verification

When the user says “主频道的 skill”, “默认频道的 skill”, or asks to update a skill for everyday use:

1. Identify target profile(s): usually default `~/.hermes/skills/...`, current `regent`, and any worker profile that generated the draft.
2. Require execution tasks to name exact target paths, not only a skill name.
3. After completion, independently read back or hash the intended target files.
4. If only the worker profile changed, issue a narrow sync/fix task before final response.

## Safe sync pattern

Use the worker profile version as source only after review, then copy/sync to the intended target profile(s) and verify:

- `version:` line
- expected key phrases/sections
- line count or SHA256 across copies
- no unintended file edits

Do not store one-off task IDs or report progress in long-term memory; this is a procedural pitfall for skill/governance workflows.
