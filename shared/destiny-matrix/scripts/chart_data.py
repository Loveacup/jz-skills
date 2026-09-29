#!/usr/bin/env python3
"""Compute chart coordinates and emit JSON for the v5 output contract."""
from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any


class InputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(f"chart_data: {message}", file=sys.stderr)
        json.dump(
            {"status": "error", "error": {"code": "invalid_input", "path": "$", "message": message}},
            sys.stdout,
            ensure_ascii=False,
        )
        print(file=sys.stdout)
        raise SystemExit(2)


def finite_float(value: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("must be finite")
    return number


def parse_kv(raw: str) -> list[tuple[str, float]]:
    pairs: list[tuple[str, float]] = []
    seen: set[str] = set()
    for item in raw.split(","):
        item = item.strip()
        if not item or item.count("=") != 1:
            raise InputError(f"invalid key=value item: {item!r}")
        key, value = (part.strip() for part in item.split("=", 1))
        if not key or key in seen:
            raise InputError(f"empty or duplicate key: {key!r}")
        try:
            number = float(value)
        except ValueError as exc:
            raise InputError(f"value for {key!r} is not numeric") from exc
        if not math.isfinite(number):
            raise InputError(f"value for {key!r} must be finite")
        seen.add(key)
        pairs.append((key, number))
    return pairs


def _validate_range(minimum: float, maximum: float, value: float, label: str) -> None:
    if not math.isfinite(minimum) or not math.isfinite(maximum) or maximum <= minimum:
        raise InputError("maximum must be finite and greater than minimum")
    if not math.isfinite(value) or value < minimum or value > maximum:
        raise InputError(f"{label} must be finite and within [{minimum}, {maximum}]")


def _point(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
    angle = math.radians(angle_deg)
    return round(cx - radius * math.cos(angle), 2), round(cy + radius * math.sin(angle), 2)


def cmd_radar(args: argparse.Namespace) -> dict[str, Any]:
    values = parse_kv(args.values)
    if len(values) < 3:
        raise InputError("radar requires at least 3 supplied dimensions")
    _validate_range(0.0, args.max, args.max, "max")
    if args.rmax <= 0:
        raise InputError("rmax must be greater than zero")

    axes = []
    points = []
    count = len(values)
    for index, (label, score) in enumerate(values):
        _validate_range(0.0, args.max, score, f"value[{label}]")
        theta = 2 * math.pi * index / count
        radius = score / args.max * args.rmax
        x = args.cx + radius * math.sin(theta)
        y = args.cy - radius * math.cos(theta)
        axis_end = (args.cx + args.rmax * math.sin(theta), args.cy - args.rmax * math.cos(theta))
        label_pos = (args.cx + (args.rmax + 22) * math.sin(theta), args.cy - (args.rmax + 22) * math.cos(theta))
        axes.append({
            "label": label,
            "score": score,
            "x": round(x, 2),
            "y": round(y, 2),
            "axis_end": [round(axis_end[0], 2), round(axis_end[1], 2)],
            "label_pos": [round(label_pos[0], 2), round(label_pos[1], 2)],
        })
        points.append(f"{round(x, 2)},{round(y, 2)}")

    grid = []
    for fraction in (0.25, 0.5, 0.75, 1.0):
        ring = []
        for index in range(count):
            theta = 2 * math.pi * index / count
            ring.append(f"{round(args.cx + args.rmax * fraction * math.sin(theta), 2)},"
                        f"{round(args.cy - args.rmax * fraction * math.cos(theta), 2)}")
        grid.append({"fraction": fraction, "points": " ".join(ring)})
    return {
        "type": "radar",
        "cx": args.cx,
        "cy": args.cy,
        "rmax": args.rmax,
        "max": args.max,
        "axes": axes,
        "polygon_points": " ".join(points),
        "grid_rings": grid,
    }


def cmd_wheel(args: argparse.Namespace) -> dict[str, Any]:
    if args.r <= 0:
        raise InputError("r must be greater than zero")
    if not 0 <= args.asc < 360:
        raise InputError("asc longitude must be in [0, 360)")
    planets = []
    for label, longitude in parse_kv(args.planets):
        if not 0 <= longitude < 360:
            raise InputError(f"planet longitude for {label!r} must be in [0, 360)")
        offset = (longitude - args.asc) % 360.0
        x, y = _point(args.cx, args.cy, args.r, offset)
        label_x, label_y = _point(args.cx, args.cy, args.r + 20, offset)
        planets.append({
            "label": label,
            "longitude": longitude,
            "offset_deg": round(offset, 2),
            "x": x,
            "y": y,
            "label_pos": [label_x, label_y],
            "sign_index": int(longitude // 30) % 12,
            "deg_in_sign": round(longitude % 30, 2),
        })

    try:
        raw_cusps = [float(item.strip()) for item in args.cusps.split(",")]
    except ValueError as exc:
        raise InputError("cusps must be 12 comma-separated longitudes") from exc
    if len(raw_cusps) != 12:
        raise InputError(f"cusps requires exactly 12 longitudes, received {len(raw_cusps)}")
    if any(not math.isfinite(value) or not 0 <= value < 360 for value in raw_cusps):
        raise InputError("each cusp longitude must be finite and in [0, 360)")
    if len(set(raw_cusps)) != 12:
        raise InputError("cusp longitudes must be distinct")
    offsets = [(longitude - args.asc) % 360.0 for longitude in raw_cusps]
    if len(set(offsets)) != 12:
        raise InputError("cusp offsets must be distinct")

    cusp_lines = []
    for house, (longitude, offset) in enumerate(zip(raw_cusps, offsets), start=1):
        inner = _point(args.cx, args.cy, args.r * 0.55, offset)
        outer = _point(args.cx, args.cy, args.r, offset)
        cusp_lines.append({
            "house": house,
            "longitude": longitude,
            "offset_deg": round(offset, 2),
            "x1": inner[0],
            "y1": inner[1],
            "x2": outer[0],
            "y2": outer[1],
        })
    return {
        "type": "wheel",
        "cx": args.cx,
        "cy": args.cy,
        "r": args.r,
        "asc": args.asc,
        "cusps": raw_cusps,
        "planets": planets,
        "cusp_lines": cusp_lines,
    }


def cmd_timeline(args: argparse.Namespace) -> dict[str, Any]:
    if args.end <= args.start:
        raise InputError("end must be greater than start")
    if args.step <= 0:
        raise InputError("step must be greater than zero")
    if args.x1 <= args.x0:
        raise InputError("x1 must be greater than x0")
    span = args.end - args.start

    def x_of(value: float) -> float:
        return args.x0 + (value - args.start) / span * (args.x1 - args.x0)

    ticks = []
    value = args.start
    while value <= args.end + 1e-9:
        ticks.append({"value": round(value, 2), "x": round(x_of(value), 2)})
        value += args.step
    result = {
        "type": "timeline",
        "x0": args.x0,
        "x1": args.x1,
        "start": args.start,
        "end": args.end,
        "ticks": ticks,
    }
    if args.now is not None:
        if args.now < args.start or args.now > args.end:
            result["now"] = {"value": args.now, "x": None, "status": "outside_range"}
        else:
            result["now"] = {"value": args.now, "x": round(x_of(args.now), 2), "status": "inside_range"}
    return result

def cmd_arc(args: argparse.Namespace) -> dict[str, Any]:
    _validate_range(0.0, args.max, args.value, "value")
    if args.r <= 0:
        raise InputError("r must be greater than zero")
    sweep = args.sweep_deg * args.value / args.max
    start = math.radians(args.start_deg)
    end = math.radians(args.start_deg + sweep)
    x1 = round(args.cx + args.r * math.cos(start), 2)
    y1 = round(args.cy - args.r * math.sin(start), 2)
    x2 = round(args.cx + args.r * math.cos(end), 2)
    y2 = round(args.cy - args.r * math.sin(end), 2)
    large = 1 if abs(sweep) > 180 else 0
    sweep_flag = 1 if args.sweep_deg > 0 else 0
    path = f"M {x1} {y1} A {args.r} {args.r} 0 {large} {sweep_flag} {x2} {y2}"
    return {
        "type": "arc",
        "value": args.value,
        "max": args.max,
        "fraction": round(args.value / args.max, 2),
        "start_point": [x1, y1],
        "end_point": [x2, y2],
        "path_d": path,
    }


def _load_pairs(raw: str) -> list[dict[str, Any]]:
    def reject_constant(value: str):
        raise InputError(f"non-finite JSON number is not allowed: {value}")
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise InputError(f"duplicate pairs JSON key: {key}")
            result[key] = value
        return result

    try:
        data = json.loads(raw, parse_constant=reject_constant, object_pairs_hook=reject_duplicates)
    except (json.JSONDecodeError, InputError) as exc:
        raise InputError(f"invalid pairs JSON: {exc}") from exc
    if not isinstance(data, list):
        raise InputError("pairs JSON must be an array")
    return data


def cmd_dumbbell(args: argparse.Namespace) -> dict[str, Any]:
    if args.maximum <= args.minimum:
        raise InputError("max must be greater than min")
    if args.x1 <= args.x0:
        raise InputError("x1 must be greater than x0")
    pairs = _load_pairs(args.pairs)
    output = []
    seen_functions: set[str] = set()
    for index, row in enumerate(pairs):
        path = f"pairs[{index}]"
        if not isinstance(row, dict):
            raise InputError(f"{path} must be an object")
        function = row.get("function")
        left_key = row.get("left_key")
        right_key = row.get("right_key")
        if not all(isinstance(value, str) and value for value in (function, left_key, right_key)):
            raise InputError(f"{path} requires non-empty function, left_key and right_key")
        if function in seen_functions:
            raise InputError(f"duplicate function: {function}")
        seen_functions.add(function)
        left = _checked_endpoint(row.get("left"), args.minimum, args.maximum, f"{path}.left")
        right = _checked_endpoint(row.get("right"), args.minimum, args.maximum, f"{path}.right")
        item: dict[str, Any] = {
            "function": function,
            "left_key": left_key,
            "right_key": right_key,
        }
        if left is not None:
            item["left"] = left
            item["left_x"] = round(args.x0 + (left - args.minimum) / (args.maximum - args.minimum) * (args.x1 - args.x0), 2)
        if right is not None:
            item["right"] = right
            item["right_x"] = round(args.x0 + (right - args.minimum) / (args.maximum - args.minimum) * (args.x1 - args.x0), 2)
        if left is None or right is None:
            item["status"] = "missing_endpoint"
            item["missing"] = [key for key, value in (("left", left), ("right", right)) if value is None]
        else:
            item["status"] = "complete"
            item["delta"] = right - left
            item["line"] = {"x1": item["left_x"], "x2": item["right_x"]}
        output.append(item)
    return {
        "type": "dumbbell",
        "min": args.minimum,
        "max": args.maximum,
        "x0": args.x0,
        "x1": args.x1,
        "pairs": output,
    }


def _checked_endpoint(value: Any, minimum: float, maximum: float, path: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{path} must be a finite number or null")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise InputError(f"{path} must be finite") from exc
    if not math.isfinite(number) or number < minimum or number > maximum:
        raise InputError(f"{path} must be finite and within [{minimum}, {maximum}]")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True, parser_class=JsonArgumentParser)

    radar = sub.add_parser("radar")
    radar.add_argument("--values", required=True)
    radar.add_argument("--max", type=finite_float, required=True)
    radar.add_argument("--cx", type=finite_float, default=200.0)
    radar.add_argument("--cy", type=finite_float, default=200.0)
    radar.add_argument("--rmax", type=finite_float, default=150.0)

    wheel = sub.add_parser("wheel")
    wheel.add_argument("--cusps", required=True)
    wheel.add_argument("--asc", type=finite_float, required=True)
    wheel.add_argument("--planets", required=True)
    wheel.add_argument("--cx", type=finite_float, default=200.0)
    wheel.add_argument("--cy", type=finite_float, default=200.0)
    wheel.add_argument("--r", type=finite_float, default=140.0)

    timeline = sub.add_parser("timeline")
    timeline.add_argument("--start", type=finite_float, required=True)
    timeline.add_argument("--end", type=finite_float, required=True)
    timeline.add_argument("--step", type=finite_float, default=10.0)
    timeline.add_argument("--now", type=finite_float)
    timeline.add_argument("--x0", type=finite_float, default=40.0)
    timeline.add_argument("--x1", type=finite_float, default=660.0)

    arc = sub.add_parser("arc")
    arc.add_argument("--value", type=finite_float, required=True)
    arc.add_argument("--max", type=finite_float, required=True)
    arc.add_argument("--cx", type=finite_float, default=200.0)
    arc.add_argument("--cy", type=finite_float, default=200.0)
    arc.add_argument("--r", type=finite_float, default=120.0)
    arc.add_argument("--start-deg", dest="start_deg", type=finite_float, default=180.0)
    arc.add_argument("--sweep-deg", dest="sweep_deg", type=finite_float, default=180.0)

    dumbbell = sub.add_parser("dumbbell")
    dumbbell.add_argument("--pairs", required=True)
    dumbbell.add_argument("--min", dest="minimum", type=finite_float, required=True)
    dumbbell.add_argument("--max", dest="maximum", type=finite_float, required=True)
    dumbbell.add_argument("--x0", type=finite_float, default=40.0)
    dumbbell.add_argument("--x1", type=finite_float, default=660.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    function = {
        "radar": cmd_radar,
        "wheel": cmd_wheel,
        "timeline": cmd_timeline,
        "arc": cmd_arc,
        "dumbbell": cmd_dumbbell,
    }[args.cmd]
    try:
        result = function(args)
        serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    except (InputError, ValueError) as exc:
        print(f"chart_data: {exc}", file=sys.stderr)
        json.dump(
            {"status": "error", "error": {"code": "invalid_input", "path": "$", "message": str(exc)}},
            sys.stdout,
            ensure_ascii=False,
        )
        print(file=sys.stdout)
        return 2
    sys.stdout.write(serialized + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
