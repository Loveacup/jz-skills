#!/usr/bin/env python3
"""Compare two chart bundles without inferring relationship quality or outcomes."""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any

from _common import InputError as SharedInputError
from _common import match_aspect, resolve_orbs

FUNCTIONS = ("Se", "Si", "Ne", "Ni", "Te", "Ti", "Fe", "Fi")
SUBTYPE_KEYS = {
    "Ti": ("TiA", "TiH"), "Te": ("TeA", "TeH"),
    "Fi": ("FiA", "FiH"), "Fe": ("FeA", "FeH"),
    "Ni": ("NiO", "NiB"), "Ne": ("NeO", "NeB"),
    "Si": ("SiO", "SiB"), "Se": ("SeO", "SeB"),
}
STANDARD_STACKS = {
    "INTJ": ["Ni", "Te", "Fi", "Se"], "INTP": ["Ti", "Ne", "Si", "Fe"],
    "ENTJ": ["Te", "Ni", "Se", "Fi"], "ENTP": ["Ne", "Ti", "Fe", "Si"],
    "INFJ": ["Ni", "Fe", "Ti", "Se"], "INFP": ["Fi", "Ne", "Si", "Te"],
    "ENFJ": ["Fe", "Ni", "Se", "Ti"], "ENFP": ["Ne", "Fi", "Te", "Si"],
    "ISTJ": ["Si", "Te", "Fi", "Ne"], "ISFJ": ["Si", "Fe", "Ti", "Ne"],
    "ESTJ": ["Te", "Si", "Ne", "Fi"], "ESFJ": ["Fe", "Si", "Ne", "Ti"],
    "ISTP": ["Ti", "Se", "Ni", "Fe"], "ISFP": ["Fi", "Se", "Ni", "Te"],
    "ESTP": ["Se", "Ti", "Fe", "Ni"], "ESFP": ["Se", "Fi", "Te", "Ni"],
}
OPPOSITE = {"Se": "Si", "Si": "Se", "Ne": "Ni", "Ni": "Ne",
            "Te": "Ti", "Ti": "Te", "Fe": "Fi", "Fi": "Fe"}
BEEBE_ROLES = ("Hero", "Parent", "Child", "Inferior", "Opposing", "Critic", "Trickster", "Demon")
STEM_ELEMENTS = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
                 "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
STEM_COMBINATIONS = {
    frozenset(("甲", "己")): "土",
    frozenset(("乙", "庚")): "金",
    frozenset(("丙", "辛")): "水",
    frozenset(("丁", "壬")): "木",
    frozenset(("戊", "癸")): "火",
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
PLANET_PAIRS = (
    ("太阳", "太阳"), ("太阳", "月亮"), ("月亮", "太阳"), ("月亮", "月亮"),
    ("水星", "水星"), ("金星", "金星"), ("金星", "火星"), ("火星", "金星"),
    ("土星", "太阳"), ("土星", "金星"), ("冥王星", "金星"),
)


class ContractError(ValueError):
    pass

class InputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _emit_error(message, "invalid_input")
        raise SystemExit(2)


def _emit_error(message: str, code: str) -> None:
    print(f"synastry_calc: {message}", file=sys.stderr)
    json.dump({"status": "error", "error": {"code": code, "path": "$", "message": message}},
              sys.stdout, ensure_ascii=False)
    print(file=sys.stdout)


def _parse_json(raw: str, label: str) -> Any:
    def reject_constant(value: str):
        raise InputError(f"non-finite JSON number: {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value = {}
        for key, item in pairs:
            if key in value:
                raise InputError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    try:
        return json.loads(raw, parse_constant=reject_constant, object_pairs_hook=reject_duplicates)
    except (json.JSONDecodeError, InputError) as exc:
        raise InputError(f"invalid {label} JSON: {exc}") from exc


def _read_json(path: str, label: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            return _parse_json(stream.read(), label)
    except OSError as exc:
        raise InputError(f"cannot read {label} file: {exc}") from exc


def _validate_bundle(bundle: Any, label: str) -> dict[str, Any]:
    if not isinstance(bundle, dict) or bundle.get("schema_version") != 2:
        raise ContractError(f"{label} must be a chart_bundle with schema_version 2")
    if bundle.get("status") not in {"ok", "partial", "error"}:
        raise ContractError(f"{label}.status must be ok, partial, or error")
    if bundle["status"] == "error":
        raise ContractError(f"{label} chart_bundle reports an error status")
    dimensions = bundle.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ContractError(f"{label}.dimensions must be an object")
    for dimension in ("bazi", "ziwei", "astrology"):
        entry = dimensions.get(dimension)
        if not isinstance(entry, dict) or entry.get("status") not in {
            "ok", "partial", "missing_input", "not_applicable", "error"
        }:
            raise ContractError(f"{label}.dimensions.{dimension} is missing a valid status")
        data = entry.get("data")
        if "data" not in entry or (data is not None and not isinstance(data, dict)):
            raise ContractError(f"{label}.dimensions.{dimension}.data must be an object or null")
    return bundle


def _dimension(bundle: dict[str, Any], dimension: str, person: str) -> tuple[dict[str, Any] | None, str | None]:
    entry = bundle["dimensions"][dimension]
    if entry["status"] not in ("ok", "partial") or not isinstance(entry.get("data"), dict):
        return None, None
    return entry["data"], f"{person}.chart_bundle#/dimensions/{dimension}/data"


def _layer(status: str, refs: list[str], observations: list[dict[str, Any]], limits: list[str]) -> dict[str, Any]:
    return {"status": status, "input_refs": refs, "observations": observations, "limits": limits}


def _day_stem(data: dict[str, Any]) -> str | None:
    pillars = data.get("四柱") or data.get("八字")
    if isinstance(pillars, list):
        for pillar in pillars:
            if isinstance(pillar, dict) and pillar.get("柱") == "日柱":
                stem = pillar.get("天干")
                if isinstance(stem, str) and stem in STEM_ELEMENTS:
                    return stem
    if isinstance(pillars, dict):
        day = pillars.get("日柱")
        if isinstance(day, dict) and day.get("天干") in STEM_ELEMENTS:
            return day["天干"]
    day_master = data.get("日主")
    stem = day_master.get("天干") if isinstance(day_master, dict) else data.get("日干")
    return stem if isinstance(stem, str) and stem in STEM_ELEMENTS else None


def analyze_bazi(a_bundle: dict[str, Any], b_bundle: dict[str, Any]) -> dict[str, Any]:
    a_data, a_ref = _dimension(a_bundle, "bazi", "a")
    b_data, b_ref = _dimension(b_bundle, "bazi", "b")
    refs = [ref for ref in (a_ref, b_ref) if ref]
    if a_data is None or b_data is None:
        return _layer("unavailable", refs, [], ["Both chart bundles must provide usable bazi data."])
    a_stem, b_stem = _day_stem(a_data), _day_stem(b_data)
    if a_stem is None or b_stem is None:
        return _layer("unavailable", refs, [], ["Both data sets need a recognized day stem for this comparison."])

    a_element, b_element = STEM_ELEMENTS[a_stem], STEM_ELEMENTS[b_stem]
    relation = "same_element" if a_element == b_element else "no_direct_relation"
    direction = None
    if GENERATES[a_element] == b_element:
        relation, direction = "generates", "a_to_b"
    elif GENERATES[b_element] == a_element:
        relation, direction = "generates", "b_to_a"
    elif CONTROLS[a_element] == b_element:
        relation, direction = "controls", "a_to_b"
    elif CONTROLS[b_element] == a_element:
        relation, direction = "controls", "b_to_a"
    observations = [{
        "calculation_method": "day_stem_element_relations",
        "day_stems": {"a": a_stem, "b": b_stem},
        "elements": {"a": a_element, "b": b_element},
        "element_relation": relation,
        "direction": direction,
        "ten_stem_combination_element": STEM_COMBINATIONS.get(frozenset((a_stem, b_stem))),
    }]
    return _layer("available", refs, observations, [
        "These are traditional rule-table relationships between supplied day stems, not observations of either person's behavior or relationship outcome.",
        "This result does not infer anyone's gender, role, identity, or relationship status.",
    ])


def _ziwei_palaces(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    base = data
    leap = data.get("闰月警告")
    if isinstance(leap, dict) and isinstance(leap.get("中分法盘"), dict):
        base = leap["中分法盘"]
    palaces = base.get("十二宫")
    if not isinstance(palaces, list):
        return {}
    result = {}
    for palace in palaces:
        if not isinstance(palace, dict) or not isinstance(palace.get("宫位"), str):
            continue
        stars = palace.get("主星", [])
        if not isinstance(stars, list):
            continue
        star_names = [star["名称"] for star in stars if isinstance(star, dict) and isinstance(star.get("名称"), str)]
        mutagens = [
            {"star": star["名称"], "transformation": star["四化"]}
            for star in stars if isinstance(star, dict) and isinstance(star.get("名称"), str)
            and isinstance(star.get("四化"), str)
        ]
        result[palace["宫位"]] = {"main_stars": star_names, "mutagens": mutagens}
    return result


def analyze_ziwei(a_bundle: dict[str, Any], b_bundle: dict[str, Any]) -> dict[str, Any]:
    a_data, a_ref = _dimension(a_bundle, "ziwei", "a")
    b_data, b_ref = _dimension(b_bundle, "ziwei", "b")
    refs = [ref for ref in (a_ref, b_ref) if ref]
    if a_data is None or b_data is None:
        return _layer("unavailable", refs, [], ["Both chart bundles must provide usable ziwei data."])
    a_palaces, b_palaces = _ziwei_palaces(a_data), _ziwei_palaces(b_data)
    shared = [name for name in ("命宫", "夫妻宫", "福德宫") if name in a_palaces and name in b_palaces]
    if not shared:
        return _layer("unavailable", refs, [], ["No matching palace data is available on both charts."])
    observations = [{
        "calculation_method": "traditional_palace_configuration",
        "palace": name,
        "a": a_palaces[name],
        "b": b_palaces[name],
    } for name in shared]
    return _layer("available", refs, observations, [
        "The output compares supplied palace and star configurations only; it does not predict relationship events or fit.",
        "Palace terminology is part of the traditional chart, not an inference about either person's identity or status.",
    ])


def _planet_positions(data: dict[str, Any]) -> dict[str, float]:
    positions = data.get("十大行星+北交+凯龙")
    if not isinstance(positions, dict):
        positions = data.get("planets") if isinstance(data.get("planets"), dict) else data
    result = {}
    for planet in ("太阳", "月亮", "水星", "金星", "火星", "土星", "冥王星"):
        item = positions.get(planet)
        longitude = item.get("黄经") if isinstance(item, dict) else None
        if longitude is None:
            continue
        if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
            raise ContractError(f"astrology longitude for {planet} must be numeric")
        longitude = float(longitude)
        if not math.isfinite(longitude) or not 0 <= longitude < 360:
            raise ContractError(f"astrology longitude for {planet} must be finite and in [0, 360)")
        result[planet] = longitude
    return result


def analyze_astrology(a_bundle: dict[str, Any], b_bundle: dict[str, Any], orbs: dict[str, float], profile: str) -> dict[str, Any]:
    a_data, a_ref = _dimension(a_bundle, "astrology", "a")
    b_data, b_ref = _dimension(b_bundle, "astrology", "b")
    refs = [ref for ref in (a_ref, b_ref) if ref]
    if a_data is None or b_data is None:
        return _layer("unavailable", refs, [], ["Both chart bundles must provide usable astrology data."])
    a_positions, b_positions = _planet_positions(a_data), _planet_positions(b_data)
    checked = 0
    observations = []
    for a_point, b_point in PLANET_PAIRS:
        if a_point not in a_positions or b_point not in b_positions:
            continue
        checked += 1
        match = match_aspect(a_positions[a_point], b_positions[b_point], orbs)
        if match is not None:
            observations.append({
                "kind": "computed_aspect",
                "a_point": a_point,
                "b_point": b_point,
                **match,
                "profile": profile,
            })
    if checked == 0:
        return _layer("unavailable", refs, [], ["No supported cross-chart planet pair has both longitudes."])
    observations.append({"kind": "aspect_scan", "checked_pairs": checked, "matched_pairs": len(observations)})
    return _layer("available", refs, observations, [
        "Aspect geometry is computed from supplied longitudes; aspect counts do not measure compatibility or relationship outcomes.",
        "Unlisted aspects are not evidence that no interaction exists.",
    ])


def _validate_jung(data: Any, label: str) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("construct"), str):
        raise InputError(f"{label} Jung JSON requires a supported construct")
    construct = data["construct"]
    if construct == "mbti_type":
        type_code = data.get("self_reported_type")
        if not isinstance(type_code, str) or type_code.upper() not in STANDARD_STACKS:
            raise InputError(f"{label} contains an invalid type code")
        mapping = data.get("theory_mapping")
        stack = mapping.get("stack") if isinstance(mapping, dict) else None
        if not isinstance(stack, list) or len(stack) != 8:
            raise InputError(f"{label} Beebe theory mapping must contain exactly 8 stack entries")
        functions = []
        for index, entry in enumerate(stack, start=1):
            if (not isinstance(entry, dict) or entry.get("position") != index
                    or entry.get("function") not in FUNCTIONS
                    or entry.get("role") != BEEBE_ROLES[index - 1]):
                raise InputError(f"{label} has an invalid stack entry at position {index}")
            functions.append(entry["function"])
        if len(set(functions)) != 8:
            raise InputError(f"{label} stack functions must be unique")
        expected = STANDARD_STACKS[type_code.upper()]
        if functions != expected + [OPPOSITE[function] for function in expected]:
            raise InputError(f"{label} stack does not match the supplied type's theory mapping")
        return {"construct": construct, "type": type_code.upper(), "stack": functions}
    if construct in ("functions8", "subtypes16"):
        keys = FUNCTIONS if construct == "functions8" else tuple(
            key for function in FUNCTIONS for key in SUBTYPE_KEYS[function]
        )
        scores = data.get("raw_scores")
        if not isinstance(scores, dict) or set(scores) != set(keys):
            raise InputError(f"{label} has an incomplete or invalid {construct} score set")
        scale = data.get("scale")
        if isinstance(scale, bool) or not isinstance(scale, (int, float)):
            raise InputError(f"{label} requires a finite positive scale")
        try:
            scale = float(scale)
        except (OverflowError, ValueError) as exc:
            raise InputError(f"{label} requires a finite positive scale") from exc
        if not math.isfinite(scale) or scale <= 0:
            raise InputError(f"{label} requires a finite positive scale")
        checked = {}
        for key in keys:
            value = scores[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InputError(f"{label} score {key} is outside the declared scale")
            try:
                value = float(value)
            except (OverflowError, ValueError) as exc:
                raise InputError(f"{label} score {key} is outside the declared scale") from exc
            if not math.isfinite(value) or not 0 <= value <= scale:
                raise InputError(f"{label} score {key} is outside the declared scale")
            checked[key] = value
        return {"construct": construct, "raw_scores": checked, "scale": scale}
    raise InputError(f"{label} has an unsupported construct: {construct}")



def analyze_jung(a_data: dict[str, Any] | None, b_data: dict[str, Any] | None) -> dict[str, Any]:
    refs = []
    if a_data is not None:
        a_data = _validate_jung(a_data, "a")
        refs.append("a.jung")
    if b_data is not None:
        b_data = _validate_jung(b_data, "b")
        refs.append("b.jung")
    if a_data is None or b_data is None:
        return _layer("unavailable", refs, [], ["Jung inputs are optional; a paired comparison requires both inputs."])
    a, b = a_data, b_data
    if a["construct"] != b["construct"]:
        return _layer("unavailable", refs, [], ["Paired Jung comparison requires matching constructs; the individual inputs remain distinct."])
    if a["construct"] == "mbti_type":
        observations = [
            {"kind": "theory_mapping", "person": person, "self_reported_type": item["type"], "stack": item["stack"]}
            for person, item in (("a", a), ("b", b))
        ]
        limits = ["These are separately supplied theory mappings, not measured behavior or relationship outcomes."]
    else:
        observations = [
            {"kind": "construct_snapshot", "person": person, "construct": item["construct"],
             "raw_scores": item["raw_scores"], "scale": item["scale"]}
            for person, item in (("a", a), ("b", b))
        ]
        limits = ["Raw scores are shown side by side without inferring compatibility, ability, or a unified profile."]
    return _layer("available", refs, observations, limits)


def calc_synastry(a_bundle: dict[str, Any], b_bundle: dict[str, Any],
                  a_jung: dict[str, Any] | None = None, b_jung: dict[str, Any] | None = None,
                  custom_orbs: dict[str, Any] | None = None) -> dict[str, Any]:
    a_bundle = _validate_bundle(a_bundle, "a")
    b_bundle = _validate_bundle(b_bundle, "b")
    profile, orbs = resolve_orbs(custom_orbs)
    jung = analyze_jung(a_jung, b_jung)
    bazi = analyze_bazi(a_bundle, b_bundle)
    ziwei = analyze_ziwei(a_bundle, b_bundle)
    astrology = analyze_astrology(a_bundle, b_bundle, orbs, profile)
    dimensions = {"jung": jung, "bazi": bazi, "ziwei": ziwei, "astrology": astrology}
    any_available = any(layer["status"] == "available" for layer in dimensions.values())
    return {
        "schema_version": 1,
        "status": "ok" if any_available else "partial",
        "aspect_profile": profile,
        "orbs": orbs,
        "dimensions": dimensions,
        "communication_options": [{
            "action": "If both people want to discuss a disagreement, each can first restate the other's point before offering a response.",
            "trigger": "A conversation both participants choose to have",
            "review_question": "Did each person feel accurately heard?",
            "adapt_or_stop": "Change or stop the exercise if either person does not find it useful.",
        }],
        "limitations": [
            "Chart calculations and theory mappings do not establish attraction, compatibility, identity, or future events.",
            "Each person's input remains separate; missing layers are reported as unavailable rather than scored.",
        ],
    }


def _parse_orbs(raw: str | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    value = _parse_json(raw, "orbs")
    if not isinstance(value, dict):
        raise InputError("--orbs must be a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument("--a", required=True, help="person A chart_bundle JSON")
    parser.add_argument("--b", required=True, help="person B chart_bundle JSON")
    parser.add_argument("--a-jung", help="optional person A jung_calc JSON")
    parser.add_argument("--b-jung", help="optional person B jung_calc JSON")
    parser.add_argument("--orbs", help="optional JSON object of custom aspect orbs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        a_bundle = _read_json(args.a, "chart_bundle A")
        b_bundle = _read_json(args.b, "chart_bundle B")
        a_jung = _read_json(args.a_jung, "Jung A") if args.a_jung else None
        b_jung = _read_json(args.b_jung, "Jung B") if args.b_jung else None
        orbs = _parse_orbs(args.orbs)
        result = calc_synastry(a_bundle, b_bundle, a_jung, b_jung, orbs)
    except (InputError, SharedInputError) as exc:
        _emit_error(str(exc), "invalid_input")
        return 2
    except ContractError as exc:
        _emit_error(str(exc), "contract_failure")
        return 1
    except Exception as exc:
        _emit_error(str(exc), "calculation_failure")
        return 1
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, allow_nan=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
