#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_report.py — Bilibili 解析报告"深度质量门"静态校验器
Statically verify a generated Bilibili-analysis Markdown report against
structural "depth quality gates".

用途：在报告生成后，无需 LLM，纯静态检查报告是否满足结构性深度要求。
依赖：仅标准库 (sys, re, json, argparse)。无第三方依赖。

GATES（全量版 full / 默认）:
  G1  §1 逻辑链 ≤ 100 行
  G3  §3 ≥ 3 个洞察小节，每个正文 ≥ 200 词
  G4  §4 ≥ 3 个模块小节，每个正文 ≥ 500 词
  G5  §5 ≥ 5 个高光引用块组 (blockquote groups)
  G7  §7 ≥ 3 独特价值 且 ≥ 2 局限偏见 且 ≥ 3 可行动项

精简版 condensed 放宽:
  G1 ≤100 行; G3 ≥2 洞察 × ≥150 词; G4 ≥2 模块 (不强制每模块上限);
  G5 ≥2 高光; G7 不变。

Claim-First Gates (opt-in with --claim-first):
  G8  §3 每条洞察含 claim/evidence/warrant/boundary 结构
  G9  §4 每个模块含显性/隐性/元叙事或等价结构（核心论点/论证展开/批判审视）
  G10 §7 行动项含证据引用或 claim id ([E#] 或 [C#] 或时间戳)

用法:
  python3 verify_report.py <report.md> [--mode full|condensed] [--json]
  python3 verify_report.py <report.md> --depth full [--claim-first] [--json]

参数:
  --mode full|condensed   别名 --depth，控制 G1/G3/G4/G5/G7 阈值
  --depth full|condensed  同上
  --claim-first           启用 G8-G10 claim-first 质量门
  --json                  输出 JSON 格式结果

退出码: 0 全部通过 / 1 有门未通过 / 2 用法错误或文件不存在。
"""

import sys
import re
import json
import argparse

# ---------------------------------------------------------------------------
# 词数统计 / Word counting (Chinese-aware)
# ---------------------------------------------------------------------------

# CJK 表意文字范围 (基本汉字块 一-鿿 = U+4E00..U+9FFF)
_CJK_RE = re.compile(r'[一-鿿]')
# ASCII 字母数字词元 (连续的 A-Za-z0-9 算一个词)
_ASCII_WORD_RE = re.compile(r'[A-Za-z0-9]+')


def word_count(text: str) -> int:
    """
    中文文本词数 = CJK 表意文字个数 + ASCII 字母数字词元个数。
    word_count(text) = (#CJK ideographs) + (#ASCII alnum tokens)
    """
    cjk = len(_CJK_RE.findall(text))
    ascii_words = len(_ASCII_WORD_RE.findall(text))
    return cjk + ascii_words


def strip_markup(line: str) -> str:
    """
    去除 markdown 标记后再计数：
      - 行首的 #、>、-、* (列表/引用/标题标记)
      - 表格管道符 |
      - mermaid 代码围栏 ``` 行整行剔除
    其余文字保留（统计函数本身只数 CJK + 字母数字，所以表格内文字仍计入）。
    """
    stripped = line.strip()
    # mermaid / 代码围栏整行不计
    if stripped.startswith('```'):
        return ''
    # 去掉行首的引用/标题/列表标记（可能叠加，如 "> - "）
    stripped = re.sub(r'^([#>\-\*\s]|\[ \]|\[x\])+', '', stripped)
    # 去掉表格管道符
    stripped = stripped.replace('|', ' ')
    # 去掉行内强调标记 ** __ * _ `
    stripped = re.sub(r'[*_`]', ' ', stripped)
    return stripped


# ---------------------------------------------------------------------------
# 分节 / Section parsing
# ---------------------------------------------------------------------------

def split_into_lines(md: str):
    return md.splitlines()


def find_section(lines, num):
    """
    找到 `## <num>.` 章节，返回 (start_idx, end_idx)，end 为下一个 `## ` 之前。
    未找到返回 (None, None)。
    匹配如 `## 1. 逻辑链 ...` / `## 3. 核心洞察 ...`。
    """
    start = None
    pat = re.compile(r'^##\s+' + re.escape(str(num)) + r'\.')
    for i, ln in enumerate(lines):
        if pat.match(ln):
            start = i
            break
    if start is None:
        return None, None
    # 找下一个 `## ` 顶级章节
    end = len(lines)
    top = re.compile(r'^##\s')
    for j in range(start + 1, len(lines)):
        if top.match(lines[j]):
            end = j
            break
    return start, end


def split_subsections(section_lines, heading_filter=None):
    """
    将一个章节的行切成若干 `### ` 小节。
    heading_filter: 可选函数，接收小节标题行文本，返回 True 才计入。
    返回列表 [(heading_line, [body_lines...]), ...]，body 不含 `###` 标题行。
    """
    subs = []
    cur_head = None
    cur_body = []
    h3 = re.compile(r'^###\s')
    for ln in section_lines:
        if h3.match(ln):
            # 收尾上一节
            if cur_head is not None:
                subs.append((cur_head, cur_body))
            cur_head = ln
            cur_body = []
        else:
            if cur_head is not None:
                cur_body.append(ln)
    if cur_head is not None:
        subs.append((cur_head, cur_body))

    if heading_filter is not None:
        subs = [(h, b) for (h, b) in subs if heading_filter(h)]
    return subs


def body_word_count(body_lines) -> int:
    """对一个小节正文（已不含 ### 标题）统计词数，逐行 strip_markup。"""
    total = 0
    for ln in body_lines:
        total += word_count(strip_markup(ln))
    return total


# ---------------------------------------------------------------------------
# 各 Gate 测量 / Per-gate measurement
# ---------------------------------------------------------------------------

def measure_g1(lines):
    """§1 逻辑链行数：从 `## 1.` 行起，到下一个 `## ` 之前（不含）。"""
    start, end = find_section(lines, 1)
    if start is None:
        return None  # 缺失
    return end - start  # 含 ## 1. 标题行，不含下一节标题


def _is_insight_heading(h):
    """§3 洞察小节：含 💡。排除 🔥 反直觉/争议点。"""
    if '🔥' in h:
        return False
    return '💡' in h


def measure_g3(lines):
    """返回 (insight_count, min_words) 或 None（章节缺失）。"""
    start, end = find_section(lines, 3)
    if start is None:
        return None
    subs = split_subsections(lines[start:end], heading_filter=_is_insight_heading)
    if not subs:
        return (0, 0)
    counts = [body_word_count(b) for (_h, b) in subs]
    return (len(subs), min(counts))


def _is_module_heading(h):
    """§4 模块小节：`### 模块 N: ...`。"""
    return bool(re.search(r'###\s*模块\s*\d', h)) or bool(re.search(r'###\s*Module\s*\d', h, re.I))


def measure_g4(lines):
    """返回 (module_count, min_words) 或 None。"""
    start, end = find_section(lines, 4)
    if start is None:
        return None
    subs = split_subsections(lines[start:end], heading_filter=_is_module_heading)
    if not subs:
        return (0, 0)
    counts = [body_word_count(b) for (_h, b) in subs]
    return (len(subs), min(counts))


def measure_g5(lines):
    """
    §5 高光引用块组数量。
    一个"引用块组" = 连续若干以 `>` 开头的行（中间允许空行？——不允许，
    空行视为分隔）。每组通常以 `> "..."` 起头，但只要是连续 `>` 行即算一组。
    返回 group_count 或 None。
    """
    start, end = find_section(lines, 5)
    if start is None:
        return None
    groups = 0
    in_group = False
    for ln in lines[start + 1:end]:  # 跳过 §5 标题行本身
        is_quote = ln.lstrip().startswith('>')
        if is_quote:
            if not in_group:
                groups += 1
                in_group = True
            # 仍在组内
        else:
            # 非引用行（含空行、### 子标题、普通文字）结束当前组
            in_group = False
    return groups


def measure_g7(lines):
    """
    §7 批判与行动：
      独特价值 (### 独特价值 下的 `- ` 项),
      局限与偏见 (### 局限与偏见 下的 `- ` 项),
      可行动项 (### 可行动项 下的 列表项，含 1. / - [ ] / - 等)。
    返回 (valid, blind, action) 或 None。
    """
    start, end = find_section(lines, 7)
    if start is None:
        return None
    section = lines[start:end]
    # 把 §7 再按 ### 切块（不过滤），逐块归类
    subs = split_subsections(section)

    valid = blind = action = 0

    bullet_re = re.compile(r'^\s*-\s+')                 # "- xxx"
    ordered_re = re.compile(r'^\s*\d+\.\s')             # "1. xxx"
    checkbox_re = re.compile(r'^\s*-\s*\[[ xX]?\]')     # "- [ ] xxx"

    def count_bullets(body):
        n = 0
        for ln in body:
            if bullet_re.match(ln):
                n += 1
        return n

    def count_action_items(body):
        n = 0
        for ln in body:
            if ordered_re.match(ln) or checkbox_re.match(ln) or bullet_re.match(ln):
                n += 1
        return n

    for head, body in subs:
        if '独特价值' in head:
            valid += count_bullets(body)
        elif '局限' in head or '偏见' in head:
            blind += count_bullets(body)
        elif '可行动' in head or '行动项' in head:
            # 可行动项下可能还有 立即执行/短期跟进/长期探索 加粗子组（非 ###），
            # 这些子组与列表项混在同一 body 内，逐行扫即可。
            action += count_action_items(body)

    return (valid, blind, action)


def measure_g8(lines):
    """G8: §3 每个洞察小节必须包含 claim/warrant/证据/边界或反证关键字。
    返回 (insights_count, insights_with_keywords_count) 或 None。
    """
    start, end = find_section(lines, 3)
    if start is None:
        return None
    subs = split_subsections(lines[start:end], heading_filter=_is_insight_heading)
    if not subs:
        return (0, 0)

    # 扩展证据引用格式：[E1], @[E1], @E1, （E1）, (E1), 时间戳
    keywords_pattern = re.compile(r'claim|warrant|主张|证据|推理|许可|边界|反证|局限|但是|然而|不过|例外|\[E\d+\]|@\[E\d+\]|@E\d+|[（(]E\d+[）)]|\b\d{1,2}:\d{2}\b')
    insights_with_keywords = 0
    for _head, body in subs:
        body_text = '\n'.join(body)
        if keywords_pattern.search(body_text):
            insights_with_keywords += 1

    return (len(subs), insights_with_keywords)


def measure_g9(lines):
    """G9: §4 每个模块必须包含显性/隐性/元叙事或等价结构关键字。
    返回 (modules_count, modules_with_keywords_count) 或 None。
    """
    start, end = find_section(lines, 4)
    if start is None:
        return None
    subs = split_subsections(lines[start:end], heading_filter=_is_module_heading)
    if not subs:
        return (0, 0)

    keywords_pattern = re.compile(r'显性|隐性|元叙事|表层|深层|底层|系统|结构|机制|动力|explicit|implicit|meta|narrative|surface|underlying')
    modules_with_keywords = 0
    for _head, body in subs:
        body_text = '\n'.join(body)
        if keywords_pattern.search(body_text):
            modules_with_keywords += 1

    return (len(subs), modules_with_keywords)


def measure_g10(lines):
    """G10: §7 行动项必须包含证据引用或 claim ID。
    返回 (action_items_count, action_items_with_refs_count) 或 None。
    """
    start, end = find_section(lines, 7)
    if start is None:
        return None
    section = lines[start:end]
    subs = split_subsections(section)

    action_start_re = re.compile(r'^(?:-\s+(?:\[[ xX]?\]\s*)?|\d+\.\s+)')
    # 扩展证据引用格式：[E1], [C1], @[E1], @E1, （E1）, (E1), 时间戳
    ref_pattern = re.compile(r'\[E\d+\]|\[C\d+\]|@\[E\d+\]|@E\d+|[（(]E\d+[）)]|\b\d{1,2}:\d{2}\b')

    action_items = []
    for head, body in subs:
        if '可行动' not in head and '行动项' not in head:
            continue
        current = []
        for ln in body:
            if action_start_re.match(ln):
                if current:
                    action_items.append('\n'.join(current))
                current = [ln]
            elif current:
                current.append(ln)
        if current:
            action_items.append('\n'.join(current))

    if not action_items:
        return (0, 0)

    items_with_refs = sum(1 for item in action_items if ref_pattern.search(item))
    return (len(action_items), items_with_refs)


# ---------------------------------------------------------------------------
# Gate 评估 / Gate evaluation
# ---------------------------------------------------------------------------

def build_gates(mode):
    """根据模式返回各门阈值配置。"""
    if mode == 'condensed':
        return {
            'min_insights': 2, 'insight_words': 150,
            'min_modules': 2, 'module_words': None,   # 不强制每模块词数
            'min_highlights': 2,
            'valid': 3, 'blind': 2, 'action': 3,
            'g1_max_lines': 100,
        }
    # full (default)
    return {
        'min_insights': 3, 'insight_words': 200,
        'min_modules': 3, 'module_words': 500,
        'min_highlights': 5,
        'valid': 3, 'blind': 2, 'action': 3,
        'g1_max_lines': 100,
    }


def evaluate(md, mode, claim_first=False):
    """运行所有门，返回 (results_dict, overall_pass)。"""
    lines = split_into_lines(md)
    cfg = build_gates(mode)
    results = {}

    # ---- G1 ----
    g1 = measure_g1(lines)
    if g1 is None:
        results['G1'] = {
            'pass': False, 'measured': '§1 缺失 (section missing)',
            'threshold': f'≤ {cfg["g1_max_lines"]} 行',
        }
    else:
        ok = g1 <= cfg['g1_max_lines']
        results['G1'] = {
            'pass': ok, 'measured': f'§1: {g1} 行',
            'threshold': f'≤ {cfg["g1_max_lines"]} 行',
        }

    # ---- G3 ----
    g3 = measure_g3(lines)
    if g3 is None:
        results['G3'] = {
            'pass': False, 'measured': '§3 缺失 (section missing)',
            'threshold': f'≥ {cfg["min_insights"]} 洞察 × ≥ {cfg["insight_words"]} 词',
        }
    else:
        cnt, mn = g3
        ok = cnt >= cfg['min_insights'] and mn >= cfg['insight_words']
        results['G3'] = {
            'pass': ok,
            'measured': f'§3: {cnt} insights, min {mn} words',
            'threshold': f'≥ {cfg["min_insights"]} 洞察 × ≥ {cfg["insight_words"]} 词',
        }

    # ---- G4 ----
    g4 = measure_g4(lines)
    if g4 is None:
        results['G4'] = {
            'pass': False, 'measured': '§4 缺失 (section missing)',
            'threshold': _g4_threshold_text(cfg),
        }
    else:
        cnt, mn = g4
        ok = cnt >= cfg['min_modules']
        if cfg['module_words'] is not None:
            ok = ok and mn >= cfg['module_words']
        results['G4'] = {
            'pass': ok,
            'measured': f'§4: {cnt} modules, min {mn} words',
            'threshold': _g4_threshold_text(cfg),
        }

    # ---- G5 ----
    g5 = measure_g5(lines)
    if g5 is None:
        results['G5'] = {
            'pass': False, 'measured': '§5 缺失 (section missing)',
            'threshold': f'≥ {cfg["min_highlights"]} 高光引用块',
        }
    else:
        ok = g5 >= cfg['min_highlights']
        results['G5'] = {
            'pass': ok, 'measured': f'§5: {g5} highlight blockquote groups',
            'threshold': f'≥ {cfg["min_highlights"]} 高光引用块',
        }

    # ---- G7 ----
    g7 = measure_g7(lines)
    if g7 is None:
        results['G7'] = {
            'pass': False, 'measured': '§7 缺失 (section missing)',
            'threshold': f'≥ {cfg["valid"]} 价值 & ≥ {cfg["blind"]} 局限 & ≥ {cfg["action"]} 行动',
        }
    else:
        valid, blind, action = g7
        ok = valid >= cfg['valid'] and blind >= cfg['blind'] and action >= cfg['action']
        results['G7'] = {
            'pass': ok,
            'measured': f'§7: {valid} valid, {blind} blind spots, {action} actions',
            'threshold': f'≥ {cfg["valid"]} 价值 & ≥ {cfg["blind"]} 局限 & ≥ {cfg["action"]} 行动',
        }

    # ---- G8/G9/G10 (claim-first only) ----
    if claim_first:
        # G8: §3 insights have claim/warrant/evidence/boundary
        g8 = measure_g8(lines)
        if g8 is None:
            results['G8'] = {
                'pass': False, 'measured': '§3 缺失 (section missing)',
                'threshold': '所有洞察含 claim/warrant/证据/边界关键词',
            }
        else:
            cnt, with_kw = g8
            ok = cnt > 0 and with_kw == cnt
            results['G8'] = {
                'pass': ok,
                'measured': f'§3: {with_kw}/{cnt} insights have claim-first keywords',
                'threshold': '所有洞察含 claim/warrant/证据/边界关键词',
            }

        # G9: §4 modules have explicit/implicit/meta-narrative structure
        g9 = measure_g9(lines)
        if g9 is None:
            results['G9'] = {
                'pass': False, 'measured': '§4 缺失 (section missing)',
                'threshold': '所有模块含显性/隐性/元叙事结构关键词',
            }
        else:
            cnt, with_kw = g9
            ok = cnt > 0 and with_kw == cnt
            results['G9'] = {
                'pass': ok,
                'measured': f'§4: {with_kw}/{cnt} modules have narrative structure keywords',
                'threshold': '所有模块含显性/隐性/元叙事结构关键词',
            }

        # G10: §7 action items have evidence refs or claim IDs
        g10 = measure_g10(lines)
        if g10 is None:
            results['G10'] = {
                'pass': False, 'measured': '§7 缺失 (section missing)',
                'threshold': '所有行动项含证据引用或 claim ID',
            }
        else:
            cnt, with_refs = g10
            ok = cnt > 0 and with_refs == cnt
            results['G10'] = {
                'pass': ok,
                'measured': f'§7: {with_refs}/{cnt} action items have evidence refs',
                'threshold': '所有行动项含证据引用或 claim ID',
            }

    overall = all(r['pass'] for r in results.values())
    return results, overall


def _g4_threshold_text(cfg):
    if cfg['module_words'] is not None:
        return f'≥ {cfg["min_modules"]} 模块 × ≥ {cfg["module_words"]} 词'
    return f'≥ {cfg["min_modules"]} 模块 (不强制词数)'


# ---------------------------------------------------------------------------
# 输出 / Output
# ---------------------------------------------------------------------------

GATE_NAMES = {
    'G1': '逻辑链 (Logic Chain)',
    'G3': '核心洞察 (Key Insights)',
    'G4': '内容深度拆解 (Deep Dive)',
    'G5': '高光时刻 (Highlights)',
    'G7': '批判与行动 (Critical Review & Action)',
    'G8': 'Claim-First 洞察结构 (Insight Structure)',
    'G9': 'Claim-First 叙事层次 (Narrative Layers)',
    'G10': 'Claim-First 行动证据 (Action Evidence)',
}


def print_report(results, overall, mode):
    claim_first_enabled = 'G8' in results
    mode_label = f"mode={mode}, claim-first={'on' if claim_first_enabled else 'off'}"
    print(f"📋 深度质量门校验 ({mode_label})")
    print("=" * 70)
    gate_ids = ['G1', 'G3', 'G4', 'G5', 'G7']
    if claim_first_enabled:
        gate_ids.extend(['G8', 'G9', 'G10'])
    for gid in gate_ids:
        if gid not in results:
            continue
        r = results[gid]
        mark = '✅' if r['pass'] else '❌'
        status = 'PASS' if r['pass'] else 'FAIL'
        print(f"{mark} {gid} {GATE_NAMES[gid]}")
        print(f"     measured : {r['measured']}")
        print(f"     threshold: {r['threshold']}")
        print(f"     → {status}")
    print("=" * 70)
    if overall:
        print("✅ OVERALL: PASS — 所有质量门通过")
    else:
        failed = [g for g in gate_ids if g in results and not results[g]['pass']]
        print(f"❌ OVERALL: FAIL — 未通过: {', '.join(failed)}")


def print_json(results, overall, claim_first=False):
    claim_first_gates = {k: results[k] for k in ['G8', 'G9', 'G10'] if k in results}
    obj = {
        'gates': {
            gid: {
                'pass': r['pass'],
                'measured': r['measured'],
                'threshold': r['threshold'],
            } for gid, r in results.items()
        },
        'overall_pass': overall,
        'claim_first_enabled': claim_first,
        'g8_passed': claim_first_gates.get('G8', {}).get('pass', None) if claim_first else None,
        'g9_passed': claim_first_gates.get('G9', {}).get('pass', None) if claim_first else None,
        'g10_passed': claim_first_gates.get('G10', {}).get('pass', None) if claim_first else None,
    }
    print("RESULT_JSON_START")
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    print("RESULT_JSON_END")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='静态校验 Bilibili 解析报告的结构深度质量门。'
    )
    parser.add_argument('report', help='报告 Markdown 文件路径')
    parser.add_argument('--mode', choices=['full', 'condensed'], default='full',
                        help='全量版 full(默认) 或精简版 condensed')
    parser.add_argument('--depth', choices=['full', 'condensed'], dest='depth',
                        help='深度模式（--mode 的别名）：full(默认) 或 condensed')
    parser.add_argument('--claim-first', action='store_true', dest='claim_first',
                        help='启用 claim-first 质量门 (G8/G9/G10)')
    parser.add_argument('--json', action='store_true', dest='as_json',
                        help='额外输出 RESULT_JSON 机器可读块')
    # argparse 在参数错误时退出码为 2，符合"用法错误"要求
    args = parser.parse_args()

    # --depth is an alias for --mode; --depth takes precedence if both are provided
    mode = args.depth if args.depth else args.mode

    try:
        with open(args.report, 'r', encoding='utf-8') as f:
            md = f.read()
    except FileNotFoundError:
        print(f"❌ 错误：文件不存在 — {args.report}", file=sys.stderr)
        sys.exit(2)
    except OSError as e:
        print(f"❌ 错误：无法读取文件 — {e}", file=sys.stderr)
        sys.exit(2)

    results, overall = evaluate(md, mode, claim_first=args.claim_first)
    print_report(results, overall, mode)
    if args.as_json:
        print()
        print_json(results, overall, claim_first=args.claim_first)

    sys.exit(0 if overall else 1)


if __name__ == '__main__':
    main()
