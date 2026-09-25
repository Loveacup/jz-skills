# Blip RPC upgrade validation

Policy (user decision 2026-09-25): the adapter no longer hard-pins one Blip build. Every run checks the installed version/build against `scripts/verified-builds.json`. A build outside that list is usable only while the read-only compatibility probe passes, and becomes verified only through a real Completed send on that exact build. The adapter stays unofficial and fail-closed.

## A. Detect (every session)

- **A1 — Version check.** Run `python3 <skill-dir>/scripts/blip-rpc.py doctor`. `build_verified: true` → done; skip the rest of this file.
- **A2 — Functional probe.** For `build_verified: false`, read `compatibility_probe`:
  - `passed` → go to C (no code change needed).
  - `failed` (with `probe_error`) → go to B.
  - Transport failures (`socket_unavailable`, `rpc_unavailable`, …) are not incompatibility. Report them; do not adapt code for them.

The probe decodes the allowlisted `GetState` fields and requires exactly one self device, one own user ID, and complete names/IDs on own rows. It reads no database, credential, or raw state, and never creates a transfer.

## B. Adapt (only when the probe fails)

- **B1 — Bounded investigation.** Compare the new build against the contract in `headless-rpc.md`: DRPC framing, the two allowlisted methods, `frontend.State` fields `500`/`600`, the user/device/transfer field numbers, status values, event `type_url`s, and the account `PeerId` encoding. Use static evidence from the installed app bundle (strings, the embedded `service.proto` descriptor, exported symbols). Do not inspect Blip databases, the keychain, registration/auth payloads, emails, or raw live state. Do not publish descriptor payloads.
- **B2 — Change only what moved.** Update the parser/encoder for the moved fields or methods. Keep every existing safety check: exact recipients, fresh peer re-resolution, prepared-content verification, no retries, and redaction. Do not add wildcards, environment overrides, or silent fallbacks. Never add a build to `verified-builds.json` by hand.
- **B3 — Offline suite.** From the skill root, `python3 -m unittest discover -s tests -p 'test_*.py'` must exit `0` before any live probe. Add or adjust synthetic tests for every changed field.
- **B4 — Re-probe.** `doctor` must now report `compatibility_probe: "passed"`, and `devices` must return valid minimized JSON. Pass that snapshot to `inventory.py sync`; the shared inventory must survive unchanged, and new entries must still produce questions. If the probe still fails, stop and report the exact `probe_error`; keep the last verified revision in production.

## C. Accept (first real send on the new build)

- **C1 — Real, user-requested send.** Only a current user request naming the file and recipient counts, under the normal authorization rules. Do not invent test transfers. `send` binds the UUID to the installed build in the private ledger before the create mutation.
- **C2 — Completion.** Run `watch --transfer-id UUID` until `Completed` (8) with `error_scope: none`. `Invited`, `Pending`, and `Active` are not acceptance. If the receiver has not accepted yet, keep the UUID and re-run `watch` later; never resend.
- **C3 — Record.** Run `record-verified --transfer-id UUID`. It appends the build to `verified-builds.json` only for this adapter's outgoing, error-free Completed transfer on that exact build.

## D. Deploy and publish (automatic after C3)

- **D1 — Deploy.** The canonical directory `~/.omp/agent/managed-skills/blip-transfer` is the deployed copy that runtimes link to. Re-run the offline suite there; it must exit `0`.
- **D2 — Publish.** Standing user authorization (2026-09-25) covers publishing to `Loveacup/jz-skills` `main`, path `shared/blip-transfer` only:
  1. `git fetch origin`.
  2. Create a clean worktree from `origin/main`; never use the dirty main checkout.
  3. Copy the canonical skill files (excluding `__pycache__`) into `shared/blip-transfer`.
  4. Check the staged diff: only `shared/blip-transfer`, and no private inventory, transfer UUIDs, device names, emails, personal paths, or audit evidence.
  5. Commit and fast-forward `git push origin HEAD:main`.

  Never force-push. If the push is rejected, re-fetch, rebuild the worktree, and repeat.
- **D3 — Evidence.** Keep sanitized local evidence under `~/.agents/audits/<date>/blip-transfer-<version>-adapt/`: doctor/probe output, suite result, status summary, and published commit. The transfer UUID stays in an owner-only private file only.

## E. Rollback

Restore the previous published revision of `shared/blip-transfer` into the canonical directory. The private inventory, ledger, and initialization files live outside the skill and are unaffected. After restoring, run the offline suite and `doctor`. A restored adapter that fails the probe on the installed build stays fail-closed. Downgrading the Blip app itself is a separate, user-authorized action.

## Historical baseline

Build `1.2.0`/`20260914015615` was promoted on 2026-09-22 through the former exact-pin U1–U18 gates: a locked account-scope transfer reached exact-UUID `Completed` (8), and an independent audit passed. Evidence is in `~/.agents/audits/2026-09-22/blip-transfer-1.2.0-upgrade/`.
