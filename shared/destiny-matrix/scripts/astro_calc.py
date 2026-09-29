#!/usr/bin/env python3
"""占星本命盘计算。所有时刻经 _common.normalize_birth_time 统一规范化。"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime

import swisseph as swe

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from _common import (  # noqa: E402
    ASTRO_POSITIONS_KEY, CalcError, InputError, format_coord, format_tz, match_aspect,
    normalize_birth_time, resolve_orbs,
)

SIGNS = ['白羊', '金牛', '双子', '巨蟹', '狮子', '处女',
         '天秤', '天蝎', '射手', '摩羯', '水瓶', '双鱼']
SIGN_RULERS = {
    '白羊': '火星', '金牛': '金星', '双子': '水星', '巨蟹': '月亮',
    '狮子': '太阳', '处女': '水星', '天秤': '金星', '天蝎': '冥王星',
    '射手': '木星', '摩羯': '土星', '水瓶': '天王星', '双鱼': '海王星',
}
HOUSE_MEANINGS = {
    1: '命宫·自我形象', 2: '财帛·价值观', 3: '兄弟·学习沟通',
    4: '田宅·家庭根基', 5: '子女·创造与爱', 6: '日常·健康与工作',
    7: '关系·一对一互动', 8: '共享资源·转化', 9: '迁移·哲学远方',
    10: '事业·社会角色', 11: '朋友·理想', 12: '潜意识·隐秘事务',
}
PLANETS_CORE = [
    ('太阳', swe.SUN), ('月亮', swe.MOON), ('水星', swe.MERCURY),
    ('金星', swe.VENUS), ('火星', swe.MARS), ('木星', swe.JUPITER),
    ('土星', swe.SATURN), ('天王星', swe.URANUS), ('海王星', swe.NEPTUNE),
    ('冥王星', swe.PLUTO),
]
ASPECT_LABELS = {
    'conjunction': '合相', 'opposition': '对冲', 'trine': '三合',
    'square': '四分', 'sextile': '六合',
}
ASPECT_DEGREES = {
    'conjunction': 0.0, 'opposition': 180.0, 'trine': 120.0,
    'square': 90.0, 'sextile': 60.0,
}


def deg_to_sign(deg: float) -> tuple[str, float]:
    deg = float(deg) % 360.0
    index = int(deg / 30)
    return SIGNS[index], deg - index * 30


def _engine(returned_flags: int) -> str:
    if returned_flags & swe.FLG_SWIEPH:
        return 'SWIEPH'
    if returned_flags & swe.FLG_MOSEPH:
        return 'MOSEPH'
    return 'unknown'


def _calc_point(jd_ut: float, planet_id: int) -> tuple[tuple, int, int]:
    requested = swe.FLG_SWIEPH | swe.FLG_SPEED
    values, returned = swe.calc_ut(jd_ut, planet_id, requested)
    return values, requested, returned


def calc_chart(time_context: dict, *, house_system: str = 'placidus',
               use_true_node: bool = True, orbs: dict | None = None) -> dict:
    """从规范化 UTC 瞬间计算占星盘；返回维度 envelope。"""
    if house_system not in {'placidus', 'whole_sign'}:
        raise InputError('invalid_house_system', 'house_system',
                         'house_system 只能为 placidus 或 whole_sign')
    if time_context.get('precision') != 'minute':
        candidates = [
            {
                'validity': {key: row[key] for key in
                             ('start_utc', 'end_utc', 'end_inclusive') if key in row},
                'status': 'precise_chart_unavailable',
                'limitations': ['精确出生时刻未定；不输出单一星体度数、ASC/MC 或宫位'],
            }
            for row in time_context.get('candidate_intervals', [])
        ]
        return {
            'status': 'partial', 'data': None, 'candidates': candidates,
            'limitations': ['非精确时刻不输出确定本命星体度数、ASC/MC 或宫位'],
        }
    utc_text = time_context.get('utc_instant')
    if not isinstance(utc_text, str):
        raise InputError('missing_utc_instant', 'time_context.utc_instant',
                         '精确时刻缺少规范化 UTC 瞬间')
    try:
        utc = datetime.fromisoformat(utc_text.replace('Z', '+00:00'))
        jd_et, jd_ut = swe.utc_to_jd(
            utc.year, utc.month, utc.day, utc.hour, utc.minute,
            utc.second + utc.microsecond / 1_000_000, swe.GREG_CAL,
        )
    except Exception as exc:
        raise CalcError('utc_to_jd_failed', 'time_context.utc_instant', str(exc)) from exc

    profile_id, resolved_orbs = resolve_orbs(orbs)
    node_id = swe.TRUE_NODE if use_true_node else swe.MEAN_NODE
    planets = PLANETS_CORE + [('北交点', node_id)]
    positions, planet_methods = {}, {}
    for name, planet_id in planets:
        try:
            values, requested, returned = _calc_point(jd_ut, planet_id)
        except Exception as exc:
            raise CalcError('core_planet_failed', f'planets.{name}', str(exc)) from exc
        longitude = float(values[0]) % 360.0
        sign, within = deg_to_sign(longitude)
        positions[name] = {
            '黄经': longitude, '星座': sign, '宫内度数': within,
            '逆行': values[3] < 0, '主管': SIGN_RULERS.get(sign, ''),
            '黄经日速': float(values[3]),
        }
        planet_methods[name] = {
            'requested_flags': requested, 'returned_flags': returned,
            'engine': _engine(returned),
        }

    # Chiron is an optional point: a missing ephemeris never invalidates core planets.
    try:
        values, requested, returned = _calc_point(jd_ut, swe.CHIRON)
        longitude = float(values[0]) % 360.0
        sign, within = deg_to_sign(longitude)
        positions['凯龙星'] = {
            '黄经': longitude, '星座': sign, '宫内度数': within,
            '逆行': values[3] < 0, '主管': SIGN_RULERS.get(sign, ''),
            '黄经日速': float(values[3]), 'available': True,
        }
        planet_methods['凯龙星'] = {
            'requested_flags': requested, 'returned_flags': returned,
            'engine': _engine(returned), 'optional': True,
        }
    except Exception as exc:
        positions['凯龙星'] = {'available': False, 'reason': str(exc)}
        planet_methods['凯龙星'] = {'available': False, 'optional': True}

    try:
        values, requested, returned = _calc_point(jd_ut, swe.MEAN_APOG)
        longitude = float(values[0]) % 360.0
        sign, within = deg_to_sign(longitude)
        positions['莉莉丝'] = {
            '黄经': longitude, '星座': sign, '宫内度数': within,
            '逆行': values[3] < 0, '主管': SIGN_RULERS.get(sign, ''),
            '黄经日速': float(values[3]),
            'available': True, 'point': 'Mean Apogee',
        }
        planet_methods['莉莉丝'] = {
            'requested_flags': requested, 'returned_flags': returned,
            'engine': _engine(returned), 'optional': True,
        }
    except Exception as exc:
        positions['莉莉丝'] = {'available': False, 'reason': str(exc),
                              'point': 'Mean Apogee'}
        planet_methods['莉莉丝'] = {'available': False, 'optional': True}

    lat = float(time_context['location']['latitude'])
    lon = float(time_context['location']['longitude'])
    house_code = b'P' if house_system == 'placidus' else b'W'
    house_label = 'Placidus' if house_system == 'placidus' else 'Whole Sign'
    cusps, ascmc = None, None
    house_error = None
    asc_mc_solver = 'requested_house_system'
    try:
        raw_cusps, raw_ascmc = swe.houses(jd_ut, lat, lon, house_code)
        cusps = tuple(float(value) % 360.0 for value in raw_cusps[:12])
        ascmc = tuple(float(value) % 360.0 for value in raw_ascmc)
    except Exception as exc:
        house_error = str(exc)
        if house_system == 'placidus':
            try:
                # The alternate call supplies only house-system-independent angles.
                # Its cusps are deliberately discarded; Placidus remains unavailable.
                _, angle_only = swe.houses(jd_ut, lat, lon, b'W')
                ascmc = tuple(float(value) % 360.0 for value in angle_only)
                asc_mc_solver = 'whole_sign_angle_only'
            except Exception:
                ascmc = None

    houses = []
    aspects = []
    extras = {'凯龙星': positions['凯龙星'], '莉莉丝': positions['莉莉丝']}
    axis = None
    limitations = []
    if ascmc is None:
        limitations.append(f'{house_label} 宫位不可用: {house_error or "缺少宫位结果"}')
    else:
        asc_lon, mc_lon = ascmc[0], ascmc[1]
        asc_sign, asc_degree = deg_to_sign(asc_lon)
        mc_sign, mc_degree = deg_to_sign(mc_lon)
        axis = {
            '太阳': f"{positions['太阳']['星座']}座 {positions['太阳']['宫内度数']:.2f}°",
            '月亮': f"{positions['月亮']['星座']}座 {positions['月亮']['宫内度数']:.2f}°",
            '上升': f'{asc_sign}座 {asc_degree:.2f}°',
            '天顶MC': f'{mc_sign}座 {mc_degree:.2f}°',
        }
        if cusps is None:
            limitations.append(
                f'{house_label} 宫位不可用: {house_error or "缺少宫位结果"}；ASC/MC 保留，未替代宫位制。')
            extras['福点'] = {
                'available': False,
                'reason': '宫位不可用，无法依据太阳落宫判定日盘/夜盘',
            }
        else:
            for index, cusp in enumerate(cusps):
                sign, within = deg_to_sign(cusp)
                houses.append({
                    '宫位': index + 1, '黄经': cusp, '含义': HOUSE_MEANINGS[index + 1],
                    '宫始星座': sign, '宫内度数': within,
                    '宫主': SIGN_RULERS.get(sign, ''),
                })
            for name, position in positions.items():
                if position.get('available') is False or '黄经' not in position:
                    continue
                position['落宫'] = find_house(position['黄经'], cusps)
            axis['太阳'] += f" (落 {positions['太阳'].get('落宫')} 宫)"
            axis['月亮'] += f" (落 {positions['月亮'].get('落宫')} 宫)"
            # 日夜盘按地平线判定，与宫制无关（whole sign 下太阳可在 1 宫而已升起）
            is_day = (positions['太阳']['黄经'] - asc_lon) % 360.0 >= 180.0
            fortune = ((asc_lon + positions['月亮']['黄经'] - positions['太阳']['黄经'])
                       if is_day else
                       (asc_lon + positions['太阳']['黄经'] - positions['月亮']['黄经'])) % 360
            fortune_sign, fortune_within = deg_to_sign(fortune)
            extras['福点'] = {
                '黄经': fortune, '星座': fortune_sign, '宫内度数': fortune_within,
                '落宫': find_house(fortune, cusps), '盘别': '日盘' if is_day else '夜盘',
            }
            vertex = ascmc[3] if len(ascmc) > 3 else None
            if vertex is not None:
                vertex_sign, vertex_within = deg_to_sign(vertex)
                extras['Vertex'] = {
                    '黄经': vertex, '星座': vertex_sign, '宫内度数': vertex_within,
                    '落宫': find_house(vertex, cusps),
                }
    names = list(positions)
    for first, a in enumerate(names):
        if '黄经' not in positions[a]:
            continue
        for b in names[first + 1:]:
            if '黄经' not in positions[b]:
                continue
            match = match_aspect(positions[a]['黄经'], positions[b]['黄经'], resolved_orbs)
            if match:
                aspects.append({
                    '行星A': a, '行星B': b,
                    '相位': ASPECT_LABELS[match['aspect']],
                    '实际角度': match['angle'], '偏差': match['exact_diff'],
                    '使用容许度': match['orb_used'],
                })

    from astro_structure import build_structure
    structure = build_structure(
        positions, cusps,
        None if ascmc is None else ascmc[0], None if ascmc is None else ascmc[1],
        aspects, resolved_orbs['conjunction'],
    )
    input_subject = time_context.get('input', {}).get('subject', {})
    time_input = time_context.get('input', {}).get('time_input', {})
    data = {
        '出生信息': {
            '公历': time_context['local_apparent_datetime'],
            'UTC': utc_text, 'UT1 儒略日': jd_ut, 'TT 儒略日': jd_et,
            '出生地经纬度': format_coord(lat, lon),
            '时区偏移': format_tz(time_context['timezone']['utc_offset_hours']),
            'IANA 时区': time_context['timezone'].get('name'),
        },
        '宫位制': house_label if cusps is not None else 'unavailable',
        'requested_house_system': house_system,
        '北交类型': 'True Node' if use_true_node else 'Mean Node',
        '相位方案': profile_id, '使用容许度': resolved_orbs,
        '三轴心': axis,
        'ASC_MC_原始黄经': None if ascmc is None else {'ASC': ascmc[0], 'MC': ascmc[1]},
        '十二宫始黄经': list(cusps) if cusps is not None else None,
        ASTRO_POSITIONS_KEY: positions,
        '十二宫': houses, '扩展配点': extras,
        '主要相位': aspects,
        '结构': structure,
    }
    methods = {
        'utc_conversion': 'swe.utc_to_jd', 'house_system_requested': house_system,
        'house_system_actual': house_label if cusps is not None else None,
        'asc_mc_solver': asc_mc_solver if ascmc is not None else None,
        'planets': planet_methods, 'ephemeris_version': swe.version,
        'pyswisseph_version': swe.__version__,
        'timezone_resolution': time_context['timezone']['resolution'],
        'calendar': input_subject.get('date_calendar', 'gregorian'),
        'clock_basis': time_input.get('clock_basis', 'civil'),
    }
    return {
        'status': 'partial' if limitations else 'ok', 'data': data,
        'methods': methods, 'candidates': [], 'limitations': limitations,
    }


def find_house(planet_lon: float, cusps: tuple[float, ...]) -> int | None:
    planet_lon %= 360
    for index, start in enumerate(cusps):
        end = cusps[(index + 1) % 12]
        if (start <= planet_lon < end) if start < end else (planet_lon >= start or planet_lon < end):
            return index + 1
    return None


def _parse_cli(argv: list[str]) -> tuple[list[str], dict]:
    values = {'timezone_name': None, 'utc_offset_hours': None,
              'house_system': 'placidus', 'use_true_node': True, 'orbs': None}
    positional = []
    i = 0
    while i < len(argv):
        item = argv[i]
        key, sep, value = item.partition('=')
        if key in {'--tz', '--tz-name', '--house-system', '--orbs'}:
            if not sep:
                i += 1
                value = argv[i] if i < len(argv) else None
            if value is None:
                raise InputError('missing_argument', key, f'{key} 需要参数值')
            if key == '--tz':
                try:
                    values['utc_offset_hours'] = float(value)
                except ValueError as exc:
                    raise InputError('invalid_offset', key, '--tz 必须为数字偏移') from exc
            elif key == '--tz-name':
                values['timezone_name'] = value
            elif key == '--house-system':
                if value not in {'placidus', 'whole_sign'}:
                    raise InputError('invalid_house_system', key, '只接受 placidus|whole_sign')
                values['house_system'] = value
            else:
                try:
                    values['orbs'] = json.loads(value)
                except json.JSONDecodeError as exc:
                    raise InputError('invalid_orbs', key, '--orbs 必须是 JSON 对象') from exc
        elif item == '--mean-node':
            values['use_true_node'] = False
        elif item.startswith('--'):
            raise InputError('unknown_argument', item, f'未知参数: {item}')
        else:
            positional.append(item)
        i += 1
    if (values['timezone_name'] is None) == (values['utc_offset_hours'] is None):
        raise InputError('timezone_required', '--tz', '必须且只能提供 --tz 或 --tz-name')
    if len(positional) != 4:
        raise InputError('invalid_arguments', 'argv', '用法: astro_calc.py DATE TIME LAT LON --tz=<offset>|--tz-name=<IANA> [--house-system placidus|whole_sign]')
    return positional, values


def main() -> None:
    try:
        positional, opts = _parse_cli(sys.argv[1:])
        date_text, time_text = positional[:2]
        try:
            lat, lon = float(positional[2]), float(positional[3])
            start = datetime.fromisoformat(f'{date_text}T{time_text}').isoformat(timespec='seconds')
        except (TypeError, ValueError) as exc:
            raise InputError('invalid_datetime_or_coordinates', 'argv', str(exc)) from exc
        subject = {'birth_date': date_text, 'latitude': lat, 'longitude': lon,
                   'date_calendar': 'gregorian'}
        time_input = {
            'precision': 'minute', 'start': start,
            'timezone_name': opts['timezone_name'],
            'utc_offset_hours': opts['utc_offset_hours'], 'fold': None,
            'clock_basis': 'civil',
        }
        context = normalize_birth_time(subject, time_input)
        result = calc_chart(context, house_system=opts['house_system'],
                            use_true_node=opts['use_true_node'], orbs=opts['orbs'])
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except Exception as exc:
        code = 2 if isinstance(exc, (InputError, FileNotFoundError, json.JSONDecodeError)) else 1
        print(json.dumps({'status': 'error', 'errors': [{
            'code': getattr(exc, 'code', 'calculation_error'),
            'path': getattr(exc, 'path', ''),
            'message': getattr(exc, 'message', str(exc)),
        }]}, ensure_ascii=False))
        print(f'astro_calc: {exc}', file=sys.stderr)
        sys.exit(code)


if __name__ == '__main__':
    main()
