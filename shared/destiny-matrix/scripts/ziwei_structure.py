#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由已排出的十二宫确定性派生的盘面关系：三方四正、空宫借星、邻宫、四化落点。

只列构成事实，不判格局成立、吉凶或强弱；采用三合派的宫位关系，不含宫干飞化。
"""
EB = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
MUTAGEN_ORDER = ['禄', '权', '科', '忌']

METHOD = {
    '三方四正': '本宫、对宫（地支相冲位）与两个三合宫（地支三合位）',
    '空宫借星': '本宫无十四主星时列出对宫主星及其在对宫的亮度；是否借用、借后亮度如何论，'
            '属解读取法，记在 claim 的方法说明里',
    '邻宫': '前后相邻两宫的主星与辅星，供判断夹宫；不判夹宫格局是否成立',
    '生年四化': '取排盘结果中标在星曜上的化禄、化权、化科、化忌及其落宫',
    '运限四化': '大限、流年天干四化按禄权科忌顺序，对应星曜在本命盘的落宫',
    '未采用': '宫干飞化、自化未计算',
}


def _names(stars):
    return [star['名称'] for star in stars]


def _brief(palace):
    return {'宫位': palace['宫位'], '地支': palace['地支'],
            '主星': [{'名称': s['名称'], '亮度': s['亮度'], '四化': s['四化']}
                     for s in palace['主星']]}


def _locate(palaces, star_name):
    for palace in palaces:
        for group in ('主星', '辅星', '杂耀'):
            if star_name in _names(palace.get(group, [])):
                return {'宫位': palace['宫位'], '地支': palace['地支'], '星曜类别': group}
    return None


def _period(palaces, period):
    if not isinstance(period, dict) or '四化' not in period:
        return None
    rows = []
    for kind, star in zip(MUTAGEN_ORDER, period['四化']):
        rows.append({'四化': kind, '星曜': star, '本命落宫': _locate(palaces, star)})
    branch = period.get('地支')
    host = next((p['宫位'] for p in palaces if p['地支'] == branch), None)
    return {'天干': period.get('天干'), '地支': branch,
            '命宫所在本命宫': host, '四化': rows}


def build_structure(palaces, horoscope=None):
    by_branch = {palace['地支']: palace for palace in palaces}
    if sorted(by_branch) != sorted(EB):
        raise ValueError('十二宫地支不完整，无法派生宫位关系')

    def at(branch, offset):
        return by_branch[EB[(EB.index(branch) + offset) % 12]]

    relations = []
    for palace in palaces:
        branch = palace['地支']
        opposite = at(branch, 6)
        row = {
            '宫位': palace['宫位'], '地支': branch,
            '主星': _brief(palace)['主星'], '空宫': not palace['主星'],
            '对宫': _brief(opposite),
            '三合宫': [_brief(at(branch, 4)), _brief(at(branch, 8))],
            '邻宫': [
                {'宫位': p['宫位'], '地支': p['地支'],
                 '主星': _names(p['主星']), '辅星': _names(p['辅星'])}
                for p in (at(branch, -1), at(branch, 1))
            ],
        }
        row['借对宫主星'] = _brief(opposite)['主星'] if row['空宫'] else None
        row['三方四正四化'] = [
            {'四化': star['四化'], '星曜': star['名称'], '宫位': member['宫位']}
            for member in (palace, opposite, at(branch, 4), at(branch, 8))
            for group in ('主星', '辅星')
            for star in member[group] if star['四化']
        ]
        relations.append(row)

    natal = [
        {'四化': star['四化'], '星曜': star['名称'], '亮度': star['亮度'],
         '宫位': palace['宫位'], '地支': palace['地支']}
        for palace in palaces for group in ('主星', '辅星', '杂耀')
        for star in palace.get(group, []) if star['四化']
    ]
    natal.sort(key=lambda row: MUTAGEN_ORDER.index(row['四化'])
               if row['四化'] in MUTAGEN_ORDER else len(MUTAGEN_ORDER))

    horoscope = horoscope or {}
    return {
        '命宫': next(({'地支': p['地支']} for p in palaces if p['宫位'] == '命宫'), None),
        '身宫': next(({'所在宫位': p['宫位'], '地支': p['地支']}
                    for p in palaces if p.get('是否身宫')), None),
        '空宫': [p['宫位'] for p in palaces if not p['主星']],
        '宫位关系': relations,
        '生年四化': natal,
        '当前大限四化': _period(palaces, horoscope.get('当前大限')),
        '当前流年四化': _period(palaces, horoscope.get('当前流年')),
        '取法': METHOD,
    }
