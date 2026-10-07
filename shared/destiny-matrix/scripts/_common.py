#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命盘计算共享时区、历法、太阳时、坐标和相位工具。"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date as _date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    import geonamescache
    _HAS_GC = True
except ImportError:
    _HAS_GC = False

try:
    from timezonefinder import TimezoneFinder
    _HAS_TF = True
except ImportError:
    _HAS_TF = False


# 单例初始化（首次调用时再加载，避免脚本启动开销）
_GC = None
_TF = None


def _get_gc():
    global _GC
    if _GC is None and _HAS_GC:
        _GC = geonamescache.GeonamesCache()
    return _GC


def _get_tf():
    global _TF
    if _TF is None and _HAS_TF:
        _TF = TimezoneFinder()
    return _TF


# ---------------------------------------------------------------------------
# 时辰索引
# ---------------------------------------------------------------------------

def hour_to_idx(hour: int, minute: int = 0) -> int:
    """时分→时辰索引（0-11，子=0；23:00 后归早子时）"""
    h = hour + minute / 60
    if h < 1: return 0
    if h < 3: return 1
    if h < 5: return 2
    if h < 7: return 3
    if h < 9: return 4
    if h < 11: return 5
    if h < 13: return 6
    if h < 15: return 7
    if h < 17: return 8
    if h < 19: return 9
    if h < 21: return 10
    if h < 23: return 11
    return 0


HOUR_BRANCHES = '子丑寅卯辰巳午未申酉戌亥'


# ---------------------------------------------------------------------------
# 经纬度 / 时区格式化
# ---------------------------------------------------------------------------

def format_coord(lat: float, lon: float) -> str:
    """经纬度格式化，自动判定南北/东西
    例:
        format_coord(33.87, 151.21)  -> '33.87°N, 151.21°E'
        format_coord(-33.87, 151.21) -> '33.87°S, 151.21°E'
        format_coord(40.71, -74.01)  -> '40.71°N, 74.01°W'
    """
    ns = 'N' if lat >= 0 else 'S'
    ew = 'E' if lon >= 0 else 'W'
    return f'{abs(lat):.2f}°{ns}, {abs(lon):.2f}°{ew}'


def format_tz(tz_hours: float) -> str:
    """时区格式化：UTC+8 / UTC-5 / UTC+5.5 / UTC+5.75"""
    sign = '+' if tz_hours >= 0 else '-'
    abs_h = abs(tz_hours)
    if abs_h == int(abs_h):
        return f'UTC{sign}{int(abs_h)}'
    # 保留必要小数（去尾零）
    s = f'{abs_h:g}'
    return f'UTC{sign}{s}'


class InputError(ValueError):
    """输入违反明确字段/取值约束。"""

    def __init__(self, code: str, path: str, message: str):
        self.code, self.path, self.message = code, path, message
        super().__init__(message)


class CalcError(RuntimeError):
    """输入合法但计算或依赖执行失败。"""

    def __init__(self, code: str, path: str, message: str):
        self.code, self.path, self.message = code, path, message
        super().__init__(message)


ASPECT_PROFILES = {
    "standard-v1": {
        "conjunction": 8.0, "opposition": 8.0, "trine": 7.0,
        "square": 7.0, "sextile": 5.0,
    }
}


def resolve_orbs(custom: dict | None) -> tuple[str, dict]:
    profile = dict(ASPECT_PROFILES["standard-v1"])
    if custom is None:
        return "standard-v1", profile
    if not isinstance(custom, dict):
        raise InputError("invalid_orbs", "orbs", "容许度必须是对象")
    for key, value in custom.items():
        if key not in profile:
            raise InputError("unknown_orb", f"orbs.{key}", f"未知相位键: {key}")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise InputError("invalid_orb", f"orbs.{key}", "容许度必须为有限非负数")
        profile[key] = float(value)
    return "standard-v1", profile


# astro_calc 写出、synastry_calc 读取的星体表键名；两端共用，避免各写一份而失配
ASTRO_POSITIONS_KEY = "十大行星+北交+凯龙+莉莉丝"


def match_aspect(lon_a: float, lon_b: float, orbs: dict) -> dict | None:
    if not all(math.isfinite(x) for x in (lon_a, lon_b)):
        raise InputError("non_finite_angle", "angle", "黄经必须为有限数")
    keys = (("conjunction", 0.0), ("opposition", 180.0), ("trine", 120.0),
            ("square", 90.0), ("sextile", 60.0))
    delta = abs((lon_a - lon_b) % 360.0)
    angle = min(delta, 360.0 - delta)
    for name, exact in keys:
        orb = orbs[name]
        exact_diff = abs(angle - exact)
        if exact_diff <= orb:
            return {"aspect": name, "angle": angle, "orb_used": orb,
                    "exact_diff": exact_diff}
    return None


def _julian_to_gregorian(year: int, month: int, day: int,
                         hour: int = 0, minute: int = 0, second: float = 0.0) -> datetime:
    try:
        import swisseph as swe
        _validate_julian_date(year, month, day)
        jd = swe.julday(year, month, day,
                        hour + minute / 60 + second / 3600, swe.JUL_CAL)
        gy, gm, gd, gh = swe.revjul(jd, swe.GREG_CAL)
        whole = int(gh * 3600)
        return datetime(gy, gm, gd, whole // 3600, whole % 3600 // 60,
                       whole % 60) + timedelta(seconds=(gh * 3600 - whole))
    except (ValueError, OverflowError) as exc:
        raise InputError("invalid_date", "subject.date", str(exc)) from exc


def _validate_julian_date(year: int, month: int, day: int) -> None:
    if not 1 <= month <= 12:
        raise ValueError("儒略历月份无效")
    leap = year % 4 == 0
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if not 1 <= day <= days[month - 1]:
        raise ValueError("儒略历日期无效")


def _parse_wall(value: str, calendar: str, path: str) -> datetime:
    try:
        wall = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise InputError("invalid_datetime", path, "需要不含时区偏移的本地 ISO 日期时间") from exc
    if wall.tzinfo is not None:
        raise InputError("embedded_offset", path, "时间值不得夹带未确认 UTC 偏移")
    if calendar == "gregorian":
        return wall
    if calendar == "julian":
        return _julian_to_gregorian(wall.year, wall.month, wall.day,
                                    wall.hour, wall.minute,
                                    wall.second + wall.microsecond / 1_000_000)
    raise InputError("invalid_calendar", "subject.date_calendar",
                     "date_calendar 只能为 gregorian 或 julian")


def _zone_candidates(wall: datetime, zone: ZoneInfo) -> list[tuple[datetime, int, float]]:
    candidates = []
    for fold in (0, 1):
        aware = wall.replace(tzinfo=zone, fold=fold)
        utc = aware.astimezone(timezone.utc)
        back = utc.astimezone(zone)
        if back.replace(tzinfo=None) == wall and back.fold == fold:
            offset = aware.utcoffset()
            if offset is not None:
                entry = (utc, fold, offset.total_seconds() / 3600)
                if entry not in candidates:
                    candidates.append(entry)
    return candidates


def _solar_eot_seconds(utc_dt: datetime) -> float:
    import swisseph as swe
    utc = utc_dt.astimezone(timezone.utc)
    jd_ut = swe.julday(utc.year, utc.month, utc.day,
                       utc.hour + utc.minute / 60 +
                       (utc.second + utc.microsecond / 1_000_000) / 3600,
                       swe.GREG_CAL)
    return swe.time_equ(jd_ut) * 86400


def _term_datetime(utc_dt: datetime) -> datetime:
    return utc_dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)


def local_solar_to_lunar(value: datetime):
    """经 Swiss JD 将本地视太阳公历日期适配到 lunar-python 混合历法。"""
    try:
        import swisseph as swe
        from lunar_python import Solar
    except ImportError as exc:
        raise CalcError("missing_dependency", "calendar", str(exc)) from exc
    jd = swe.julday(value.year, value.month, value.day,
                    value.hour + value.minute / 60 +
                    (value.second + value.microsecond / 1e6) / 3600,
                    swe.GREG_CAL)
    return Solar.fromJulianDay(jd)


def lunar_date_to_lunar(lunar_date: dict):
    """解析公历化的原始农历日期；闰月以负月号传给 lunar-python。"""
    if not isinstance(lunar_date, dict) or set(lunar_date) != {
            "year", "month", "day", "is_leap_month"}:
        raise InputError("invalid_lunar_date", "subject.lunar_date",
                         "农历日期需包含 year/month/day/is_leap_month")
    year, month, day = (lunar_date.get("year"), lunar_date.get("month"),
                        lunar_date.get("day"))
    leap = lunar_date.get("is_leap_month")
    if (isinstance(year, bool) or not isinstance(year, int)
            or isinstance(month, bool) or not isinstance(month, int)
            or isinstance(day, bool) or not isinstance(day, int)
            or not 1 <= month <= 12 or not 1 <= day <= 30
            or not isinstance(leap, bool)):
        raise InputError("invalid_lunar_date", "subject.lunar_date",
                         "农历年/月/日范围无效，闰月标记必须为布尔值")
    try:
        from lunar_python import Lunar
    except ImportError as exc:
        raise CalcError("missing_dependency", "lunar_python", str(exc)) from exc
    signed_month = -month if leap else month
    try:
        lunar = Lunar.fromYmd(year, signed_month, day)
        solar = lunar.getSolar()
        solar_date = f"{solar.getYear():04d}-{solar.getMonth():02d}-{solar.getDay():02d}"
        julian_day = float(solar.getJulianDay())
    except Exception as exc:
        raise InputError("invalid_lunar_date", "subject.lunar_date",
                         f"农历日期或闰月无效: {exc}") from exc
    solar_calendar = ("julian" if (solar.getYear(), solar.getMonth(), solar.getDay())
                      < (1582, 10, 15) else "gregorian")
    try:
        from importlib.metadata import version
        library_version = version("lunar-python")
    except Exception:
        library_version = None
    conversion = {
        "input": {
            "year": year, "month": month, "day": day, "is_leap_month": leap,
        },
        "solar_date": solar_date, "solar_calendar": solar_calendar,
        "julian_day": julian_day, "library": "lunar-python",
        "library_version": library_version,
        "rule": "Lunar.fromYmd(year, -month if is_leap_month else month, day).getSolar()",
    }
    return lunar, conversion


def _civil_day_number(value: datetime) -> int:
    try:
        import swisseph as swe
    except ImportError as exc:
        raise CalcError("missing_dependency", "pyswisseph", str(exc)) from exc
    jd = swe.julday(value.year, value.month, value.day, 0, swe.GREG_CAL)
    return math.floor(jd + 0.5)


def _local_solar_datetimes(utc_dt: datetime, lon: float) -> tuple[datetime, datetime, float]:
    mean = utc_dt.replace(tzinfo=None) + timedelta(hours=lon / 15)
    eot = _solar_eot_seconds(utc_dt)
    return mean, mean + timedelta(seconds=eot), eot


def _resolve_place(subject: dict, time_input: dict, wall: datetime) -> tuple[float, float, str | None, str]:
    location = subject.get("location")
    lat, lon, city = subject.get("latitude"), subject.get("longitude"), subject.get("city")
    if isinstance(location, dict):
        lat = location.get("latitude", location.get("lat", lat))
        lon = location.get("longitude", location.get("lon", lon))
        city = location.get("city", location.get("name", city))
    elif isinstance(location, str):
        city = location
    if (lat is None) != (lon is None):
        raise InputError("incomplete_coordinates", "subject.location",
                         "经纬度必须同时提供")
    if lat is not None:
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in (lat, lon)):
            raise InputError("invalid_coordinates", "subject.location",
                             "经纬度必须为有限数")
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise InputError("invalid_coordinates", "subject.location",
                             "纬度/经度超出有效范围")
        name = time_input.get("timezone_name")
        if not name and isinstance(location, dict):
            name = location.get("timezone_name") or location.get("tz_name")
        if not name:
            try:
                tf = _get_tf()
                name = tf.timezone_at(lat=float(lat), lng=float(lon)) if tf else None
            except Exception:
                name = None
        return float(lat), float(lon), name, subject.get("location_source", "coordinates")
    if isinstance(city, str) and city.strip():
        found = resolve_location(city, ref_date=wall.date())
        if found is None:
            raise InputError("unknown_city", "subject.location", f"无法解析地点: {city}")
        if found.get("ambiguous"):
            raise InputError("ambiguous_city", "subject.location",
                             json.dumps(found["candidates"], ensure_ascii=False))
        return found["lat"], found["lon"], time_input.get("timezone_name") or found.get("tz_name"), "city_lookup"
    raise InputError("missing_location", "subject.location", "需要地点或经纬度")


def _actual_timezone_state(utc_dt: datetime, zone_name: str | None,
                           explicit_offset: float | None) -> tuple[float | None, int | None]:
    if zone_name:
        try:
            local = utc_dt.astimezone(ZoneInfo(zone_name))
        except ZoneInfoNotFoundError as exc:
            raise InputError("unknown_timezone", "time_input.timezone_name",
                             f"未知 IANA 时区: {zone_name}") from exc
        actual = local.utcoffset()
        if actual is None:
            raise InputError("unknown_offset", "time_input.timezone_name",
                             "无法取得出生瞬间 UTC 偏移")
        offset = actual.total_seconds() / 3600
        if explicit_offset is not None and abs(offset - explicit_offset) > 1e-9:
            raise InputError("offset_zone_conflict", "time_input.utc_offset_hours",
                             "显式 UTC 偏移与出生瞬间 IANA 时区不符")
        return offset, local.fold
    return (float(explicit_offset), None) if explicit_offset is not None else (None, None)

def normalize_birth_time(subject: dict, time_input: dict, *,
                         as_of: str | None = None) -> dict:
    """统一规范化出生时刻；非精确输入保留区间，不选代表性中点。"""
    if not isinstance(subject, dict) or not isinstance(time_input, dict):
        raise InputError("invalid_input", "input", "subject 与 time_input 必须为对象")
    calendar = subject.get("date_calendar", "gregorian")
    if calendar not in {"gregorian", "julian"}:
        raise InputError("invalid_calendar", "subject.date_calendar",
                         "date_calendar 只能为 gregorian 或 julian")
    raw_date = subject.get("birth_date")
    if raw_date is None:
        raw_date = subject.get("date")
    lunar_input = subject.get("lunar_date")
    lunar_conversion = None
    if lunar_input is not None:
        _, lunar_conversion = lunar_date_to_lunar(lunar_input)
    if raw_date:
        try:
            parsed_year = int(str(raw_date)[:4])
        except ValueError as exc:
            raise InputError("invalid_date", "subject.birth_date", "出生日期需为 ISO 日期") from exc
        if parsed_year < 1582 and "date_calendar" not in subject:
            raise InputError("calendar_confirmation_required", "subject.date_calendar",
                             "1582-10-15 以前必须明确声明公历或儒略历")
        if lunar_conversion:
            birth_wall = _parse_wall(f"{raw_date}T00:00:00", calendar,
                                     "subject.birth_date")
            birth_day = _civil_day_number(birth_wall)
            lunar_day = math.floor(lunar_conversion["julian_day"] + 0.5)
            if birth_day != lunar_day:
                raise InputError("date_conflict", "subject.lunar_date",
                                 "birth_date 与 lunar_date 转换后的公历日期不一致")
    precision = time_input.get("precision")
    if precision not in {"minute", "range", "branch", "unknown"}:
        raise InputError("invalid_precision", "time_input.precision", "未知时刻精度")
    start_text, end_text = time_input.get("start"), time_input.get("end")
    wall_calendar = calendar
    if not start_text:
        date_text = raw_date or (
            lunar_conversion.get("solar_date") if lunar_conversion else None)
        if precision == "minute":
            raise InputError("missing_time", "time_input.start", "minute 精度需要出生时间")
        if not date_text:
            raise InputError("missing_date", "subject.birth_date",
                             "需要 birth_date 或 lunar_date")
        if raw_date is None and lunar_conversion:
            wall_calendar = lunar_conversion["solar_calendar"]
        start_text = f"{date_text}T00:00:00"
    wall_start = _parse_wall(start_text, wall_calendar, "time_input.start")
    if lunar_conversion:
        start_day = _civil_day_number(wall_start)
        lunar_day = math.floor(lunar_conversion["julian_day"] + 0.5)
        if start_day != lunar_day:
            raise InputError("date_conflict", "time_input.start",
                             "time_input.start 的日期与 lunar_date 对应公历日不一致")
    if precision == "minute" and time_input.get("end") is not None:
        raise InputError("unexpected_end", "time_input.end", "minute 精度只提供 start")
    if precision == "range":
        if not end_text:
            raise InputError("missing_end", "time_input.end", "range 精度需要闭区间终点")
        wall_end = _parse_wall(end_text, wall_calendar, "time_input.end")
        if wall_end <= wall_start:
            raise InputError("invalid_range", "time_input", "区间终点必须晚于起点")
    elif precision == "branch":
        branch = time_input.get("branch_label")
        if branch not in HOUR_BRANCHES:
            raise InputError("missing_branch", "time_input.branch_label", "branch 精度需要有效地支")
        if raw_date is None and lunar_conversion is None:
            raise InputError("missing_date", "subject.birth_date",
                             "时辰输入需要 birth_date 或 lunar_date")
        start_hour = 23 if branch == "子" else HOUR_BRANCHES.index(branch) * 2 - 1
        wall_start = wall_start.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        wall_end = wall_start + timedelta(hours=2)
    elif precision == "unknown":
        if raw_date is None and lunar_conversion is None:
            raise InputError("missing_date", "subject.birth_date",
                             "unknown 精度需要 birth_date 或 lunar_date")
        wall_start = wall_start.replace(hour=0, minute=0, second=0, microsecond=0)
        wall_end = wall_start + timedelta(days=1)
    else:
        wall_end = None

    basis = time_input.get("clock_basis", "civil")
    if basis not in {"civil", "local_mean_solar", "local_apparent_solar", "unknown"}:
        raise InputError("invalid_clock_basis", "time_input.clock_basis", "未知钟表口径")
    lat, lon, inferred_zone, location_source = _resolve_place(subject, time_input, wall_start)
    location = subject.get("location")
    location_zone = location.get("timezone_name") if isinstance(location, dict) else None
    explicit_zone_name = time_input.get("timezone_name") or location_zone
    explicit_offset = time_input.get("utc_offset_hours")
    zone_name = explicit_zone_name or (inferred_zone if explicit_offset is None else None)
    if explicit_offset is not None and (isinstance(explicit_offset, bool)
            or not isinstance(explicit_offset, (int, float))
            or not math.isfinite(explicit_offset) or not -14 <= explicit_offset <= 14):
        raise InputError("invalid_offset", "time_input.utc_offset_hours", "UTC 偏移必须为有限的 -14 至 +14 小时")
    if time_input.get("fold") not in (None, 0, 1):
        raise InputError("invalid_fold", "time_input.fold", "fold 只能为 0、1 或 null")

    def convert(wall: datetime, fold: int | None = None) -> tuple[datetime, float, int | None]:
        if basis == "unknown":
            raise InputError("unknown_clock_basis", "time_input.clock_basis",
                             "钟表口径未知，无法选定唯一 UTC 瞬间")
        if basis == "local_mean_solar":
            utc = (wall - timedelta(hours=lon / 15)).replace(tzinfo=timezone.utc)
            return utc, lon / 15, None
        if basis == "local_apparent_solar":
            utc = (wall - timedelta(hours=lon / 15)).replace(tzinfo=timezone.utc)
            for _ in range(5):
                utc = (wall - timedelta(hours=lon / 15) -
                       timedelta(seconds=_solar_eot_seconds(utc))).replace(tzinfo=timezone.utc)
            return utc, lon / 15, None
        if zone_name:
            try:
                zone = ZoneInfo(zone_name)
            except ZoneInfoNotFoundError as exc:
                raise InputError("unknown_timezone", "time_input.timezone_name",
                                 f"未知 IANA 时区: {zone_name}") from exc
            candidates = _zone_candidates(wall, zone)
            if not candidates:
                raise InputError("nonexistent_local_time", "time_input.start",
                                 f"{wall.isoformat()} 在 {zone_name} 中不存在")
            requested_fold = time_input.get("fold") if fold is None else fold
            if explicit_offset is not None:
                candidates = [c for c in candidates if abs(c[2] - explicit_offset) < 1e-9]
                if not candidates:
                    raise InputError("offset_zone_conflict", "time_input.utc_offset_hours",
                                     "显式 UTC 偏移与该时刻 IANA 时区不符")
            if requested_fold is not None:
                candidates = [c for c in candidates if c[1] == requested_fold]
            if len(candidates) > 1:
                raise InputError("ambiguous_local_time", "time_input.fold",
                                 "重复本地时间必须提供 fold 或匹配的显式 UTC 偏移")
            if not candidates:
                raise InputError("offset_zone_conflict", "time_input",
                                 "fold/UTC 偏移与 IANA 时区候选不符")
            utc, resolved_fold, offset = candidates[0]
            return utc, offset, resolved_fold
        if explicit_offset is None:
            raise InputError("missing_timezone", "time_input",
                             "无 IANA 时区时必须显式提供 utc_offset_hours")
        utc = (wall - timedelta(hours=explicit_offset)).replace(tzinfo=timezone.utc)
        return utc, float(explicit_offset), None

    if precision == "minute":
        utc, offset, fold = convert(wall_start)
        if basis != "civil":
            offset, fold = _actual_timezone_state(utc, zone_name, explicit_offset)
        start_utc = utc
        intervals = [{
            "start_utc": utc.isoformat().replace("+00:00", "Z"),
            "end_utc": utc.isoformat().replace("+00:00", "Z"),
            "utc_offset_hours": offset, "fold": fold,
        }]
    else:
        intervals = _interval_utc_segments(
            wall_start, wall_end, basis=basis, zone_name=zone_name,
            explicit_offset=explicit_offset, fold=time_input.get("fold"),
            lon=lon, closed=precision == "range",
        )
        if not intervals:
            raise InputError("empty_interval", "time_input", "出生时间区间内没有有效瞬间")
        start_utc = datetime.fromisoformat(
            intervals[0]["start_utc"].replace("Z", "+00:00"))
        offsets = {row["utc_offset_hours"] for row in intervals}
        folds = {row["fold"] for row in intervals}
        offset = next(iter(offsets)) if len(offsets) == 1 else None
        fold = next(iter(folds)) if len(folds) == 1 else None
    if precision == "minute":
        local_mean, local_apparent, eot_seconds = _local_solar_datetimes(start_utc, lon)
    else:
        local_mean = local_apparent = eot_seconds = None
    return {
        "input": {"subject": subject, "time_input": time_input},
        "calendar": wall_calendar, "precision": precision,
        "lunar_date_conversion": lunar_conversion,
        "location": {"latitude": lat, "longitude": lon, "source": location_source},
        "timezone": {"name": zone_name, "resolution": (
            "explicit_iana" if explicit_zone_name else
            "coordinates" if inferred_zone and explicit_offset is None else "explicit_offset"),
            "utc_offset_hours": offset, "fold": fold},
        "utc_instant": start_utc.isoformat().replace("+00:00", "Z") if precision == "minute" else None,
        "term_datetime": _term_datetime(start_utc).isoformat(timespec="microseconds") if precision == "minute" else None,
        "local_mean_datetime": local_mean.isoformat(timespec="microseconds") if local_mean else None,
        "local_apparent_datetime": local_apparent.isoformat(timespec="microseconds") if local_apparent else None,
        "equation_of_time_seconds": eot_seconds,
        "candidate_intervals": intervals,
        "analysis_as_of": as_of,
        "methods": {"solar_time": "Swiss Ephemeris time_equ(jd_ut)",
                    "term_timezone": "fixed UTC+08:00", "dependency": "pyswisseph",
                    "lunar_date_conversion": (
                        lunar_conversion and {
                            "library": lunar_conversion["library"],
                            "version": lunar_conversion["library_version"],
                            "rule": lunar_conversion["rule"],
                        })},
        "limitations": [] if precision == "minute" else
            ["非精确时刻；不得输出确定本命占星宫位或代表性起运时点"],
    }


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _offset_minutes(zone: ZoneInfo, instant: datetime) -> tuple[int, int]:
    local = instant.astimezone(zone)
    offset = local.utcoffset()
    if offset is None:
        raise InputError("unknown_offset", "time_input.timezone_name",
                         "无法取得出生时刻 UTC 偏移")
    return int(offset.total_seconds()), local.fold


def _zone_interval_segments(start: datetime, end: datetime, zone: ZoneInfo,
                            explicit_offset: float | None,
                            requested_fold: int | None,
                            *, closed: bool) -> list[dict]:
    limit = end + timedelta(microseconds=1) if closed else end

    def resolve_edge(wall: datetime, *, is_start: bool) -> datetime | None:
        candidates = _zone_candidates(wall, zone)
        if not candidates:
            if is_start and (explicit_offset is not None or requested_fold is not None):
                raise InputError("nonexistent_local_time", "time_input.start",
                                 f"{wall.isoformat()} 在 {zone.key} 中不存在")
            return None
        selected = candidates
        if requested_fold is not None:
            selected = [row for row in selected if row[1] == requested_fold]
        if is_start and explicit_offset is not None:
            selected = [row for row in selected
                        if abs(row[2] - explicit_offset) < 1e-9]
        elif not is_start and len(selected) > 1 and explicit_offset is not None:
            selected = [row for row in selected
                        if abs(row[2] - explicit_offset) < 1e-9]
        if not selected:
            code = "offset_zone_conflict" if explicit_offset is not None else "fold_conflict"
            raise InputError(code, "time_input",
                             "fold/UTC 偏移与 IANA 时区候选不符")
        if len(selected) > 1:
            raise InputError("ambiguous_local_time", "time_input.fold",
                             "重复本地时间必须提供 fold 或匹配的显式 UTC 偏移")
        return selected[0][0]

    start_utc = resolve_edge(start, is_start=True)
    end_utc = resolve_edge(end, is_start=False)
    search_start = (start - timedelta(days=1)).replace(tzinfo=timezone.utc)
    search_end = (limit + timedelta(days=1)).replace(tzinfo=timezone.utc)
    step = timedelta(minutes=30)
    boundaries = [search_start]
    left = search_start
    left_offset, _ = _offset_minutes(zone, left)
    probe = left + step
    while probe < search_end:
        probe_offset, _ = _offset_minutes(zone, probe)
        if probe_offset != left_offset:
            low, high = left, probe
            while (high - low) > timedelta(microseconds=1):
                middle = low + (high - low) / 2
                if _offset_minutes(zone, middle)[0] == left_offset:
                    low = middle
                else:
                    high = middle
            boundaries.append(high)
            left_offset, _ = _offset_minutes(zone, high)
            left = high
        else:
            left = probe
        probe += step
    boundaries.append(search_end)

    output = []
    for utc_start, utc_end in zip(boundaries, boundaries[1:]):
        offset_seconds, _ = _offset_minutes(zone, utc_start)
        offset = timedelta(seconds=offset_seconds)
        local_start = utc_start.replace(tzinfo=None) + offset
        local_end = utc_end.replace(tzinfo=None) + offset
        intersection_start = max(start, local_start)
        intersection_end = min(limit, local_end)
        if intersection_start >= intersection_end:
            continue
        actual_start = (intersection_start - offset).replace(tzinfo=timezone.utc)
        actual_end = (intersection_end - offset).replace(tzinfo=timezone.utc)
        if start_utc is not None:
            actual_start = max(actual_start, start_utc)
        if end_utc is not None:
            actual_end = min(actual_end, end_utc + (timedelta(microseconds=1) if closed
                                                     else timedelta(0)))
        if actual_start >= actual_end:
            continue
        local_actual_start = actual_start.astimezone(zone)
        local_actual_end = actual_end.astimezone(zone)
        output.append({
            "start_utc": _utc_text(actual_start), "end_utc": _utc_text(actual_end),
            "local_start": local_actual_start.replace(tzinfo=None).isoformat(timespec="microseconds"),
            "local_end": local_actual_end.replace(tzinfo=None).isoformat(timespec="microseconds"),
            "utc_offset_hours": offset_seconds / 3600,
            "fold": local_actual_start.fold, "end_inclusive": closed,
        })
    return sorted(output, key=lambda item: item["start_utc"])


def _interval_utc_segments(start: datetime, end: datetime, *, basis: str,
                           zone_name: str | None, explicit_offset: float | None,
                           fold: int | None, lon: float, closed: bool) -> list[dict]:
    if basis == "unknown":
        raise InputError("unknown_clock_basis", "time_input.clock_basis",
                         "钟表口径未知，无法选定唯一时间轴")
    if basis == "civil" and zone_name:
        try:
            zone = ZoneInfo(zone_name)
        except ZoneInfoNotFoundError as exc:
            raise InputError("unknown_timezone", "time_input.timezone_name",
                             f"未知 IANA 时区: {zone_name}") from exc
        return _zone_interval_segments(start, end, zone, explicit_offset, fold,
                                       closed=closed)
    limit = end + timedelta(microseconds=1) if closed else end
    if basis == "civil":
        if explicit_offset is None:
            raise InputError("missing_timezone", "time_input",
                             "无 IANA 时区时必须显式提供 utc_offset_hours")
        offset = timedelta(hours=explicit_offset)
    else:
        offset = timedelta(hours=lon / 15)

    def to_utc(wall: datetime) -> datetime:
        candidate = (wall - offset).replace(tzinfo=timezone.utc)
        if basis == "local_apparent_solar":
            for _ in range(5):
                candidate = (wall - offset -
                             timedelta(seconds=_solar_eot_seconds(candidate))).replace(
                                 tzinfo=timezone.utc)
        return candidate

    utc_start, utc_end = to_utc(start), to_utc(limit)
    if utc_start >= utc_end:
        return []
    actual_offset, actual_fold = _actual_timezone_state(
        utc_start, zone_name, explicit_offset)
    return [{
        "start_utc": _utc_text(utc_start), "end_utc": _utc_text(utc_end),
        "local_start": start.isoformat(timespec="microseconds"),
        "local_end": limit.isoformat(timespec="microseconds"),
        "utc_offset_hours": actual_offset,
        "fold": actual_fold, "end_inclusive": closed,
    }]


def candidate_intervals(subject: dict, time_input: dict, *, as_of: str | None = None) -> list[dict]:
    """返回本地精度区间内的时刻候选，不选择区间中点。"""
    return normalize_birth_time(subject, time_input, as_of=as_of)["candidate_intervals"]


def _apparent_at(utc_dt: datetime, longitude: float) -> datetime:
    return _local_solar_datetimes(utc_dt, longitude)[1]


def _solve_apparent_boundary(wall: datetime, longitude: float) -> datetime:
    estimate = (wall - timedelta(hours=longitude / 15)).replace(tzinfo=timezone.utc)
    low, high = estimate - timedelta(minutes=30), estimate + timedelta(minutes=30)
    while (high - low) > timedelta(milliseconds=100):
        middle = low + (high - low) / 2
        if _apparent_at(middle, longitude) < wall:
            low = middle
        else:
            high = middle
    return high


def _solar_term_boundaries(start_utc: datetime, end_utc: datetime) -> set[datetime]:
    try:
        from lunar_python import Solar
    except ImportError as exc:
        raise CalcError("missing_dependency", "lunar_python", str(exc)) from exc
    start_bjt = _term_datetime(start_utc)
    end_bjt = _term_datetime(end_utc)
    names = {"立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
             "立秋", "白露", "寒露", "立冬", "大雪", "小寒", "DA_XUE"}
    boundaries = set()
    for year in range(start_bjt.year - 1, end_bjt.year + 2):
        try:
            table = Solar.fromYmdHms(year, 6, 1, 12, 0, 0).getLunar().getJieQiTable()
        except Exception as exc:
            raise CalcError("unsupported_date", "time_input",
                            f"无法取得 {year} 年节气候选边界: {exc}") from exc
        for name, term in table.items():
            if name not in names:
                continue
            second = float(term.getSecond())
            whole = int(second)
            wall = datetime(term.getYear(), term.getMonth(), term.getDay(),
                            term.getHour(), term.getMinute(), whole,
                            round((second - whole) * 1_000_000))
            instant = wall.replace(tzinfo=timezone(timedelta(hours=8))).astimezone(timezone.utc)
            if start_utc < instant < end_utc:
                boundaries.add(instant)
    return boundaries


def _exact_context_at(context: dict, instant: datetime, offset: float,
                      fold: int | None, *, interval: dict | None = None) -> dict:
    import copy

    exact = copy.deepcopy(context)
    instant = instant.astimezone(timezone.utc)
    local_mean, local_apparent, eot_seconds = _local_solar_datetimes(
        instant, context["location"]["longitude"])
    zone_name = context.get("timezone", {}).get("name")
    if zone_name and context.get("input", {}).get("time_input", {}).get("clock_basis") == "civil":
        local = instant.astimezone(ZoneInfo(zone_name))
        offset = local.utcoffset().total_seconds() / 3600
        fold = local.fold
    exact.update({
        "precision": "minute",
        "utc_instant": _utc_text(instant),
        "term_datetime": _term_datetime(instant).isoformat(timespec="microseconds"),
        "local_mean_datetime": local_mean.isoformat(timespec="microseconds"),
        "local_apparent_datetime": local_apparent.isoformat(timespec="microseconds"),
        "equation_of_time_seconds": eot_seconds,
    })
    exact["timezone"] = {
        **exact.get("timezone", {}), "utc_offset_hours": offset, "fold": fold,
    }
    if interval:
        exact["candidate_intervals"] = [interval]
    else:
        exact["candidate_intervals"] = [{
            "start_utc": _utc_text(instant), "end_utc": _utc_text(instant),
            "utc_offset_hours": offset, "fold": fold,
        }]
    return exact


def candidate_contexts(time_context: dict) -> list[dict]:
    """Split uncertain input at DST, apparent-hour, and Jie boundaries, never at a midpoint."""
    if time_context.get("precision") == "minute":
        return []
    longitude = float(time_context["location"]["longitude"])
    output = []
    for source_interval in time_context.get("candidate_intervals", []):
        start = datetime.fromisoformat(source_interval["start_utc"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(source_interval["end_utc"].replace("Z", "+00:00"))
        if start >= end:
            continue
        local_start, local_end = _apparent_at(start, longitude), _apparent_at(end, longitude)
        boundaries = {start, end}
        hour = local_start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        while hour < local_end:
            candidate = _solve_apparent_boundary(hour, longitude)
            if start < candidate < end:
                boundaries.add(candidate)
            hour += timedelta(hours=1)
        boundaries.update(_solar_term_boundaries(start, end))
        ordered = sorted(boundaries)
        for left, right in zip(ordered, ordered[1:]):
            if left >= right:
                continue
            zone_name = time_context.get("timezone", {}).get("name")
            if zone_name and time_context.get("input", {}).get(
                    "time_input", {}).get("clock_basis") == "civil":
                local = left.astimezone(ZoneInfo(zone_name))
                offset = local.utcoffset().total_seconds() / 3600
                fold = local.fold
            else:
                offset = source_interval["utc_offset_hours"]
                fold = source_interval.get("fold")
            validity = {
                "start_utc": _utc_text(left), "end_utc": _utc_text(right),
                "end_inclusive": False,
            }
            interval = {
                **validity, "utc_offset_hours": offset, "fold": fold,
            }
            output.append({
                "validity": validity,
                "time_context": _exact_context_at(
                    time_context, left, offset, fold, interval=interval),
            })
        if source_interval.get("end_inclusive"):
            endpoint = end - timedelta(microseconds=1)
            offset, fold = (source_interval["utc_offset_hours"],
                            source_interval.get("fold"))
            zone_name = time_context.get("timezone", {}).get("name")
            if zone_name and time_context.get("input", {}).get(
                    "time_input", {}).get("clock_basis") == "civil":
                local = endpoint.astimezone(ZoneInfo(zone_name))
                offset, fold = local.utcoffset().total_seconds() / 3600, local.fold
            output.append({
                "validity": {"instant_utc": _utc_text(endpoint),
                             "end_inclusive": True},
                "time_context": _exact_context_at(time_context, endpoint, offset, fold),
            })
    return output


def resolve_birth_timezone(time_input: dict, location: dict, wall: datetime) -> dict:
    """根据本地出生日期时间解析 zoneinfo 真实 offset/fold（内部公用）。"""
    return normalize_birth_time(
        {"date": wall.date().isoformat(), "latitude": location["latitude"],
         "longitude": location["longitude"]},
        {**time_input, "precision": "minute", "start": wall.isoformat(timespec="seconds")},
    )
# ---------------------------------------------------------------------------
# 城市名解析（geonamescache 模糊匹配）
# ---------------------------------------------------------------------------

_ADMIN_SUFFIXES = ('特别行政区', '自治区', '自治州', '市', '县', '区', '省', '盟', '旗')

# 简繁字符级映射（覆盖常见城市用字）
_S2T = str.maketrans({
    '纽': '紐', '约': '約', '尔': '爾', '济': '濟', '罗': '羅', '亚': '亞',
    '兰': '蘭', '丽': '麗', '伦': '倫', '马': '馬', '门': '門', '岛': '島',
    '韩': '韓', '湾': '灣', '区': '區', '广': '廣', '东': '東', '汉': '漢',
    '宁': '寧', '苏': '蘇', '鲁': '魯', '齐': '齊', '阳': '陽', '阴': '陰',
    '滨': '濱', '辽': '遼', '业': '業',
})
_T2S = str.maketrans({
    '紐': '纽', '約': '约', '爾': '尔', '濟': '济', '羅': '罗', '亞': '亚',
    '蘭': '兰', '麗': '丽', '倫': '伦', '馬': '马', '門': '门', '島': '岛',
    '韓': '韩', '灣': '湾', '區': '区', '廣': '广', '東': '东', '漢': '汉',
    '寧': '宁', '蘇': '苏', '魯': '鲁', '齊': '齐', '陽': '阳', '陰': '阴',
    '濱': '滨', '遼': '辽', '業': '业',
})

# 常见城市别名（geonamescache 无别名/拼音命中时用）
_EXTRA_ALIASES = {
    '纽约': 'New York City', '紐約': 'New York City',
    '洛杉矶': 'Los Angeles', '洛杉磯': 'Los Angeles',
    '旧金山': 'San Francisco', '舊金山': 'San Francisco', '三藩市': 'San Francisco',
    '芝加哥': 'Chicago', '波士顿': 'Boston', '波士頓': 'Boston',
    '西雅图': 'Seattle', '西雅圖': 'Seattle',
    '休斯顿': 'Houston', '休斯敦': 'Houston',
    '多伦多': 'Toronto', '多倫多': 'Toronto',
    '温哥华': 'Vancouver', '溫哥華': 'Vancouver',
    '蒙特利尔': 'Montreal', '蒙特利爾': 'Montreal',
    '伦敦': 'London', '倫敦': 'London',
    '巴黎': 'Paris', '柏林': 'Berlin',
    '罗马': 'Rome', '羅馬': 'Rome',
    '马德里': 'Madrid', '馬德里': 'Madrid',
    '阿姆斯特丹': 'Amsterdam',
    '苏黎世': 'Zurich', '蘇黎世': 'Zurich',
    '维也纳': 'Vienna', '維也納': 'Vienna',
    '莫斯科': 'Moscow',
    '悉尼': 'Sydney', '雪梨': 'Sydney',
    '墨尔本': 'Melbourne', '墨爾本': 'Melbourne',
    '奥克兰': 'Auckland', '奧克蘭': 'Auckland',
    '东京': 'Tokyo', '東京': 'Tokyo',
    '大阪': 'Osaka',
    '首尔': 'Seoul', '首爾': 'Seoul',
    '新加坡': 'Singapore', '吉隆坡': 'Kuala Lumpur',
    '曼谷': 'Bangkok', '雅加达': 'Jakarta', '雅加達': 'Jakarta',
    '马尼拉': 'Manila', '馬尼拉': 'Manila',
    '清迈': 'Chiang Mai', '清邁': 'Chiang Mai',
    '迪拜': 'Dubai', '杜拜': 'Dubai',
    '台北': 'Taipei', '香港': 'Hong Kong',
    '澳门': 'Macau', '澳門': 'Macau',
    # 中国常见城市（防止 geonamescache 拼音匹配失败）
    '北京': 'Beijing', '上海': 'Shanghai', '广州': 'Guangzhou',
    '深圳': 'Shenzhen', '杭州': 'Hangzhou', '南京': 'Nanjing',
    '苏州': 'Suzhou', '成都': 'Chengdu', '重庆': 'Chongqing',
    '武汉': 'Wuhan', '西安': 'Xi’an', '天津': 'Tianjin',
}


# 离线 fallback：geonamescache 装不上或查不到时用
_OFFLINE_CITY_DB = {
    # 中国大陆主要城市
    '北京': (39.90, 116.41, 'Asia/Shanghai', 'CN'),
    '上海': (31.23, 121.47, 'Asia/Shanghai', 'CN'),
    '广州': (23.13, 113.26, 'Asia/Shanghai', 'CN'),
    '深圳': (22.54, 114.06, 'Asia/Shanghai', 'CN'),
    '杭州': (30.27, 120.16, 'Asia/Shanghai', 'CN'),
    '南京': (32.06, 118.78, 'Asia/Shanghai', 'CN'),
    '苏州': (31.30, 120.59, 'Asia/Shanghai', 'CN'),
    '成都': (30.66, 104.07, 'Asia/Shanghai', 'CN'),
    '重庆': (29.56, 106.55, 'Asia/Shanghai', 'CN'),
    '武汉': (30.59, 114.31, 'Asia/Shanghai', 'CN'),
    '西安': (34.27, 108.95, 'Asia/Shanghai', 'CN'),
    '天津': (39.13, 117.20, 'Asia/Shanghai', 'CN'),
    '青岛': (36.07, 120.38, 'Asia/Shanghai', 'CN'),
    '济南': (36.65, 117.00, 'Asia/Shanghai', 'CN'),
    '郑州': (34.75, 113.62, 'Asia/Shanghai', 'CN'),
    '长沙': (28.20, 112.97, 'Asia/Shanghai', 'CN'),
    '合肥': (31.83, 117.28, 'Asia/Shanghai', 'CN'),
    '福州': (26.07, 119.30, 'Asia/Shanghai', 'CN'),
    '厦门': (24.48, 118.09, 'Asia/Shanghai', 'CN'),
    '南昌': (28.68, 115.89, 'Asia/Shanghai', 'CN'),
    '昆明': (24.88, 102.83, 'Asia/Shanghai', 'CN'),
    '贵阳': (26.65, 106.63, 'Asia/Shanghai', 'CN'),
    '南宁': (22.82, 108.37, 'Asia/Shanghai', 'CN'),
    '海口': (20.04, 110.32, 'Asia/Shanghai', 'CN'),
    '兰州': (36.06, 103.84, 'Asia/Shanghai', 'CN'),
    '银川': (38.49, 106.23, 'Asia/Shanghai', 'CN'),
    '西宁': (36.62, 101.78, 'Asia/Shanghai', 'CN'),
    '乌鲁木齐': (43.83, 87.62, 'Asia/Urumqi', 'CN'),
    '太原': (37.87, 112.55, 'Asia/Shanghai', 'CN'),
    '石家庄': (38.04, 114.51, 'Asia/Shanghai', 'CN'),
    '哈尔滨': (45.80, 126.53, 'Asia/Shanghai', 'CN'),
    '长春': (43.82, 125.32, 'Asia/Shanghai', 'CN'),
    '沈阳': (41.81, 123.43, 'Asia/Shanghai', 'CN'),
    '大连': (38.91, 121.61, 'Asia/Shanghai', 'CN'),
    '宁波': (29.87, 121.55, 'Asia/Shanghai', 'CN'),
    '温州': (28.00, 120.65, 'Asia/Shanghai', 'CN'),
    '无锡': (31.49, 120.31, 'Asia/Shanghai', 'CN'),
    '常州': (31.81, 119.97, 'Asia/Shanghai', 'CN'),
    '徐州': (34.26, 117.18, 'Asia/Shanghai', 'CN'),
    '佛山': (23.02, 113.12, 'Asia/Shanghai', 'CN'),
    '东莞': (23.05, 113.75, 'Asia/Shanghai', 'CN'),
    '珠海': (22.27, 113.58, 'Asia/Shanghai', 'CN'),
    '香港': (22.32, 114.17, 'Asia/Hong_Kong', 'HK'),
    '澳门': (22.20, 113.55, 'Asia/Macau', 'MO'),
    '台北': (25.03, 121.57, 'Asia/Taipei', 'TW'),
    # 海外
    '东京': (35.68, 139.65, 'Asia/Tokyo', 'JP'),
    '首尔': (37.57, 126.98, 'Asia/Seoul', 'KR'),
    '新加坡': (1.35, 103.82, 'Asia/Singapore', 'SG'),
    '曼谷': (13.75, 100.50, 'Asia/Bangkok', 'TH'),
    '吉隆坡': (3.14, 101.69, 'Asia/Kuala_Lumpur', 'MY'),
    '雅加达': (-6.21, 106.85, 'Asia/Jakarta', 'ID'),
    '马尼拉': (14.60, 120.98, 'Asia/Manila', 'PH'),
    '清迈': (18.79, 98.99, 'Asia/Bangkok', 'TH'),
    '伦敦': (51.51, -0.13, 'Europe/London', 'GB'),
    '巴黎': (48.86, 2.35, 'Europe/Paris', 'FR'),
    '柏林': (52.52, 13.40, 'Europe/Berlin', 'DE'),
    '罗马': (41.90, 12.50, 'Europe/Rome', 'IT'),
    '马德里': (40.42, -3.70, 'Europe/Madrid', 'ES'),
    '阿姆斯特丹': (52.37, 4.90, 'Europe/Amsterdam', 'NL'),
    '苏黎世': (47.38, 8.55, 'Europe/Zurich', 'CH'),
    '维也纳': (48.21, 16.37, 'Europe/Vienna', 'AT'),
    '莫斯科': (55.76, 37.62, 'Europe/Moscow', 'RU'),
    '纽约': (40.71, -74.01, 'America/New_York', 'US'),
    '洛杉矶': (34.05, -118.24, 'America/Los_Angeles', 'US'),
    '芝加哥': (41.88, -87.63, 'America/Chicago', 'US'),
    '旧金山': (37.77, -122.42, 'America/Los_Angeles', 'US'),
    '波士顿': (42.36, -71.06, 'America/New_York', 'US'),
    '西雅图': (47.61, -122.33, 'America/Los_Angeles', 'US'),
    '多伦多': (43.65, -79.38, 'America/Toronto', 'CA'),
    '温哥华': (49.28, -123.12, 'America/Vancouver', 'CA'),
    '悉尼': (-33.87, 151.21, 'Australia/Sydney', 'AU'),
    '墨尔本': (-37.81, 144.96, 'Australia/Melbourne', 'AU'),
    '奥克兰': (-36.85, 174.76, 'Pacific/Auckland', 'NZ'),
}


def _normalize_query(name: str) -> list[str]:
    """生成多个候选查询字符串"""
    name = name.strip()
    candidates = []
    if name in _EXTRA_ALIASES:
        candidates.append(_EXTRA_ALIASES[name])
    candidates.append(name)
    # 剥离行政后缀
    for suf in _ADMIN_SUFFIXES:
        if name.endswith(suf) and len(name) > len(suf):
            candidates.append(name[:-len(suf)])
            break
    candidates.append(name.translate(_S2T))
    candidates.append(name.translate(_T2S))
    seen, uniq = set(), []
    for c in candidates:
        if c and c not in seen:
            seen.add(c); uniq.append(c)
    return uniq


def _pick_best_match(query: str, candidates: list[dict]) -> Optional[dict]:
    """只接受唯一精确命中；重名不按人口静默择一。"""
    if not candidates:
        return None
    q = query.lower()
    exact = [c for c in candidates if c['name'].lower() == q]
    matches = exact or [c for c in candidates
                        if query in c.get('alternatenames', [])]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return {"ambiguous_candidates": matches}
    ranked = sorted(candidates, key=lambda c: c.get('population', 0), reverse=True)
    if ranked and ranked[0].get('population', 0) >= 100_000:
        if len(ranked) == 1 or ranked[0].get('population', 0) > ranked[1].get('population', 0) * 2:
            return ranked[0]
        return {"ambiguous_candidates": ranked[:5]}
    return None
def resolve_location(name: str, ref_date: Optional[_date] = None) -> Optional[dict]:
    """解析唯一城市；重名返回候选，不按人口或字典序猜测。"""
    if not name or not name.strip():
        return None
    best = None
    gc = _get_gc()
    if gc is not None:
        for query in _normalize_query(name):
            try:
                results = gc.search_cities(query, case_sensitive=False)
            except Exception:
                continue
            pick = _pick_best_match(query, results)
            if pick:
                if "ambiguous_candidates" in pick:
                    return {"ambiguous": True, "candidates": [
                        {"name": c.get("name"), "country": c.get("countrycode"),
                         "latitude": c.get("latitude"), "longitude": c.get("longitude"),
                         "timezone": c.get("timezone")}
                        for c in pick["ambiguous_candidates"]
                    ]}
                best = pick
                break
    if best:
        lat = float(best["latitude"])
        lon = float(best["longitude"])
        country = best.get("countrycode") or best.get("country") or ""
        tz_name = None
        tf = _get_tf()
        if tf is not None:
            try:
                tz_name = tf.timezone_at(lat=lat, lng=lon)
            except Exception:
                tz_name = None
        tz_name = tz_name or best.get("timezone")
        result = {"name": best["name"], "country": country, "lat": lat,
                  "lon": lon, "tz_name": tz_name, "tz_offset_hours": None,
                  "dst_aware": False}
    else:
        result = _offline_lookup(name)
        if result is None:
            return None
    if result["tz_name"]:
        try:
            zone = ZoneInfo(result["tz_name"])
            ref = ref_date or _date.today()
            possible = _zone_candidates(datetime(ref.year, ref.month, ref.day), zone)
            if possible:
                result["tz_offset_hours"] = possible[0][1]
                result["dst_aware"] = possible[0][0].astimezone(zone).dst() not in (None, timedelta(0))
        except ZoneInfoNotFoundError:
            result["tz_name"] = None
    return result


def _offline_lookup(name: str) -> Optional[dict]:
    """硬编码 fallback"""
    for cand in _normalize_query(name):
        if cand in _OFFLINE_CITY_DB:
            lat, lon, tz_name, country = _OFFLINE_CITY_DB[cand]
            return {
                'name': cand, 'country': country, 'lat': lat, 'lon': lon,
                'tz_name': tz_name, 'tz_offset_hours': None, 'dst_aware': False,
            }
    return None




# ---------------------------------------------------------------------------
# 时区偏移辅助（zoneinfo 单点查询）
# ---------------------------------------------------------------------------

def get_utc_offset_at(iana_tz: str, year: int, month: int, day: int,
                      hour: int = 12, minute: int = 0) -> float:
    """指定时刻该 IANA 时区的实际 UTC 偏移（小时，含 DST）"""
    try:
        tz = ZoneInfo(iana_tz)
    except ZoneInfoNotFoundError as e:
        raise ValueError(f'未知 IANA 时区: {iana_tz}') from e
    off = datetime(year, month, day, hour, minute, tzinfo=tz).utcoffset()
    if off is None:
        raise ValueError(f'无法计算 {iana_tz} 的 UTC 偏移')
    return off.total_seconds() / 3600.0


def is_dst_at(iana_tz: str, year: int, month: int, day: int,
              hour: int = 12, minute: int = 0) -> bool:
    """指定时刻该时区是否处于 DST"""
    try:
        tz = ZoneInfo(iana_tz)
    except ZoneInfoNotFoundError:
        return False
    dst = datetime(year, month, day, hour, minute, tzinfo=tz).dst()
    return dst is not None and dst.total_seconds() > 0


 # Solar time is normalized from the birth instant in normalize_birth_time().

# ---------------------------------------------------------------------------
# 命盘输入哈希
# ---------------------------------------------------------------------------

def compute_chart_hash(date: str, time: str, gender: str, location: str) -> str:
    """SHA-256(date|time|gender|location) → 16 字符 hex，用于缓存键"""
    payload = json.dumps(
        {'date': date.strip(), 'time': time.strip(),
         'gender': gender.strip().lower(), 'location': location.strip()},
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]
