#!/usr/bin/env python3
# v3.0
"""
合盘计算引擎（v3 · Agent J · 性格本位合盘）

哲学骨架：
  双方关系动力 = 性格桥接 × 玄学应期
  性格层为主语；八字 / 紫微 / 占星三层都是辅证。
  「印证度评估」回答"玄学三层是否一致印证性格层判断"。

输入：双方各 4 份 JSON（八字 / 紫微 / 占星 / 荣格）
输出：性格层主导 + 八字辅证 + 紫微剧场 + 占星节律 + 印证度 + 命运可塑路径

用法:
  python3 synastry_calc.py \\
    --person-a-bazi=a_bazi.json \\
    --person-a-ziwei=a_ziwei.json \\
    --person-a-astro=a_astro.json \\
    --person-a-jung=a_jung.json \\
    --person-b-bazi=b_bazi.json \\
    --person-b-ziwei=b_ziwei.json \\
    --person-b-astro=b_astro.json \\
    --person-b-jung=b_jung.json \\
    [--name-a NAME_A --name-b NAME_B]

任一 person-?-? 缺失时，对应辅证层会标注"缺数据"而不报错。
最低要求：双方 jung JSON 必须提供（性格层是主语，缺则无法主导分析）。
"""
import sys
import json
import argparse
from typing import Dict, Optional


# ============================================================
# 类型 → 标准功能栈（与 jung_calc.py 一致）
# ============================================================

STANDARD_STACKS = {
    'INTJ': ['Ni', 'Te', 'Fi', 'Se'], 'INTP': ['Ti', 'Ne', 'Si', 'Fe'],
    'ENTJ': ['Te', 'Ni', 'Se', 'Fi'], 'ENTP': ['Ne', 'Ti', 'Fe', 'Si'],
    'INFJ': ['Ni', 'Fe', 'Ti', 'Se'], 'INFP': ['Fi', 'Ne', 'Si', 'Te'],
    'ENFJ': ['Fe', 'Ni', 'Se', 'Ti'], 'ENFP': ['Ne', 'Fi', 'Te', 'Si'],
    'ISTJ': ['Si', 'Te', 'Fi', 'Ne'], 'ISFJ': ['Si', 'Fe', 'Ti', 'Ne'],
    'ESTJ': ['Te', 'Si', 'Ne', 'Fi'], 'ESFJ': ['Fe', 'Si', 'Ne', 'Ti'],
    'ISTP': ['Ti', 'Se', 'Ni', 'Fe'], 'ISFP': ['Fi', 'Se', 'Ni', 'Te'],
    'ESTP': ['Se', 'Ti', 'Fe', 'Ni'], 'ESFP': ['Se', 'Fi', 'Te', 'Ni'],
}

# ============================================================
# 16x16 吸引力 / 挑战度矩阵（来自 jung-relationship-dynamics.md §3.2）
# 格式：{(A, B): (吸引力 1-5, 挑战度 1-5)}
# ============================================================

ATTRACT_CHALLENGE = {}

_MATRIX_TABLE = """\
INTJ:3/3 4/3 4/4 5/4 4/3 4/4 4/3 5/3 3/3 3/3 3/4 4/4 2/4 3/4 2/4 3/4
INTP:4/3 3/3 4/4 4/3 4/3 4/3 5/3 4/3 3/3 3/2 3/4 3/3 3/3 3/3 3/4 3/3
ENTJ:4/4 4/4 3/4 4/4 4/3 5/4 4/3 4/3 4/3 3/3 3/3 3/3 3/3 3/4 3/3 3/3
ENTP:5/4 4/3 4/4 3/4 5/3 4/3 4/3 4/3 3/4 3/3 3/3 3/3 3/4 3/3 3/3 3/2
INFJ:4/3 4/3 4/3 5/3 3/3 4/3 4/3 5/3 3/3 3/4 3/4 4/4 3/3 4/3 3/3 4/4
INFP:4/4 4/3 5/4 4/3 4/3 3/3 4/3 4/3 3/4 3/3 2/5 3/4 3/3 3/3 3/3 3/3
ENFJ:4/3 5/3 4/3 4/3 4/3 4/3 3/3 4/3 3/3 3/4 3/3 4/3 3/2 4/3 3/2 4/3
ENFP:5/3 4/3 4/3 4/3 5/3 4/3 4/3 3/3 3/4 3/3 3/4 3/3 3/3 4/3 3/3 4/3
ISTJ:3/3 3/3 4/3 3/4 3/3 3/4 3/3 3/4 3/3 3/2 4/2 3/3 4/2 3/3 4/2 3/3
ISTP:3/3 3/2 3/3 3/3 3/4 3/3 3/4 3/3 3/2 3/3 3/3 4/3 3/3 4/3 3/3 4/3
ESTJ:3/4 3/4 3/3 3/3 3/4 2/5 3/3 3/4 4/2 3/3 3/3 3/3 4/2 3/4 4/2 3/3
ESTP:4/4 3/3 3/3 3/3 4/4 3/4 4/3 3/3 3/3 4/3 3/3 3/3 3/3 4/3 3/3 4/2
ISFJ:2/4 3/3 3/3 3/4 3/3 3/3 3/2 3/3 4/2 3/3 4/2 3/3 3/3 3/3 4/2 4/3
ISFP:3/4 3/3 3/4 3/3 4/3 3/3 4/3 4/3 3/3 4/3 3/4 4/3 3/3 3/3 3/3 4/3
ESFJ:2/4 3/4 3/3 3/3 3/3 3/3 3/2 3/3 4/2 3/3 4/2 3/3 4/2 3/3 3/3 4/2
ESFP:3/4 3/3 3/3 3/2 4/4 3/3 4/3 4/3 3/3 4/3 3/3 4/2 4/3 4/3 4/2 3/3
"""

_TYPES_ORDER = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP',
                'ISTJ', 'ISTP', 'ESTJ', 'ESTP', 'ISFJ', 'ISFP', 'ESFJ', 'ESFP']


def _parse_matrix():
    for line in _MATRIX_TABLE.strip().split('\n'):
        row_type, cells = line.split(':')
        row_type = row_type.strip()
        for col_type, cell in zip(_TYPES_ORDER, cells.split()):
            a, c = cell.split('/')
            ATTRACT_CHALLENGE[(row_type, col_type)] = (int(a), int(c))


_parse_matrix()


def stars(n: int) -> str:
    """1-5 → ★ 字符串"""
    n = max(1, min(5, n))
    return '★' * n + '☆' * (5 - n)


# ============================================================
# 桥接功能对识别（出自 jung-relationship-dynamics.md §2）
# ============================================================

# 8 桥接对：判断对 4 + 感知对 4
BRIDGE_PAIRS = [
    ({'Te', 'Fi'}, 'Te-Fi 桥接（系统↔价值）'),
    ({'Ti', 'Fe'}, 'Ti-Fe 桥接（逻辑↔和谐）'),
    ({'Te', 'Ti'}, 'Te-Ti 桥接（外部秩序↔内部逻辑）'),
    ({'Fe', 'Fi'}, 'Fe-Fi 桥接（外部和谐↔内部价值）'),
    ({'Se', 'Ni'}, 'Se-Ni 桥接（行动↔洞察）'),
    ({'Si', 'Ne'}, 'Si-Ne 桥接（传统↔可能）'),
    ({'Se', 'Si'}, 'Se-Si 桥接（当下↔经验）'),
    ({'Ne', 'Ni'}, 'Ne-Ni 桥接（发散↔收敛）'),
]


def detect_bridges(stack_a, stack_b):
    """识别 A、B 前 4 位之间共出现的桥接对。

    桥接成立条件：桥接对的两端均在两人 top4 中出现，且至少有一端在
    两人前 2 位（主导 / 辅助）——这才构成"跨人激活"。
    """
    top4_a = set(stack_a[:4])
    top4_b = set(stack_b[:4])
    top2_a = set(stack_a[:2])
    top2_b = set(stack_b[:2])
    bridges = []
    for pair_set, desc in BRIDGE_PAIRS:
        a, b = list(pair_set)
        # 双方 top4 必须共同涵盖这两端
        in_a = a in top4_a or a in top4_b
        in_b = b in top4_a or b in top4_b
        if not (in_a and in_b):
            continue
        # 至少一端落在某一方的前 2 位（主导 / 辅助 = 强激活）
        strong = ((a in top2_a) or (a in top2_b) or
                  (b in top2_a) or (b in top2_b))
        if strong:
            bridges.append(desc)
    return bridges


# ============================================================
# 八字辅证：日柱合化 + 五行互补 + 喜用神冲击
# ============================================================

# 天干五合化
TIANGAN_HE = {
    frozenset(['甲', '己']): '土 → 中正之合，性格化学反应：稳重感',
    frozenset(['乙', '庚']): '金 → 仁义之合，性格化学反应：决断与温润互补',
    frozenset(['丙', '辛']): '水 → 威制之合，性格化学反应：刚柔互转，张力大',
    frozenset(['丁', '壬']): '木 → 淫慝之合，性格化学反应：情欲与生发并起',
    frozenset(['戊', '癸']): '火 → 无情之合，性格化学反应：理性结合，情感冷',
}

# 五行生克
WX_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
WX_KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


def _bazi_get_day_gan(bazi: dict) -> Optional[str]:
    """从 bazi JSON 提取日干"""
    if not bazi:
        return None
    # 优先从「四柱.日柱」结构
    pillars = bazi.get('四柱') or bazi.get('八字') or []
    if isinstance(pillars, list):
        for p in pillars:
            if isinstance(p, dict) and p.get('柱') == '日柱':
                return p.get('天干')
    # 其次从直接字段
    return bazi.get('日干') or bazi.get('日主', {}).get('天干') if isinstance(bazi.get('日主'), dict) else bazi.get('日主')


def _bazi_get_yongshen(bazi: dict) -> Optional[str]:
    """从 bazi JSON 提取喜用神 / 调候用神"""
    if not bazi:
        return None
    return bazi.get('调候用神') or bazi.get('喜用神') or bazi.get('用神')


def _bazi_get_wx_strong_weak(bazi: dict):
    """提取五行偏强 / 偏弱"""
    if not bazi:
        return None, None
    return bazi.get('五行偏强'), bazi.get('五行薄弱')


def analyze_bazi_layer(a_bazi: Optional[dict], b_bazi: Optional[dict],
                       name_a: str, name_b: str) -> dict:
    if not a_bazi or not b_bazi:
        return {'状态': f'缺数据：{"A" if not a_bazi else "B"} 八字 JSON 未提供'}

    out = {}

    # 日柱合化
    a_gan = _bazi_get_day_gan(a_bazi)
    b_gan = _bazi_get_day_gan(b_bazi)
    if a_gan and b_gan:
        key = frozenset([a_gan, b_gan])
        if key in TIANGAN_HE:
            out['日柱合化'] = f'{a_gan}+{b_gan} → 合化{TIANGAN_HE[key]}'
        else:
            # 同干 / 一般关系
            if a_gan == b_gan:
                out['日柱合化'] = f'{a_gan}+{b_gan} → 比肩同气，性格相似但易竞争'
            else:
                # 检测克
                a_wx = _gan_wx(a_gan)
                b_wx = _gan_wx(b_gan)
                if a_wx and b_wx:
                    if WX_KE.get(a_wx) == b_wx:
                        out['日柱合化'] = f'{a_gan}({a_wx})克{b_gan}({b_wx}) → A 主动施压 B'
                    elif WX_KE.get(b_wx) == a_wx:
                        out['日柱合化'] = f'{b_gan}({b_wx})克{a_gan}({a_wx}) → B 主动施压 A'
                    elif WX_SHENG.get(a_wx) == b_wx:
                        out['日柱合化'] = f'{a_gan}({a_wx})生{b_gan}({b_wx}) → A 滋养 B'
                    elif WX_SHENG.get(b_wx) == a_wx:
                        out['日柱合化'] = f'{b_gan}({b_wx})生{a_gan}({a_wx}) → B 滋养 A'
                    else:
                        out['日柱合化'] = f'{a_gan}+{b_gan} → 五行无显著生克'

    # 五行互补（A 缺 → B 补）
    a_strong, a_weak = _bazi_get_wx_strong_weak(a_bazi)
    b_strong, b_weak = _bazi_get_wx_strong_weak(b_bazi)
    互补 = []
    # 简单模式匹配："X 偏弱" 字符串里找五行
    for label, val in [('A弱→B强', (a_weak, b_strong)), ('B弱→A强', (b_weak, a_strong))]:
        weak, strong = val
        if isinstance(weak, str) and isinstance(strong, str):
            for wx in ('木', '火', '土', '金', '水'):
                if wx in weak and wx in strong:
                    互补.append(f'{label}：{wx}')
                    break
    if 互补:
        out['五行互补'] = '；'.join(互补)

    # 喜用神冲击
    a_ys = _bazi_get_yongshen(a_bazi)
    b_ys = _bazi_get_yongshen(b_bazi)
    yongshen_note = []
    if a_ys:
        yongshen_note.append(f'{name_a}用神：{a_ys}')
    if b_ys:
        yongshen_note.append(f'{name_b}用神：{b_ys}')
    if yongshen_note:
        out['用神记录'] = ' / '.join(yongshen_note)

    # 夫妻星呼应（粗略提示，需 bazi JSON 提供「夫妻星」字段才能精确）
    out['_提示'] = '夫妻星呼应需在 bazi JSON 包含「夫妻星」字段时给出；目前仅做日干层匹配'

    return out


def _gan_wx(gan: str) -> Optional[str]:
    table = {'甲': '木', '乙': '木', '丙': '火', '丁': '火',
             '戊': '土', '己': '土', '庚': '金', '辛': '金',
             '壬': '水', '癸': '水'}
    return table.get(gan)


# ============================================================
# 紫微辅证：双方夫妻宫互看 + 福德宫相照
# ============================================================

def _ziwei_get_palace(ziwei: dict, palace_name: str) -> Optional[dict]:
    """从 ziwei JSON 中取指定宫位（「夫妻」「福德」「命宫」等）"""
    if not ziwei:
        return None
    # ziwei v3 可能含「闰月警告.中分法盘」嵌套；统一取顶层 / 中分法
    base = ziwei
    if '闰月警告' in ziwei and '中分法盘' in ziwei['闰月警告']:
        base = ziwei['闰月警告']['中分法盘']
    palaces = base.get('十二宫', [])
    for p in palaces:
        if isinstance(p, dict) and p.get('宫位') == palace_name:
            return p
    return None


def _palace_main_stars(palace: Optional[dict]) -> list:
    if not palace:
        return []
    return [s.get('名称') for s in palace.get('主星', []) if isinstance(s, dict)]


def _palace_mutagen(palace: Optional[dict]) -> list:
    """提取本宫四化星"""
    if not palace:
        return []
    out = []
    for s in palace.get('主星', []):
        if isinstance(s, dict) and s.get('四化'):
            out.append(f'{s.get("名称")}化{s.get("四化")}')
    return out


def analyze_ziwei_layer(a_ziwei: Optional[dict], b_ziwei: Optional[dict],
                        name_a: str, name_b: str) -> dict:
    if not a_ziwei or not b_ziwei:
        return {'状态': f'缺数据：{"A" if not a_ziwei else "B"} 紫微 JSON 未提供'}

    out = {}

    # 双方夫妻宫互看
    a_spouse = _palace_main_stars(_ziwei_get_palace(a_ziwei, '夫妻'))
    b_spouse = _palace_main_stars(_ziwei_get_palace(b_ziwei, '夫妻'))
    a_ming = _palace_main_stars(_ziwei_get_palace(a_ziwei, '命宫'))
    b_ming = _palace_main_stars(_ziwei_get_palace(b_ziwei, '命宫'))

    out['夫妻宫互看'] = {
        f'{name_a}夫妻宫主星': a_spouse or ['空宫，借对宫论'],
        f'{name_b}夫妻宫主星': b_spouse or ['空宫，借对宫论'],
        f'{name_a}命宫 → {name_b}夫妻宫互射': _shexpect(a_ming, b_spouse, name_a, name_b),
        f'{name_b}命宫 → {name_a}夫妻宫互射': _shexpect(b_ming, a_spouse, name_b, name_a),
    }

    # 福德宫相照
    a_fortune = _palace_main_stars(_ziwei_get_palace(a_ziwei, '福德'))
    b_fortune = _palace_main_stars(_ziwei_get_palace(b_ziwei, '福德'))
    fortune_score = _fortune_harmony(a_fortune, b_fortune)
    out['福德宫相照'] = {
        f'{name_a}福德宫': a_fortune or ['空宫'],
        f'{name_b}福德宫': b_fortune or ['空宫'],
        '和谐度': stars(fortune_score),
    }

    # 化忌 / 化禄入夫妻宫
    a_spouse_hua = _palace_mutagen(_ziwei_get_palace(a_ziwei, '夫妻'))
    b_spouse_hua = _palace_mutagen(_ziwei_get_palace(b_ziwei, '夫妻'))
    if a_spouse_hua or b_spouse_hua:
        out['夫妻宫四化'] = {
            f'{name_a}夫妻宫四化': a_spouse_hua or ['无'],
            f'{name_b}夫妻宫四化': b_spouse_hua or ['无'],
            '说明': '化禄主和合，化权主主导，化科主温和，化忌主纠葛与执着',
        }

    return out


def _shexpect(actor_ming, target_spouse, actor_name, target_name) -> str:
    """A 命宫主星 → B 夫妻宫的解读（粗略）"""
    if not actor_ming:
        return f'{actor_name} 命宫无主星，无强烈"角色感"投射'
    if not target_spouse:
        return f'{target_name} 夫妻宫空宫，{actor_name} 易成"剧本作者"'
    a_first = actor_ming[0]
    return f'{actor_name} 命宫{a_first} → {target_name} 期待的"伴侣类型"是 {",".join(target_spouse)}'


# 福德宫主星和谐近似评级
_FORTUNE_HARMONY = {
    # 同星 / 互补星 → 高和谐
    ('紫微', '紫微'): 4, ('天府', '天府'): 4,
    ('紫微', '天府'): 5, ('天府', '紫微'): 5,
    ('紫微', '七杀'): 3, ('七杀', '紫微'): 3,
    ('天同', '太阴'): 5, ('太阴', '天同'): 5,
    ('太阳', '太阴'): 5, ('太阴', '太阳'): 5,
    ('七杀', '破军'): 4, ('破军', '七杀'): 4,
    ('贪狼', '廉贞'): 3, ('廉贞', '贪狼'): 3,
    ('天梁', '天机'): 4, ('天机', '天梁'): 4,
}


def _fortune_harmony(a_stars, b_stars) -> int:
    if not a_stars or not b_stars:
        return 3
    pair = (a_stars[0], b_stars[0])
    if a_stars[0] == b_stars[0]:
        return 4  # 同星：相互理解但缺新鲜
    return _FORTUNE_HARMONY.get(pair, 3)


# ============================================================
# 占星辅证：日月相位 + 金星相位 + 土星相位
# ============================================================

# 简化「黄经差 → 相位」（本脚本不做精确度数计算，只读 JSON 已有相位字段）
_ASPECT_MEANING = {
    '合相': '紧密融合 → 强吸引',
    '冲相': '对位张力 → 高动力',
    '三合': '柔和流动 → 长期和谐',
    '六合': '协助配合 → 中等支持',
    '四分': '紧张摩擦 → 需主动调和',
}


def _astro_planet_sign(astro: dict, planet: str) -> Optional[str]:
    if not astro:
        return None
    p = (astro.get('十大行星+北交+凯龙', {}) or {}).get(planet)
    if isinstance(p, dict):
        return p.get('星座')
    # 退化路径
    raw = astro.get(planet)
    if isinstance(raw, str):
        # "天秤座 12.3°" → "天秤"
        for sign in ['白羊', '金牛', '双子', '巨蟹', '狮子', '处女',
                     '天秤', '天蝎', '射手', '摩羯', '水瓶', '双鱼']:
            if sign in raw:
                return sign
    return None


def _astro_planet_lon(astro: dict, planet: str) -> Optional[float]:
    if not astro:
        return None
    p = (astro.get('十大行星+北交+凯龙', {}) or {}).get(planet)
    if isinstance(p, dict):
        return p.get('黄经')
    return None


def _calc_aspect(lon_a, lon_b, orb=8.0) -> Optional[str]:
    """根据两颗星的黄经差判定相位（容许度 8°）"""
    if lon_a is None or lon_b is None:
        return None
    diff = abs(lon_a - lon_b) % 360
    diff = min(diff, 360 - diff)
    for angle, name in [(0, '合相'), (60, '六合'), (90, '四分'),
                        (120, '三合'), (180, '冲相')]:
        if abs(diff - angle) <= orb:
            return name
    return None


def analyze_astro_layer(a_astro: Optional[dict], b_astro: Optional[dict],
                        name_a: str, name_b: str) -> dict:
    if not a_astro or not b_astro:
        return {'状态': f'缺数据：{"A" if not a_astro else "B"} 占星 JSON 未提供'}

    out = {}

    # 关键合盘相位
    pairs_to_check = [
        (('太阳', '月亮'), '日月相位（主导功能↔阿尼玛/阿尼姆斯）'),
        (('月亮', '太阳'), '月日相位（反向）'),
        (('金星', '月亮'), '金星-月亮（情感共鸣）'),
        (('月亮', '金星'), '月亮-金星（反向）'),
        (('金星', '金星'), '双方金星（爱的方式匹配）'),
        (('火星', '金星'), '火星-金星（性吸引轴）'),
        (('土星', '太阳'), '土星-太阳（长期承诺压力）'),
        (('土星', '金星'), '土星-金星（爱的限制）'),
        (('冥王星', '金星'), '冥王-金星（Demon 投射轴）'),
    ]

    aspects_found = []
    for (planet_a, planet_b), label in pairs_to_check:
        lon_a = _astro_planet_lon(a_astro, planet_a)
        lon_b = _astro_planet_lon(b_astro, planet_b)
        asp = _calc_aspect(lon_a, lon_b)
        if asp:
            meaning = _ASPECT_MEANING.get(asp, asp)
            aspects_found.append(
                f'{name_a}{planet_a} {asp} {name_b}{planet_b} → {label}：{meaning}'
            )

    out['关键合盘相位'] = aspects_found if aspects_found else ['未在容许度 8° 内检出主要相位']

    # 日月星座匹配（粗略元素匹配）
    a_sun = _astro_planet_sign(a_astro, '太阳')
    b_moon = _astro_planet_sign(b_astro, '月亮')
    a_moon = _astro_planet_sign(a_astro, '月亮')
    b_sun = _astro_planet_sign(b_astro, '太阳')

    if a_sun and b_moon:
        out['星座对位'] = {
            f'{name_a}太阳/{name_b}月亮': f'{a_sun} / {b_moon} → {_element_pair(a_sun, b_moon)}',
            f'{name_b}太阳/{name_a}月亮': f'{b_sun} / {a_moon} → {_element_pair(b_sun, a_moon)}',
        }

    return out


_SIGN_ELEMENT = {
    '白羊': '火', '狮子': '火', '射手': '火',
    '金牛': '土', '处女': '土', '摩羯': '土',
    '双子': '风', '天秤': '风', '水瓶': '风',
    '巨蟹': '水', '天蝎': '水', '双鱼': '水',
}


def _element_pair(s1, s2) -> str:
    e1 = _SIGN_ELEMENT.get(s1, '?')
    e2 = _SIGN_ELEMENT.get(s2, '?')
    if e1 == '?' or e2 == '?':
        return '元素未知'
    if e1 == e2:
        return f'同{e1}元素 · 自然共鸣'
    pairs = {
        ('火', '风'): '火风互助 · 行动 + 思考',
        ('风', '火'): '火风互助 · 行动 + 思考',
        ('土', '水'): '土水互滋 · 稳定 + 滋养',
        ('水', '土'): '土水互滋 · 稳定 + 滋养',
        ('火', '土'): '火土需磨合 · 冲动 vs 稳定',
        ('土', '火'): '火土需磨合 · 冲动 vs 稳定',
        ('火', '水'): '火水高张力 · 蒸腾或熄灭',
        ('水', '火'): '火水高张力 · 蒸腾或熄灭',
        ('土', '风'): '土风需磨合 · 务实 vs 概念',
        ('风', '土'): '土风需磨合 · 务实 vs 概念',
        ('风', '水'): '风水需磨合 · 思考 vs 感受',
        ('水', '风'): '风水需磨合 · 思考 vs 感受',
    }
    return pairs.get((e1, e2), f'{e1}+{e2}')


# ============================================================
# 印证度评估
# ============================================================

def assess_consistency(personality_attract, personality_challenge,
                       bazi_layer, ziwei_layer, astro_layer) -> dict:
    """玄学三层是否一致印证性格层判断"""
    consistent_count = 0
    notes = []

    # 八字：日柱合化为正面（合 / 生）→ 印证；克 / 比肩 → 张力
    bazi_text = bazi_layer.get('日柱合化', '') if isinstance(bazi_layer, dict) else ''
    if '合化' in bazi_text or '滋养' in bazi_text:
        if personality_attract >= 4:
            consistent_count += 1
            notes.append('八字 ✓ 印证性格高吸引')
        else:
            notes.append('八字 △ 命理偏吉但性格未必合')
    elif '克' in bazi_text or '比肩' in bazi_text:
        if personality_challenge >= 4:
            consistent_count += 1
            notes.append('八字 ✓ 印证性格高挑战')
        else:
            notes.append('八字 △ 命理张力但性格未必冲')
    else:
        notes.append('八字 — 中性')

    # 紫微：福德宫和谐度高 → 印证吸引；化忌入夫妻 → 印证挑战
    if isinstance(ziwei_layer, dict):
        fortune = ziwei_layer.get('福德宫相照', {})
        if isinstance(fortune, dict):
            harm_str = fortune.get('和谐度', '')
            harm_n = harm_str.count('★')
            if harm_n >= 4 and personality_attract >= 4:
                consistent_count += 1
                notes.append('紫微 ✓ 福德宫高度和谐印证性格吸引')
            elif harm_n <= 2 and personality_challenge >= 4:
                consistent_count += 1
                notes.append('紫微 ✓ 福德宫不和谐印证性格挑战')
            else:
                notes.append(f'紫微 △ 福德宫{harm_str}')
        spouse_hua = ziwei_layer.get('夫妻宫四化', {})
        if isinstance(spouse_hua, dict):
            for v in spouse_hua.values():
                if isinstance(v, list) and any('忌' in str(x) for x in v):
                    notes.append('紫微 ⚠ 夫妻宫化忌 → 投射裂缝高发期')
                    break

    # 占星：合相 / 三合 → 印证吸引；冲相 / 四分 → 印证挑战
    if isinstance(astro_layer, dict):
        aspects = astro_layer.get('关键合盘相位', [])
        if isinstance(aspects, list):
            harmonious = sum(1 for a in aspects if '合相' in a or '三合' in a or '六合' in a)
            tense = sum(1 for a in aspects if '冲相' in a or '四分' in a)
            if harmonious > tense and personality_attract >= 4:
                consistent_count += 1
                notes.append(f'占星 ✓ 和谐相位 {harmonious} 个印证性格吸引')
            elif tense > harmonious and personality_challenge >= 4:
                consistent_count += 1
                notes.append(f'占星 ✓ 张力相位 {tense} 个印证性格挑战')
            else:
                notes.append(f'占星 △ 和谐 {harmonious}/张力 {tense}')

    if consistent_count >= 3:
        rating = stars(5)
        summary = '三层（八字/紫微/占星）一致印证性格层判断'
    elif consistent_count == 2:
        rating = stars(4)
        summary = '双层印证性格层，单层中性 / 张力'
    elif consistent_count == 1:
        rating = stars(3)
        summary = '单层印证；其余层中性或偏离'
    else:
        rating = stars(2)
        summary = '玄学三层未明显印证性格层 → 性格层独立判断'

    return {
        '评级': rating,
        '一句话总评': summary,
        '层级注解': notes,
    }


# ============================================================
# 命运可塑路径生成
# ============================================================

def generate_paths(type_a, type_b, top4_a, top4_b, bridges, name_a, name_b) -> list:
    """根据双方类型 + 桥接对生成 3-5 条具体可操作建议"""
    paths = []
    inferior_a = top4_a[3] if len(top4_a) >= 4 else '?'
    inferior_b = top4_b[3] if len(top4_b) >= 4 else '?'
    third_a = top4_a[2] if len(top4_a) >= 3 else '?'
    third_b = top4_b[2] if len(top4_b) >= 3 else '?'

    # 路径 1：劣势功能开发
    paths.append(
        f'{name_a} 主动训练 {inferior_a}（劣势位），停止把成长任务丢给 {name_b}；'
        f'{name_b} 主动训练 {inferior_b}，停止依赖 {name_a} 补全'
    )

    # 路径 2：桥接对的健康激活
    if bridges:
        paths.append(
            f'珍视并保护「{bridges[0]}」这条桥接通道——这是双方最核心的成长机会，'
            f'不要在它紧张时直接撤离，而要留下来共同练习'
        )
    else:
        paths.append(
            f'{name_a}（{type_a}）与 {name_b}（{type_b}）功能栈缺乏经典桥接 → '
            f'刻意创造共同活动，让双方第三功能（{third_a}/{third_b}）得到练习'
        )

    # 路径 3：Child 位的健康满足（避免在亲密关系中失控触发）
    paths.append(
        f'双方各自识别自己的 Child 位（{third_a} / {third_b}）何时上线 → '
        f'主动在关系中安排"撒娇时间"，而非等到压力爆发时无意识退行'
    )

    # 路径 4：投射意识化日记
    paths.append(
        f'设立"投射日记"——每次"被对方激怒"或"对对方极度迷恋"时，'
        f'写下"我刚才在对方身上看到的是我自己的什么"。3-6 个月可显著降低投射强度'
    )

    # 路径 5：玄学应期的主动利用（占位 · 分析师可在写命书时填具体年份）
    paths.append(
        f'当玄学标注关系应期窗口（大限/大运/行运冥王过 7 宫等）时，主动启动整合任务，'
        f'而非被动等待事件冲击；具体应期由分析师对照八字/紫微/占星层标注'
    )

    return paths


# ============================================================
# 主流程
# ============================================================

def _safe_load_json(path: Optional[str]) -> Optional[dict]:
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'WARN: 无法加载 {path}: {e}', file=sys.stderr)
        return None


def _extract_jung_info(jung: Optional[dict]) -> tuple:
    """从 jung_calc.py 输出中提取 (类型代号, 前 4 位功能栈)"""
    if not jung:
        return None, []
    type_code = jung.get('类型推断') or jung.get('推断假说', {}).get('首选类型')
    stack = jung.get('功能栈', [])
    top4 = []
    for item in stack:
        if isinstance(item, dict) and item.get('位') and item['位'] <= 4:
            top4.append(item.get('功能'))
    if not top4 and type_code in STANDARD_STACKS:
        top4 = STANDARD_STACKS[type_code]
    return type_code, top4


def calc_synastry(a_bazi, a_ziwei, a_astro, a_jung,
                  b_bazi, b_ziwei, b_astro, b_jung,
                  name_a='A', name_b='B') -> dict:
    type_a, top4_a = _extract_jung_info(a_jung)
    type_b, top4_b = _extract_jung_info(b_jung)

    if not type_a or not type_b:
        raise ValueError('双方 jung JSON 必须包含类型推断或功能栈，否则无法主导分析')

    # ============ 性格层（主导）============
    bridges = detect_bridges(top4_a, top4_b)
    attract, challenge = ATTRACT_CHALLENGE.get((type_a, type_b), (3, 3))

    # 动力学摘要（从矩阵 + 桥接组合）
    summary_parts = []
    if attract >= 4:
        summary_parts.append('高吸引')
    if challenge >= 4:
        summary_parts.append('高挑战')
    if not summary_parts:
        summary_parts.append('平稳关系')
    if bridges:
        summary_parts.append(f'激活{len(bridges)}条桥接通道')

    personality_layer = {
        '类型配对': {name_a: type_a, name_b: type_b},
        '功能栈': {
            name_a: top4_a,
            name_b: top4_b,
        },
        '桥接功能对': bridges if bridges else ['无经典桥接 → 同类相吸 / 互不交集'],
        '吸引力': stars(attract),
        '挑战度': stars(challenge),
        '动力学摘要': ' · '.join(summary_parts) +
                       f'。详见 jung-relationship-dynamics.md §2 与 §3 矩阵',
    }

    # ============ 八字层（辅证）============
    bazi_layer = analyze_bazi_layer(a_bazi, b_bazi, name_a, name_b)

    # ============ 紫微层（剧场）============
    ziwei_layer = analyze_ziwei_layer(a_ziwei, b_ziwei, name_a, name_b)

    # ============ 占星层（节律）============
    astro_layer = analyze_astro_layer(a_astro, b_astro, name_a, name_b)

    # ============ 印证度 ============
    consistency = assess_consistency(attract, challenge, bazi_layer, ziwei_layer, astro_layer)

    # ============ 可塑路径 ============
    paths = generate_paths(type_a, type_b, top4_a, top4_b, bridges, name_a, name_b)

    return {
        '合盘类型': 'synastry',
        '哲学声明': '性格决定关系动力，玄学辅证应期。本输出以性格层为主语，玄学三层为辅证。',
        '性格层（主导）': personality_layer,
        '八字层（辅证）': bazi_layer,
        '紫微层（剧场）': ziwei_layer,
        '占星层（节律）': astro_layer,
        '印证度评估': consistency,
        '命运可塑路径': paths,
    }


def main():
    parser = argparse.ArgumentParser(
        description='合盘计算引擎（v3）—— 性格本位合盘',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--person-a-bazi', dest='a_bazi')
    parser.add_argument('--person-a-ziwei', dest='a_ziwei')
    parser.add_argument('--person-a-astro', dest='a_astro')
    parser.add_argument('--person-a-jung', dest='a_jung', required=True)
    parser.add_argument('--person-b-bazi', dest='b_bazi')
    parser.add_argument('--person-b-ziwei', dest='b_ziwei')
    parser.add_argument('--person-b-astro', dest='b_astro')
    parser.add_argument('--person-b-jung', dest='b_jung', required=True)
    parser.add_argument('--name-a', default='A')
    parser.add_argument('--name-b', default='B')

    args = parser.parse_args()

    result = calc_synastry(
        a_bazi=_safe_load_json(args.a_bazi),
        a_ziwei=_safe_load_json(args.a_ziwei),
        a_astro=_safe_load_json(args.a_astro),
        a_jung=_safe_load_json(args.a_jung),
        b_bazi=_safe_load_json(args.b_bazi),
        b_ziwei=_safe_load_json(args.b_ziwei),
        b_astro=_safe_load_json(args.b_astro),
        b_jung=_safe_load_json(args.b_jung),
        name_a=args.name_a, name_b=args.name_b,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
