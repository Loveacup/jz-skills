#!/usr/bin/env python3
# v3.0
"""destiny-matrix v3 统一调度脚本

一次性调用八字、紫微、占星三体系，输出统一 JSON。

相比 v2 的关键变更：
  - 去除 70 城硬编码 CITY_DB，全部走 _common.resolve_location（geonamescache 32k+ 城市，
    自动 IANA + 当时 UTC 偏移 + DST 状态）
  - 真太阳时校正（经度时差 + 均时差），默认开启
  - 海外历史日期 DST 自动识别（zoneinfo），不再有 1985 NYC 偏一小时这类 v2 bug
  - 经纬度/时区展示走 _common.format_coord / format_tz，南半球与西半球符号正确

用法:
  python3 cast_chart.py <yyyy-mm-dd> <hh:mm> <gender:m|f> <city> [选项]

示例:
  python3 cast_chart.py 1993-09-30 17:30 f 杭州
  python3 cast_chart.py 1985-07-15 14:00 m 纽约
  python3 cast_chart.py 1990-01-15 08:30 m 自定义 --lat=40.7 --lon=-74.0 --tz=-5
  python3 cast_chart.py 1993-09-30 17:30 f 杭州 --use-true-solar-time=off

选项:
  --lat=<float>        手工指定纬度（与 --lon 同时给出时跳过城市解析）
  --lon=<float>        手工指定经度
  --tz=<float>         手工指定 UTC 偏移（小时；提供时跳过 DST 自动计算）
  --use-true-solar-time=on|off
                       是否启用真太阳时校正（默认 on）
"""
import sys
import json
import os
import subprocess
import datetime as _dt
from datetime import date as _date

# 让 _common 可被 import（同目录脚本）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from _common import (  # noqa: E402
    hour_to_idx,
    format_coord,
    format_tz,
    resolve_location,
    solar_time_correction,
    compute_chart_hash,
    HOUR_BRANCHES,
)

CACHE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'cache')


def _cache_path(hash_key: str) -> str:
    return os.path.join(CACHE_DIR, f'{hash_key}.json')


def cache_load(hash_key: str):
    p = _cache_path(hash_key)
    if os.path.isfile(p):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None


def cache_save(hash_key: str, data: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(_cache_path(hash_key), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 缓存写失败不影响主流程


def run_script(script: str, args: list) -> dict:
    """调用子脚本（bazi_calc / ziwei_calc / astro_calc）并解析其 JSON 输出"""
    cmd = ['python3', os.path.join(SCRIPT_DIR, script)] + [str(a) for a in args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {'error': f'{script} exit {result.returncode}',
                    'stderr': result.stderr.strip()[:500]}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {'error': f'{script} timeout'}
    except json.JSONDecodeError as e:
        return {'error': f'{script} invalid JSON: {str(e)}',
                'output': result.stdout[:500]}


def parse_args() -> tuple[list, dict]:
    """解析 CLI 参数，返回 (positional, options)"""
    opts = {
        'lat': None,
        'lon': None,
        'tz': None,
        'use_true_solar_time': True,
    }
    positional = []
    for a in sys.argv[1:]:
        if a.startswith('--lat='):
            opts['lat'] = float(a[6:])
        elif a.startswith('--lon='):
            opts['lon'] = float(a[6:])
        elif a.startswith('--tz='):
            opts['tz'] = float(a[5:])
        elif a.startswith('--use-true-solar-time='):
            val = a.split('=', 1)[1].lower()
            opts['use_true_solar_time'] = (val in ('on', 'true', '1', 'yes'))
        elif not a.startswith('--'):
            positional.append(a)
    return positional, opts


def _resolve_geo(city: str, opts: dict, year: int, month: int, day: int) -> dict:
    """统一解析地理与时区信息

    返回字段：lat, lon, iana_tz, utc_offset, is_dst, resolved, city_canonical。
    若用户手工 --lat --lon，则跳过 geonamescache 但仍尝试反查 IANA。
    """
    info = {
        'lat': None, 'lon': None, 'iana_tz': None,
        'utc_offset': None, 'is_dst': False,
        'resolved': False, 'city_canonical': city,
    }

    if opts['lat'] is not None and opts['lon'] is not None:
        info['lat'] = opts['lat']
        info['lon'] = opts['lon']
        info['resolved'] = True
        # 用 timezonefinder 反查 IANA（_common 内有单例）
        try:
            from _common import _get_tf
            tf = _get_tf()
            iana = tf.timezone_at(lat=info['lat'], lng=info['lon']) if tf else None
        except Exception:
            iana = None
        if iana:
            info['iana_tz'] = iana
            # 计算出生日期当时的 UTC 偏移
            from zoneinfo import ZoneInfo
            try:
                tz = ZoneInfo(iana)
                dt = _dt.datetime(year, month, day, 12, 0, tzinfo=tz)
                info['utc_offset'] = dt.utcoffset().total_seconds() / 3600.0
                info['is_dst'] = dt.dst() is not None and dt.dst().total_seconds() > 0
            except Exception:
                pass
        if opts['tz'] is not None:
            info['utc_offset'] = opts['tz']
        if info['utc_offset'] is None:
            info['utc_offset'] = 8.0  # 兜底
        return info

    resolved = resolve_location(city, ref_date=_date(year, month, day))
    if resolved is None:
        return info
    info['lat'] = resolved['lat']
    info['lon'] = resolved['lon']
    info['iana_tz'] = resolved['tz_name']
    info['utc_offset'] = (opts['tz'] if opts['tz'] is not None
                          else resolved['tz_offset_hours'])
    info['is_dst'] = resolved['dst_aware']
    info['resolved'] = True
    info['city_canonical'] = resolved.get('name') or city
    if info['utc_offset'] is None:
        info['utc_offset'] = 8.0
    return info


def main():
    positional, opts = parse_args()
    if len(positional) < 4:
        print(__doc__)
        sys.exit(1)

    date_str = positional[0]
    time_str = positional[1]
    gender = positional[2].lower()
    city = positional[3]

    try:
        year, month, day = map(int, date_str.split('-'))
        hour, minute = map(int, time_str.split(':'))
    except ValueError:
        print(f'ERROR: 日期或时间格式错误: {date_str} {time_str}', file=sys.stderr)
        sys.exit(1)

    if gender not in ('m', 'f'):
        print(f"ERROR: 性别参数需为 m 或 f，收到 '{gender}'", file=sys.stderr)
        sys.exit(1)

    # 1. 地理 + 时区
    geo = _resolve_geo(city, opts, year, month, day)
    if not geo['resolved']:
        print(f"ERROR: 未能解析城市 '{city}'。请用 --lat= --lon= [--tz=] 显式指定。",
              file=sys.stderr)
        sys.exit(1)

    lat = geo['lat']
    lon = geo['lon']
    iana = geo['iana_tz']
    tz = geo['utc_offset']
    dst = geo['is_dst']

    # 2. 真太阳时校正（默认开启）
    raw_hour_idx = hour_to_idx(hour, minute)
    if opts['use_true_solar_time']:
        correction = solar_time_correction(
            lon, hour, minute, tz,
            year=year, month=month, day=day, iana_tz=iana,
        )
        c_year, c_month, c_day = map(int, correction['校正后date'].split('-'))
        c_hour = correction['校正后hour']
        c_minute = correction['校正后minute']
        solar_offset_min = correction['偏差分钟']
        cross_branch = correction['是否跨时辰']
        solar_warn = correction['警告']
    else:
        correction = None
        c_year, c_month, c_day = year, month, day
        c_hour, c_minute = hour, minute
        solar_offset_min = 0.0
        cross_branch = False
        solar_warn = None

    hour_idx = hour_to_idx(c_hour, c_minute)
    corrected_date_str = f'{c_year:04d}-{c_month:02d}-{c_day:02d}'
    corrected_time_str = f'{c_hour:02d}:{c_minute:02d}'

    # 3. 调用三个子脚本（传入校正后的时刻）
    # astro_calc 接受 IANA 字符串作为 tz 参数，让它内部按出生日期算 DST
    astro_tz_arg = iana if iana else str(tz)
    bazi = run_script('bazi_calc.py', [corrected_date_str, corrected_time_str, gender])
    ziwei = run_script('ziwei_calc.py', [corrected_date_str, str(hour_idx), gender])
    astro = run_script('astro_calc.py', [corrected_date_str, corrected_time_str,
                                          lat, lon, astro_tz_arg])

    # 4. 输出统一结构
    result = {
        '元数据': {
            '版本': 'destiny-matrix v3',
            '生成时间': _dt.datetime.now().isoformat(timespec='seconds'),
            '输入': {
                '公历': f'{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}',
                '性别': '男' if gender == 'm' else '女',
                '出生地': city,
                '解析为': geo['city_canonical'],
                '经纬度': format_coord(lat, lon),
                '时区': format_tz(tz),
                'IANA 时区': iana or '(未知)',
                'DST 状态': '夏令时' if dst else '标准时',
                '时辰索引': f'{hour_idx} ({HOUR_BRANCHES[hour_idx]}时)',
            },
            '真太阳时校正': {
                '启用': opts['use_true_solar_time'],
                '偏差分钟': round(solar_offset_min, 2),
                '校正后时刻': f'{corrected_date_str} {corrected_time_str}',
                '原始时辰': HOUR_BRANCHES[raw_hour_idx] + '时',
                '校正后时辰': HOUR_BRANCHES[hour_idx] + '时',
                '跨时辰边界': cross_branch,
                '警告': solar_warn,
                # 暴露完整校正信息（含经度时差、均时差）便于调试
                '详情': correction,
            },
        },
        '八字': bazi,
        '紫微': ziwei,
        '占星': astro,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
