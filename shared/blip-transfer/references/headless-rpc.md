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

# Own-device mode
python3 "$SKILL/scripts/blip-rpc.py" send \
  --recipient "EXACT_LIVE_DEVICE_NAME" \
  --confirm-recipient "EXACT_LIVE_DEVICE_NAME" \
  --transfer-id "UUID" \
  "/absolute/path/to/authorized-file" ["/absolute/path/to/another-file"]

# Contact mode: both exact child-device confirmations are mandatory together
python3 "$SKILL/scripts/blip-rpc.py" send \
  --recipient "EXACT_LIVE_CONTACT_NAME" \
  --confirm-recipient "EXACT_LIVE_CONTACT_NAME" \
  --recipient-device "EXACT_LIVE_CHILD_DEVICE_NAME" \
  --confirm-recipient-device "EXACT_LIVE_CHILD_DEVICE_NAME" \
  --transfer-id "UUID" \
  "/absolute/path/to/authorized-file" ["/absolute/path/to/another-file"]
```

The caller must create and retain a fresh UUID for one intended transfer. Confirmation arguments are mechanical exact-match guards, not evidence of consent. Own-device mode rejects contact-device flags; contact mode requires both of them and rejects omission or mismatch.

Exit codes: `0` means a successful non-transmitting check or an observed `Completed` transfer. The raw RPC `devices` command uses `2` when its valid JSON contains identity or classification questions; capture that JSON rather than treating it as transport failure. Passing the successful snapshot to `inventory.py sync` is the scope-aware readiness step: sync exits `0` only for `initialization_status: "ready"` and exits `2` for every valid non-ready status, including ownership questions, duplicate ambiguity, live entries with unknown/missing/conflicting kind, an unverified contact check, or absent known contacts. `send` and `status` use `10` for a valid but not completed transfer. Exit `10` is not a transport failure and must never trigger automatic resend. JSON `code`, `initialization_status`, and pending arrays are authoritative.

`doctor` is non-transmitting and does not need GUI or Accessibility access. It accepts only Blip version `1.1.16`, build `20260425132215`, and the fixed local socket under `~/Library/Group Containers/AY8UB8KTUX.blip/Library/Caches/sock`. It verifies that the socket is a socket and is owned by the current UID. There is no remote-address or socket override. A different app version/build, missing socket, wrong owner, or wrong filesystem type is a hard failure: do not guess that the wire schema is compatible.

`devices` is read-only and works without an unlocked GUI. This adapter parses the pinned build's allowlisted full current discovered-user collection and emits `discovery_scope: "discovered_devices_and_contacts"`. The top-level `devices` array contains own physical rows with `live_entry_type: "device"` and discovered non-self contact rows with `live_entry_type: "contact"`. Each contact row has informational `recipient_devices` rows containing only `display_name`, `device_id`, `is_online`, `is_pushable`, `live`, and `is_self`; child rows are not independently enrolled into private inventory. Public contact rows never include `user_id`. The scope documents the full current discovered collection, not an exhaustive address book, permission, permanent connectivity, or delivery.

`status` reads only the transfer named by `--transfer-id` and reports its status code/name and `completed` boolean. It is not a global transfer-history command.

`send` performs create, content attachment, validation, and one invite. Dispatch acknowledgments precede asynchronous state publication: the CLI polls for the newly created object and exact prepared archive without repeating mutations. Before invitation it requires `Created` (`1`), outgoing, the exact peer, no local/remote errors, `content_job_count == 0`, and exact authorized filenames and sizes. It then revalidates the unique live recipient and source-file identity immediately before the single invite. A post-invite read may still report `Created`; that is an observation delay, not delivery. Query the same UUID later.

## Per-session preflight, authorization, and supported scope

Every transfer session starts with the current RPC `devices` query and synchronization of its successful structured output, even when an exact recipient was used before. Its `discovered_devices_and_contacts` scope is the required current own-device and contact-capable check while locked or unlocked. The GUI is neither required nor permitted as a substitute for a locked contact preflight. If the actual send uses the separate unlocked GUI route, follow `workflow.md` and inspect its current GUI surface too.

Each synchronization recomputes coverage from its current snapshot. Live names whose stored kind is unknown/missing or conflicts with observed `live_entry_type` appear in `unclassified_entries`; conflicts also appear in `classification_conflicts` and require renewed identity/type confirmation. Known stored contacts absent from the current collection appear in `unverified_contacts`. Neither condition deletes private annotations. A nameless discovered contact cannot silently count as complete coverage. Status priority is `awaiting_ownership_confirmation`, then `awaiting_entry_classification`, then `awaiting_contact_check`, then `ready`.

This global coverage state is separate from per-send authorization. Every send requires a current user request naming the exact recipient and exact source files. Contact mode also requires the current request to identify the exact child device. Stored kind/ownership and an earlier name confirmation are never standing permission.

Own-device mode preserves the original narrow gates:

- the exact live display name has one and only one top-level match;
- the private inventory marks that exact entry `entry_type: "device"`, `ownership: "user_confirmed"`, with identity confirmation complete;
- the live row is an own non-local device and has one complete reachable peer;
- contact-device flags are absent;
- aliases, similar names, prior receipt, owner choice, and account resemblance are insufficient.

Contact mode is a separate explicit branch:

- `--recipient` and `--confirm-recipient` exactly match one live non-self row with `is_contact: true` and `live_entry_type: "contact"`;
- the private record has `entry_type: "contact"`, `ownership: "other_person_confirmed"`, and `requires_identity_confirmation: false`;
- both child-device flags are present, equal, and exactly match one nested live non-self `recipient_devices` row;
- the selected contact user ID and child device ID are both complete internally, producing one complete peer;
- the same unique contact and child device are re-resolved immediately before invitation and the complete peer must remain equal.

The CLI never routes account-only, chooses the first device, broadcasts, falls back to another row, or broadens the own-device ownership gate. It does not invent or persist a stable account binding: each request relies on fresh exact-name confirmation and current complete identifiers. Duplicate contact or child names, incomplete identifiers, offline/unpushable children, an identity/type conflict, or any fresh peer change fails closed.

For every new or unregistered top-level live name, present the annotation helper's questions to the user: who owns it, and is it a device, contact, or still unknown? Also surface every current `classification_conflicts` and `unclassified_entries` item. Never answer from the name, observed type, owner category, alias, child devices, or discovery source. Confirmation updates private ownership and stored kind only; it is not send permission. Nested child devices remain live routing choices and are never separate inventory records.

Only absolute paths to existing readable regular files are supported. Directories and symlinks fail clearly; they are not traversed, followed, archived, or silently transformed. The existing GUI helper's separately documented folder support is unchanged.

## Mutation uncertainty and delivery claims

Create, add-content, and invite are mutations and are never automatically retried. Once create may have run, every error includes the known transfer UUID. If a response is lost or ambiguous, inspect that exact UUID with `status`; do not claim “not sent,” generate another UUID, or resend automatically. A repeated command can duplicate user-visible work even when its first response was not observed.

Status meanings relevant to reporting are:

| Code | Name | Allowed claim |
|---:|---|---|
| 1 | `Created` | Local transfer object exists; not invited or delivered |
| 2 | `InviteRequested` | Invitation requested; not delivered |
| 3 | `Invited` | Recipient invited; pending, not delivered |
| 4 | `Pending` | Pending, not delivered |
| 5 | `Active` | Transfer active; not delivered |
| 8 | `Completed` | Blip reports this exact transfer completed |
| 9 | `Cancelled` | Cancelled; not delivered |

Delivery is accepted only when the queried exact UUID reaches `Completed` (`8`) or the human confirms receipt of the exact file. Locked-screen acceptance requires the Mac already locked before a new create/invite and completion tied to that file and recipient. On 2026-09-17, the original own-device CLI created and invited its harmless test transfer while locked before and after; a subsequent exact-ID query returned `Completed` (`8`). This is app-reported own-device completion, not a claimed human receipt and not contact/friend evidence. The contact-capable discovery and explicit contact-plus-child send path are configured and offline-checked only; no locked cross-account end-to-end send has been performed or accepted. A real contact acceptance requires a new current authorization. Earlier CLI probes stopped before invitation on asynchronous observation races; the fixed implementation waits for state publication and never resends their events automatically.

## Privacy boundary

`GetState` necessarily transports opaque application state, including sensitive fields. Responses remain in memory and are never written, cached, logged, or printed raw. For this pinned adapter, parsing allowlists only the discovered-user/device fields required for minimized discovery and exact peer resolution plus field `600` for the exact requested transfer. It skips registration field `200`, auth field `201`, email fields, unknown contact-map keys, and unrelated state without interpreting or copying their payloads. No contact user ID is printed or persisted; complete user/device IDs exist only transiently for exact peer validation. Raw RPC errors are not exposed. Mutable response/discard buffers are zeroed without resizing, including when parsing fails.

The helper does not request credentials, read the app database or keychain, invoke host/takeover functionality, or inspect unrelated transfers. Output must remain minimized; device IDs may be shown only when necessary to resolve identity, and full state is never an output format.

## Wire and schema evidence

The framing source is [`storj/drpc` v0.0.32 `drpcwire/packet.go`](https://raw.githubusercontent.com/storj/drpc/v0.0.32/drpcwire/packet.go). Each fresh socket uses DRPC frames with `control = (kind << 1) | done`, followed by varint stream ID, message ID, payload length, and payload. The helper sends stream 1 `invoke` (kind 1/message 1/method UTF-8), `message` (kind 2/message 2/protobuf), and `close-send` (kind 6/message 3/empty), then reads message frames through `done`. Close is kind 5; error kind 3 is handled without exposing its payload. Reads are bounded to 8 MiB, 8 seconds, and 256 frames.

The two unary methods recovered for the pinned build are:

- `/rpc.Service/GetState`: empty request; response fields `id` (1, uint64) and `state` (2, bytes containing `frontend.State`).
- `/rpc.Service/Dispatch`: request field `event` (1, bytes containing `google.protobuf.Any`); successful response is empty. `Any.type_url` is `type.googleapis.com/event.<Name>`, and `Any.value` contains the event protobuf.

The mutation schemas used are `TransferCreateRequested { transfer_id: 1, peer_id: 2 }`, `TransferAddContentRequested { transfer_id: 1, locations: 2 repeated }`, and `TransferInviteRequested { transfer_id: 1, peer_id: 2 }`. The installed `BlipKit` framework supplies corroborating local evidence: exported `_libblip_client_create`, `_libblip_get_state`, and `_libblip_dispatch`; demangled `Core` RPC connection/dispatch accessors and `Event.protobuf`; the embedded `frontend/cmd/libblip/rpc/service.proto` descriptor; exact `/rpc.Service/GetState` and `/rpc.Service/Dispatch` strings; and protobuf symbols for all three transfer events. Embedded Go source-path strings identify `storj.io/drpc v0.0.32`. Running Blip and BlipShare were observed using the local Unix socket. These are implementation observations, not a vendor stability promise.

Public evidence remains narrower: in a [2025-07-22 comment](https://news.ycombinator.com/item?id=44651955), a self-identified [Blip cofounder](https://news.ycombinator.com/item?id=44651802) wrote that Blip did not yet have an API. That is historical evidence, not proof about every later build; no current public invocation contract was found in the sources examined.

## GitHub project fit

- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) provides a useful methodology for wrapping a real engine/API/CLI, but it does not create a missing backend. Its inspected registries had no Blip file-transfer entry; the small standard-library helper directly wraps the now-verified local backend.
- [OpenCLI](https://github.com/jackwener/opencli) can pass through an existing binary, while its browser/CDP and AppleScript/Accessibility adapters do not make a native locked session headless. Registration would add discovery, not capability, and is unnecessary here.
- [Peekaboo](https://github.com/openclaw/Peekaboo) is generic macOS Accessibility/UI automation. Background window control is not the same as screen-locked, UI-independent operation.

No Blip file-transfer adapter was found in the inspected current registries, documented catalogs, and scoped indexed searches. This is not a claim that none exists anywhere on GitHub, and none of these projects is evidence of public or vendor-supported Blip RPC.

## Upgrade and regression checks

Follow `upgrade-validation.md` before supporting a different Blip build. Run `python3 -m unittest discover -s tests -p 'test_*.py'` from the skill root for offline regressions; these tests use synthetic state and never send. Fresh model-session diagnostics on 2026-09-17 succeeded in OMP, Claude Code, and Hermes while locked. Codex discovered and executed the helper under its workspace-write sandbox, but `doctor` returned exit 3 with `rpc_unavailable` and `screen_lock_unavailable`; no sandbox bypass was attempted. Hermes produced a successful diagnostic and final report before its outer process timed out; Codex's outer session also timed out after its failed diagnostic. Do not claim four fully passing runtimes.