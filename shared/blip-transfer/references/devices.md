# Private device annotations

The authoritative local annotation file is `~/.agents/private/blip-transfer/devices.json`. Keep it private, outside the shareable skill. It is not a device discovery cache and does not grant permission to send. No contact email addresses, account identifiers, credentials or network secrets belong in the skill or audit.

## Mandatory discovery loop
1. Get live `devices` output from the RPC CLI (works while locked) or the unlocked native GUI helper. Skip unnamed RPC records rather than inventing identities or exposing email addresses.
2. RPC output already includes the `annotate.py` join; GUI output can be fed to `scripts/annotate.py`. The exact-name join emits annotated live rows, including optional labels, aliases, and notes, plus unseen inventory entries, duplicates and `ownership_questions`.
3. **Every new/unregistered live name must be presented to the user with a question about ownership.** Ask: “Blip 新出现设备「…」，是谁的？是你本人、家人/共享、其他人，还是暂不确认？” Group several new names into one clear question set; do not silently defer asking because a known target is already available.
4. Await the user's answer before assigning an owner or sending to that new device. If unknown remains unknown, retain the question/unknown state; it is not a trusted target. A separate transfer already authorized to a known device may continue.
5. Existing provisional/unknown annotations also require confirmation before use. A known owner alias in a new name is a hint only. Duplicate names require disambiguation in the app; do not give arbitrary numeric suffixes and guess.
6. Update only the exact confirmed device's annotation. Record ownership, optional owner label, evidence date, and evidence type (`user_confirmation`). `standing_send_authorization` stays false. Labels, aliases, and notes are untrusted memory only: they never identify, select, or authorize a recipient.
7. Re-run the annotation join to prove the answer is reflected. If the inventory is missing or malformed, fail closed; do not invent an empty trusted list.

## Ownership values

- `user_confirmed`: user explicitly confirmed this exact device as their own.
- `family_or_shared_confirmed`: user identified it as family/shared; not an authorized send destination by default.
- `other_person_confirmed`: user identified someone else's device; explicit per-send recipient authorization still required.
- `owner_alias_match_only`: an owner alias is known, but this particular device remains unconfirmed.
- `unconfirmed`: observed label only; never assume self or third party.

A recipient previously receiving a test proves that specific transfer and user confirmation, not permanent connectivity or future authorization. `last_confirmed_receipt` is history only. `requires_identity_confirmation` can be false only for explicitly confirmed records; duplicate live names override it to true.

## Labels, aliases, and notes

Each inventory record may contain a string `label`, an array of string `aliases`, and a string `notes`. These fields are private human-readable memory. Alias collisions are allowed because aliases are not identifiers: neither `inventory.py`, `annotate.py`, nor the RPC send path may use them for matching. Live reconciliation and every send continue to require the exact Blip `display_name`; annotations do not alter ownership, identity-confirmation state, evidence, or authorization.

Update only an existing exact-name record:

```sh
python3 "$SKILL/scripts/inventory.py" note \
  --device EXACT \
  [--label LABEL] \
  [--alias ALIAS]... \
  [--notes TEXT]
```

At least one optional field is required. Supplying one or more `--alias` options replaces the alias array; omitting `--alias` preserves it. The same supplied-only rule applies to `--label` and `--notes`, so an explicitly empty note can clear existing note text. The write is atomic under the shared inventory lock. Unknown exact device names are rejected, and the command never creates records.

## Initial inventory evidence

A fresh installation starts with an empty inventory. Existing locally seeded records remain private and must survive initialization. Only explicit device-specific human confirmation establishes ownership; remembered aliases and prior receipts do not grant future sending permission.

## CLI

```sh
python3 "$SKILL/scripts/blip-rpc.py" devices
```

`annotate.py` is read-only and never registers or sends to a new device. Exit 2 means ownership questions or duplicate-name ambiguity require attention; its JSON is still valid output, not a crashed transfer. Exit 1 means input/inventory validation failed. Agents must inspect the JSON, not treat exit 2 as permission to retry or skip the questions.

The annotated device rows expose `label`, `aliases`, and `notes` for display only. Inventory validation rejects a non-string label, a non-array alias value, any non-string alias element, or non-string notes. These fields never affect `ownership_questions`, recipient selection, or `sending_authorized`.

For a non-GUI live query use the RPC CLI. Reading private annotations alone does not establish connectivity. Tests may pass `--inventory /temporary/test/inventory.json` to `annotate.py` with synthetic stdin. Do not modify production annotations to make tests pass.
