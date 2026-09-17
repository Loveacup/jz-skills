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
python3 "$SKILL/scripts/blip-rpc.py" send \
  --recipient "EXACT_LIVE_DEVICE_NAME" \
  --confirm-recipient "EXACT_LIVE_DEVICE_NAME" \
  --transfer-id "UUID" \
  "/absolute/path/to/authorized-file" ["/absolute/path/to/another-file"]
```

The caller must create and retain a fresh UUID for one intended transfer. The helper does not choose an implicit transfer identity. `--confirm-recipient` is a mechanical exact-match guard, not evidence of consent.

Exit codes: `0` means a successful non-transmitting check or an observed `Completed` transfer; `devices` uses `2` for ownership questions; `send` and `status` use `10` for a valid but not completed transfer. Exit `10` is not a transport failure and must never trigger automatic resend. JSON `code` and the retained transfer UUID explain other failures. CLI sends are serialized with an owner-only nonblocking `.blip-rpc-send.lock`; a busy caller fails rather than racing another runtime.

`doctor` is non-transmitting and does not need GUI or Accessibility access. It accepts only Blip version `1.1.16`, build `20260425132215`, and the fixed local socket under `~/Library/Group Containers/AY8UB8KTUX.blip/Library/Caches/sock`. It verifies that the socket is a socket and is owned by the current UID. There is no remote-address or socket override. A different app version/build, missing socket, wrong owner, or wrong filesystem type is a hard failure: do not guess that the wire schema is compatible.

`devices` is read-only. It reports the minimum live device names and identifiers needed to disambiguate recipients, joins them through the adjacent annotation helper, emits every outstanding `ownership_question`, and always reports `sending_authorized: false`. It does not grant permission.

`status` reads only the transfer named by `--transfer-id` and reports its status code/name and `completed` boolean. It is not a global transfer-history command.

`send` performs create, content attachment, validation, and one invite. Dispatch acknowledgments precede asynchronous state publication: the CLI polls for the newly created object and exact prepared archive without repeating mutations. Before invitation it requires `Created` (`1`), outgoing, the exact peer, no local/remote errors, `content_job_count == 0`, and exact authorized filenames and sizes. It then revalidates the unique live recipient and source-file identity immediately before the single invite. A post-invite read may still report `Created`; that is an observation delay, not delivery. Query the same UUID later.

## Authorization and supported scope

Every send requires a current user request naming the exact recipient and exact source files. The currently authorized locked-screen test covered only its user-confirmed iPhone and one 92-byte harmless file; it grants no standing permission for another file, recipient, or future transfer.

The first supported recipient scope is deliberately narrow:

- the exact live display name has one and only one match;
- the private inventory marks that exact device `user_confirmed`;
- the live peer belongs to the same Blip account and is not this Mac;
- aliases, similar names, prior receipt, and account resemblance are insufficient;
- family/shared, other-person, unknown, absent, duplicate, or cross-account/email contacts are unsupported for this path.

For every new or unregistered live name, present the annotation helper's question to the user: is it the user's own device, family/shared, another person's, or still unknown? Never answer from the name. Confirmation updates ownership evidence only; `standing_send_authorization` and live `sending_authorized` remain false. A separately authorized send to an already confirmed device may proceed, but the new-device questions must still be surfaced.

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

Delivery is accepted only when the queried exact UUID reaches `Completed` (`8`) or the human confirms receipt of the exact file. Locked-screen acceptance requires the Mac already locked before a new create/invite and completion tied to that file and recipient. On 2026-09-17, the final CLI created and invited its harmless test transfer while locked before and after; a subsequent exact-ID query returned `Completed` (`8`). This is app-reported completion, not a claimed human receipt confirmation. Earlier CLI probes stopped before invitation on asynchronous observation races; the fixed implementation waits for state publication and never resends their events automatically. The two uninvited test drafts were subsequently removed under explicit user authorization, without deleting source files.

## Privacy boundary

`GetState` necessarily transports opaque application state, including sensitive fields. Responses remain in memory and are never written, cached, logged, or printed raw. Parsing allowlists state field `500` (same-account devices for target resolution) and field `600` (the exact requested transfer). Registration field `200`, auth field `201`, email fields, and unrelated state are skipped without interpreting or copying their payloads. Raw RPC errors are not exposed. Mutable response/discard buffers are zeroed without resizing, including when exception tracebacks retain memoryviews.

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