#!/usr/bin/env python3
"""Transform explicitly supplied Jungian construct data into bounded JSON output."""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any

FUNCTIONS = ("Se", "Si", "Ne", "Ni", "Te", "Ti", "Fe", "Fi")
SUBTYPE_KEYS = {
    "Ti": ("TiA", "TiH", "H-A"),
    "Te": ("TeA", "TeH", "H-A"),
    "Fi": ("FiA", "FiH", "H-A"),
    "Fe": ("FeA", "FeH", "H-A"),
    "Ni": ("NiO", "NiB", "B-O"),
    "Ne": ("NeO", "NeB", "B-O"),
    "Si": ("SiO", "SiB", "B-O"),
    "Se": ("SeO", "SeB", "B-O"),
}
STANDARD_STACKS = {
    "INTJ": ["Ni", "Te", "Fi", "Se"],
    "INTP": ["Ti", "Ne", "Si", "Fe"],
    "ENTJ": ["Te", "Ni", "Se", "Fi"],
    "ENTP": ["Ne", "Ti", "Fe", "Si"],
    "INFJ": ["Ni", "Fe", "Ti", "Se"],
    "INFP": ["Fi", "Ne", "Si", "Te"],
    "ENFJ": ["Fe", "Ni", "Se", "Ti"],
    "ENFP": ["Ne", "Fi", "Te", "Si"],
    "ISTJ": ["Si", "Te", "Fi", "Ne"],
    "ISFJ": ["Si", "Fe", "Ti", "Ne"],
    "ESTJ": ["Te", "Si", "Ne", "Fi"],
    "ESFJ": ["Fe", "Si", "Ne", "Ti"],
    "ISTP": ["Ti", "Se", "Ni", "Fe"],
    "ISFP": ["Fi", "Se", "Ni", "Te"],
    "ESTP": ["Se", "Ti", "Fe", "Ni"],
    "ESFP": ["Se", "Fi", "Te", "Ni"],
}
OPPOSITE = {"Se": "Si", "Si": "Se", "Ne": "Ni", "Ni": "Ne",
            "Te": "Ti", "Ti": "Te", "Fe": "Fi", "Fi": "Fe"}
_BEEBE_ROLES = ("Hero", "Parent", "Child", "Inferior", "Opposing", "Critic", "Trickster", "Demon")
REFLECTION_PROMPTS = [
    {
        "theory_basis": "Jungian function preferences are a theoretical interpretive lens, not a measure of ability.",
        "question": "In which situations does this preference feel useful, and when might another approach be worth trying?",
        "needs_observation": True,
    },
    {
        "theory_basis": "A reported score or type does not establish a stable trait across every context.",
        "question": "What recent example supports this description, and what counterexample would make you qualify it?",
        "needs_observation": True,
    },
]


class InputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _emit_error(message)
        raise SystemExit(2)


def _emit_error(message: str) -> None:
    print(f"jung_calc: {message}", file=sys.stderr)
    json.dump(
        {"status": "error", "error": {"code": "invalid_input", "path": "$", "message": message}},
        sys.stdout,
        ensure_ascii=False,
    )
    print(file=sys.stdout)


def _reject_constant(value: str):
    raise InputError(f"non-finite JSON number is not allowed: {value}")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_scores(raw: str, required_keys: tuple[str, ...]) -> dict[str, float]:
    try:
        value = json.loads(
            raw,
            parse_constant=_reject_constant,
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (json.JSONDecodeError, InputError) as exc:
        raise InputError(f"invalid score JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError("score JSON must be an object")
    missing = [key for key in required_keys if key not in value]
    extra = [key for key in value if key not in required_keys]
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing keys: {', '.join(missing)}")
        if extra:
            parts.append(f"unexpected keys: {', '.join(str(key) for key in extra)}")
        raise InputError("; ".join(parts))
    scores = {}
    for key in required_keys:
        score = value[key]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise InputError(f"score for {key} must be a finite number")
        try:
            score = float(score)
        except (OverflowError, ValueError) as exc:
            raise InputError(f"score for {key} must be finite") from exc
        if not math.isfinite(score):
            raise InputError(f"score for {key} must be finite")
        scores[key] = score
    return scores


def validate_scale(scale: float | None, scores: dict[str, float]) -> float:
    if scale is None:
        raise InputError("--scale is required with --scores and --scores16")
    try:
        full_scale = float(scale)
    except (OverflowError, TypeError, ValueError) as exc:
        raise InputError("--scale must be a finite positive number") from exc
    if isinstance(scale, bool) or not math.isfinite(full_scale) or full_scale <= 0:
        raise InputError("--scale must be a finite positive number")
    out_of_range = [key for key, value in scores.items() if value < 0 or value > full_scale]
    if out_of_range:
        raise InputError(f"scores must be within [0, {full_scale}]: {', '.join(out_of_range)}")
    return full_scale


def _ranked_tiers(scores: dict[str, float], scale: float) -> list[dict[str, Any]]:
    grouped: dict[float, list[str]] = {}
    for function in FUNCTIONS:
        grouped.setdefault(scores[function], []).append(function)
    return [
        {
            "functions": functions,
            "raw_score": score,
            "normalized_score": round(score / scale * 10.0, 4),
        }
        for score, functions in sorted(grouped.items(), key=lambda item: item[0], reverse=True)
    ]


def calculate_functions8(raw_scores: dict[str, float], scale: float | None) -> dict[str, Any]:
    scores = _validate_mapping(raw_scores, FUNCTIONS)
    full_scale = validate_scale(scale, scores)
    return {
        "construct": "functions8",
        "raw_scores": scores,
        "scale": full_scale,
        "normalized_scores": {key: round(scores[key] / full_scale * 10.0, 4) for key in FUNCTIONS},
        "ranked_tiers": _ranked_tiers(scores, full_scale),
        "reflection_prompts": REFLECTION_PROMPTS,
        "interpretation_limits": [
            "Normalization is only a linear display transform and does not assess measurement reliability.",
            "Tied scores remain tied; no type, dominant function, ability ranking, or diagnosis is inferred.",
            "Scores are only interpretable in the context of their named instrument and documented scale.",
        ],
    }


def calculate_subtypes16(raw_scores: dict[str, float], scale: float | None) -> dict[str, Any]:
    keys = tuple(key for function in FUNCTIONS for key in SUBTYPE_KEYS[function][:2])
    scores = _validate_mapping(raw_scores, keys)
    full_scale = validate_scale(scale, scores)
    pairs = []
    for function in FUNCTIONS:
        left_key, right_key, _ = SUBTYPE_KEYS[function]
        left = scores[left_key]
        right = scores[right_key]
        delta = right - left
        pairs.append({
            "function": function,
            "left_key": left_key,
            "right_key": right_key,
            "left": left,
            "right": right,
            "delta": delta,
        })
    return {
        "construct": "subtypes16",
        "raw_scores": scores,
        "scale": full_scale,
        "pairs": pairs,
        "derived_functions": None,
        "reflection_prompts": REFLECTION_PROMPTS,
        "interpretation_limits": [
            "Pair deltas use the supplied raw values: T/F are H−A and N/S are B−O.",
            "No 16-to-8 aggregation rule is applied; deltas do not measure ability, certainty, development, or risk.",
            "Every score must be supplied explicitly within the declared scale; missing values are not imputed.",
        ],
    }


def _validate_mapping(scores: dict[str, float], required_keys: tuple[str, ...]) -> dict[str, float]:
    if not isinstance(scores, dict):
        raise InputError("scores must be a JSON object")
    missing = [key for key in required_keys if key not in scores]
    extra = [key for key in scores if key not in required_keys]
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing keys: {', '.join(missing)}")
        if extra:
            parts.append(f"unexpected keys: {', '.join(str(key) for key in extra)}")
        raise InputError("; ".join(parts))
    result = {}
    for key in required_keys:
        value = scores[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InputError(f"score for {key} must be a finite number")
        try:
            value = float(value)
        except (OverflowError, ValueError) as exc:
            raise InputError(f"score for {key} must be finite") from exc
        if not math.isfinite(value):
            raise InputError(f"score for {key} must be finite")
        result[key] = value
    return result


def calculate_type_mapping(type_code: str) -> dict[str, Any]:
    normalized_type = type_code.upper()
    if normalized_type not in STANDARD_STACKS:
        raise InputError(f"unknown type code: {type_code}")
    top_four = STANDARD_STACKS[normalized_type]
    functions = top_four + [OPPOSITE[function] for function in top_four]
    return {
        "construct": "mbti_type",
        "self_reported_type": normalized_type,
        "theory_mapping": {
            "basis": "Beebe theory_mapping",
            "stack": [
                {"position": index + 1, "function": function, "role": _BEEBE_ROLES[index]}
                for index, function in enumerate(functions)
            ],
        },
        "reflection_prompts": REFLECTION_PROMPTS,
        "interpretation_limits": [
            "This is a theoretical mapping of the supplied type, not a measured function score or diagnosis.",
            "The mapping does not establish ability, behavior in every context, or relationship outcomes.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scores", metavar="JSON", help="JSON object with the eight functions8 keys")
    mode.add_argument("--scores16", metavar="JSON", help="JSON object with the sixteen subtype keys")
    mode.add_argument("--type", dest="type_code", metavar="XXXX", help="user-supplied four-letter type")
    parser.add_argument("--scale", type=_finite_positive_scale, help="explicit score maximum; required for score inputs")
    return parser


def _finite_positive_scale(value: str) -> float:
    try:
        scale = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--scale must be a number") from exc
    if not math.isfinite(scale) or scale <= 0:
        raise argparse.ArgumentTypeError("--scale must be finite and positive")
    return scale


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.scores is not None:
            scores = parse_scores(args.scores, FUNCTIONS)
            result = calculate_functions8(scores, args.scale)
        elif args.scores16 is not None:
            keys = tuple(key for function in FUNCTIONS for key in SUBTYPE_KEYS[function][:2])
            scores = parse_scores(args.scores16, keys)
            result = calculate_subtypes16(scores, args.scale)
        else:
            if args.scale is not None:
                raise InputError("--scale is only valid with --scores or --scores16")
            result = calculate_type_mapping(args.type_code)
    except InputError as exc:
        _emit_error(str(exc))
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, allow_nan=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
