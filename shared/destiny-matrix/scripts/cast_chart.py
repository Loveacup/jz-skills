#!/usr/bin/env python3
"""destiny-matrix v5 chart calculator and schema-v2 bundle dispatcher."""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from _common import CalcError, InputError, normalize_birth_time, resolve_location


METHODS = {
    'bundle_schema': 2,
    'time_pipeline': 'normalize_birth_time',
    'time_rule': 'civil/local solar time from one UTC instant; term axis fixed UTC+08:00',
}


def parse_args(argv: list[str]) -> tuple[dict, dict]:
    options = {'subject': 'primary', 'zi_hour_rule': 'midnight',
               'house_system': 'placidus', 'lat': None, 'lon': None,
               'tz': None, 'tz_name': None}
    positional, intake_path = [], None
    i = 0
    while i < len(argv):
        token = argv[i]
        key, has_value, value = token.partition('=')
        if key in {'--intake', '--subject', '--zi-hour-rule', '--house-system',
                   '--lat', '--lon', '--tz', '--tz-name'}:
            if not has_value:
                i += 1
                value = argv[i] if i < len(argv) else None
            if value is None:
                raise InputError('missing_argument', key, f'{key} 需要参数值')
            if key == '--intake':
                intake_path = value
            elif key == '--subject':
                if value not in {'primary', 'partner'}:
                    raise InputError('invalid_subject', key, '只接受 primary 或 partner')
                options['subject'] = value
            elif key == '--zi-hour-rule':
                if value not in {'midnight', 'zi_start'}:
                    raise InputError('invalid_zi_hour_rule', key, '只接受 midnight 或 zi_start')
                options['zi_hour_rule'] = value
            elif key == '--house-system':
                if value not in {'placidus', 'whole_sign'}:
                    raise InputError('invalid_house_system', key, '只接受 placidus 或 whole_sign')
                options['house_system'] = value
            elif key in {'--lat', '--lon'}:
                try:
                    options[key[2:]] = float(value)
                except ValueError as exc:
                    raise InputError('invalid_coordinate', key, f'{key} 必须为数字') from exc
            elif key == '--tz':
                try:
                    options['tz'] = float(value)
                except ValueError as exc:
                    raise InputError('invalid_offset', key, '--tz 必须为数字 UTC 偏移') from exc
            else:
                options['tz_name'] = value
        elif token.startswith('--'):
            raise InputError('unknown_argument', token, f'未知参数: {token}')
        else:
            positional.append(token)
        i += 1
    if intake_path and positional:
        raise InputError('mutually_exclusive_inputs', 'argv', '--intake 与位置参数不能同时使用')
    if not intake_path and len(positional) != 4:
        raise InputError('invalid_arguments', 'argv',
                         '用法: cast_chart.py DATE TIME m|f|- CITY [--lat= --lon= --tz=<offset>|--tz-name=<IANA>]')
    if options['subject'] == 'partner' and not intake_path:
        raise InputError('invalid_subject', '--subject', 'partner 仅能与 --intake 一起使用')
    return {'intake': intake_path, 'positional': positional}, options


def _load_case(args: dict, opts: dict) -> tuple[dict, dict, dict]:
    if args['intake']:
        try:
            with open(args['intake'], encoding='utf-8') as stream:
                intake = json.load(stream)
        except json.JSONDecodeError as exc:
            raise InputError('invalid_json', args['intake'], str(exc)) from exc
        except OSError as exc:
            raise InputError('file_error', args['intake'], str(exc)) from exc
        if opts['subject'] == 'primary':
            subject, time_input = intake.get('subject'), intake.get('time_input')
        else:
            partner = intake.get('synastry', {}).get('partner')
            subject = partner.get('subject') if isinstance(partner, dict) else None
            time_input = partner.get('time_input') if isinstance(partner, dict) else None
        if not isinstance(subject, dict) or not isinstance(time_input, dict):
            raise InputError('missing_subject', opts['subject'], 'intake 缺少 subject/time_input')
        return intake, subject, time_input

    date_text, time_text, sex_text, city = args['positional']
    if sex_text not in {'m', 'f', '-'}:
        raise InputError('invalid_calculation_sex', 'sex', '传统计算参数只接受 m、f 或 -')
    try:
        datetime.fromisoformat(f'{date_text}T{time_text}')
    except ValueError as exc:
        raise InputError('invalid_datetime', 'birth_time', str(exc)) from exc
    location = {'city': city}
    if (opts['lat'] is None) != (opts['lon'] is None):
        raise InputError('incomplete_coordinates', 'coordinates', '--lat 与 --lon 必须同时提供')
    if opts['lat'] is not None:
        location.update(latitude=opts['lat'], longitude=opts['lon'])
    if opts['tz_name'] and opts['tz'] is not None:
        raise InputError('conflicting_timezone', 'timezone', '--tz 与 --tz-name 互斥')
    subject = {
        'birth_date': date_text, 'date_calendar': 'gregorian',
        'calculation_sex': sex_text if sex_text != '-' else None,
        'location': location,
    }
    time_input = {
        'precision': 'minute', 'start': f'{date_text}T{time_text}',
        'timezone_name': opts['tz_name'], 'utc_offset_hours': opts['tz'],
        'fold': None, 'clock_basis': 'civil',
    }
    return {'analysis_as_of': None}, subject, time_input


def _missing_dimension(status: str, message: str) -> dict:
    return {'status': status, 'data': None, 'candidates': [], 'limitations': [message]}


def _dimension_error(exc: Exception) -> dict:
    return {'status': 'error', 'data': None, 'candidates': [],
            'limitations': [getattr(exc, 'message', str(exc))]}



def build_bundle(intake: dict, subject: dict, time_input: dict,
                 *, zi_hour_rule: str = 'midnight',
                 house_system: str = 'placidus') -> tuple[dict, int]:
    dimensions = {}
    errors = []
    limitations = []
    time_context = None
    birth_date = subject.get('birth_date')
    lunar_date = subject.get('lunar_date')
    if not birth_date and not lunar_date:
        for name in ('bazi', 'ziwei', 'astrology'):
            dimensions[name] = _missing_dimension(
                'missing_input', '缺出生日期或农历日期；该维度未计算')
        return ({'schema_version': 2, 'status': 'partial', 'time_context': None,
                 'methods': dict(METHODS), 'dimensions': dimensions,
                 'errors': [], 'limitations': ['缺出生日期或农历日期；未运行三体系排盘']}, 0)

    time_context = normalize_birth_time(
        subject, time_input, as_of=intake.get('analysis_as_of'))
    if not intake.get('analysis_as_of'):
        zone_name = time_context.get('timezone', {}).get('name')
        try:
            if zone_name:
                from zoneinfo import ZoneInfo
                as_of = datetime.now(ZoneInfo(zone_name)).date().isoformat()
            else:
                as_of = datetime.now().date().isoformat()
        except Exception:
            as_of = datetime.now().date().isoformat()
        intake['analysis_as_of'] = as_of
        time_context['analysis_as_of'] = as_of
    limitations.extend(time_context.get('limitations', []))
    from bazi_calc import calc_bazi
    from ziwei_calc import calc_ziwei
    from astro_calc import calc_chart

    calls = (
        ('bazi', lambda: calc_bazi(
            time_context, subject.get('calculation_sex'),
            zi_hour_rule=zi_hour_rule,
            analysis_as_of=intake.get('analysis_as_of'),
            timing_request=intake.get('timing_request'))),
        ('ziwei', lambda: calc_ziwei(
            time_context, subject.get('calculation_sex'),
            intake.get('analysis_as_of'))),
        ('astrology', lambda: calc_chart(
            time_context, house_system=house_system)),
    )
    for name, compute in calls:
        try:
            result = compute()
            dimensions[name] = result
            limitations.extend(result.get('limitations', []))
        except InputError:
            raise
        except Exception as exc:
            dimensions[name] = _dimension_error(exc)
            errors.append({'code': getattr(exc, 'code', 'calculation_error'),
                           'path': getattr(exc, 'path', name),
                           'message': getattr(exc, 'message', str(exc))})
    status = 'error' if errors else (
        'partial' if limitations or any(d['status'] != 'ok' for d in dimensions.values())
        else 'ok')
    bundle = {
        'schema_version': 2, 'status': status,
        'time_context': time_context,
        'methods': {**METHODS, 'zi_hour_rule': zi_hour_rule,
                    'house_system': house_system,
                    'analysis_as_of': intake.get('analysis_as_of')},
        'dimensions': dimensions, 'errors': errors,
        'limitations': list(dict.fromkeys(limitations)),
    }
    return bundle, 1 if errors else 0


def main() -> None:
    try:
        args, options = parse_args(sys.argv[1:])
        intake, subject, time_input = _load_case(args, options)
        bundle, exit_code = build_bundle(
            intake, subject, time_input,
            zi_hour_rule=options['zi_hour_rule'],
            house_system=options['house_system'],
        )
        print(json.dumps(bundle, ensure_ascii=False, allow_nan=False, default=str))
        if exit_code:
            print('; '.join(error['message'] for error in bundle['errors']), file=sys.stderr)
        sys.exit(exit_code)
    except Exception as exc:
        code = 2 if isinstance(exc, (InputError, FileNotFoundError, json.JSONDecodeError)) else 1
        print(json.dumps({'schema_version': 2, 'status': 'error',
                          'time_context': None, 'methods': dict(METHODS),
                          'dimensions': {}, 'errors': [{
                              'code': getattr(exc, 'code', 'calculation_error'),
                              'path': getattr(exc, 'path', ''),
                              'message': getattr(exc, 'message', str(exc))}],
                          'limitations': []}, ensure_ascii=False))
        print(f'cast_chart: {exc}', file=sys.stderr)
        sys.exit(code)


if __name__ == '__main__':
    main()
