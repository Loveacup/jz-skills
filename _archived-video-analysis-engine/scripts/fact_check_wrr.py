#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fact_check_wrr.py — WRR 事实核查路由（claim 提取层）

职责边界（重要）：
  本脚本**只做 claim 提取 + 结构化输出**，不实际调用 WRR。
  真正的溯源核查由上层（fetch_all.py 编排或人工执行 WRR）完成；
  本脚本产出的 claim 列表是 WRR 的输入清单。

claim 提取两步：
  1. 正则匹配——优先命中「可验证性强」的 claim：
     number（数字/百分比/金额/倍数）> date（年/月/日）> ranking（第X/首个）
     > superlative（最大/最强/唯一/史上）
  2. 去重（按归一化文本）+ 按可验证性排序（数字 > 日期 > 排名 > 定性最）

输入二选一：
  --transcript FILE.txt   纯文本（支持 [m:ss] 时间戳前缀，自动剥离）
  --input FILE.json       字幕 JSON（B站 body/json3 events / 通用 text 字段）

输出：/tmp/{bvid}_fact_checks.json，并走 RESULT_JSON_START/END 协议。

用法:
  python3 fact_check_wrr.py --transcript /tmp/BVxxx_subtitle_official.txt --bvid BVxxx
  python3 fact_check_wrr.py --input /tmp/BVxxx_subtitle_official.json --bvid BVxxx --dry-run
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import json
import argparse
from datetime import datetime, timezone


# ============ claim 类型与优先级 ============
# 两套优先级，刻意分开（曾因混用导致「2023年3月发布」被 \d{3,} 抢判为 number）：
#   CLASSIFY_PRIORITY — 同句命中多类时归哪一类：date 比 number 更「具体」，优先归 date。
#   SORT_PRIORITY     — 输出排序的可验证性：数字 > 日期 > 排名 > 定性「最」。
CLASSIFY_PRIORITY = {'date': 4, 'number': 3, 'ranking': 2, 'superlative': 1}
SORT_PRIORITY = {'number': 4, 'date': 3, 'ranking': 2, 'superlative': 1}

# 各类型识别正则（针对中文视频字幕/简介，兼顾常见英文写法）
PATTERNS = {
    # 数字类：百分比、金额（亿/万/元/美元）、倍数、计数单位、纯大数
    'number': [
        r'\d+(?:\.\d+)?\s*[%％]',
        r'\d+(?:\.\d+)?\s*(?:亿|万|千万|百万|十万)',
        r'(?:[¥$￥]|人民币|美元|美金|欧元|日元)\s*\d+(?:\.\d+)?',
        r'\d+(?:\.\d+)?\s*(?:美元|美金|元|块钱|欧元|日元)',
        r'\d+(?:\.\d+)?\s*倍',
        r'(?:增长|下降|上涨|下跌|提升|提高|降低|减少)\s*(?:了)?\s*\d+(?:\.\d+)?\s*[%％倍]?',
        r'\d+(?:\.\d+)?\s*(?:个|名|位|款|家|款|条|次|项|种|款|人|台|辆|颗|枚)',
        r'\d{3,}',  # 三位以上纯数字（年份会被 date 优先抢走）
    ],
    # 日期类：年/年月/年月日
    'date': [
        r'\d{4}\s*年(?:\s*\d{1,2}\s*月)?(?:\s*\d{1,2}\s*[日号])?',
        r'\d{1,2}\s*月\s*\d{1,2}\s*[日号]',
        r'(?:19|20)\d{2}(?:[-/.]\d{1,2}(?:[-/.]\d{1,2})?)',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}',
    ],
    # 排名类：第X、首个、头部序数
    'ranking': [
        r'第\s*[一二三四五六七八九十百千万\d]+\s*(?:个|名|位|代|款|届|批|大|强)',
        r'首\s*(?:个|款|次|位|家|部|批)',
        r'(?:全球|国内|世界|业界|行业|国产)?\s*(?:第一|No\.?\s*1|TOP\s*\d+|前\s*\d+\s*名)',
    ],
    # 定性「最」类 / 唯一 / 史上：可验证性最弱但仍值得核
    'superlative': [
        r'最\s*(?:大|小|高|低|快|慢|强|多|早|新|贵|便宜|先进|领先|流行|受欢迎|畅销|成功)',
        r'唯一',
        r'史上',
        r'前所未有',
        r'空前',
        r'(?:世界|全球|国内|业界)\s*领先',
    ],
}

# 预编译
_COMPILED = {t: [re.compile(p) for p in pats] for t, pats in PATTERNS.items()}

# 行首时间戳前缀 [m:ss] / [mm:ss] / [h:mm:ss]
_TS_PREFIX = re.compile(r'^\s*\[\d{1,2}:\d{2}(?::\d{2})?\]\s*')


def strip_timestamp(line):
    """剥离行首 [m:ss] 时间戳前缀。"""
    return _TS_PREFIX.sub('', line)


def split_sentences(text):
    """把文本切成句子。中文按句末标点切，并保留换行作为天然边界。"""
    sentences = []
    for raw_line in text.splitlines():
        line = strip_timestamp(raw_line).strip()
        if not line:
            continue
        # 按句末标点切（保留分句），合并过短碎句
        parts = re.split(r'(?<=[。！？!?；;])\s*', line)
        for p in parts:
            p = p.strip()
            if p:
                sentences.append(p)
    return sentences


def classify_claim(sentence):
    """判断句子命中的最高优先级 claim 类型，未命中返回 None。"""
    hits = []
    for t, regexes in _COMPILED.items():
        for rx in regexes:
            if rx.search(sentence):
                hits.append(t)
                break
    if not hits:
        return None
    return max(hits, key=lambda t: CLASSIFY_PRIORITY[t])


def _normalize(text):
    """归一化用于去重：去空白与标点，保留字母数字与中文。"""
    return re.sub(r'[\s\W_]+', '', text)


def extract_claims(text, max_claims=50):
    """从文本提取 claim，去重并按可验证性排序。"""
    seen = set()
    claims = []
    for sent in split_sentences(text):
        # 过滤过短句（少于 6 字符通常无核查价值）
        if len(sent) < 6:
            continue
        ctype = classify_claim(sent)
        if ctype is None:
            continue
        key = _normalize(sent)
        if not key or key in seen:
            continue
        seen.add(key)
        claims.append({'claim': sent, 'type': ctype})

    # 按可验证性（SORT_PRIORITY）降序；同级保持原顺序（稳定排序）
    claims.sort(key=lambda c: SORT_PRIORITY[c['type']], reverse=True)
    return claims[:max_claims]


# ============ 输入读取 ============
def read_transcript(path):
    """读纯文本字幕。"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_text_from_json(path):
    """从字幕 JSON 提取纯文本，兼容多种结构。"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # B站原生 {body:[{from,content}]}
    if isinstance(data, dict) and isinstance(data.get('body'), list):
        return '\n'.join(item.get('content', '') for item in data['body'])
    # json3 {events:[{segs:[{utf8}]}]}
    if isinstance(data, dict) and isinstance(data.get('events'), list):
        out = []
        for ev in data['events']:
            for seg in ev.get('segs', []) or []:
                out.append(seg.get('utf8', ''))
        return ''.join(out)
    # 通用：顶层 text / transcript / desc 字段
    for key in ('text', 'transcript', 'desc', 'description'):
        if isinstance(data, dict) and isinstance(data.get(key), str):
            return data[key]
    # 列表 of {content/text}
    if isinstance(data, list):
        return '\n'.join(
            (x.get('content') or x.get('text') or '') for x in data if isinstance(x, dict)
        )
    raise ValueError('无法从 JSON 中识别字幕文本结构')


def now_iso():
    """当前 UTC 时间 ISO 字符串。"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def build_result(claims, bvid, dry_run):
    """组装最终结果 dict。

    verdict 默认 'uncertain'（脚本不核查，留给上层 WRR）；
    dry_run 时语义相同，仅在顶层标记 dry_run=True。
    """
    checked_at = now_iso()
    out_claims = []
    for c in claims:
        out_claims.append({
            'claim': c['claim'],
            'type': c['type'],
            'verdict': 'uncertain',     # 待上层 WRR 核查（本脚本不判定）
            'sources': [],
            'checked_at': checked_at,
        })

    summary = {
        'total': len(out_claims),
        'verified': 0,
        'uncertain': len(out_claims),
        'unfound': 0,
        # 额外给出类型分布，便于上层优先核查数字/日期类
        'by_type': {
            t: sum(1 for c in out_claims if c['type'] == t)
            for t in SORT_PRIORITY
        },
    }
    return {
        'bvid': bvid,
        'dry_run': dry_run,
        'note': 'claim 提取层；verdict 待上层 WRR 核查（本脚本不实际调用 WRR）',
        'claims': out_claims,
        'summary': summary,
    }


def main():
    parser = argparse.ArgumentParser(
        description='WRR 事实核查路由：从字幕/描述提取可验证 claim（不实际调 WRR）',
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--transcript', help='纯文本字幕文件（支持 [m:ss] 前缀）')
    src.add_argument('--input', help='字幕/描述 JSON 文件')
    parser.add_argument('--bvid', default='unknown', help='视频 BV 号（用于输出文件名）')
    parser.add_argument('--limit', type=int, default=50, help='最多提取 claim 数（默认 50）')
    parser.add_argument('--output', help='输出 JSON 路径（默认 /tmp/{bvid}_fact_checks.json）')
    parser.add_argument('--dry-run', action='store_true', help='只提取 claim 不核查（标记 dry_run）')
    args = parser.parse_args()

    # 读取文本
    try:
        if args.transcript:
            text = read_transcript(args.transcript)
        else:
            text = extract_text_from_json(args.input)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f'❌ 读取输入失败: {e}')
        print('\nRESULT_JSON_START')
        print(json.dumps({'bvid': args.bvid, 'claims': [],
                          'summary': {'total': 0}, 'error': str(e)},
                         ensure_ascii=False, indent=2))
        print('RESULT_JSON_END')
        sys.exit(1)

    print(f'🔍 claim 提取: bvid={args.bvid} dry_run={args.dry_run}')
    print('=' * 60)

    claims = extract_claims(text, args.limit)
    result = build_result(claims, args.bvid, args.dry_run)

    # 落盘
    out_path = args.output or f'/tmp/{args.bvid}_fact_checks.json'
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        result['path'] = out_path
        print(f'💾 已保存: {out_path}')
    except OSError as e:
        print(f'⚠️  保存失败: {e}')

    s = result['summary']
    print(f"\n📦 提取 {s['total']} 条 claim  类型分布: {s['by_type']}")
    for i, c in enumerate(result['claims'][:5], 1):
        print(f"  {i}. [{c['type']}] {c['claim'][:80]}")

    print('\n' + '=' * 60)
    print('RESULT_JSON_START')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('RESULT_JSON_END')


if __name__ == '__main__':
    main()
