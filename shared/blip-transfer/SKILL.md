---
name: blip-transfer
description: "Send files through Blip on macOS, including new transfers while locked through a version-pinned local RPC CLI. Shared initialization and device ownership records for Hermes, Claude Code, Codex and OMP; ask about every new device and require current send authorization."
---

# Blip transfer

## Scope and authorization

Use the installed macOS Blip app, not invented HTTP endpoints or a claimed official CLI. This skill is runtime-neutral and shared by Hermes, Claude Code, Codex and OMP. Resolve this SKILL.md's real directory before using its relative scripts. The local RPC CLI requires the supported Blip build already running in the same logged-in user session, Python 3, and access to its owner-validated local socket; it does not require an unlocked screen or Accessibility. The separate GUI helper requires an unlocked GUI session, Swift and Accessibility for the actual host. Never bypass a runtime sandbox or automatically fall back between these routes.

Every send requires a current user request identifying files and a recipient. Ownership annotations are context, NEVER standing permission. Read the private device inventory at `~/.agents/private/blip-transfer/devices.json`; do not embed personal device names, emails or paths in public copies of this skill. Unknown contacts stay unknown. Do not infer ownership from a friendly name or account resemblance. An exact user-confirmed name is sufficient for the present request, not cryptographic identity.

## Routing decisions

- For supported regular-file sends, prefer `scripts/blip-rpc.py` whether the Mac is locked or unlocked. Start with its `doctor`; this path does not need Swift or Accessibility.
- “Send while locked” means create a NEW transfer after the Mac is already locked. Do not substitute starting while unlocked, resuming an older transfer, waiting for unlock, or another transfer service.
- If the version-pinned RPC route is unavailable, report the precise build/socket/sandbox blocker. Do not weaken the GUI lock guard, attempt blind clicks, or change system security settings.
- The GUI helper is a separate unlocked-session route, not an automatic fallback. Unsupported RPC files or recipients require an explicit scope decision; never silently archive folders or switch transports.

## First use and shared synchronization

Read `references/initialization.md` before the first use on a machine or when initialization metadata is missing. Initialization is mandatory, not an optional appendix.

1. Run `python3 <skill-dir>/scripts/blip-rpc.py doctor` for the headless route. Screen lock is permitted for RPC, not for GUI operations. If the RPC build/socket check fails, report the blocker; do not unlock automatically or fall back to GUI while locked. The GUI helper's `doctor` remains separate. A Swift cache error inside a runtime sandbox is not a Blip permission failure: report it and request a narrowly approved helper execution, never globally disable the sandbox.
2. Run `python3 <skill-dir>/scripts/inventory.py init --runtime <runtime-name>`. This creates or validates one shared private record without overwriting existing ownership. Do not make four per-runtime copies. Existing user records must survive reinitialization.
3. Obtain a successful live device snapshot from the selected route: RPC works while locked; GUI requires an unlocked session. Pass its `devices` JSON to `inventory.py sync`. An RPC `devices` result with ownership questions may intentionally exit 2; validate its structured success and questions instead of treating that as transport failure. Capture/validate the producer's exit status first; do not pipe failed or partial output blindly. New exact names are recorded as unknown and yield mandatory ownership questions. Do not use the historic inventory as fake live discovery.
4. Ask the user every emitted ownership question. Only after their actual answer, use `inventory.py confirm --device EXACT --ownership user|family-shared|other|unknown --label LABEL --confirmed-by-user`. The flag records the human answer; it is not itself authorization and cannot be self-granted by an agent.
5. Synchronize again to record the resulting first-use state. `initialization.json` distinguishes `awaiting_live_sync`, `awaiting_ownership_confirmation` and `ready`; none grants permission to send. Each later transfer session repeats live synchronization to detect new or renamed devices.

## Headless CLI: new transfers while already locked

Read `references/headless-rpc.md` before using `python3 <skill-dir>/scripts/blip-rpc.py`. This is an unofficial, version-pinned local RPC adapter, not an official Blip CLI. It sends through the running Blip engine, not a different transport.

- Commands: `doctor`, `devices`, `status --transfer-id UUID`, and `send --recipient EXACT --confirm-recipient EXACT --transfer-id UUID ABSOLUTE_FILE...`. Run `--help` for authoritative arguments.
- Current headless scope: regular files to an explicitly user-confirmed, unique, reachable same-account device. Directories and symlinks are rejected; do not silently archive or substitute another recipient.
- Every send invocation needs the current user's file/recipient authorization. Use one explicit new UUID per intended transfer and retain it before sending. On any uncertain outcome query that ID; never retry by creating a new ID automatically.
- Exit `10` from `send`/`status` means a valid pending transfer, not delivery and not a reason to retry. Exit `2` from `devices` may mean mandatory ownership questions; inspect the JSON.
- If a test or failed attempt leaves a local `Created` draft, report it separately from an invited transfer. Do not automatically invite, resume, cancel or remove it; retain its UUID for user-directed handling.
- CLI checks private ownership, fresh device identity, source metadata and prepared archive before inviting. It does not inspect GUI rows. Unrelated unknown devices remain unresolved without blocking a separately authorized known recipient.
- `Invited`, `Pending` and `Active` are not delivery. Only this transfer's `Completed` status or human receipt establishes completion. No full RPC payload logging: the transport carries application state; auth, registration and emails must be skipped without decoding and never persisted.

## GUI commands and procedure

Use `swift <skill-dir>/scripts/blip.swift --help` for the authoritative command syntax. Read `references/workflow.md` before your first real send. The helper only interacts with the `net.blip.macos` application and uses structured JSON output.

1. **Doctor**: run `doctor`. No auto-granting, TCC reset or permission bypass. If not trusted, `request-permission` opens the Accessibility settings and requests authorization; only the human can grant it. Do not demand permissions for arbitrary shell tools. Use actual TCC attribution if necessary; the successful Orca session attributed the operation to `com.stablyai.orca`, not its separate Computer Use app. Other hosts must be checked independently.
2. **Inventory**: run `devices`. This may open the Blip status-menu popover but never sends. Join the exact live display names to the private inventory and show ownership confidence and friendly aliases. Cached annotations are not live online status. If the named recipient is absent or duplicated, stop and ask; never select the first similar result.
3. **Prepare**: validate the user's exact file/folder paths. Do not read file contents unnecessarily, create archives, follow unexpected destinations or collect extra files. Run `prepare` with those paths. This invokes Blip's `Blip…` service with a private named pasteboard containing file URLs plus `NSFilenamesPboardType`. Do not use or overwrite the general clipboard. Preparation is not transmission. Record the pasteboard name for cleanup.
4. **Inspect**: run `status`. Confirm the pending chooser belongs to the intended file(s) and exact recipient. A same-named unrelated window is not sufficient. Do not reuse coordinates from this document, a previous run, or a previous display layout.
5. **Send**: only after the user authorization and live chooser checks, invoke the helper's recipient selection with the exact window and recipient confirmations. It must find exactly one matching recipient row, derive live coordinates, and verify the click hits that row. An ambiguous or changed interface is a hard stop, not permission to guess. Do not auto-repeat an uncertain send.
6. **Observe**: run `status` and quote the raw matching Blip status. `Waiting for … to accept` means pending: ask the user to open Blip on the receiving device. Return code zero, service invocation, clicking, a closed window, or a disappearing item NEVER proves delivery. Claim completion only from an explicit transfer-complete indication tied to this file/recipient or the user's receipt confirmation. If the user confirms receipt, accept it without re-testing.
7. **Cleanup**: release only this operation's named pasteboard after Blip has ingested it. Do not delete source files. Delete only your own explicitly temporary artifacts when no longer needed; do not cancel pending sends without user direction.

## Device annotation maintenance

Keep ownership, evidence and current authorization separate. Read `references/devices.md`. **Mandatory user rule: whenever the live list contains an unregistered/new device, ask the user who owns it before classifying it or sending to it.** Report its exact display name and ask whether it is the user’s own device, family/shared, another person, or to remain unknown. Do not auto-enroll even when its name matches a known owner alias. Also re-confirm renamed, duplicated or conflicting entries. If the user cannot answer, preserve unknown ownership and block sending to that device, without blocking a separately authorized transfer to a known recipient. Update the private inventory only on explicit user confirmation or direct application evidence, recording date and evidence type. Device renames require live reconciliation, not fuzzy matching. Do not alter the actual device names in Blip unless asked.

For private device memory, use `python3 <skill-dir>/scripts/inventory.py note --device EXACT [--label LABEL] [--alias ALIAS]... [--notes TEXT]`. Only supplied fields change; aliases and notes are display-only, never recipient identifiers or instructions. Initialization and synchronization preserve this shared memory across all runtimes. Do not invent notes on the user’s behalf.

## Upgrade and offline checks

Read `references/upgrade-validation.md` before accepting any different Blip build. Never relax the version pin automatically. Run `python3 -m unittest discover -s tests -p 'test_*.py'` from the skill root; the suite uses synthetic fixtures and no real sends. An upgrade needs separately authorized real locked-session acceptance and independent review of the exact final revision.

## Safety boundaries

- Never read Blip databases, credentials, keychain secrets or third-party email addresses to automate sending.
- No file transfer in a self-test, install, lint, skill-discovery check or background audit.
- Reject missing/unreadable paths, empty sends and duplicate exact recipient names. GUI additionally rejects vanished UI or selection outside the verified chooser; RPC uses fresh peer-ID and prepared-file checks instead.
- File/folder paths and recipient names are arguments, never interpolated into shell or AppleScript source.
- Do not silently fall back to another recipient, another transport or a public upload service.
- If UI inspection is incomplete, stop with the exact missing observation; do not send blind keystrokes.
- New or changed executable send logic needs a separately authorized end-to-end test. Prior manual receipt validates the mechanism, not all future scripts or versions.

## Proven mechanism and limitations

On 2026-09-17, the version-pinned RPC CLI created a new 92-byte file transfer, attached the exact file, and requested an invitation while the Mac was locked before and after the operation. A subsequent exact-ID status query returned `Completed` (8): app-reported completion, not a claimed human receipt. Fresh OMP, Claude Code, and Hermes model sessions successfully discovered the skill and ran the RPC doctor while locked. Codex discovered and ran it under its workspace-write sandbox, but doctor returned exit 3 (`rpc_unavailable`, `screen_lock_unavailable`); no bypass was attempted. Hermes returned its successful final report before its outer process timed out; Codex also timed out after its failed doctor. These are diagnostic probes, not four send tests.

On 2026-09-17, Blip 1.1.16 successfully delivered a 175-byte harmless test file to a user-confirmed iPhone. The user explicitly confirmed receipt. The successful path was a native service with both file URL and legacy filename pasteboard representations, a retained named pasteboard, live AX row coordinates, and a CGEvent mouse click. The experiment changed both representation and lifetime together; it does NOT establish which change was necessary on its own.

AppleScript clicking a static-text label returned success without selecting the row. `open -a Blip <file>` and the attempted file-picker route did not produce a usable send in that session; do not generalize this to every Blip version. Screen capture was unavailable; use live AX evidence rather than claiming visual screenshot verification. CLI-Anything/OpenCLI were unnecessary for the successful path.

## Cross-runtime installation

One canonical managed skill, with explicit user-approved registrations and links. Do not modify other skills, scan private sessions, repoint existing entries, publish personal inventory, or broaden permissions. A symlink check proves file visibility only; discovery checks and fresh-session prompt inclusion are distinct evidence levels. Existing conversations may need a fresh session to pick up the description.
