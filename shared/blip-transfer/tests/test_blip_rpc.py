#!/usr/bin/env python3
"""No-send behavioral regression tests for the local Blip RPC client."""

from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import socket
import sys
import stat
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
ACCOUNT_PEER = {"user_id": "account-1", "device_id": ""}


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


class UpgradeSafetyTests(unittest.TestCase):
    def test_build_guard_accepts_only_exact_candidate_version_and_build(self):
        with mock.patch.object(
                blip_rpc, "_installed_build",
                return_value=(blip_rpc.EXPECTED_VERSION, blip_rpc.EXPECTED_BUILD)):
            self.assertEqual(
                blip_rpc._require_pinned_build(),
                (blip_rpc.EXPECTED_VERSION, blip_rpc.EXPECTED_BUILD),
            )
        for installed in (
                ("1.1.16", blip_rpc.EXPECTED_BUILD),
                (blip_rpc.EXPECTED_VERSION, "20260425132215")):
            with self.subTest(installed=installed):
                with mock.patch.object(
                        blip_rpc, "_installed_build", return_value=installed):
                    with self.assertRaises(blip_rpc.BlipError) as raised:
                        blip_rpc._require_pinned_build()
                self.assertEqual(
                    raised.exception.code, "unsupported_blip_build")

    def test_socket_path_rejects_non_socket_and_wrong_owner(self):
        cases = (
            (SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=os.getuid()),
             "invalid_socket"),
            (SimpleNamespace(st_mode=stat.S_IFSOCK | 0o600, st_uid=os.getuid() + 1),
             "invalid_socket_owner"),
        )
        for metadata, code in cases:
            with self.subTest(code=code):
                with mock.patch.object(os, "stat", return_value=metadata):
                    with self.assertRaises(blip_rpc.BlipError) as raised:
                        blip_rpc._validated_socket_stat()
                self.assertEqual(raised.exception.code, code)

    def test_sources_reject_missing_directory_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / "regular.txt"
            regular.write_text("fixture", encoding="utf-8")
            symlink = root / "link.txt"
            symlink.symlink_to(regular)
            for source in (root / "missing.txt", root, symlink):
                with self.subTest(source=source.name):
                    with self.assertRaises(blip_rpc.BlipError) as raised:
                        blip_rpc._validate_sources([os.fspath(source)])
                    self.assertEqual(raised.exception.code, "invalid_source")

    def test_response_rejects_oversized_and_malformed_frames(self):
        oversized = b"".join((
            _varint((2 << 1) | 1), _varint(1), _varint(1),
            _varint(blip_rpc.MAX_RESPONSE + 1),
        ))
        for payload, code in (
                (oversized, "rpc_response_too_large"),
                (b"\xff" * 10, "invalid_rpc_frame")):
            reader, writer = socket.socketpair()
            try:
                writer.sendall(payload)
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc._receive_message(reader)
                self.assertEqual(raised.exception.code, code)
            finally:
                reader.close()
                writer.close()

    def test_response_rejects_more_than_bounded_frame_count(self):
        frame = b"".join((
            _varint(2 << 1), _varint(1), _varint(1), _varint(0),
        ))
        reader, writer = socket.socketpair()
        try:
            writer.sendall(frame * blip_rpc.MAX_FRAMES)
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._receive_message(reader)
            self.assertEqual(
                raised.exception.code, "rpc_response_too_many_frames")
        finally:
            reader.close()
            writer.close()


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
            "wrong device on same account": _transfer(
                peer={"user_id": PEER["user_id"], "device_id": "device-2"},
                files=[{"name": source["basename"], "kind": "file",
                        "size": source["size"]}]),
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
        self.assertEqual(result["recipient_scope"], "device")
        self.assertNotIn("recipient_device", result)
        self.assertEqual(exit_status, blip_rpc.PENDING_EXIT)

    def test_device_scope_rejects_same_account_device_change_after_invite(self):
        source = _source()
        prepared = _transfer(
            files=[{"name": source["basename"], "kind": "file",
                    "size": source["size"]}])
        changed = _transfer(
            peer={"user_id": PEER["user_id"], "device_id": "device-2"},
            files=prepared["files"],
            status_code=2,
        )
        snapshots = [
            {"devices": [_device()], "transfer": None},
            {"devices": [_device()], "transfer": prepared},
            {"devices": [], "transfer": changed},
        ]
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
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._run_send_locked(
                    SimpleNamespace(recipient="Owned Phone"),
                    TRANSFER_ID,
                    [source],
                )

        self.assertEqual(raised.exception.code, "transfer_peer_changed")
        self.assertEqual(
            [call.args[0] for call in dispatch.call_args_list],
            ["TransferCreateRequested", "TransferAddContentRequested",
             "TransferInviteRequested"],
        )

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
            confirm_recipient_device="Other Phone",
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
        self.assertEqual(result["recipient_scope"], "device")
        self.assertNotIn("user_id", result)
        self.assertNotIn("device_id", result)
        self.assertEqual(exit_status, blip_rpc.PENDING_EXIT)

    def test_account_send_accepts_engine_selected_device_after_invite(self):
        source = _source()
        prepared = _transfer(
            peer=ACCOUNT_PEER,
            files=[{"name": source["basename"], "kind": "file",
                    "size": source["size"]}],
        )
        after_invite = _transfer(
            peer={"user_id": ACCOUNT_PEER["user_id"], "device_id": "engine-choice"},
            files=prepared["files"],
            status_code=2,
        )
        contact = _contact(
            device_name="",
            peer={"user_id": ACCOUNT_PEER["user_id"], "device_id": "reachable-child"},
        )
        snapshots = [
            {"devices": [contact], "transfer": None},
            {"devices": [contact], "transfer": prepared},
            {"devices": [], "transfer": after_invite},
        ]
        args = SimpleNamespace(
            recipient="Other Person",
            recipient_scope="account",
            recipient_device=None,
            confirm_recipient_device=None,
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
        self.assertEqual(result["recipient_scope"], "account")
        self.assertNotIn("recipient_device", result)
        self.assertEqual(exit_status, blip_rpc.PENDING_EXIT)

    def test_account_send_rejects_wrong_user_observed_after_invite(self):
        source = _source()
        prepared = _transfer(
            peer=ACCOUNT_PEER,
            files=[{"name": source["basename"], "kind": "file",
                    "size": source["size"]}],
        )
        wrong_user = _transfer(
            peer={"user_id": "different-account", "device_id": "engine-choice"},
            files=prepared["files"],
            status_code=2,
        )
        contact = _contact(
            device_name="",
            peer={"user_id": ACCOUNT_PEER["user_id"], "device_id": "reachable-child"},
        )
        args = SimpleNamespace(
            recipient="Other Person",
            recipient_scope="account",
            recipient_device=None,
            confirm_recipient_device=None,
        )
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                blip_rpc, "_state_snapshot", side_effect=[
                    {"devices": [contact], "transfer": None},
                    {"devices": [contact], "transfer": prepared},
                    {"devices": [], "transfer": wrong_user},
                ]))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_dispatch_event"))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_wait_until_created"))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_wait_until_prepared"))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_revalidate_sources"))
            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._run_send_locked(args, TRANSFER_ID, [source])

        self.assertEqual(raised.exception.code, "transfer_peer_changed")


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

    def test_send_parser_defaults_to_device_scope_and_accepts_explicit_account(self):
        parser = blip_rpc.build_parser()
        common = [
            "send",
            "--recipient", "Other Person",
            "--confirm-recipient", "Other Person",
            "--transfer-id", TRANSFER_ID,
            "/synthetic-source",
        ]

        self.assertEqual(
            parser.parse_args(common).recipient_scope, "device")
        self.assertEqual(
            parser.parse_args(
                common[:1] + ["--recipient-scope", "account"] + common[1:]
            ).recipient_scope,
            "account",
        )

    def test_incorrect_live_target_name_is_rejected(self):
        with self.assertRaises(blip_rpc.BlipError) as raised:
            blip_rpc._select_recipient([_device()], "Different Phone")
        self.assertEqual(raised.exception.code, "recipient_not_unique")

    def test_default_own_route_rejects_a_foreign_account_row_without_fallback(self):
        foreign = _contact(
            "Owned Phone",
            "Unnamed child",
            peer={"user_id": "foreign-account", "device_id": "foreign-device"},
        )
        with self.assertRaises(blip_rpc.BlipError) as raised:
            blip_rpc._select_send_recipient(
                [foreign], SimpleNamespace(recipient="Owned Phone"))
        self.assertEqual(raised.exception.code, "recipient_not_owned_device")

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

    def test_account_resolution_uses_account_peer_with_five_nameless_children(self):
        contact = _contact(
            peer={"user_id": "account-a", "device_id": "child-0"})
        contact["recipient_devices"] = [{
            "display_name": "",
            "device_id": f"child-{index}",
            "is_online": index == 4,
            "is_pushable": False,
            "live": index == 4,
            "is_self": False,
        } for index in range(5)]

        selected = blip_rpc._select_account_recipient(
            [contact], "Other Person")

        self.assertEqual(
            selected, {"user_id": "account-a", "device_id": ""})

    def test_account_resolution_rejects_ambiguous_or_unreachable_accounts(self):
        duplicate = [
            _contact(peer={"user_id": "account-a", "device_id": "child-a"}),
            _contact(peer={"user_id": "account-b", "device_id": "child-b"}),
        ]
        unreachable = _contact(
            peer={"user_id": "account-a", "device_id": "child-a"},
            live=False,
        )
        incomplete = _contact(
            peer={"user_id": "account-a", "device_id": ""},
        )
        cases = (
            (duplicate, "recipient_not_unique"),
            ([unreachable], "recipient_not_reachable"),
            ([incomplete], "recipient_invalid"),
        )
        for entries, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(blip_rpc.BlipError) as raised:
                    blip_rpc._select_account_recipient(
                        entries, "Other Person")
                self.assertEqual(raised.exception.code, expected_code)

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

    def test_external_send_accepts_confirmed_human_device_or_contact_kind(self):
        for entry_type in ("device", "contact"):
            record = {
                "display_name": "Other Person",
                "entry_type": entry_type,
                "ownership": "other_person_confirmed",
                "requires_identity_confirmation": False,
            }
            with self.subTest(entry_type=entry_type):
                with mock.patch.object(
                        blip_rpc, "_load_inventory",
                        return_value={"devices": [record]}):
                    selected = blip_rpc._confirmed_inventory_recipient(
                        "Other Person",
                        entry_types=("device", "contact"),
                        ownership="other_person_confirmed",
                    )
                self.assertIs(selected, record)

    def test_external_send_rejects_unconfirmed_kind_ownership_or_identity(self):
        base = {
            "display_name": "Other Person",
            "entry_type": "contact",
            "ownership": "other_person_confirmed",
            "requires_identity_confirmation": False,
        }
        cases = (
            {**base, "entry_type": "unknown"},
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
                            entry_types=("device", "contact"),
                            ownership="other_person_confirmed",
                        )
                self.assertEqual(raised.exception.code, "recipient_not_confirmed")

    def test_account_mode_accepts_confirmed_human_device_classification(self):
        args = SimpleNamespace(
            transfer_id=TRANSFER_ID,
            recipient="Other Person",
            confirm_recipient="Other Person",
            recipient_scope="account",
            recipient_device=None,
            confirm_recipient_device=None,
            files=["/synthetic-source"],
        )
        stored_device = {
            "display_name": "Other Person",
            "entry_type": "device",
            "ownership": "other_person_confirmed",
            "requires_identity_confirmation": False,
        }
        sources = [_source()]
        expected = ({"command": "send"}, blip_rpc.PENDING_EXIT)
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(blip_rpc, "_require_pinned_build"))
            stack.enter_context(mock.patch.object(
                blip_rpc, "_load_inventory",
                return_value={"devices": [stored_device]}))
            stack.enter_context(
                mock.patch.object(blip_rpc, "_exclusive_send_lock"))
            validate = stack.enter_context(mock.patch.object(
                blip_rpc, "_validate_sources", return_value=sources))
            send = stack.enter_context(mock.patch.object(
                blip_rpc, "_run_send_locked", return_value=expected))

            result = blip_rpc.run_send(args)

        self.assertEqual(result, expected)
        validate.assert_called_once_with(args.files)
        send.assert_called_once_with(args, TRANSFER_ID, sources)

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

    def test_account_scope_rejects_either_child_flag_before_lock_or_mutation(self):
        for field in ("recipient_device", "confirm_recipient_device"):
            values = {
                "recipient_device": None,
                "confirm_recipient_device": None,
            }
            values[field] = "Other Phone"
            args = SimpleNamespace(
                transfer_id=TRANSFER_ID,
                recipient="Other Person",
                confirm_recipient="Other Person",
                recipient_scope="account",
                files=[],
                **values,
            )
            with self.subTest(field=field):
                with mock.patch.object(blip_rpc, "_require_pinned_build"):
                    with mock.patch.object(
                            blip_rpc, "_exclusive_send_lock") as lock:
                        with self.assertRaises(blip_rpc.BlipError) as raised:
                            blip_rpc.run_send(args)
                self.assertEqual(
                    raised.exception.code, "recipient_scope_conflict")
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
            confirm_recipient_device="Other Phone",
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

    def test_account_user_identity_drift_stops_before_invitation(self):
        source = _source()
        prepared = _transfer(
            peer={"user_id": "account-a", "device_id": ""},
            files=[{"name": source["basename"], "kind": "file",
                    "size": source["size"]}],
        )
        initial = {"devices": [
            _contact(peer={"user_id": "account-a", "device_id": "device-a"})
        ], "transfer": None}
        final = {"devices": [
            _contact(peer={"user_id": "account-b", "device_id": "device-b"})
        ], "transfer": prepared}
        args = SimpleNamespace(
            recipient="Other Person",
            recipient_scope="account",
            recipient_device=None,
            confirm_recipient_device=None,
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
                    "entry_type": "device",
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
        self.assertNotIn("live_entry_type", contact)
        self.assertEqual(contact["entry_type"], "device")
        self.assertEqual(result["classification_conflicts"], [])
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
    def test_account_peer_wire_omits_device_field_only_for_account_scope(self):
        account_fields = [
            number for number, _wire_type, _value
            in blip_rpc._fields(
                blip_rpc._peer_message(ACCOUNT_PEER, account_scope=True))
        ]
        device_fields = [
            number for number, _wire_type, _value
            in blip_rpc._fields(blip_rpc._peer_message(PEER))
        ]

        self.assertEqual(account_fields, [1])
        self.assertEqual(device_fields, [1, 2])
        with self.assertRaises(blip_rpc.BlipError) as raised:
            blip_rpc._peer_message(ACCOUNT_PEER)
        self.assertEqual(raised.exception.code, "protocol_violation")

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


class ReadOnlyWatchTests(unittest.TestCase):
    def setUp(self):
        self.clock = 0.0
        self.args = SimpleNamespace(
            transfer_id=TRANSFER_ID, timeout=5.0, interval=2.0)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(blip_rpc, "_require_pinned_build"))
        self.stack.enter_context(mock.patch.object(
            blip_rpc.time, "monotonic", side_effect=lambda: self.clock))
        self.stack.enter_context(mock.patch.object(
            blip_rpc.time, "sleep", side_effect=self.advance))
        self.dispatch = self.stack.enter_context(mock.patch.object(
            blip_rpc, "_dispatch_event", side_effect=AssertionError("watch mutated state")))
        self.state = self.stack.enter_context(mock.patch.object(blip_rpc, "_state_snapshot"))

    def advance(self, seconds):
        self.clock += seconds

    def snapshot(self, **kwargs):
        return {"devices": [], "transfer": _transfer(**kwargs)}

    def test_pending_active_completed_observations_stop_without_resending(self):
        self.state.side_effect = [
            self.snapshot(status_code=4), self.snapshot(status_code=5),
            self.snapshot(status_code=8),
        ]
        result, exit_status = blip_rpc.run_watch(self.args)
        self.assertEqual(exit_status, 0)
        self.assertEqual(result["stop_reason"], "completed")
        self.assertEqual(result["observations"], 3)
        self.assertEqual(result["elapsed_seconds"], 4.0)
        self.assertTrue(result["completed"])
        self.assertTrue(result["terminal"])
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["command"], "watch")
        self.assertEqual(
            self.state.call_args_list,
            [mock.call(TRANSFER_ID, budget, include_devices=False)
             for budget in (5.0, 3.0, 1.0)],
        )
        self.dispatch.assert_not_called()

    def test_paused_and_unknown_remain_observable_without_invented_failure(self):
        for code, reason in ((6, "transfer_paused"), (42, "status_unknown")):
            with self.subTest(code=code):
                self.clock = 0.0
                self.state.reset_mock()
                self.state.return_value = self.snapshot(status_code=code)
                result, exit_status = blip_rpc.run_watch(self.args)
                self.assertEqual(exit_status, blip_rpc.PENDING_EXIT)
                self.assertEqual(result["stop_reason"], "timeout")
                self.assertEqual(result["status_code"], code)
                self.assertEqual(result["reason"], reason)
                self.assertEqual(result["elapsed_seconds"], 5.0)
                self.assertEqual(result["observations"], 3)
                self.assertTrue(result["timed_out"])
                self.assertFalse(result["terminal"])
                self.assertFalse(result["completed"])

    def test_cancel_or_error_stops_watching_without_cancelling_engine(self):
        cases = (
            (dict(status_code=9), "cancelled", True, "none"),
            (dict(status_code=5, has_local_error=True), "error", False, "local"),
            (dict(status_code=4, has_remote_error=True), "error", False, "remote"),
            (dict(status_code=8, has_local_error=True, has_remote_error=True),
             "error", True, "local_and_remote"),
        )
        for values, stop_reason, terminal, scope in cases:
            with self.subTest(values=values):
                self.state.reset_mock()
                self.state.return_value = self.snapshot(**values)
                result, exit_status = blip_rpc.run_watch(self.args)
                self.assertEqual(exit_status, 4)
                self.assertEqual(result["stop_reason"], stop_reason)
                self.assertEqual(result["terminal"], terminal)
                self.assertEqual(result["error_scope"], scope)
                self.assertEqual(result["observations"], 1)
                self.assertFalse(result["timed_out"])
                self.assertEqual(self.state.call_count, 1)
        self.dispatch.assert_not_called()

    def test_rpc_failure_preserves_last_observation_without_retry(self):
        self.state.side_effect = [
            self.snapshot(status_code=5),
            blip_rpc.BlipError("redacted", code="rpc_unavailable", exit_status=3),
        ]
        with self.assertRaises(blip_rpc.BlipError) as raised:
            blip_rpc.run_watch(self.args)
        self.assertEqual(raised.exception.exit_status, 3)
        self.assertEqual(raised.exception.code, "rpc_unavailable")
        self.assertEqual(raised.exception.details["stop_reason"], "rpc_error")
        self.assertEqual(raised.exception.details["observations"], 1)
        self.assertEqual(raised.exception.details["last_status"]["status_code"], 5)
        self.assertEqual(self.state.call_count, 2)
        self.dispatch.assert_not_called()

    def test_rpc_deadline_failure_is_not_disguised_as_pending(self):
        def expire(*_args, **_kwargs):
            self.advance(5)
            raise blip_rpc.BlipError("deadline", code="rpc_timeout", exit_status=3)
        self.state.side_effect = expire
        with self.assertRaises(blip_rpc.BlipError) as raised:
            blip_rpc.run_watch(self.args)
        self.assertEqual(raised.exception.code, "rpc_timeout")
        self.assertEqual(raised.exception.details["observations"], 0)
        self.assertNotIn("last_status", raised.exception.details)
        self.assertEqual(self.state.call_count, 1)

    def test_rpc_and_sleep_consume_the_same_bounded_budget(self):
        self.args.timeout = 1.0
        self.args.interval = 100.0
        def observe(_target, budget, *, include_devices):
            self.assertEqual(budget, 1.0)
            self.assertFalse(include_devices)
            self.advance(0.75)
            return self.snapshot(status_code=4)
        self.state.side_effect = observe
        result, exit_status = blip_rpc.run_watch(self.args)
        self.assertEqual(exit_status, 10)
        self.assertEqual(result["elapsed_seconds"], 1.0)
        self.assertEqual(result["observations"], 1)
        self.assertEqual(self.state.call_count, 1)

    def test_expired_budget_without_observation_does_not_invent_status(self):
        with mock.patch.object(blip_rpc.time, "monotonic", side_effect=[0, 6, 6]):
            result, exit_status = blip_rpc.run_watch(self.args)
        self.assertEqual(exit_status, 10)
        self.assertFalse(result["status_available"])
        self.assertEqual(result["observations"], 0)
        self.assertNotIn("status_code", result)
        self.state.assert_not_called()

    def test_invalid_duration_or_uuid_cannot_query_or_mutate(self):
        for field in ("timeout", "interval"):
            for value in (0, -1, float("nan"), float("inf"), "invalid"):
                with self.subTest(field=field, value=value):
                    args = SimpleNamespace(**vars(self.args))
                    setattr(args, field, value)
                    with self.assertRaises(blip_rpc.BlipError) as raised:
                        blip_rpc.run_watch(args)
                    self.assertEqual(raised.exception.exit_status, 2)
        self.args.transfer_id = "not-a-uuid"
        with self.assertRaises(blip_rpc.BlipError) as raised:
            blip_rpc.run_watch(self.args)
        self.assertEqual(raised.exception.code, "invalid_transfer_id")
        self.state.assert_not_called()
        self.dispatch.assert_not_called()

    def test_status_distinguishes_cancel_error_and_unknown(self):
        for values, exit_status, reason in (
            (dict(status_code=8), 0, "completed"),
            (dict(status_code=9), 4, "cancelled"),
            (dict(status_code=5, has_remote_error=True), 4, "remote_error_reported"),
            (dict(status_code=42), 10, "status_unknown"),
            (dict(status_code=1), 10, "created_invitation_unconfirmed"),
            (dict(status_code=4), 10, "pending_reason_unknown"),
        ):
            with self.subTest(values=values):
                self.state.return_value = self.snapshot(**values)
                result, actual_exit = blip_rpc.run_status(self.args)
                self.assertEqual(actual_exit, exit_status)
                self.assertEqual(result["reason"], reason)
        self.dispatch.assert_not_called()

    def test_error_payloads_and_peer_identifiers_never_reach_status_output(self):
        raw = (
            _integer(800, 5)
            + _field(600, b"PRIVATE_LOCAL_ERROR")
            + _field(601, b"PRIVATE_REMOTE_ERROR")
            + _field(200, _field(1, b"PRIVATE_ACCOUNT") + _field(2, b"PRIVATE_DEVICE"))
        )
        parsed = blip_rpc._parse_transfer(raw)
        self.state.return_value = {"devices": [], "transfer": parsed}
        result, exit_status = blip_rpc.run_status(self.args)
        self.assertEqual(exit_status, 4)
        self.assertEqual(result["error_scope"], "local_and_remote")
        self.assertEqual(result["reason"], "local_and_remote_error_reported")
        self.assertNotIn("PRIVATE_", repr(result))
        self.assertNotIn("peer", result)


if __name__ == "__main__":
    unittest.main()
