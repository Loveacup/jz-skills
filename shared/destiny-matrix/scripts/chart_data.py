#!/usr/bin/env python3
"""chart_data.py — 图表坐标计算辅助（v4，V4_PLAN §3.3）

只算数据与坐标，不出成图：视觉呈现（配色/标注/图注/比喻元素）由 book-writer 决定。
公式与 references/chart-patterns.md 各模式节保持一致（P01 雷达 / P07 星盘轮 / P11 时间轴 / P04 弧线）。

用法（均输出 JSON 到 stdout）：
  # P01 八轴雷达：顶点坐标 + polygon points 字符串
  python3 chart_data.py radar --values "Ni=21,Ne=14,Fi=23,Fe=12,Ti=15,Te=8,Si=16,Se=9" \
      [--max 25] [--cx 200] [--cy 200] [--rmax 150]

  # P07 星盘轮：行星经度 → 轮上 x,y（ASC 固定在左侧 9 点位）
  python3 chart_data.py wheel --asc 267.87 \
      --planets "Sun=187.2,Moon=95.4,Mercury=201.1" [--cx 200] [--cy 200] [--r 140]

  # P11 时间轴：年龄/年份区间 → 等距刻度 x 坐标（含当前位置标记）
  python3 chart_data.py timeline --start 4 --end 53 --step 10 [--now 24] \
      [--x0 40] [--x1 660]

  # P04 弧线/仪表盘：数值 → 圆弧端点与 SVG arc path
  python3 chart_data.py arc --value 62 [--max 100] [--cx 200] [--cy 200] [--r 120] \
      [--start-deg 180] [--sweep-deg 180]
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def _round(v: float) -> float:
    return round(v, 2)


def parse_kv(s: str) -> "list[tuple[str, float]]":
    out = []
    seen = set()
    for item in s.split(","):
        item = item.strip()
        if not item or item.count("=") != 1:
            raise ValueError("'%s' 不是 key=value 形式" % item)
        k, v = (part.strip() for part in item.split("=", 1))
        if not k or not v:
            raise ValueError("'%s' 不是有效的 key=value" % item)
        if k in seen:
            raise ValueError("标签重复: %s" % k)
        try:
            number = float(v)
        except ValueError:
            raise ValueError("'%s' 的值不是数字" % item)
        if not math.isfinite(number):
            raise ValueError("'%s' 的值必须是有限数字" % item)
        seen.add(k)
        out.append((k, number))
    return out


def finite_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("必须是数字")
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("必须是有限数字")
    return number


def cmd_radar(a) -> dict:
    values = parse_kv(a.values)
    n = len(values)
    if n < 3:
        raise SystemExit("错误：雷达图至少 3 轴")
    axes, pts = [], []
    for i, (label, score) in enumerate(values):
        theta = 2 * math.pi * i / n  # 0 = 正上方，顺时针
        r = max(0.0, min(score, a.max)) / a.max * a.rmax
        x = a.cx + r * math.sin(theta)
        y = a.cy - r * math.cos(theta)
        ax_x = a.cx + a.rmax * math.sin(theta)
        ax_y = a.cy - a.rmax * math.cos(theta)
        lb_x = a.cx + (a.rmax + 22) * math.sin(theta)
        lb_y = a.cy - (a.rmax + 22) * math.cos(theta)
        axes.append({
            "label": label, "score": score,
            "x": _round(x), "y": _round(y),
            "axis_end": [_round(ax_x), _round(ax_y)],
            "label_pos": [_round(lb_x), _round(lb_y)],
        })
        pts.append(f"{_round(x)},{_round(y)}")
    grid = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        ring = []
        for i in range(n):
            theta = 2 * math.pi * i / n
            ring.append(f"{_round(a.cx + a.rmax * frac * math.sin(theta))},"
                        f"{_round(a.cy - a.rmax * frac * math.cos(theta))}")
        grid.append({"fraction": frac, "points": " ".join(ring)})
    return {"type": "radar", "cx": a.cx, "cy": a.cy, "rmax": a.rmax, "max": a.max,
            "axes": axes, "polygon_points": " ".join(pts), "grid_rings": grid}


def cmd_wheel(a) -> dict:
    # chart-patterns P07：offset=(λ−λ_ASC) mod 360；ASC 在 9 点位，黄道逆时针
    planets = []
    for label, lon in parse_kv(a.planets):
        offset = (lon - a.asc) % 360.0
        rad = math.radians(offset)
        x = a.cx - a.r * math.cos(rad)
        y = a.cy + a.r * math.sin(rad)
        lb = a.r + 20
        planets.append({
            "label": label, "longitude": lon, "offset_deg": _round(offset),
            "x": _round(x), "y": _round(y),
            "label_pos": [_round(a.cx - lb * math.cos(rad)), _round(a.cy + lb * math.sin(rad))],
            "sign_index": int(lon // 30) % 12,  # 0=白羊 … 11=双鱼
            "deg_in_sign": _round(lon % 30),
        })
    cusps = []
    for i in range(12):
        rad = math.radians((i * 30) % 360)
        cusps.append({
            "house": i + 1,
            "x1": _round(a.cx - (a.r * 0.55) * math.cos(rad)),
            "y1": _round(a.cy + (a.r * 0.55) * math.sin(rad)),
            "x2": _round(a.cx - a.r * math.cos(rad)),
            "y2": _round(a.cy + a.r * math.sin(rad)),
        })
    return {"type": "wheel", "cx": a.cx, "cy": a.cy, "r": a.r, "asc": a.asc,
            "planets": planets, "whole_sign_cusp_lines": cusps}


def cmd_timeline(a) -> dict:
    if a.end <= a.start:
        raise SystemExit("错误：end 必须大于 start")
    span = a.end - a.start

    def x_of(v: float) -> float:
        return a.x0 + (v - a.start) / span * (a.x1 - a.x0)

    ticks = []
    v = a.start
    while v <= a.end + 1e-9:
        ticks.append({"value": _round(v), "x": _round(x_of(v))})
        v += a.step
    out = {"type": "timeline", "x0": a.x0, "x1": a.x1,
           "start": a.start, "end": a.end, "ticks": ticks}
    if a.now is not None:
        out["now"] = {"value": a.now, "x": _round(x_of(a.now))}
    return out


def cmd_arc(a) -> dict:
    frac = max(0.0, min(a.value / a.max, 1.0))
    start = math.radians(a.start_deg)
    end = math.radians(a.start_deg + a.sweep_deg * frac)

    def pt(rad: float):
        return _round(a.cx + a.r * math.cos(rad)), _round(a.cy - a.r * math.sin(rad))

    x1, y1 = pt(start)
    x2, y2 = pt(end)
    large = 1 if abs(a.sweep_deg * frac) > 180 else 0
    sweep_flag = 1 if a.sweep_deg > 0 else 0
    path = f"M {x1} {y1} A {a.r} {a.r} 0 {large} {sweep_flag} {x2} {y2}"
    return {"type": "arc", "value": a.value, "max": a.max, "fraction": _round(frac),
            "start_point": [x1, y1], "end_point": [x2, y2], "path_d": path}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("radar")
    r.add_argument("--values", required=True)
    r.add_argument("--max", type=finite_float, default=25.0)
    r.add_argument("--cx", type=finite_float, default=200.0)
    r.add_argument("--cy", type=finite_float, default=200.0)
    r.add_argument("--rmax", type=finite_float, default=150.0)

    w = sub.add_parser("wheel")
    w.add_argument("--asc", type=finite_float, required=True)
    w.add_argument("--planets", required=True)
    w.add_argument("--cx", type=finite_float, default=200.0)
    w.add_argument("--cy", type=finite_float, default=200.0)
    w.add_argument("--r", type=finite_float, default=140.0)

    t = sub.add_parser("timeline")
    t.add_argument("--start", type=finite_float, required=True)
    t.add_argument("--end", type=finite_float, required=True)
    t.add_argument("--step", type=finite_float, default=10.0)
    t.add_argument("--now", type=finite_float, default=None)
    t.add_argument("--x0", type=finite_float, default=40.0)
    t.add_argument("--x1", type=finite_float, default=660.0)

    c = sub.add_parser("arc")
    c.add_argument("--value", type=finite_float, required=True)
    c.add_argument("--max", type=finite_float, default=100.0)
    c.add_argument("--cx", type=finite_float, default=200.0)
    c.add_argument("--cy", type=finite_float, default=200.0)
    c.add_argument("--r", type=finite_float, default=120.0)
    c.add_argument("--start-deg", dest="start_deg", type=finite_float, default=180.0)
    c.add_argument("--sweep-deg", dest="sweep_deg", type=finite_float, default=180.0)

    a = p.parse_args()
    try:
        if a.cmd == "timeline" and a.step <= 0:
            p.error("--step 必须大于 0")
        if a.cmd in ("radar", "arc") and a.max <= 0:
            p.error("--max 必须大于 0")
        fn = {"radar": cmd_radar, "wheel": cmd_wheel,
              "timeline": cmd_timeline, "arc": cmd_arc}[a.cmd]
        result = fn(a)
    except ValueError as e:
        p.error(str(e))
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
