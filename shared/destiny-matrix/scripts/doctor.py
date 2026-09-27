#!/usr/bin/env python3
"""destiny-matrix 第 0 步 preflight（v4.1）。只用标准库，任何 python3 都能跑。

用法:
  python3 doctor.py            # 人读摘要
  python3 doctor.py --json     # 结构化输出（Leader 读 dm_root / dm_py 注入派遣）
  python3 doctor.py --regression   # 额外跑完整回归（约 15 秒）

解析 $DM_PY 的顺序：环境变量 DM_PY → ~/.local/share/destiny-matrix/venv/bin/python
→ 当前解释器 → PATH 上的 python3；取第一个依赖齐备者。

退出码: 0 = 无 🔴；1 = 存在 🔴（停线报用户，不降级运行）
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DM_ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
DEFAULT_VENV_PY = HOME / '.local/share/destiny-matrix/venv/bin/python'

CORE_MODULES = ['lunar_python', 'iztro_py', 'swisseph', 'sxtwl', 'geonamescache', 'timezonefinder']
EXPORT_MODULES = ['playwright', 'pypdf']
OPTIONAL_MODULES = ['kerykeion']
TIERS = ['dm-deep', 'dm-research', 'dm-light']

checks: list[dict] = []


def add(cid: str, level: str, detail: str) -> None:
    checks.append({'id': cid, 'level': level, 'detail': detail})


def probe_modules(py: str) -> dict:
    code = ('import importlib,json,sys\nr={}\n'
            'for m in sys.argv[1:]:\n'
            '    try: importlib.import_module(m); r[m]=True\n'
            '    except Exception: r[m]=False\n'
            'print(json.dumps({"version": sys.version.split()[0], "mods": r}))')
    try:
        out = subprocess.run([py, '-c', code, *CORE_MODULES, *EXPORT_MODULES, *OPTIONAL_MODULES],
                             capture_output=True, text=True, timeout=60)
        return json.loads(out.stdout)
    except Exception as e:  # 解释器不存在 / 崩溃
        return {'error': f'{type(e).__name__}: {e}'}


def resolve_dm_py() -> str | None:
    cands = []
    if os.environ.get('DM_PY'):
        cands.append(os.environ['DM_PY'])
    cands += [str(DEFAULT_VENV_PY), sys.executable, shutil.which('python3') or '']
    seen = set()
    for c in cands:
        if not c or c in seen or not Path(c).exists():
            continue
        seen.add(c)
        r = probe_modules(c)
        mods = r.get('mods', {})
        missing = [m for m in CORE_MODULES + EXPORT_MODULES if not mods.get(m)]
        if not missing:
            opt = [m for m in OPTIONAL_MODULES if not mods.get(m)]
            add('python', 'green', f'{c}（Python {r["version"]}）依赖齐备'
                + (f'；可选缺 {opt}（占星 SVG 圆盘不可用）' if opt else ''))
            return c
        add('python.candidate', 'yellow', f'{c} 缺 {missing}' if 'error' not in r else f'{c}: {r["error"]}')
    add('python', 'red', '没有依赖齐备的解释器。建 venv：'
        f'python3.12 -m venv {DEFAULT_VENV_PY.parent.parent} && {DEFAULT_VENV_PY} -m pip install '
        + ' '.join(['lunar_python', 'iztro-py', 'pyswisseph', 'sxtwl', 'geonamescache', 'timezonefinder',
                    'kerykeion', 'playwright', 'pypdf'])
        + f' && {DEFAULT_VENV_PY} -m playwright install chromium')
    return None


def check_chromium(py: str) -> None:
    code = ('from playwright.sync_api import sync_playwright\n'
            'p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop(); print("ok")')
    r = subprocess.run([py, '-c', code], capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and 'ok' in r.stdout:
        add('pdf.chromium', 'green', 'playwright chromium 可启动（S10 export_pdf 可用）')
    else:
        add('pdf.chromium', 'red', f'playwright chromium 启动失败：{r.stderr.strip()[-300:]}；'
            f'修复：{py} -m playwright install chromium')


def check_cast(py: str) -> None:
    """判官隔离与时间管线自检：排一张固定样盘。"""
    r = subprocess.run([py, str(DM_ROOT / 'scripts/cast_chart.py'), '1990-01-15', '08:30', 'm', '北京'],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        add('cast', 'red', f'cast_chart.py exit={r.returncode}: {r.stderr.strip()[-300:]}')
        return
    d = json.loads(r.stdout)
    errs = [k for k in ('八字', '紫微', '占星') if isinstance(d.get(k), dict) and 'error' in d[k]]
    if errs:
        add('cast', 'red', f'子脚本失败: {errs}')
        return
    add('cast', 'green', '样盘三体系齐备')
    if '性格映射提示' in r.stdout:
        add('isolation.hints', 'red', '排盘 JSON 含「性格映射提示」——会污染 S4 判官（脚本被回退到 v4.0？）')
    else:
        add('isolation.hints', 'green', '排盘 JSON 不含「性格映射提示」')
    if '时刻口径' in d.get('元数据', {}):
        add('astro.clock_time', 'green', '占星段使用钟表时（元数据.时刻口径 存在）')
    else:
        add('astro.clock_time', 'red', 'cast_chart 无「时刻口径」——可能仍是 v4.0 的占星重复校正版本')


def check_regression(py: str) -> None:
    r = subprocess.run([py, str(DM_ROOT / 'tests/run_regression.py')], capture_output=True, text=True, timeout=600)
    tail = r.stdout.strip().splitlines()[-12:]
    add('regression', 'green' if r.returncode == 0 else 'red', ' | '.join(tail))


def check_omp() -> None:
    agents_dir = HOME / '.omp/agent/agents'
    if not (HOME / '.omp').exists():
        add('omp', 'yellow', '未检测到 ~/.omp（非 omp 环境可忽略）')
        return
    for t in TIERS:
        link = agents_dir / f'{t}.md'
        target = DM_ROOT / 'adapters/omp' / f'{t}.md'
        if link.exists() and link.resolve() == target.resolve():
            add(f'omp.agent.{t}', 'green', f'{link} → {target}')
        else:
            add(f'omp.agent.{t}', 'red', f'缺 omp 档位 agent：ln -s {target} {link}')
    skill_links = [HOME / '.agents/skills/destiny-matrix', HOME / '.omp/agent/skills/destiny-matrix']
    found = [str(p) for p in skill_links if p.exists() and p.resolve() == DM_ROOT]
    if found:
        add('omp.skill', 'green', f'omp 可发现本 skill：{found[0]}')
    else:
        add('omp.skill', 'red', f'omp 发现不到本 skill：ln -s {DM_ROOT} {skill_links[0]}')
    cfg = HOME / '.omp/agent/config.yml'
    text = cfg.read_text(encoding='utf-8') if cfg.exists() else ''
    unlocked = [t for t in TIERS if f'{t}: "off"' not in text and f"{t}: off" not in text]
    if unlocked:
        add('omp.prewalk_advisor', 'yellow',
            f'config.yml 未显式锁 off：{unlocked}（frontmatter 已是 false；如需与 sil-* 同样双保险，'
            '在 task.agentPrewalk / task.agentAdvisor 下各加 `dm-xxx: "off"`）')
    else:
        add('omp.prewalk_advisor', 'green', 'config.yml 已锁 dm-* prewalk/advisor off')


def check_cc() -> None:
    v = os.environ.get('CLAUDE_CODE_SUBAGENT_MODEL')
    if v and v != 'inherit':
        add('cc.subagent_model', 'yellow', f'CLAUDE_CODE_SUBAGENT_MODEL={v}：cc 端所有 teammate 会被改用该模型')


def main() -> int:
    as_json = '--json' in sys.argv
    dm_py = resolve_dm_py()
    if dm_py:
        check_chromium(dm_py)
        check_cast(dm_py)
        if '--regression' in sys.argv:
            check_regression(dm_py)
    check_omp()
    check_cc()
    red = [c for c in checks if c['level'] == 'red']
    report = {'dm_root': str(DM_ROOT), 'dm_py': dm_py, 'ok': not red, 'checks': checks}
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        icon = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}
        print(f'DM    = {DM_ROOT}\nDM_PY = {dm_py}')
        for c in checks:
            print(f"{icon[c['level']]} {c['id']}: {c['detail']}")
    return 1 if red else 0


if __name__ == '__main__':
    sys.exit(main())
