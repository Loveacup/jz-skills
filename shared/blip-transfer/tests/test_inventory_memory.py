import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


INVENTORY = Path(__file__).parents[1] / "scripts" / "inventory.py"
DEVICE = "Synthetic Device"


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
        live = {"devices": [{"display_name": name} for name in names]}
        self.run_cli("sync", input_value=live, expected=2)
        return live

    def read_inventory(self):
        return json.loads((self.state_dir / "devices.json").read_text(encoding="utf-8"))

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
        self.assertIn("exactly match", rejected["error"])
        self.assertFalse(rejected["sending_authorized"])
        self.assertEqual(self.record(DEVICE)["aliases"], ["shared friendly name"])
        self.assertEqual(self.record(other)["aliases"], ["shared friendly name"])

    def test_unknown_exact_name_and_empty_update_are_rejected(self):
        self.initialize_with(DEVICE)
        unknown = self.run_cli(
            "note", "--device", "Missing Device", "--notes", "x", expected=1
        )
        self.assertIn("exactly match", unknown["error"])
        empty = self.run_cli("note", "--device", DEVICE, expected=1)
        self.assertIn("at least one", empty["error"])

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
            "sync", input_value={"devices": [{"display_name": DEVICE}]}
        )

        record = self.record()
        self.assertEqual(record["legacy_field"], "preserve me")
        self.assertNotIn("label", record)
        self.assertNotIn("aliases", record)
        self.assertNotIn("notes", record)
        self.assertEqual(annotated["devices"][0]["label"], DEVICE)
        self.assertEqual(annotated["devices"][0]["aliases"], [])
        self.assertEqual(annotated["devices"][0]["notes"], "")

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
                self.assertIn("inventory device", rejected["error"])
                self.assertFalse(rejected["sending_authorized"])


if __name__ == "__main__":
    unittest.main()
