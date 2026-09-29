#!/usr/bin/env python3
"""destiny-matrix v5 preflight. Reports interpreter, contracts and a real chart smoke."""
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
CORE_MODULES = [
    'lunar_python', 'iztro_py', 'swisseph', 'sxtwl', 'geonamescache',
    'timezonefinder', 'jsonschema',
]
EXPORT_MODULES = ['playwright', 'pypdf']
TIERS = ['dm-deep', 'dm-research', 'dm-light']

DIST_NAMES = {'lunar_python': 'lunar-python', 'iztro_py': 'iztro-py',
              'swisseph': 'pyswisseph'}
checks: list[dict] = []
def add(cid: str, level: str, detail: str) -> None:
    checks.append({'id': cid, 'level': level, 'detail': detail})


def probe_modules(py: str) -> dict:
    code = (
        'import importlib,importlib.metadata,json,sys\n'
        'mods={}\n'
        f'dist={DIST_NAMES!r}\n'
        'for name in sys.argv[1:]:\n'
        ' try:\n'
        '  mod=importlib.import_module(name)\n'
        '  ver=getattr(mod,"__version__",None) or getattr(mod,"version",None)\n'
        '  if not isinstance(ver,(str,int,float)): ver=importlib.metadata.version(dist.get(name,name))\n'
        '  mods[name]={"ok":True,"version":str(ver)}\n'
        ' except Exception as exc: mods[name]={"ok":False,"error":type(exc).__name__+": "+str(exc)}\n'
        'print(json.dumps({"python":sys.executable,"version":sys.version.split()[0],"modules":mods}))'
    )
    try:
        result = subprocess.run([py, '-c', code, *CORE_MODULES, *EXPORT_MODULES],
                                capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as exc:
        return {'error': 'interpreter_timeout', 'detail': str(exc)}
    except OSError as exc:
        return {'error': 'interpreter_unavailable', 'detail': str(exc)}
    if result.returncode:
        return {'error': 'interpreter_failed', 'detail': result.stderr.strip()[-500:]}
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {'error': 'invalid_probe_json', 'detail': f'{exc}: {result.stdout[:200]!r}'}
    if not isinstance(report, dict) or not isinstance(report.get('modules'), dict):
        return {'error': 'invalid_probe_shape', 'detail': result.stdout[:200]}
    report['stderr'] = result.stderr.strip()[-300:] if result.stderr.strip() else None
    return report


def resolve_dm_py() -> str | None:
    candidates = []
    if os.environ.get('DM_PY'):
        candidates.append(os.environ['DM_PY'])
    candidates += [str(DEFAULT_VENV_PY), sys.executable, shutil.which('python3') or '']
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen or not Path(candidate).exists():
            continue
        seen.add(candidate)
        result = probe_modules(candidate)
        modules = result.get('modules', {})
        missing = [name for name in CORE_MODULES + EXPORT_MODULES
                   if not modules.get(name, {}).get('ok')]
        if not missing:
            versions = ', '.join(f'{name}={modules[name]["version"]}'
                                 for name in CORE_MODULES + EXPORT_MODULES)
            add('python', 'green', f'{candidate} (Python {result["version"]}); {versions}')
            return candidate
        if 'error' in result:
            add('python.candidate', 'red',
                f'{candidate}: {result["error"]}: {result.get("detail", "")}')
        else:
            failed = {name: modules.get(name) for name in missing}
            add('python.candidate', 'yellow', f'{candidate} modules unavailable: {failed}')
    add('python', 'red',
        f'没有依赖齐备的解释器；请使用 {DEFAULT_VENV_PY} 并按 requirements.txt 安装')
    return None


def check_chromium(py: str) -> None:
    code = ('from playwright.sync_api import sync_playwright\n'
            'p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop(); print("ok")')
    try:
        result = subprocess.run([py, '-c', code], capture_output=True,
                                text=True, timeout=120)
    except subprocess.TimeoutExpired:
        add('pdf.chromium', 'red', 'Chromium 启动超时')
        return
    if result.returncode == 0 and result.stdout.strip() == 'ok':
        add('pdf.chromium', 'green', 'Playwright Chromium 可启动；这不代表 PDF 导出通过')
    else:
        add('pdf.chromium', 'red',
            f'Chromium 启动失败: {result.stderr.strip()[-300:]}')


def check_chart_bundle_schema(py: str, payload: str) -> tuple[bool, str]:
    code = (
        'import json,sys; from jsonschema import Draft202012Validator; '
        'schema=json.load(open(sys.argv[1],encoding="utf-8")); '
        'data=json.load(sys.stdin); errors=list(Draft202012Validator(schema).iter_errors(data)); '
        'print("; ".join(f"{e.json_path}: {e.message}" for e in errors)); sys.exit(bool(errors))'
    )
    try:
        result = subprocess.run([py, '-c', code, str(DM_ROOT / 'schemas/chart_bundle.json')],
                                input=payload, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return False, 'schema validation timed out'
    return result.returncode == 0, result.stdout.strip() or result.stderr.strip()


def check_cast(py: str) -> None:
    """Exercise positional contract and compare astro JD with Swiss UTC conversion."""
    script = DM_ROOT / 'scripts/cast_chart.py'
    command = [py, str(script), '1990-07-15', '12:00', 'm', 'Chicago',
               '--lat=41.88', '--lon=-87.63', '--tz=-5']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        add('cast', 'red', 'cast_chart.py smoke 超时')
        return
    if result.returncode != 0:
        add('cast', 'red', f'cast_chart.py exit={result.returncode}: {result.stderr.strip()[-300:]}')
        try:
            response = json.loads(result.stdout)
            if response.get('status') == 'error':
                add('cast.error_json', 'green', str(response.get('errors', [])))
        except json.JSONDecodeError:
            add('cast.error_json', 'red', '失败输出不是结构化 error JSON')
        return
    try:
        bundle = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        add('cast', 'red', f'cast 输出非 JSON: {exc}')
        return
    if bundle.get('schema_version') != 2 or set(bundle.get('dimensions', {})) != {'bazi', 'ziwei', 'astrology'}:
        add('cast.bundle', 'red', '缺少 schema_version 2 或三维命盘')
        return
    valid, detail = check_chart_bundle_schema(py, result.stdout)
    add('cast.schema', 'green' if valid else 'red',
        'chart_bundle Draft 2020-12 校验通过' if valid else detail)
    utc = bundle.get('time_context', {}).get('utc_instant')
    astro = bundle['dimensions']['astrology'].get('data') or {}
    birth = astro.get('出生信息', {})
    actual_jd = birth.get('UT1 儒略日')
    if utc != '1990-07-15T17:00:00Z' or birth.get('UTC') != utc:
        add('astro.clock_time', 'red', f'UTC 瞬间不符: context={utc}, astro={birth.get("UTC")}')
        return
    expected_code = (
        'import json,swisseph as s; print(json.dumps(s.utc_to_jd(1990,7,15,17,0,0,s.GREG_CAL)[1]))'
    )
    try:
        expected_run = subprocess.run([py, '-c', expected_code], capture_output=True,
                                      text=True, timeout=20)
        expected_jd = json.loads(expected_run.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        add('astro.clock_time', 'red', f'无法独立取得 Swiss UTC→UT1 JD: {exc}')
        return
    if expected_run.returncode or actual_jd is None or abs(float(actual_jd) - expected_jd) > 1e-10:
        add('astro.clock_time', 'red',
            f'UT1 JD 与 swe.utc_to_jd 不符: actual={actual_jd}, expected={expected_jd}')
    else:
        add('astro.clock_time', 'green', f'UTC=17:00Z; 实际 UT1 JD={actual_jd} 与 swe.utc_to_jd 一致')
    apparent = bundle.get('time_context', {}).get('local_apparent_datetime')
    add('cast.bundle', 'green', f'三维结果 status={bundle.get("status")}; true-solar={apparent}')
    if any(d.get('status') == 'error' for d in bundle['dimensions'].values()):
        add('cast.dimensions', 'red', '存在计算失败维度')


def check_omp() -> None:
    omp_cli = shutil.which('omp')
    if not omp_cli:
        add('omp.roles', 'yellow', '未检测到 omp CLI；无法只读确认 /model roles 可见性')
        return
    add('omp.roles', 'yellow',
        f'检测到 omp CLI ({omp_cli})；未修改配置，doctor 不推断 /model roles 的 resolvedModel')
    agents_dir = HOME / '.omp/agent/agents'
    for tier in TIERS:
        link = agents_dir / f'{tier}.md'
        target = DM_ROOT / 'adapters/omp' / f'{tier}.md'
        if link.exists() and link.resolve() == target.resolve():
            add(f'omp.agent.{tier}', 'green', f'{link} → {target}')
        else:
            add(f'omp.agent.{tier}', 'yellow', f'未发现 {tier} agent 链接到本技能 adapter')


def frontmatter(path: Path) -> dict[str, str]:
    """Top-level `key: value` lines of a Markdown agent definition (no YAML dependency)."""
    lines = path.read_text(encoding='utf-8').splitlines()
    if not lines or lines[0].strip() != '---':
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == '---':
            break
        if ':' in line and not line[:1].isspace():
            key, value = line.split(':', 1)
            fields[key.strip()] = value.strip()
    return fields


def check_judge_adapters() -> None:
    """dm-judge must be linked on both runtimes and must stay tool-less (see runtime-*.md)."""
    runtimes = (
        ('omp', HOME / '.omp/agent/agents/dm-judge.md', DM_ROOT / 'adapters/omp/dm-judge.md',
         {'tools': '[]'}, ('spawns',)),
        ('cc', HOME / '.claude/agents/dm-judge.md', DM_ROOT / 'adapters/cc/dm-judge.md',
         {'tools': 'ToolSearch', 'disallowedTools': 'mcp__*', 'omitClaudeMd': 'true'}, ()),
    )
    for runtime, link, target, required, forbidden in runtimes:
        cid = f'{runtime}.agent.dm-judge'
        if link.exists() and link.resolve() == target.resolve():
            add(cid, 'green', f'{link} → {target}')
        else:
            add(cid, 'yellow', f'未发现 dm-judge 链接到本技能 adapter；安装：ln -s "{target}" "{link}"')
        try:
            fields = frontmatter(target)
        except OSError as exc:
            add(f'{cid}.tools', 'red', f'无法读取 {target}: {exc}')
            continue
        wrong = {k: fields.get(k) for k, v in required.items() if fields.get(k) != v}
        wrong.update({k: fields[k] for k in forbidden if k in fields})
        if wrong:
            add(f'{cid}.tools', 'red', f'{target.name} frontmatter 破坏判官隔离: {wrong}；期望 {required}')
        else:
            add(f'{cid}.tools', 'green', f'frontmatter {required}' + (f'，无 {"/".join(forbidden)}' if forbidden else ''))
    if shutil.which('omp'):
        add('omp.agent.dm-judge.mcp', 'yellow',
            'omp 不按 agent tools 过滤用户配置的 MCP 工具；dm-judge 无文件/Shell，但可能仍见网络类 MCP，'
            '由 adapter 纪律禁止调用（见 runtime-omp.md）')


def check_cc() -> None:
    cli = shutil.which('claude')
    model = os.environ.get('CLAUDE_CODE_SUBAGENT_MODEL')
    if not cli:
        add('cc.roles', 'yellow', '未检测到 Claude Code CLI；无法确认子代理 role 可见性')
    elif model and model != 'inherit':
        add('cc.roles', 'yellow',
            f'检测到 Claude Code；CLAUDE_CODE_SUBAGENT_MODEL={model} 覆盖可能生效，未修改设置')
    else:
        add('cc.roles', 'yellow',
            '检测到 Claude Code CLI；只读检查未能证明实际子代理 resolvedModel')


def check_regression(py: str) -> None:
    try:
        result = subprocess.run([py, str(DM_ROOT / 'tests/run_regression.py')],
                                capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        add('regression', 'red', '回归执行超时')
        return
    tail = ' | '.join(result.stdout.strip().splitlines()[-12:])
    add('regression', 'green' if result.returncode == 0 else 'red', tail or result.stderr[-300:])


def main() -> int:
    as_json = '--json' in sys.argv[1:]
    dm_py = resolve_dm_py()
    if dm_py:
        check_chromium(dm_py)
        check_cast(dm_py)
        if '--regression' in sys.argv[1:]:
            check_regression(dm_py)
    check_omp()
    check_cc()
    check_judge_adapters()
    red = [item for item in checks if item['level'] == 'red']
    report = {'dm_root': str(DM_ROOT), 'dm_py': dm_py,
              'dm_py_path': dm_py, 'ok': not red, 'checks': checks}
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        icon = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}
        print(f'DM    = {DM_ROOT}\nDM_PY = {dm_py}')
        for item in checks:
            print(f"{icon[item['level']]} {item['id']}: {item['detail']}")
    return 1 if red else 0


if __name__ == '__main__':
    sys.exit(main())
