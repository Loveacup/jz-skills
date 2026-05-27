#!/usr/bin/env python3
# v3.0
"""
八字命理完整排盘（v3）

v3 相比 v2 的增强：
1. 调候用神补全 120 组（十日主 x 十二月）—— 据徐乐吾《穷通宝鉴评注》
2. 神煞模块：17 种核心神煞按四柱分列输出
3. 早 / 夜子时参数化（--zi-hour-rule=early|late）
4. 跨节气警告：出生时刻距节气 < 15 分钟时附"另一可能月柱"双盘
5. 真太阳时已校正标记（接 _common.py 上游处理）
6. 性格映射提示：日主意象 + 格局倾向 + 五行偏强 / 偏弱 + 调候 -> 认知功能线索

核心立场（v3）：八字是"性格的能量基础"，玄学辅证而非决定。
本脚本只产生数据，命书叙事由 cast_chart.py 之上的工作流完成。

主库：lunar_python（精确起运、纳音、十神、空亡、大运）
辅库：sxtwl（四柱交叉校验）

用法：
    python3 bazi_calc.py <yyyy-mm-dd> <hh:mm> <gender:m|f>
                         [--zi-hour-rule=early|late]
                         [--true-solar-time-corrected=yes|no]

示例：
    python3 bazi_calc.py 1993-09-30 17:30 f
    python3 bazi_calc.py 1985-12-21 23:30 m --zi-hour-rule=late

依赖：pip install lunar_python sxtwl --break-system-packages
"""
import sys
import json
from datetime import datetime, timedelta

try:
    from lunar_python import Lunar, Solar
except ImportError:
    print("ERROR: 请先安装 lunar_python: pip install lunar_python --break-system-packages")
    sys.exit(1)

try:
    import sxtwl
    HAS_SXTWL = True
except ImportError:
    HAS_SXTWL = False


# ============================================================
# 基础常量
# ============================================================

HS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
EB = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 天干阴阳
GAN_YINYANG = {
    '甲': '阳', '丙': '阳', '戊': '阳', '庚': '阳', '壬': '阳',
    '乙': '阴', '丁': '阴', '己': '阴', '辛': '阴', '癸': '阴',
}

# 天干五行
GAN_WX = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
    '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水',
}

# 地支五行
ZHI_WX = {
    '寅': '木', '卯': '木',
    '巳': '火', '午': '火',
    '辰': '土', '戌': '土', '丑': '土', '未': '土',
    '申': '金', '酉': '金',
    '亥': '水', '子': '水',
}

# 地支藏干（本气 / 中气 / 余气 + 权重）
HIDDEN_WEIGHTS = {
    '子': [('癸', 1.0)],
    '丑': [('己', 0.6), ('癸', 0.3), ('辛', 0.1)],
    '寅': [('甲', 0.6), ('丙', 0.3), ('戊', 0.1)],
    '卯': [('乙', 1.0)],
    '辰': [('戊', 0.6), ('乙', 0.3), ('癸', 0.1)],
    '巳': [('丙', 0.6), ('庚', 0.3), ('戊', 0.1)],
    '午': [('丁', 0.7), ('己', 0.3)],
    '未': [('己', 0.6), ('丁', 0.3), ('乙', 0.1)],
    '申': [('庚', 0.6), ('壬', 0.3), ('戊', 0.1)],
    '酉': [('辛', 1.0)],
    '戌': [('戊', 0.6), ('辛', 0.3), ('丁', 0.1)],
    '亥': [('壬', 0.7), ('甲', 0.3)],
}

DM_IMAGE = {
    '甲': '参天大树 · 向上生长 · 刚直不阿',
    '乙': '花草藤蔓 · 柔韧灵活 · 善于适应',
    '丙': '太阳 · 光明磊落 · 热情奔放',
    '丁': '灯烛 · 温暖细腻 · 持续燃烧',
    '戊': '高山大地 · 厚重稳定 · 包容万物',
    '己': '田园湿土 · 滋养生长 · 谦逊务实',
    '庚': '刀剑铁器 · 锋利果断 · 杀伐决断',
    '辛': '珠玉首饰 · 精致优雅 · 追求完美',
    '壬': '江河大海 · 智慧流通 · 奔流不息',
    '癸': '雨露清泉 · 润物无声 · 灵动聪慧',
}


# ============================================================
# 调候用神表（120 组，徐乐吾《穷通宝鉴评注》核心条目）
# 数据格式：(日主, 月支) -> {'用神': '主用·辅用·调候', 'reason': '...'}
# 用神排序遵循典籍原序，· 分隔
# ============================================================

DIAOHOU_TABLE = {
    # ---------- 甲木十二月 ----------
    ('甲', '寅'): {'用神': '丙·癸', 'reason': '初春木嫩，专取丙火解寒，癸水润根'},
    ('甲', '卯'): {'用神': '庚·丙·丁', 'reason': '阳刃当令，专用庚金制刃，丙丁火透为佐'},
    ('甲', '辰'): {'用神': '庚·丁·壬', 'reason': '伤官制杀，用庚必须丁火制之，壬水润木'},
    ('甲', '巳'): {'用神': '癸·丁·庚', 'reason': '调候为急，癸水为主，丁庚为辅'},
    ('甲', '午'): {'用神': '癸·丁·庚', 'reason': '木性虚焦，专取癸水滋润'},
    ('甲', '未'): {'用神': '癸·丁·庚', 'reason': '上半月同午月用癸，下半月用庚丁'},
    ('甲', '申'): {'用神': '庚·丁·壬', 'reason': '七杀当令，用丁制杀，壬水通根'},
    ('甲', '酉'): {'用神': '庚·丁·丙', 'reason': '正官当令，用丁制杀，丙火调候'},
    ('甲', '戌'): {'用神': '庚·甲·丁·壬·癸', 'reason': '土旺用甲疏，木旺用庚劈'},
    ('甲', '亥'): {'用神': '庚·丁·丙·戊', 'reason': '亥月木长生而水旺，丙火调候，戊土止水'},
    ('甲', '子'): {'用神': '丁·庚·丙', 'reason': '木性生寒，丁火为主，庚金劈甲引丁'},
    ('甲', '丑'): {'用神': '丁·庚·丙', 'reason': '严冬冻木，丁火必不可少，庚劈甲引丁'},

    # ---------- 乙木十二月 ----------
    ('乙', '寅'): {'用神': '丙·癸', 'reason': '寒木向阳，丙火为主，癸水为佐'},
    ('乙', '卯'): {'用神': '丙·癸', 'reason': '阳刃格，丙暖癸润，气候为先'},
    ('乙', '辰'): {'用神': '癸·丙·戊', 'reason': '木气尚有余，先癸后丙'},
    ('乙', '巳'): {'用神': '癸·丙', 'reason': '调候为急，专用癸水'},
    ('乙', '午'): {'用神': '癸·丙', 'reason': '夏木须水，无癸不秀'},
    ('乙', '未'): {'用神': '癸·丙·庚', 'reason': '润土养木，癸水为主'},
    ('乙', '申'): {'用神': '丙·癸·己', 'reason': '七杀当令，丙火制杀，癸水化杀'},
    ('乙', '酉'): {'用神': '癸·丙·丁', 'reason': '秋木凋零，丙火暖局，癸水润根'},
    ('乙', '戌'): {'用神': '癸·辛', 'reason': '土旺木枯，专用癸水'},
    ('乙', '亥'): {'用神': '丙·戊', 'reason': '木气向衰，丙暖戊止'},
    ('乙', '子'): {'用神': '丙·戊', 'reason': '冬木向阳，丙火为主，戊土制水'},
    ('乙', '丑'): {'用神': '丙·戊', 'reason': '严寒之木，无丙不生，戊土培根'},

    # ---------- 丙火十二月 ----------
    ('丙', '寅'): {'用神': '壬·庚', 'reason': '初春丙火虽弱，专用壬水显其辉'},
    ('丙', '卯'): {'用神': '壬·己', 'reason': '阳刃驾杀，壬水为主，己土泄火'},
    ('丙', '辰'): {'用神': '壬·甲', 'reason': '土晦丙光，先壬后甲'},
    ('丙', '巳'): {'用神': '壬·庚·癸', 'reason': '建禄之月，壬水制火，庚金生壬'},
    ('丙', '午'): {'用神': '壬·庚', 'reason': '阳刃当令，专用壬水制火'},
    ('丙', '未'): {'用神': '壬·庚', 'reason': '伤官泄气，壬水调候'},
    ('丙', '申'): {'用神': '壬·戊', 'reason': '杀刃相停，壬水通根，戊土制水'},
    ('丙', '酉'): {'用神': '壬·癸', 'reason': '日落西山，壬水辅照'},
    ('丙', '戌'): {'用神': '甲·壬', 'reason': '土旺晦火，先取甲木破土'},
    ('丙', '亥'): {'用神': '甲·戊·庚·壬', 'reason': '失令之火，需甲木生扶'},
    ('丙', '子'): {'用神': '壬·戊·己', 'reason': '正官当令，壬水辅照，戊己晦火'},
    ('丙', '丑'): {'用神': '壬·甲', 'reason': '冬寒之火，专用壬水辅照，甲木生火'},

    # ---------- 丁火十二月 ----------
    ('丁', '寅'): {'用神': '甲·庚', 'reason': '丁火得寅，甲木为主，庚金劈甲引丁'},
    ('丁', '卯'): {'用神': '庚·甲', 'reason': '湿木难生丁，专用庚金劈甲'},
    ('丁', '辰'): {'用神': '甲·庚', 'reason': '木气尚旺，甲庚并用'},
    ('丁', '巳'): {'用神': '甲·庚', 'reason': '建禄之月，甲木生丁，庚劈甲为薪'},
    ('丁', '午'): {'用神': '壬·庚·癸', 'reason': '阳刃驾杀，专用壬水制火'},
    ('丁', '未'): {'用神': '甲·壬·庚', 'reason': '燥土难生火，先甲后壬'},
    ('丁', '申'): {'用神': '甲·庚·丙·戊', 'reason': '正财当令，甲木生丁，庚劈甲'},
    ('丁', '酉'): {'用神': '甲·庚·丙·戊', 'reason': '失令之火，专用甲木'},
    ('丁', '戌'): {'用神': '甲·庚·戊', 'reason': '土晦丁光，先甲后庚'},
    ('丁', '亥'): {'用神': '甲·庚', 'reason': '正官当令，木旺无妨，甲庚为辅'},
    ('丁', '子'): {'用神': '甲·庚', 'reason': '七杀当令，专用甲木化杀生身'},
    ('丁', '丑'): {'用神': '甲·庚', 'reason': '冬寒之火，丁不离甲，甲不离庚'},

    # ---------- 戊土十二月 ----------
    ('戊', '寅'): {'用神': '丙·甲·癸', 'reason': '七杀当令，专用丙火，甲木疏土'},
    ('戊', '卯'): {'用神': '丙·甲·癸', 'reason': '正官当令，丙暖癸润'},
    ('戊', '辰'): {'用神': '甲·丙·癸', 'reason': '比劫当令，专用甲木疏土'},
    ('戊', '巳'): {'用神': '甲·丙·癸', 'reason': '调候为急，专用癸水滋润'},
    ('戊', '午'): {'用神': '壬·甲·丙', 'reason': '阳刃当令，专用壬水润土'},
    ('戊', '未'): {'用神': '癸·丙·甲', 'reason': '燥土干裂，专用癸水滋润'},
    ('戊', '申'): {'用神': '丙·癸·甲', 'reason': '食神当令，丙火调候，癸水滋养'},
    ('戊', '酉'): {'用神': '丙·癸', 'reason': '伤官泄秀，丙照癸润'},
    ('戊', '戌'): {'用神': '甲·癸·丙', 'reason': '土厚专用甲木疏'},
    ('戊', '亥'): {'用神': '甲·丙', 'reason': '土气虚寒，先甲后丙'},
    ('戊', '子'): {'用神': '丙·甲', 'reason': '三冬土不暖不生，丙火为先'},
    ('戊', '丑'): {'用神': '丙·甲', 'reason': '严寒湿土，丙火解冻，甲木疏土'},

    # ---------- 己土十二月 ----------
    ('己', '寅'): {'用神': '丙·庚·甲', 'reason': '湿土寒冷，专用丙火暖局'},
    ('己', '卯'): {'用神': '甲·癸·丙', 'reason': '七杀当令，甲己合化，癸水润土'},
    ('己', '辰'): {'用神': '丙·癸·甲', 'reason': '杂气印格，先丙后癸'},
    ('己', '巳'): {'用神': '癸·丙', 'reason': '调候为先，癸水为主'},
    ('己', '午'): {'用神': '癸·丙', 'reason': '夏土燥裂，专用癸水'},
    ('己', '未'): {'用神': '癸·丙', 'reason': '炎夏湿土，专取癸水滋润'},
    ('己', '申'): {'用神': '丙·癸', 'reason': '伤官当令，丙暖癸润'},
    ('己', '酉'): {'用神': '丙·癸', 'reason': '食神当令，丙照癸润'},
    ('己', '戌'): {'用神': '甲·癸·丙', 'reason': '土旺用甲疏'},
    ('己', '亥'): {'用神': '丙·甲·戊', 'reason': '土虚水旺，专用丙火'},
    ('己', '子'): {'用神': '丙·甲·戊', 'reason': '严寒之土，无丙不生'},
    ('己', '丑'): {'用神': '丙·甲·戊', 'reason': '冬土冻结，丙火为先'},

    # ---------- 庚金十二月 ----------
    ('庚', '寅'): {'用神': '戊·甲·壬·丙·丁', 'reason': '木旺火相，戊土生金，丙暖丁炼'},
    ('庚', '卯'): {'用神': '丁·甲·庚·丙', 'reason': '正财当令，丁火炼金，甲木为薪'},
    ('庚', '辰'): {'用神': '甲·丁·壬·癸', 'reason': '土旺生金，甲木疏土，丁火炼之'},
    ('庚', '巳'): {'用神': '壬·戊·丙·丁', 'reason': '建禄之月，壬水为主，戊土制壬'},
    ('庚', '午'): {'用神': '壬·癸', 'reason': '炎夏火旺，专用壬癸制火'},
    ('庚', '未'): {'用神': '丁·甲·癸', 'reason': '湿土生金，丁火炼之'},
    ('庚', '申'): {'用神': '丁·甲', 'reason': '建禄之月，专用丁火，甲木为薪'},
    ('庚', '酉'): {'用神': '丁·甲·丙', 'reason': '阳刃当令，专用丁火炼锋'},
    ('庚', '戌'): {'用神': '甲·壬', 'reason': '土厚埋金，先甲疏土'},
    ('庚', '亥'): {'用神': '丁·丙', 'reason': '寒金待火，丁丙并用'},
    ('庚', '子'): {'用神': '丁·甲·丙', 'reason': '伤官当令，丁火为暖，甲木为薪'},
    ('庚', '丑'): {'用神': '丙·丁·甲', 'reason': '严冬之金，丙暖丁炼'},

    # ---------- 辛金十二月 ----------
    ('辛', '寅'): {'用神': '己·壬·庚', 'reason': '正财当令，己土生身，壬水洗淘'},
    ('辛', '卯'): {'用神': '壬·甲', 'reason': '偏财当令，壬水淘洗，甲木疏土'},
    ('辛', '辰'): {'用神': '壬·甲', 'reason': '正印当令，专用壬水'},
    ('辛', '巳'): {'用神': '壬·甲·癸', 'reason': '调候为急，壬水洗金'},
    ('辛', '午'): {'用神': '壬·己·癸', 'reason': '夏金喜水，专用壬水'},
    ('辛', '未'): {'用神': '壬·庚·甲', 'reason': '湿土埋金，壬水淘洗'},
    ('辛', '申'): {'用神': '壬·甲·戊', 'reason': '建禄之月，壬水洗金，甲木疏土'},
    ('辛', '酉'): {'用神': '壬·甲', 'reason': '阳刃当令，专用壬水'},
    ('辛', '戌'): {'用神': '壬·甲', 'reason': '土厚埋金，壬水甲木并用'},
    ('辛', '亥'): {'用神': '壬·丙', 'reason': '伤官当令，专用壬水，丙火调候'},
    ('辛', '子'): {'用神': '丙·壬·戊·甲', 'reason': '寒金喜暖，丙火为主'},
    ('辛', '丑'): {'用神': '丙·壬·戊·己', 'reason': '严冬冻金，先丙后壬'},

    # ---------- 壬水十二月 ----------
    ('壬', '寅'): {'用神': '庚·丙·戊', 'reason': '木旺水弱，专用庚金生身'},
    ('壬', '卯'): {'用神': '戊·辛·庚', 'reason': '伤官当令，戊土制水，辛金生水'},
    ('壬', '辰'): {'用神': '甲·庚', 'reason': '杂气七杀格，先甲后庚'},
    ('壬', '巳'): {'用神': '壬·辛·庚·癸', 'reason': '财杀两旺，比劫帮身'},
    ('壬', '午'): {'用神': '癸·庚·辛', 'reason': '炎夏水涸，专用癸水比劫'},
    ('壬', '未'): {'用神': '辛·甲·癸', 'reason': '土旺水弱，辛金生身，甲木疏土'},
    ('壬', '申'): {'用神': '戊·丁', 'reason': '偏印当令，先戊后丁'},
    ('壬', '酉'): {'用神': '甲·庚', 'reason': '正印当令，专用甲木泄水'},
    ('壬', '戌'): {'用神': '甲·丙', 'reason': '土厚水弱，甲木疏土，丙火调候'},
    ('壬', '亥'): {'用神': '戊·庚·丙', 'reason': '建禄之月，专用戊土制水'},
    ('壬', '子'): {'用神': '戊·丙', 'reason': '阳刃当令，戊土制水，丙火调候'},
    ('壬', '丑'): {'用神': '丙·丁·甲', 'reason': '严冬之水，专用丙火解冻'},

    # ---------- 癸水十二月 ----------
    ('癸', '寅'): {'用神': '辛·丙', 'reason': '木旺泄水，专用辛金生身'},
    ('癸', '卯'): {'用神': '庚·辛', 'reason': '食神当令，庚辛金为印'},
    ('癸', '辰'): {'用神': '丙·辛·甲', 'reason': '杂气正官，丙火调候，辛金生水'},
    ('癸', '巳'): {'用神': '辛·庚', 'reason': '正财当令，辛金生身，庚金为辅'},
    ('癸', '午'): {'用神': '庚·壬·癸', 'reason': '炎夏水弱，专用庚金生水'},
    ('癸', '未'): {'用神': '庚·辛·壬·癸', 'reason': '七杀当令，庚辛生身，壬癸比劫帮扶'},
    ('癸', '申'): {'用神': '丁·甲', 'reason': '正印当令，丁火配丁火炼金'},
    ('癸', '酉'): {'用神': '辛·丙', 'reason': '偏印当令，专用辛金，丙火调候'},
    ('癸', '戌'): {'用神': '辛·甲·壬·癸', 'reason': '土旺克水，辛金生身'},
    ('癸', '亥'): {'用神': '庚·辛·戊·丁', 'reason': '建禄之月，专用庚辛金'},
    ('癸', '子'): {'用神': '丙·辛', 'reason': '阳刃当令，专用丙火调候'},
    ('癸', '丑'): {'用神': '丙·丁', 'reason': '严冬冻水，专用丙丁火解冻'},
}


# ============================================================
# 十神计算（用于神煞推导）
# ============================================================

def calc_shishen_gan(day_gan, other_gan):
    """十神计算：以日干为我，判断其他天干的十神关系"""
    if day_gan == other_gan:
        return '比肩'
    me_wx = GAN_WX[day_gan]
    other_wx = GAN_WX[other_gan]
    me_yang = GAN_YINYANG[day_gan] == '阳'
    other_yang = GAN_YINYANG[other_gan] == '阳'
    same_polar = me_yang == other_yang

    sheng = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
    ke = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}

    if sheng[other_wx] == me_wx:  # 它生我
        return '偏印' if same_polar else '正印'
    if sheng[me_wx] == other_wx:  # 我生它
        return '食神' if same_polar else '伤官'
    if me_wx == other_wx:
        return '比肩' if same_polar else '劫财'
    if ke[me_wx] == other_wx:  # 我克它
        return '偏财' if same_polar else '正财'
    if ke[other_wx] == me_wx:  # 它克我
        return '七杀' if same_polar else '正官'
    return ''


# ============================================================
# 神煞模块（17 种）
# 每个函数返回 True / False，调用方按四柱分别判定
# 古籍出处：《三命通会》《神峰通考》《渊海子平》《珞琭子三命消息赋》
# ============================================================

def is_tianyi_guiren(day_gan, zhi):
    """天乙贵人：以日干查地支。
    甲戊庚-丑未，乙己-子申，丙丁-亥酉，壬癸-巳卯，辛-午寅"""
    table = {
        '甲': ('丑', '未'), '戊': ('丑', '未'), '庚': ('丑', '未'),
        '乙': ('子', '申'), '己': ('子', '申'),
        '丙': ('亥', '酉'), '丁': ('亥', '酉'),
        '壬': ('巳', '卯'), '癸': ('巳', '卯'),
        '辛': ('午', '寅'),
    }
    return zhi in table.get(day_gan, ())


def is_wenchang(day_gan, zhi):
    """文昌贵人：以日干查地支，主食神临官之位（驿马前一位之文）。
    甲-巳，乙-午，丙戊-申，丁己-酉，庚-亥，辛-子，壬-寅，癸-卯"""
    table = {
        '甲': '巳', '乙': '午', '丙': '申', '戊': '申',
        '丁': '酉', '己': '酉', '庚': '亥', '辛': '子',
        '壬': '寅', '癸': '卯',
    }
    return zhi == table.get(day_gan)


def is_taiji_guiren(day_gan, zhi):
    """太极贵人：以日干查地支，主好玄学、信仰。
    甲乙-子午，丙丁-卯酉，戊己-辰戌丑未，庚辛-寅亥，壬癸-巳申"""
    table = {
        '甲': ('子', '午'), '乙': ('子', '午'),
        '丙': ('卯', '酉'), '丁': ('卯', '酉'),
        '戊': ('辰', '戌', '丑', '未'), '己': ('辰', '戌', '丑', '未'),
        '庚': ('寅', '亥'), '辛': ('寅', '亥'),
        '壬': ('巳', '申'), '癸': ('巳', '申'),
    }
    return zhi in table.get(day_gan, ())


def is_yuede_guiren(month_zhi, gan):
    """月德贵人：以月支查天干。
    寅午戌月-丙，申子辰月-壬，亥卯未月-甲，巳酉丑月-庚"""
    table = {
        ('寅', '午', '戌'): '丙',
        ('申', '子', '辰'): '壬',
        ('亥', '卯', '未'): '甲',
        ('巳', '酉', '丑'): '庚',
    }
    for group, target in table.items():
        if month_zhi in group:
            return gan == target
    return False


def is_yuede_he(month_zhi, gan):
    """月德合：月德贵人的合干。
    寅午戌-辛（丙辛合），申子辰-丁（壬丁合），亥卯未-己（甲己合），巳酉丑-乙（庚乙合）"""
    table = {
        ('寅', '午', '戌'): '辛',
        ('申', '子', '辰'): '丁',
        ('亥', '卯', '未'): '己',
        ('巳', '酉', '丑'): '乙',
    }
    for group, target in table.items():
        if month_zhi in group:
            return gan == target
    return False


def is_tiande_guiren(month_zhi, gan_or_zhi):
    """天德贵人：以月支查。
    正月-丁，二月-申，三月-壬，四月-辛，五月-亥，六月-甲，
    七月-癸，八月-寅，九月-丙，十月-乙，十一月-巳，十二月-庚"""
    table = {
        '寅': '丁', '卯': '申', '辰': '壬', '巳': '辛',
        '午': '亥', '未': '甲', '申': '癸', '酉': '寅',
        '戌': '丙', '亥': '乙', '子': '巳', '丑': '庚',
    }
    return gan_or_zhi == table.get(month_zhi)


def is_tiande_he(month_zhi, gan):
    """天德合：天德的合干（仅对天干 entry 适用）。
    丁合壬，壬合丁，辛合丙，甲合己，癸合戊，丙合辛，乙合庚，庚合乙"""
    he_map = {'甲': '己', '己': '甲', '乙': '庚', '庚': '乙',
              '丙': '辛', '辛': '丙', '丁': '壬', '壬': '丁',
              '戊': '癸', '癸': '戊'}
    base = {
        '寅': '丁', '辰': '壬', '巳': '辛', '未': '甲',
        '戌': '丙', '亥': '乙', '丑': '庚', '申': '癸',
    }
    target = base.get(month_zhi)
    if target is None:
        return False
    return gan == he_map.get(target)


def is_taohua(base_zhi, zhi):
    """桃花（咸池）：以年支或日支三合局首位前一位查。
    申子辰-酉，寅午戌-卯，巳酉丑-午，亥卯未-子"""
    table = {
        ('申', '子', '辰'): '酉',
        ('寅', '午', '戌'): '卯',
        ('巳', '酉', '丑'): '午',
        ('亥', '卯', '未'): '子',
    }
    for group, target in table.items():
        if base_zhi in group:
            return zhi == target
    return False


def is_yima(base_zhi, zhi):
    """驿马：以年支或日支三合局对冲查。
    申子辰-寅，寅午戌-申，巳酉丑-亥，亥卯未-巳"""
    table = {
        ('申', '子', '辰'): '寅',
        ('寅', '午', '戌'): '申',
        ('巳', '酉', '丑'): '亥',
        ('亥', '卯', '未'): '巳',
    }
    for group, target in table.items():
        if base_zhi in group:
            return zhi == target
    return False


def is_hongyan(day_gan, zhi):
    """红艳煞：以日干查地支，主异性缘、感情桃花。
    甲乙-午，丙-寅，丁-未，戊己-辰，庚-戌，辛-酉，壬-子，癸-申"""
    table = {
        '甲': '午', '乙': '午', '丙': '寅', '丁': '未',
        '戊': '辰', '己': '辰', '庚': '戌', '辛': '酉',
        '壬': '子', '癸': '申',
    }
    return zhi == table.get(day_gan)


def is_huagai(base_zhi, zhi):
    """华盖：以年支或日支三合局末位查。
    申子辰-辰，寅午戌-戌，巳酉丑-丑，亥卯未-未"""
    table = {
        ('申', '子', '辰'): '辰',
        ('寅', '午', '戌'): '戌',
        ('巳', '酉', '丑'): '丑',
        ('亥', '卯', '未'): '未',
    }
    for group, target in table.items():
        if base_zhi in group:
            return zhi == target
    return False


def is_guchen(year_zhi, zhi):
    """孤辰：以年支查，主孤独。
    亥子丑-寅，寅卯辰-巳，巳午未-申，申酉戌-亥"""
    table = {
        ('亥', '子', '丑'): '寅',
        ('寅', '卯', '辰'): '巳',
        ('巳', '午', '未'): '申',
        ('申', '酉', '戌'): '亥',
    }
    for group, target in table.items():
        if year_zhi in group:
            return zhi == target
    return False


def is_guasu(year_zhi, zhi):
    """寡宿：以年支查，主孤独。
    亥子丑-戌，寅卯辰-丑，巳午未-辰，申酉戌-未"""
    table = {
        ('亥', '子', '丑'): '戌',
        ('寅', '卯', '辰'): '丑',
        ('巳', '午', '未'): '辰',
        ('申', '酉', '戌'): '未',
    }
    for group, target in table.items():
        if year_zhi in group:
            return zhi == target
    return False


def is_wangshen(base_zhi, zhi):
    """亡神：以年支或日支三合局帝旺前一位查（即三合中位）。
    申子辰-亥，寅午戌-巳，巳酉丑-申，亥卯未-寅"""
    table = {
        ('申', '子', '辰'): '亥',
        ('寅', '午', '戌'): '巳',
        ('巳', '酉', '丑'): '申',
        ('亥', '卯', '未'): '寅',
    }
    for group, target in table.items():
        if base_zhi in group:
            return zhi == target
    return False


def is_jiesha(base_zhi, zhi):
    """劫煞：以年支或日支三合局驿马对冲再退一位查。
    申子辰-巳，寅午戌-亥，巳酉丑-寅，亥卯未-申"""
    table = {
        ('申', '子', '辰'): '巳',
        ('寅', '午', '戌'): '亥',
        ('巳', '酉', '丑'): '寅',
        ('亥', '卯', '未'): '申',
    }
    for group, target in table.items():
        if base_zhi in group:
            return zhi == target
    return False


def is_zaisha(base_zhi, zhi):
    """灾煞：以年支或日支三合局五行对冲方位查（劫煞前一位）。
    申子辰-午，寅午戌-子，巳酉丑-卯，亥卯未-酉"""
    table = {
        ('申', '子', '辰'): '午',
        ('寅', '午', '戌'): '子',
        ('巳', '酉', '丑'): '卯',
        ('亥', '卯', '未'): '酉',
    }
    for group, target in table.items():
        if base_zhi in group:
            return zhi == target
    return False


def is_jinyu(day_gan, zhi):
    """金舆：以日干查地支，主妻财、车马，居于禄前二位。
    甲-辰，乙-巳，丙-未，丁-申，戊-未，己-申，庚-戌，辛-亥，壬-丑，癸-寅"""
    table = {
        '甲': '辰', '乙': '巳', '丙': '未', '丁': '申',
        '戊': '未', '己': '申', '庚': '戌', '辛': '亥',
        '壬': '丑', '癸': '寅',
    }
    return zhi == table.get(day_gan)


def is_guoyin(day_gan, zhi):
    """国印：以日干查地支，主权威、印章。
    甲-戌，乙-亥，丙-丑，丁-寅，戊-丑，己-寅，庚-辰，辛-巳，壬-未，癸-申"""
    table = {
        '甲': '戌', '乙': '亥', '丙': '丑', '丁': '寅',
        '戊': '丑', '己': '寅', '庚': '辰', '辛': '巳',
        '壬': '未', '癸': '申',
    }
    return zhi == table.get(day_gan)


def is_liuxia(day_gan, zhi):
    """流霞：以日干查地支，女命主血灾或风流。
    甲-酉，乙-戌，丙-未，丁-申，戊-巳，己-午，庚-辰，辛-卯，壬-亥，癸-寅"""
    table = {
        '甲': '酉', '乙': '戌', '丙': '未', '丁': '申',
        '戊': '巳', '己': '午', '庚': '辰', '辛': '卯',
        '壬': '亥', '癸': '寅',
    }
    return zhi == table.get(day_gan)


def calc_shensha(pillars_zhi, pillars_gan, day_gan, year_zhi, day_zhi, month_zhi):
    """按四柱分列计算 17 种神煞。
    pillars_zhi / pillars_gan：[年, 月, 日, 时]
    返回 {柱名: [神煞名...]}
    """
    pillar_names = ['年柱', '月柱', '日柱', '时柱']
    result = {name: [] for name in pillar_names}

    # 以日干 / 月支 / 年支 / 日支为不同神煞的查询基准
    for i, (zhi, gan) in enumerate(zip(pillars_zhi, pillars_gan)):
        name = pillar_names[i]

        # 以日干查地支类
        if is_tianyi_guiren(day_gan, zhi):
            result[name].append('天乙贵人')
        if is_wenchang(day_gan, zhi):
            result[name].append('文昌贵人')
        if is_taiji_guiren(day_gan, zhi):
            result[name].append('太极贵人')
        if is_hongyan(day_gan, zhi):
            result[name].append('红艳煞')
        if is_jinyu(day_gan, zhi):
            result[name].append('金舆')
        if is_guoyin(day_gan, zhi):
            result[name].append('国印')
        if is_liuxia(day_gan, zhi):
            result[name].append('流霞')

        # 月德 / 天德（既查天干也查地支）
        if is_yuede_guiren(month_zhi, gan):
            result[name].append('月德贵人')
        if is_yuede_he(month_zhi, gan):
            result[name].append('月德合')
        if is_tiande_guiren(month_zhi, gan):
            result[name].append('天德贵人')
        if is_tiande_guiren(month_zhi, zhi):
            result[name].append('天德贵人')  # 天德也可对地支
        if is_tiande_he(month_zhi, gan):
            result[name].append('天德合')

        # 以年支查（孤辰寡宿）
        if is_guchen(year_zhi, zhi):
            result[name].append('孤辰')
        if is_guasu(year_zhi, zhi):
            result[name].append('寡宿')

        # 以年支或日支为基准的三合系列：取并集（任一基准命中即可）
        for base in (year_zhi, day_zhi):
            if is_taohua(base, zhi) and '桃花' not in result[name]:
                result[name].append('桃花')
            if is_yima(base, zhi) and '驿马' not in result[name]:
                result[name].append('驿马')
            if is_huagai(base, zhi) and '华盖' not in result[name]:
                result[name].append('华盖')
            if is_wangshen(base, zhi) and '亡神' not in result[name]:
                result[name].append('亡神')
            if is_jiesha(base, zhi) and '劫煞' not in result[name]:
                result[name].append('劫煞')
            if is_zaisha(base, zhi) and '灾煞' not in result[name]:
                result[name].append('灾煞')

    # 去重（保持顺序）
    for k in result:
        seen, dedup = set(), []
        for s in result[k]:
            if s not in seen:
                seen.add(s)
                dedup.append(s)
        result[k] = dedup
    return result


# ============================================================
# 调候用神查询
# ============================================================

def get_diaohou(day_gan, month_zhi):
    """调候用神查询：120 组完整覆盖，无 fallback"""
    key = (day_gan, month_zhi)
    if key in DIAOHOU_TABLE:
        return dict(DIAOHOU_TABLE[key])
    return {'用神': '未定', 'reason': '查表失败'}


# ============================================================
# 跨节气警告
# ============================================================

def calc_jieqi_warning(solar):
    """检测出生时刻距上下"节"的精确分钟数，附另一可能月柱"""
    lunar = solar.getLunar()
    prev_jq = lunar.getPrevJieQi()
    next_jq = lunar.getNextJieQi()

    # 仅关心"节"（不取"气"）—— 节决定月柱边界
    # JieQi 对象的 isJie() / isQi() 区分
    # 寻找最近的"节"（前 / 后）
    def _to_dt(jq):
        s = jq.getSolar()
        return datetime(s.getYear(), s.getMonth(), s.getDay(),
                        s.getHour(), s.getMinute(), s.getSecond())

    birth_dt = datetime(solar.getYear(), solar.getMonth(), solar.getDay(),
                        solar.getHour(), solar.getMinute(), solar.getSecond())

    # prev_jq / next_jq 取自 JieQiTable，可能是节或气，需自己筛
    jq_table = lunar.getJieQiTable()
    nearest = []
    for name, jq_solar in jq_table.items():
        jq_dt = datetime(jq_solar.getYear(), jq_solar.getMonth(), jq_solar.getDay(),
                         jq_solar.getHour(), jq_solar.getMinute(), jq_solar.getSecond())
        delta = (birth_dt - jq_dt).total_seconds() / 60  # 分钟
        nearest.append((name, jq_dt, delta))

    # 找最接近的（绝对值最小的）"节"
    # lunar_python 节气表里"节"的中文名：立春惊蛰清明立夏芒种小暑立秋白露寒露立冬大雪小寒
    JIE_NAMES = {'立春', '惊蛰', '清明', '立夏', '芒种', '小暑',
                 '立秋', '白露', '寒露', '立冬', '大雪', '小寒'}
    jie_only = [(n, dt, d) for (n, dt, d) in nearest if n in JIE_NAMES]
    if not jie_only:
        return None
    jie_only.sort(key=lambda x: abs(x[2]))
    name, jq_dt, delta = jie_only[0]
    if abs(delta) >= 15:  # 阈值：15 分钟
        return None

    sign = '+' if delta >= 0 else ''
    direction = '已过' if delta >= 0 else '未到'
    return {
        f'距{name}': f'{sign}{int(delta)} 分钟（{direction}）',
        '提示': f'距{name}仅 {abs(int(delta))} 分钟，月柱可能存在边界争议，建议双盘对比',
        '_jie_name': name,
        '_delta_minutes': int(delta),
    }


# ============================================================
# 早 / 夜子时切换
# ============================================================

def apply_zi_hour_rule(solar, rule):
    """根据 zi-hour-rule 调整 Solar 对象用于排盘。
    - early（默认推荐）：23:00-00:59 全部归当日早子时
        实现：lunar_python 默认会将 23:00+ 归次日；要"归当日"，
        把 23:xx 视为当日 23 时（保留），但日柱按出生日（不变），其实
        lunar_python 在 23:00-24:00 区间会自动给出"当日日柱 + 子时柱"
        即"子时柱由出生日次日干推"，与"早子时归当日"流派一致，
        所以默认无需调整。
    - late（夜子时归次日）：23:00-24:00 视为次日 0 点之前，日柱按次日推
        实现：将 Solar 时刻整体 +1 小时后传给 lunar_python，得到次日的
        日柱与子时柱（这是"夜子时"流派的处理方式）。
    返回 (用于排盘的 solar, 子时调整说明)
    """
    h = solar.getHour()
    if h != 23:
        return solar, None

    if rule == 'late':
        # 23:xx + 1 小时 = 次日 0:xx —— 由 datetime 处理跨月 / 跨年 / 闰
        dt = datetime(solar.getYear(), solar.getMonth(), solar.getDay(),
                      23, solar.getMinute(), solar.getSecond()) + timedelta(hours=1)
        next_solar = Solar.fromYmdHms(dt.year, dt.month, dt.day,
                                      0, dt.minute, dt.second)
        return next_solar, '夜子时归次日：日柱按次日推（--zi-hour-rule=late）'

    # early：明确告知用户当前规则；lunar_python 默认即为"早子时归当日"
    return solar, '早子时归当日：23:00 后日柱仍按当日（--zi-hour-rule=early，默认）'


# ============================================================
# 性格映射提示
# ============================================================

def build_personality_mapping(dm, month_zhi, wx_pct, pillars, diaohou):
    """构造性格映射提示（v3 哲学：八字是性格的能量基础）"""
    # 日主意象
    dm_image = DM_IMAGE.get(dm, '未知')

    # 格局倾向：以月支本气十神为格局主线索
    month_benqi = HIDDEN_WEIGHTS[month_zhi][0][0]
    if month_benqi == dm:
        geju = '建禄 / 月刃格 → 自我能量充沛，倾向 Ti / Fi 主导'
    else:
        ss = calc_shishen_gan(dm, month_benqi)
        ss_to_jung = {
            '正官': '正官格 → 倾向 Te 规则秩序 / Si 守序',
            '七杀': '七杀格 → 倾向 Te 强势执行 / Se 应激',
            '正印': '正印格 → 倾向 Ni 内倾直觉 / Si 内倾感觉',
            '偏印': '偏印格 → 倾向 Ni 直觉 / Ti 内倾思考',
            '正财': '正财格 → 倾向 Te 务实经营 / Si 稳定',
            '偏财': '偏财格 → 倾向 Se 资源调度 / Te 外倾思考',
            '食神': '食神格 → 倾向 Fe 表达 / Se 享受当下',
            '伤官': '伤官格 → 倾向 Ne 创造 / Ti 锋芒批判',
            '比肩': '比肩格 → 倾向 Ti 独立 / Fi 自我认同',
            '劫财': '劫财格 → 倾向 Te 竞争 / Se 行动力',
        }
        geju = ss_to_jung.get(ss, f'{ss}格 → 待映射')

    # 五行偏强 / 偏弱
    sorted_wx = sorted(wx_pct.items(), key=lambda x: -x[1])
    strongest = sorted_wx[0]
    weakest = sorted_wx[-1]

    wx_to_func = {
        '木': ('Ne 外倾直觉', 'Si 内倾感觉'),
        '火': ('Fe 外倾情感', 'Ti 内倾思考'),
        '土': ('Si 内倾感觉', 'Ne 外倾直觉'),
        '金': ('Te 外倾思考', 'Fi 内倾情感'),
        '水': ('Ni 内倾直觉', 'Se 外倾感觉'),
    }
    strong_func = wx_to_func.get(strongest[0], ('', ''))[0]
    weak_func = wx_to_func.get(weakest[0], ('', ''))[1]

    # 调候用神 → 待整合的功能（劣势线索）
    yongshen = diaohou.get('用神', '')
    main_use = yongshen.split('·')[0] if '·' in yongshen else yongshen
    main_use_wx = GAN_WX.get(main_use, '')
    diaohou_hint = ''
    if main_use_wx:
        ys_funcs = wx_to_func.get(main_use_wx, ('', ''))[0]
        diaohou_hint = f'{main_use}（{main_use_wx}）→ 暗示 {ys_funcs} 待整合 / 需补充'

    return {
        '日主意象': f'{dm}（{GAN_WX[dm]}）· {dm_image}',
        '格局倾向': geju,
        '五行偏强': f'{strongest[0]} {strongest[1]}% → 印证 {strong_func} 主导可能性',
        '五行薄弱': f'{weakest[0]} {weakest[1]}% → 物质 / 心理 {weakest[0]} 维度薄弱，与 {weak_func} 弱位呼应',
        '调候用神': diaohou_hint or f'{yongshen} → 命局调候线索',
        '_说明': '本字段为命书第一阶段「性格画像」的线索池，最终映射由 jung_calc.py 主导，本表仅做交叉印证',
    }


# ============================================================
# 主计算函数
# ============================================================

def calc_bazi(year, month, day, hour, minute, gender,
              zi_hour_rule='early', true_solar_corrected=False):
    """主计算函数：用 lunar_python 排盘 + v3 增强模块"""
    raw_solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    solar, zi_note = apply_zi_hour_rule(raw_solar, zi_hour_rule)

    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    # 四柱
    pillar_data = [
        ('年柱', ec.getYear(), ec.getYearGan(), ec.getYearZhi(), ec.getYearNaYin()),
        ('月柱', ec.getMonth(), ec.getMonthGan(), ec.getMonthZhi(), ec.getMonthNaYin()),
        ('日柱', ec.getDay(), ec.getDayGan(), ec.getDayZhi(), ec.getDayNaYin()),
        ('时柱', ec.getTime(), ec.getTimeGan(), ec.getTimeZhi(), ec.getTimeNaYin()),
    ]

    # 十神
    ssg = [None, ec.getYearShiShenGan(), ec.getMonthShiShenGan(), '日主', ec.getTimeShiShenGan()]
    ssz = [None, ec.getYearShiShenZhi(), ec.getMonthShiShenZhi(), ec.getDayShiShenZhi(), ec.getTimeShiShenZhi()]

    pillars = []
    for i, (name, gz, gan, zhi, nayin) in enumerate(pillar_data, 1):
        pillars.append({
            '柱': name,
            '干支': gz,
            '天干': gan,
            '地支': zhi,
            '纳音': nayin,
            '天干十神': ssg[i],
            '地支藏干十神': ssz[i],
        })

    dm = ec.getDayGan()
    day_zhi = ec.getDayZhi()
    month_zhi = ec.getMonthZhi()
    year_zhi = ec.getYearZhi()

    # 起运（lunar_python 精确计算）
    yun_gender = 1 if gender == 'm' else 0
    yun = ec.getYun(yun_gender)
    qi_yun = {
        '起运': f'{yun.getStartYear()}年{yun.getStartMonth()}月{yun.getStartDay()}天',
        '起运公历': yun.getStartSolar().toYmd(),
    }

    # 大运
    da_yun_list = []
    for da in yun.getDaYun()[:9]:
        gz = da.getGanZhi()
        if gz:
            da_yun_list.append({
                '干支': gz,
                '起始年龄': da.getStartAge(),
                '终止年龄': da.getEndAge(),
                '起始公历年': da.getStartYear(),
                '终止公历年': da.getEndYear(),
            })

    # 五行权重统计（藏干）
    wx_count = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
    for _, _, gan, zhi, _ in pillar_data:
        wx_count[GAN_WX[gan]] += 1.0
        for h, w in HIDDEN_WEIGHTS[zhi]:
            wx_count[GAN_WX[h]] += w
    total = sum(wx_count.values())
    wx_pct = {k: round(v / total * 100, 1) for k, v in wx_count.items()}

    # 调候用神
    diaohou = get_diaohou(dm, month_zhi)

    # 神煞
    pillars_zhi = [p[3] for p in pillar_data]
    pillars_gan = [p[2] for p in pillar_data]
    shensha = calc_shensha(pillars_zhi, pillars_gan, dm, year_zhi, day_zhi, month_zhi)

    # 跨节气警告 —— 计算需基于原始时刻
    jieqi_warn = calc_jieqi_warning(raw_solar)
    if jieqi_warn:
        # 计算另一可能月柱（用上一节气前一刻的月柱 vs 下一节气后一刻的月柱）
        jie_name = jieqi_warn.pop('_jie_name', None)
        delta = jieqi_warn.pop('_delta_minutes', 0)
        # 如果出生在节气后 < 15 分钟，另一可能月柱 = 节气前的旧月柱
        # 如果出生在节气前 < 15 分钟，另一可能月柱 = 节气后的新月柱
        try:
            if delta >= 0:
                shift_dt = datetime(raw_solar.getYear(), raw_solar.getMonth(), raw_solar.getDay(),
                                    raw_solar.getHour(), raw_solar.getMinute()) - timedelta(minutes=abs(delta) + 5)
            else:
                shift_dt = datetime(raw_solar.getYear(), raw_solar.getMonth(), raw_solar.getDay(),
                                    raw_solar.getHour(), raw_solar.getMinute()) + timedelta(minutes=abs(delta) + 5)
            alt_solar = Solar.fromYmdHms(shift_dt.year, shift_dt.month, shift_dt.day,
                                         shift_dt.hour, shift_dt.minute, 0)
            alt_month = alt_solar.getLunar().getEightChar().getMonth()
            jieqi_warn['另一可能月柱'] = alt_month
        except Exception:
            pass

    # 性格映射提示
    personality_hint = build_personality_mapping(dm, month_zhi, wx_pct, pillars, diaohou)

    # sxtwl 交叉校验
    sxtwl_check = None
    if HAS_SXTWL:
        try:
            d = sxtwl.fromSolar(year, month, day)
            sx_year_gz = HS[d.getYearGZ().tg] + EB[d.getYearGZ().dz]
            sx_month_gz = HS[d.getMonthGZ().tg] + EB[d.getMonthGZ().dz]
            sx_day_gz = HS[d.getDayGZ().tg] + EB[d.getDayGZ().dz]
            sxtwl_check = {
                '年柱': sx_year_gz, '月柱': sx_month_gz, '日柱': sx_day_gz,
                '一致': (sx_year_gz == ec.getYear() and
                        sx_month_gz == ec.getMonth() and
                        sx_day_gz == ec.getDay()),
            }
        except Exception:
            sxtwl_check = {'error': 'sxtwl 校验失败'}

    out = {
        '公历': raw_solar.toYmdHms(),
        '农历': lunar.toString(),
        '真太阳时状态': '已校正' if true_solar_corrected else '未校正（输入为标准时间）',
        '子时规则': zi_hour_rule + ('（早子时归当日）' if zi_hour_rule == 'early'
                                  else '（夜子时归次日）'),
        '子时调整说明': zi_note,
        '四柱': pillars,
        '日主': {'天干': dm, '五行': GAN_WX[dm], '意象': DM_IMAGE.get(dm, '未知')},
        '五行权重': {k: round(v, 2) for k, v in wx_count.items()},
        '五行比例': wx_pct,
        '调候用神': diaohou,
        '神煞': shensha,
        '起运': qi_yun,
        '大运': da_yun_list,
        '空亡': {
            '年柱空亡': ec.getYearXunKong(),
            '日柱空亡': ec.getDayXunKong(),
        },
        '性格映射提示': personality_hint,
        'sxtwl_交叉校验': sxtwl_check,
    }
    if jieqi_warn:
        out['节气警告'] = jieqi_warn
    return out


# ============================================================
# CLI
# ============================================================

def parse_args(argv):
    """解析 CLI 参数（避免依赖 argparse 模块以保持轻量）"""
    args = {'zi_hour_rule': 'early', 'true_solar_corrected': False}
    positional = []
    for a in argv:
        if a.startswith('--zi-hour-rule='):
            v = a.split('=', 1)[1]
            if v in ('early', 'late'):
                args['zi_hour_rule'] = v
        elif a.startswith('--true-solar-time-corrected='):
            v = a.split('=', 1)[1]
            args['true_solar_corrected'] = (v == 'yes')
        else:
            positional.append(a)
    return positional, args


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    positional, opts = parse_args(sys.argv[1:])
    date_str, time_str, gender = positional[0], positional[1], positional[2].lower()
    year, month, day = map(int, date_str.split('-'))
    hour, minute = map(int, time_str.split(':'))

    result = calc_bazi(year, month, day, hour, minute, gender,
                       zi_hour_rule=opts['zi_hour_rule'],
                       true_solar_corrected=opts['true_solar_corrected'])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
