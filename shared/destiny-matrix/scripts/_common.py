#!/usr/bin/env python3
# v3.0
"""destiny-matrix v3 公共工具

函数：
  hour_to_idx              时分→时辰索引（0=子）
  format_coord             经纬度格式化（自动南北/东西）
  format_tz                时区格式化（UTC±N[.x]）
  resolve_location         城市名模糊匹配（geonamescache + timezonefinder）
  solar_time_correction    真太阳时校正（经度偏移 + 均时差 + 时辰边界警告）
  compute_chart_hash       命盘输入哈希（SHA-256，供缓存层）
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date as _date, datetime
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
    """从 search_cities 命中里挑最优"""
    if not candidates:
        return None
    q = query.lower()
    exact = [c for c in candidates if c['name'].lower() == q]
    if exact:
        return max(exact, key=lambda c: c.get('population', 0))
    alt = [c for c in candidates if query in c.get('alternatenames', [])]
    if alt:
        return max(alt, key=lambda c: c.get('population', 0))
    # 兜底人口阈值
    s = sorted(candidates, key=lambda c: c.get('population', 0), reverse=True)
    if s and s[0].get('population', 0) >= 100_000:
        return s[0]
    return None


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


def resolve_location(name: str, ref_date: Optional[_date] = None) -> Optional[dict]:
    """城市名模糊匹配，返回 {name, country, lat, lon, tz_name, tz_offset_hours, dst_aware}

    ref_date 用以计算当时的 UTC 偏移（处理 DST）；缺省取当下。
    匹配优先级：alias 表 → geonamescache 精确 name → alternatenames → 人口兜底 → 离线 fallback。
    返回 None 表示未找到。
    """
    if not name or not name.strip():
        return None

    best = None
    gc = _get_gc()
    if gc is not None:
        for q in _normalize_query(name):
            try:
                results = gc.search_cities(q, case_sensitive=False)
            except Exception:
                continue
            pick = _pick_best_match(q, results)
            if pick:
                best = pick
                break

    if best:
        lat = float(best['latitude'])
        lon = float(best['longitude'])
        country = best.get('countrycode') or best.get('country') or ''
        # timezonefinder 优先（更精确），失败回退 geonamescache 字段
        tz_name = None
        tf = _get_tf()
        if tf is not None:
            try:
                tz_name = tf.timezone_at(lat=lat, lng=lon)
            except Exception:
                tz_name = None
        if not tz_name:
            tz_name = best.get('timezone')
        result = {
            'name': best['name'], 'country': country,
            'lat': lat, 'lon': lon, 'tz_name': tz_name,
            'tz_offset_hours': None, 'dst_aware': False,
        }
    else:
        result = _offline_lookup(name)
        if result is None:
            return None

    # 计算当时 UTC 偏移与 DST 状态
    if result['tz_name']:
        try:
            tz = ZoneInfo(result['tz_name'])
            ref = ref_date or _date.today()
            dt = datetime(ref.year, ref.month, ref.day, 12, 0, tzinfo=tz)
            off = dt.utcoffset()
            if off is not None:
                result['tz_offset_hours'] = off.total_seconds() / 3600.0
            dst = dt.dst()
            result['dst_aware'] = dst is not None and dst.total_seconds() > 0
        except ZoneInfoNotFoundError:
            pass
    return result


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


# ---------------------------------------------------------------------------
# 真太阳时校正
# ---------------------------------------------------------------------------

# 主要 IANA 时区的"标称中心经度"——本时区标准时间对应的子午线
# 中国境内一律按 120°E（北京时间基准）
_TZ_CENTER_LONGITUDE = {
    'Asia/Shanghai': 120.0, 'Asia/Hong_Kong': 120.0, 'Asia/Macau': 120.0,
    'Asia/Taipei': 120.0, 'Asia/Urumqi': 90.0,
    'Asia/Tokyo': 135.0, 'Asia/Seoul': 135.0,
    'Asia/Singapore': 120.0, 'Asia/Kuala_Lumpur': 120.0,
    'Asia/Bangkok': 105.0, 'Asia/Jakarta': 105.0,
    'Asia/Manila': 120.0, 'Asia/Dubai': 60.0,
    'Asia/Kolkata': 82.5,
    'Europe/London': 0.0, 'Europe/Paris': 15.0, 'Europe/Berlin': 15.0,
    'Europe/Rome': 15.0, 'Europe/Madrid': 15.0, 'Europe/Amsterdam': 15.0,
    'Europe/Vienna': 15.0, 'Europe/Zurich': 15.0, 'Europe/Moscow': 45.0,
    'America/New_York': -75.0, 'America/Chicago': -90.0,
    'America/Denver': -105.0, 'America/Los_Angeles': -120.0,
    'America/Toronto': -75.0, 'America/Vancouver': -120.0,
    'America/Mexico_City': -90.0, 'America/Sao_Paulo': -45.0,
    'Australia/Sydney': 150.0, 'Australia/Melbourne': 150.0,
    'Australia/Perth': 120.0, 'Pacific/Auckland': 180.0,
}


def _center_longitude_from_offset(tz_offset_hours: float) -> float:
    """从 tz_offset 推导标称中心经度：每小时偏移对应 15°"""
    return tz_offset_hours * 15.0


def _equation_of_time_minutes(day_of_year: int) -> float:
    """均时差（分钟）。Spencer / Whitman 近似公式：
        B = (360/365) × (N - 81)
        EoT = 9.87×sin(2B) - 7.53×cos(B) - 1.5×sin(B)
    """
    B = math.radians((360.0 / 365.0) * (day_of_year - 81))
    return 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)


def solar_time_correction(
    lon: float,
    hour: int,
    minute: int,
    tz_offset: float,
    *,
    year: Optional[int] = None,
    month: Optional[int] = None,
    day: Optional[int] = None,
    iana_tz: Optional[str] = None,
) -> dict:
    """真太阳时校正

    参数:
        lon         经度（°，东正西负）
        hour/minute 本地钟点（24h）
        tz_offset   本地时区当时 UTC 偏移（小时，含 DST）
        year/month/day 用以算均时差（缺省取今日）
        iana_tz     若提供且在 _TZ_CENTER_LONGITUDE 中，优先用该表的中心经度

    返回:
        {
            '偏差分钟': float（正=真太阳时早于本地钟，排盘需把本地钟前移）,
            '经度时差': float,
            '均时差': float,
            '校正后hh:mm': str,
            '校正后hour': int, '校正后minute': int,
            '是否跨时辰': bool,
            '警告': str | None,
        }

    算法:
        中国境内基准经度 = 120°E（即使 lon=88 也以 120 为基准，这就是新疆出生需大幅校正的原因）
        其他时区：优先用 _TZ_CENTER_LONGITUDE 表；否则从 tz_offset×15 推导。
        经度时差(分) = (lon - center) × 4
        均时差(分)   = 9.87 sin(2B) - 7.53 cos(B) - 1.5 sin(B), B = (360/365)(N-81)
        真太阳时 = 本地钟 + 经度时差 + 均时差
    """
    if iana_tz and iana_tz in _TZ_CENTER_LONGITUDE:
        center = _TZ_CENTER_LONGITUDE[iana_tz]
    else:
        center = _center_longitude_from_offset(tz_offset)

    today = _date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day
    try:
        doy = _date(y, m, d).timetuple().tm_yday
    except ValueError:
        doy = today.timetuple().tm_yday

    lon_minutes = (lon - center) * 4.0
    eot_minutes = _equation_of_time_minutes(doy)
    total_offset = lon_minutes + eot_minutes

    # 应用偏移到本地钟（真太阳时为新时刻）
    base = datetime(y, m, d, hour, minute)
    from datetime import timedelta
    corrected = base + timedelta(minutes=total_offset)

    raw_idx = hour_to_idx(hour, minute)
    new_idx = hour_to_idx(corrected.hour, corrected.minute)
    crossed = (raw_idx != new_idx)

    # 时辰边界 10 分钟内警告（任一侧）
    warn = None
    if crossed:
        warn = (f'真太阳时校正后跨越时辰边界（{HOUR_BRANCHES[raw_idx]}时→'
                f'{HOUR_BRANCHES[new_idx]}时），干支盘以校正后为准')
    else:
        # 距离上下时辰边界的分钟数
        h_dec = corrected.hour + corrected.minute / 60
        # 时辰边界：23, 1, 3, 5, ..., 21（每两小时一个）
        boundaries = [-1, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25]
        min_dist = min(abs(h_dec - b) * 60 for b in boundaries)
        if min_dist <= 10:
            warn = (f'真太阳时校正后距时辰边界仅 {min_dist:.1f} 分钟，建议人工核对'
                    f'（出生时间精度若 >10 分钟可能落入相邻时辰）')

    return {
        '偏差分钟': round(total_offset, 2),
        '经度时差': round(lon_minutes, 2),
        '均时差': round(eot_minutes, 2),
        '校正后hh:mm': f'{corrected.hour:02d}:{corrected.minute:02d}',
        '校正后hour': corrected.hour,
        '校正后minute': corrected.minute,
        '校正后date': corrected.strftime('%Y-%m-%d'),
        '是否跨时辰': crossed,
        '原时辰': HOUR_BRANCHES[raw_idx],
        '校正后时辰': HOUR_BRANCHES[new_idx],
        '警告': warn,
    }


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
