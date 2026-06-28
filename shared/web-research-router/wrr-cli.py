#!/usr/bin/env python3
"""wrr-cli: Web Research Router 的命令行入口。

直接驱动 wrr 包（router + registry + engines），**不经过 Hermes 运行时 / tool handler**，
便于在终端、脚本、CI 里独立调用 search / fetch / similar。

用法::

    wrr-cli.py search "查询词" [--provider exa] [--count 10] [--mode deep] [--lang zh-CN]
    wrr-cli.py fetch  "https://..." [--provider exa] [--max-chars 5000]
    wrr-cli.py similar "https://..." [--count 10]
    wrr-cli.py test  [--provider exa]

通用选项：--json（机器可读）/ --env PATH（指定 .env）/ -q 静默元信息。

设计取舍：
  - 走 wrr.router.route()（wrr 自带的 fallback + 超时 + 总预算编排），而非
    wrr.tools.handle_web_* —— 后者是 Hermes 工具适配层，会耦合运行时。
  - --provider 透传为 route 的 explicit_provider：单引擎、禁用 fallback。
  - 仅依赖标准库 + wrr 自身；不引入 click/typer，.env 用内置极简解析器。
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import sys

# ── 让脚本无论从何处调用都能 import 同目录下的 wrr 包 ──────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


# ── .env 加载（极简，零依赖）──────────────────────────────────────────
def _candidate_env_paths(explicit: str | None) -> list[str]:
    """按优先级返回候选 .env 路径：--env > $WRR_ENV > ~/.hermes/.env。"""
    out: list[str] = []
    for p in (explicit, os.environ.get("WRR_ENV"),
              os.path.join(os.path.expanduser("~"), ".hermes", ".env")):
        if p and p not in out:
            out.append(p)
    return out


def load_env(explicit: str | None = None) -> str | None:
    """把第一个存在的 .env 解析进 os.environ（不覆盖已存在的真实环境变量）。

    返回实际加载的文件路径；都不存在时返回 None。
    支持 `KEY=VALUE` / `export KEY=VALUE`、# 注释、空行、首尾引号。
    """
    for path in _candidate_env_paths(explicit):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[len("export "):]
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except OSError as e:
            _eprint(f"警告：读取 {path} 失败：{e}")
            continue
        return path
    return None


# ── 输出辅助 ─────────────────────────────────────────────────────────
def _eprint(*a) -> None:
    print(*a, file=sys.stderr)


def _emit_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _result_to_payload(operation: str, result) -> object:
    """RouterResult.payload → 可 JSON 化结构（search/similar 为 list，extract 为 dict）。"""
    payload = result.payload
    if isinstance(payload, list):
        return [dataclasses.asdict(r) for r in payload]
    if dataclasses.is_dataclass(payload):
        return dataclasses.asdict(payload)
    return payload


def _chain_to_list(result) -> list:
    return [dataclasses.asdict(s) for s in result.fallback_chain]


# ── 运行单个动作（统一异常 → 退出码）─────────────────────────────────
async def _run(operation: str, options, provider: str | None):
    from wrr.registry import get_registry
    from wrr.router import route
    return await route(operation, options, get_registry(), explicit_provider=provider)


def _dispatch(operation: str, options, provider, ident, as_json, quiet, formatter):
    """执行 + 渲染 + 退出码。返回 0/1。"""
    from wrr.errors import AllEnginesFailedError, WRRError
    try:
        result = asyncio.run(_run(operation, options, provider))
    except AllEnginesFailedError as e:
        if as_json:
            _emit_json({"operation": operation, "ok": False,
                        "error": "all_engines_failed", "detail": str(e)})
        else:
            _eprint(f"✗ 所有引擎失败（{operation}）：\n{e}")
            _eprint("  提示：检查 API key（EXA_API_KEY / BRAVE_API_KEY / SEARXNG_URL）、"
                    "网络连通性，或换 --provider 试单引擎。")
        return 1
    except WRRError as e:
        if as_json:
            _emit_json({"operation": operation, "ok": False,
                        "error": type(e).__name__, "detail": str(e)})
        else:
            _eprint(f"✗ {type(e).__name__}: {e}")
        return 1

    if as_json:
        _emit_json({
            "operation": operation,
            "ok": True,
            "provider": result.actual_provider,
            "fallback_chain": _chain_to_list(result),
            "result": _result_to_payload(operation, result),
        })
    else:
        if not quiet:
            degraded = result.degraded_from if hasattr(result, "degraded_from") else None
            tag = f"  (降级自 {degraded})" if degraded else ""
            _eprint(f"● provider={result.actual_provider}{tag}")
        # formatters 返回 Hermes 工具响应信封 {"success","content","details"}；
        # 人类可读模式只取其中的 markdown content。解析失败则原样输出。
        rendered = formatter(result, ident)
        try:
            env = json.loads(rendered)
            print(env.get("content", rendered) if isinstance(env, dict) else rendered)
        except (json.JSONDecodeError, TypeError):
            print(rendered)
    return 0


# ── 子命令实现 ───────────────────────────────────────────────────────
def cmd_search(ns) -> int:
    from wrr.schemas import SearchOptions
    from wrr.formatters import format_search
    from wrr import config
    if ns.count < 1 or ns.count > config.MAX_SEARCH_COUNT:
        _eprint(f"✗ --count 须在 1..{config.MAX_SEARCH_COUNT}")
        return 2
    opts = SearchOptions(query=ns.query, count=ns.count,
                         provider=ns.provider, mode=ns.mode)
    return _dispatch("search", opts, ns.provider, ns.query,
                     ns.json, ns.quiet, format_search)


def cmd_fetch(ns) -> int:
    from wrr.schemas import ExtractOptions
    from wrr.formatters import format_extract
    from wrr import config
    if not ns.url.lower().startswith(("http://", "https://")):
        _eprint("✗ url 须以 http:// 或 https:// 开头")
        return 2
    if ns.max_chars < 1 or ns.max_chars > config.MAX_MAX_CHARACTERS:
        _eprint(f"✗ --max-chars 须在 1..{config.MAX_MAX_CHARACTERS}")
        return 2
    opts = ExtractOptions(url=ns.url, max_characters=ns.max_chars,
                          provider=ns.provider)
    return _dispatch("extract", opts, ns.provider, ns.url,
                     ns.json, ns.quiet, format_extract)


def cmd_similar(ns) -> int:
    from wrr.schemas import SimilarOptions
    from wrr.formatters import format_similar
    from wrr import config
    if not ns.url.lower().startswith(("http://", "https://")):
        _eprint("✗ url 须以 http:// 或 https:// 开头")
        return 2
    if ns.count < 1 or ns.count > config.MAX_SEARCH_COUNT:
        _eprint(f"✗ --count 须在 1..{config.MAX_SEARCH_COUNT}")
        return 2
    opts = SimilarOptions(url=ns.url, count=ns.count, provider=ns.provider)
    return _dispatch("similar", opts, ns.provider, ns.url,
                     ns.json, ns.quiet, format_similar)


def cmd_test(ns) -> int:
    """冒烟测试：依次验证 search / fetch / similar 能否调通。"""
    from wrr.schemas import SearchOptions, ExtractOptions, SimilarOptions
    from wrr.errors import WRRError

    prov = ns.provider
    cases = [
        ("search", SearchOptions(query="hello world", count=3,
                                 provider=prov, mode=None)),
        ("extract", ExtractOptions(url="https://example.com",
                                   max_characters=500, provider=prov)),
        # similar 仅 Exa 支持；显式 provider 非 exa 时跳过
        ("similar", SimilarOptions(url="https://example.com",
                                   count=3, provider=prov)),
    ]

    report = []
    overall_ok = True
    for op, opts in cases:
        if op == "similar" and prov not in (None, "exa"):
            report.append({"op": op, "status": "skip",
                           "detail": f"similar 仅 exa 支持，当前 --provider={prov}"})
            continue
        try:
            result = asyncio.run(_run(op, opts, prov))
            n = (len(result.payload) if isinstance(result.payload, list)
                 else len(getattr(result.payload, "text", "") or ""))
            report.append({"op": op, "status": "ok",
                           "provider": result.actual_provider, "count": n})
        except WRRError as e:
            overall_ok = False
            report.append({"op": op, "status": "fail",
                           "error": type(e).__name__, "detail": str(e)[:300]})
        except Exception as e:  # noqa: BLE001 — 冒烟测试要兜住一切
            overall_ok = False
            report.append({"op": op, "status": "fail",
                           "error": type(e).__name__, "detail": str(e)[:300]})

    if ns.json:
        _emit_json({"ok": overall_ok, "provider": prov, "cases": report})
    else:
        print("wrr-cli 冒烟测试" + (f"（provider={prov}）" if prov else "（默认 fallback 链）"))
        for r in report:
            mark = {"ok": "✓", "fail": "✗", "skip": "—"}[r["status"]]
            if r["status"] == "ok":
                print(f"  {mark} {r['op']:<8} provider={r['provider']} count={r['count']}")
            elif r["status"] == "skip":
                print(f"  {mark} {r['op']:<8} {r['detail']}")
            else:
                print(f"  {mark} {r['op']:<8} {r['error']}: {r['detail']}")
        print("结果：" + ("全部通过" if overall_ok else "存在失败"))
    return 0 if overall_ok else 1


def cmd_doctor(ns) -> int:
    """Doctor: 检查引擎健康状况和本地依赖。"""
    from wrr.registry import get_registry
    from wrr.doctor import run_doctor, summarize_checks, doctor_exit_code
    from wrr.formatters import format_doctor_report

    registry = get_registry()

    # 验证 --engine 参数（如果指定）
    if ns.engine:
        if ns.engine not in registry.names():
            _eprint(f"✗ 未知引擎: {ns.engine}")
            _eprint(f"  可用引擎: {', '.join(registry.names())}")
            return 2

    # 运行 doctor
    try:
        results = asyncio.run(run_doctor(
            registry,
            engine=ns.engine,
            tier=ns.tier,
            deep=False,  # P0 不支持 deep
        ))
    except ValueError as e:
        _eprint(f"✗ {e}")
        return 2
    except Exception as e:
        _eprint(f"✗ Doctor 失败: {type(e).__name__}: {e}")
        return 1

    # 输出结果
    if ns.json:
        summary = summarize_checks(results)
        payload = {
            "ok": summary["status"] != "fail",
            "status": summary["status"],
            "summary": {k: summary[k] for k in ("ok", "warn", "fail", "skip")},
            "engines": [r.to_dict() for r in results],
        }
        _emit_json(payload)
    else:
        print(format_doctor_report(results))

    # 返回退出码
    return doctor_exit_code(results, strict=ns.strict)


# ── argparse 组装 ────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wrr-cli.py",
        description="Web Research Router CLI —— 独立于 Hermes 的 search/fetch/similar。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
               "  wrr-cli.py search \"claude opus 4.8\" --mode deep --count 5\n"
               "  wrr-cli.py fetch https://exa.ai --max-chars 2000 --json\n"
               "  wrr-cli.py similar https://exa.ai\n"
               "  wrr-cli.py test --provider exa",
    )
    # 全局选项（放父 parser，子命令继承）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="输出 JSON（机器可读）")
    common.add_argument("--env", metavar="PATH", help="指定 .env 路径（默认 $WRR_ENV 或 ~/.hermes/.env）")
    common.add_argument("-q", "--quiet", action="store_true", help="不打印 provider 等元信息")
    common.add_argument("--provider", choices=["exa", "brave", "searxng", "github", "community", "academic", "skill"],
                        help="强制单引擎（禁用 fallback）")

    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search", parents=[common], help="多引擎 fallback 搜索")
    sp.add_argument("query")
    sp.add_argument("--count", type=int, default=10, help="结果数（默认 10）")
    sp.add_argument("--mode", choices=["fast", "auto", "deep-lite", "deep"],
                    default=None, help="Exa 模式；缺省自动路由")
    sp.set_defaults(func=cmd_search)

    fp = sub.add_parser("fetch", parents=[common], help="抓取 URL 正文")
    fp.add_argument("url")
    fp.add_argument("--max-chars", type=int, default=5000, dest="max_chars",
                    help="正文截断上限（默认 5000）")
    fp.set_defaults(func=cmd_fetch)

    mp = sub.add_parser("similar", parents=[common], help="查找相似页面（仅 Exa）")
    mp.add_argument("url")
    mp.add_argument("--count", type=int, default=10, help="结果数（默认 10）")
    mp.set_defaults(func=cmd_similar)

    tp = sub.add_parser("test", parents=[common], help="冒烟测试 search/fetch/similar")
    tp.set_defaults(func=cmd_test)

    # doctor 子命令（v5.1，不继承 common 中的 --provider，因需独立 --engine）
    dp = sub.add_parser("doctor", help="检查引擎健康状况和本地依赖")
    dp.add_argument("--engine", choices=["exa", "brave", "github", "skill", "searxng", "community", "academic"],
                    help="仅检查指定引擎")
    dp.add_argument("--tier", type=int, choices=[0, 1, 2], help="仅检查指定 tier")
    dp.add_argument("--json", action="store_true", help="输出 JSON 格式")
    dp.add_argument("--env", metavar="PATH", help="指定 .env 路径")
    dp.add_argument("-q", "--quiet", action="store_true", help="不打印元信息")
    dp.add_argument("--strict", action="store_true", help="严格模式：warn 也视为失败（退出码 1）")
    dp.set_defaults(func=cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)

    loaded = load_env(getattr(ns, "env", None))
    if not ns.quiet and not getattr(ns, "json", False):
        if loaded:
            _eprint(f"· 已加载 env：{loaded}")
        else:
            _eprint("· 未找到 .env（将仅依赖现有环境变量）")

    return ns.func(ns)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _eprint("\n已中断")
        sys.exit(130)
