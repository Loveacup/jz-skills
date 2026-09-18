#!/usr/bin/env python3
"""Initialize and maintain Blip's shared private device inventory."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import platform
import stat
import sys
import tempfile

from annotate import annotate

SCHEMA_VERSION = 1
DEFAULT_STATE_DIR = Path.home() / ".agents/private/blip-transfer"
OWNERSHIP = {
    "user": "user_confirmed",
    "family-shared": "family_or_shared_confirmed",
    "other": "other_person_confirmed",
    "unknown": "unconfirmed",
}


def today():
    return datetime.now(timezone.utc).date().isoformat()


def normalized_path(value):
    """Expand and absolutize without resolving or rewriting symlinks."""
    return Path(os.path.abspath(os.path.expanduser(os.fspath(value))))


def reject_symlink(path):
    if path.is_symlink():
        raise ValueError(f"sensitive path must not be a symlink: {path}")


def ensure_state_dir(path):
    reject_symlink(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    reject_symlink(path)
    if not path.is_dir():
        raise ValueError(f"state path is not a directory: {path}")
    path.chmod(0o700)


@contextmanager
def locked_state(path):
    ensure_state_dir(path)
    for name in (".inventory.lock", "devices.json", "initialization.json"):
        reject_symlink(path / name)
    lock_path = path / ".inventory.lock"
    reject_symlink(lock_path)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"lock path is not a regular file: {lock_path}")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def load_json(path):
    reject_symlink(path)
    if not path.exists():
        raise ValueError(f"missing state file; run init first: {path}")
    if not path.is_file():
        raise ValueError(f"state path is not a regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error
    return value


def validate_inventory(value):
    annotate({"devices": []}, value)
    return value


def validate_initialization(value):
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported initialization schema")
    if not isinstance(value.get("date"), str) or not value["date"]:
        raise ValueError("initialization date must be a nonempty string")
    if not isinstance(value.get("platform"), str) or not value["platform"]:
        raise ValueError("initialization platform must be a nonempty string")
    if "runtime" in value and (not isinstance(value["runtime"], str) or not value["runtime"]):
        raise ValueError("initialization runtime must be a nonempty string")
    return value


def write_temp(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return Path(temporary)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        Path(temporary).unlink(missing_ok=True)
        raise


def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create_json(path, value):
    reject_symlink(path)
    temporary = write_temp(path, value)
    try:
        os.link(temporary, path, follow_symlinks=False)
        fsync_directory(path.parent)
    except FileExistsError:
        raise ValueError(f"refusing to overwrite existing state file: {path}") from None
    finally:
        temporary.unlink(missing_ok=True)


def replace_json(path, value):
    reject_symlink(path)
    temporary = write_temp(path, value)
    try:
        reject_symlink(path)
        os.replace(temporary, path)
        path.chmod(0o600)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def parse_live(stream):
    try:
        live = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid live device JSON: {error}") from error
    if not isinstance(live, dict) or not isinstance(live.get("devices"), list):
        raise ValueError("expected helper JSON with a devices array")
    if live.get("ok") is False or "error" in live:
        raise ValueError("failed discovery output cannot be synchronized")
    for item in live["devices"]:
        if not isinstance(item, dict) or not isinstance(item.get("display_name"), str) or not item["display_name"]:
            raise ValueError("live device requires a nonempty display_name")
    return live


def run_init(args, state_dir):
    devices_path = state_dir / "devices.json"
    initialization_path = state_dir / "initialization.json"
    created = []
    with locked_state(state_dir):
        if devices_path.exists() or devices_path.is_symlink():
            validate_inventory(load_json(devices_path))
            devices_path.chmod(0o600)
        else:
            create_json(devices_path, {
                "schema_version": SCHEMA_VERSION,
                "devices": [],
                "policy": {
                    "new_devices_require_identity_confirmation": True,
                    "standing_send_authorization": False,
                },
            })
            created.append("devices.json")
        if initialization_path.exists() or initialization_path.is_symlink():
            validate_initialization(load_json(initialization_path))
            initialization_path.chmod(0o600)
        else:
            initialization = {
                "schema_version": SCHEMA_VERSION,
                "date": today(),
                "platform": platform.system(),
                "status": "awaiting_live_sync",
            }
            if args.runtime:
                initialization["runtime"] = args.runtime
            create_json(initialization_path, initialization)
            created.append("initialization.json")
    return {"state_dir": str(state_dir), "created": created,
            "existing": [name for name in ("devices.json", "initialization.json") if name not in created],
            "sending_authorized": False}, 0


def run_sync(_args, state_dir):
    live = parse_live(sys.stdin)
    devices_path = state_dir / "devices.json"
    with locked_state(state_dir):
        inventory = validate_inventory(load_json(devices_path))
        initialization = validate_initialization(load_json(state_dir / "initialization.json"))
        result = annotate(live, inventory)
        by_name = {item["display_name"]: item for item in inventory["devices"]}
        seen_date = today()
        for live_item in live["devices"]:
            name = live_item["display_name"]
            record = by_name.get(name)
            if record is None:
                record = {
                    "display_name": name,
                    "entry_type": "unknown",
                    "label": name,
                    "aliases": [],
                    "ownership": "unconfirmed",
                    "requires_identity_confirmation": True,
                    "standing_send_authorization": False,
                    "evidence_type": "live_observation",
                    "evidence_date": seen_date,
                }
                inventory["devices"].append(record)
                by_name[name] = record
            record["last_seen"] = seen_date
        replace_json(devices_path, inventory)
        scope = live.get("discovery_scope")
        if scope not in (
            "same_account_devices",
            "visible_devices_and_contacts",
            "discovered_devices_and_contacts",
        ):
            scope = "unverified"
        contacts_checked = scope in (
            "visible_devices_and_contacts",
            "discovered_devices_and_contacts",
        )
        unverified_contacts = [
            item["display_name"] for item in inventory["devices"]
            if item.get("entry_type") == "contact"
            and item["display_name"] in result["not_currently_listed"]
        ]
        classification_conflicts = result["classification_conflicts"]
        conflict_names = set(classification_conflicts)
        unclassified_entries = [
            row["display_name"] for row in result["devices"]
            if row["entry_type"] == "unknown"
            or row["display_name"] in conflict_names
        ]
        status = ("awaiting_ownership_confirmation" if result["ownership_questions"]
                  else "awaiting_entry_classification" if unclassified_entries
                  else "awaiting_contact_check" if not contacts_checked or unverified_contacts
                  else "ready")
        coverage = {
            "discovery_scope": scope,
            "contacts_checked": contacts_checked,
            "unverified_contacts": unverified_contacts,
            "unclassified_entries": unclassified_entries,
            "classification_conflicts": classification_conflicts,
        }
        initialization.update({
            "last_sync_date": seen_date,
            "status": status,
            "unresolved_live_device_count": len(result["ownership_questions"]),
            **coverage,
        })
        replace_json(state_dir / "initialization.json", initialization)
        result.update(coverage, initialization_status=status)
    return result, 0 if status == "ready" else 2


def run_confirm(args, state_dir):
    if not args.device or not args.label:
        raise ValueError("device and label must be nonempty")
    if args.ownership != "unknown" and not args.confirmed_by_user:
        raise ValueError("--confirmed-by-user is required for non-unknown ownership")
    if args.entry_type is not None and not args.confirmed_by_user:
        raise ValueError("--confirmed-by-user is required for entry type confirmation")
    devices_path = state_dir / "devices.json"
    with locked_state(state_dir):
        inventory = validate_inventory(load_json(devices_path))
        validate_initialization(load_json(state_dir / "initialization.json"))
        matches = [item for item in inventory["devices"] if item["display_name"] == args.device]
        if len(matches) != 1:
            raise ValueError("device must exactly match one previously observed inventory name")
        record = matches[0]
        if args.entry_type is not None:
            record["entry_type"] = args.entry_type
        record.update({
            "label": args.label,
            "ownership": OWNERSHIP[args.ownership],
            "requires_identity_confirmation": args.ownership == "unknown",
            "standing_send_authorization": False,
            "evidence_type": "user_confirmation" if args.confirmed_by_user else "unconfirmed",
            "evidence_date": today(),
        })
        replace_json(devices_path, inventory)
    return {"device": args.device, "label": args.label,
            "ownership": OWNERSHIP[args.ownership],
            "entry_type": record.get("entry_type", "unknown"),
            "requires_identity_confirmation": args.ownership == "unknown",
            "standing_send_authorization": False,
            "sending_authorized": False}, 0


def run_note(args, state_dir):
    if not args.device:
        raise ValueError("device must be nonempty")
    if args.label is None and args.alias is None and args.notes is None:
        raise ValueError("note requires at least one of --label, --alias, or --notes")
    devices_path = state_dir / "devices.json"
    with locked_state(state_dir):
        inventory = validate_inventory(load_json(devices_path))
        validate_initialization(load_json(state_dir / "initialization.json"))
        matches = [item for item in inventory["devices"] if item["display_name"] == args.device]
        if len(matches) != 1:
            raise ValueError("device must exactly match one previously observed inventory name")
        record = matches[0]
        if args.label is not None:
            record["label"] = args.label
        if args.alias is not None:
            record["aliases"] = args.alias
        if args.notes is not None:
            record["notes"] = args.notes
        replace_json(devices_path, inventory)
    return {
        "device": args.device,
        "label": record.get("label", args.device),
        "aliases": list(record.get("aliases", [])),
        "notes": record.get("notes", ""),
        "ownership": record.get("ownership", "unconfirmed"),
        "requires_identity_confirmation": record.get("requires_identity_confirmation", True),
        "standing_send_authorization": False,
        "sending_authorized": False,
    }, 0


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create or validate shared private state")
    init.add_argument("--runtime", help="optional runtime label recorded only on first initialization")
    commands.add_parser("sync", help="merge successful live device JSON from stdin")
    confirm = commands.add_parser("confirm", help="record a human ownership answer")
    confirm.add_argument("--device", required=True)
    confirm.add_argument("--ownership", required=True, choices=OWNERSHIP)
    confirm.add_argument("--label", required=True)
    confirm.add_argument("--confirmed-by-user", action="store_true")
    confirm.add_argument("--entry-type", choices=("device", "contact", "unknown"))
    note = commands.add_parser("note", help="update non-authorizing device annotations")
    note.add_argument("--device", required=True)
    note.add_argument("--label")
    note.add_argument("--alias", action="append")
    note.add_argument("--notes")
    return root


def main():
    args = parser().parse_args()
    state_dir = normalized_path(args.state_dir)
    try:
        action = {
            "init": run_init,
            "sync": run_sync,
            "confirm": run_confirm,
            "note": run_note,
        }[args.command]
        result, status = action(args, state_dir)
    except (OSError, TypeError, ValueError) as error:
        print(json.dumps({"error": str(error), "sending_authorized": False}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    sys.exit(main())
