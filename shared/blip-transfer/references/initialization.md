# Shared private inventory initialization

All runtimes use one private state directory. The default is `~/.agents/private/blip-transfer`; `--state-dir` exists only for an intentionally isolated state directory, such as a disposable test fixture. Paths are expanded and made absolute without resolving or rewriting symlinks. The state directory, lock file, `devices.json`, and `initialization.json` must not be symlinks.

The inventory CLI does not open Blip, inspect the UI, discover devices, prepare files, or send anything. A runtime must first obtain a successful, valid `devices` JSON response from the native helper and only then pipe that response to `sync`. Never pipe failed or partial discovery output.

## Exact CLI

```text
python3 scripts/inventory.py [--state-dir DIR] init [--runtime LABEL]
python3 scripts/inventory.py [--state-dir DIR] sync < successful-devices.json
python3 scripts/inventory.py [--state-dir DIR] confirm \
  --device EXACT \
  --ownership user|family-shared|other|unknown \
  --label LABEL \
  [--confirmed-by-user]
```

Global options precede the subcommand. Every successful command writes JSON to standard output. Exit status `0` means the operation completed without unresolved live ownership questions. For `sync`, exit status `2` means its JSON output is valid but contains mandatory `ownership_questions` or duplicate-name ambiguity. Exit status `1` is a state, input, filesystem, or validation failure. Standard argument-parser usage errors also use exit status `2`.

## `init`

`init` creates the state directory with mode `0700`. When absent, it creates `devices.json` and `initialization.json` with mode `0600`, schema version 1, and an atomic no-overwrite operation. The initial inventory has an empty `devices` array and a policy requiring identity confirmation for every new device while forbidding standing send authorization. Initialization records the UTC date and platform; `--runtime` adds an informational runtime label only when `initialization.json` is first created.

Existing records are never replaced or reset. `init` validates existing JSON and schema under the same interprocess lock, normalizes the managed file modes, and fails closed for corrupt JSON, unsupported schemas, non-regular files, or symlink destinations. Re-running `init` from another runtime therefore continues to use the same records rather than creating a runtime-specific inventory.

`initialization.json` starts with `status: awaiting_live_sync`. A successful live sync records `last_sync_date`, `unresolved_live_device_count`, and `status: awaiting_ownership_confirmation` or `ready`. An ownership answer is followed by another live sync before claiming setup is ready. If the Mac is locked, local metadata initialization may complete but live synchronization remains pending; never substitute cached names for a fresh discovery.

## `sync`

`sync` accepts only an object shaped as `{ "devices": [{ "display_name": "..." }] }` on standard input. The caller is responsible for ensuring it came from a successful current native discovery. Under the shared lock, `sync`:

- matches display names exactly and never infers a rename, alias, or owner;
- updates `last_seen` for each observed exact name;
- adds each newly observed name as `unconfirmed`, with `requires_identity_confirmation: true`, `evidence_type: "live_observation"`, and `standing_send_authorization: false`;
- preserves existing ownership, labels, aliases, evidence, and records absent from the current live list;
- retains one record for a duplicated exact live name, while the returned annotation still reports the duplicate and requires disambiguation.

The output is the same annotation shape produced by `annotate.py`. Every new exact display name must be shown to the human as an ownership question, even if it resembles a known alias. Do not hide, auto-answer, or postpone that question because a different known target is usable. Unknown or incomplete first-use state remains explicitly unconfirmed.

## `confirm`

`confirm` changes only the one existing inventory record whose `display_name` exactly equals `--device`; it never creates a record. `user`, `family-shared`, and `other` map to the documented confirmed ownership values and require `--confirmed-by-user`. `unknown` keeps identity confirmation required. The command records the supplied friendly label, UTC evidence date, and `evidence_type: "user_confirmation"` only when the human-confirmation flag is present (otherwise `unconfirmed`), preserves unrelated records and fields such as aliases, and forces standing send authorization to false.

`--confirmed-by-user` is an audit assertion, not permission to send. The agent must first ask the human who owns the exact newly observed device and must never supply the flag based on its own inference, an alias resemblance, prior transfer history, or another runtime's guess. Choosing `unknown` is not a bypass: the record remains blocked for identity-sensitive use. Every future send still requires a current user request naming the files and recipient.

All mutating operations use the same `.inventory.lock` and atomic file replacement. They never grant standing permission and never delete records merely because a device is absent from one discovery.
