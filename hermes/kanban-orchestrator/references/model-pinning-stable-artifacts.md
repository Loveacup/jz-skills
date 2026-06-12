# Kanban Model Pinning + Stable Artifact Handoff

Use when the user asks a Kanban/swarm run to use a specific model across all collaborating agents, or when the final deliverable is a file/PDF/audio artifact.

## Model pinning checklist

1. Discover actual participating profiles (`hermes profile list` or the swarm spec).
2. For each worker/verifier/synthesizer profile, update **both**:
   - `model.default`
   - `fallback_providers`
3. Restart/kickstart each gateway before dispatch so the worker process reloads config.
4. Verify the configured profile set before creating the swarm.
5. If a profile hits provider content-risk or transient errors, recover inside the pinned model constraint first (retry, soften wording, reassign to another pinned profile). Do not silently change model.

## Stable artifact handoff

Kanban scratch workspaces may be cleaned after a card completes. For deliverables the user must receive later:

- Prefer creating the publisher/finalizer card with `--workspace dir:/stable/path`.
- If the finalizer already completed in scratch, immediately create a persistence/regeneration card that writes files to a stable workspace under the active profile, e.g.:
  `~/.hermes/profiles/<profile>/workspaces/<task-name>/final-artifacts/`
- Final response should reference the stable path and attach `MEDIA:` files from that path, not from a scratch workspace.

## Verification before completion

- `hermes kanban show <task>` says final card is `done`.
- `ls -lh` confirms each artifact exists and has plausible size.
- For PDFs, run text extraction / sentinel checks when available.
- For audio, verify the file exists and is non-empty before reporting TTS success.