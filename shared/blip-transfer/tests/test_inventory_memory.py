import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


INVENTORY = Path(__file__).parents[1] / "scripts" / "inventory.py"
DEVICE = "Synthetic Device"
CONTACT = "Synthetic Contact"
GUI_SCOPE = "visible_devices_and_contacts"
SAME_ACCOUNT_SCOPE = "same_account_devices"
DISCOVERED_SCOPE = "discovered_devices_and_contacts"


class InventoryMemoryCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temporary.name) / "state"

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, *arguments, input_value=None, expected=0):
        completed = subprocess.run(
            [
                sys.executable,
                str(INVENTORY),
                "--state-dir",
                str(self.state_dir),
                *arguments,
            ],
            input=None if input_value is None else json.dumps(input_value),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout={completed.stdout!r}\nstderr={completed.stderr!r}",
        )
        return json.loads(completed.stdout)

    def initialize_with(self, *names):
        self.run_cli("init", "--runtime", "unittest")
        live = {
            "devices": [{"display_name": name} for name in names],
            "discovery_scope": GUI_SCOPE,
        }
        self.run_cli("sync", input_value=live, expected=2)
        return live

    def read_inventory(self):
        return json.loads((self.state_dir / "devices.json").read_text(encoding="utf-8"))

    def read_initialization(self):
        return json.loads(
            (self.state_dir / "initialization.json").read_text(encoding="utf-8")
        )

    def record(self, name=DEVICE):
        return next(
            item for item in self.read_inventory()["devices"]
            if item["display_name"] == name
        )

    def test_reinit_sync_and_confirm_preserve_annotations(self):
        live = self.initialize_with(DEVICE)
        self.run_cli(
            "note",
            "--device",
            DEVICE,
            "--label",
            "Desk phone",
            "--alias",
            "phone",
            "--alias",
            "daily",
            "--notes",
            "Synthetic note",
        )
        self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "user",
            "--label",
            "Confirmed label",
            "--entry-type",
            "device",
            "--confirmed-by-user",
        )

        self.run_cli("init", "--runtime", "second-runtime")
        annotated = self.run_cli("sync", input_value=live)

        record = self.record()
        self.assertEqual(record["label"], "Confirmed label")
        self.assertEqual(record["aliases"], ["phone", "daily"])
        self.assertEqual(record["notes"], "Synthetic note")
        self.assertEqual(record["ownership"], "user_confirmed")
        self.assertEqual(annotated["devices"][0]["aliases"], ["phone", "daily"])
        self.assertEqual(annotated["devices"][0]["notes"], "Synthetic note")
        self.assertFalse(annotated["sending_authorized"])

    def test_partial_snapshot_after_full_discovery_reopens_contact_coverage(self):
        gui_live = self.initialize_with(DEVICE, CONTACT)
        self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "user",
            "--label",
            "Owned device",
            "--entry-type",
            "device",
            "--confirmed-by-user",
        )
        self.run_cli(
            "confirm",
            "--device",
            CONTACT,
            "--ownership",
            "other",
            "--label",
            "Known contact",
            "--entry-type",
            "contact",
            "--confirmed-by-user",
        )

        ready = self.run_cli("sync", input_value=gui_live)
        self.assertEqual(ready["initialization_status"], "ready")
        self.assertEqual(ready["discovery_scope"], GUI_SCOPE)
        self.assertTrue(ready["contacts_checked"])
        self.assertEqual(ready["unverified_contacts"], [])

        rpc = self.run_cli(
            "sync",
            input_value={
                "devices": [{"display_name": DEVICE}],
                "discovery_scope": SAME_ACCOUNT_SCOPE,
            },
            expected=2,
        )
        self.assertEqual(rpc["initialization_status"], "awaiting_contact_check")
        self.assertEqual(rpc["discovery_scope"], SAME_ACCOUNT_SCOPE)
        self.assertEqual(rpc["unclassified_entries"], [])
        self.assertFalse(rpc["contacts_checked"])
        self.assertEqual(rpc["unverified_contacts"], [CONTACT])
        initialization = self.read_initialization()
        self.assertEqual(initialization["status"], "awaiting_contact_check")
        self.assertEqual(initialization["discovery_scope"], SAME_ACCOUNT_SCOPE)
        self.assertFalse(initialization["contacts_checked"])
        self.assertEqual(initialization["unverified_contacts"], [CONTACT])

    def test_discovered_contact_scope_is_current_coverage_without_enrolling_children(self):
        child = "Synthetic Recipient Device"
        live = {
            "devices": [
                {"display_name": DEVICE, "live_entry_type": "device"},
                {
                    "display_name": CONTACT,
                    "live_entry_type": "contact",
                    "recipient_devices": [{
                        "display_name": child,
                        "device_id": "synthetic-device-id",
                        "is_online": True,
                        "is_pushable": True,
                        "live": True,
                        "is_self": False,
                    }],
                },
            ],
            "discovery_scope": DISCOVERED_SCOPE,
        }
        self.run_cli("init", "--runtime", "unittest")
        self.run_cli("sync", input_value=live, expected=2)
        self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "user",
            "--label",
            "Owned device",
            "--entry-type",
            "device",
            "--confirmed-by-user",
        )
        self.run_cli(
            "confirm",
            "--device",
            CONTACT,
            "--ownership",
            "other",
            "--label",
            "Known contact",
            "--entry-type",
            "contact",
            "--confirmed-by-user",
        )

        ready = self.run_cli("sync", input_value=live)

        self.assertEqual(ready["initialization_status"], "ready")
        self.assertEqual(ready["discovery_scope"], DISCOVERED_SCOPE)
        self.assertTrue(ready["contacts_checked"])
        self.assertEqual(ready["classification_conflicts"], [])
        self.assertEqual(
            {row["display_name"]: row["live_entry_type"] for row in ready["devices"]},
            {DEVICE: "device", CONTACT: "contact"},
        )
        inventory_names = [
            record["display_name"] for record in self.read_inventory()["devices"]
        ]
        self.assertEqual(inventory_names, [DEVICE, CONTACT])
        self.assertNotIn(child, inventory_names)

        missing = self.run_cli(
            "sync",
            input_value={
                "devices": [{
                    "display_name": DEVICE,
                    "live_entry_type": "device",
                }],
                "discovery_scope": DISCOVERED_SCOPE,
            },
            expected=2,
        )
        self.assertTrue(missing["contacts_checked"])
        self.assertEqual(missing["unverified_contacts"], [CONTACT])
        self.assertEqual(
            missing["initialization_status"], "awaiting_contact_check"
        )

    def test_observed_type_conflict_requires_reconfirmation_without_changing_kind(self):
        live = {
            "devices": [{
                "display_name": CONTACT,
                "live_entry_type": "contact",
                "recipient_devices": [],
            }],
            "discovery_scope": DISCOVERED_SCOPE,
        }
        self.run_cli("init", "--runtime", "unittest")
        self.run_cli("sync", input_value=live, expected=2)
        self.run_cli(
            "confirm",
            "--device",
            CONTACT,
            "--ownership",
            "other",
            "--label",
            "Known contact",
            "--entry-type",
            "contact",
            "--confirmed-by-user",
        )
        self.run_cli("sync", input_value=live)

        conflict = self.run_cli(
            "sync",
            input_value={
                "devices": [{
                    "display_name": CONTACT,
                    "live_entry_type": "device",
                }],
                "discovery_scope": DISCOVERED_SCOPE,
            },
            expected=2,
        )

        self.assertEqual(
            conflict["initialization_status"], "awaiting_ownership_confirmation"
        )
        self.assertEqual(conflict["classification_conflicts"], [CONTACT])
        self.assertEqual(conflict["unclassified_entries"], [CONTACT])
        self.assertEqual(
            conflict["ownership_questions"][0]["reason"], "entry_type_conflict"
        )
        self.assertTrue(conflict["devices"][0]["entry_type_conflict"])
        self.assertTrue(conflict["devices"][0]["requires_identity_confirmation"])
        self.assertEqual(conflict["devices"][0]["entry_type"], "contact")
        self.assertEqual(conflict["devices"][0]["live_entry_type"], "device")
        record = self.record(CONTACT)
        self.assertEqual(record["entry_type"], "contact")
        self.assertNotIn("live_entry_type", record)
        initialization = self.read_initialization()
        self.assertEqual(initialization["classification_conflicts"], [CONTACT])
        self.assertEqual(initialization["unclassified_entries"], [CONTACT])

        self.run_cli(
            "confirm", "--device", CONTACT, "--ownership", "unknown",
            "--label", "Unconfirmed contact", "--confirmed-by-user",
        )
        unconfirmed_conflict = self.run_cli(
            "sync",
            input_value={
                "devices": [{"display_name": CONTACT, "live_entry_type": "device"}],
                "discovery_scope": DISCOVERED_SCOPE,
            },
            expected=2,
        )
        self.assertEqual(
            unconfirmed_conflict["ownership_questions"][0]["reason"], "entry_type_conflict"
        )
        self.assertEqual(unconfirmed_conflict["classification_conflicts"], [CONTACT])
        self.assertTrue(unconfirmed_conflict["devices"][0]["requires_identity_confirmation"])
        self.assertEqual(self.record(CONTACT)["entry_type"], "contact")

    def test_unknown_and_missing_discovery_scope_fail_closed(self):
        gui_live = self.initialize_with(DEVICE)
        self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "user",
            "--label",
            "Owned device",
            "--entry-type",
            "device",
            "--confirmed-by-user",
        )

        for scope in (None, "future_scope"):
            with self.subTest(scope=scope):
                self.run_cli("sync", input_value=gui_live)
                payload = {"devices": [{"display_name": DEVICE}]}
                if scope is not None:
                    payload["discovery_scope"] = scope
                result = self.run_cli("sync", input_value=payload, expected=2)
                self.assertEqual(result["discovery_scope"], "unverified")
                self.assertEqual(result["unclassified_entries"], [])
                self.assertFalse(result["contacts_checked"])
                self.assertEqual(result["unverified_contacts"], [])
                self.assertEqual(
                    result["initialization_status"], "awaiting_contact_check"
                )
                initialization = self.read_initialization()
                self.assertEqual(initialization["discovery_scope"], "unverified")
                self.assertFalse(initialization["contacts_checked"])
                self.assertEqual(initialization["status"], "awaiting_contact_check")

    def test_full_snapshot_missing_remembered_contact_stays_pending(self):
        gui_live = self.initialize_with(CONTACT)
        self.run_cli(
            "confirm",
            "--device",
            CONTACT,
            "--ownership",
            "other",
            "--label",
            "Known contact",
            "--entry-type",
            "contact",
            "--confirmed-by-user",
        )
        self.run_cli(
            "note", "--device", CONTACT, "--notes", "Synthetic contact note"
        )
        ready = self.run_cli("sync", input_value=gui_live)
        self.assertEqual(ready["initialization_status"], "ready")
        self.assertEqual(ready["devices"][0]["entry_type"], "contact")
        self.assertFalse(ready["sending_authorized"])

        missing = self.run_cli(
            "sync",
            input_value={"devices": [], "discovery_scope": GUI_SCOPE},
            expected=2,
        )
        self.assertTrue(missing["contacts_checked"])
        self.assertEqual(missing["unverified_contacts"], [CONTACT])
        self.assertEqual(missing["unclassified_entries"], [])
        self.assertEqual(
            missing["initialization_status"], "awaiting_contact_check"
        )
        contact = self.record(CONTACT)
        self.assertEqual(contact["entry_type"], "contact")
        self.assertEqual(contact["notes"], "Synthetic contact note")

    def test_confirmation_preserves_entry_type_and_requires_change_consent(self):
        gui_live = self.initialize_with(DEVICE)
        initial = self.run_cli("sync", input_value=gui_live, expected=2)
        self.assertEqual(
            initial["initialization_status"], "awaiting_ownership_confirmation"
        )
        self.assertEqual(initial["unclassified_entries"], [DEVICE])
        self.assertEqual(self.record()["entry_type"], "unknown")
        self.run_cli("note", "--device", DEVICE, "--alias", "person-like alias")
        self.assertEqual(self.record()["entry_type"], "unknown")
        self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "other",
            "--label",
            "Known owner, unknown kind",
            "--confirmed-by-user",
        )
        unclassified = self.run_cli("sync", input_value=gui_live, expected=2)
        self.assertEqual(
            unclassified["initialization_status"], "awaiting_entry_classification"
        )
        self.assertEqual(unclassified["unclassified_entries"], [DEVICE])
        self.assertEqual(
            self.read_initialization()["unclassified_entries"], [DEVICE]
        )
        self.assertEqual(self.record()["ownership"], "other_person_confirmed")
        self.assertEqual(self.record()["entry_type"], "unknown")

        self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "unknown",
            "--label",
            "Rejected contact",
            "--entry-type",
            "contact",
            expected=1,
        )
        self.assertEqual(self.record()["entry_type"], "unknown")
        self.assertEqual(self.record()["label"], "Known owner, unknown kind")
        self.assertEqual(self.record()["ownership"], "other_person_confirmed")

        changed = self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "other",
            "--label",
            "Known contact",
            "--entry-type",
            "contact",
            "--confirmed-by-user",
        )
        self.assertEqual(changed["entry_type"], "contact")
        self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "other",
            "--label",
            "Renamed contact",
            "--confirmed-by-user",
        )
        record = self.record()
        self.assertEqual(record["label"], "Renamed contact")
        self.assertEqual(record["entry_type"], "contact")
        classified = self.run_cli("sync", input_value=gui_live)
        self.assertEqual(classified["unclassified_entries"], [])
        self.assertEqual(classified["initialization_status"], "ready")


    def test_note_updates_only_supplied_fields(self):
        self.initialize_with(DEVICE)
        self.run_cli(
            "note",
            "--device",
            DEVICE,
            "--label",
            "Original label",
            "--alias",
            "old one",
            "--alias",
            "old two",
            "--notes",
            "Original notes",
        )

        label_result = self.run_cli(
            "note", "--device", DEVICE, "--label", "Updated label"
        )
        self.assertEqual(label_result["aliases"], ["old one", "old two"])
        self.assertEqual(label_result["notes"], "Original notes")

        aliases_result = self.run_cli(
            "note",
            "--device",
            DEVICE,
            "--alias",
            "replacement one",
            "--alias",
            "replacement two",
        )
        self.assertEqual(aliases_result["label"], "Updated label")
        self.assertEqual(
            aliases_result["aliases"], ["replacement one", "replacement two"]
        )
        self.assertEqual(aliases_result["notes"], "Original notes")

        notes_result = self.run_cli(
            "note", "--device", DEVICE, "--notes", ""
        )
        self.assertEqual(notes_result["label"], "Updated label")
        self.assertEqual(
            notes_result["aliases"], ["replacement one", "replacement two"]
        )
        self.assertEqual(notes_result["notes"], "")

    def test_notes_do_not_change_ownership_evidence_or_authorization(self):
        self.initialize_with(DEVICE)
        self.run_cli(
            "confirm",
            "--device",
            DEVICE,
            "--ownership",
            "family-shared",
            "--label",
            "Shared device",
            "--confirmed-by-user",
        )
        before = self.record()

        result = self.run_cli(
            "note", "--device", DEVICE, "--notes", "Remember this detail"
        )
        after = self.record()

        for field in (
            "ownership",
            "requires_identity_confirmation",
            "standing_send_authorization",
            "evidence_type",
            "evidence_date",
        ):
            self.assertEqual(after[field], before[field])
        self.assertEqual(result["ownership"], "family_or_shared_confirmed")
        self.assertFalse(result["standing_send_authorization"])
        self.assertFalse(result["sending_authorized"])

    def test_alias_collisions_are_allowed_but_never_match_a_device(self):
        other = "Other Synthetic Device"
        self.initialize_with(DEVICE, other)
        for name in (DEVICE, other):
            self.run_cli(
                "note", "--device", name, "--alias", "shared friendly name"
            )

        rejected = self.run_cli(
            "note",
            "--device",
            "shared friendly name",
            "--notes",
            "must not resolve through alias",
            expected=1,
        )
        self.assertFalse(rejected["sending_authorized"])
        self.assertEqual(self.record(DEVICE)["aliases"], ["shared friendly name"])
        self.assertEqual(self.record(other)["aliases"], ["shared friendly name"])

    def test_unknown_exact_name_and_empty_update_are_rejected(self):
        self.initialize_with(DEVICE)
        before = self.read_inventory()
        self.run_cli(
            "note", "--device", "Missing Device", "--notes", "x", expected=1
        )
        self.run_cli("note", "--device", DEVICE, expected=1)
        self.assertEqual(self.read_inventory(), before)

    def test_old_schema_one_record_without_memory_fields_remains_valid(self):
        self.run_cli("init")
        legacy = {
            "schema_version": 1,
            "devices": [{
                "display_name": DEVICE,
                "ownership": "user_confirmed",
                "requires_identity_confirmation": False,
                "standing_send_authorization": False,
                "evidence_type": "user_confirmation",
                "evidence_date": "2026-01-01",
                "legacy_field": "preserve me",
            }],
            "policy": {
                "new_devices_require_identity_confirmation": True,
                "standing_send_authorization": False,
            },
        }
        (self.state_dir / "devices.json").write_text(
            json.dumps(legacy), encoding="utf-8"
        )

        self.run_cli("init", "--runtime", "later-runtime")
        annotated = self.run_cli(
            "sync", input_value={"devices": [{"display_name": DEVICE}]}, expected=2
        )

        record = self.record()
        self.assertEqual(record["legacy_field"], "preserve me")
        self.assertNotIn("label", record)
        self.assertNotIn("aliases", record)
        self.assertNotIn("notes", record)
        self.assertEqual(annotated["devices"][0]["label"], DEVICE)
        self.assertEqual(annotated["devices"][0]["aliases"], [])
        self.assertEqual(annotated["devices"][0]["notes"], "")
        self.assertEqual(annotated["devices"][0]["entry_type"], "unknown")
        self.assertEqual(
            annotated["initialization_status"], "awaiting_entry_classification"
        )
        self.assertEqual(annotated["unclassified_entries"], [DEVICE])

    def test_malformed_optional_metadata_is_rejected(self):
        self.run_cli("init")
        base_record = {
            "display_name": DEVICE,
            "ownership": "unconfirmed",
            "requires_identity_confirmation": True,
            "standing_send_authorization": False,
        }
        malformed = {
            "label": ["not", "a", "string"],
            "aliases": "not an array",
            "alias element": ["valid", 7],
            "notes": {"not": "a string"},
            "entry_type": "person",
        }
        for field, value in malformed.items():
            with self.subTest(field=field):
                record = dict(base_record)
                record["aliases" if field == "alias element" else field] = value
                inventory = {
                    "schema_version": 1,
                    "devices": [record],
                    "policy": {
                        "new_devices_require_identity_confirmation": True,
                        "standing_send_authorization": False,
                    },
                }
                (self.state_dir / "devices.json").write_text(
                    json.dumps(inventory), encoding="utf-8"
                )
                rejected = self.run_cli("init", expected=1)
                self.assertFalse(rejected["sending_authorized"])


if __name__ == "__main__":
    unittest.main()

