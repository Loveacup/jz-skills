#!/usr/bin/env python3
"""v5 legacy input pipeline checks; these cases do not claim chart accuracy."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BASELINE = Path(__file__).with_name('regression_baseline.json')
ROOT = BASELINE.parent.parent
SCRIPTS = ROOT / 'scripts'
CAST_CHART = SCRIPTS / 'cast_chart.py'
ASTRO_CALC = SCRIPTS / 'astro_calc.py'
CHART_SCHEMA = ROOT / 'schemas/chart_bundle.json'
ANALYSIS_AS_OF = '2026-01-15'


def safe_get(value: Any, *path, default=None):
    current = value
    for key in path:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return default
    return current


def extract_zodiac(text: str) -> str | None:
    if not isinstance(text, str):
        return None
    for sign in ('白羊', '金牛', '双子', '巨蟹', '狮子', '处女',
                 '天秤', '天蝎', '射手', '摩羯', '水瓶', '双鱼'):
        if sign in text:
            return sign
    return None


def find_ming_palace(value: Any) -> dict | None:
    if not isinstance(value, list):
        return None
    return next((row for row in value if isinstance(row, dict)
                 and row.get('宫位') in {'命宫', '命宫宫'}), None)


def extract_actual(key: str, bundle: dict):
    bazi = safe_get(bundle, 'dimensions', 'bazi', 'data', default={}) or {}
    ziwei = safe_get(bundle, 'dimensions', 'ziwei', 'data', default={}) or {}
    astro = safe_get(bundle, 'dimensions', 'astrology', 'data', default={}) or {}
    if key in {'bazi_year_pillar', 'bazi_month_pillar'}:
        pillar = '年柱' if key == 'bazi_year_pillar' else '月柱'
        row = next((item for item in bazi.get('四柱', [])
                    if isinstance(item, dict) and item.get('柱') == pillar), None)
        return row.get('干支') if row else None
    if key == 'bazi_day_master':
        return safe_get(bazi, '日主', '天干')
    if key == 'bazi_day_master_element':
        return safe_get(bazi, '日主', '五行')
    if key == 'bazi_dominant_element':
        ratios = bazi.get('五行比例', {})
        return max(ratios, key=ratios.get) if ratios else None
    if key == 'ziwei_ming_palace_stars':
        palace = find_ming_palace(ziwei.get('十二宫', [])) or {}
        return [item.get('名称') for item in palace.get('主星', [])
                if isinstance(item, dict)]
    if key == 'ziwei_ming_branch':
        return safe_get(ziwei, '基础信息', '命宫地支')
    if key == 'ziwei_wuxing_ju':
        return safe_get(ziwei, '基础信息', '五行局')
    if key in {'astro_sun_sign', 'astro_rising_sign', 'astro_moon_sign'}:
        field = {'astro_sun_sign': '太阳', 'astro_rising_sign': '上升',
                 'astro_moon_sign': '月亮'}[key]
        return extract_zodiac(safe_get(astro, '三轴心', field, default=''))
    if key in {'astro_asc_lon', 'astro_sun_lon', 'astro_moon_lon'}:
        if key == 'astro_asc_lon':
            raw = safe_get(astro, 'ASC_MC_原始黄经', 'ASC')
        else:
            name = '太阳' if key == 'astro_sun_lon' else '月亮'
            raw = safe_get(astro, '十大行星+北交+凯龙+莉莉丝', name, '黄经')
        return float(raw) if raw is not None else None
    raise ValueError(f'未知精确锚点字段: {key}')


def validate_anchor_metadata(case: dict) -> list[str]:
    anchors = case.get('expected_anchors', [])
    if not isinstance(anchors, list):
        return [f'{case.get("id")}: expected_anchors 必须为带来源元数据的数组']
    issues = []
    nullable = set(case.get('nullable_anchors', []))
    for row in anchors:
        if not isinstance(row, dict):
            issues.append(f'{case.get("id")}: anchor 必须为对象')
            continue
        key = row.get('id')
        if not key:
            issues.append(f'{case.get("id")}: anchor 缺少 id')
            continue
        try:
            extract_actual(key, {})
        except ValueError as exc:
            issues.append(f'{case.get("id")}: {exc}')
        for field in ('value', 'source', 'locator', 'method', 'dependency_version', 'tolerance'):
            if field not in row or row[field] is None or row[field] == '':
                issues.append(f'{case.get("id")}.{key}: 缺少锚点元数据 {field}')
        if row.get('source_status') not in {'verified', 'disputed'}:
            issues.append(f'{case.get("id")}.{key}: source_status 必须为 verified/disputed')
        if row.get('source_status') == 'disputed' and key not in nullable:
            issues.append(f'{case.get("id")}.{key}: 史料争议锚点必须列入 nullable_anchors')
        tol = row.get('tolerance')
        if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or tol < 0:
            issues.append(f'{case.get("id")}.{key}: tolerance 必须为有限非负数')
    if nullable - {row.get('id') for row in anchors if isinstance(row, dict)}:
        issues.append(f'{case.get("id")}: nullable_anchors 指向不存在的锚点')
    return issues


def validate_contract_metadata(case: dict) -> list[str]:
    contracts = case.get('expected_contracts', [])
    if not isinstance(contracts, list):
        return [f'{case.get("id")}: expected_contracts 必须为数组']
    known = {'placidus_unavailable', 'asc_mc_available', 'whole_sign_available'}
    seen = set()
    issues = []
    for row in contracts:
        if not isinstance(row, dict) or row.get('id') not in known:
            issues.append(f'{case.get("id")}: expected_contracts 有未知断言')
            continue
        key = row['id']
        if key in seen:
            issues.append(f'{case.get("id")}: expected_contracts 重复 {key}')
        seen.add(key)
        if type(row.get('value')) is not bool:
            issues.append(f'{case.get("id")}.{key}: value 必须为布尔值')
    return issues


def contract_value(key: str, bundle: dict) -> bool:
    astro = safe_get(bundle, 'dimensions', 'astrology', 'data', default={}) or {}
    raw_angles = astro.get('ASC_MC_原始黄经')
    if key == 'placidus_unavailable':
        return (astro.get('requested_house_system') == 'placidus'
                and astro.get('宫位制') == 'unavailable'
                and astro.get('十二宫始黄经') is None)
    if key == 'asc_mc_available':
        axis = astro.get('三轴心')
        return (isinstance(raw_angles, dict)
                and all(isinstance(raw_angles.get(name), (int, float))
                        and not isinstance(raw_angles.get(name), bool)
                        and math.isfinite(raw_angles[name])
                        and 0 <= raw_angles[name] < 360
                        for name in ('ASC', 'MC'))
                and isinstance(axis, dict)
                and '上升' in axis and '天顶MC' in axis)
    if key == 'whole_sign_available':
        cusps = astro.get('十二宫始黄经')
        return (astro.get('requested_house_system') == 'whole_sign'
                and astro.get('宫位制') == 'Whole Sign'
                and isinstance(cusps, list) and len(cusps) == 12)
    raise ValueError(f'未知合同断言: {key}')


def compare_contracts(case: dict, bundle: dict) -> list[str]:
    failures = []
    for row in case.get('expected_contracts', []):
        actual = contract_value(row['id'], bundle)
        if actual is not row['value']:
            failures.append(f'{row["id"]}: expected={row["value"]!r}, actual={actual!r}')
    return failures


def compare_anchors(case: dict, bundle: dict) -> tuple[list[str], list[str]]:
    failures, warnings = [], []
    nullable = set(case.get('nullable_anchors', []))
    for row in case.get('expected_anchors', []):
        key, expected = row['id'], row['value']
        actual = extract_actual(key, bundle)
        tolerance = row['tolerance']
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            matched = actual is not None and abs(float(actual) - float(expected)) <= tolerance
        elif key == 'ziwei_ming_palace_stars':
            exp = set(expected if isinstance(expected, list) else [expected])
            matched = bool(exp & set(actual or []))
        else:
            matched = actual == expected
        if not matched:
            message = f'{key}: expected={expected!r} ±{tolerance}, actual={actual!r}'
            (warnings if key in nullable else failures).append(message)
    return failures, warnings


def make_intake(case: dict) -> dict:
    raw = case['input']
    location = {}
    if raw.get('city'):
        location['city'] = raw['city']
    if raw.get('latitude') is not None:
        location['latitude'] = raw['latitude']
    if raw.get('longitude') is not None:
        location['longitude'] = raw['longitude']
    subject = {
        'birth_date': raw.get('birth_date'), 'lunar_date': raw.get('lunar_date'),
        'date_calendar': case.get('date_calendar', 'gregorian'),
        'calculation_sex': raw.get('calculation_sex'), 'location': location,
    }
    precision = raw.get('precision', 'minute')
    start = raw.get('time_input_start')
    if start is None and raw.get('birth_date') and raw.get('birth_time'):
        start = f"{raw['birth_date']}T{raw['birth_time']}"
    time_input = {
        'precision': precision, 'start': start,
        'end': raw.get('time_input_end'), 'branch_label': raw.get('branch_label'),
        'timezone_name': raw.get('timezone_name'),
        'utc_offset_hours': raw.get('utc_offset_hours'), 'fold': None,
        'clock_basis': 'civil',
    }
    return {
        'analysis_as_of': ANALYSIS_AS_OF, 'subject': subject,
        'time_input': time_input,
        'timing_request': {'years': [], 'months': [], 'systems': []},
    }


def run_cast_chart(case: dict, timeout: int = 60) -> tuple[dict | None, str]:
    intake = make_intake(case)
    try:
        with tempfile.TemporaryDirectory(prefix='dm-regression-') as temp_dir:
            intake_path = Path(temp_dir) / 'intake.json'
            intake_path.write_text(json.dumps(intake, ensure_ascii=False), encoding='utf-8')
            command = [sys.executable, str(CAST_CHART), '--intake', str(intake_path)]
            if case.get('house_system'):
                command.extend(['--house-system', case['house_system']])
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f'cast_chart.py timeout ({timeout}s)'
    except OSError as exc:
        return None, f'cast_chart.py 无法启动: {exc}'
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f'输出非 JSON: {exc}; stdout={result.stdout[:200]!r}; stderr={result.stderr[:200]!r}'
    if result.returncode:
        return None, f'cast_chart.py exit={result.returncode}; response={output!r}; stderr={result.stderr[:300]}'
    return output, ''


def check_parameter_pipeline(case: dict, bundle: dict, timeout: int = 60) -> list[str]:
    """Compare cast and direct astro CLI outputs; same implementation, not independent-engine evidence."""
    context = bundle.get('time_context') or {}
    if context.get('precision') != 'minute':
        return []
    raw = case['input']
    location = context.get('location', {})
    lat, lon = location.get('latitude'), location.get('longitude')
    if lat is None or lon is None:
        return ['占星参数管线检查缺少规范化坐标']
    command = [sys.executable, str(ASTRO_CALC), raw['birth_date'], raw['birth_time'],
               str(lat), str(lon),
               f"--house-system={case.get('house_system', 'placidus')}"]
    timezone_name = context.get('timezone', {}).get('name')
    offset = raw.get('utc_offset_hours')
    if timezone_name and offset is None:
        command.append(f'--tz-name={timezone_name}')
    else:
        if offset is None:
            offset = context.get('timezone', {}).get('utc_offset_hours')
        command.append(f'--tz={offset}')
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        direct = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
        return [f'astro_calc 参数管线调用失败: {exc}']
    if result.returncode:
        return [f'astro_calc 参数管线 exit={result.returncode}: {direct!r}']
    cast_astro = safe_get(bundle, 'dimensions', 'astrology', 'data', default={}) or {}
    direct_astro = direct.get('data') or {}
    checks = [
        ('UTC instant', safe_get(cast_astro, '出生信息', 'UTC'),
         safe_get(direct_astro, '出生信息', 'UTC'), 0.0),
        ('UT1 JD', safe_get(cast_astro, '出生信息', 'UT1 儒略日'),
         safe_get(direct_astro, '出生信息', 'UT1 儒略日'), 1e-10),
        ('ASC longitude', safe_get(cast_astro, 'ASC_MC_原始黄经', 'ASC'),
         safe_get(direct_astro, 'ASC_MC_原始黄经', 'ASC'), 1e-8),
    ]
    failures = []
    for label, actual, expected, tolerance in checks:
        if actual is None or expected is None:
            failures.append(f'{label}: 缺少 cast/direct 结果 ({actual!r}, {expected!r})')
        elif isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            if abs(actual - expected) > tolerance:
                failures.append(f'{label}: cast={actual!r}, direct={expected!r}')
        elif actual != expected:
            failures.append(f'{label}: cast={actual!r}, direct={expected!r}')
    return failures


def run_case(case: dict) -> dict:
    cid = case['id']
    if case.get('input_status') == 'calendar_pending_confirmation':
        return {'id': cid, 'status': 'BLOCKED', 'reason': case.get('review_reason')}
    bundle, error = run_cast_chart(case)
    if bundle is None:
        return {'id': cid, 'status': 'FAIL', 'reason': error}
    from jsonschema import Draft202012Validator
    schema = json.loads(CHART_SCHEMA.read_text(encoding='utf-8'))
    schema_errors = list(Draft202012Validator(schema).iter_errors(bundle))
    if schema_errors:
        return {'id': cid, 'status': 'FAIL',
                'reason': '; '.join(f'{e.json_path}: {e.message}' for e in schema_errors)}
    if bundle.get('status') == 'error' or any(
            bundle['dimensions'][key].get('status') == 'error'
            for key in ('bazi', 'ziwei', 'astrology')):
        return {'id': cid, 'status': 'FAIL', 'reason': 'bundle 声明计算错误'}
    anchor_failures, anchor_warnings = compare_anchors(case, bundle)
    contract_failures = compare_contracts(case, bundle)
    pipeline_failures = check_parameter_pipeline(case, bundle)
    failures = anchor_failures + contract_failures + pipeline_failures
    if failures:
        return {'id': cid, 'status': 'FAIL', 'fails': failures,
                'warns': anchor_warnings, 'dimension_statuses': {
                    key: bundle['dimensions'][key]['status']
                    for key in ('bazi', 'ziwei', 'astrology')}}
    if anchor_warnings:
        status = 'WARN'
    elif case.get('expected_anchors') or case.get('expected_contracts'):
        status = 'PASS'
    else:
        status = 'CONTRACT_OK'
    return {'id': cid, 'status': status, 'warns': anchor_warnings,
            'dimension_statuses': {
                key: bundle['dimensions'][key]['status']
                for key in ('bazi', 'ziwei', 'astrology')},
            'accuracy_claim': False}


def main() -> int:
    parser = argparse.ArgumentParser(description='destiny-matrix v5 regression pipeline checks')
    parser.add_argument('--id', help='只运行指定 case id')
    parser.add_argument('--category', help='只运行指定 category')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()
    try:
        baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        print(f'ERROR: 无法加载 regression baseline: {exc}', file=sys.stderr)
        return 2
    if baseline.get('_meta', {}).get('version') != '5.0.0':
        print('ERROR: baseline version/schema 未知', file=sys.stderr)
        return 2
    try:
        from jsonschema import Draft202012Validator  # noqa: F401
    except ImportError as exc:
        print(f'ERROR: 缺少 chart_bundle schema 验证依赖: {exc}', file=sys.stderr)
        return 2
    cases = baseline.get('cases', [])
    if args.id:
        cases = [row for row in cases if row.get('id') == args.id]
    if args.category:
        cases = [row for row in cases if row.get('category') == args.category]
    if not cases:
        print('ERROR: 没有匹配的用例', file=sys.stderr)
        return 2
    metadata_errors = [
        issue
        for case in cases
        for issue in validate_anchor_metadata(case) + validate_contract_metadata(case)
    ]
    if metadata_errors:
        print('ERROR: exact anchor metadata 不完整（不得从待测实现反向生成 expected）')
        for issue in metadata_errors:
            print(f'  {issue}')
        return 2

    totals = {'PASS': 0, 'CONTRACT_OK': 0, 'WARN': 0, 'BLOCKED': 0, 'FAIL': 0}
    results = []
    for index, case in enumerate(cases, 1):
        result = run_case(case)
        results.append(result)
        totals[result['status']] += 1
        print(f'[{index}/{len(cases)}] {result["id"]}: {result["status"]}')
        if args.verbose:
            for key in ('reason', 'fails', 'warns', 'dimension_statuses'):
                if result.get(key):
                    print(f'  {key}: {result[key]}')
    print('汇总:', json.dumps(totals, ensure_ascii=False))
    print('说明: CONTRACT_OK 仅表示 chart_bundle v2 与参数管线通过，不证明命例资料或解释准确。')
    if totals['FAIL'] or totals['BLOCKED']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
