# Blip RPC upgrade validation

This checklist governs any change away from the currently verified private local RPC contract: Blip version `1.1.16`, build `20260425132215`. The adapter is unofficial and fail-closed. A newer version or build is unsupported in production until every gate below passes for one exact final revision. Keep the production guard unchanged during investigation; an isolated candidate may use one explicitly reviewed exact candidate pin, never a relaxed guard.

For every gate, record `PASS` or `FAIL`, the date, the reviewer, and a pointer to the sanitized evidence. Any `FAIL`, missing evidence, ambiguous result, or changed candidate build stops promotion. Investigation artifacts are not permission to send or publish.

## 1. Freeze the baseline and candidate

- [ ] **U1 — Exact identity recorded.** Record the current and candidate `CFBundleShortVersionString` and `CFBundleVersion`, plus SHA-256 hashes of the application executable and every shipped framework or descriptor-bearing artifact used as protocol evidence. Record the hashing tool and exact paths so another reviewer can reproduce the hashes. PASS only when the installed candidate matches the recorded build and hashes.
- [ ] **U2 — Public static contract recorded.** In a sanitized artifact, record only the static invocation contract needed by the adapter: local method names, DRPC framing/version evidence, protobuf message and field numbers, `Any.type_url` values, relevant status values, and the source path plus hash of each static descriptor or binary that supports them. PASS only when the contract can be checked without runtime state. Do not publish descriptor payloads or extracted data unless their redistribution is authorized.
- [ ] **U3 — Privacy boundary preserved.** Confirm that collection inspected no Blip database, keychain item, credential, registration/auth payload, email/contact data, device inventory, unrelated transfer, or raw live RPC state. Runtime payloads are not substitutes for static descriptor evidence. PASS only if the evidence contains no private identifier or secret.
- [ ] **U4 — Production and candidate are distinct.** Confirm the checked-in and installed production helper still accepts only the recorded baseline version/build and rejects the different candidate. Create an explicitly identified isolated candidate source tree, record its absolute path, and leave runtime links and production files unchanged. After U1–U3 establish the candidate contract, set only that isolated tree to the exact candidate version/build; no wildcard, override, fallback, or weakened guard is allowed. Offline fixtures use disposable state. Live candidate probes use the existing private inventory read-only until the separately authorized initialization/send stages; never copy private records into the candidate tree. PASS only if socket rules, privacy allowlists, send guards, GUI lock guards, and authorization checks remain intact.

## 2. Prove compatibility without sending

- [ ] **U5 — Candidate implementation is bounded.** Compare the candidate static contract with the baseline and account for every changed method, event, field, status, framing rule, limit, and error behavior. Unknown or conflicting schema evidence is a failure, not a reason to guess compatibility.
- [ ] **U6 — Candidate offline regression suite passes first.** From the isolated candidate skill root identified in U4, run:

  ```sh
  python3 -m unittest discover -s tests -p 'test_*.py'
  ```

  PASS only if the entire offline suite exits `0` before any live RPC probe. The suite must not open Blip, connect to its socket, read private inventory, inspect credentials/databases, use the GUI, or create/send a transfer. It must cover wrong-build rejection, bounded/parsing failures, mutation non-retry behavior, delivery-claim rules, and initialization/device-annotation preservation. Preserve existing schema-1 inventory fields and optional `label`, `aliases`, and `notes` across `init` and `sync`; annotations must remain non-authoritative and must never become recipient resolution or standing send authorization.
- [ ] **U7 — Existing safety behavior remains exact.** Confirm offline tests still reject missing or duplicate exact recipients, unsupported sources, changed source identity, wrong-owner/non-socket paths, malformed or oversized responses, and ambiguous mutation outcomes. PASS only if no test was weakened, deleted, or rewritten merely to accept the candidate.

## 3. Read-only live validation in every runtime

Use the exact candidate tree only after U1–U7 pass. In a fresh real session of each supported runtime—Hermes, Claude Code, Codex, and OMP—discover the installed skill normally, then explicitly identify the authorized candidate path for the probes. Do not repoint production runtime links or present four invocations from one host shell as runtime coverage.

For each runtime, run the documented commands against the installed candidate:

Set `SKILL` to the same absolute isolated candidate directory recorded in U4. Record its source hashes with each runtime's result; do not run the unchanged production helper, a different copy, or a stale candidate.

```sh
python3 "$SKILL/scripts/blip-rpc.py" doctor
python3 "$SKILL/scripts/blip-rpc.py" devices
```

- [ ] **U8 — Four real `doctor` probes pass.** Each runtime must report the exact candidate version/build, valid current-user Unix socket, reachable read-only RPC, and lock state through its actual execution boundary. PASS only with four separately attributable structured results and no sandbox or wrapper bypass.
- [ ] **U9 — Four real `devices` probes pass.** Each runtime must return a current, minimized, annotated device result without sending. Exit `2` is acceptable only when the JSON is valid and reports ownership questions or duplicate-name ambiguity. PASS only if no runtime prints raw state, credentials, registration/auth fields, email/contact data, or unrelated transfers.
- [ ] **U10 — Shared initialization is preserved.** Run the normal initialization and live-sync workflow without replacing the existing shared records. PASS only if schema-1 data, ownership/evidence fields, `label`, `aliases`, `notes`, absent-device records, and `standing_send_authorization: false` survive; new exact names remain unconfirmed and emit ownership questions. No automatic rename, alias-based owner inference, or implicit target resolution is allowed.

## 4. Separately authorize one locked-session delivery

This phase is not part of doctor, discovery, installation, auditing, or the offline suite. Obtain a new, explicit user authorization naming one harmless regular test file and one exact, currently live, user-confirmed display name. Do not reuse an earlier authorization, transfer UUID, file, or receipt.

- [ ] **U11 — Lock precondition is proven.** Record that the Mac was already locked before the new transfer was created and invited. PASS only if the candidate RPC path performs the transfer without unlocking, GUI/Accessibility actions, clipboard use, blind input, or another transport.
- [ ] **U12 — One new send is bounded.** Use one freshly generated and retained UUID, validate the exact file and exact real `display_name`, and issue at most one create/add/invite sequence. PASS only if no mutation is automatically retried and any uncertainty is investigated with `status` for that same UUID.
- [ ] **U13 — Delivery is established.** Query the same UUID. `Created`, `InviteRequested`, `Invited`, `Pending`, `Active`, a successful command exit, or a closed window is not delivery. PASS only when that UUID reports `Completed` (`8`) or the human confirms receipt of that exact file on that exact recipient. Record only sanitized evidence; do not publish the UUID, device name, file path, or personal metadata.

## 5. Audit and promote one exact revision

- [ ] **U14 — Tested candidate is frozen.** After U1–U13 pass, freeze the already-tested candidate, including its exact pin from U4, and record the source revision and hashes of every file proposed for promotion. Do not change the pin or implementation after testing. No automatic range, wildcard, minimum-version check, environment override, or fallback acceptance is allowed. Production promotion occurs only after U15 and explicit scoped approval; install the audited candidate byte-for-byte without copying private state.
- [ ] **U15 — Independent audit passes.** A reviewer who did not produce the candidate checks the exact final revision—not an earlier diff or working tree—against this checklist, the static contract, offline output, four-runtime live evidence, and completed/receipt evidence. Any post-audit change invalidates the audit and requires the affected gates to run again.
- [ ] **U16 — Publication is scoped and sanitized.** Publish only the audited skill files required for the upgrade. Before publication, inspect the exact staged content for credentials, database material, raw RPC payloads, device names/IDs, transfer UUIDs, emails, local paths, private inventory, test-recipient details, and unrelated changes. PASS only if the published revision and hashes equal U14 and the private evidence remains local.

## 6. Rollback and hard stops

- [ ] **U17 — Rollback is prepared before promotion.** Record the exact prior revision and its hashes, keep the prior `1.1.16` / `20260425132215` guard available, and document how to restore the previous audited skill revision without copying private state. PASS only if rollback preserves the shared inventory and initialization files, including labels, aliases, and notes.
- [ ] **U18 — Rollback is verified fail-closed.** After rollback, run the offline suite and `doctor`. PASS when the restored helper accepts only its pinned build and refuses an incompatible installed build; do not weaken the pin merely to regain service. Restore a compatible app build only through a separately authorized application-management process.

There is no automatic pin relaxation, compatibility guess, fallback to the GUI helper, fallback to another recipient, or fallback to another transport at any stage. If the candidate cannot satisfy a gate, retain or restore the last audited revision and report the exact blocker.
