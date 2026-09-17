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

TRANSFER_ID = "086cc826-18a2-4cbf-a6f9-6518e5109ea6"
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

    def test_source_identity_change_is_rejected_before_invitation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.txt"
            source.write_bytes(b"original")
            snapshot = blip_rpc._source_snapshot(os.fspath(source))
            replacement = Path(directory) / "replacement.txt"
            replacement.write_bytes(b"replacement-content")
            os.replace(replacement, source)

            with self.assertRaises(blip_rpc.BlipError) as raised:
                blip_rpc._revalidate_sources([snapshot])

        self.assertEqual(raised.exception.code, "source_changed")
        self.assertEqual(raised.exception.details["source"], os.fspath(source))


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
            _field(2, b"\xffprivate-email"),
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
