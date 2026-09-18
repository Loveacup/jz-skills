# Headless local RPC

This is an unofficial adapter for a private, undocumented, version-pinned protocol exposed by the installed Blip app through its local Unix socket. Publishing this helper does not make the protocol official or vendor-supported. Keep Blip responsible for its existing account and transport; do not extract credentials, read its databases, alter its settings, inject code, or connect to a remote RPC service.

## GUI path versus headless path

The native helper in `scripts/blip.swift` drives Blip's service and recipient chooser. Its lock guard is deliberate: when `doctor` reports `screenLocked: true`, all GUI, Accessibility, and synthetic-input operations must stop until the user unlocks.

`scripts/blip-rpc.py` is a separate headless path. It talks only to Blip's local socket and has no Accessibility, screen, chooser, clipboard, or foreground-window dependency. A locked screen therefore does not itself block this path. Do not weaken or bypass the native helper's guard, and never silently fall back between the two paths.

## Commands

Resolve the canonical managed skill directory first; examples use `$SKILL` for that absolute directory.

```sh
python3 "$SKILL/scripts/blip-rpc.py" doctor
python3 "$SKILL/scripts/blip-rpc.py" devices
python3 "$SKILL/scripts/blip-rpc.py" status --transfer-id "UUID"
python3 "$SKILL/scripts/blip-rpc.py" watch --transfer-id "UUID" --timeout 120 --interval 2

# Own-device mode (`--recipient-scope device` is the default)
python3 "$SKILL/scripts/blip-rpc.py" send \
  --recipient "EXACT_LIVE_DEVICE_NAME" \
  --confirm-recipient "EXACT_LIVE_DEVICE_NAME" \
  --transfer-id "UUID" \
  "/absolute/path/to/authorized-file" ["/absolute/path/to/another-file"]

# Exact-child mode: default device scope and both child confirmations
python3 "$SKILL/scripts/blip-rpc.py" send \
  --recipient "EXACT_LIVE_EXTERNAL_RECEIVER_NAME" \
  --confirm-recipient "EXACT_LIVE_EXTERNAL_RECEIVER_NAME" \
  --recipient-device "EXACT_LIVE_CHILD_DEVICE_NAME" \
  --confirm-recipient-device "EXACT_LIVE_CHILD_DEVICE_NAME" \
  --transfer-id "UUID" \
  "/absolute/path/to/authorized-file" ["/absolute/path/to/another-file"]

# Account mode: explicit scope, exact top-level receiver, and no child flags
python3 "$SKILL/scripts/blip-rpc.py" send \
  --recipient-scope account \
  --recipient "EXACT_LIVE_EXTERNAL_RECEIVER_NAME" \
  --confirm-recipient "EXACT_LIVE_EXTERNAL_RECEIVER_NAME" \
  --transfer-id "UUID" \
  "/absolute/path/to/authorized-file" ["/absolute/path/to/another-file"]
```

The caller must create and retain a fresh UUID for one intended transfer. Confirmation arguments are mechanical exact-match guards, not evidence of consent. `--recipient-scope` accepts only `device` or `account` and defaults to `device`. Device scope preserves the two existing branches: no child flags selects the guarded own-device route, while both equal child flags select the guarded external exact-child route; supplying only one child flag is rejected. Explicit account scope rejects either child flag instead of ignoring it. Successful send output identifies `recipient_scope`; only exact-child output includes `recipient_device`.

Exit codes: `0` means a successful non-transmitting check or an observed `Completed` transfer without reported errors. The raw RPC `devices` command uses `2` when its valid JSON contains identity or classification questions; capture that JSON rather than treating it as transport failure. Passing the successful snapshot to `inventory.py sync` is the scope-aware readiness step: sync exits `0` only for `initialization_status: "ready"` and exits `2` for every valid non-ready status, including ownership questions, duplicate ambiguity, live entries with unknown/missing stored kind, a genuine conflict with a present observed kind, an unverified contact check, or absent known contacts. Missing `live_entry_type` alone is not a conflict. `send` retains its existing pending exit `10`; `status` uses `10` for nonterminal observations without reported errors, and `watch` uses `10` for a clean observation timeout. `status`/`watch` use `4` for cancellation or reported local/remote errors. Argument errors use `2`, transport failures normally use `3`, and a missing exact transfer uses `4`. Exit `10` must never trigger automatic resend. JSON `code`, `initialization_status`, and pending arrays are authoritative.

`doctor` is non-transmitting and does not need GUI or Accessibility access. It accepts only Blip version `1.1.16`, build `20260425132215`, and the fixed local socket under `~/Library/Group Containers/AY8UB8KTUX.blip/Library/Caches/sock`. It verifies that the socket is a socket and is owned by the current UID. There is no remote-address or socket override. A different app version/build, missing socket, wrong owner, or wrong filesystem type is a hard failure: do not guess that the wire schema is compatible.

`devices` is read-only and works without an unlocked GUI. This adapter parses the pinned build's allowlisted full current discovered-user collection and emits `discovery_scope: "discovered_devices_and_contacts"`. The top-level `devices` array contains own physical rows with genuinely observed `live_entry_type: "device"` and non-self external receiver rows identified technically by `is_contact: true`. `is_contact` describes the account relation used for discovery and deduplication; it is not evidence that the human-confirmed inventory `entry_type` is `contact`. External rows therefore omit `live_entry_type` and may validly retain a user-confirmed `device` or `contact` kind. Each external row has informational `recipient_devices` rows containing only `display_name`, `device_id`, `is_online`, `is_pushable`, `live`, and `is_self`; child rows are not independently enrolled into private inventory and need no name for account routing. Public external rows never include `user_id`. The scope documents the full current discovered collection, not an exhaustive address book, permission, permanent connectivity, or proof an absent person is not a Blip contact.

`status` reads only the transfer named by `--transfer-id` and reports its status code/name, raw `completed` boolean (status 8), `terminal` (only statuses 8 and 9), `has_local_error`, `has_remote_error`, `error_scope`, and `reason`. Error scope is `none`, `local`, `remote`, or `local_and_remote`, derived only from opaque error-field presence. Error flags take reason/exit precedence but do not establish an engine-terminal failure; a contradictory Completed-plus-error snapshot keeps its raw status but exits `4`. No raw error text, account/device identifiers, file list, root-cause guess, or global transfer history is returned.

`send` performs create, content attachment, validation, and one invite. Dispatch acknowledgments precede asynchronous state publication: the CLI polls for the newly created object and exact prepared archive without repeating mutations. Before invitation it requires `Created` (`1`), outgoing, the exact peer, no local/remote errors, `content_job_count == 0`, and exact authorized filenames and sizes. It then revalidates the unique live recipient and source-file identity immediately before the single invite. A post-invite read may still report `Created`; that is an observation delay, not delivery. Query the same UUID later.

### Bounded read-only observation

`watch` polls the same exact canonical UUID and returns one final JSON object, not a stream or persistent log. Defaults are `--timeout 120` and `--interval 2`, both finite positive seconds. One monotonic deadline bounds every RPC request and sleep; a poll interval longer than the remaining budget is clipped. Version validation happens before the polling budget starts. No mutating method, automatic retry after a query error, GUI, or alternative transport is used.

Normal output includes the last safe status fields plus `command: "watch"`, `status_available`, `observations` (successful queries), `elapsed_seconds`, `timed_out`, and `stop_reason`. Stop reasons are `completed` (exit 0), `cancelled` or `error` (exit 4), and `timeout` (exit 10). If the budget expires before any snapshot, `status_available` is false and no status code is invented. A timeout never cancels the underlying transfer, proves failure, or authorizes another send.

A query error exits immediately with its original sanitized `code` and exit status, plus the UUID, observation count, elapsed time, `stop_reason: "rpc_error"`, and `last_status` when available. An RPC deadline failure remains an explicit query error rather than masquerading as a clean pending timeout. A missing transfer is also a query error, not an invitation to recreate it.

Reasons are deliberately conservative: `created_invitation_unconfirmed`, `invitation_requested`, `invited_acceptance_unconfirmed`, `pending_reason_unknown`, `transfer_active`, `transfer_paused`, `resume_requested`, `completed`, `cancelled`, or `status_unknown`. Error presence overrides these with `local_error_reported`, `remote_error_reported`, or `local_and_remote_error_reported`. A Created snapshot can lag an already-requested invite; neither it nor Pending establishes that the receiver has not accepted. Unknown enum values are preserved numerically without guessing. Stopping observation because an error is reported does not cancel or label the engine state terminal.

## Per-session preflight, authorization, and supported scope

Every transfer session starts with the current RPC `devices` query and synchronization of its successful structured output, even when an exact recipient was used before. Its `discovered_devices_and_contacts` scope is the required current own-device and contact-capable check while locked or unlocked. The GUI is neither required nor permitted as a substitute for a locked external-recipient preflight. If the actual send uses the separate unlocked GUI route, follow `workflow.md` and inspect its current GUI surface too.

Each synchronization recomputes coverage from its current snapshot. Live names whose stored kind is unknown/missing or conflicts with an actually present `live_entry_type` appear in `unclassified_entries`; genuine conflicts also appear in `classification_conflicts` and require renewed identity/type confirmation. An external `is_contact` row without `live_entry_type` preserves a confirmed human kind and does not itself create a conflict. A new external row is still unknown and requires the human's identity and kind answers. Known stored contacts absent from the current collection appear in `unverified_contacts`. Neither condition deletes private annotations. A nameless top-level receiver cannot silently count as complete coverage. Status priority is `awaiting_ownership_confirmation`, then `awaiting_entry_classification`, then `awaiting_contact_check`, then `ready`.

This global coverage state is separate from per-send authorization. Every send requires a current user request naming the exact top-level recipient and exact source files. Exact-child mode additionally requires the current request to identify the exact child device. Account mode requires an explicit account-scoped request for the displayed top-level receiver and never treats a child as selected. Stored kind/ownership and an earlier name confirmation are never standing permission.

Own-device mode preserves the original narrow gates:

- `--recipient-scope` is omitted or `device`, and both child flags are absent;
- the exact live display name has one and only one top-level match;
- the private inventory marks that exact entry `entry_type: "device"`, `ownership: "user_confirmed"`, with identity confirmation complete;
- the live row is an own non-local device with `is_contact: false` and one complete reachable peer;
- aliases, similar names, prior receipt, owner choice, and account resemblance are insufficient.

Exact-child mode is the other device-scope branch:

- `--recipient` and `--confirm-recipient` exactly match one live non-self row with `is_contact: true`;
- the private record has human-confirmed `entry_type: "device"` or `"contact"`, `ownership: "other_person_confirmed"`, and `requires_identity_confirmation: false`;
- both child-device flags are present, equal, and exactly match one nested live non-self `recipient_devices` row;
- the selected external user ID and child device ID are both complete internally, producing one complete peer;
- the same unique top-level receiver and child device are re-resolved immediately before invitation, and the complete peer must remain equal.

Account mode is a third, explicit branch:

- `--recipient-scope account` is present and both child flags are absent;
- `--recipient` and `--confirm-recipient` exactly match one live non-self row with `is_contact: true` and a nonempty user ID;
- the private record has human-confirmed `entry_type: "device"` or `"contact"`, `ownership: "other_person_confirmed"`, and `requires_identity_confirmation: false`;
- at least one nested non-self child has a complete device ID and is currently online or pushable; child names are not required and no child is selected;
- the route constructs exactly `{user_id: <fresh external user>, device_id: ""}`. The fresh user ID must remain unchanged through the pre-invite re-resolution, and the `Created` state plus pre-invite state must retain that exact account peer, including the empty device ID;
- after the single invite, only account mode may accept Blip populating a device ID, and only when the user ID still exactly matches. Own and exact-child modes continue to require their complete original pair.

The CLI never chooses the first child, broadcasts, falls back between account/device/own/exact-child branches, or broadens the own-device ownership gate. Account scope targets the displayed top-level receiver entry. Receiver-side device selection and acceptance remain Blip behavior; the sender must not claim that all children receive, that any child was selected, or that acceptance is automatic. Each request relies on fresh exact-name confirmation and current identifiers rather than an invented persistent account binding. Duplicate top-level or selected-child names, incomplete required identifiers, unavailable targets, an identity/type conflict, a changed account user ID, a wrong post-invite user ID, or any disallowed peer change fails closed.

For every new or unregistered top-level live name, present the annotation helper's questions to the user: who owns it, and is it a device, contact, or still unknown? Also surface every current `classification_conflicts` and `unclassified_entries` item. Never answer from the name, `is_contact`, owner category, alias, child devices, or discovery source. An actually emitted `live_entry_type` remains an observation, not a human answer. Confirmation updates private ownership and stored kind only; it is not send permission. Nested child devices remain routing/readiness information and are never separate inventory records.

Only absolute paths to existing readable regular files are supported. Directories and symlinks fail clearly; they are not traversed, followed, archived, or silently transformed. The existing GUI helper's separately documented folder support is unchanged.

## Mutation uncertainty and delivery claims

Create, add-content, and invite are mutations and are never automatically retried. Once create may have run, every error includes the known transfer UUID. If a response is lost or ambiguous, inspect that exact UUID with `status`; do not claim “not sent,” generate another UUID, or resend automatically. A repeated command can duplicate user-visible work even when its first response was not observed.

Status meanings relevant to reporting are:

| Code | Name | Allowed claim |
|---:|---|---|
| 1 | `Created` | Local Created observation; invitation unconfirmed, not delivered |
| 2 | `InviteRequested` | Invitation requested; not delivered |
| 3 | `Invited` | Recipient invited; pending, not delivered |
| 4 | `Pending` | Pending, not delivered |
| 5 | `Active` | Transfer active; not delivered |
| 8 | `Completed` | Blip reports this exact transfer completed |
| 9 | `Cancelled` | Cancelled; not delivered |

Delivery is accepted only when the queried exact UUID reaches `Completed` (`8`) or the human confirms receipt of the exact file. Locked-screen acceptance requires the Mac already locked before a new create/invite and completion tied to that file and recipient. On 2026-09-17, the original own-device CLI completed its harmless test after creating and inviting while locked; this remains own-device evidence only. On 2026-09-18, one separately authorized 100-byte external account-scoped transfer was created, prepared and invited once. Its first send observation was `Created` with `invite_requested: true` and exit `10`; the later exact-ID status query returned `Completed` (`8`) and exit `0`, without retry. Fresh preflight had five reachable nameless child records and preserved the human-confirmed device classification of the external receiver. The Mac was unlocked before this transfer, so it proves app-reported account-route delivery, not locked cross-account acceptance, human receipt, which physical child received, or broadcast. Exact-child cross-account acceptance remains separate. Every subsequent send still needs current authorization.

A second, separately authorized test on 2026-09-18 used a new UUID and a new 115-byte file after the Mac was locked. RPC doctor reported `screen_locked: true` before creation and after invitation. The new transfer's exact-ID query returned `Completed` (`8`) and exit `0`; it was neither an unlocked pre-start nor a resumed/retried task. No unlock, GUI/Accessibility, clipboard, or alternative transport was used. This supplies locked cross-account app-reported completion for the tested pinned revision, not human receipt, named-child routing, or broadcast proof.

## Privacy boundary

`GetState` necessarily transports opaque application state, including sensitive fields. Responses remain in memory and are never written, cached, logged, or printed raw. For this pinned adapter, parsing allowlists only the discovered-user/device fields required for minimized discovery and exact peer resolution plus field `600` for the exact requested transfer. It skips registration field `200`, auth field `201`, email fields, unknown contact-map keys, and unrelated state without interpreting or copying their payloads. No contact user ID is printed or persisted; complete user/device IDs exist only transiently for exact peer validation. Raw RPC errors are not exposed. Mutable response/discard buffers are zeroed without resizing, including when parsing fails.

The helper does not request credentials, read the app database or keychain, invoke host/takeover functionality, or inspect unrelated transfers. Output must remain minimized; device IDs may be shown only when necessary to resolve identity, and full state is never an output format.

## Wire and schema evidence

The framing source is [`storj/drpc` v0.0.32 `drpcwire/packet.go`](https://raw.githubusercontent.com/storj/drpc/v0.0.32/drpcwire/packet.go). Each fresh socket uses DRPC frames with `control = (kind << 1) | done`, followed by varint stream ID, message ID, payload length, and payload. The helper sends stream 1 `invoke` (kind 1/message 1/method UTF-8), `message` (kind 2/message 2/protobuf), and `close-send` (kind 6/message 3/empty), then reads message frames through `done`. Close is kind 5; error kind 3 is handled without exposing its payload. Reads are bounded to 8 MiB, 8 seconds, and 256 frames.

The two unary methods recovered for the pinned build are:

- `/rpc.Service/GetState`: empty request; response fields `id` (1, uint64) and `state` (2, bytes containing `frontend.State`).
- `/rpc.Service/Dispatch`: request field `event` (1, bytes containing `google.protobuf.Any`); successful response is empty. `Any.type_url` is `type.googleapis.com/event.<Name>`, and `Any.value` contains the event protobuf.

The mutation schemas used are `TransferCreateRequested { transfer_id: 1, peer_id: 2 }`, `TransferAddContentRequested { transfer_id: 1, locations: 2 repeated }`, and `TransferInviteRequested { transfer_id: 1, peer_id: 2 }`. The installed `BlipKit` framework supplies corroborating local evidence: exported `_libblip_client_create`, `_libblip_get_state`, and `_libblip_dispatch`; demangled `Core` RPC connection/dispatch accessors and `Event.protobuf`; the embedded `frontend/cmd/libblip/rpc/service.proto` descriptor; exact `/rpc.Service/GetState` and `/rpc.Service/Dispatch` strings; and protobuf symbols for all three transfer events. Embedded Go source-path strings identify `storj.io/drpc v0.0.32`. Running Blip and BlipShare were observed using the local Unix socket. These are implementation observations, not a vendor stability promise.

For account routing, static inspection of the installed pinned `BlipKit` native code supplies a narrower peer-encoding contract. `PeerId.init(userID:deviceID:)` at file offset `0x1013f0` converts a nil optional device ID to an empty string; `PeerId.isPerson` at `0x101918` returns true only when the user ID is nonempty and the device ID is empty; and the native protobuf traversal at `0xa68bc` emits user field 1 while omitting empty device field 2. The same `PeerId` type is used by the create and invite events described above. This is static evidence that an account peer is represented by a user ID plus empty/omitted device ID. It is not real delivery evidence, does not establish which receiver-side device Blip chooses, and does not imply broadcast or automatic acceptance.

Public evidence remains narrower: in a [2025-07-22 comment](https://news.ycombinator.com/item?id=44651955), a self-identified [Blip cofounder](https://news.ycombinator.com/item?id=44651802) wrote that Blip did not yet have an API. That is historical evidence, not proof about every later build; no current public invocation contract was found in the sources examined.

## GitHub project fit

- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) provides a useful methodology for wrapping a real engine/API/CLI, but it does not create a missing backend. Its inspected registries had no Blip file-transfer entry; the small standard-library helper directly wraps the now-verified local backend.
- [OpenCLI](https://github.com/jackwener/opencli) can pass through an existing binary, while its browser/CDP and AppleScript/Accessibility adapters do not make a native locked session headless. Registration would add discovery, not capability, and is unnecessary here.
- [Peekaboo](https://github.com/openclaw/Peekaboo) is generic macOS Accessibility/UI automation. Background window control is not the same as screen-locked, UI-independent operation.

No Blip file-transfer adapter was found in the inspected current registries, documented catalogs, and scoped indexed searches. This is not a claim that none exists anywhere on GitHub, and none of these projects is evidence of public or vendor-supported Blip RPC.

## Upgrade and regression checks

Follow `upgrade-validation.md` before supporting a different Blip build. Run `python3 -m unittest discover -s tests -p 'test_*.py'` from the skill root for offline regressions; these tests use synthetic state and never send. Fresh model-session diagnostics on 2026-09-17 succeeded in OMP, Claude Code, and Hermes while locked. Codex discovered and executed the helper under its workspace-write sandbox, but `doctor` returned exit 3 with `rpc_unavailable` and `screen_lock_unavailable`; no sandbox bypass was attempted. Hermes produced a successful diagnostic and final report before its outer process timed out; Codex's outer session also timed out after its failed diagnostic. Do not claim four fully passing runtimes.