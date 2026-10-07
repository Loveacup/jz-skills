# Shared private inventory initialization

All runtimes use one private state directory. The default is `~/.agents/private/blip-transfer`; `--state-dir` exists only for an intentionally isolated state directory, such as a disposable test fixture. Paths are expanded and made absolute without resolving or rewriting symlinks. The state directory, lock file, `devices.json`, and `initialization.json` must not be symlinks.

The private inventory contains both devices and contacts. For schema and API compatibility the collection and live-output property remain named `devices`; an entry in that array can have `entry_type: "device"`, `"contact"`, or `"unknown"`. An omitted `entry_type` is read as `unknown`. This private kind memory is identity context only: it is not live discovery, ownership evidence, or permission to send.

The inventory CLI does not open Blip, inspect the UI, discover entries, prepare files, or send anything. Obtain successful current output from the producer before `sync`. The RPC adapter emits `discovery_scope: "discovered_devices_and_contacts"` after parsing the installed (verified or probe-passing) build's full current discovered-user collection. It emits own physical devices and non-self contacts as top-level rows; a contact's nested `recipient_devices` are informational send choices and are never independent inventory entries. The unlocked GUI helper emits `discovery_scope: "visible_devices_and_contacts"` because it inspects the visible chooser/status surface. Both scopes are current contact-capable evidence, not authorization or an exhaustive address book, and they do not assert that the two snapshots contain identical names. In particular, a local/self device visible to RPC may be omitted from the GUI recipient surface.

## Exact CLI

```text
python3 scripts/inventory.py [--state-dir DIR] init [--runtime LABEL]
python3 scripts/inventory.py [--state-dir DIR] sync < successful-devices.json
python3 scripts/inventory.py [--state-dir DIR] confirm \
  --device EXACT \
  --ownership user|family-shared|other|unknown \
  --label LABEL \
  [--entry-type device|contact|unknown] \
  [--confirmed-by-user]
python3 scripts/inventory.py [--state-dir DIR] note \
  --device EXACT \
  [--label LABEL] \
  [--alias ALIAS]... \
  [--notes TEXT]
```

Global options precede the subcommand. Every successful command writes JSON to standard output. Exit status `0` means the operation completed and, for `sync`, `initialization_status` is `ready`. A successful `sync` exits `2` whenever its structured output has a non-ready `initialization_status`; this includes ownership questions, duplicate-name ambiguity, live entries whose stored kind is unknown or conflicts with observation, a missing/unverified contact check, or absent previously known contacts. Exit status `1` is a state, input, filesystem, or validation failure. Standard argument-parser usage errors also use exit status `2`, so callers must inspect valid JSON rather than interpreting an exit code alone. The `note` command requires at least one of `--label`, `--alias`, or `--notes`.

Capture and validate the producer command's exit status and JSON before passing its output to `sync`. Never pipe a transport error or partial discovery. A producer's `devices` command and the following inventory synchronization are separate checks; neither prepares or sends a file.

## Required initial setup and recurring preflight

Initial setup and every later transfer session use the same coverage loop:

1. Run `init` to create or validate the shared private state without replacing existing records.
2. Run the RPC adapter's current `devices` query and synchronize that successful output. Its `discovered_devices_and_contacts` scope is the required per-session current own-device and external-receiver check, including when the screen is locked. Own physical rows carry observed device kind; technical `is_contact: true` external rows do not supply a human kind.
3. If the actual send uses the GUI route, the session must be unlocked and the GUI helper's current `devices` output must also be inspected; its `visible_devices_and_contacts` scope is independently accepted as current contact coverage. Do not invoke GUI/Accessibility operations while locked.
4. Surface every `ownership_question`, `classification_conflicts`, `unclassified_entries`, and `unverified_contacts` entry. Ask the human to identify each new exact name and to classify every live unknown/missing or genuinely conflicting kind as a device, contact, or still unknown. Do not infer type or ownership from the name, owner, alias, account resemblance, technical `is_contact`, `live_entry_type`, child rows, or which producer exposed it.
5. Apply only the human's answer with `confirm`, then synchronize the relevant current live output again. The most recent sync alone determines current coverage; an earlier contact-capable result never carries forward through a later same-account-only, unknown, or partial snapshot.

Each `sync` recomputes coverage from the current input. `discovered_devices_and_contacts` describes the complete current discovered collection returned by the version-checked RPC state, not the user's exhaustive Blip address book. Known human-confirmed contacts absent from that collection still remain in `unverified_contacts`, and a top-level discovered receiver without a usable exact name must fail closed or remain pending rather than silently count as covered. Nameless nested children remain informational and may satisfy only the separate account-route reachability requirement; they are not inventory entries.

Initialization readiness and send authorization are independent. A pending contact check, classification conflict, or unrelated unresolved name must be reported, but it does not grant or revoke authorization for a separately verified recipient. Every send still requires a current user request naming the files and exact top-level recipient. Exact-child mode additionally requires the exact child name; account mode instead requires explicit `--recipient-scope account` and forbids child flags.

## `init`

`init` creates the state directory with mode `0700`. When absent, it creates `devices.json` and `initialization.json` with mode `0600` and an atomic no-overwrite operation. The initial inventory has an empty `devices` array and a policy requiring identity confirmation for every new entry while forbidding standing send authorization. Initialization records the UTC date and platform; `--runtime` adds an informational runtime label only when `initialization.json` is first created.

Existing records are never replaced or reset. `init` validates existing JSON and schema, including optional `entry_type`, `label: string`, `aliases: string[]`, and `notes: string` annotations, under the same interprocess lock. It normalizes the managed file modes and fails closed for corrupt JSON, malformed annotations, unsupported schemas, non-regular files, or symlink destinations. Re-running `init` from another runtime therefore continues to use the same private records and annotations rather than creating runtime-specific inventory.

`initialization.json` starts with `status: "awaiting_live_sync"`. Each successful live synchronization records its current scope and coverage. Status priority is deterministic:

1. `awaiting_ownership_confirmation` when `ownership_questions` is nonempty, including an observed/stored type conflict that requires identity reconfirmation;
2. otherwise `awaiting_entry_classification` when `unclassified_entries` is nonempty;
3. otherwise `awaiting_contact_check` when `contacts_checked` is false or `unverified_contacts` is nonempty;
4. otherwise `ready`.

The structured sync output exposes the same value as `initialization_status`. It also reports `discovery_scope`, `contacts_checked`, `ownership_questions`, `classification_conflicts`, `unclassified_entries`, and `unverified_contacts`, so a caller can state exactly why setup is pending. `unclassified_entries` contains current live names whose stored `entry_type` is unknown or missing and names whose actually observed `live_entry_type` conflicts with a confirmed stored kind. `classification_conflicts` names the latter subset. A missing `live_entry_type` supplies no observation and therefore cannot conflict with a confirmed stored kind; the row still remains unclassified if its stored kind is unknown. `contacts_checked` is true for `discovered_devices_and_contacts` and `visible_devices_and_contacts`; an unknown or missing input scope is normalized to `unverified` and cannot produce `ready`.

## `sync`

`sync` accepts a current producer object containing a `devices` array of rows with `display_name`, optional observed `live_entry_type`, and its `discovery_scope`. The caller must ensure the object came from a successful current RPC or native GUI discovery. The historical property name `devices` is retained for compatibility even though rows may represent devices or contacts. Technical `is_contact` is an account relation, not an inventory kind. Under the shared lock, `sync`:

- matches display names exactly and never infers a rename, alias, owner, or entry type;
- validates `live_entry_type` as `device` or `contact` only when a producer genuinely supplies that observation, exposes it in current annotated output only then, and never stores it as the human-confirmed `entry_type`;
- updates `last_seen` for each observed top-level exact name;
- adds each newly observed top-level name with `entry_type: "unknown"`, `ownership: "unconfirmed"`, `requires_identity_confirmation: true`, `evidence_type: "live_observation"`, and `standing_send_authorization: false`, including external `is_contact` rows without a live kind;
- ignores an external row's nested `recipient_devices` for enrollment, so named or nameless child devices never become top-level private records;
- preserves existing ownership, entry type, labels, aliases, notes, evidence, and records absent from the current live list;
- retains one record for a duplicated exact live name, while the returned annotation still reports the duplicate and requires disambiguation;
- normalizes an unknown or missing input scope to `unverified`, persists that `discovery_scope` and `contacts_checked`, and sets `contacts_checked` true only for `discovered_devices_and_contacts` or `visible_devices_and_contacts`;
- emits and persists in `classification_conflicts` every current live name whose actually present `live_entry_type` differs from its confirmed stored `entry_type`, without changing that stored kind;
- emits and persists in `unclassified_entries` every current live name whose stored `entry_type` is unknown/missing or genuinely conflicts with a present observation;
- emits and persists in `unverified_contacts` every previously known human-confirmed `entry_type: "contact"` name absent from this current snapshot.

Absence never deletes a record or its notes. It is surfaced as failed current coverage instead. An absent remembered contact remains explicit even under a contact-capable snapshot, because the scopes describe the current discovered/visible collection rather than an exhaustive address book. The output is the annotation shape produced by `annotate.py`, augmented with current initialization coverage.

Every new exact display name must be shown to the human as an ownership question, even if it resembles a known alias or arrives with technical `is_contact` or an observed `live_entry_type`. New entries always start with stored `entry_type: "unknown"` and therefore also appear in `unclassified_entries`. A legacy or already ownership-confirmed live record with unknown/missing type remains `awaiting_entry_classification`. When `live_entry_type` is actually present, a stored/observed type conflict sets identity confirmation pending, appears in `classification_conflicts` and `unclassified_entries`, and requires a human answer before `confirm` may change the stored kind. Absence of `live_entry_type` preserves any confirmed kind without creating a conflict. Do not hide, auto-answer, or postpone any question because a different known target is usable.

## `confirm`

`confirm` changes only the one existing inventory record whose `display_name` exactly equals `--device`; it never creates a record. `user`, `family-shared`, and `other` map to the documented confirmed ownership values and require `--confirmed-by-user`. `unknown` keeps identity confirmation required.

`--entry-type device|contact|unknown` changes the private kind only when supplied. Supplying it requires `--confirmed-by-user`; omitting the option preserves the existing kind. Entry type and ownership are orthogonal: neither may be inferred from the other, technical `is_contact`, observed `live_entry_type`, or nested child devices, and neither is send permission. An omitted/unknown kind for a live entry remains in `unclassified_entries`; a genuine present stored/observed conflict also remains in `classification_conflicts` until the human explicitly confirms the correction. The command records the supplied friendly label, UTC evidence date, and `evidence_type: "user_confirmation"` only when the human-confirmation flag is present, preserves unrelated fields such as aliases and notes, and never marks a send authorized.

`--confirmed-by-user` is an audit assertion, not permission to send. The agent must first ask the human who owns the exact observed top-level entry and whether it is a device, contact, or unknown, including when a real live observation conflicts with stored kind. It must never supply the flag from its own inference, an alias resemblance, `is_contact`, `live_entry_type`, nested devices, prior transfer history, or another runtime's guess. Choosing `unknown` is not a bypass: unresolved ownership stays identity-sensitive, and unresolved kind stays `awaiting_entry_classification` while the entry is live. Every future send still requires a current user request naming the files and top-level recipient; exact-child mode also requires the exact child, while account mode requires explicit account scope and no child flags.

## `note`

`note` updates private human-readable memory on exactly one existing record. `--label` replaces the label only when supplied, repeated `--alias` values replace the aliases array only when supplied, and `--notes` replaces the notes only when supplied. An explicitly empty notes value clears notes. The command rejects an unknown or inexact `--device` and never creates a record.

Labels, aliases, and notes are untrusted annotation data. Alias collisions are permitted, but no alias is ever an alternate `display_name`: annotations cannot select a live entry, satisfy ownership confirmation, change entry type, change ownership or evidence, or authorize a send. The command preserves `entry_type`, `ownership`, `requires_identity_confirmation`, `standing_send_authorization`, and all evidence fields exactly as stored.

All mutating operations use the same `.inventory.lock` and atomic file replacement. They never grant standing permission and never delete records merely because an entry is absent from one discovery.
