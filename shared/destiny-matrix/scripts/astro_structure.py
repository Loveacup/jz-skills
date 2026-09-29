#!/usr/bin/env python3
"""由已计算的星体、宫头与相位确定性派生的盘面结构。

只列构成事实与所用查表，不给强弱评分、吉凶或心理含义；
传统守护与现代守护并列给出，采用哪一套由解读说明。
"""
from __future__ import annotations

from itertools import combinations

SIGNS = ['白羊', '金牛', '双子', '巨蟹', '狮子', '处女',
         '天秤', '天蝎', '射手', '摩羯', '水瓶', '双鱼']
ELEMENTS = ['火', '土', '风', '水']
MODES = ['开创', '固定', '变动']
TEN_PLANETS = ['太阳', '月亮', '水星', '金星', '火星', '木星', '土星',
               '天王星', '海王星', '冥王星']
SEVEN_PLANETS = TEN_PLANETS[:7]

RULERS_TRADITIONAL = {
    '白羊': '火星', '金牛': '金星', '双子': '水星', '巨蟹': '月亮',
    '狮子': '太阳', '处女': '水星', '天秤': '金星', '天蝎': '火星',
    '射手': '木星', '摩羯': '土星', '水瓶': '土星', '双鱼': '木星',
}
RULERS_MODERN = {**RULERS_TRADITIONAL, '天蝎': '冥王星', '水瓶': '天王星', '双鱼': '海王星'}
RULER_SCHEMES = {'传统守护': RULERS_TRADITIONAL, '现代守护': RULERS_MODERN}
EXALTATION = {'太阳': '白羊', '月亮': '金牛', '水星': '处女', '金星': '双鱼',
              '火星': '摩羯', '木星': '巨蟹', '土星': '天秤'}
ANGLE_NAMES = ['上升', '天底', '下降', '天顶']

METHOD = {
    '守护': '传统守护为七星制；现代守护将天蝎、水瓶、双鱼改配冥王星、天王星、海王星；两套并列，不择一；'
          '解读采用哪一套记在 claim 的方法说明里',
    '先天尊贵': '仅七颗传统行星；入庙=本垣(domicile)、擢升=exaltation、失势=detriment(入庙对宫)、落陷=fall(擢升对宫)；'
            '三分主星、界、面未计算，不作强弱评分',
    '盘别': '太阳黄经在下降点至上升点之间（经天顶一侧）为日盘，否则为夜盘；与宫制无关',
    '定位星链': '沿所在星座的守护星逐级上溯，至入庙星或循环为止',
    '互容': '仅按守护（入庙）互容；擢升互容与混合互容未计算',
    '元素模式': '太阳至冥王星十星等权计数；上升、天顶与其他配点不计入',
    '相位趋势': '按出生瞬间两星黄经日速判断偏差在缩小（入相）或扩大（出相），两星同速记持平；'
            '不判断成相前是否停滞转向或换座，不含视差与纬度',
    '相位图形': '仅取十星之间已成立的主要相位；大三角=三星两两三合，T三角=一组对冲加顶点对两端四分，'
            '大十字=两组对冲且四星依次四分，其内含的 T 三角不另列；图形内最宽偏差一并列出',
    '星群': '同一星座或同一宫内三颗及以上十星',
    '轴点合相': '十星与上升、天顶、下降、天底的黄经差不超过合相容许度',
    '宫界距离': '星体到所在宫宫头与下一宫宫头的黄经距离；是否按邻宫解读由解读说明',
}


def sign_of(longitude: float) -> str:
    return SIGNS[int((longitude % 360.0) / 30)]


def _arc(start: float, end: float) -> float:
    return (end - start) % 360.0


def _separation(a: float, b: float) -> float:
    delta = abs((a - b) % 360.0)
    return min(delta, 360.0 - delta)


def dignity(planet: str, sign: str) -> list[str]:
    if planet not in SEVEN_PLANETS:
        return []
    found = []
    index = SIGNS.index(sign)
    opposite = SIGNS[(index + 6) % 12]
    if RULERS_TRADITIONAL[sign] == planet:
        found.append('入庙')
    if EXALTATION[planet] == sign:
        found.append('擢升')
    if RULERS_TRADITIONAL[opposite] == planet:
        found.append('失势')
    if EXALTATION[planet] == opposite:
        found.append('落陷')
    return found


def dispositor_chain(planet: str, signs: dict, rulers: dict) -> dict:
    chain, current = [planet], planet
    while True:
        ruler = rulers[signs[current]]
        if ruler not in signs:
            return {'链': chain + [ruler], '终点': None, '类型': '定位星无数据'}
        if ruler == current:
            return {'链': chain, '终点': current, '类型': '入庙星'}
        if ruler in chain:
            return {'链': chain + [ruler], '终点': None, '类型': '循环',
                    '循环成员': chain[chain.index(ruler):]}
        chain.append(ruler)
        current = ruler


def aspect_trend(name: str, exact: float, a: dict, b: dict) -> str | None:
    speed_a, speed_b = a.get('黄经日速'), b.get('黄经日速')
    if speed_a is None or speed_b is None or '黄经' not in a or '黄经' not in b:
        return None
    signed = ((b['黄经'] - a['黄经'] + 180.0) % 360.0) - 180.0
    separation_rate = (1 if signed >= 0 else -1) * (speed_b - speed_a)
    gap = abs(signed) - exact
    if gap == 0:
        return '正相位'
    if separation_rate == 0:
        return '持平'
    return '入相' if (gap > 0) != (separation_rate > 0) else '出相'


ASPECT_EXACT = {'合相': 0.0, '对冲': 180.0, '三合': 120.0, '四分': 90.0, '六合': 60.0}


def _patterns(aspects: list[dict]) -> list[dict]:
    table = {}
    for row in aspects:
        a, b = row['行星A'], row['行星B']
        if a in TEN_PLANETS and b in TEN_PLANETS:
            table[frozenset((a, b))] = row
    planets = [p for p in TEN_PLANETS if any(p in key for key in table)]

    def kind(a, b):
        row = table.get(frozenset((a, b)))
        return row['相位'] if row else None

    def widest(pairs):
        return max(table[frozenset(pair)]['偏差'] for pair in pairs)

    found = []
    for trio in combinations(planets, 3):
        pairs = list(combinations(trio, 2))
        if all(kind(*pair) == '三合' for pair in pairs):
            found.append({'类型': '大三角', '成员': list(trio), '最宽偏差': widest(pairs)})
        for apex in trio:
            base = [p for p in trio if p != apex]
            if (kind(*base) == '对冲'
                    and all(kind(apex, p) == '四分' for p in base)):
                found.append({'类型': 'T三角', '成员': list(trio), '顶点': apex,
                              '对冲两端': base, '最宽偏差': widest(pairs)})
    crosses = []
    for quad in combinations(planets, 4):
        pairs = list(combinations(quad, 2))
        kinds = [kind(*pair) for pair in pairs]
        if kinds.count('对冲') == 2 and kinds.count('四分') == 4:
            crosses.append({'类型': '大十字', '成员': list(quad), '最宽偏差': widest(pairs)})
    # 大十字内含的四个 T 三角不重复列出
    found = [row for row in found if row['类型'] != 'T三角'
             or not any(set(row['成员']) <= set(cross['成员']) for cross in crosses)]
    return found + crosses


def build_structure(positions: dict, cusps, asc: float | None, mc: float | None,
                    aspects: list[dict], conjunction_orb: float) -> dict:
    ten = {name: positions[name] for name in TEN_PLANETS if '黄经' in positions.get(name, {})}
    signs = {name: row['星座'] for name, row in ten.items()}

    element_rows = {key: [] for key in ELEMENTS}
    mode_rows = {key: [] for key in MODES}
    for name, sign in signs.items():
        index = SIGNS.index(sign)
        element_rows[ELEMENTS[index % 4]].append(name)
        mode_rows[MODES[index % 3]].append(name)

    rulers = {}
    for scheme, table in RULER_SCHEMES.items():
        chains = {name: dispositor_chain(name, signs, table) for name in ten}
        receptions = [
            {'行星': [a, b], '星座': [signs[a], signs[b]]}
            for a, b in combinations(ten, 2)
            if table[signs[a]] == b and table[signs[b]] == a
        ]
        rulers[scheme] = {
            '定位星': {name: table[sign] for name, sign in signs.items()},
            '定位星链': chains,
            '终点定位星': sorted({row['终点'] for row in chains.values() if row['终点']},
                            key=TEN_PLANETS.index),
            '互容': receptions,
        }

    stelliums = []
    for sign in SIGNS:
        members = [name for name, value in signs.items() if value == sign]
        if len(members) >= 3:
            stelliums.append({'范围': '星座', '位置': sign, '成员': members})

    result = {
        '先天尊贵': {name: {'星座': signs[name], '状态': dignity(name, signs[name])}
                  for name in SEVEN_PLANETS if name in ten},
        '元素分布': {key: {'数量': len(value), '成员': value}
                  for key, value in element_rows.items()},
        '模式分布': {key: {'数量': len(value), '成员': value}
                  for key, value in mode_rows.items()},
        '守护': rulers,
        '相位趋势': [
            {'行星A': row['行星A'], '行星B': row['行星B'], '相位': row['相位'],
             '偏差': row['偏差'],
             '趋势': aspect_trend(row['相位'], ASPECT_EXACT[row['相位']],
                                positions.get(row['行星A'], {}),
                                positions.get(row['行星B'], {}))}
            for row in aspects
        ],
        '相位图形': _patterns(aspects),
        '盘别': None, '命主星': None, '轴点合相': None,
        '宫主落宫': None, '宫内行星': None, '宫界距离': None,
    }

    if asc is not None:
        if '太阳' in ten:
            result['盘别'] = '日盘' if _arc(asc, ten['太阳']['黄经']) >= 180.0 else '夜盘'
        asc_sign = sign_of(asc)
        result['命主星'] = {'上升星座': asc_sign, **{
            scheme: {'行星': table[asc_sign],
                     '星座': signs.get(table[asc_sign]),
                     '落宫': ten.get(table[asc_sign], {}).get('落宫')}
            for scheme, table in RULER_SCHEMES.items()
        }}
        if mc is not None:
            angles = dict(zip(ANGLE_NAMES, [asc, (mc + 180.0) % 360.0,
                                            (asc + 180.0) % 360.0, mc]))
            result['轴点合相'] = [
                {'行星': name, '轴点': angle, '偏差': _separation(row['黄经'], value)}
                for name, row in ten.items() for angle, value in angles.items()
                if _separation(row['黄经'], value) <= conjunction_orb
            ]

    if cusps is not None:
        house_rows, occupants, distances = [], {}, {}
        for index, cusp in enumerate(cusps):
            sign = sign_of(cusp)
            row = {'宫位': index + 1, '宫始星座': sign}
            for scheme, table in RULER_SCHEMES.items():
                ruler = table[sign]
                row[scheme] = {'宫主': ruler, '星座': signs.get(ruler),
                               '落宫': ten.get(ruler, {}).get('落宫')}
            house_rows.append(row)
            occupants[str(index + 1)] = [name for name, item in ten.items()
                                         if item.get('落宫') == index + 1]
        for name, item in ten.items():
            house = item.get('落宫')
            if house:
                distances[name] = {
                    '落宫': house,
                    '距本宫宫头': _arc(cusps[house - 1], item['黄经']),
                    '距下一宫宫头': _arc(item['黄经'], cusps[house % 12]),
                }
        for house, members in occupants.items():
            if len(members) >= 3:
                stelliums.append({'范围': '宫位', '位置': int(house), '成员': members})
        result['宫主落宫'] = house_rows
        result['宫内行星'] = occupants
        result['宫界距离'] = distances

    result['星群'] = stelliums
    result['取法'] = METHOD
    return result
