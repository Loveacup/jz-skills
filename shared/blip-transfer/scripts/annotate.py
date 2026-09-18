#!/usr/bin/env python3
"""Join live Blip names to private annotations; never infer ownership or send."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def annotate(live, inventory):
    if not isinstance(inventory, dict) or inventory.get("schema_version") != 1:
        raise ValueError("unsupported inventory schema")
    records = inventory.get("devices")
    if not isinstance(records, list):
        raise ValueError("inventory devices must be an array")
    known = {}
    confirmed = {"user_confirmed", "family_or_shared_confirmed", "other_person_confirmed"}
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("inventory device must be an object")
        name = item.get("display_name")
        if not isinstance(name, str) or not name or name in known:
            raise ValueError("inventory names must be nonempty and unique")
        if item.get("standing_send_authorization") is not False:
            raise ValueError("inventory must never grant standing send authorization")
        if "label" in item and not isinstance(item["label"], str):
            raise ValueError("inventory device label must be a string")
        aliases = item.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
            raise ValueError("inventory device aliases must be an array of strings")
        if "notes" in item and not isinstance(item["notes"], str):
            raise ValueError("inventory device notes must be a string")
        if item.get("entry_type", "unknown") not in ("device", "contact", "unknown"):
            raise ValueError("inventory entry_type must be device, contact, or unknown")
        known[name] = item
    if not isinstance(live, dict) or not isinstance(live.get("devices"), list):
        raise ValueError("expected helper JSON with a devices array")
    names = []
    observed_types = {}
    for item in live["devices"]:
        if not isinstance(item, dict) or not isinstance(item.get("display_name"), str) or not item["display_name"]:
            raise ValueError("live device requires a nonempty display_name")
        live_entry_type = item.get("live_entry_type")
        if live_entry_type is not None and live_entry_type not in ("device", "contact"):
            raise ValueError("live_entry_type must be device or contact")
        name = item["display_name"]
        names.append(name)
        observed_types.setdefault(name, set()).add(live_entry_type)
    counts = Counter(names)
    rows, questions, classification_conflicts = [], [], []
    for name in dict.fromkeys(names):
        record = known.get(name)
        duplicate = counts[name] > 1
        live_types = observed_types[name]
        live_entry_type = next(iter(live_types)) if len(live_types) == 1 else None
        stored_entry_type = record.get("entry_type", "unknown") if record else "unknown"
        type_conflict = (
            record is not None
            and stored_entry_type in ("device", "contact")
            and live_entry_type in ("device", "contact")
            and stored_entry_type != live_entry_type
        )
        if type_conflict:
            classification_conflicts.append(name)
        needs_confirmation = (record is None or record.get("ownership") not in confirmed
                              or record.get("requires_identity_confirmation") is not False
                              or duplicate or type_conflict)
        row = {"display_name": name,
               "label": record.get("label", name) if record else name,
               "aliases": list(record.get("aliases", [])) if record else [],
               "notes": record.get("notes", "") if record else "",
               "entry_type": stored_entry_type,
               "ownership": record.get("ownership", "unconfirmed") if record else "unconfirmed",
               "new_device": record is None,
               "duplicate_live_name": duplicate,
               "entry_type_conflict": type_conflict,
               "requires_identity_confirmation": needs_confirmation,
               "standing_send_authorization": False}
        if live_entry_type is not None:
            row["live_entry_type"] = live_entry_type
        rows.append(row)
        if needs_confirmation:
            if duplicate:
                reason = "duplicate_name"
                question = "同名设备或联系人无法安全区分，请在 Blip 中确认具体目标、类型和身份。"
            elif type_conflict:
                reason = "entry_type_conflict"
                question = "实时观察到的设备/联系人类型与已确认记录冲突，请重新确认类型和身份。"
            else:
                reason = ("new_device" if record is None else
                          "unconfirmed_ownership" if record.get("ownership") not in confirmed else
                          "identity_reconfirmation")
                question = "这个条目是设备、联系人还是未知；它属于你本人、家人/共享、其他人，还是暂不确认？"
            questions.append({"display_name": name,
                              "reason": reason,
                              "question": question})
    return {"devices": rows, "ownership_questions": questions,
            "classification_conflicts": classification_conflicts,
            "not_currently_listed": [name for name in known if name not in counts],
            "sending_authorized": False,
            "note": "Exact-name annotations only. New or type-conflicting devices and contacts require a user identity and kind answer. Every send still requires current user authorization."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path,
                        default=Path.home() / ".agents/private/blip-transfer/devices.json")
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        result = annotate(json.load(sys.stdin), inventory)
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error), "sending_authorized": False}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["ownership_questions"] else 0


if __name__ == "__main__":
    sys.exit(main())
