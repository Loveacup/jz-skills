#!/usr/bin/env python3
# v3.1.1
from __future__ import annotations  # PEP 604 类型在 Python 3.9 兼容
"""
西方占星完整排盘
基于 pyswisseph（瑞士星历表的 Python 绑定）。

用法: python3 astro_calc.py <yyyy-mm-dd> <hh:mm> <lat> <lon> [tz] [选项]
  tz 可以是浮点小时数（如 8 / -4 / 5.5）或 IANA 名称（如 'America/New_York'）。
  IANA 名称模式下会自动按出生日期计算实际 UTC 偏移（含 DST）。

可选参数（任意位置，--key=value 或 --flag）:
  --mean-node           北交点用 MEAN_NODE（默认 TRUE_NODE）
  --orbs=KV[,KV...]     覆盖相位容许度，格式: 合相=8,对冲=8,三合=7,四分=7,六合=5
  --svg                 生成 kerykeion 圆盘 SVG
  --svg-name=NAME       SVG 中显示的命主名（默认 'Subject'）
  --svg-tz=TZ           生成 SVG 时强制指定的 IANA 时区（缺省由 tz 推导）
  --svg-out=DIR         SVG 输出目录（默认 ./cache/svg）

示例:
  python3 astro_calc.py 1993-09-30 17:30 30.27 120.16 8
  python3 astro_calc.py 1985-07-15 14:00 40.71 -74.01 America/New_York --svg

依赖: pip install pyswisseph kerykeion --break-system-packages

v3.1 变更（本次）:
  - 高纬度（|lat|>60°）自动 fallback Whole Sign 宫位制
  - 北交点默认 TRUE_NODE，可 --mean-node 切回
  - 新增配点：Lilith（黑月）、Part of Fortune（福点）、Vertex
  - 相位容许度可通过 --orbs 覆盖
  - 输出 JSON 新增「宫位制」「北交类型」「扩展配点」「性格映射提示」
  - 接入 kerykeion 出 SVG 圆盘（--svg）
"""
import os
import sys
import json
import re
import hashlib

import swisseph as swe

# 让 _common 可被 import（同目录脚本）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from _common import format_coord, format_tz  # noqa: E402
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # noqa: E402
from datetime import datetime as _datetime  # noqa: E402


def _utc_offset_at(iana_tz: str, y: int, m: int, d: int, h: int, mi: int) -> float:
    """返回指定时刻该 IANA 时区的 UTC 偏移（小时，含 DST）"""
    tz = ZoneInfo(iana_tz)
    dt = _datetime(y, m, d, h, mi, tzinfo=tz)
    return dt.utcoffset().total_seconds() / 3600.0


def _is_dst_at(iana_tz: str, y: int, m: int, d: int, h: int, mi: int) -> bool:
    """该时刻是否处于 DST"""
    try:
        tz = ZoneInfo(iana_tz)
    except ZoneInfoNotFoundError:
        return False
    dt = _datetime(y, m, d, h, mi, tzinfo=tz)
    dst = dt.dst()
    return dst is not None and dst.total_seconds() > 0


def _iana_from_offset(utc_offset: float) -> str:
    """从 UTC 偏移推一个标称 IANA 名（仅 SVG 用，凑得上即可）"""
    # 优先常见时区
    table = {
        8.0: 'Asia/Shanghai', 9.0: 'Asia/Tokyo', 5.5: 'Asia/Kolkata',
        0.0: 'Europe/London', 1.0: 'Europe/Paris', 2.0: 'Europe/Athens',
        3.0: 'Europe/Moscow', -5.0: 'America/New_York', -6.0: 'America/Chicago',
        -7.0: 'America/Denver', -8.0: 'America/Los_Angeles',
        10.0: 'Australia/Sydney', 12.0: 'Pacific/Auckland',
    }
    if utc_offset in table:
        return table[utc_offset]
    # 兜底：Etc/GMT 系列（注意符号反向）
    sign = '-' if utc_offset >= 0 else '+'
    return f'Etc/GMT{sign}{abs(int(utc_offset))}'


# 行星编号（pyswisseph 标准）—— 北交点在 calc_chart 内部按 use_true_node 选择
PLANETS_BASE = [
    ('太阳', swe.SUN), ('月亮', swe.MOON), ('水星', swe.MERCURY),
    ('金星', swe.VENUS), ('火星', swe.MARS), ('木星', swe.JUPITER),
    ('土星', swe.SATURN), ('天王星', swe.URANUS), ('海王星', swe.NEPTUNE),
    ('冥王星', swe.PLUTO),
    ('凯龙星', swe.CHIRON),
]

SIGNS = ['白羊', '金牛', '双子', '巨蟹', '狮子', '处女',
         '天秤', '天蝎', '射手', '摩羯', '水瓶', '双鱼']

SIGN_RULERS = {
    '白羊': '火星', '金牛': '金星', '双子': '水星', '巨蟹': '月亮',
    '狮子': '太阳', '处女': '水星', '天秤': '金星', '天蝎': '冥王星',
    '射手': '木星', '摩羯': '土星', '水瓶': '天王星', '双鱼': '海王星',
}

# 12 宫含义（占星十二宫，与紫微不同）
HOUSE_MEANINGS = {
    1: '命宫·自我形象', 2: '财帛·价值观', 3: '兄弟·学习沟通',
    4: '田宅·家庭根基', 5: '子女·创造与爱', 6: '奴仆·健康与日常',
    7: '夫妻·一对一关系', 8: '疾厄·共享资源与转化', 9: '迁移·哲学远方',
    10: '官禄·事业与社会形象', 11: '福德·朋友与理想', 12: '相貌·潜意识业力',
}

# 主要相位（角度+默认容差）— 可由 CLI --orbs 覆盖
DEFAULT_ORBS = {
    '合相': 8.0, '对冲': 8.0, '三合': 7.0, '四分': 7.0, '六合': 5.0,
}
ASPECT_DEGREES = {
    '合相': 0.0, '对冲': 180.0, '三合': 120.0, '四分': 90.0, '六合': 60.0,
}


# ---------------------------------------------------------------------------
# 性格映射提示（v3 哲学骨架：玄学辅证性格）
# ---------------------------------------------------------------------------

# 太阳元素 → 主导功能候选（粗粒度，仅作 jung_calc 的参考线索）
_SUN_ELEMENT_FN = {
    '火': 'Ne/Se（外向直觉/感官）倾向',
    '土': 'Si/Te（内向感官/外向思考）倾向',
    '风': 'Ti/Ne（内向思考/外向直觉）倾向',
    '水': 'Ni/Fi（内向直觉/内向情感）倾向',
}
_SIGN_ELEMENT = {
    '白羊': '火', '狮子': '火', '射手': '火',
    '金牛': '土', '处女': '土', '摩羯': '土',
    '双子': '风', '天秤': '风', '水瓶': '风',
    '巨蟹': '水', '天蝎': '水', '双鱼': '水',
}

# 月亮 → 阿尼玛/阿尼姆斯发展阶段（荣格关系动力学的近似映射）
_MOON_ANIMA_STAGE = {
    '白羊': 'Eve（原始冲动·活在身体）',
    '金牛': 'Eve（感官安全·扎根肉身）',
    '双子': 'Helen（智识联结·兼容多面）',
    '巨蟹': 'Eve（母性原型·情感容器）',
    '狮子': 'Helen（被仰慕的爱人）',
    '处女': 'Mary（侍奉与净化·圣母）',
    '天秤': 'Helen（关系审美·镜像之爱）',
    '天蝎': 'Sophia（深渊之爱·穿越死亡）',
    '射手': 'Sophia（哲思之爱·真理探索）',
    '摩羯': 'Mary（克制守护·责任之爱）',
    '水瓶': 'Sophia（理想化之爱·去人格）',
    '双鱼': 'Sophia（神秘合一·边界消融）',
}

# 金星 → Fi/Fe 表达（情感功能在关系中的取向）
_VENUS_F_EXPRESSION = {
    '白羊': 'Fe（直接热烈，需要回应）',
    '金牛': 'Fi（感官私享，价值内定）',
    '双子': 'Fe（多元社交，灵活试探）',
    '巨蟹': 'Fi（深度依附，情绪私密）',
    '狮子': 'Fe（公开表达，需要见证）',
    '处女': 'Fi（私下完美主义，挑剔细节）',
    '天秤': 'Fe（关系审美，平衡他人）',
    '天蝎': 'Fi（极端忠诚，全有或全无）',
    '射手': 'Fe（外放豪爽，开放界限）',
    '摩羯': 'Fi（克制深藏，长期承诺）',
    '水瓶': 'Fe（去人格化博爱，群体导向）',
    '双鱼': 'Fi（无界共情，自我消融）',
}

# 土星 → 劣势功能压力点（哪个功能最容易因压力而失衡）
_SATURN_INFERIOR_PRESSURE = {
    '白羊': 'Si（不善慢工·完成感焦虑）',
    '金牛': 'Ne（拒绝改变·机会成本恐惧）',
    '双子': 'Ni（信息过载·难以收敛洞见）',
    '巨蟹': 'Te（情感主导·难以果决执行）',
    '狮子': 'Si（戏剧性夸大·稳定性弱）',
    '处女': 'Si（细节完美主义，自我消耗）',
    '天秤': 'Ti（怕得罪人·决断瘫痪）',
    '天蝎': 'Ne（控制欲与突变恐惧并存）',
    '射手': 'Ni（兴趣发散·难收口）',
    '摩羯': 'Fi（情感压抑·过度成就驱动）',
    '水瓶': 'Fe（人际温度不足·疏离）',
    '双鱼': 'Te（执行力涣散·边界感弱）',
}

# 冥王 → Demon 位投射（Beebe 第八位的破坏力色彩）
_PLUTO_DEMON_FLAVOR = {
    '白羊': '冲动性破坏（怒火失控）',
    '金牛': '占有性破坏（迷恋与窒息）',
    '双子': '言语性破坏（毒舌与造谣）',
    '巨蟹': '情绪性破坏（情感勒索）',
    '狮子': '自恋性破坏（宏大幻象崩塌）',
    '处女': '完美主义性破坏（自我攻击）',
    '天秤': '关系性破坏（拉拢与挑拨）',
    '天蝎': '权力性破坏（深渊报复）',
    '射手': '哲学性破坏（信念盲冲）',
    '摩羯': '结构性破坏（绝对秩序崩坏）',
    '水瓶': '颠覆性破坏（去人化革命）',
    '双鱼': '溶解性破坏（边界消融与沉沦）',
}


def _build_personality_hints(positions: dict, asc_sign: str) -> dict:
    """根据本命主要行星位置，输出给 jung_calc 的「性格签名候选」线索"""
    hints = {}

    sun_sign = positions.get('太阳', {}).get('星座')
    sun_house = positions.get('太阳', {}).get('落宫')
    if sun_sign:
        elem = _SIGN_ELEMENT.get(sun_sign, '')
        fn_hint = _SUN_ELEMENT_FN.get(elem, '')
        h_str = f'+{sun_house}宫' if sun_house else ''
        hints['太阳→主导功能候选'] = f'{sun_sign}{h_str} → {fn_hint}'

    moon_sign = positions.get('月亮', {}).get('星座')
    if moon_sign:
        hints['月亮→阿尼玛阶段'] = f'{moon_sign} → {_MOON_ANIMA_STAGE.get(moon_sign, "")}'

    venus_sign = positions.get('金星', {}).get('星座')
    if venus_sign:
        hints['金星→Fi/Fe表达'] = f'{venus_sign} → {_VENUS_F_EXPRESSION.get(venus_sign, "")}'

    saturn_sign = positions.get('土星', {}).get('星座')
    if saturn_sign:
        hints['土星→劣势功能压力点'] = (
            f'{saturn_sign} → {_SATURN_INFERIOR_PRESSURE.get(saturn_sign, "")}'
        )

    pluto_sign = positions.get('冥王星', {}).get('星座')
    if pluto_sign:
        hints['冥王→Demon位投射'] = f'{pluto_sign} → {_PLUTO_DEMON_FLAVOR.get(pluto_sign, "")}'

    if asc_sign:
        hints['上升→人格面具'] = f'{asc_sign} → 第一印象气质底色'

    return hints


# ---------------------------------------------------------------------------
# 基础算法
# ---------------------------------------------------------------------------

def deg_to_sign(deg):
    """0-360° 转换为星座+度数"""
    deg = deg % 360
    sign_idx = int(deg / 30)
    in_sign = deg - sign_idx * 30
    return SIGNS[sign_idx], round(in_sign, 2)


def calc_julian_day(year, month, day, hour, minute, tz_hours):
    """计算儒略日（UT）"""
    ut_hour = hour + minute / 60 - tz_hours
    return swe.julday(year, month, day, ut_hour)


def calc_planet(jd, planet_id):
    """计算行星位置 → (经度, 纬度, 距离, 速度) 的 tuple；速度<0 表示逆行"""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    return result  # (lon, lat, dist, lon_speed, lat_speed, dist_speed)


def calc_houses(jd, lat, lon):
    """计算十二宫宫始位置；高纬度自动 fallback Whole Sign。

    返回 (cusps, ascmc, system_label)
    """
    if abs(lat) > 60.0:
        cusps, ascmc = swe.houses(jd, lat, lon, b'W')  # 'W' = Whole Sign
        system_label = 'Whole Sign (高纬度自动 fallback)'
    else:
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')  # Placidus 默认
        system_label = 'Placidus'
    return cusps, ascmc, system_label


def find_house(planet_lon, cusps):
    """根据行星黄经判断它落在哪一宫（cusps 是 0-based 12 元素 tuple）"""
    planet_lon = planet_lon % 360
    for i in range(12):
        start = cusps[i] % 360
        end = cusps[(i + 1) % 12] % 360
        if start < end:
            if start <= planet_lon < end:
                return i + 1
        else:  # 跨 0°
            if planet_lon >= start or planet_lon < end:
                return i + 1
    return None


def _merge_orbs(orbs: dict | None) -> dict:
    """把用户覆盖项合并到默认 ORBS 上，缺失走默认。"""
    merged = dict(DEFAULT_ORBS)
    if orbs:
        for k, v in orbs.items():
            if k in merged:
                merged[k] = float(v)
    return merged


def calc_aspects(positions, orbs=None):
    """计算行星间相位（5 种主相位）；orbs 缺省走 DEFAULT_ORBS。"""
    orbs = _merge_orbs(orbs)
    aspects = []
    names = [n for n in positions.keys() if 'error' not in positions[n]]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            diff = abs(positions[a]['黄经'] - positions[b]['黄经'])
            if diff > 180:
                diff = 360 - diff
            for asp_name, asp_deg in ASPECT_DEGREES.items():
                orb = orbs.get(asp_name, DEFAULT_ORBS[asp_name])
                if abs(diff - asp_deg) <= orb:
                    aspects.append({
                        '行星A': a, '行星B': b, '相位': asp_name,
                        '实际角度': round(diff, 2),
                        '偏差': round(abs(diff - asp_deg), 2),
                        '使用容许度': orb,
                    })
                    break
    return aspects


def _coerce_tz(tz_arg, year, month, day, hour, minute):
    """把 tz 参数（浮点小时数或 IANA 名）统一规整为 (utc_hours, iana_or_none, is_dst)"""
    if isinstance(tz_arg, (int, float)):
        return float(tz_arg), None, False
    s = str(tz_arg).strip()
    # 纯数字字符串
    try:
        return float(s), None, False
    except ValueError:
        pass
    # IANA 名称：用 zoneinfo 算出生当时的偏移与 DST 标志
    utc = _utc_offset_at(s, year, month, day, hour, minute)
    dst = _is_dst_at(s, year, month, day, hour, minute)
    return utc, s, dst


def _validate_inputs(year, month, day, hour, minute, lat, lon):
    """入参校验"""
    if not (1 <= month <= 12):
        raise ValueError(f'月份非法: {month}')
    if not (1 <= day <= 31):
        raise ValueError(f'日期非法: {day}')
    if not (0 <= hour <= 23):
        raise ValueError(f'小时非法: {hour}')
    if not (0 <= minute <= 59):
        raise ValueError(f'分钟非法: {minute}')
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f'纬度需在 -90 ~ 90 之间: {lat}')
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f'经度需在 -180 ~ 180 之间: {lon}')


# ---------------------------------------------------------------------------
# 扩展配点：Lilith / 福点 / Vertex
# ---------------------------------------------------------------------------

def _calc_lilith(jd):
    """黑月莉莉丝（Mean Apogee）"""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, swe.MEAN_APOG, flags)
    return result[0] % 360.0


def _calc_part_of_fortune(asc_lon, sun_lon, moon_lon, is_day_chart):
    """福点公式：
      白天盘（太阳在地平线上方，1/12/11/10/9/8 宫）: ASC + Moon - Sun
      夜晚盘:                                            ASC + Sun - Moon
    """
    if is_day_chart:
        return (asc_lon + moon_lon - sun_lon) % 360.0
    return (asc_lon + sun_lon - moon_lon) % 360.0


def _is_day_chart(sun_house):
    """太阳在地平线上方（7-12 宫）即为白天盘"""
    if sun_house is None:
        return True
    return sun_house >= 7


# ---------------------------------------------------------------------------
# kerykeion SVG 生成
# ---------------------------------------------------------------------------

def generate_chart_svg(year, month, day, hour, minute, lat, lon, tz_str,
                       name='Subject', output_dir=None) -> str:
    """用 kerykeion 生成专业占星圆盘 SVG，返回文件路径。

    失败（kerykeion 未装 / 调用异常）时返回 None。
    output_dir 默认为 cache/svg（相对脚本目录）。
    """
    try:
        from kerykeion import AstrologicalSubject, KerykeionChartSVG  # type: ignore
    except ImportError:
        print('WARN: kerykeion 未安装，跳过 SVG 生成。可执行: '
              'pip install kerykeion --break-system-packages', file=sys.stderr)
        return None

    if output_dir is None:
        output_dir = os.path.join(_SCRIPT_DIR, '..', 'cache', 'svg')
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    try:
        subject = AstrologicalSubject(
            name, year, month, day, hour, minute,
            lng=float(lon), lat=float(lat), tz_str=tz_str,
            online=False,  # 已提供经纬度+时区，禁用 geonames 在线查询
        )
        chart = KerykeionChartSVG(
            subject, chart_type="Natal",
            new_output_directory=output_dir,
        )
        chart.makeSVG()
    except Exception as e:
        print(f'WARN: kerykeion SVG 生成失败: {e}', file=sys.stderr)
        return None

    # kerykeion 默认命名: {name} - Natal Chart.svg；按命主名拼装确切路径
    default_path = os.path.join(output_dir, f'{name} - Natal Chart.svg')
    if not os.path.exists(default_path):
        # 兜底：扫目录里最新的 svg
        svgs = [f for f in os.listdir(output_dir) if f.endswith('.svg')]
        if not svgs:
            return None
        svgs.sort(key=lambda f: os.path.getmtime(os.path.join(output_dir, f)),
                  reverse=True)
        return os.path.join(output_dir, svgs[0])

    # 重命名为 hash.svg 便于缓存层使用
    h = hashlib.sha256(
        f'{year}{month}{day}{hour}{minute}{lat}{lon}{tz_str}'.encode()
    ).hexdigest()[:16]
    final_path = os.path.join(output_dir, f'{h}.svg')
    try:
        os.replace(default_path, final_path)
        return final_path
    except OSError:
        return default_path


# ---------------------------------------------------------------------------
# 主排盘
# ---------------------------------------------------------------------------

def calc_chart(year, month, day, hour, minute, lat, lon, tz_hours,
               *, use_true_node=True, orbs=None,
               want_svg=False, svg_name='Subject', svg_tz=None, svg_out=None):
    """主排盘函数

    tz_hours 可为 float（UTC 偏移小时数）或 IANA 字符串（如 'America/New_York'）。
    use_true_node=True → swe.TRUE_NODE；False → swe.MEAN_NODE。
    orbs 形如 {'合相': 8, '对冲': 8, ...}，缺失项走默认。
    want_svg=True 触发 kerykeion 生成 SVG（失败不阻塞主流程）。
    """
    _validate_inputs(year, month, day, hour, minute, lat, lon)
    utc_offset, iana_name, dst_active = _coerce_tz(tz_hours, year, month, day, hour, minute)
    jd = calc_julian_day(year, month, day, hour, minute, utc_offset)

    # 行星（含可选 True/Mean Node）
    planets = list(PLANETS_BASE)
    node_id = swe.TRUE_NODE if use_true_node else swe.MEAN_NODE
    planets.insert(10, ('北交点', node_id))  # 保持原顺序：冥王后插入

    positions = {}
    for name, pid in planets:
        try:
            r = calc_planet(jd, pid)
            sign, in_sign = deg_to_sign(r[0])
            positions[name] = {
                '黄经': round(r[0], 4),
                '星座': sign,
                '宫内度数': in_sign,
                '逆行': r[3] < 0,
                '主管': SIGN_RULERS.get(sign, ''),
            }
        except Exception as e:
            positions[name] = {'error': str(e)}

    # 宫位（含高纬度 fallback）
    cusps, ascmc, house_system_label = calc_houses(jd, lat, lon)
    asc_sign, asc_deg = deg_to_sign(ascmc[0])
    mc_sign, mc_deg = deg_to_sign(ascmc[1])
    asc_lon = ascmc[0] % 360.0

    houses = []
    for i in range(12):
        sign, in_sign = deg_to_sign(cusps[i])
        houses.append({
            '宫位': i + 1,
            '含义': HOUSE_MEANINGS[i + 1],
            '宫始星座': sign,
            '宫内度数': in_sign,
            '宫主': SIGN_RULERS.get(sign, ''),
        })

    # 行星落宫
    for name, pos in positions.items():
        if 'error' in pos:
            continue
        h = find_house(pos['黄经'], cusps)
        pos['落宫'] = h

    # 扩展配点：Lilith / 福点 / Vertex
    extras = {}
    try:
        lilith_lon = _calc_lilith(jd)
        l_sign, l_deg = deg_to_sign(lilith_lon)
        extras['Lilith黑月'] = {
            '黄经': round(lilith_lon, 4),
            '星座': l_sign,
            '宫内度数': l_deg,
            '落宫': find_house(lilith_lon, cusps),
            '说明': '黑月莉莉丝（Mean Apogee）— 阴影中的女性原型 / 被压抑的本能',
        }
    except Exception as e:
        extras['Lilith黑月'] = {'error': str(e)}

    try:
        sun_house = positions.get('太阳', {}).get('落宫')
        is_day = _is_day_chart(sun_house)
        sun_lon_v = positions['太阳']['黄经']
        moon_lon_v = positions['月亮']['黄经']
        pof_lon = _calc_part_of_fortune(asc_lon, sun_lon_v, moon_lon_v, is_day)
        p_sign, p_deg = deg_to_sign(pof_lon)
        extras['福点'] = {
            '黄经': round(pof_lon, 4),
            '星座': p_sign,
            '宫内度数': p_deg,
            '落宫': find_house(pof_lon, cusps),
            '盘别': '日盘' if is_day else '夜盘',
            '说明': '福点 Part of Fortune — 身体福祉与生命资源的落点',
        }
    except Exception as e:
        extras['福点'] = {'error': str(e)}

    try:
        vertex_lon = ascmc[3] % 360.0
        v_sign, v_deg = deg_to_sign(vertex_lon)
        extras['Vertex'] = {
            '黄经': round(vertex_lon, 4),
            '星座': v_sign,
            '宫内度数': v_deg,
            '落宫': find_house(vertex_lon, cusps),
            '说明': 'Vertex — 命定相遇 / 第二下降点（关系中的宿命触发）',
        }
    except Exception as e:
        extras['Vertex'] = {'error': str(e)}

    # 相位
    aspects = calc_aspects(positions, orbs=orbs)

    # 太阳/月亮/上升 三轴心
    axis = {
        '太阳': f"{positions['太阳']['星座']}座 {positions['太阳']['宫内度数']}° (落 {positions['太阳']['落宫']} 宫)",
        '月亮': f"{positions['月亮']['星座']}座 {positions['月亮']['宫内度数']}° (落 {positions['月亮']['落宫']} 宫)",
        '上升': f"{asc_sign}座 {asc_deg}°",
        '天顶MC': f"{mc_sign}座 {mc_deg}°",
    }

    # 性格映射提示（v3 哲学骨架）
    personality_hints = _build_personality_hints(positions, asc_sign)

    result = {
        '出生信息': {
            '公历': f'{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}',
            '出生地经纬度': format_coord(lat, lon),
            '时区': format_tz(utc_offset),
            'IANA 时区': iana_name,
            'DST 状态': '夏令时' if dst_active else '标准时',
            '儒略日': round(jd, 6),
        },
        '宫位制': house_system_label,
        '北交类型': 'True Node' if use_true_node else 'Mean Node',
        '使用容许度': _merge_orbs(orbs),
        '三轴心': axis,
        '十大行星+北交+凯龙': positions,
        '十二宫': houses,
        '扩展配点': extras,
        '主要相位': aspects,
        '性格映射提示': personality_hints,
    }

    # 可选：生成 kerykeion SVG
    if want_svg:
        tz_for_svg = svg_tz or iana_name or _iana_from_offset(utc_offset)
        svg_path = generate_chart_svg(
            year, month, day, hour, minute, lat, lon, tz_for_svg,
            name=svg_name, output_dir=svg_out,
        )
        result['SVG圆盘'] = {
            '路径': svg_path,
            '时区': tz_for_svg,
            '生成器': 'kerykeion',
        } if svg_path else {'error': 'SVG 生成失败（kerykeion 未装或调用异常）'}

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')
_TIME_RE = re.compile(r'^\d{1,2}:\d{2}$')


def _parse_orbs(orbs_str: str) -> dict:
    """解析 --orbs=合相=8,对冲=8,三合=7,四分=7,六合=5"""
    out = {}
    for kv in orbs_str.split(','):
        kv = kv.strip()
        if not kv or '=' not in kv:
            continue
        k, v = kv.split('=', 1)
        k = k.strip()
        try:
            out[k] = float(v.strip())
        except ValueError:
            continue
    return out


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)

    # 抽出可选 --flag / --key=value 参数
    use_true_node = True
    orbs_override = None
    want_svg = False
    svg_name = 'Subject'
    svg_tz = None
    svg_out = None

    positional = []
    for arg in sys.argv[1:]:
        if arg == '--mean-node':
            use_true_node = False
        elif arg == '--svg':
            want_svg = True
        elif arg.startswith('--orbs='):
            orbs_override = _parse_orbs(arg[len('--orbs='):])
        elif arg.startswith('--svg-name='):
            svg_name = arg[len('--svg-name='):].strip() or 'Subject'
        elif arg.startswith('--svg-tz='):
            svg_tz = arg[len('--svg-tz='):].strip() or None
        elif arg.startswith('--svg-out='):
            svg_out = arg[len('--svg-out='):].strip() or None
        else:
            positional.append(arg)

    if len(positional) < 4:
        print(__doc__)
        sys.exit(1)

    date_arg = positional[0]
    time_arg = positional[1]
    if not _DATE_RE.match(date_arg):
        print(f'ERROR: 日期格式错误（需 YYYY-MM-DD）: {date_arg}', file=sys.stderr)
        sys.exit(2)
    if not _TIME_RE.match(time_arg):
        print(f'ERROR: 时间格式错误（需 HH:MM）: {time_arg}', file=sys.stderr)
        sys.exit(2)

    year, month, day = map(int, date_arg.split('-'))
    hour, minute = map(int, time_arg.split(':'))
    try:
        lat = float(positional[2])
        lon = float(positional[3])
    except ValueError:
        print('ERROR: 经纬度必须为数字', file=sys.stderr)
        sys.exit(2)

    # tz 参数允许浮点数或 IANA 字符串
    if len(positional) >= 5:
        tz_arg: object = positional[4]
        try:
            tz_arg = float(positional[4])  # 形如 "8" / "-4.5"
        except ValueError:
            pass  # 保留为字符串（IANA 名）
    else:
        tz_arg = 8.0

    try:
        result = calc_chart(
            year, month, day, hour, minute, lat, lon, tz_arg,
            use_true_node=use_true_node, orbs=orbs_override,
            want_svg=want_svg, svg_name=svg_name,
            svg_tz=svg_tz, svg_out=svg_out,
        )
    except ValueError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
