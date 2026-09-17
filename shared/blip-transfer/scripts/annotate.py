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
        known[name] = item
    if not isinstance(live, dict) or not isinstance(live.get("devices"), list):
        raise ValueError("expected helper JSON with a devices array")
    names = []
    for item in live["devices"]:
        if not isinstance(item, dict) or not isinstance(item.get("display_name"), str) or not item["display_name"]:
            raise ValueError("live device requires a nonempty display_name")
        names.append(item["display_name"])
    counts = Counter(names)
    rows, questions = [], []
    for name in dict.fromkeys(names):
        record = known.get(name)
        duplicate = counts[name] > 1
        needs_confirmation = (record is None or record.get("ownership") not in confirmed
                              or record.get("requires_identity_confirmation") is not False or duplicate)
        row = {"display_name": name,
               "label": record.get("label", name) if record else name,
               "ownership": record.get("ownership", "unconfirmed") if record else "unconfirmed",
               "new_device": record is None,
               "duplicate_live_name": duplicate,
               "requires_identity_confirmation": needs_confirmation,
               "standing_send_authorization": False}
        rows.append(row)
        if needs_confirmation:
            questions.append({"display_name": name,
                              "reason": "duplicate_name" if duplicate else "new_device" if record is None else "unconfirmed_ownership" if record.get("ownership") not in confirmed else "identity_reconfirmation",
                              "question": "同名设备无法安全区分，请在 Blip 中确认具体目标。" if duplicate else "这个设备是谁的：你本人、家人/共享、其他人，还是暂不确认？"})
    return {"devices": rows, "ownership_questions": questions,
            "not_currently_listed": [name for name in known if name not in counts],
            "sending_authorized": False,
            "note": "Exact-name annotations only. New devices require a user ownership answer. Every send still requires current user authorization."}


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
