---
name: blip-transfer
description: "Operate Blip on macOS to send files or folders to explicitly authorized devices, annotate the live device list, ask the user about every newly discovered device owner, troubleshoot permissions, and distinguish queued transfers from confirmed receipt. Shared by Hermes, Claude Code, Codex and OMP."
---

# Blip transfer

## Scope and authorization

Use the installed macOS Blip app, not invented HTTP endpoints or a claimed official CLI. This skill is runtime-neutral and shared by Hermes, Claude Code, Codex and OMP. Resolve this SKILL.md's real directory before using its relative scripts. It requires a logged-in macOS GUI session, Blip, Swift command-line tools and Accessibility permission for the actual agent host. A headless/SSH agent cannot assume GUI access. Permissions are per host, not shared by installing this skill.

Every send requires a current user request identifying files and a recipient. Ownership annotations are context, NEVER standing permission. Read the private device inventory at `~/.agents/private/blip-transfer/devices.json`; do not embed personal device names, emails or paths in public copies of this skill. Unknown contacts stay unknown. Do not infer ownership from a friendly name or account resemblance. An exact user-confirmed name is sufficient for the present request, not cryptographic identity.

## First use and shared synchronization

Read `references/initialization.md` before the first use on a machine or when initialization metadata is missing. Initialization is mandatory, not an optional appendix.

1. Run `doctor`. If `screenLocked` is true, stop GUI operations and ask the user to unlock; do not ask them to regrant Accessibility. A Swift cache error inside a runtime sandbox is not a Blip permission failure: report it and request a narrowly approved helper execution, never globally disable the sandbox.
2. Run `python3 <skill-dir>/scripts/inventory.py init --runtime <runtime-name>`. This creates or validates one shared private record without overwriting existing ownership. Do not make four per-runtime copies. Existing user records must survive reinitialization.
3. Only with an unlocked session and successful live `devices` output, pass that JSON to `inventory.py sync`. Capture/validate the producer's exit status first; do not pipe failed or partial output blindly. New exact names are recorded as unknown and yield mandatory ownership questions. Do not use the historic inventory as fake live discovery.
4. Ask the user every emitted ownership question. Only after their actual answer, use `inventory.py confirm --device EXACT --ownership user|family-shared|other|unknown --label LABEL --confirmed-by-user`. The flag records the human answer; it is not itself authorization and cannot be self-granted by an agent.
5. Synchronize again to record the resulting first-use state. `initialization.json` distinguishes `awaiting_live_sync`, `awaiting_ownership_confirmation` and `ready`; none grants permission to send. Each later transfer session repeats live synchronization to detect new or renamed devices.

## Commands and procedure

Use `swift <skill-dir>/scripts/blip.swift --help` for the authoritative command syntax. Read `references/workflow.md` before your first real send. The helper only interacts with the `net.blip.macos` application and uses structured JSON output.

1. **Doctor**: run `doctor`. No auto-granting, TCC reset or permission bypass. If not trusted, `request-permission` opens the Accessibility settings and requests authorization; only the human can grant it. Do not demand permissions for arbitrary shell tools. Check Accessibility trust for the actual runtime host because permissions and TCC attribution are host-specific.
2. **Inventory**: run `devices`. This may open the Blip status-menu popover but never sends. Join the exact live display names to the private inventory and show ownership confidence and friendly aliases. Cached annotations are not live online status. If the named recipient is absent or duplicated, stop and ask; never select the first similar result.
3. **Prepare**: validate the user's exact file/folder paths. Do not read file contents unnecessarily, create archives, follow unexpected destinations or collect extra files. Run `prepare` with those paths. This invokes Blip's `Blip…` service with a private named pasteboard containing file URLs plus `NSFilenamesPboardType`. Do not use or overwrite the general clipboard. Preparation is not transmission. Record the pasteboard name for cleanup.
4. **Inspect**: run `status`. Confirm the pending chooser belongs to the intended file(s) and exact recipient. A same-named unrelated window is not sufficient. Do not reuse coordinates from this document, a previous run, or a previous display layout.
5. **Send**: only after the user authorization and live chooser checks, invoke the helper's recipient selection with the exact window and recipient confirmations. It must find exactly one matching recipient row, derive live coordinates, and verify the click hits that row. An ambiguous or changed interface is a hard stop, not permission to guess. Do not auto-repeat an uncertain send.
6. **Observe**: run `status` and quote the raw matching Blip status. `Waiting for … to accept` means pending: ask the user to open Blip on the receiving device. Return code zero, service invocation, clicking, a closed window, or a disappearing item NEVER proves delivery. Claim completion only from an explicit transfer-complete indication tied to this file/recipient or the user's receipt confirmation. If the user confirms receipt, accept it without re-testing.
7. **Cleanup**: release only this operation's named pasteboard after Blip has ingested it. Do not delete source files. Delete only your own explicitly temporary artifacts when no longer needed; do not cancel pending sends without user direction.

## Device annotation maintenance

Keep ownership, evidence and current authorization separate. Read `references/devices.md`. **Mandatory user rule: whenever the live list contains an unregistered/new device, ask the user who owns it before classifying it or sending to it.** Report its exact display name and ask whether it is the user’s own device, family/shared, another person, or to remain unknown. Do not auto-enroll even when its name matches a known owner alias. Also re-confirm renamed, duplicated or conflicting entries. If the user cannot answer, preserve unknown ownership and block sending to that device, without blocking a separately authorized transfer to a known recipient. Update the private inventory only on explicit user confirmation or direct application evidence, recording date and evidence type. Device renames require live reconciliation, not fuzzy matching. Do not alter the actual device names in Blip unless asked.

## Safety boundaries

- Never read Blip databases, credentials, keychain secrets or third-party email addresses to automate sending.
- No file transfer in a self-test, install, lint, skill-discovery check or background audit.
- Reject missing/unreadable paths, empty sends, duplicate exact recipient labels, vanished UI and selection outside the verified Blip chooser.
- File/folder paths and recipient names are arguments, never interpolated into shell or AppleScript source.
- Do not silently fall back to another recipient, another transport or a public upload service.
- If UI inspection is incomplete, stop with the exact missing observation; do not send blind keystrokes.
- New or changed executable send logic needs a separately authorized end-to-end test. Prior manual receipt validates the mechanism, not all future scripts or versions.

## Proven mechanism and limitations

**Manual mechanism proof:** A separately authorized end-to-end trial delivered a harmless file and the recipient explicitly confirmed receipt. The successful path used the native service with both file URL and legacy filename pasteboard representations, a retained named pasteboard, live AX row coordinates, and a CGEvent mouse click. That trial changed representation and pasteboard lifetime together, so it does NOT establish which change was necessary on its own.

**Script testing:** Manual proof of the mechanism does not validate a new or changed helper. Each executable send-path change requires its own separately authorized end-to-end test; non-transmitting discovery or doctor checks are not substitutes. In the manual trial, clicking a static-text label did not select the row, while live-coordinate clicking did. Alternative launch and file-picker approaches did not produce a usable send in that configuration; do not generalize those results to every Blip version. Use live AX evidence and never claim screenshot verification when no screenshot was observed.

## Cross-runtime installation

Install one canonical managed skill and expose it to each runtime only through that runtime's supported, explicitly approved registration mechanism. Do not modify other skills, scan private sessions, repoint existing entries, publish personal inventory, or broaden permissions. A symlink check proves file visibility only; discovery checks and fresh-session prompt inclusion are distinct evidence levels. Existing conversations may need a fresh session to pick up the description.
