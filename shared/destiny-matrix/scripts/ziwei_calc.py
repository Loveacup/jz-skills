#!/usr/bin/env python3
# v3.0
"""
紫微斗数完整排盘（v3 · Agent J · 紫微严谨性）

基于 iztro-py（纯 Python 实现的 iztro），使用其内置 zh_CN 翻译资源。
v3 增强：
  1. 派别明示：顶部输出排盘派别说明（三合派为 iztro-py 默认）
  2. 闰月双盘：检测出生月是否处于闰月，如是则同时输出
                  「中分法盘」（fix_leap=True，iztro 默认）+
                  「正玄山人法盘」（fix_leap=False，闰月独立排）
  3. 性格映射提示：命宫主星 → Beebe Hero / 夫妻宫 → 阿尼玛阶段 /
                    福德宫 → Child / 命主+身主 → 个体化任务
  4. 输入校验：日期格式、时辰索引 0-11、性别 m/f

用法:
  python3 ziwei_calc.py <yyyy-mm-dd> <时辰索引 0-11> <gender:m|f>
示例:
  python3 ziwei_calc.py 1993-09-30 9 f   (酉时 = 9, 17:00-19:00)

时辰索引:
  0=子(23-01) 1=丑(01-03) 2=寅(03-05) 3=卯(05-07) 4=辰(07-09) 5=巳(09-11)
  6=午(11-13) 7=未(13-15) 8=申(15-17) 9=酉(17-19) 10=戌(19-21) 11=亥(21-23)

依赖:
  pip install iztro-py lunar_python --break-system-packages
"""
import sys
import json
import re
import copy
from datetime import datetime

try:
    import iztro_py
    from iztro_py.i18n.locales.zh_CN import translations as ZH_CN
except ImportError:
    print("ERROR: 请先安装 iztro-py: pip install iztro-py --break-system-packages",
          file=sys.stderr)
    sys.exit(1)

try:
    from lunar_python import Solar  # 用于闰月检测
    _HAS_LUNAR = True
except ImportError:
    _HAS_LUNAR = False


# ============================================================
# i18n 翻译表
# ============================================================

def _build_lookup():
    flat = {}
    for k, v in ZH_CN.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, dict):
                    for ssk, ssv in sub_v.items():
                        flat[ssk] = ssv
                else:
                    flat[sub_k] = sub_v
        else:
            flat[k] = v
    flat['changshengChang'] = '长生'
    flat['siChang'] = '死'
    flat['jueChang'] = '绝'
    flat['xishenJiang'] = '息神'
    flat['tianyue2'] = '天月'
    return flat


LOOKUP = _build_lookup()


def L(s):
    if not s or not isinstance(s, str):
        return s
    return LOOKUP.get(s, s)


def localize_star(star):
    return {
        '名称': L(star.name),
        '亮度': star.brightness or '',
        '四化': star.mutagen or '',
        '类型': star.type,
    }


# ============================================================
# v3 · 性格映射提示表
# ============================================================

# 紫微 14 主星 → Beebe Hero / Parent 候选
# 出处：cross-analysis-patterns.md 表 2（Agent F）
ZIWEI_TO_BEEBE = {
    '紫微': {'Hero候选': 'Te-Hero', 'Parent候选': 'Ni-Parent',
             '原型剧场': '统御舞台 — 性格被迫学习"承担与孤独"'},
    '天府': {'Hero候选': 'Si-Hero', 'Parent候选': 'Te-Parent',
             '原型剧场': '稳定舞台 — 性格在"守成与积累"中验证自己'},
    '太阳': {'Hero候选': 'Fe-Hero', 'Parent候选': '随宫位变化',
             '原型剧场': '光明舞台 — 性格在被照见与被消耗之间摆动'},
    '太阴': {'Hero候选': 'Fi-Hero', 'Parent候选': '随宫位变化',
             '原型剧场': '内省舞台 — 性格通过"内在涟漪"理解世界'},
    '武曲': {'Hero候选': 'Te-Hero', 'Parent候选': 'Ti-Parent',
             '原型剧场': '实战舞台 — 性格在"硬碰硬"中锻炼判断'},
    '天同': {'Hero候选': 'Fe-Hero', 'Parent候选': 'Si-Parent',
             '原型剧场': '享乐舞台 — 性格学习"享受与放下"'},
    '廉贞': {'Hero候选': 'Ni-Hero', 'Parent候选': 'Te-Parent',
             '原型剧场': '谋略舞台 — 性格在"暗流与博弈"中演化'},
    '天机': {'Hero候选': 'Ne-Hero', 'Parent候选': 'Ti-Parent',
             '原型剧场': '智囊舞台 — 性格在"为他人出主意"中安放才智'},
    '巨门': {'Hero候选': 'Ti-Hero', 'Parent候选': 'Ne-Parent',
             '原型剧场': '言辞舞台 — 性格通过"剖析与质疑"建立位置'},
    '天相': {'Hero候选': 'Fe-Hero', 'Parent候选': 'Si-Parent',
             '原型剧场': '辅佐舞台 — 性格在"成就他人"中找到价值'},
    '天梁': {'Hero候选': 'Si-Hero', 'Parent候选': 'Fe-Parent',
             '原型剧场': '长者舞台 — 性格在"承担长辈角色"中成熟'},
    '七杀': {'Hero候选': 'Se-Hero', 'Parent候选': '随宫位变化',
             '原型剧场': '战场舞台 — 性格在"一次次重新出发"中前进'},
    '破军': {'Hero候选': 'Ne-Hero', 'Parent候选': 'Se-Parent',
             '原型剧场': '革新舞台 — 性格在"打碎重建"的循环中演化'},
    '贪狼': {'Hero候选': 'Se-Hero', 'Parent候选': 'Fe-Parent',
             '原型剧场': '享乐舞台 — 性格在"欲望的张力"中辨认自我'},
}

# 夫妻宫主星 → 阿尼玛/阿尼姆斯停留阶段（出处：jung-relationship-dynamics.md §4.4）
SPOUSE_TO_ANIMA = {
    '紫微': {'男阿尼玛阶段': 'Sophia（精神追求型伴侣）',
             '女阿尼姆斯阶段': '智慧（智者型伴侣）'},
    '天府': {'男阿尼玛阶段': 'Mary（稳定母性型伴侣）',
             '女阿尼姆斯阶段': '行动（事业型伴侣）'},
    '太阴': {'男阿尼玛阶段': 'Mary/Sophia（柔和精神型）',
             '女阿尼姆斯阶段': '言说（敏感智识型）'},
    '太阳': {'男阿尼玛阶段': 'Helen（光辉戏剧型）',
             '女阿尼姆斯阶段': '行动（英雄型）'},
    '武曲': {'男阿尼玛阶段': 'Eve（实力派/能干型）',
             '女阿尼姆斯阶段': '力量（强势保护型）'},
    '廉贞': {'男阿尼玛阶段': 'Eve/Helen（感官激情型）',
             '女阿尼姆斯阶段': '力量（性吸引强烈）'},
    '贪狼': {'男阿尼玛阶段': 'Eve（感官放纵型）',
             '女阿尼姆斯阶段': '力量（魅力型）'},
    '七杀': {'男阿尼玛阶段': 'Helen（戏剧冲突型）',
             '女阿尼姆斯阶段': '行动（凌厉型）'},
    '破军': {'男阿尼玛阶段': 'Helen（毁灭重生型）',
             '女阿尼姆斯阶段': '行动（破坏建造型）'},
    '天机': {'男阿尼玛阶段': 'Mary（智慧温柔型）',
             '女阿尼姆斯阶段': '言说（学者型）'},
    '天梁': {'男阿尼玛阶段': 'Mary（长辈型）',
             '女阿尼姆斯阶段': '言说（导师型）'},
    '天同': {'男阿尼玛阶段': 'Eve（孩童母性型）',
             '女阿尼姆斯阶段': '力量（保护型）'},
    '巨门': {'男阿尼玛阶段': 'Mary（深谈型）',
             '女阿尼姆斯阶段': '言说（口才型）'},
    '天府_配合': '稳定 / 积累型阶段',
}

# 福德宫主星 → 第三功能 Child 表达倾向
# 福德宫主"内心 / 享受 / 精神归属"，与 Beebe 第 3 位 Child 的"撒娇/退行"模式直接对应
FORTUNE_TO_CHILD = {
    '紫微': '权威化 Child — 想被尊崇地呵护，但羞于明说',
    '天府': '稳定型 Child — 渴望被像储藏宝物一样珍藏',
    '太阴': 'Fi-Child — 在私密场所对少数人显露真情',
    '太阳': 'Fe-Child — 在被照见的瞬间撒娇，要求"看见我"',
    '武曲': 'Te-Child — 用"做事"代替撒娇，渴望成果被认可',
    '天同': 'Fe-Child — 直接索要被宠爱，最透明的撒娇位',
    '廉贞': 'Ni-Child — 在情绪暗流中表达脆弱，难以言说',
    '天机': 'Ne-Child — 撒娇方式是"陪我想象一件不实际的事"',
    '巨门': 'Ti-Child — 撒娇方式是"陪我钻一个小牛角尖"',
    '天相': 'Fe-Child — 在"被需要"中获得撒娇的合法性',
    '天梁': 'Si-Child — 怀旧型撒娇，要老味道老地方',
    '七杀': 'Se-Child — 用冒险/玩乐索要陪伴，不善软语',
    '破军': 'Ne-Child — 撒娇方式是"陪我做一件破坏性的傻事"',
    '贪狼': 'Se-Child — 直接索要感官与娱乐，最外显的 Child 位',
}

# 命主 + 身主 → 个体化任务
# 命主代表"先天禀赋"（生年支决定），身主代表"后天修行"（生年支决定）
SOUL_BODY_TASK = {
    # 仅列出常见组合，未列出者用通用模板
}


def _first_main_star_name(palace_data):
    """从一个宫位 dict 中提取首颗主星中文名（无主星返回 None）"""
    stars = palace_data.get('主星', [])
    for s in stars:
        name = s.get('名称') if isinstance(s, dict) else None
        if name and name in ZIWEI_TO_BEEBE:
            return name
    return None


def build_personality_hint(palaces, base):
    """构造性格映射提示（v3 哲学骨架）

    输入:
      palaces  已 i18n 化的十二宫 list（顺序按 iztro-py 输出）
      base     基础信息 dict（含命主 / 身主）

    输出:
      dict 形式的性格映射提示
    """
    # 索引宫位
    by_name = {p.get('宫位'): p for p in palaces}
    ming = by_name.get('命宫')
    spouse = by_name.get('夫妻')
    fortune = by_name.get('福德')

    ming_star = _first_main_star_name(ming) if ming else None
    spouse_star = _first_main_star_name(spouse) if spouse else None
    fortune_star = _first_main_star_name(fortune) if fortune else None

    soul = base.get('命主', '')
    body = base.get('身主', '')

    hint = {
        '说明': '本表只给"候选 / 倾向"，最终性格签名由 jung_calc.py 主导，紫微仅做剧场印证',
    }

    # 1) 命宫 → Beebe Hero / Parent
    if ming_star and ming_star in ZIWEI_TO_BEEBE:
        h = ZIWEI_TO_BEEBE[ming_star]
        hint['命宫主星→Beebe Hero 候选'] = (
            f'{ming_star} → {h["Hero候选"]} / {h["Parent候选"]}（{h["原型剧场"]}）'
        )
    elif ming and not ming.get('主星'):
        hint['命宫主星→Beebe Hero 候选'] = (
            f'命宫无主星，借对宫{by_name.get("迁移", {}).get("宫位", "迁移")}宫主星论；'
            f'性格倾向更受外部环境刻画'
        )

    # 2) 夫妻宫 → 阿尼玛 / 阿尼姆斯阶段
    if spouse_star and spouse_star in SPOUSE_TO_ANIMA:
        a = SPOUSE_TO_ANIMA[spouse_star]
        hint['夫妻宫主星→阿尼玛/阿尼姆斯阶段'] = (
            f'{spouse_star} → 男命常停 {a["男阿尼玛阶段"]}；女命常停 {a["女阿尼姆斯阶段"]}'
        )

    # 3) 福德宫 → 第三功能 Child 表达
    if fortune_star and fortune_star in FORTUNE_TO_CHILD:
        hint['福德宫主星→第三功能 Child 表达'] = (
            f'{fortune_star} → {FORTUNE_TO_CHILD[fortune_star]}'
        )
    if fortune:
        # 检查福德宫是否有化忌（受阻信号）
        for s in fortune.get('主星', []):
            mu = s.get('四化') if isinstance(s, dict) else ''
            if mu and '忌' in str(mu):
                hint.setdefault('福德宫四化警示', []).append(
                    f'{s.get("名称")}化忌入福德 → Child 位表达受阻，撒娇通道易闭锁')

    # 4) 命主 + 身主 → 个体化任务
    if soul and body:
        soul_clean = soul.strip()
        body_clean = body.strip()
        # 命主代表"内核"，身主代表"修行方向"
        # 通用模板：从命主主星 → 身主主星 = 性格的内化重心
        soul_beebe = ZIWEI_TO_BEEBE.get(soul_clean, {}).get('Hero候选', '?')
        body_beebe = ZIWEI_TO_BEEBE.get(body_clean, {}).get('Hero候选', '?')
        if soul_clean == body_clean:
            task = (f'命主与身主同为「{soul_clean}」（{soul_beebe}）→ '
                    f'内外合一型，个体化任务：把先天禀赋的能量充分外化')
        else:
            task = (f'命主「{soul_clean}」（{soul_beebe}）→ 身主「{body_clean}」（{body_beebe}）'
                    f' → 个体化任务：将{soul_beebe}的内核能量整合进{body_beebe}的外在表达')
        hint['命主+身主→个体化任务'] = task

    return hint


# ============================================================
# v3 · 输入校验
# ============================================================

_DATE_RE = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')


def validate_inputs(date_str, hour_idx, gender_str):
    """输入校验：日期 / 时辰 / 性别。失败抛 ValueError"""
    if not _DATE_RE.match(date_str):
        raise ValueError(f'日期格式错误：{date_str!r}，应为 YYYY-MM-DD')
    try:
        y, m, d = (int(x) for x in date_str.split('-'))
        datetime(y, m, d)
    except ValueError as e:
        raise ValueError(f'日期非法：{date_str!r}（{e}）')

    if not isinstance(hour_idx, int) or not (0 <= hour_idx <= 11):
        raise ValueError(f'时辰索引必须为 0-11 整数，得到 {hour_idx!r}')

    if gender_str not in ('m', 'f'):
        raise ValueError(f"性别必须为 'm' 或 'f'，得到 {gender_str!r}")

    return y, m, d


# ============================================================
# v3 · 闰月检测
# ============================================================

def detect_leap_month(year, month, day):
    """检测出生公历日是否落在农历闰月。

    返回:
        {'is_leap': bool, 'lunar_year': int, 'lunar_month': int,
         'lunar_day': int, 'lunar_month_chinese': str}
        若未安装 lunar_python 返回 None
    """
    if not _HAS_LUNAR:
        return None
    s = Solar.fromYmd(year, month, day)
    lu = s.getLunar()
    raw_month = lu.getMonth()  # 负数代表闰月
    return {
        'is_leap': raw_month < 0,
        'lunar_year': lu.getYear(),
        'lunar_month': abs(raw_month),
        'lunar_day': lu.getDay(),
        'lunar_month_chinese': lu.getMonthInChinese(),
    }


# ============================================================
# 核心排盘
# ============================================================

def _build_chart(date_str, hour_idx, gender_zh, leap_info=None,
                 force_lunar=False, fix_leap=True):
    """构造单张完整命盘（不含派别说明 / 性格映射，由调用方拼装）

    force_lunar=True 时通过 by_lunar(is_leap_month=True, fix_leap=fix_leap) 排盘；
    否则通过 by_solar (iztro-py 默认 fix_leap=True，对应中分法)。
    """
    if force_lunar and leap_info and leap_info['is_leap']:
        lunar_str = (f"{leap_info['lunar_year']}-"
                     f"{leap_info['lunar_month']}-{leap_info['lunar_day']}")
        astrolabe = iztro_py.by_lunar(
            lunar_str, hour_idx, gender_zh,
            is_leap_month=True, fix_leap=fix_leap, language='zh-CN',
        )
    else:
        astrolabe = iztro_py.by_solar(date_str, hour_idx, gender_zh, language='zh-CN')

    base = {
        '公历日期': astrolabe.solar_date,
        '农历日期': astrolabe.lunar_date,
        '四柱': astrolabe.chinese_date,
        '出生时辰': astrolabe.time,
        '时辰范围': astrolabe.time_range,
        '太阳星座': astrolabe.sign,
        '生肖': astrolabe.zodiac,
        '命宫地支': L(astrolabe.earthly_branch_of_soul_palace),
        '身宫地支': L(astrolabe.earthly_branch_of_body_palace),
        '命主': L(astrolabe.soul),
        '身主': L(astrolabe.body),
        '五行局': astrolabe.five_elements_class,
    }

    palaces = []
    for p in astrolabe.palaces:
        palace_data = {
            '宫位': L(p.name),
            '地支': L(p.earthly_branch),
            '天干': L(p.heavenly_stem),
            '是否身宫': p.is_body_palace,
            '是否来因宫': p.is_original_palace,
            '主星': [localize_star(s) for s in p.major_stars],
            '辅星': [localize_star(s) for s in p.minor_stars],
            '杂耀': [localize_star(s) for s in p.adjective_stars],
            '长生十二神': L(p.changsheng12) if p.changsheng12 else '',
            '博士十二神': L(p.boshi12) if p.boshi12 else '',
            '将前十二神': L(p.jiangqian12) if p.jiangqian12 else '',
            '岁前十二神': L(p.suiqian12) if p.suiqian12 else '',
            '小限年龄': p.ages,
        }
        if p.decadal:
            palace_data['大限'] = {
                '范围': p.decadal.range,
                '天干': L(p.decadal.heavenly_stem),
                '地支': L(p.decadal.earthly_branch),
            }
        palaces.append(palace_data)

    today = datetime.now().strftime('%Y-%m-%d')
    horoscope = astrolabe.horoscope(today)

    def horo_to_dict(item):
        if item is None:
            return None
        d = item.model_dump() if hasattr(item, 'model_dump') else dict(item)
        out = {}
        for k, v in d.items():
            if v is None:
                continue
            if k == 'name':
                out['名称'] = v
            elif k == 'index':
                out['宫位序号'] = v
            elif k == 'heavenly_stem':
                out['天干'] = L(v)
            elif k == 'earthly_branch':
                out['地支'] = L(v)
            elif k == 'palace_names':
                out['宫位排列'] = [L(n) for n in v]
            elif k == 'mutagen':
                out['四化'] = [L(s) for s in v]
            elif k == 'range':
                out['年龄范围'] = v
            elif k == 'stars':
                if v:
                    out['流耀'] = [
                        [L(s.get('name', '')) if isinstance(s, dict)
                         else (L(getattr(s, 'name', str(s)))) for s in cell]
                        for cell in v
                    ]
        return out

    horoscope_data = {
        '查询日期': today,
        '虚岁': horoscope.nominal_age,
        '实岁': horoscope.age if isinstance(horoscope.age, int) else None,
        '当前大限': horo_to_dict(horoscope.decadal),
        '当前流年': horo_to_dict(horoscope.yearly),
        '当前流月': horo_to_dict(horoscope.monthly),
        '当前流日': horo_to_dict(horoscope.daily),
    }

    return {
        '基础信息': base,
        '十二宫': palaces,
        '运限': horoscope_data,
        '性格映射提示': build_personality_hint(palaces, base),
    }


def calc_ziwei(date_str, hour_idx, gender_str):
    """主计算函数（v3）"""
    y, m, d = validate_inputs(date_str, hour_idx, gender_str)
    gender_zh = '男' if gender_str == 'm' else '女'

    # 主排盘（中分法 = iztro-py 默认）
    main_chart = _build_chart(date_str, hour_idx, gender_zh,
                              leap_info=None, force_lunar=False)

    # 派别明示
    main_chart['排盘派别'] = '三合派（iztro-py 默认）'
    main_chart['派别说明'] = (
        '本盘以三合派排盘，重视星耀亮度与三方四正；'
        '如需飞星派四化分析，请另调用飞星派工具校验'
    )

    # 闰月检测
    leap_info = detect_leap_month(y, m, d)
    if leap_info and leap_info['is_leap']:
        # 双盘对比
        # 中分法：iztro 默认 fix_leap=True，前 15 天归上月，后 15 天归下月
        # main_chart 已经是中分法盘（by_solar 入口自动 fix_leap=True）
        # 这里独立深拷贝一份，避免循环引用
        zhongfen_chart = copy.deepcopy(main_chart)
        zhongfen_chart['排盘派别'] = '三合派（中分法 · iztro-py 默认）'
        zhongfen_chart['派别说明'] = (
            '本盘按中分法处理闰月：闰月前 15 天归上月、后 15 天归下月排盘'
        )

        # 正玄山人法：闰月独立排，强制按闰 N 月起紫微
        zhengxuan_chart = _build_chart(
            date_str, hour_idx, gender_zh,
            leap_info=leap_info, force_lunar=True, fix_leap=False,
        )
        zhengxuan_chart['排盘派别'] = '三合派（正玄山人法 · 闰月独立）'
        zhengxuan_chart['派别说明'] = (
            '本盘按正玄山人法处理闰月：闰月独立排盘，'
            '紫微星按闰月份直接定位，不并入相邻月'
        )

        main_chart['闰月警告'] = {
            '状态': f'命主出生于闰{leap_info["lunar_month"]}月（{leap_info["lunar_month_chinese"]}）',
            '建议': '两盘并行，对照分析师已知历史事件择优；若无法判定，以中分法盘为主',
            '中分法盘': zhongfen_chart,
            '正玄山人法盘': zhengxuan_chart,
        }
    elif leap_info:
        # 普通月，记录一行说明
        main_chart['闰月警告'] = {
            '状态': f'命主出生于普通月（农历{leap_info["lunar_month_chinese"]}月）',
            '建议': '无需双盘',
        }

    return main_chart


# ============================================================
# CLI
# ============================================================

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    date_str = sys.argv[1]
    try:
        hour_idx = int(sys.argv[2])
    except ValueError:
        print(f'ERROR: 时辰索引非整数: {sys.argv[2]!r}', file=sys.stderr)
        sys.exit(1)
    gender_str = sys.argv[3].lower()

    try:
        result = calc_ziwei(date_str, hour_idx, gender_str)
    except ValueError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)

    def fallback(o):
        if hasattr(o, 'model_dump'):
            return o.model_dump()
        if hasattr(o, '__dict__'):
            return o.__dict__
        return str(o)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=fallback))


if __name__ == '__main__':
    main()
