#!/usr/bin/env python3
"""Bounded local DRPC client for the verified Blip transfer workflow."""

import argparse
from contextlib import contextmanager
import ctypes
import fcntl
import json
import math
import os
from pathlib import Path
import plistlib
import pwd
import socket
import stat
import sys
import time
import uuid

from annotate import annotate
from inventory import DEFAULT_STATE_DIR, load_json, replace_json, validate_inventory


VERIFIED_BUILDS_PATH = Path(__file__).resolve().with_name("verified-builds.json")
UNVERIFIED_SENDS_NAME = "unverified-build-sends.json"
OUTGOING_DIRECTION = 2
# Schema/protocol-level errors mean the installed build speaks a different contract
# (adapt the adapter); socket, timeout and early-EOF errors stay transport failures.
PROBE_FAILURE_CODES = frozenset((
    "invalid_protobuf", "invalid_contact_state", "invalid_transfer_state",
    "invalid_state_envelope", "invalid_rpc_frame", "rpc_response_too_many_frames",
    "rpc_server_error", "protocol_violation", "compatibility_probe_failed",
))
APP_PLIST = Path("/Applications/Blip.app/Contents/Info.plist")
SOCKET_SUFFIX = Path("Library/Group Containers/AY8UB8KTUX.blip/Library/Caches/sock")
GET_STATE_METHOD = "/rpc.Service/GetState"
DISPATCH_METHOD = "/rpc.Service/Dispatch"
ALLOWED_METHODS = frozenset((GET_STATE_METHOD, DISPATCH_METHOD))
EVENT_TYPES = {
    "TransferCreateRequested": "type.googleapis.com/event.TransferCreateRequested",
    "TransferAddContentRequested": "type.googleapis.com/event.TransferAddContentRequested",
    "TransferInviteRequested": "type.googleapis.com/event.TransferInviteRequested",
}
STATUS_NAMES = {
    0: "UnknownStatus",
    1: "Created",
    2: "InviteRequested",
    3: "Invited",
    4: "Pending",
    5: "Active",
    6: "Paused",
    7: "ResumeRequested",
    8: "Completed",
    9: "Cancelled",
}
STATUS_REASONS = {
    1: "created_invitation_unconfirmed",
    2: "invitation_requested",
    3: "invited_acceptance_unconfirmed",
    4: "pending_reason_unknown",
    5: "transfer_active",
    6: "transfer_paused",
    7: "resume_requested",
    8: "completed",
    9: "cancelled",
}
MAX_RESPONSE = 8 * 1024 * 1024
MAX_FRAMES = 256
RPC_TIMEOUT = 8.0
PREPARE_TIMEOUT = 30.0
PENDING_EXIT = 10


class BlipError(Exception):
    def __init__(self, message, *, code="operation_failed", exit_status=1, details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.exit_status = exit_status
        self.details = dict(details or {})


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise BlipError(message, code="invalid_arguments", exit_status=2)


def _socket_path():
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    return home / SOCKET_SUFFIX


def _installed_build():
    try:
        with APP_PLIST.open("rb") as stream:
            info = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException) as error:
        raise BlipError("Blip application metadata is unavailable", code="blip_not_installed", exit_status=3) from error
    version = str(info.get("CFBundleShortVersionString", ""))
    build = str(info.get("CFBundleVersion", ""))
    return version, build


def _verified_builds():
    try:
        with VERIFIED_BUILDS_PATH.open("r", encoding="utf-8") as stream:
            entries = json.load(stream)
    except (OSError, ValueError) as error:
        raise BlipError("the verified Blip build list is missing or invalid",
                        code="verified_builds_unavailable", exit_status=3) from error
    if not isinstance(entries, list) or not entries:
        raise BlipError("the verified Blip build list is missing or invalid",
                        code="verified_builds_unavailable", exit_status=3)
    builds = set()
    for entry in entries:
        if (not isinstance(entry, dict)
                or not isinstance(entry.get("version"), str) or not entry["version"]
                or not isinstance(entry.get("build"), str) or not entry["build"]):
            raise BlipError("the verified Blip build list is missing or invalid",
                            code="verified_builds_unavailable", exit_status=3)
        builds.add((entry["version"], entry["build"]))
    return entries, builds


def _build_identity():
    version, build = _installed_build()
    _, builds = _verified_builds()
    return {"installed_version": version, "installed_build": build,
            "build_verified": (version, build) in builds}


def _compatibility_probe(snapshot):
    own = [entry for entry in snapshot["devices"] if entry.get("is_contact") is not True]
    if (not own
            or sum(1 for entry in own if entry.get("is_self")) != 1
            or len({entry.get("user_id") for entry in own}) != 1
            or not all(entry.get("user_id") and entry.get("device_id")
                       and entry.get("display_name") for entry in own)):
        raise BlipError(
            "the installed Blip build failed the read-only compatibility probe",
            code="compatibility_probe_failed", exit_status=3)
    return snapshot


def _probe_unverified_build(build):
    try:
        return _compatibility_probe(_state_snapshot())
    except BlipError as error:
        if error.code not in PROBE_FAILURE_CODES:
            raise
        raise BlipError(
            "the installed unverified Blip build is incompatible with this adapter; adapt it before use",
            code="compatibility_probe_failed", exit_status=3,
            details={**build, "probe_error": error.code},
        ) from error


def _require_usable_build():
    """Verified builds pass directly; any other build must pass the read-only probe."""
    build = _build_identity()
    if not build["build_verified"]:
        _probe_unverified_build(build)
    return build


def _validated_socket_stat():
    path = _socket_path()
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as error:
        raise BlipError("the local Blip RPC socket is unavailable; Blip must already be running",
                        code="socket_unavailable", exit_status=3) from error
    if not stat.S_ISSOCK(metadata.st_mode):
        raise BlipError("the expected Blip RPC path is not a Unix socket",
                        code="invalid_socket", exit_status=3)
    if metadata.st_uid != os.getuid():
        raise BlipError("the Blip RPC socket is not owned by the current user",
                        code="invalid_socket_owner", exit_status=3)
    return path, metadata


def _connect(timeout=RPC_TIMEOUT):
    path, before = _validated_socket_stat()
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        client.connect(os.fspath(path))
        _, after = _validated_socket_stat()
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise BlipError("the Blip RPC socket changed while connecting",
                            code="socket_changed", exit_status=3)
        return client
    except BlipError:
        client.close()
        raise
    except (OSError, TimeoutError) as error:
        client.close()
        raise BlipError("cannot connect to the validated local Blip RPC socket",
                        code="rpc_unavailable", exit_status=3) from error


def _varint(value):
    if not isinstance(value, int) or value < 0:
        raise ValueError("varint requires a nonnegative integer")
    encoded = bytearray()
    while value > 0x7f:
        encoded.append((value & 0x7f) | 0x80)
        value >>= 7
    encoded.append(value)
    return bytes(encoded)


def _pb_key(number, wire_type):
    return _varint((number << 3) | wire_type)


def _pb_bytes(number, value):
    return _pb_key(number, 2) + _varint(len(value)) + value


def _pb_text(number, value):
    return _pb_bytes(number, value.encode("utf-8"))


def _pb_message(number, value):
    return _pb_bytes(number, value)


def _frame(kind, message_number, payload, *, done=True):
    control = (kind << 1) | int(done)
    return b"".join((_varint(control), _varint(1), _varint(message_number),
                     _varint(len(payload)), payload))


def _send_call(client, method, request):
    if method not in ALLOWED_METHODS:
        raise BlipError("RPC method is not allowlisted", code="protocol_violation", exit_status=3)
    method_bytes = method.encode("utf-8")
    client.sendall(_frame(1, 1, method_bytes))
    client.sendall(_frame(2, 2, request))
    client.sendall(_frame(6, 3, b""))


def _recv_byte(client):
    scratch = bytearray(1)
    try:
        count = client.recv_into(scratch)
        if count != 1:
            raise BlipError("Blip RPC closed before completing a frame",
                            code="incomplete_rpc_response", exit_status=3)
        return scratch[0]
    except socket.timeout as error:
        raise BlipError("Blip RPC timed out", code="rpc_timeout", exit_status=3) from error
    except OSError as error:
        raise BlipError("Blip RPC read failed", code="rpc_unavailable", exit_status=3) from error
    finally:
        scratch[0] = 0


def _recv_varint(client):
    value = 0
    for shift in range(0, 70, 7):
        byte = _recv_byte(client)
        if shift == 63 and byte > 1:
            break
        value |= (byte & 0x7f) << shift
        if not byte & 0x80:
            return value
    raise BlipError("Blip RPC returned an invalid frame header",
                    code="invalid_rpc_frame", exit_status=3)


def _recv_into(client, destination, offset, length):
    view = memoryview(destination)
    try:
        end = offset + length
        while offset < end:
            try:
                received = client.recv_into(view[offset:end])
            except socket.timeout as error:
                raise BlipError("Blip RPC timed out", code="rpc_timeout", exit_status=3) from error
            except OSError as error:
                raise BlipError("Blip RPC read failed", code="rpc_unavailable", exit_status=3) from error
            if received == 0:
                raise BlipError("Blip RPC closed before completing a frame",
                                code="incomplete_rpc_response", exit_status=3)
            offset += received
    finally:
        view.release()


def _discard_payload(client, length):
    scratch = bytearray(min(65536, max(1, length)))
    try:
        remaining = length
        while remaining:
            chunk = min(remaining, len(scratch))
            _recv_into(client, scratch, 0, chunk)
            remaining -= chunk
    finally:
        _zero_clear(scratch)


def _zero_clear(value):
    if value:
        ctypes.memset(ctypes.addressof(ctypes.c_char.from_buffer(value)), 0, len(value))
    # Do not resize: exception tracebacks may still retain exported memoryviews.


def _receive_message(client):
    response = bytearray()
    total_payload = 0
    try:
        for _ in range(MAX_FRAMES):
            control = _recv_varint(client)
            kind, done = control >> 1, bool(control & 1)
            stream_number = _recv_varint(client)
            _recv_varint(client)
            length = _recv_varint(client)
            if length > MAX_RESPONSE or total_payload + length > MAX_RESPONSE:
                raise BlipError("Blip RPC response exceeded the 8 MiB limit",
                                code="rpc_response_too_large", exit_status=3)
            if stream_number != 1:
                _discard_payload(client, length)
                raise BlipError("Blip RPC returned an unexpected stream",
                                code="invalid_rpc_frame", exit_status=3)
            total_payload += length
            if kind == 2:
                offset = len(response)
                response.extend(bytearray(length))
                _recv_into(client, response, offset, length)
                if done:
                    return response
            elif kind == 3:
                _discard_payload(client, length)
                raise BlipError("Blip RPC returned a redacted server error",
                                code="rpc_server_error", exit_status=3)
            else:
                _discard_payload(client, length)
                if kind == 5:
                    raise BlipError("Blip RPC closed without a complete response",
                                    code="incomplete_rpc_response", exit_status=3)
                raise BlipError("Blip RPC returned a non-allowlisted frame kind",
                                code="invalid_rpc_frame", exit_status=3)
        raise BlipError("Blip RPC response exceeded the 256-frame limit",
                        code="rpc_response_too_many_frames", exit_status=3)
    except Exception:
        _zero_clear(response)
        raise


class _DeadlineSocket:
    """One monotonic deadline across connect, frame headers and payload reads."""

    def __init__(self, client, deadline):
        self.client = client
        self.deadline = deadline

    def _set_remaining_timeout(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise BlipError("Blip RPC deadline expired", code="rpc_timeout", exit_status=3)
        self.client.settimeout(remaining)

    def sendall(self, data):
        self._set_remaining_timeout()
        return self.client.sendall(data)

    def recv_into(self, buffer):
        self._set_remaining_timeout()
        return self.client.recv_into(buffer)

    def close(self):
        self.client.close()


def _rpc(method, request, timeout=RPC_TIMEOUT):
    deadline = time.monotonic() + timeout
    client = _DeadlineSocket(_connect(timeout), deadline)
    try:
        try:
            _send_call(client, method, request)
        except (OSError, socket.timeout) as error:
            raise BlipError("Blip RPC write failed", code="rpc_unavailable", exit_status=3) from error
        return _receive_message(client)
    finally:
        client.close()


def _decode_varint(view, offset):
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(view):
            raise BlipError("Blip returned truncated protobuf data",
                            code="invalid_protobuf", exit_status=3)
        byte = view[offset]
        offset += 1
        if shift == 63 and byte > 1:
            break
        value |= (byte & 0x7f) << shift
        if not byte & 0x80:
            return value, offset
    raise BlipError("Blip returned an invalid protobuf varint",
                    code="invalid_protobuf", exit_status=3)


def _fields(data, wanted=None):
    view = data if isinstance(data, memoryview) else memoryview(data)
    offset = 0
    while offset < len(view):
        key, offset = _decode_varint(view, offset)
        number, wire_type = key >> 3, key & 7
        if number == 0:
            raise BlipError("Blip returned protobuf field zero",
                            code="invalid_protobuf", exit_status=3)
        selected = wanted is None or number in wanted
        if wire_type == 0:
            value, offset = _decode_varint(view, offset)
            if selected:
                yield number, wire_type, value
        elif wire_type == 1:
            end = offset + 8
            if end > len(view):
                raise BlipError("Blip returned truncated protobuf data",
                                code="invalid_protobuf", exit_status=3)
            if selected:
                yield number, wire_type, view[offset:end]
            offset = end
        elif wire_type == 2:
            length, offset = _decode_varint(view, offset)
            end = offset + length
            if end > len(view):
                raise BlipError("Blip returned truncated protobuf data",
                                code="invalid_protobuf", exit_status=3)
            if selected:
                yield number, wire_type, view[offset:end]
            offset = end
        elif wire_type == 5:
            end = offset + 4
            if end > len(view):
                raise BlipError("Blip returned truncated protobuf data",
                                code="invalid_protobuf", exit_status=3)
            if selected:
                yield number, wire_type, view[offset:end]
            offset = end
        else:
            raise BlipError("Blip returned an unsupported protobuf wire type",
                            code="invalid_protobuf", exit_status=3)


def _text(value, label):
    if len(value) > 65536:
        raise BlipError(f"Blip returned an oversized {label}",
                        code="invalid_protobuf", exit_status=3)
    try:
        return bytes(value).decode("utf-8")
    except UnicodeDecodeError as error:
        raise BlipError(f"Blip returned invalid UTF-8 for {label}",
                        code="invalid_protobuf", exit_status=3) from error


def _with_state(decoder, timeout=RPC_TIMEOUT):
    response = _rpc(GET_STATE_METHOD, b"", timeout)
    state = None
    try:
        for number, wire_type, value in _fields(memoryview(response), {2}):
            if number == 2:
                if wire_type != 2 or state is not None:
                    raise BlipError("Blip returned an invalid GetState envelope",
                                    code="invalid_state_envelope", exit_status=3)
                state = value
        if state is None:
            raise BlipError("Blip returned no state", code="invalid_state_envelope", exit_status=3)
        return decoder(state)
    finally:
        if state is not None:
            state.release()
        _zero_clear(response)


def _parse_reach(data):
    online = False
    pushable = False
    for number, wire_type, value in _fields(data, {1, 2}):
        if wire_type != 0:
            raise BlipError("Blip returned invalid device reachability",
                            code="invalid_protobuf", exit_status=3)
        if number == 1:
            online = bool(value)
        elif number == 2:
            pushable = bool(value)
    return online, pushable


def _parse_device(data):
    result = {"device_id": "", "display_name": "", "is_online": False,
              "is_pushable": False, "is_self": False}
    for number, wire_type, value in _fields(data, {1, 3, 4, 6}):
        if number in (1, 3):
            if wire_type != 2:
                raise BlipError("Blip returned invalid device text",
                                code="invalid_protobuf", exit_status=3)
            text = _text(value, "device field")
            result["device_id" if number == 1 else "display_name"] = text
        elif number == 4:
            if wire_type != 2:
                raise BlipError("Blip returned invalid reachability",
                                code="invalid_protobuf", exit_status=3)
            result["is_online"], result["is_pushable"] = _parse_reach(value)
        elif number == 6:
            if wire_type != 0:
                raise BlipError("Blip returned invalid self-device flag",
                                code="invalid_protobuf", exit_status=3)
            result["is_self"] = bool(value)
    result["live"] = result["is_online"] or result["is_pushable"]
    return result


def _parse_device_entry(data):
    map_key = ""
    device = None
    for number, wire_type, value in _fields(data, {1, 2}):
        if wire_type != 2:
            raise BlipError("Blip returned an invalid device entry",
                            code="invalid_protobuf", exit_status=3)
        if number == 1:
            map_key = _text(value, "device map key")
        elif number == 2:
            if device is not None:
                raise BlipError("Blip returned a duplicate device value",
                                code="invalid_protobuf", exit_status=3)
            device = _parse_device(value)
    if device is None:
        return None
    if not device["device_id"]:
        device["device_id"] = map_key
    return device


def _parse_user(data):
    user_name = ""
    user_id = ""
    is_contact = False
    is_self = False
    devices = []
    seen = set()
    for number, wire_type, value in _fields(data, {2, 7, 8, 9, 10}):
        if number == 7:
            if wire_type != 2:
                raise BlipError("Blip returned an invalid device collection",
                                code="invalid_protobuf", exit_status=3)
            device = _parse_device_entry(value)
            if device is not None:
                devices.append(device)
            continue
        if number in seen:
            raise BlipError("Blip returned duplicate user identity fields",
                            code="invalid_contact_state", exit_status=3)
        seen.add(number)
        if number in (2, 8):
            if wire_type != 2:
                raise BlipError("Blip returned an invalid user identity",
                                code="invalid_protobuf", exit_status=3)
            text = _text(value, "user identity")
            if number == 2:
                user_name = text
            else:
                user_id = text
        else:
            if wire_type != 0:
                raise BlipError("Blip returned an invalid user classification",
                                code="invalid_protobuf", exit_status=3)
            if number == 9:
                is_contact = bool(value)
            else:
                is_self = bool(value)

    if is_self:
        for device in devices:
            device.update({
                "user_id": user_id,
                "is_contact": False,
                "live_entry_type": "device",
            })
        return devices
    if not is_contact:
        return []
    if not user_name or not user_id:
        raise BlipError("Blip returned an incomplete discovered contact",
                        code="invalid_contact_state", exit_status=3)
    device_ids = [device["device_id"] for device in devices if device["device_id"]]
    if len(device_ids) != len(set(device_ids)):
        raise BlipError("Blip returned duplicate devices for a discovered contact",
                        code="invalid_contact_state", exit_status=3)
    return [{
        "display_name": user_name,
        "user_id": user_id,
        "is_contact": True,
        "is_self": False,
        "recipient_devices": devices,
    }]


def _parse_discovered_entry(data):
    user = None
    for number, wire_type, value in _fields(data, {2}):
        if number == 2:
            if wire_type != 2:
                raise BlipError("Blip returned an invalid discovered user",
                                code="invalid_protobuf", exit_status=3)
            if user is not None:
                raise BlipError("Blip returned a duplicate discovered user value",
                                code="invalid_contact_state", exit_status=3)
            user = _parse_user(value)
    return user or []


def _parse_users(data):
    entries = []
    for number, wire_type, value in _fields(data, {1}):
        if number == 1:
            if wire_type != 2:
                raise BlipError("Blip returned an invalid discovered-user list",
                                code="invalid_protobuf", exit_status=3)
            entries.extend(_parse_discovered_entry(value))
    return entries


def _parse_peer(data):
    peer = {"user_id": "", "device_id": ""}
    for number, wire_type, value in _fields(data, {1, 2}):
        if wire_type != 2:
            raise BlipError("Blip returned an invalid peer identifier",
                            code="invalid_protobuf", exit_status=3)
        peer["user_id" if number == 1 else "device_id"] = _text(value, "peer identifier")
    return peer


def _parse_file(data):
    size = 0
    for number, wire_type, value in _fields(data, {1}):
        if number == 1:
            if wire_type != 0:
                raise BlipError("Blip returned an invalid file size",
                                code="invalid_protobuf", exit_status=3)
            size = value
    return size


def _parse_any_item(data):
    file_size = None
    other_kind = False
    for number, wire_type, value in _fields(data, {1, 2, 3, 4}):
        if wire_type != 2:
            raise BlipError("Blip returned an invalid archive item",
                            code="invalid_protobuf", exit_status=3)
        if number == 1:
            file_size = _parse_file(value)
        else:
            other_kind = True
    if file_size is not None and not other_kind:
        return "file", file_size
    return "unsupported", None


def _parse_item_entry(data):
    name = None
    item_kind = "unsupported"
    size = None
    for number, wire_type, value in _fields(data, {1, 2}):
        if wire_type != 2:
            raise BlipError("Blip returned an invalid archive entry",
                            code="invalid_protobuf", exit_status=3)
        if number == 1:
            name = _text(value, "archive item name")
        elif number == 2:
            item_kind, size = _parse_any_item(value)
    return {"name": name, "kind": item_kind, "size": size}


def _parse_archive(data):
    items = []
    for number, wire_type, value in _fields(data, {1}):
        if number == 1:
            if wire_type != 2:
                raise BlipError("Blip returned an invalid archive",
                                code="invalid_protobuf", exit_status=3)
            items.append(_parse_item_entry(value))
    return items


def _parse_transfer(data):
    transfer = {
        "transfer_id": "", "peer": {"user_id": "", "device_id": ""},
        "content_job_count": 0, "archive_present": False, "files": [],
        "has_local_error": False, "has_remote_error": False,
        "direction": 0, "status_code": 0,
    }
    wanted = {100, 200, 300, 400, 600, 601, 700, 800}
    for number, wire_type, value in _fields(data, wanted):
        if number == 100:
            if wire_type != 2:
                raise BlipError("Blip returned an invalid transfer identifier",
                                code="invalid_protobuf", exit_status=3)
            transfer["transfer_id"] = _text(value, "transfer identifier")
        elif number == 200:
            if wire_type != 2:
                raise BlipError("Blip returned an invalid transfer peer",
                                code="invalid_protobuf", exit_status=3)
            transfer["peer"] = _parse_peer(value)
        elif number == 300:
            if wire_type != 0:
                raise BlipError("Blip returned an invalid content-job count",
                                code="invalid_protobuf", exit_status=3)
            transfer["content_job_count"] = value
        elif number == 400:
            if wire_type != 2:
                raise BlipError("Blip returned invalid archive metadata",
                                code="invalid_protobuf", exit_status=3)
            transfer["archive_present"] = True
            transfer["files"] = _parse_archive(value)
        elif number == 600:
            transfer["has_local_error"] = True
        elif number == 601:
            transfer["has_remote_error"] = True
        elif number == 700:
            if wire_type != 0:
                raise BlipError("Blip returned an invalid transfer direction",
                                code="invalid_protobuf", exit_status=3)
            transfer["direction"] = value
        elif number == 800:
            if wire_type != 0:
                raise BlipError("Blip returned an invalid transfer status",
                                code="invalid_protobuf", exit_status=3)
            transfer["status_code"] = value
    return transfer


def _parse_transfer_entry(data, target_id):
    key = None
    transfer_value = None
    for number, wire_type, value in _fields(data, {1, 2}):
        if wire_type != 2:
            raise BlipError("Blip returned an invalid transfer entry",
                            code="invalid_protobuf", exit_status=3)
        if number == 1:
            key = _text(value, "transfer map key")
        elif number == 2:
            transfer_value = value
    if key != target_id or transfer_value is None:
        return None
    transfer = _parse_transfer(transfer_value)
    if transfer["transfer_id"] != target_id:
        raise BlipError("Blip transfer key and identifier disagree",
                        code="invalid_transfer_state", exit_status=3)
    return transfer


def _decode_state(data, target_id=None, *, include_devices=True):
    devices = []
    contact_ids = set()
    transfer = None
    wanted = set()
    if include_devices:
        wanted.add(500)
    if target_id is not None:
        wanted.add(600)
    for number, wire_type, value in _fields(data, wanted):
        if wire_type != 2:
            raise BlipError("Blip returned an invalid allowlisted state field",
                            code="invalid_protobuf", exit_status=3)
        if number == 500:
            parsed = _parse_users(value)
            for entry in parsed:
                if entry.get("is_contact") is True:
                    if entry["user_id"] in contact_ids:
                        raise BlipError("Blip returned a duplicate discovered contact",
                                        code="invalid_contact_state", exit_status=3)
                    contact_ids.add(entry["user_id"])
            devices.extend(parsed)
        elif number == 600:
            candidate = _parse_transfer_entry(value, target_id)
            if candidate is not None:
                if transfer is not None:
                    raise BlipError("Blip returned a duplicate transfer identifier",
                                    code="invalid_transfer_state", exit_status=3)
                transfer = candidate
    return {"devices": devices, "transfer": transfer}


def _state_snapshot(target_id=None, timeout=RPC_TIMEOUT, *, include_devices=True):
    return _with_state(
        lambda state: _decode_state(state, target_id, include_devices=include_devices),
        timeout,
    )


def _load_inventory():
    try:
        return validate_inventory(load_json(DEFAULT_STATE_DIR / "devices.json"))
    except (OSError, ValueError, TypeError) as error:
        raise BlipError("the private Blip device inventory is missing or invalid; run initialization",
                        code="invalid_private_inventory", exit_status=2) from error


@contextmanager
def _exclusive_send_lock():
    try:
        directory = os.stat(DEFAULT_STATE_DIR, follow_symlinks=False)
    except OSError as error:
        raise BlipError("the private Blip state directory is unavailable",
                        code="invalid_private_inventory", exit_status=2) from error
    if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid()
            or directory.st_mode & 0o077):
        raise BlipError("the private Blip state directory is not owner-only",
                        code="insecure_private_state", exit_status=2)
    lock_path = DEFAULT_STATE_DIR / ".blip-rpc-send.lock"
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as error:
        raise BlipError("the private Blip send lock is unavailable",
                        code="send_lock_unavailable", exit_status=3) from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise BlipError("the private Blip send lock is invalid",
                            code="send_lock_unavailable", exit_status=3)
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise BlipError("another Blip RPC send is already in progress",
                            code="send_busy", exit_status=5) from error
        yield
    finally:
        os.close(descriptor)


def _annotated_devices(devices):
    inventory = _load_inventory()
    live_for_annotation = {"devices": [
        {
            "display_name": entry["display_name"],
            **({"live_entry_type": entry["live_entry_type"]}
               if "live_entry_type" in entry else {}),
        }
        for entry in devices if entry["display_name"]
    ]}
    try:
        annotations = annotate(live_for_annotation, inventory)
    except (ValueError, TypeError) as error:
        raise BlipError("live devices could not be joined to the private inventory",
                        code="invalid_device_annotations", exit_status=2) from error
    by_name = {row["display_name"]: row for row in annotations["devices"]}
    rows = []
    for entry in devices:
        name = entry["display_name"]
        if not name:
            continue
        annotation = by_name[name]
        row = {
            "display_name": name,
            **({"live_entry_type": entry["live_entry_type"]}
               if "live_entry_type" in entry else {}),
            "label": annotation["label"],
            "aliases": annotation["aliases"],
            "notes": annotation["notes"],
            "entry_type": annotation["entry_type"],
            "ownership": annotation["ownership"],
            "new_device": annotation["new_device"],
            "duplicate_live_name": annotation["duplicate_live_name"],
            "requires_identity_confirmation": annotation["requires_identity_confirmation"],
            "standing_send_authorization": False,
        }
        if "entry_type_conflict" in annotation:
            row["entry_type_conflict"] = annotation["entry_type_conflict"]
        if entry.get("is_contact") is True:
            row.update({
                "is_contact": True,
                "is_self": False,
                "recipient_devices": [{
                    "display_name": device["display_name"],
                    "device_id": device["device_id"],
                    "is_online": device["is_online"],
                    "is_pushable": device["is_pushable"],
                    "live": device["live"],
                    "is_self": device["is_self"],
                } for device in entry["recipient_devices"]],
            })
        else:
            row.update({
                "device_id": entry["device_id"],
                "is_online": entry["is_online"],
                "is_pushable": entry["is_pushable"],
                "live": entry["live"],
                "is_self": entry["is_self"],
            })
        rows.append(row)
    return {
        "command": "devices",
        "discovery_scope": "discovered_devices_and_contacts",
        "devices": rows,
        "ownership_questions": annotations["ownership_questions"],
        "classification_conflicts": annotations.get("classification_conflicts", []),
        "not_currently_listed": annotations["not_currently_listed"],
        "sending_authorized": False,
        "note": annotations["note"],
    }


def _confirmed_inventory_recipient(name, *, entry_types=("device",),
                                   ownership="user_confirmed"):
    inventory = _load_inventory()
    matches = [item for item in inventory["devices"] if item.get("display_name") == name]
    if len(matches) != 1:
        raise BlipError("recipient must exactly match one private inventory record",
                        code="recipient_not_confirmed", exit_status=2)
    record = matches[0]
    if (record.get("entry_type") not in entry_types
            or record.get("ownership") != ownership
            or record.get("requires_identity_confirmation") is not False):
        raise BlipError("recipient inventory kind or ownership is not confirmed for this send mode",
                        code="recipient_not_confirmed", exit_status=2)
    return record


def _select_recipient(devices, exact_name):
    matches = [
        entry for entry in devices
        if entry["display_name"] == exact_name
    ]
    if len(matches) != 1:
        raise BlipError("recipient name is absent or duplicated in freshly queried Blip state",
                        code="recipient_not_unique", exit_status=2)
    recipient = matches[0]
    if (recipient.get("is_contact") is not False
            or recipient.get("live_entry_type") != "device"):
        raise BlipError("recipient is not a freshly discovered owned device",
                        code="recipient_not_owned_device", exit_status=2)
    if recipient["is_self"]:
        raise BlipError("the current device cannot be a transfer recipient",
                        code="recipient_is_self", exit_status=2)
    if not recipient["live"]:
        raise BlipError("recipient is not currently online or push-reachable",
                        code="recipient_not_reachable", exit_status=2)
    if not recipient["user_id"] or not recipient["device_id"]:
        raise BlipError("recipient lacks a complete peer identifier",
                        code="recipient_invalid", exit_status=2)
    return {"user_id": recipient["user_id"], "device_id": recipient["device_id"]}


def _select_external_account(entries, exact_name):
    matches = [
        entry for entry in entries
        if entry["display_name"] == exact_name
    ]
    if len(matches) != 1:
        raise BlipError("recipient name is absent or duplicated in freshly queried Blip state",
                        code="recipient_not_unique", exit_status=2)
    recipient = matches[0]
    if (recipient.get("is_contact") is not True
            or recipient.get("is_self") is not False
            or not recipient.get("user_id")):
        raise BlipError("recipient lacks a complete non-self account identity",
                        code="recipient_invalid", exit_status=2)
    return recipient


def _select_contact_recipient(entries, contact_name, device_name):
    contact = _select_external_account(entries, contact_name)
    matches = [
        device for device in contact.get("recipient_devices", [])
        if device.get("display_name") == device_name
    ]
    if len(matches) != 1:
        raise BlipError("contact device name is absent or duplicated in freshly queried Blip state",
                        code="recipient_device_not_unique", exit_status=2)
    device = matches[0]
    if device.get("is_self"):
        raise BlipError("the local device cannot be selected as a contact device",
                        code="recipient_is_self", exit_status=2)
    if not device.get("live"):
        raise BlipError("contact device is not currently online or push-reachable",
                        code="recipient_not_reachable", exit_status=2)
    if not device.get("device_id"):
        raise BlipError("contact device lacks a complete peer identifier",
                        code="recipient_invalid", exit_status=2)
    return {"user_id": contact["user_id"], "device_id": device["device_id"]}


def _select_account_recipient(entries, account_name):
    account = _select_external_account(entries, account_name)
    children = [
        device for device in account.get("recipient_devices", [])
        if device.get("is_self") is False and device.get("device_id")
    ]
    if not children:
        raise BlipError("recipient account has no complete non-self device identity",
                        code="recipient_invalid", exit_status=2)
    if not any(device.get("live") for device in children):
        raise BlipError("recipient account has no online or push-reachable device",
                        code="recipient_not_reachable", exit_status=2)
    return {"user_id": account["user_id"], "device_id": ""}


def _select_send_recipient(entries, args, mode=None):
    mode = mode or _recipient_mode(args)
    if mode == "account":
        return _select_account_recipient(entries, args.recipient)
    if mode == "child":
        return _select_contact_recipient(
            entries, args.recipient, args.recipient_device)
    return _select_recipient(entries, args.recipient)


def _source_snapshot(raw_path):
    path = Path(raw_path)
    try:
        raw_path.encode("utf-8")
    except UnicodeEncodeError as error:
        raise BlipError("source paths must be valid UTF-8",
                        code="invalid_source", exit_status=2) from error
    if not path.is_absolute():
        raise BlipError("every source path must be absolute",
                        code="invalid_source", exit_status=2, details={"source": raw_path})
    try:
        before = os.stat(path, follow_symlinks=False)
    except OSError as error:
        raise BlipError("source file is missing or unreadable",
                        code="invalid_source", exit_status=2, details={"source": raw_path}) from error
    if stat.S_ISLNK(before.st_mode):
        raise BlipError("source symlinks are not supported",
                        code="invalid_source", exit_status=2, details={"source": raw_path})
    if not stat.S_ISREG(before.st_mode):
        raise BlipError("source must be a regular file; directories are not supported",
                        code="invalid_source", exit_status=2, details={"source": raw_path})
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise BlipError("source file is unreadable",
                        code="invalid_source", exit_status=2, details={"source": raw_path}) from error
    try:
        opened = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
        raise BlipError("source identity changed during validation",
                        code="source_changed", exit_status=2, details={"source": raw_path})
    return {
        "path": os.fspath(path), "basename": path.name, "size": opened.st_size,
        "identity": (opened.st_dev, opened.st_ino, opened.st_size,
                     opened.st_mtime_ns, opened.st_ctime_ns),
    }


def _validate_sources(paths):
    if not paths:
        raise BlipError("at least one source file is required",
                        code="invalid_source", exit_status=2)
    snapshots = [_source_snapshot(path) for path in paths]
    names = [item["basename"] for item in snapshots]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise BlipError("source files must have nonempty, unique basenames",
                        code="duplicate_source_basename", exit_status=2)
    return snapshots


def _revalidate_sources(snapshots):
    for expected in snapshots:
        current = _source_snapshot(expected["path"])
        if current["identity"] != expected["identity"] or current["basename"] != expected["basename"]:
            raise BlipError("source identity changed before invitation",
                            code="source_changed", exit_status=2,
                            details={"source": expected["path"]})


def _peer_message(peer, *, account_scope=False):
    user_id = peer.get("user_id")
    device_id = peer.get("device_id")
    if not user_id or not isinstance(device_id, str):
        raise BlipError("peer identity is incomplete",
                        code="protocol_violation", exit_status=3)
    message = _pb_text(1, user_id)
    if account_scope:
        if device_id:
            raise BlipError("account-scoped peer must omit the device identity",
                            code="protocol_violation", exit_status=3)
        return message
    if not device_id:
        raise BlipError("device-scoped peer requires a device identity",
                        code="protocol_violation", exit_status=3)
    return message + _pb_text(2, device_id)


def _event_payload(event_name, transfer_id, peer=None, paths=None,
                   *, account_scope=False):
    if event_name == "TransferCreateRequested":
        return (
            _pb_text(1, transfer_id)
            + _pb_message(2, _peer_message(peer, account_scope=account_scope))
        )
    if event_name == "TransferAddContentRequested":
        payload = bytearray(_pb_text(1, transfer_id))
        for path in paths:
            payload.extend(_pb_text(2, path))
        return bytes(payload)
    if event_name == "TransferInviteRequested":
        return (
            _pb_text(1, transfer_id)
            + _pb_message(2, _peer_message(peer, account_scope=account_scope))
        )
    raise BlipError("event type is not allowlisted", code="protocol_violation", exit_status=3)


def _dispatch_event(event_name, payload, timeout=RPC_TIMEOUT):
    type_url = EVENT_TYPES.get(event_name)
    if type_url is None:
        raise BlipError("event type is not allowlisted", code="protocol_violation", exit_status=3)
    any_message = _pb_text(1, type_url) + _pb_bytes(2, payload)
    request = _pb_message(1, any_message)
    response = _rpc(DISPATCH_METHOD, request, timeout)
    try:
        if response:
            raise BlipError("Blip returned a nonempty mutation response",
                            code="invalid_rpc_response", exit_status=3)
    finally:
        _zero_clear(response)


def _require_transfer(snapshot, transfer_id):
    transfer = snapshot["transfer"]
    if transfer is None:
        raise BlipError("the requested transfer does not exist",
                        code="transfer_not_found", exit_status=4,
                        details={"transfer_id": transfer_id})
    return transfer


def _verify_created(transfer, peer):
    if transfer["status_code"] != 1:
        raise BlipError("transfer is not in the required Created state",
                        code="unexpected_transfer_state", exit_status=4)
    if transfer["direction"] != OUTGOING_DIRECTION:
        raise BlipError("transfer is not outgoing",
                        code="unexpected_transfer_direction", exit_status=4)
    if transfer["peer"] != peer:
        raise BlipError("transfer peer does not match the confirmed recipient",
                        code="transfer_peer_changed", exit_status=4)
    if transfer["has_local_error"] or transfer["has_remote_error"]:
        raise BlipError("transfer reports a redacted local or remote error",
                        code="transfer_error", exit_status=4)


def _verify_prepared(transfer, peer, sources):
    _verify_created(transfer, peer)
    if transfer["content_job_count"] != 0 or not transfer["archive_present"]:
        return False
    expected = {source["basename"]: source["size"] for source in sources}
    actual = {}
    for item in transfer["files"]:
        name = item["name"]
        if item["kind"] != "file" or name is None or name in actual:
            raise BlipError("prepared transfer contains unsupported or duplicate archive items",
                            code="prepared_content_mismatch", exit_status=4)
        actual[name] = item["size"]
    # Content attachment is asynchronous: wait for the exact archive, not its ack.
    return actual == expected


def _wait_until_created(transfer_id, peer):
    # Dispatch acknowledges the event before the asynchronous state becomes visible.
    deadline = time.monotonic() + PREPARE_TIMEOUT
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BlipError("timed out observing the newly created Blip transfer",
                            code="create_observation_timeout", exit_status=4)
        snapshot = _state_snapshot(
            transfer_id, min(RPC_TIMEOUT, remaining), include_devices=False)
        if snapshot["transfer"] is not None:
            _verify_created(snapshot["transfer"], peer)
            return snapshot["transfer"]
        time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))


def _wait_until_prepared(transfer_id, peer, sources):
    deadline = time.monotonic() + PREPARE_TIMEOUT
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BlipError("timed out waiting for Blip to prepare transfer content",
                            code="prepare_timeout", exit_status=4)
        snapshot = _state_snapshot(
            transfer_id, min(RPC_TIMEOUT, remaining), include_devices=False)
        transfer = _require_transfer(snapshot, transfer_id)
        if _verify_prepared(transfer, peer, sources):
            return transfer
        time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))


def _status_result(transfer_id, transfer):
    code = transfer["status_code"]
    local_error = transfer["has_local_error"]
    remote_error = transfer["has_remote_error"]
    error_scope = ("local_and_remote" if local_error and remote_error
                   else "local" if local_error else "remote" if remote_error else "none")
    return {
        "command": "status",
        "transfer_id": transfer_id,
        "status_code": code,
        "status_name": STATUS_NAMES.get(code, "UnrecognizedStatus"),
        "completed": code == 8,
        "terminal": code in (8, 9),
        "has_local_error": local_error,
        "has_remote_error": remote_error,
        "error_scope": error_scope,
        "reason": (error_scope + "_error_reported" if error_scope != "none"
                   else STATUS_REASONS.get(code, "status_unknown")),
    }


def _status_exit(result):
    if result["error_scope"] != "none" or result["status_code"] == 9:
        return 4
    return 0 if result["completed"] else PENDING_EXIT


def _positive_seconds(value):
    try:
        seconds = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise BlipError("watch durations must be finite positive seconds",
                        code="invalid_arguments", exit_status=2) from error
    if not math.isfinite(seconds) or seconds <= 0:
        raise BlipError("watch durations must be finite positive seconds",
                        code="invalid_arguments", exit_status=2)
    return seconds


def _parse_transfer_id(value):
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise BlipError("transfer id must be a canonical UUID",
                        code="invalid_transfer_id", exit_status=2) from error
    if str(parsed) != value:
        raise BlipError("transfer id must be a canonical lowercase UUID",
                        code="invalid_transfer_id", exit_status=2)
    return value


def _screen_locked():
    core_graphics = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    core_foundation = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    core_graphics.CGSessionCopyCurrentDictionary.restype = ctypes.c_void_p
    core_foundation.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    core_foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
    core_foundation.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    core_foundation.CFDictionaryGetValue.restype = ctypes.c_void_p
    core_foundation.CFBooleanGetValue.argtypes = [ctypes.c_void_p]
    core_foundation.CFBooleanGetValue.restype = ctypes.c_bool
    core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
    dictionary = core_graphics.CGSessionCopyCurrentDictionary()
    if not dictionary:
        raise OSError("CGSessionCopyCurrentDictionary returned null")
    key = core_foundation.CFStringCreateWithCString(
        None, b"CGSSessionScreenIsLocked", 0x08000100)
    if not key:
        core_foundation.CFRelease(dictionary)
        raise OSError("CFStringCreateWithCString returned null")
    try:
        value = core_foundation.CFDictionaryGetValue(dictionary, key)
        return bool(value and core_foundation.CFBooleanGetValue(value))
    finally:
        core_foundation.CFRelease(key)
        core_foundation.CFRelease(dictionary)


def _doctor_rpc_check(build, result, failures, warnings):
    if build["build_verified"]:
        _with_state(lambda _state: True)
        result["rpc_reachable"] = True
        result["compatibility_probe"] = "not_needed"
        return
    warnings.append("unverified_blip_build")
    try:
        snapshot = _state_snapshot()
        result["rpc_reachable"] = True
        _compatibility_probe(snapshot)
    except BlipError as error:
        if error.code not in PROBE_FAILURE_CODES:
            raise
        result["rpc_reachable"] = True
        result["compatibility_probe"] = "failed"
        result["probe_error"] = error.code
        result["next_step"] = "adapt the RPC adapter per references/upgrade-validation.md"
        failures.append("compatibility_probe_failed")
        return
    result["compatibility_probe"] = "passed"
    result["next_step"] = ("send once with current user authorization, watch that UUID "
                           "to Completed, then run record-verified --transfer-id UUID")


def run_doctor(_args):
    result = {
        "command": "doctor",
        "installed_version": None,
        "installed_build": None,
        "build_verified": False,
        "compatibility_probe": "not_run",
        "socket_valid": False,
        "rpc_reachable": False,
        "screen_locked": None,
        "screen_lock_known": False,
        "gui_or_accessibility_required": False,
    }
    failures = []
    warnings = []
    build = None
    try:
        build = _build_identity()
        result.update(build)
    except BlipError as error:
        failures.append(error.code)
    try:
        _validated_socket_stat()
        result["socket_valid"] = True
    except BlipError as error:
        failures.append(error.code)
    if build is not None and result["socket_valid"]:
        try:
            _doctor_rpc_check(build, result, failures, warnings)
        except BlipError as error:
            failures.append(error.code)
    try:
        result["screen_locked"] = _screen_locked()
        result["screen_lock_known"] = True
    except (OSError, AttributeError):
        failures.append("screen_lock_unavailable")
    result["ok"] = not failures
    if warnings:
        result["warnings"] = warnings
    if failures:
        result["failures"] = list(dict.fromkeys(failures))
    return result, 0 if result["ok"] else 3


def run_devices(_args):
    build = _build_identity()
    snapshot = (_state_snapshot() if build["build_verified"]
                else _probe_unverified_build(build))
    result = _annotated_devices(snapshot["devices"])
    result.update(build)
    return result, 2 if result["ownership_questions"] else 0


def run_status(args):
    _require_usable_build()
    transfer_id = _parse_transfer_id(args.transfer_id)
    transfer = _require_transfer(
        _state_snapshot(transfer_id, include_devices=False), transfer_id)
    result = _status_result(transfer_id, transfer)
    return result, _status_exit(result)


def run_watch(args):
    transfer_id = _parse_transfer_id(args.transfer_id)
    timeout = _positive_seconds(args.timeout)
    interval = _positive_seconds(args.interval)
    _require_usable_build()
    started = time.monotonic()
    deadline = started + timeout
    last_status = None
    observations = 0

    def finish(stop_reason):
        result = last_status if last_status is not None else {
            "transfer_id": transfer_id, "completed": False,
        }
        result.update({
            "command": "watch",
            "status_available": last_status is not None,
            "observations": observations,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "timed_out": stop_reason == "timeout",
            "stop_reason": stop_reason,
        })
        return result, (PENDING_EXIT if stop_reason == "timeout"
                        else _status_exit(result))

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return finish("timeout")
        try:
            transfer = _require_transfer(
                _state_snapshot(transfer_id, min(RPC_TIMEOUT, remaining),
                                include_devices=False),
                transfer_id,
            )
        except BlipError as error:
            error.details.update({
                "command": "watch",
                "transfer_id": transfer_id,
                "observations": observations,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "stop_reason": "rpc_error",
            })
            if last_status is not None:
                error.details["last_status"] = last_status
            raise
        observations += 1
        last_status = _status_result(transfer_id, transfer)
        if last_status["error_scope"] != "none":
            return finish("error")
        if last_status["terminal"]:
            return finish("completed" if last_status["completed"] else "cancelled")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return finish("timeout")
        time.sleep(min(interval, remaining))


def _post_invite_peer_matches(expected, observed, mode):
    if mode == "account":
        return observed.get("user_id") == expected["user_id"]
    return observed == expected


def _run_send_locked(args, transfer_id, sources, before_create=None):
    last_mutation = None
    try:
        mode = _recipient_mode(args)
        account_scope = mode == "account"
        initial = _state_snapshot(transfer_id)
        if initial["transfer"] is not None:
            raise BlipError("transfer id already exists; existing transfers are never resumed or retried",
                            code="transfer_id_exists", exit_status=2)
        peer = _select_send_recipient(initial["devices"], args, mode)
        if before_create is not None:
            before_create()

        last_mutation = "create_requested"
        _dispatch_event(
            "TransferCreateRequested",
            _event_payload(
                "TransferCreateRequested", transfer_id, peer=peer,
                account_scope=account_scope,
            ),
        )
        _wait_until_created(transfer_id, peer)

        last_mutation = "content_requested"
        _dispatch_event("TransferAddContentRequested",
                        _event_payload("TransferAddContentRequested", transfer_id,
                                       paths=[source["path"] for source in sources]))
        _wait_until_prepared(transfer_id, peer, sources)

        final_snapshot = _state_snapshot(transfer_id)
        final_peer = _select_send_recipient(final_snapshot["devices"], args, mode)
        if final_peer != peer:
            raise BlipError("recipient identity changed before invitation",
                            code="recipient_identity_changed", exit_status=4)
        final_transfer = _require_transfer(final_snapshot, transfer_id)
        if not _verify_prepared(final_transfer, peer, sources):
            raise BlipError("transfer content is no longer prepared",
                            code="prepared_content_changed", exit_status=4)
        _revalidate_sources(sources)

        last_mutation = "invite_requested"
        _dispatch_event(
            "TransferInviteRequested",
            _event_payload(
                "TransferInviteRequested", transfer_id, peer=peer,
                account_scope=account_scope,
            ),
        )
        observed = _require_transfer(
            _state_snapshot(transfer_id, include_devices=False), transfer_id)
        if not _post_invite_peer_matches(peer, observed["peer"], mode):
            raise BlipError("transfer peer changed after invitation",
                            code="transfer_peer_changed", exit_status=4)
        if observed["has_local_error"] or observed["has_remote_error"]:
            raise BlipError("transfer reports a redacted local or remote error",
                            code="transfer_error", exit_status=4)
        result = _status_result(transfer_id, observed)
        result.update({
            "command": "send",
            "recipient": args.recipient,
            "recipient_scope": "account" if account_scope else "device",
            **({"recipient_device": args.recipient_device}
               if mode == "child" else {}),
            "files": [{"name": source["basename"], "size": source["size"]}
                      for source in sources],
            "invite_requested": True,
            "delivery_pending": not result["completed"],
        })
        return result, 0 if result["completed"] else PENDING_EXIT
    except (BlipError, OSError, ValueError, TypeError) as error:
        if not isinstance(error, BlipError):
            error = BlipError("local validation or RPC processing failed",
                              code="unexpected_local_error", exit_status=1)
        if last_mutation is not None:
            error.details.setdefault("transfer_id", transfer_id)
            error.details.setdefault("last_mutation", last_mutation)
            error.details.setdefault("inspect_with_status", True)
            error.details.setdefault("mutation_outcome_unknown", True)
            if last_mutation == "invite_requested":
                error.details.setdefault("delivery_unknown", True)
        raise error


def _recipient_mode(args):
    recipient_scope = getattr(args, "recipient_scope", "device")
    recipient_device = getattr(args, "recipient_device", None)
    confirmed_device = getattr(args, "confirm_recipient_device", None)
    if recipient_scope not in ("device", "account"):
        raise BlipError("recipient scope must be device or account",
                        code="invalid_arguments", exit_status=2)
    if recipient_scope == "account":
        if recipient_device is not None or confirmed_device is not None:
            raise BlipError(
                "account scope cannot be combined with recipient device flags",
                code="recipient_scope_conflict",
                exit_status=2,
            )
        return "account"
    if recipient_device is None and confirmed_device is None:
        return "own"
    if (not recipient_device or not confirmed_device
            or recipient_device != confirmed_device):
        raise BlipError(
            "recipient device and confirmation must both be the same nonempty exact display name",
            code="recipient_device_confirmation_mismatch",
            exit_status=2,
        )
    return "child"


def _unverified_sends_path():
    return DEFAULT_STATE_DIR / UNVERIFIED_SENDS_NAME


def _load_unverified_sends():
    path = _unverified_sends_path()
    if not os.path.lexists(path):
        return {"schema_version": 1, "entries": []}
    try:
        value = load_json(path)
    except ValueError as error:
        raise BlipError("the private unverified-build send ledger is invalid",
                        code="invalid_private_state", exit_status=2) from error
    entries = value.get("entries") if isinstance(value, dict) else None
    if (not isinstance(entries, list) or value.get("schema_version") != 1
            or not all(isinstance(entry, dict)
                       and all(isinstance(entry.get(key), str) and entry[key]
                               for key in ("version", "build", "transfer_id"))
                       for entry in entries)):
        raise BlipError("the private unverified-build send ledger is invalid",
                        code="invalid_private_state", exit_status=2)
    return value


def _write_private_json(path, value):
    try:
        replace_json(path, value)
    except (OSError, ValueError) as error:
        raise BlipError("cannot write private Blip adapter state",
                        code="private_state_write_failed", exit_status=3) from error


def _ledger_entry(build, transfer_id):
    return {"version": build["installed_version"], "build": build["installed_build"],
            "transfer_id": transfer_id}


def _record_unverified_send(build, transfer_id):
    ledger = _load_unverified_sends()
    entry = _ledger_entry(build, transfer_id)
    if entry not in ledger["entries"]:
        ledger["entries"].append(entry)
        _write_private_json(_unverified_sends_path(), ledger)


def run_send(args):
    build = _require_usable_build()
    transfer_id = _parse_transfer_id(args.transfer_id)
    if not args.recipient or args.recipient != args.confirm_recipient:
        raise BlipError("recipient and confirmation must be the same nonempty exact display name",
                        code="recipient_confirmation_mismatch", exit_status=2)
    mode = _recipient_mode(args)
    with _exclusive_send_lock():
        if mode in ("child", "account"):
            _confirmed_inventory_recipient(
                args.recipient,
                entry_types=("device", "contact"),
                ownership="other_person_confirmed",
            )
        else:
            _confirmed_inventory_recipient(args.recipient)
        sources = _validate_sources(args.files)
        # An unverified build's first real send is its acceptance evidence; bind the
        # UUID to this build before any mutation so record-verified cannot reuse
        # an unrelated or pre-upgrade transfer.
        before_create = (None if build["build_verified"]
                         else lambda: _record_unverified_send(build, transfer_id))
        try:
            result, exit_status = _run_send_locked(
                args, transfer_id, sources, before_create=before_create)
        except BlipError as error:
            error.details.update(build)
            raise
        result.update(build)
        return result, exit_status


def run_record_verified(args):
    transfer_id = _parse_transfer_id(args.transfer_id)
    build = _build_identity()
    result = {"command": "record-verified", **build, "recorded": False,
              "sending_authorized": False}
    if build["build_verified"]:
        result["already_verified"] = True
        return result, 0
    with _exclusive_send_lock():
        ledger = _load_unverified_sends()
        if _ledger_entry(build, transfer_id) not in ledger["entries"]:
            raise BlipError(
                "only a transfer sent by this adapter on the installed build can verify it",
                code="verification_evidence_mismatch", exit_status=2)
        transfer = _require_transfer(
            _state_snapshot(transfer_id, include_devices=False), transfer_id)
        status = _status_result(transfer_id, transfer)
        outgoing = transfer["direction"] == OUTGOING_DIRECTION
        if not outgoing or not status["completed"] or status["error_scope"] != "none":
            raise BlipError(
                "only an outgoing Completed transfer without reported errors verifies a build",
                code="verification_not_completed",
                exit_status=_status_exit(status) if outgoing else 4,
                details={"status_name": status["status_name"],
                         "error_scope": status["error_scope"], "outgoing": outgoing},
            )
        entries, _ = _verified_builds()
        entries.append({
            "version": build["installed_version"],
            "build": build["installed_build"],
            "verified_on": time.strftime("%Y-%m-%d"),
            "evidence": "outgoing exact-UUID Completed (8) RPC send by this adapter",
        })
        _write_private_json(VERIFIED_BUILDS_PATH, entries)
        try:
            VERIFIED_BUILDS_PATH.chmod(0o644)
        except OSError as error:
            raise BlipError("cannot set verified build list permissions",
                            code="private_state_write_failed", exit_status=3) from error
        ledger["entries"] = [
            entry for entry in ledger["entries"]
            if (entry["version"], entry["build"])
            != (build["installed_version"], build["installed_build"])
        ]
        _write_private_json(_unverified_sends_path(), ledger)
    result.update({"recorded": True, "build_verified": True})
    return result, 0


def build_parser():
    parser = JsonArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "doctor", help="check app build, local socket, RPC, compatibility probe, and lock state")
    commands.add_parser("devices", help="query and annotate freshly discovered devices")
    status_parser = commands.add_parser("status", help="query exactly one transfer")
    status_parser.add_argument("--transfer-id", required=True)
    watch_parser = commands.add_parser(
        "watch", help="read-only bounded polling of exactly one transfer")
    watch_parser.add_argument("--transfer-id", required=True)
    watch_parser.add_argument("--timeout", type=_positive_seconds, default=120.0)
    watch_parser.add_argument("--interval", type=_positive_seconds, default=2.0)
    send_parser = commands.add_parser("send", help="create, prepare, and invite one transfer")
    send_parser.add_argument("--recipient", required=True)
    send_parser.add_argument("--confirm-recipient", required=True)
    send_parser.add_argument(
        "--recipient-scope", choices=("device", "account"), default="device")
    send_parser.add_argument("--recipient-device")
    send_parser.add_argument("--confirm-recipient-device")
    send_parser.add_argument("--transfer-id", required=True)
    send_parser.add_argument("files", nargs="+")
    record_parser = commands.add_parser(
        "record-verified",
        help="mark the installed build verified after this adapter's Completed send on it")
    record_parser.add_argument("--transfer-id", required=True)
    return parser


def main():
    try:
        args = build_parser().parse_args()
        handlers = {
            "doctor": run_doctor,
            "devices": run_devices,
            "status": run_status,
            "watch": run_watch,
            "send": run_send,
            "record-verified": run_record_verified,
        }
        result, exit_status = handlers[args.command](args)
    except BlipError as error:
        result = {"error": error.message, "code": error.code,
                  "sending_authorized": False}
        result.update(error.details)
        exit_status = error.exit_status
    except (OSError, ValueError, TypeError) as error:
        result = {"error": "local validation or RPC processing failed",
                  "code": "unexpected_local_error", "sending_authorized": False}
        exit_status = 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_status


if __name__ == "__main__":
    sys.exit(main())
