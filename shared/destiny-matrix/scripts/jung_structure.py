#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由八功能分或十六亚型分确定性派生的轮廓结构：排序分层、对立轴、合计、类型贴合度、亚型方向。

只做可复算的算术与查表。类型贴合度给出的是“这组分数与哪一型的标准功能栈最像”，
属于类型假说的盘面依据；假说怎样落到具体的人身上，由 analyst 按 cognitive-functions.md 的推读路径给出。
"""
import math
import re

from jung_calc import FUNCTIONS, OPPOSITE, STANDARD_STACKS, SUBTYPE_KEYS

POSITIONS = ['主导', '辅助', '第三', '劣势', '对立人格', '长者/女巫', '捣蛋鬼', '魔性人格']
ARCHETYPES = ['英雄', '父母', '永恒少年', '阿尼玛/阿尼姆斯', '对立人格', '长者/女巫', '捣蛋鬼', '魔性人格']
# 八个位置的期望分（功能合计，八项共 240）：取自 JUNGUS 第二代测验 64 型原型矩阵按位置归并后的数值
POSITION_EXPECTED = [42, 37, 33, 24, 31, 31, 20, 22]
AXES = [('Te', 'Fi'), ('Ti', 'Fe'), ('Se', 'Ni'), ('Si', 'Ne')]
PERCEIVING = ('Se', 'Si', 'Ne', 'Ni')
JUDGING = ('Te', 'Ti', 'Fe', 'Fi')
EXTRAVERTED = ('Se', 'Ne', 'Te', 'Fe')
INTROVERTED = ('Si', 'Ni', 'Ti', 'Fi')
SUBTYPE_NAMES = {'O': '主体', 'B': '背景', 'A': '分析', 'H': '整体'}
TYPE_CODE = re.compile(r'^([EI][SN][TF][JP])(?:([OB])([AH]))?$')
# 首选与次选的贴合度差小于此值时，两型并列提出
CLOSE_MARGIN = 0.05
# 极差占量程低于此值时，分数几乎拉不开，不定类型假说、不分层
FLAT_RANGE = 0.05
# 十六项合计与 240 相差超过此值记为偏离
TOTAL_TOLERANCE = 1.0
EPS = 1e-9

METHOD = {
    '功能分': '八功能输入直接使用原始分；十六亚型输入以同一功能两亚型的均值作功能分（保持原量程），另列合计。'
           'JUNGUS 官方原型矩阵把一个功能的分数按比例拆给两个亚型，功能合计即两亚型之和；'
           '取均值是本技能为保持量程所作的约定，与合计只差一个常数倍，不改变排序、轴差方向与贴合度',
    '排序': '按功能分从高到低；同分并列同一名次，其后名次顺延；与下一名差为本名次分数减下一名次分数',
    '分层': '在相邻名次的分差里取最大的两处切开，分成上、中、下三层；分差并列时取名次靠前的一处；'
          '只有一处分差时分两层；极差占量程低于 0.05（含八项全同分）时不分层。分层只描述这组分数内部的远近',
    '对立轴': '四组轴为 Te–Fi、Ti–Fe、Se–Ni、Si–Ne，即同一型功能栈里主导对劣势、辅助对第三的配对；差为前项减后项',
    '合计': '外倾功能为 Se、Ne、Te、Fe，内倾功能为 Si、Ni、Ti、Fi；判断功能为 Te、Ti、Fe、Fi，知觉功能为 Se、Si、Ne、Ni',
    '类型贴合度': '对十六型逐一计算：把该型八个位置的功能（前四位为标准功能栈，后四位为各自的反向态度）'
             '配上位置期望分 42、37、33、24、31、31、20、22，与实际八功能分求皮尔逊相关系数，范围 −1 到 1，'
             '保留四位小数后从高到低排列。相关系数与量纲无关，分数几乎拉不开时也能算出很高的数，'
             '所以极差占量程低于 0.05 时首选置空、不定假说；八项全同分（最高减最低小于 1e-9）时相关系数无定义，候选也为空。'
             '各键在所有情况下都存在，无值时为 null 或空列表',
    '位置期望分': '取自 JUNGUS 第二代测验公开的 64 型原型矩阵（每型十六项合计 240），按八个位置归并功能合计得到；'
             '用于其他测验的八功能分时，它只是本技能的约定模板',
    '邻近型辨析': '对首选类型列出三个邻近型：主辅对调（如 INTJ 与 ENTJ）、同主导换辅助（如 INTJ 与 INFJ）、'
             '同辅助换主导（如 INTJ 与 ISTJ），并给出区分两者的那一对功能的分差',
    '展开': '首选功能栈、首选主辅分差、首选主导劣势分差、邻近型辨析四项展开的是“展开类型”所指的那一型，即贴合度最高的一型；'
          '并列时其余首选的同样四项在“各首选展开”里逐型列出',
    '并列': f'首选与次选贴合度之差小于 {CLOSE_MARGIN} 时记为并列假说，两型都要讲',
    '亚型方向': '知觉功能为 B−O，判断功能为 H−A；差为 0 记持平',
    '十六项合计': 'JUNGUS 第二代测验页面展示的十六项分数，是 64 型原型分数按后验概率加权的混合，合计恒为 240；'
             '合计与 240 相差超过 1 时“合计偏离240”为真，这组分数多半不是出自该测验的这一版本，位置期望分与后缀读法只能当约定用',
    '后缀': '按 JUNGUS 官方说明，第五字母看主导或辅助位上那个知觉功能偏主体（O）还是背景（B），'
          '第六字母看主导或辅助位上那个判断功能偏分析（A）还是整体（H）；该功能两亚型持平时后缀留空',
    '测验自带类型': '只比较字母是否一致，不重算测验的匹配百分比；JUNGUS 的百分比是 64 型后验概率的立方根乘以 100',
}


def _round(value, digits=4):
    return round(value + 0.0, digits)


def _pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def full_stack(type_code):
    """八个位置的功能：前四位为标准功能栈，后四位依次为其反向态度。"""
    top_four = STANDARD_STACKS[type_code]
    return top_four + [OPPOSITE[function] for function in top_four]


def parse_type_code(text):
    """接受四字母类型或 JUNGUS 六字母类型（如 INFJBH）；无法识别返回 None。"""
    if not isinstance(text, str):
        return None
    match = TYPE_CODE.match(text.strip().upper())
    if not match:
        return None
    base, fifth, sixth = match.groups()
    return {'四字母': base, '后缀': (fifth + sixth) if fifth else None}


def function_scores_from_subtypes(scores16):
    rows = {}
    for function in FUNCTIONS:
        left_key, right_key, _ = SUBTYPE_KEYS[function]
        left, right = scores16[left_key], scores16[right_key]
        rows[function] = {'合计': _round(left + right), '均值': _round((left + right) / 2)}
    return rows


def ranking(scores):
    ordered = sorted(FUNCTIONS, key=lambda f: (-scores[f], FUNCTIONS.index(f)))
    groups = []
    for function in ordered:
        if groups and abs(groups[-1]['分数'] - scores[function]) < EPS:
            groups[-1]['功能'].append(function)
        else:
            groups.append({'功能': [function], '分数': scores[function]})
    rank = 1
    for index, group in enumerate(groups):
        group['名次'] = rank
        rank += len(group['功能'])
        nxt = groups[index + 1]['分数'] if index + 1 < len(groups) else None
        group['与下一名差'] = None if nxt is None else _round(group['分数'] - nxt)
    return [{'名次': g['名次'], '功能': g['功能'], '分数': g['分数'], '与下一名差': g['与下一名差']}
            for g in groups]


def tiers(ranked):
    gaps = [(row['与下一名差'], index) for index, row in enumerate(ranked) if row['与下一名差'] is not None]
    cuts = sorted(index for _, index in sorted(gaps, key=lambda item: (-item[0], item[1]))[:2])
    names = {0: [], 1: ['上层', '下层'], 2: ['上层', '中层', '下层']}[len(cuts)]
    if not cuts:
        return []
    result, start = [], 0
    for name, end in zip(names, cuts + [len(ranked) - 1]):
        rows = ranked[start:end + 1]
        result.append({'层': name, '功能': [f for row in rows for f in row['功能']],
                       '分数范围': [rows[-1]['分数'], rows[0]['分数']],
                       '与下一层差': rows[-1]['与下一名差'] if end < len(ranked) - 1 else None})
        start = end + 1
    return result


def _lean(delta, positive, negative):
    if abs(delta) < EPS:
        return '持平'
    return positive if delta > 0 else negative


def axes(scores):
    rows = []
    for left, right in AXES:
        delta = _round(scores[left] - scores[right])
        rows.append({'轴': f'{left}–{right}', '两端': {left: scores[left], right: scores[right]},
                     '差': delta, '偏向': _lean(delta, left, right)})
    return rows


def totals(scores):
    def pair(name_a, keys_a, name_b, keys_b):
        a = _round(sum(scores[k] for k in keys_a))
        b = _round(sum(scores[k] for k in keys_b))
        return {name_a: a, name_b: b, '差': _round(a - b), '偏向': _lean(a - b, name_a, name_b)}

    return {
        '态度': pair('外倾功能合计', EXTRAVERTED, '内倾功能合计', INTROVERTED),
        '判断与知觉': pair('判断功能合计', JUDGING, '知觉功能合计', PERCEIVING),
        '感觉与直觉': pair('感觉合计', ('Se', 'Si'), '直觉合计', ('Ne', 'Ni')),
        '思考与情感': pair('思考合计', ('Te', 'Ti'), '情感合计', ('Fe', 'Fi')),
    }


def stack_rows(type_code, scores=None):
    rows = []
    for index, function in enumerate(full_stack(type_code)):
        row = {'位置': index + 1, '位置名': POSITIONS[index], '原型': ARCHETYPES[index], '功能': function}
        if scores is not None:
            row['分数'] = scores[function]
        rows.append(row)
    return rows


def neighbours(type_code, scores, fit_of):
    """与首选只差一步的三型：主辅对调、同主导换辅助、同辅助换主导，各列决定取舍的那一处分差。"""
    dominant, auxiliary = STANDARD_STACKS[type_code][:2]
    found = {}
    for other, stack in STANDARD_STACKS.items():
        if stack[0] == auxiliary and stack[1] == dominant:
            found['主辅对调'] = (other, dominant, auxiliary)
        elif stack[0] == dominant and stack[1] != auxiliary:
            found['同主导换辅助'] = (other, auxiliary, stack[1])
        elif stack[1] == auxiliary and stack[0] != dominant:
            found['同辅助换主导'] = (other, dominant, stack[0])
    rows = []
    for relation in ('主辅对调', '同主导换辅助', '同辅助换主导'):
        other, mine, theirs = found[relation]
        delta = _round(scores[mine] - scores[theirs])
        rows.append({'关系': relation, '类型': other, '贴合度': fit_of[other],
                     '判别': {'首选一侧': mine, '邻近型一侧': theirs, '差': delta,
                            '偏向': _lean(delta, '首选', '邻近型')}})
    return rows


def _expand(type_code, scores, fit_of):
    stack = STANDARD_STACKS[type_code]
    return {'类型': type_code, '功能栈': stack_rows(type_code, scores),
            '主辅分差': _round(scores[stack[0]] - scores[stack[1]]),
            '主导劣势分差': _round(scores[stack[0]] - scores[stack[3]]),
            '邻近型辨析': neighbours(type_code, scores, fit_of)}


def type_fit(scores, scale):
    """键集合固定；无值时为 None 或空列表。"""
    result = {'可定假说': False, '说明': None, '候选': [], '首选': [], '并列': False,
              '首选与次选贴合度差': None, '备选': [], '展开类型': None, '首选功能栈': [],
              '首选主辅分差': None, '首选主导劣势分差': None, '邻近型辨析': [], '各首选展开': []}
    spread = max(scores.values()) - min(scores.values())
    if spread < EPS:
        result['说明'] = '八项功能分全部相同，轮廓没有区分度，不提出类型假说'
        return result
    rows = []
    for type_code in STANDARD_STACKS:
        stack = full_stack(type_code)
        r = _pearson([scores[f] for f in stack], POSITION_EXPECTED)
        rows.append({'类型': type_code, '贴合度': _round(r), '主导': stack[0], '辅助': stack[1],
                     '第三': stack[2], '劣势': stack[3], '主辅搭配': f'{stack[0]}-{stack[1]}'})
    rows.sort(key=lambda row: (-row['贴合度'], list(STANDARD_STACKS).index(row['类型'])))
    for index, row in enumerate(rows):
        row['名次'] = index + 1
    result['候选'] = rows
    result['首选与次选贴合度差'] = _round(rows[0]['贴合度'] - rows[1]['贴合度'])
    if spread / scale < FLAT_RANGE - EPS:
        result['说明'] = '分数几乎拉不开，不足以定类型假说；候选只列出算术结果，不作首选'
        return result
    best = rows[0]['贴合度']
    first = [row['类型'] for row in rows if best - row['贴合度'] < CLOSE_MARGIN - EPS]
    fit_of = {row['类型']: row['贴合度'] for row in rows}
    expanded = [_expand(code, scores, fit_of) for code in first]
    result.update({
        '可定假说': True,
        '首选': first,
        '并列': len(first) > 1,
        '备选': [row['类型'] for row in rows[len(first):len(first) + 2]],
        '展开类型': first[0],
        '首选功能栈': expanded[0]['功能栈'],
        '首选主辅分差': expanded[0]['主辅分差'],
        '首选主导劣势分差': expanded[0]['主导劣势分差'],
        '邻近型辨析': expanded[0]['邻近型辨析'],
        '各首选展开': expanded,
    })
    return result


def subtype_structure(scores16):
    pairs = []
    sums = {'O': 0.0, 'B': 0.0, 'A': 0.0, 'H': 0.0}
    for function in FUNCTIONS:
        left_key, right_key, _ = SUBTYPE_KEYS[function]
        left, right = scores16[left_key], scores16[right_key]
        left_tag, right_tag = left_key[-1], right_key[-1]
        delta = _round(right - left)
        sums[left_tag] += left
        sums[right_tag] += right
        pairs.append({'功能': function, '类别': '知觉' if function in PERCEIVING else '判断',
                      '两亚型': {left_key: left, right_key: right},
                      '差': delta, '差的方向': f'{right_tag}−{left_tag}',
                      '偏向': _lean(delta, right_tag, left_tag),
                      '合计': _round(left + right), '均值': _round((left + right) / 2)})
    leans_p = {row['偏向'] for row in pairs if row['类别'] == '知觉'}
    leans_j = {row['偏向'] for row in pairs if row['类别'] == '判断'}
    total = _round(sum(scores16.values()))
    return {
        '各功能': pairs,
        '十六项合计': total,
        '合计偏离240': abs(total - 240) > TOTAL_TOLERANCE,
        '知觉四功能': {'主体O合计': _round(sums['O']), '背景B合计': _round(sums['B']),
                    '差': _round(sums['B'] - sums['O']), '偏向': _lean(sums['B'] - sums['O'], 'B', 'O'),
                    '四功能同向': len(leans_p) == 1 and '持平' not in leans_p},
        '判断四功能': {'分析A合计': _round(sums['A']), '整体H合计': _round(sums['H']),
                    '差': _round(sums['H'] - sums['A']), '偏向': _lean(sums['H'] - sums['A'], 'H', 'A'),
                    '四功能同向': len(leans_j) == 1 and '持平' not in leans_j},
        '字母含义': SUBTYPE_NAMES,
    }


def suffix_for(type_code, subtype_rows):
    """按官方说明取主导或辅助位上的知觉功能、判断功能各自的亚型偏向。"""
    by_function = {row['功能']: row for row in subtype_rows}
    dominant, auxiliary = STANDARD_STACKS[type_code][:2]
    perceiving = dominant if dominant in PERCEIVING else auxiliary
    judging = dominant if dominant in JUDGING else auxiliary
    fifth, sixth = by_function[perceiving]['偏向'], by_function[judging]['偏向']
    complete = '持平' not in (fifth, sixth)
    return {'类型': type_code, '主要知觉功能': perceiving, '第五字母': None if fifth == '持平' else fifth,
            '主要判断功能': judging, '第六字母': None if sixth == '持平' else sixth,
            '六字母': type_code + fifth + sixth if complete else None}


def compare_reported(reported, fit, suffixes):
    parsed = parse_type_code(reported)
    if parsed is None:
        return {'原文': reported, '可识别': False,
                '说明': '不是四字母类型或 JUNGUS 六字母类型，只作为自述保留，不参与比较'}
    base = parsed['四字母']
    row = next((r for r in fit['候选'] if r['类型'] == base), None)
    result = {'原文': reported, '可识别': True, **parsed,
              '在候选中的名次': row['名次'] if row else None,
              '贴合度': row['贴合度'] if row else None,
              '与首选一致': base in fit['首选'] if fit['首选'] else None}
    if parsed['后缀'] and suffixes:
        mine = next((s for s in suffixes if s['类型'] == base), None)
        if mine is not None:
            derived = (mine['第五字母'] or '') + (mine['第六字母'] or '')
            result['本技能推得后缀'] = derived or None
            result['后缀一致'] = derived == parsed['后缀']
    return result


def build_structure(scores, scale, *, scores16=None, reported_type=None):
    """scores 为八功能分（十六亚型输入时传 None，由 scores16 取均值）；scale 为量程上限。"""
    derived = None
    if scores16 is not None:
        derived = function_scores_from_subtypes(scores16)
        scores = {function: derived[function]['均值'] for function in FUNCTIONS}
    ranked = ranking(scores)
    high, low = ranked[0]['分数'], ranked[-1]['分数']
    flat = (high - low) / scale < FLAT_RANGE - EPS
    fit = type_fit(scores, scale)
    structure = {
        '功能分': {'来源': '两亚型均值' if scores16 is not None else '原始八功能分',
                 '量程': scale, '各功能': {function: scores[function] for function in FUNCTIONS}},
        '排序': ranked,
        '分层': [] if flat else tiers(ranked),
        '极差': {'最高': {'功能': ranked[0]['功能'], '分数': high},
               '最低': {'功能': ranked[-1]['功能'], '分数': low},
               '差': _round(high - low), '差占量程': _round((high - low) / scale)},
        '对立轴': axes(scores),
        '合计': totals(scores),
        '类型贴合度': fit,
    }
    suffixes = []
    if scores16 is not None:
        structure['功能分']['两亚型合计'] = {f: derived[f]['合计'] for f in FUNCTIONS}
        subtype = subtype_structure(scores16)
        suffixes = [suffix_for(code, subtype['各功能'])
                    for code in fit['首选'] + fit['备选']]
        subtype['候选后缀'] = suffixes
        structure['亚型'] = subtype
    if reported_type is not None:
        structure['测验自带类型'] = compare_reported(reported_type, fit, suffixes)
    structure['取法'] = dict(METHOD)
    return structure


def build_type_structure(type_code, suffix=None, original=None):
    """只有类型、没有分数时的理论结构；suffix 为六字母类型的后两位。"""
    stack = full_stack(type_code)
    axis_of = {function: f'{left}–{right}' for left, right in AXES for function in (left, right)}
    return {
        '功能栈': stack_rows(type_code),
        '主辅搭配': f'{stack[0]}-{stack[1]}',
        '主导轴': axis_of[stack[0]],
        '辅助轴': axis_of[stack[1]],
        '原文': original or type_code,
        '后缀': suffix,
        '取法': {'功能栈': '前四位按类型理论的标准功能栈，后四位为各自的反向态度，位置名按 Beebe 八原型模型；'
                       '这是类型标签的理论展开，没有分数可以对照',
               '后缀': '输入为六字母类型时，前四位作类型，后两位原样记为后缀；没有亚型分数，后缀不作推算'},
    }
