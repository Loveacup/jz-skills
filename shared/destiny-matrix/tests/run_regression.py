#!/usr/bin/env python3
# v4.1
"""destiny-matrix 回归测试运行器

跑遍 regression_baseline.json 中所有命例，比对 cast_chart.py 输出与期望锚点。

v4.1 起每条用例额外做「占星直调对照」：用钟表时原值直接调用 astro_calc.py，
要求与 cast_chart.py 占星段的儒略日与上升黄经完全一致——专门拦截
「占星段被喂了真太阳时校正后时刻」这类时间管线错误（v4.0 潜伏三个月的 🔴）。

用法（解释器用 venv，见 SKILL.md「运行环境」）:
    $DM_PY tests/run_regression.py                # 跑全部
    $DM_PY tests/run_regression.py --id 毛泽东     # 跑单条
    $DM_PY tests/run_regression.py --category boundary  # 只跑边界用例
    $DM_PY tests/run_regression.py --verbose      # 显示每条详情

退出码:
    0  全部 PASS / WARN
    1  存在 FAIL
    2  基线无法加载 / 过滤条件未匹配任何用例
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

BASELINE = Path(__file__).parent / 'regression_baseline.json'
SCRIPTS = Path(__file__).parent.parent / 'scripts'
CAST_CHART = SCRIPTS / 'cast_chart.py'
ASTRO_CALC = SCRIPTS / 'astro_calc.py'

# 度数级锚点容差：输出保留 2 位小数，容差取 0.02°
DEG_TOL = 0.02

import os

# 中文星座关键字（占星输出形如 "天秤座 7.24° (落 7 宫)"）
ZODIAC_KEYS = [
    '白羊', '金牛', '双子', '巨蟹', '狮子', '处女',
    '天秤', '天蝎', '射手', '摩羯', '水瓶', '双鱼',
]


# ---------- 辅助提取函数 ----------

def safe_get(d: Any, *path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def extract_zodiac(text: str) -> str | None:
    """从 '天秤座 7.24° (落 7 宫)' 中提取 '天秤'"""
    if not text or not isinstance(text, str):
        return None
    for k in ZODIAC_KEYS:
        if k in text:
            return k
    return None


def sign_lon(sign: str | None, deg_in_sign: float | None) -> float | None:
    """星座 + 宫内度数 → 黄经（0-360）"""
    if sign not in ZODIAC_KEYS or deg_in_sign is None:
        return None
    return round(ZODIAC_KEYS.index(sign) * 30 + float(deg_in_sign), 2)


def extract_asc_lon(astro: dict) -> float | None:
    """上升黄经 = 第 1 宫宫始星座 × 30 + 宫内度数"""
    houses = safe_get(astro, '十二宫', default=[])
    if not isinstance(houses, list) or not houses:
        return None
    h1 = next((h for h in houses if isinstance(h, dict) and h.get('宫位') == 1), None)
    if not h1:
        return None
    return sign_lon(h1.get('宫始星座'), h1.get('宫内度数'))


def extract_planet_lon(astro: dict, planet: str) -> float | None:
    v = safe_get(astro, '十大行星+北交+凯龙', planet, '黄经')
    return round(float(v), 2) if v is not None else None


def extract_dominant_element(ratios: dict) -> str | None:
    """从 五行比例 dict 中找最大者"""
    if not ratios or not isinstance(ratios, dict):
        return None
    try:
        return max(ratios.items(), key=lambda kv: kv[1])[0]
    except Exception:
        return None


def find_ming_palace(twelve: list) -> dict | None:
    if not isinstance(twelve, list):
        return None
    for g in twelve:
        if isinstance(g, dict) and g.get('宫位') == '命宫':
            return g
    return None


# ---------- 单条用例执行 ----------

def run_cast_chart(inp: dict, timeout: int = 60) -> tuple[dict | None, str]:
    """调用 cast_chart.py，返回 (json_dict_or_None, 错误信息)

    使用 sys.executable：测试与子脚本同一解释器（cast_chart.py 内部亦然）。
    """
    cmd = [sys.executable, str(CAST_CHART),
           inp['date'], inp['time'], inp['gender'], inp['city']]
    if 'lat' in inp:
        cmd.append(f'--lat={inp["lat"]}')
    if 'lon' in inp:
        cmd.append(f'--lon={inp["lon"]}')
    if 'tz' in inp:
        cmd.append(f'--tz={inp["tz"]}')

    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f'cast_chart.py timeout ({timeout}s)'
    except Exception as e:
        return None, f'subprocess 异常: {type(e).__name__}: {e}'

    if result.returncode != 0:
        return None, f'cast_chart.py exit={result.returncode}; stderr={result.stderr.strip()[:300]}'
    try:
        return json.loads(result.stdout), ''
    except json.JSONDecodeError as e:
        return None, f'输出非 JSON: {e}; head={result.stdout[:200]}'


def astro_direct_check(inp: dict, out: dict) -> list:
    """占星直调对照：钟表时原值直调 astro_calc.py，儒略日与上升黄经须与 cast_chart 占星段一致。

    lat/lon/tz 取 cast_chart 已解析的地理结果（本检查只针对时间管线，不针对地名解析）。
    返回失败信息列表（空 = 一致）。
    """
    sys.path.insert(0, str(SCRIPTS))
    try:
        import cast_chart  # noqa: E402
    finally:
        sys.path.pop(0)
    y, m, d = map(int, inp['date'].split('-'))
    opts = {'lat': inp.get('lat'), 'lon': inp.get('lon'), 'tz': inp.get('tz'),
            'use_true_solar_time': True}
    geo = cast_chart._resolve_geo(inp['city'], opts, y, m, d)
    if not geo['resolved']:
        return [f'直调对照：城市 {inp["city"]!r} 未解析']
    tz_arg = str(inp['tz']) if inp.get('tz') is not None else (geo['iana_tz'] or str(geo['utc_offset']))
    cmd = [sys.executable, str(ASTRO_CALC), inp['date'], inp['time'],
           str(geo['lat']), str(geo['lon']), tz_arg]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return [f'直调对照：astro_calc exit={r.returncode}; {r.stderr.strip()[:200]}']
    direct = json.loads(r.stdout)
    chart = out.get('占星', {})
    fails = []
    jd_c = safe_get(chart, '出生信息', '儒略日')
    jd_d = safe_get(direct, '出生信息', '儒略日')
    if jd_c is None or jd_d is None or abs(jd_c - jd_d) > 1e-6:
        fails.append(f'直调对照：儒略日 cast_chart={jd_c} ≠ 直调={jd_d}（占星时刻被改动）')
    asc_c, asc_d = extract_asc_lon(chart), extract_asc_lon(direct)
    if asc_c is None or asc_d is None or abs(asc_c - asc_d) > DEG_TOL:
        fails.append(f'直调对照：上升黄经 cast_chart={asc_c} ≠ 直调={asc_d}')
    return fails


def compare_anchors(expected: dict, out: dict, nullable: set) -> tuple[list, list, list]:
    """返回 (fails, warns, oks)。fails/warns 元素形如 '锚点名: expected=X, actual=Y'。
    人工 review 字段（推断 MBTI / 性格签名锚点）跳过。
    """
    fails, warns, oks = [], [], []

    skip_keys = {'推断 MBTI', '性格签名锚点'}

    for key, exp_val in expected.items():
        if key in skip_keys:
            continue

        actual = None

        if key == 'bazi_day_master':
            actual = safe_get(out, '八字', '日主', '天干')
        elif key == 'bazi_day_master_element':
            actual = safe_get(out, '八字', '日主', '五行')
        elif key == 'bazi_dominant_element':
            actual = extract_dominant_element(safe_get(out, '八字', '五行比例', default={}))
        elif key == 'ziwei_ming_palace_stars':
            ming = find_ming_palace(safe_get(out, '紫微', '十二宫', default=[]))
            stars = []
            if ming:
                stars = [s.get('名称') for s in ming.get('主星', []) if isinstance(s, dict)]
            actual = stars
            # 期望可能是单字符串或数组，统一为集合比对
            exp_set = set(exp_val) if isinstance(exp_val, list) else {exp_val}
            act_set = set(stars)
            if not (exp_set & act_set):  # 没有任何一个命中
                msg = f'{key}: expected={sorted(exp_set)}, actual={sorted(act_set)}'
                (warns if key in nullable else fails).append(msg)
            else:
                oks.append(f'{key}={sorted(act_set)}')
            continue
        elif key == 'ziwei_ming_branch':
            actual = safe_get(out, '紫微', '基础信息', '命宫地支')
        elif key == 'ziwei_wuxing_ju':
            actual = safe_get(out, '紫微', '基础信息', '五行局')
        elif key == 'astro_sun_sign':
            actual = extract_zodiac(safe_get(out, '占星', '三轴心', '太阳', default=''))
        elif key == 'astro_rising_sign':
            actual = extract_zodiac(safe_get(out, '占星', '三轴心', '上升', default=''))
        elif key == 'astro_moon_sign':
            actual = extract_zodiac(safe_get(out, '占星', '三轴心', '月亮', default=''))
        elif key in ('astro_asc_lon', 'astro_sun_lon', 'astro_moon_lon'):
            astro = out.get('占星', {})
            actual = (extract_asc_lon(astro) if key == 'astro_asc_lon'
                      else extract_planet_lon(astro, '太阳' if key == 'astro_sun_lon' else '月亮'))
            if actual is not None and abs(actual - float(exp_val)) <= DEG_TOL:
                oks.append(f'{key}={actual}')
            else:
                msg = f'{key}: expected={exp_val!r}±{DEG_TOL}, actual={actual!r}'
                (warns if key in nullable else fails).append(msg)
            continue
        else:
            warns.append(f'{key}: 未识别的锚点字段（跳过）')
            continue

        if actual == exp_val:
            oks.append(f'{key}={actual}')
        else:
            msg = f'{key}: expected={exp_val!r}, actual={actual!r}'
            (warns if key in nullable else fails).append(msg)

    return fails, warns, oks


def run_case(case: dict) -> dict:
    """跑一条用例，返回 {id, status, ...}"""
    cid = case['id']
    if case.get('skip'):
        return {'id': cid, 'status': 'SKIP', 'reason': case.get('skip_reason', 'marked skip')}

    inp = case.get('input', {})
    expected = case.get('expected_anchors', {})
    nullable = set(case.get('nullable', []))

    out, err = run_cast_chart(inp)
    if out is None:
        return {'id': cid, 'status': 'FAIL', 'reason': err}

    # 子脚本部分错误：判定哪些锚点关联了失效模块
    sub_errors = {}
    for sub in ('八字', '紫微', '占星'):
        if isinstance(out.get(sub), dict) and 'error' in out[sub]:
            sub_errors[sub] = out[sub].get('error')

    # 模块名 → 该模块对应的锚点前缀
    module_to_prefix = {
        '八字': 'bazi_',
        '紫微': 'ziwei_',
        '占星': 'astro_',
    }
    # 哪些 expected 锚点受子脚本失败影响（这些字段比对会跳过）
    affected_anchors = set()
    for sub in sub_errors:
        prefix = module_to_prefix[sub]
        affected_anchors.update(k for k in expected if k.startswith(prefix))

    # 过滤掉受影响的锚点后，再比对剩余锚点
    expected_filtered = {k: v for k, v in expected.items() if k not in affected_anchors}
    fails, warns, oks = compare_anchors(expected_filtered, out, nullable)

    # 把子脚本失败本身记录到 warns/fails（按 nullable 决定降级）
    for sub, err in sub_errors.items():
        prefix = module_to_prefix[sub]
        related = [a for a in expected if a.startswith(prefix)]
        msg = f'{sub} 子脚本异常: {err}'
        # 该模块没有声明锚点 → WARN（用例不在乎该模块）
        # 该模块所有锚点都 nullable → WARN
        # 其它情况 → FAIL
        if not related or all(a in nullable for a in related):
            warns.append(msg)
        else:
            fails.append(msg)

    # 占星直调对照（占星子脚本正常时必做；不受 nullable 影响——这是管线一致性，不是史料问题）
    if '占星' not in sub_errors:
        fails.extend(astro_direct_check(inp, out))

    if fails:
        status = 'FAIL'
    elif warns:
        status = 'WARN'
    else:
        status = 'PASS'

    return {
        'id': cid,
        'status': status,
        'fails': fails,
        'warns': warns,
        'oks': oks,
        'note': case.get('note'),
    }


# ---------- 主流程 ----------

def main() -> int:
    parser = argparse.ArgumentParser(description='destiny-matrix v3 回归测试')
    parser.add_argument('--id', help='只跑指定 id 的用例')
    parser.add_argument('--category', help='只跑指定 category（celebrity / boundary）')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示每条用例的命中锚点')
    args = parser.parse_args()

    try:
        with open(BASELINE, encoding='utf-8') as f:
            baseline = json.load(f)
    except Exception as e:
        print(f'ERROR: 无法加载 {BASELINE}: {e}', file=sys.stderr)
        return 2

    cases = baseline.get('cases', [])
    if args.id:
        cases = [c for c in cases if c.get('id') == args.id]
    if args.category:
        cases = [c for c in cases if c.get('category') == args.category]

    if not cases:
        print('没有匹配的用例（检查 --id / --category 拼写）。', file=sys.stderr)
        return 2

    print(f'== destiny-matrix 回归测试 == 共 {len(cases)} 条 ==\n')

    results = []
    counters = {'PASS': 0, 'WARN': 0, 'FAIL': 0, 'SKIP': 0}

    for i, case in enumerate(cases, 1):
        cid = case.get('id', f'case#{i}')
        print(f'[{i}/{len(cases)}] {cid} ...', end=' ', flush=True)
        try:
            r = run_case(case)
        except Exception as e:
            r = {'id': cid, 'status': 'FAIL', 'reason': f'runner 异常: {type(e).__name__}: {e}'}
        results.append(r)
        counters[r['status']] = counters.get(r['status'], 0) + 1
        print(r['status'])
        if args.verbose and r.get('oks'):
            for ok in r['oks']:
                print(f'    + {ok}')

    print()
    print('=' * 50)
    print('=== 回归测试汇总 ===')
    total = len(cases)
    print(f'通过 PASS : {counters.get("PASS", 0):3d} / {total}')
    print(f'警告 WARN : {counters.get("WARN", 0):3d}')
    print(f'失败 FAIL : {counters.get("FAIL", 0):3d}')
    print(f'跳过 SKIP : {counters.get("SKIP", 0):3d}')
    print()

    fail_results = [r for r in results if r['status'] == 'FAIL']
    warn_results = [r for r in results if r['status'] == 'WARN']

    if fail_results:
        print('--- FAIL 详情 ---')
        for r in fail_results:
            print(f'  [{r["id"]}]')
            if r.get('reason'):
                print(f'    reason: {r["reason"]}')
            for f in r.get('fails', []):
                print(f'    FAIL: {f}')
            if r.get('note'):
                print(f'    note: {r["note"]}')

    if warn_results:
        print('--- WARN 详情 ---')
        for r in warn_results:
            print(f'  [{r["id"]}]')
            for w in r.get('warns', []):
                print(f'    WARN: {w}')

    return 0 if counters.get('FAIL', 0) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
