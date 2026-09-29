#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由最终四柱确定性派生的结构字段：藏干分层、月令、十二长生、禄刃、通根透干、干支关系。

只列构成事实与所用查表，不输出旺衰定级、格局成立、合化成败或用神结论；
这些判断属于传统解释，由 analyst 按 framework 的推读路径给出。
"""
from itertools import combinations

from bazi_calc import GAN_WX, GAN_YINYANG, HIDDEN_WEIGHTS, EB, calc_shishen_gan

PILLAR_NAMES = ['年柱', '月柱', '日柱', '时柱']
# 藏干层名逐支写明：四库（辰戌丑未）以上月残留为余气、墓库所藏为中气，与权重次序不同
HIDDEN_LAYERS = {
    '子': ['本气'], '卯': ['本气'], '酉': ['本气'],
    '午': ['本气', '中气'], '亥': ['本气', '中气'],
    '寅': ['本气', '中气', '余气'], '申': ['本气', '中气', '余气'],
    '巳': ['本气', '中气', '余气'],
    '辰': ['本气', '余气', '中气'], '戌': ['本气', '余气', '中气'],
    '丑': ['本气', '余气', '中气'], '未': ['本气', '余气', '中气'],
}
SEASON_WX = {'寅': '木', '卯': '木', '辰': '木', '巳': '火', '午': '火', '未': '火',
             '申': '金', '酉': '金', '戌': '金', '亥': '水', '子': '水', '丑': '水'}

SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}

# 十二长生：阳干顺行、阴干逆行；戊随丙、己随丁（火土同宫）
STAGES = ['长生', '沐浴', '冠带', '临官', '帝旺', '衰', '病', '死', '墓', '绝', '胎', '养']
CHANGSHENG_START = {
    '甲': '亥', '丙': '寅', '戊': '寅', '庚': '巳', '壬': '申',
    '乙': '午', '丁': '酉', '己': '酉', '辛': '子', '癸': '卯',
}

GAN_HE = {frozenset('甲己'): ['土'], frozenset('乙庚'): ['金'], frozenset('丙辛'): ['水'],
          frozenset('丁壬'): ['木'], frozenset('戊癸'): ['火']}
GAN_CHONG = {frozenset('甲庚'), frozenset('乙辛'), frozenset('丙壬'), frozenset('丁癸')}

ZHI_LIUHE = {frozenset('子丑'): ['土'], frozenset('寅亥'): ['木'], frozenset('卯戌'): ['火'],
             frozenset('辰酉'): ['金'], frozenset('巳申'): ['水'], frozenset('午未'): ['火', '土']}
ZHI_CHONG = {frozenset('子午'), frozenset('丑未'), frozenset('寅申'),
             frozenset('卯酉'), frozenset('辰戌'), frozenset('巳亥')}
ZHI_HAI = {frozenset('子未'), frozenset('丑午'), frozenset('寅巳'),
           frozenset('卯辰'), frozenset('申亥'), frozenset('酉戌')}
ZHI_PO = {frozenset('子酉'), frozenset('卯午'), frozenset('辰丑'),
          frozenset('未戌'), frozenset('寅亥'), frozenset('巳申')}
ZHI_ZIXING = {'辰', '午', '酉', '亥'}
ZHI_XING_GROUPS = {'寅巳申': '无恩之刑', '丑戌未': '恃势之刑'}
ZHI_XING_PAIR = {frozenset('子卯'): '无礼之刑'}
# 三合局按（长生, 帝旺, 墓）排列
SANHE = {'申子辰': '水', '亥卯未': '木', '寅午戌': '火', '巳酉丑': '金'}
SANHUI = {'寅卯辰': '木', '巳午未': '火', '申酉戌': '金', '亥子丑': '水'}

METHOD = {
    '藏干分层': '四库以上月残留为余气、墓库所藏为中气，寅申巳亥以长生之气为中气；权重为固定值；未采用月令分日用事',
    '十二长生': '阳干顺行、阴干逆行，戊随丙、己随丁；阴阳同生同死等取法未采用',
    '禄': '日干临官位',
    '羊刃': '仅阳干取帝旺位；阴干取法各家不一，不输出',
    '月令状态': '日主月令状态以月支本气五行论旺相休囚死，辰戌丑未月按土论；季月另给按所属季节五行论的状态，'
            '两者取哪一个属解读取法；本字段是月令一项的五行关系，不是旺衰定级',
    '通根': '地支藏干与该天干同五行即记一处根，并注明层次与权重',
    '透干': '地支藏干的同一天干出现在四柱天干',
    '干支关系': '只列构成，不判合化成败、冲之胜负或刑害轻重；合化五行为列表，午未合列火、土两说；'
            '半合、半会须含中间旺支，缺旺支的两支记拱合、拱会；三支齐全时不重复列同组的两支关系；'
            '相同地支记同支，属自刑四支的另记自刑；半会、拱合、拱会各家取舍不一，采用与否记在 claim 的方法说明里',
    '同柱': '原局两柱或来柱与原局某柱干支全同记伏吟；天干地支俱冲只取天干四冲配地支六冲，'
          '戊己与他干的相克不计，未列出不代表没有天克地冲',
    '十神分组固定权重合计': '天干各计 1.0、藏干按固定权重；日主自身另列；只是计数，不是旺衰定级，也不据此定扶抑',
}


def changsheng_stage(gan, zhi):
    start = EB.index(CHANGSHENG_START[gan])
    step = 1 if GAN_YINYANG[gan] == '阳' else -1
    return STAGES[((EB.index(zhi) - start) * step) % 12]


def lu_branch(gan):
    return next(zhi for zhi in EB if changsheng_stage(gan, zhi) == '临官')


def yangren_branch(gan):
    if GAN_YINYANG[gan] != '阳':
        return None
    return next(zhi for zhi in EB if changsheng_stage(gan, zhi) == '帝旺')


def month_state(day_wx, month_wx):
    if day_wx == month_wx:
        return '旺'
    if SHENG[month_wx] == day_wx:
        return '相'
    if SHENG[day_wx] == month_wx:
        return '休'
    if KE[day_wx] == month_wx:
        return '囚'
    return '死'


def _distance(i, j):
    return {1: '相邻', 2: '隔一柱', 3: '隔两柱'}[abs(i - j)]


def _gan_pair(a, b):
    key = frozenset((a, b))
    if key in GAN_HE:
        return {'类型': '五合', '合化五行': GAN_HE[key]}
    if key in GAN_CHONG:
        return {'类型': '相冲'}
    return None


def _zhi_pairs(a, b):
    """两个地支之间成立的全部关系（同一对可同时有合与刑、合与破）。"""
    found = []
    if a == b:
        found.append({'类型': '同支'})
        if a in ZHI_ZIXING:
            found.append({'类型': '自刑'})
        return found
    key = frozenset((a, b))
    if key in ZHI_LIUHE:
        found.append({'类型': '六合', '合化五行': ZHI_LIUHE[key]})
    if key in ZHI_CHONG:
        found.append({'类型': '六冲'})
    for group, name in ZHI_XING_GROUPS.items():
        if a in group and b in group:
            found.append({'类型': '相刑', '刑名': name, '组': group})
    if key in ZHI_XING_PAIR:
        found.append({'类型': '相刑', '刑名': ZHI_XING_PAIR[key]})
    if key in ZHI_HAI:
        found.append({'类型': '相害'})
    if key in ZHI_PO:
        found.append({'类型': '相破'})
    for group, wx in SANHE.items():
        if a in group and b in group:
            has_peak = group[1] in (a, b)
            found.append({'类型': '半合' if has_peak else '拱合', '局': group, '五行': wx,
                          '缺': next(z for z in group if z not in (a, b))})
    for group, wx in SANHUI.items():
        if a in group and b in group:
            found.append({'类型': '半会' if group[1] in (a, b) else '拱会',
                          '方': group, '五行': wx,
                          '缺': next(z for z in group if z not in (a, b))})
    return found


def _full_groups(zhis, labels):
    """三合局、三会方、三刑全：三支齐全才列。"""
    found = []
    tables = [('三合局', SANHE), ('三会方', SANHUI), ('三刑全', ZHI_XING_GROUPS)]
    for kind, table in tables:
        for group, value in table.items():
            if all(z in zhis for z in group):
                row = {'类型': kind, '地支': group,
                       '位置': {z: [labels[i] for i, x in enumerate(zhis) if x == z]
                                for z in group}}
                row['刑名' if kind == '三刑全' else '五行'] = value
                found.append(row)
    return found


def _drop_completed(rows, groups):
    """三支已齐全时，不再重复列同一局/方的两支关系。"""
    done = {row['地支'] for row in groups}
    return [row for row in rows
            if row.get('局', row.get('方', row.get('组'))) not in done]


def natal_relations(gans, zhis):
    gan_rows, zhi_rows = [], []
    for i, j in combinations(range(4), 2):
        pair = _gan_pair(gans[i], gans[j])
        if pair:
            gan_rows.append({**pair, '天干': [gans[i], gans[j]],
                             '位置': [PILLAR_NAMES[i], PILLAR_NAMES[j]],
                             '间距': _distance(i, j)})
        for pair in _zhi_pairs(zhis[i], zhis[j]):
            zhi_rows.append({**pair, '地支': [zhis[i], zhis[j]],
                             '位置': [PILLAR_NAMES[i], PILLAR_NAMES[j]],
                             '间距': _distance(i, j)})
    groups = _full_groups(zhis, PILLAR_NAMES)
    same = [{'类型': '伏吟', '干支': gans[i] + zhis[i],
             '位置': [PILLAR_NAMES[i], PILLAR_NAMES[j]], '间距': _distance(i, j)}
            for i, j in combinations(range(4), 2)
            if gans[i] == gans[j] and zhis[i] == zhis[j]]
    return {'天干': gan_rows, '地支': _drop_completed(zhi_rows, groups),
            '同柱': same, '三支成组': groups}


def incoming_relations(ganzhi, gans, zhis):
    """大运或流年干支与原局四柱的关系；只列构成。"""
    gan, zhi = ganzhi[0], ganzhi[1]
    gan_rows, zhi_rows, same = [], [], []
    for i in range(4):
        pair = _gan_pair(gan, gans[i])
        if pair:
            gan_rows.append({**pair, '对应': gans[i], '位置': PILLAR_NAMES[i]})
        for pair in _zhi_pairs(zhi, zhis[i]):
            zhi_rows.append({**pair, '对应': zhis[i], '位置': PILLAR_NAMES[i]})
        if gan == gans[i] and zhi == zhis[i]:
            same.append({'类型': '伏吟', '位置': PILLAR_NAMES[i]})
        elif (frozenset((gan, gans[i])) in GAN_CHONG
              and frozenset((zhi, zhis[i])) in ZHI_CHONG):
            same.append({'类型': '天干地支俱冲', '位置': PILLAR_NAMES[i]})
    groups = [row for row in _full_groups(list(zhis) + [zhi], PILLAR_NAMES + ['来支'])
              if not all(z in zhis for z in row['地支'])]
    return {'天干': gan_rows, '地支': _drop_completed(zhi_rows, groups),
            '同柱': same, '三支成组': groups}


def build_structure(gans, zhis, *, dayun=(), liunian=()):
    """gans/zhis 为年月日时四柱的天干与地支；dayun/liunian 为已计算的干支条目。"""
    day_gan, month_zhi = gans[2], zhis[1]
    day_wx = GAN_WX[day_gan]

    hidden = []
    for name, zhi in zip(PILLAR_NAMES, zhis):
        hidden.append({'柱': name, '地支': zhi, '藏干': [
            {'天干': stem, '层': HIDDEN_LAYERS[zhi][k], '权重': weight,
             '五行': GAN_WX[stem], '十神': calc_shishen_gan(day_gan, stem),
             '透干': [PILLAR_NAMES[i] for i, g in enumerate(gans) if g == stem]}
            for k, (stem, weight) in enumerate(HIDDEN_WEIGHTS[zhi])
        ]})

    roots = []
    for i, gan in enumerate(gans):
        found = [
            {'柱': PILLAR_NAMES[j], '地支': zhi, '藏干': stem,
             '层': HIDDEN_LAYERS[zhi][k], '权重': weight, '同干': stem == gan}
            for j, zhi in enumerate(zhis)
            for k, (stem, weight) in enumerate(HIDDEN_WEIGHTS[zhi])
            if GAN_WX[stem] == GAN_WX[gan]
        ]
        roots.append({'柱': PILLAR_NAMES[i], '天干': gan,
                      '十神': '日主' if i == 2 else calc_shishen_gan(day_gan, gan),
                      '自坐十二长生': changsheng_stage(gan, zhis[i]),
                      '根': found})

    lu, ren = lu_branch(day_gan), yangren_branch(day_gan)
    month_main = HIDDEN_WEIGHTS[month_zhi][0][0]

    groups = {'比劫': 0.0, '印': 0.0, '食伤': 0.0, '财': 0.0, '官杀': 0.0}
    group_of = {'比肩': '比劫', '劫财': '比劫', '正印': '印', '偏印': '印',
                '食神': '食伤', '伤官': '食伤', '正财': '财', '偏财': '财',
                '正官': '官杀', '七杀': '官杀'}
    for i, gan in enumerate(gans):
        if i != 2:
            groups[group_of[calc_shishen_gan(day_gan, gan)]] += 1.0
    for zhi in zhis:
        for stem, weight in HIDDEN_WEIGHTS[zhi]:
            groups[group_of[calc_shishen_gan(day_gan, stem)]] += weight

    return {
        '月令': {
            '月支': month_zhi, '本气': month_main,
            '本气十神': calc_shishen_gan(day_gan, month_main),
            '月令五行': GAN_WX[month_main], '日主五行': day_wx,
            '日主月令状态': month_state(day_wx, GAN_WX[month_main]),
            '季月': month_zhi in '辰戌丑未',
            '所属季节五行': SEASON_WX[month_zhi],
            '按季节五行状态': month_state(day_wx, SEASON_WX[month_zhi]),
        },
        '藏干明细': hidden,
        '日主十二长生': [{'柱': name, '地支': zhi, '状态': changsheng_stage(day_gan, zhi)}
                     for name, zhi in zip(PILLAR_NAMES, zhis)],
        '禄刃': {
            '禄': {'地支': lu, '位置': [PILLAR_NAMES[i] for i, z in enumerate(zhis) if z == lu]},
            '羊刃': None if ren is None else {
                '地支': ren, '位置': [PILLAR_NAMES[i] for i, z in enumerate(zhis) if z == ren]},
        },
        '天干通根': roots,
        '十神分组固定权重合计': {'日主自身': 1.0,
                     **{key: round(value, 2) for key, value in groups.items()}},
        '原局关系': natal_relations(gans, zhis),
        '大运与原局': [{'干支': row['干支'], **incoming_relations(row['干支'], gans, zhis)}
                   for row in dayun],
        '流年与原局': [{'year': row['year'], '干支': row['干支'],
                    **incoming_relations(row['干支'], gans, zhis)}
                   for row in liunian],
        '取法': METHOD,
    }
