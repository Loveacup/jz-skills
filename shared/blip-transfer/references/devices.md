# Private device annotations

The authoritative local annotation file is `~/.agents/private/blip-transfer/devices.json`. Keep it private, outside the shareable skill. It is not a device discovery cache and does not grant permission to send. No contact email addresses, account identifiers, credentials or network secrets belong in the skill or audit.

## Mandatory discovery loop

1. Get the live `devices` output from the native helper.
2. Feed JSON to `scripts/annotate.py`; this joins exact display names and emits annotated live rows, unseen inventory entries, duplicates and `ownership_questions`.
3. **Every new/unregistered live name must be presented to the user with a question about ownership.** Ask: “Blip 新出现设备「…」，是谁的？是你本人、家人/共享、其他人，还是暂不确认？” Group several new names into one clear question set; do not silently defer asking because a known target is already available.
4. Await the user's answer before assigning an owner or sending to that new device. If unknown remains unknown, retain the question/unknown state; it is not a trusted target. A separate transfer already authorized to a known device may continue.
5. Existing provisional/unknown annotations also require confirmation before use. A known owner alias in a new name is a hint only. Duplicate names require disambiguation in the app; do not give arbitrary numeric suffixes and guess.
6. Update only the exact confirmed device's annotation. Record ownership, optional owner label, evidence date, evidence type (`user_confirmation`) and the user's confirmed friendly alias. `standing_send_authorization` stays false. Atomic replacement is recommended; preserve unrelated records and enforce mode 0600.
7. Re-run the annotation join to prove the answer is reflected. If the inventory is missing or malformed, fail closed; do not invent an empty trusted list.

## Ownership values

- `user_confirmed`: user explicitly confirmed this exact device as their own.
- `family_or_shared_confirmed`: user identified it as family/shared; not an authorized send destination by default.
- `other_person_confirmed`: user identified someone else's device; explicit per-send recipient authorization still required.
- `owner_alias_match_only`: an owner alias is known, but this particular device remains unconfirmed.
- `unconfirmed`: observed label only; never assume self or third party.

A recipient previously receiving a test proves that specific transfer and user confirmation, not permanent connectivity or future authorization. `last_confirmed_receipt` is history only. `requires_identity_confirmation` can be false only for explicitly confirmed records; duplicate live names override it to true.

## Initial inventory

Create the private inventory outside the shareable skill at `~/.agents/private/blip-transfer/devices.json`. Start empty unless the user has explicitly supplied device-specific evidence:

```json
{
  "schema_version": 1,
  "devices": []
}
```

Populate one exact live display name at a time only after the mandatory ownership question is answered. Never copy real device rows into public source or examples. Friendly annotations do not rename anything inside Blip.

## CLI

```sh
swift "$SKILL/scripts/blip.swift" devices | python3 "$SKILL/scripts/annotate.py"
```

`annotate.py` is read-only and never registers or sends to a new device. Exit 2 means ownership questions or duplicate-name ambiguity require attention; its JSON is still valid output, not a crashed transfer. Exit 1 means input/inventory validation failed. Agents must inspect the JSON, not treat exit 2 as permission to retry or skip the questions.

To inspect annotations without operating the GUI, read the private JSON directly. Tests may pass `--inventory /temporary/test/inventory.json` and synthetic stdin. Do not modify production annotations to make tests pass.
