# Private device and contact annotations

The authoritative local annotation file is `~/.agents/private/blip-transfer/devices.json`. Keep it private, outside the shareable skill. It is not a discovery cache and does not grant permission to send. No contact email addresses, account identifiers, credentials, personal names, or network secrets belong in the shared skill or audit output.

The filename, top-level `devices` array, `--device` CLI option, and output `devices` property are retained for schema/API compatibility. Rows may represent either devices or contacts. Each private record may set `entry_type` to `device`, `contact`, or `unknown`; a missing value means `unknown`. Entry type is private kind memory, not ownership, reachability, or send permission.

## Mandatory discovery loop

Initial setup and every transfer session repeat this loop:

1. Run the RPC CLI's current `devices` query and synchronize its output. This works while locked. Its `discovery_scope: "discovered_devices_and_contacts"` covers the full current discovered-user collection: own physical devices plus discovered non-self contacts. It is not authorization or an exhaustive address book.
2. If the send uses the unlocked GUI route, also inspect and synchronize the GUI helper's current `devices` output. Its `discovery_scope: "visible_devices_and_contacts"` is independently accepted as a current contact-capable check. Never invoke GUI/Accessibility operations while locked.
3. Inspect `initialization_status`, `ownership_questions`, `classification_conflicts`, `unclassified_entries`, `contacts_checked`, and `unverified_contacts`. A prior snapshot does not carry over to a later partial, same-account-only, or unknown-scope sync. Unknown/missing input scope is normalized to `unverified`.
4. Present every new/unregistered live name to the user. Ask both who it belongs to—user, family/shared, another person, or unknown—and whether it is a device, contact, or still unknown. Also ask about any live legacy, unknown, or stored/observed type conflict listed in `unclassified_entries` or `classification_conflicts`. Group several names into one clear question set, but do not silently defer them because a known target is usable.
5. Surface every known contact absent from the current snapshot through `unverified_contacts`. Absence does not delete the private record, its aliases, or its notes. It means that remembered contact is not covered by the current discovered/visible collection.
6. Await the user's answer before assigning ownership or stored entry type. Never infer either field from a display name, owner choice, alias, account resemblance, producer scope, observed `live_entry_type`, nested child devices, or prior transfer. A new identity remains unavailable until ownership is confirmed. Entry type itself is not send permission, so a separately authorized transfer to an already confirmed, currently verified recipient may continue while unrelated coverage remains pending; disclose the pending fields.
7. Update only the exact confirmed top-level record, then synchronize relevant current output again. A contact row's nested `recipient_devices` are informational exact-device choices for sending and must never be enrolled as separate top-level inventory records.

RPC and GUI snapshots are not expected to be identical. They expose different surfaces, and the GUI recipient surface may omit the local/self device that appears in RPC state. Reconcile exact names without treating one producer's omission as a rename or deletion. A contact-capable scope describes the full current collection that producer observed, not every contact in an account; nameless contacts fail closed or remain pending.

## Ownership and entry-type values

Ownership values:

- `user_confirmed`: the user explicitly confirmed this exact entry as their own.
- `family_or_shared_confirmed`: the user identified it as family/shared; this is not authorization to send.
- `other_person_confirmed`: the user identified someone else's device or contact; explicit per-send recipient authorization is still required.
- `owner_alias_match_only`: legacy/manual-only evidence of an owner alias, not device/contact-specific confirmation. The current CLI does not create this value; it treats such existing records as unconfirmed and requires a human answer.
- `unconfirmed`: an observed label only; never assume self or third party.

Entry-type values:

- `device`: the human confirmed that the exact name represents a device.
- `contact`: the human confirmed that the exact name represents a contact.
- `unknown`: the kind remains unresolved; omitted legacy values are treated the same way.

Ownership and stored entry type are orthogonal. A user-owned entry is not automatically a device, an other-person entry is not automatically a contact, and an alias never establishes either field. `live_entry_type` is current producer observation only; it is exposed separately and never overwrites the human-confirmed `entry_type`. A mismatch appears in `classification_conflicts`, requires renewed identity/type confirmation, and keeps readiness pending. Entry type is not consumed as standing send permission and does not change the existing ownership confirmation rules. A recipient previously receiving a test proves that specific transfer and receipt, not permanent connectivity or future authorization. `last_confirmed_receipt` is history only. `requires_identity_confirmation` can be false only for explicitly confirmed records; duplicate live names and type conflicts override it in current annotations.

## Confirming identity and kind

Update only an existing exact-name record:

```sh
python3 "$SKILL/scripts/inventory.py" confirm \
  --device EXACT \
  --ownership user|family-shared|other|unknown \
  --label LABEL \
  [--entry-type device|contact|unknown] \
  [--confirmed-by-user]
```

`--entry-type` is optional so existing callers remain compatible. When omitted, the stored kind is preserved. Supplying it requires `--confirmed-by-user`, just like a confirmed ownership change. That flag records a real human answer; it is never evidence of current send consent and must not be self-granted by an agent. New sync records start with `entry_type: "unknown"`, even when the producer supplies a suggestive `live_entry_type` or ownership. A live unknown/missing kind or observed/stored conflict is reported in `unclassified_entries`; conflicts also appear in `classification_conflicts` and demand reconfirmation.

## Labels, aliases, and notes

Each inventory record may contain a string `label`, an array of string `aliases`, and a string `notes`. These fields are private human-readable memory. Alias collisions are allowed because aliases are not identifiers: neither `inventory.py`, `annotate.py`, nor a send path may use them for matching. Live reconciliation and every send continue to require the exact Blip `display_name`; annotations do not alter entry type, ownership, identity-confirmation state, evidence, or authorization.

Update only an existing exact-name record:

```sh
python3 "$SKILL/scripts/inventory.py" note \
  --device EXACT \
  [--label LABEL] \
  [--alias ALIAS]... \
  [--notes TEXT]
```

At least one optional field is required. Supplying one or more `--alias` options replaces the alias array; omitting `--alias` preserves it. The same supplied-only rule applies to `--label` and `--notes`, so an explicitly empty note can clear existing note text. The write is atomic under the shared inventory lock. Unknown exact names are rejected, and the command never creates records.

## CLI output and failure reporting

```sh
python3 "$SKILL/scripts/blip-rpc.py" devices
```

`annotate.py` and inventory synchronization are non-transmitting. Annotated rows expose stored `entry_type`, observed `live_entry_type` when available, `entry_type_conflict`, `label`, `aliases`, and `notes`; none is send authorization. The synchronized structured result retains the historical `devices` name and adds current `discovery_scope`, `contacts_checked`, `unverified_contacts`, `classification_conflicts`, `unclassified_entries`, `ownership_questions`, and `initialization_status`. Nested contact `recipient_devices` remain producer information and are not persisted as inventory entries.

For synchronized discovery, exit `0` means `initialization_status: "ready"`. Exit `2` means the JSON is valid but coverage is pending: ownership questions, duplicate-name ambiguity, live entries with unknown/missing/conflicting kind, no verified current contact check, or known contacts absent from the current collection. Status priority is `awaiting_ownership_confirmation`, then `awaiting_entry_classification`, then `awaiting_contact_check`, then `ready`. Report the specific arrays and status rather than calling it a crashed query, retrying blindly, or suppressing the gap. Exit `1` means input/inventory validation failed.

Reading private annotations alone does not establish connectivity. If the inventory is missing or malformed, fail closed rather than inventing an empty trusted list. Tests may use an explicitly isolated synthetic inventory, but production annotations must never be changed merely to make a check pass.
