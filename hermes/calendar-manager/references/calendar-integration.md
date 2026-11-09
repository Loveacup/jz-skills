# Calendar integration and attachment evaluation

Use when choosing a calendar backend, investigating missing attachment support, or considering a CLI wrapper. This is a capability-assessment procedure, not a claim that any untested upload path works.

## Start with the user outcome

1. Separate ordinary event CRUD from the missing capability: original image attachment, account-protected external link, mobile preview, offline access, or background execution. Do not quietly replace a requested native attachment with a link.
2. Preserve the working ordinary-event path while investigating the gap. A research request permits assessment, not server deployment, calendar migration, DNS or permission changes.
3. Check the product's official documentation, the installed interface, and the actual user workflow separately. A product can support attachments through its UI while its public automation API omits them.
4. Compare the smallest viable backend options before generating a wrapper. Include existing self-hosted infrastructure when relevant, but do not infer which services are installed from old plans.

## Inspect native interfaces

For macOS Calendar, locate the installed scripting dictionary rather than guessing its basename:

```python
from pathlib import Path
for path in Path('/System/Applications/Calendar.app').rglob('*.sdef'):
    print(path)
```

Read the `event` class's properties/elements. For EventKit, resolve the active SDK with `xcrun --show-sdk-path` and inspect `System/Library/Frameworks/EventKit.framework/Headers/EKEvent.h` and `EKCalendarItem.h`. Compare against current Apple Developer documentation. Absence of a public attachment setter establishes that interface's coverage, not the impossibility of every other route.

Apple documents file attachments in Mac Calendar, iPhone Calendar and iCloud.com. Mac instructions use the Attachments field or drag-and-drop into event details. Treat these as documented capabilities until exercised on the selected account/device; do not write a failed GUI attempt into a recommended procedure. Check current iCloud limits rather than relying on remembered numbers: the event size limit includes the event and attachments together.

Sources:
- Mac attachments: https://support.apple.com/guide/calendar/add-notes-a-url-or-files-to-events-icl58679aba2/mac
- iPhone event editing: https://support.apple.com/guide/iphone/create-and-edit-events-in-calendar-iph3d110f84/ios
- iCloud.com event editing: https://support.apple.com/guide/icloud/create-and-edit-an-event-mmfbbb32be/icloud
- iCloud limits: https://support.apple.com/en-us/103188
- EventKit: https://developer.apple.com/documentation/eventkit/ekcalendaritem

## Choose a backend, not just a command name

- AppleScript plus icalBuddy: retain for ordinary event writes/queries when proven adequate. Read back event fields and alarms; do not infer attachment support from successful CRUD.
- EventKit helper: evaluate for structured metadata access and stable app authorization identity when ordinary CRUD has a demonstrated problem. Check permission level, usage descriptions and the real calling context. Do not build it merely to solve attachments if its public interface still lacks that operation.
- Native UI: consider for a bounded attachment operation; verify the actual target window and editable event before acting. Missing UI state is not proof of permanent incompatibility, and permissions must not be reset to make a test pass without authorization.
- CalDAV: evaluate for headless event operations. Use fixed operation UID/resource paths, create with `If-None-Match: *`, and update with current ETag/`If-Match`. On timeout, GET and reconcile the original resource before retrying. Preserve unknown properties, time zones, alarms and recurrence exceptions. iCloud CalDAV authenticates with the Apple ID email plus an app-specific password (generated under account.apple.com → 登录与安全 → App 专用密码, requires two-factor authentication), never the main password; collect it through the private-key-input page, not chat.
- Self-hosted file service: reuse an existing maintained service when acceptable, but label its URL as an external file entrance. Account-authenticated URLs may require browser login; opaque share tokens and signed URLs are bearer access, not account authorization. Do not upload medical codes to public hosting as an implicit fallback.
- Self-hosted CalDAV: verify iPhone account sync and attachment interoperability separately. A Nextcloud web attachment feature or Radicale/Baikal CalDAV support is not evidence of iPhone native attachment support. Avoid introducing a full collaboration platform solely to fill an unverified attachment gap.

For CalDAV managed attachments, inspect the server's advertised capabilities before using RFC 8607 operations. Its `calendar-managed-attachments` DAV token is a discovery gate, not end-to-end acceptance. Generic RFC 5545 `ATTACH` fields, inline data and hosted URLs are not interchangeable with managed upload support. Attachment-add uses POST: after a lost response, read the event/managed IDs before retrying to avoid duplicates.

### Evidence boundaries for iCloud trials

Prior trial notes report capability advertisement, a successful upload and byte-exact retrieval on a tested iCloud path. These are bounded observations, not an Apple support contract or proof across accounts, server versions, file types and devices. The notes are not a reproducible compatibility matrix; revalidate the selected path with synthetic data under separate authorization. Keep account identifiers, event contents, attachment URLs, tokens and raw logs out of shared skill material.

RFC 8607 specifies `Cal-Managed-ID` for a successful add. The trial notes instead describe an HTTP 200 response with an empty body and a `Location` header, without `Cal-Managed-ID`; a later event read contained a managed attachment. Treat this as a reported server deviation, not the universal response shape. Save the pre-operation attachment set and event identity. After the request, freshly GET that same event, parse unfolded ICS properties and reconcile the before/after managed IDs. A returned ID must be present in that event before success is reported.

The notes also describe an attachment value with an extra path segment relative to `Location`. A `Location + "/"` prefix can be a diagnostic clue, but **prefix matching alone is not a safe or general attachment-identity rule**. Even exact URL equality does not establish which operation created an existing attachment. Validate parsed HTTPS origin and path boundaries, require a unique new managed ID in the intended event, check expected file metadata and, when authorized, byte integrity. Ambiguous matches, concurrent changes, missing evidence or a lost response remain `unknown`; do not automatically re-upload or remove a guessed attachment. Treat attachment URLs as potentially bearer-access secrets.

A candidate flow to revalidate is: OPTIONS the calendar home; inspect the DAV token; POST the intended event resource with `?action=attachment-add`, raw bytes, `Content-Type`, `Content-Disposition: attachment; filename="sample-image.png"`, and `Prefer: return=representation`; then independently GET the event and reconcile its managed attachment. For authorized retrieval, compare SHA256 of downloaded and original bytes, not just HTTP 200. Upload, event linkage and phone access require separate evidence.

Discovery may return shard hosts and an explicit HTTPS port. Parse the URL rather than treating a permissive substring regex as destination validation; check scheme, hostname, port, userinfo and each redirect against an explicit policy. A separately validated attachment host is not authorization to forward CalDAV credentials to it. Do not broaden an allowlist solely to make a failed request pass. Offline fake-transport tests establish local handling only, not iCloud compatibility or phone sync.

### Filename, removal and presentation limits

1. **Filename behavior depends on the tested client and encoding.** The trial notes report a raw non-ASCII header failing in the HTTP client and an encoded filename not being preserved as expected. A client-side header encoding failure is not proof that iCloud rejects all Chinese filenames; one `filename*` trial does not establish all encoding combinations. Use a descriptive ASCII filename as a conservative fallback for that path, preserving the original file bytes, and read back the stored filename. Treat Unicode support as unverified until tested with the selected client/server.
2. **A successful HTTP status does not prove attachment removal.** The notes report `attachment-remove` returning 200 while `ATTACH` remained in a subsequent read. This does not establish that removal always fails, or that deleting the event is necessary. Use only the documented scoped attachment-remove POST for an authorized target, then prove the event still exists and the exact managed ID is absent. If it remains, report cleanup unverified and stop; investigate request semantics and synchronization without destructive fallback. **Never use event deletion as the default attachment cleanup.** Never send `DELETE event-url?managed-id=...`: it still targets the event resource and may delete the event. Event deletion requires separate explicit authorization and exact event identity, including for disposable tests.
3. **Phone presentation is device/version/file-type dependent.** The reported iOS view displayed an attachment icon and filename rather than an inline image. Do not extrapolate that observation to every iOS version or attachment type. Use a descriptive filename and verify opening, download, image/QR readability and any requested offline behavior on the actual target device.
4. **An external explanation page is optional, not a native attachment.** Offer an event URL for rich explanatory content only when the user accepts external hosting and authorizes the upload. Check access controls, retention and revocation before publishing sensitive material; do not silently replace an original-file attachment or expose medical information. No hosting provider is required by this workflow.

Sources: https://www.rfc-editor.org/rfc/rfc8607.html ; https://www.rfc-editor.org/rfc/rfc4791.html ; https://docs.nextcloud.com/server/stable/user_manual/en/groupware/calendar.html#add-attachments-to-events

## Evaluate CLI-generation proposals

Resolve the exact project first: similarly named Anything/CLI-Anything tools can be REST wrappers, app builders or harness generators. Inspect a pinned upstream README and actual backend methodology before proposing installation.

For CLI-Anything-style harnesses, identify which real backend each command would call. Wrapping AppleScript/EventKit preserves their coverage; wrapping UI clicks preserves UI dependencies and permissions. A CLI generator cannot create a vendor API that the backend does not expose. Closed-source targets can still be wrapped through documented APIs, so lack of source is not by itself proof of impossibility. Recommend reuse of command/test conventions separately from adopting a new toolchain or implementing a missing backend.

## Acceptance and reporting

Use synthetic files/events for a separately authorized prototype. Verify event identity, target account/calendar, original-file integrity, attachment visibility, phone opening/downloading and QR readability. Test logged-out/wrong-account access and revocation for hosted files; if offline use is required, verify it explicitly. Check phone edits do not drop the attachment or overwrite newer metadata.

Report four states separately: event metadata saved, file stored, native attachment linked, phone access verified. A successful upload/URL, a local file link, a zero exit code or an RFC capability flag does not prove the next state. Recommend a candidate conditionally when evidence is incomplete; do not present a prototype plan or failed attempts as a working integration.
