#!/usr/bin/env python3
"""No-send behavioral regression tests for the local Blip RPC client."""

from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, os.fspath(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("blip_rpc", SCRIPTS / "blip-rpc.py")
blip_rpc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(blip_rpc)

TRANSFER_ID = "00000000-0000-4000-8000-000000000001"
PEER = {"user_id": "user-1", "device_id": "device-1"}


def _varint(value):
    encoded = bytearray()
    while value > 0x7f:
        encoded.append((value & 0x7f) | 0x80)
        value >>= 7
    encoded.append(value)
    return bytes(encoded)


def _field(number, value):
    return _varint((number << 3) | 2) + _varint(len(value)) + value


def _integer(number, value):
    return _varint(number << 3) + _varint(value)


def _device(name="Owned Phone", *, peer=PEER, live=True, is_self=False):
    return {
        "display_name": name,
        "user_id": peer["user_id"],
        "device_id": peer["device_id"],
        "is_online": live,
        "is_pushable": False,
        "live": live,
        "is_self": is_self,
        "is_contact": False,
        "live_entry_type": "device",
    }


def _contact(name="Other Person", device_name="Other Phone", *, peer=PEER,
             live=True, device_is_self=False):
    return {
        "display_name": name,
        "user_id": peer["user_id"],
        "is_contact": True,
        "is_self": False,
        "live_entry_type": "contact",
        "recipient_devices": [{
            "display_name": device_name,
            "device_id": peer["device_id"],
            "is_online": live,
            "is_pushable": False,
            "live": live,
            "is_self": device_is_self,
        }],
    }


def _transfer(*, peer=PEER, files=None, content_job_count=0,
              archive_present=True, status_code=1, direction=2,
              has_local_error=False, has_remote_error=False):
    return {
        "transfer_id": TRANSFER_ID,
        "peer": dict(peer),
        "content_job_count": content_job_count,
        "archive_present": archive_present,
        "files": list(files or []),
        "has_local_error": has_local_error,
        "has_remote_error": has_remote_error,
        "direction": direction,
        "status_code": status_code,
    }


def _source(name="report.txt", size=7):
    return {
        "path": f"/temporary-fixture/{name}",
        "basename": name,
        "size": size,
        "identity": (1, 2, size, 3, 4),
    }


class AsyncPublicationTests(unittest.TestCase):
    def test_create_ack_is_not_treated_as_visible_state(self):
        snapshots = [
            {"devices": [], "transfer": None},
            {"devices": [], "transfer": _transfer()},
        ]
        with mock.patch.object(blip_rpc, "_state_snapshot", side_effect=snapshots) as state:
            with mock.patch.object(blip_rpc.time, "monotonic", return_value=0):
                with mock.patch.object(blip_rpc.time, "sleep") as sleep:
                    observed = blip_rpc._wait_until_created(TRANSFER_ID, PEER)

        self.assertEqual(observed["transfer_id"], TRANSFER_ID)
        self.assertEqual(state.call_count, 2)
        sleep.assert_called_once()

    def test_content_ack_is_not_treated_as_published_archive(self):
        source = _source()
        pending = _transfer(content_job_count=1, archive_present=False)
        prepared = _transfer(files=[{"name": source["basename"], "kind": "file",
                                     "size": source["size"]}])
        snapshots = [
            {"devices": [], "transfer": pending},
            {"devices": [], "transfer": prepared},
        ]
        with mock.patch.object(blip_rpc, "_state_snapshot", side_effect=snapshots) as state:
            with mock.patch.object(blip_rpc.time, "monotonic", return_value=0):
                with mock.patch.object(blip_rpc.time, "sleep") as sleep:
                    observed = blip_rpc._wait_until_prepared(TRANSFER_ID, PEER, [source])

        self.assertIs(observed, prepared)
        self.assertEqual(state.call_count, 2)
        sleep.assert_called_once()


class InvitationGateTests(unittest.TestCase):
    def _run_with_final_transfer(self, final_transfer):
        source = _source()
        initial = {"devices": [_device()], "transfer": None}
        final = {"devices": [_device()], "transfer": final_transfer}
        args = SimpleNamespace(recipient="Owned Phone")
        with ExitStack() as stack:
            state = stack.enter_context(
                mock.patch.object(blip_rpc, "_state_snapshot", side_effect=[initial, final]))
            dispatch = stack.enter_context(mock.patch.object(blip_rpc, "_dispatch_event"))
            stack.enter_context(mock.patch.object(blip_rpc, "_wait_until_created"))
            stack.enter_context(mock.patch.object(blip_rpc, "_wait_until_prepared"))
            revalidate = stack.enter_context(mock.patch.object(blip_rpc, "_revalidate_sources"))
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._run_send_locked(args, TRANSFER_ID, [source])
        event_names = [call.args[0] for call in dispatch.call_args_list]
        self.assertEqual(event_names, ["TransferCreateRequested", "TransferAddContentRequested"])
        revalidate.assert_not_called()
        self.assertEqual(state.call_count, 2)
        return raised.exception

    def test_invitation_requires_exact_published_names_sizes_and_peer(self):
        source = _source()
        cases = {
            "wrong archive name": _transfer(
                files=[{"name": "other.txt", "kind": "file", "size": source["size"]}]),
            "wrong archive size": _transfer(
                files=[{"name": source["basename"], "kind": "file", "size": 999}]),
            "wrong peer": _transfer(
                peer={"user_id": "user-2", "device_id": "device-2"},
                files=[{"name": source["basename"], "kind": "file", "size": source["size"]}]),
        }
        for label, transfer in cases.items():
            with self.subTest(label=label):
                error = self._run_with_final_transfer(transfer)
                self.assertIn(error.code, {"prepared_content_changed", "transfer_peer_changed"})

    def test_duplicate_archive_name_is_rejected_before_invitation(self):
        source = _source()
        item = {"name": source["basename"], "kind": "file", "size": source["size"]}
        error = self._run_with_final_transfer(_transfer(files=[item, dict(item)]))
        self.assertEqual(error.code, "prepared_content_mismatch")

    def test_exact_published_archive_and_peer_are_invited_once(self):
        source = _source()
        prepared = _transfer(
            files=[{"name": source["basename"], "kind": "file", "size": source["size"]}])
        after_invite = _transfer(
            files=prepared["files"], status_code=2)
        snapshots = [
            {"devices": [_device()], "transfer": None},
            {"devices": [_device()], "transfer": prepared},
            {"devices": [], "transfer": after_invite},
        ]
        args = SimpleNamespace(recipient="Owned Phone")
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(blip_rpc, "_state_snapshot", side_effect=snapshots))
            dispatch = stack.enter_context(mock.patch.object(blip_rpc, "_dispatch_event"))
            stack.enter_context(mock.patch.object(blip_rpc, "_wait_until_created"))
            stack.enter_context(mock.patch.object(blip_rpc, "_wait_until_prepared"))
            revalidate = stack.enter_context(mock.patch.object(blip_rpc, "_revalidate_sources"))
            result, exit_status = blip_rpc._run_send_locked(args, TRANSFER_ID, [source])

        self.assertEqual(
            [call.args[0] for call in dispatch.call_args_list],
            ["TransferCreateRequested", "TransferAddContentRequested",
             "TransferInviteRequested"],
        )
        revalidate.assert_called_once_with([source])
        self.assertEqual(result["transfer_id"], TRANSFER_ID)
        self.assertTrue(result["invite_requested"])
        self.assertEqual(exit_status, blip_rpc.PENDING_EXIT)

    def test_contact_send_result_names_contact_and_selected_child_without_ids(self):
        source = _source()
        peer = {"user_id": "contact-account", "device_id": "contact-phone"}
        prepared = _transfer(
            peer=peer,
            files=[{"name": source["basename"], "kind": "file",
                    "size": source["size"]}])
        after_invite = _transfer(peer=peer, files=prepared["files"], status_code=2)
        contact = _contact(peer=peer)
        snapshots = [
            {"devices": [contact], "transfer": None},
            {"devices": [contact], "transfer": prepared},
            {"devices": [], "transfer": after_invite},
        ]
        args = SimpleNamespace(
            recipient="Other Person",
            recipient_device="Other Phone",
        )
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                blip_rpc, "_state_snapshot", side_effect=snapshots))
            dispatch = stack.enter_context(
                mock.patch.object(blip_rpc, "_dispatch_event"))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_wait_until_created"))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_wait_until_prepared"))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_revalidate_sources"))
            result, exit_status = blip_rpc._run_send_locked(
                args, TRANSFER_ID, [source])

        self.assertEqual(
            [call.args[0] for call in dispatch.call_args_list],
            ["TransferCreateRequested", "TransferAddContentRequested",
             "TransferInviteRequested"],
        )
        self.assertEqual(result["recipient"], "Other Person")
        self.assertEqual(result["recipient_device"], "Other Phone")
        self.assertNotIn("user_id", result)
        self.assertNotIn("device_id", result)
        self.assertEqual(exit_status, blip_rpc.PENDING_EXIT)


class MutationFailureTests(unittest.TestCase):
    def test_post_create_local_error_does_not_retry_and_retains_transfer_id(self):
        initial = {"devices": [_device()], "transfer": None}
        args = SimpleNamespace(recipient="Owned Phone")

        def dispatch(event_name, _payload):
            if event_name == "TransferAddContentRequested":
                raise ValueError("local encoding failure")

        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(blip_rpc, "_state_snapshot", return_value=initial))
            mutation = stack.enter_context(
                mock.patch.object(blip_rpc, "_dispatch_event", side_effect=dispatch))
            stack.enter_context(mock.patch.object(blip_rpc, "_wait_until_created"))
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._run_send_locked(args, TRANSFER_ID, [_source()])

        self.assertEqual(
            [call.args[0] for call in mutation.call_args_list],
            ["TransferCreateRequested", "TransferAddContentRequested"],
        )
        self.assertEqual(raised.exception.code, "unexpected_local_error")
        self.assertEqual(raised.exception.details["transfer_id"], TRANSFER_ID)
        self.assertEqual(raised.exception.details["last_mutation"], "content_requested")
        self.assertTrue(raised.exception.details["mutation_outcome_unknown"])
        self.assertTrue(raised.exception.details["inspect_with_status"])

    def test_create_observation_error_does_not_repeat_create(self):
        initial = {"devices": [_device()], "transfer": None}
        args = SimpleNamespace(recipient="Owned Phone")
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(blip_rpc, "_state_snapshot", return_value=initial))
            mutation = stack.enter_context(mock.patch.object(blip_rpc, "_dispatch_event"))
            stack.enter_context(mock.patch.object(
                blip_rpc, "_wait_until_created", side_effect=OSError("local state read failed")))
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._run_send_locked(args, TRANSFER_ID, [_source()])

        self.assertEqual(mutation.call_count, 1)
        self.assertEqual(mutation.call_args.args[0], "TransferCreateRequested")
        self.assertEqual(raised.exception.details["transfer_id"], TRANSFER_ID)
        self.assertEqual(raised.exception.details["last_mutation"], "create_requested")


class RecipientAndSourceTests(unittest.TestCase):
    def test_recipient_and_confirmation_must_match_exactly(self):
        args = SimpleNamespace(
            transfer_id=TRANSFER_ID,
            recipient="Owned Phone",
            confirm_recipient="owned phone",
            files=[],
        )
        with mock.patch.object(blip_rpc, "_require_pinned_build"):
            with mock.patch.object(blip_rpc, "_exclusive_send_lock") as lock:
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc.run_send(args)
        self.assertEqual(raised.exception.code, "recipient_confirmation_mismatch")
        lock.assert_not_called()

    def test_incorrect_live_target_name_is_rejected(self):
        with self.assertRaises(blip_rpc.BlipError) as raised:
            blip_rpc._select_recipient([_device()], "Different Phone")
        self.assertEqual(raised.exception.code, "recipient_not_unique")

    def test_local_unreachable_or_incomplete_peers_are_rejected_in_both_modes(self):
        cases = (
            ("local", _device(is_self=True), _contact(device_is_self=True),
             "recipient_is_self"),
            ("unreachable", _device(live=False), _contact(live=False),
             "recipient_not_reachable"),
            ("missing account", _device(peer={"user_id": "", "device_id": "phone"}),
             _contact(peer={"user_id": "", "device_id": "phone"}), "recipient_invalid"),
            ("missing device", _device(peer={"user_id": "account", "device_id": ""}),
             _contact(peer={"user_id": "account", "device_id": ""}), "recipient_invalid"),
        )
        for label, owned, contact, code in cases:
            with self.subTest(case=label, mode="owned"):
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc._select_recipient([owned], "Owned Phone")
                self.assertEqual(raised.exception.code, code)
            with self.subTest(case=label, mode="contact"):
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc._select_contact_recipient([contact], "Other Person", "Other Phone")
                self.assertEqual(raised.exception.code, code)

    def test_unconfirmed_inventory_target_is_rejected(self):
        inventory = {
            "devices": [{
                "display_name": "Owned Phone",
                "ownership": "unknown",
                "requires_identity_confirmation": True,
            }]
        }
        with mock.patch.object(blip_rpc, "_load_inventory", return_value=inventory):
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._confirmed_inventory_recipient("Owned Phone")
        self.assertEqual(raised.exception.code, "recipient_not_confirmed")

    def test_duplicate_live_target_name_is_rejected(self):
        devices = [_device(), _device(peer={"user_id": "user-2", "device_id": "device-2"})]
        with self.assertRaises(blip_rpc.BlipError) as raised:
            blip_rpc._select_recipient(devices, "Owned Phone")
        self.assertEqual(raised.exception.code, "recipient_not_unique")

    def test_device_contact_name_collision_cannot_bypass_ambiguity(self):
        entries = [_device("Same Name"), _contact("Same Name", "Other Phone")]
        with self.assertRaises(blip_rpc.BlipError) as own_error:
            blip_rpc._select_recipient(entries, "Same Name")
        self.assertEqual(own_error.exception.code, "recipient_not_unique")
        with self.assertRaises(blip_rpc.BlipError) as contact_error:
            blip_rpc._select_contact_recipient(entries, "Same Name", "Other Phone")
        self.assertEqual(contact_error.exception.code, "recipient_not_unique")

    def test_duplicate_inventory_target_is_rejected(self):
        record = {
            "display_name": "Owned Phone",
            "ownership": "user_confirmed",
            "requires_identity_confirmation": False,
        }
        with mock.patch.object(
                blip_rpc, "_load_inventory", return_value={"devices": [record, dict(record)]}):
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._confirmed_inventory_recipient("Owned Phone")
        self.assertEqual(raised.exception.code, "recipient_not_confirmed")

    def test_contact_resolution_uses_exact_account_and_child_device_names(self):
        entries = [
            _contact("Other Person", "Tablet",
                     peer={"user_id": "account-a", "device_id": "tablet-a"}),
            _contact("Another Person", "Phone",
                     peer={"user_id": "account-b", "device_id": "phone-b"}),
        ]

        selected = blip_rpc._select_contact_recipient(
            entries, "Other Person", "Tablet")

        self.assertEqual(
            selected, {"user_id": "account-a", "device_id": "tablet-a"})

    def test_contact_or_child_name_ambiguity_is_rejected(self):
        duplicate_contacts = [
            _contact(peer={"user_id": "account-a", "device_id": "device-a"}),
            _contact(peer={"user_id": "account-b", "device_id": "device-b"}),
        ]
        duplicate_children = _contact()
        duplicate_children["recipient_devices"].append({
            **duplicate_children["recipient_devices"][0],
            "device_id": "device-2",
        })
        cases = (
            (duplicate_contacts, "recipient_not_unique"),
            ([duplicate_children], "recipient_device_not_unique"),
        )
        for entries, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc._select_contact_recipient(
                        entries, "Other Person", "Other Phone")
                self.assertEqual(raised.exception.code, expected_code)

    def test_contact_send_requires_confirmed_contact_kind_and_other_person(self):
        base = {
            "display_name": "Other Person",
            "entry_type": "contact",
            "ownership": "other_person_confirmed",
            "requires_identity_confirmation": False,
        }
        cases = (
            {**base, "entry_type": "device"},
            {**base, "ownership": "user_confirmed"},
            {**base, "requires_identity_confirmation": True},
        )
        for record in cases:
            with self.subTest(record=record):
                with mock.patch.object(
                        blip_rpc, "_load_inventory",
                        return_value={"devices": [record]}):
                    with self.assertRaises(blip_rpc.BlipError) as raised:
                        blip_rpc._confirmed_inventory_recipient(
                            "Other Person",
                            entry_type="contact",
                            ownership="other_person_confirmed",
                        )
                self.assertEqual(raised.exception.code, "recipient_not_confirmed")

    def test_stored_kind_conflict_stops_before_source_validation_or_mutation(self):
        args = SimpleNamespace(
            transfer_id=TRANSFER_ID,
            recipient="Other Person",
            confirm_recipient="Other Person",
            recipient_device="Other Phone",
            confirm_recipient_device="Other Phone",
            files=["/not-inspected"],
        )
        stored_device = {
            "display_name": "Other Person",
            "entry_type": "device",
            "ownership": "other_person_confirmed",
            "requires_identity_confirmation": False,
        }
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(blip_rpc, "_require_pinned_build"))
            stack.enter_context(mock.patch.object(
                blip_rpc, "_load_inventory",
                return_value={"devices": [stored_device]}))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_exclusive_send_lock"))
            validate = stack.enter_context(
                mock.patch.object(blip_rpc, "_validate_sources"))
            send = stack.enter_context(
                mock.patch.object(blip_rpc, "_run_send_locked"))
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc.run_send(args)

        self.assertEqual(raised.exception.code, "recipient_not_confirmed")
        validate.assert_not_called()
        send.assert_not_called()

    def test_contact_device_flags_must_be_present_and_confirmed_as_a_pair(self):
        args = SimpleNamespace(
            transfer_id=TRANSFER_ID,
            recipient="Other Person",
            confirm_recipient="Other Person",
            recipient_device="Other Phone",
            confirm_recipient_device=None,
            files=[],
        )
        with mock.patch.object(blip_rpc, "_require_pinned_build"):
            with mock.patch.object(blip_rpc, "_exclusive_send_lock") as lock:
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc.run_send(args)
        self.assertEqual(
            raised.exception.code, "recipient_device_confirmation_mismatch")
        lock.assert_not_called()

    def test_contact_identity_drift_stops_before_invitation(self):
        source = _source()
        prepared = _transfer(
            files=[{"name": source["basename"], "kind": "file",
                    "size": source["size"]}])
        initial = {"devices": [
            _contact(peer={"user_id": "account-a", "device_id": "device-a"})
        ], "transfer": None}
        final = {"devices": [
            _contact(peer={"user_id": "account-b", "device_id": "device-b"})
        ], "transfer": prepared}
        args = SimpleNamespace(
            recipient="Other Person",
            recipient_device="Other Phone",
        )
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                blip_rpc, "_state_snapshot", side_effect=[initial, final]))
            dispatch = stack.enter_context(
                mock.patch.object(blip_rpc, "_dispatch_event"))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_wait_until_created"))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_wait_until_prepared"))
            revalidate = stack.enter_context(
                mock.patch.object(blip_rpc, "_revalidate_sources"))
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._run_send_locked(args, TRANSFER_ID, [source])

        self.assertEqual(raised.exception.code, "recipient_identity_changed")
        self.assertEqual(
            [call.args[0] for call in dispatch.call_args_list],
            ["TransferCreateRequested", "TransferAddContentRequested"],
        )
        revalidate.assert_not_called()

    def test_source_identity_change_is_rejected_before_invitation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.txt"
            source.write_bytes(b"original")
            snapshot = blip_rpc._source_snapshot(os.fspath(source))
            replacement = Path(directory) / "replacement.txt"
            replacement.write_bytes(b"replaced")
            prepared = _transfer(files=[{
                "name": source.name, "kind": "file", "size": snapshot["size"],
            }])
            states = [
                {"devices": [_device()], "transfer": None},
                {"devices": [_device()], "transfer": prepared},
            ]
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(
                    blip_rpc, "_state_snapshot", side_effect=states))
                dispatch = stack.enter_context(mock.patch.object(blip_rpc, "_dispatch_event"))
                stack.enter_context(mock.patch.object(blip_rpc, "_wait_until_created"))
                stack.enter_context(mock.patch.object(
                    blip_rpc, "_wait_until_prepared",
                    side_effect=lambda *_: os.replace(replacement, source)))
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc._run_send_locked(
                        SimpleNamespace(recipient="Owned Phone"), TRANSFER_ID, [snapshot])

        self.assertEqual(raised.exception.code, "source_changed")
        self.assertEqual(raised.exception.details["source"], os.fspath(source))
        self.assertEqual(
            [call.args[0] for call in dispatch.call_args_list],
            ["TransferCreateRequested", "TransferAddContentRequested"],
        )


class DeviceDiscoveryTests(unittest.TestCase):
    def test_devices_output_nests_contact_children_and_redacts_account_ids(self):
        inventory = {
            "schema_version": 1,
            "devices": [
                {
                    "display_name": "Owned Phone",
                    "entry_type": "device",
                    "ownership": "user_confirmed",
                    "requires_identity_confirmation": False,
                    "standing_send_authorization": False,
                },
                {
                    "display_name": "Other Person",
                    "entry_type": "contact",
                    "ownership": "other_person_confirmed",
                    "requires_identity_confirmation": False,
                    "standing_send_authorization": False,
                },
            ],
        }
        entries = [
            _device(peer={"user_id": "own-account", "device_id": "owned-device"}),
            _contact(peer={"user_id": "contact-account",
                           "device_id": "contact-device"}),
        ]
        with mock.patch.object(
                blip_rpc, "_load_inventory", return_value=inventory):
            result = blip_rpc._annotated_devices(entries)

        self.assertEqual(
            result["discovery_scope"], "discovered_devices_and_contacts")
        own, contact = result["devices"]
        self.assertEqual(own["live_entry_type"], "device")
        self.assertNotIn("user_id", own)
        self.assertEqual(contact["live_entry_type"], "contact")
        self.assertNotIn("user_id", contact)
        self.assertEqual(contact["recipient_devices"], [{
            "display_name": "Other Phone",
            "device_id": "contact-device",
            "is_online": True,
            "is_pushable": False,
            "live": True,
            "is_self": False,
        }])


class TransportAndRedactionTests(unittest.TestCase):
    def test_socket_reads_share_one_total_deadline(self):
        reader, writer = socket.socketpair()
        try:
            writer.sendall(blip_rpc._frame(2, 1, b"x"))
            client = blip_rpc._DeadlineSocket(reader, deadline=1.0)
            with mock.patch.object(
                    blip_rpc.time, "monotonic",
                    side_effect=[0.0, 0.2, 0.4, 0.6, 1.1]):
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc._receive_message(client)
        finally:
            reader.close()
            writer.close()
        self.assertEqual(raised.exception.code, "rpc_timeout")

    def test_decoder_skips_opaque_auth_and_email_fields(self):
        reach = _integer(1, 1)
        device = b"".join((
            _field(1, b"device-1"),
            _field(2, b"\xffopaque-device-auth"),
            _field(3, b"Owned Phone"),
            _field(4, reach),
            _integer(6, 0),
        ))
        device_entry = _field(1, b"device-1") + _field(2, device)
        user = b"".join((
            _field(1, b"\xffopaque-user-auth"),
            _field(7, device_entry),
            _field(8, b"user-1"),
            _integer(10, 1),
        ))
        discovered = _field(2, user)
        users = _field(1, discovered)
        state = _field(17, b"\xffopaque-state-auth") + _field(500, users)

        decoded = blip_rpc._decode_state(state)

        self.assertEqual(decoded["devices"], [_device()])
        self.assertIsNone(decoded["transfer"])

    def test_decoder_discovers_contact_devices_without_reading_contact_map_keys(self):
        reach = _integer(1, 1)
        device = b"".join((
            _field(1, b"contact-device"),
            _field(3, b"Other Phone"),
            _field(4, reach),
            _integer(6, 0),
        ))
        device_entry = _field(1, b"contact-device") + _field(2, device)
        user = b"".join((
            _field(1, b"\xffopaque-private-email"),
            _field(2, b"Other Person"),
            _field(7, device_entry),
            _field(8, b"contact-account"),
            _integer(9, 1),
            _integer(10, 0),
        ))
        discovered = _field(1, b"\xffopaque-discovered-map-key") + _field(2, user)
        opaque_contact_map = _field(1, b"\xffopaque-contact-map-key") + _integer(2, 1)
        state = _field(
            500, _field(1, discovered) + _field(3, opaque_contact_map))

        decoded = blip_rpc._decode_state(state)

        self.assertEqual(decoded["devices"], [
            _contact(
                peer={"user_id": "contact-account",
                      "device_id": "contact-device"})
        ])

    def test_decoder_rejects_incomplete_or_duplicate_contact_records(self):
        incomplete = b"".join((
            _field(8, b"contact-account"),
            _integer(9, 1),
        ))
        complete = b"".join((
            _field(2, b"Other Person"),
            _field(8, b"contact-account"),
            _integer(9, 1),
        ))
        states = (
            _field(500, _field(1, _field(2, incomplete))),
            _field(500, b"".join((
                _field(1, _field(2, complete)),
                _field(1, _field(2, complete)),
            ))),
        )
        for state in states:
            with self.subTest(state=state):
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc._decode_state(state)
                self.assertEqual(raised.exception.code, "invalid_contact_state")

    def test_state_response_is_zeroed_with_a_held_child_memoryview(self):
        response = bytearray(_field(2, b"secret-state"))
        held = None
        try:
            with mock.patch.object(blip_rpc, "_rpc", return_value=response):
                held = blip_rpc._with_state(lambda state: state[1:7])
            self.assertEqual(response, bytearray(len(response)))
            self.assertEqual(bytes(held), b"\x00" * len(held))
        finally:
            if held is not None:
                held.release()


if __name__ == "__main__":
    unittest.main()
