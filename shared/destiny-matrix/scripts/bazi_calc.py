#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按统一 time_context 计算四柱及明确请求的流年/流月数据。

节气年/月使用固定 UTC+08:00；日/时使用输入经度对应的地方视太阳时。
子时换日口径通过 ``--zi-hour-rule midnight|zi_start`` 显式选择。
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

def _solar_datetime(solar):
    second = float(solar.getSecond())
    whole = int(second)
    return datetime(solar.getYear(), solar.getMonth(), solar.getDay(),
                    solar.getHour(), solar.getMinute(), whole,
                    round((second - whole) * 1_000_000))


def calc_jieqi_warning(term_solar):
    """在固定 UTC+8 轴上核对出生瞬间与月令节的距离。"""
    table = term_solar.getLunar().getJieQiTable()
    jie_names = {"立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
                 "立秋", "白露", "寒露", "立冬", "大雪", "小寒"}
    birth = _solar_datetime(term_solar)
    moments = []
    for name, solar in table.items():
        if name in jie_names:
            moment = _solar_datetime(solar)
            moments.append((name, moment, (birth - moment).total_seconds()))
    if not moments:
        return None
    name, moment, delta = min(moments, key=lambda row: abs(row[2]))
    if abs(delta) >= 15 * 60:
        return None
    before_dt, after_dt = moment - timedelta(seconds=1), moment + timedelta(seconds=1)
    before = Solar.fromYmdHms(before_dt.year, before_dt.month, before_dt.day,
                              before_dt.hour, before_dt.minute, before_dt.second)
    after = Solar.fromYmdHms(after_dt.year, after_dt.month, after_dt.day,
                             after_dt.hour, after_dt.minute, after_dt.second)
    return {
        "节气": name, "有符号差秒": delta,
        "差值方向": "节后" if delta >= 0 else "节前",
        "边界前月柱": before.getLunar().getEightChar().getMonth(),
        "边界后月柱": after.getLunar().getEightChar().getMonth(),
        "精度": "lunar-python 节气表精度",
    }


# ============================================================
# 早 / 夜子时切换
# ============================================================

def _datetime_from_context(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"无效 time_context datetime: {value!r}") from exc



# ============================================================
# 主计算函数
# ============================================================

JIE_NAMES = {"立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
             "立秋", "白露", "寒露", "立冬", "大雪", "小寒", "DA_XUE"}


def _lichun_moment(year):
    """Return the lunar-python solar-term instant in its documented BJT table."""
    table = Solar.fromYmdHms(year, 2, 4, 12, 0, 0).getLunar().getJieQiTable()
    term = table.get("立春")
    if term is None:
        raise ValueError(f"无法取得 {year} 年立春时刻")
    return _solar_datetime(term)


def _term_months_in_gregorian_month(year, month):
    """Expose Gregorian scope and the actual Jie-bounded month-pillar segments."""

    month_start = datetime(year, month, 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    month_end = datetime(next_year, next_month, 1)
    table = Solar.fromYmdHms(year, month, 15, 12, 0, 0).getLunar().getJieQiTable()
    moments = sorted({
        _solar_datetime(term) for name, term in table.items()
        if name in JIE_NAMES and month_start < _solar_datetime(term) < month_end
    })
    boundaries = [month_start, *moments, month_end]
    segments = []
    for start, end in zip(boundaries, boundaries[1:]):
        marker = start + timedelta(seconds=1)
        solar = Solar.fromYmdHms(marker.year, marker.month, marker.day,
                                 marker.hour, marker.minute, marker.second)
        segments.append({
            "month_pillar": solar.getLunar().getEightChar().getMonth(),
            "validity": {
                "start": start.isoformat(timespec="seconds") + "+08:00",
                "end": end.isoformat(timespec="seconds") + "+08:00",
                "timezone": "UTC+08:00",
            },
        })
    return {
        "gregorian_month": {
            "start": month_start.isoformat(timespec="seconds") + "+08:00",
            "end": month_end.isoformat(timespec="seconds") + "+08:00",
            "timezone": "UTC+08:00",
        },
        "solar_term_month_segments": segments,
    }


def calc_bazi(time_context, calculation_sex=None, *, zi_hour_rule="midnight",
              analysis_as_of=None, timing_request=None):
    """使用统一 time_context 计算四柱；节气年/月与地方视太阳日/时分轴。"""
    if zi_hour_rule not in {"midnight", "zi_start"}:
        raise ValueError("zi_hour_rule 只能是 midnight 或 zi_start")
    if time_context.get("precision") != "minute":
        from _common import candidate_contexts
        groups = {}
        for row in candidate_contexts(time_context):
            exact = calc_bazi(
                row["time_context"], calculation_sex,
                zi_hour_rule=zi_hour_rule, analysis_as_of=analysis_as_of,
                timing_request=timing_request,
            )
            source = exact.get("data")
            if not isinstance(source, dict):
                continue
            candidate_data = {
                key: value for key, value in source.items()
                if key not in {"公历", "节气时间轴", "起运", "大运", "流年",
                               "流月查询", "节气警告", "sxtwl_交叉校验"}
            }
            identity = json.dumps(candidate_data, ensure_ascii=False, sort_keys=True)
            candidate = groups.setdefault(identity, {
                "data": candidate_data, "validity": [],
                "limitations": ["起运/大运随具体出生瞬间变化，未用区间代表值代替"],
            })
            validity = row["validity"]
            if (candidate["validity"] and "start_utc" in validity
                    and candidate["validity"][-1].get("end_utc") == validity["start_utc"]):
                candidate["validity"][-1]["end_utc"] = validity["end_utc"]
            else:
                candidate["validity"].append(validity)
        return {
            "status": "partial", "data": None,
            "candidates": list(groups.values()),
            "limitations": ["非精确时刻；按地方视太阳小时、节气与DST边界列出离散四柱候选"],
        }
    term_dt = _datetime_from_context(time_context.get("term_datetime"))
    apparent_dt = _datetime_from_context(time_context.get("local_apparent_datetime"))
    from _common import local_solar_to_lunar
    term_solar = local_solar_to_lunar(term_dt)
    day_solar = local_solar_to_lunar(apparent_dt)
    term_ec = term_solar.getLunar().getEightChar()
    day_ec = day_solar.getLunar().getEightChar()
    sect = 1 if zi_hour_rule == "zi_start" else 2
    day_ec.setSect(sect)

    pillar_data = [
        ("年柱", term_ec.getYear(), term_ec.getYearGan(), term_ec.getYearZhi(),
         term_ec.getYearNaYin()),
        ("月柱", term_ec.getMonth(), term_ec.getMonthGan(), term_ec.getMonthZhi(),
         term_ec.getMonthNaYin()),
        ("日柱", day_ec.getDay(), day_ec.getDayGan(), day_ec.getDayZhi(),
         day_ec.getDayNaYin()),
        ("时柱", day_ec.getTime(), day_ec.getTimeGan(), day_ec.getTimeZhi(),
         day_ec.getTimeNaYin()),
    ]
    day_master = day_ec.getDayGan()
    pillars = []
    for name, gz, gan, zhi, nayin in pillar_data:
        hidden = [stem for stem, _weight in HIDDEN_WEIGHTS[zhi]]
        pillars.append({
            "柱": name, "干支": gz, "天干": gan, "地支": zhi, "纳音": nayin,
            "天干十神": "日主" if name == "日柱" else calc_shishen_gan(day_master, gan),
            "地支藏干十神": [calc_shishen_gan(day_master, stem) for stem in hidden],
        })

    year_gan, year_zhi = pillar_data[0][2:4]
    month_gan, month_zhi = pillar_data[1][2:4]
    day_gan, day_zhi = pillar_data[2][2:4]
    pillar_gans = [row[2] for row in pillar_data]
    pillar_zhis = [row[3] for row in pillar_data]
    wx_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for gan, zhi in zip(pillar_gans, pillar_zhis):
        wx_count[GAN_WX[gan]] += 1.0
        for hidden_gan, weight in HIDDEN_WEIGHTS[zhi]:
            wx_count[GAN_WX[hidden_gan]] += weight
    total = sum(wx_count.values())
    wx_pct = {key: round(value / total * 100, 1) for key, value in wx_count.items()}
    diaohou = get_diaohou(day_master, month_zhi)
    shensha = calc_shensha(pillar_zhis, pillar_gans, day_master,
                           year_zhi, day_zhi, month_zhi)

    yun_data = {"status": "unavailable", "reason": "缺 calculation_sex；不默认性别"}
    da_yun_list = []
    if calculation_sex in {"m", "f"}:
        yun = term_ec.getYun(1 if calculation_sex == "m" else 0, sect=1)
        yun_data = {
            "status": "ok", "method": "sect1",
            "start": f"{yun.getStartYear()}年{yun.getStartMonth()}月{yun.getStartDay()}天",
            "start_date": yun.getStartSolar().toYmd(),
        }
        for da in yun.getDaYun()[:9]:
            if da.getGanZhi():
                da_yun_list.append({
                    "干支": da.getGanZhi(), "起始年龄": da.getStartAge(),
                    "终止年龄": da.getEndAge(), "起始公历年": da.getStartYear(),
                    "终止公历年": da.getEndYear(),
                })

    timing = timing_request if isinstance(timing_request, dict) else {}
    systems = timing.get("systems") or ["bazi"]
    run_bazi_timing = "bazi" in systems
    years = timing.get("years", []) if run_bazi_timing else []
    liunian = []
    for year in sorted(set(years)):
        year = int(year)
        start = _lichun_moment(year)
        end = _lichun_moment(year + 1)
        marker_dt = start + timedelta(seconds=1)
        marker = Solar.fromYmdHms(marker_dt.year, marker_dt.month, marker_dt.day,
                                  marker_dt.hour, marker_dt.minute, marker_dt.second)
        liunian.append({
            "year": year, "干支": marker.getLunar().getEightChar().getYear(),
            "year_boundary": "立春",
            "validity": {
                "start": start.isoformat(timespec="seconds") + "+08:00",
                "end": end.isoformat(timespec="seconds") + "+08:00",
                "timezone": "UTC+08:00",
                "source": "lunar-python solar-term table",
            },
        })
    monthly = []
    if run_bazi_timing:
        from _common import InputError
        for query in timing.get("months", []):
            if not isinstance(query, dict):
                raise InputError("invalid_timing_month", "timing_request.months",
                                 "每个流月查询必须包含 year 与 month")
            try:
                year, month = int(query["year"]), int(query["month"])
                if month < 1 or month > 12:
                    raise ValueError
            except (KeyError, TypeError, ValueError) as exc:
                raise InputError("invalid_timing_month", "timing_request.months",
                                 "流月查询 year/month 必须为有效公历年月") from exc
            monthly.append({"year": year, "month": month,
                            **_term_months_in_gregorian_month(year, month)})

    jieqi_warning = calc_jieqi_warning(term_solar)
    sxtwl_check = None
    try:
        birth_date = time_context.get("input", {}).get("subject", {}).get(
            "birth_date", time_context.get("input", {}).get("subject", {}).get("date"))
        if birth_date:
            y, m, d = map(int, birth_date.split("-"))
            day_info = sxtwl.fromSolar(y, m, d)
            sxtwl_check = {
                "date": f"{y:04d}-{m:02d}-{d:02d}",
                "sxtwl_day_ganzhi": HS[day_info.getDayGZ().tg] + EB[day_info.getDayGZ().dz],
                "precision": "date-level only; not an independent hour/month adjudication",
            }
    except (ImportError, ValueError, AttributeError):
        sxtwl_check = None
    from bazi_structure import build_structure
    structure = build_structure(pillar_gans, pillar_zhis,
                                dayun=da_yun_list, liunian=liunian)
    data = {
        "公历": apparent_dt.isoformat(timespec="seconds"),
        "节气时间轴": term_dt.isoformat(timespec="seconds"),
        "农历": day_solar.getLunar().toString(),
        "子时规则": zi_hour_rule,
        "四柱": pillars,
        "日主": {"天干": day_master, "五行": GAN_WX[day_master],
                 "意象": DM_IMAGE.get(day_master, "未知")},
        "五行权重": {key: round(value, 2) for key, value in wx_count.items()},
        "五行比例": wx_pct,
        "五行统计口径": "四柱天干+藏干固定权重；非实测能量",
        "调候用神": diaohou,
        "结构": structure,
        "神煞": shensha,
        "起运": yun_data,
        "大运": da_yun_list,
        "流年": liunian,
        "流月查询": monthly,
        "空亡": {"年柱空亡": term_ec.getYearXunKong(),
                 "日柱空亡": day_ec.getDayXunKong()},
        "胎元": term_ec.getTaiYuan(),
        "命宫": day_ec.getMingGong(),
        "节气警告": jieqi_warning,
        "sxtwl_交叉校验": sxtwl_check,
    }
    return {"status": "ok" if yun_data["status"] == "ok" else "partial",
            "data": data, "candidates": [],
            "limitations": [] if yun_data["status"] == "ok" else [yun_data["reason"]]}
def parse_args(argv):
    from _common import InputError
    result = {"intake": None, "subject": "primary", "zi_hour_rule": "midnight"}
    i = 0
    while i < len(argv):
        item = argv[i]
        key, sep, value = item.partition("=")
        if key == "--intake":
            if not sep:
                i += 1
                value = argv[i] if i < len(argv) else None
            if not value:
                raise InputError("missing_argument", "--intake", "--intake 需要文件路径")
            result["intake"] = value
        elif key in {"--subject", "--zi-hour-rule"}:
            if not sep:
                i += 1
                value = argv[i] if i < len(argv) else None
            if key == "--subject" and value in {"primary", "partner"}:
                result["subject"] = value
            elif key == "--zi-hour-rule" and value in {"midnight", "zi_start"}:
                result["zi_hour_rule"] = value
            else:
                raise InputError("invalid_argument", key, f"{key} 参数值无效")
        else:
            raise InputError("unknown_argument", key, f"未知参数: {item}")
        i += 1
    if not result["intake"]:
        raise InputError("missing_argument", "--intake", "必须提供 --intake")
    return result


def main():
    from _common import InputError, normalize_birth_time
    try:
        args = parse_args(sys.argv[1:])
        with open(args["intake"], encoding="utf-8") as stream:
            intake = json.load(stream)
        if args["subject"] == "primary":
            subject = intake.get("subject")
            time_input = intake.get("time_input")
        else:
            partner = intake.get("synastry", {}).get("partner")
            subject = partner.get("subject") if isinstance(partner, dict) else None
            time_input = partner.get("time_input") if isinstance(partner, dict) else None
        if not isinstance(subject, dict) or not isinstance(time_input, dict):
            raise InputError("missing_subject", args["subject"],
                             f"intake 缺少 {args['subject']} subject/time_input")
        context = normalize_birth_time(subject, time_input,
                                       as_of=intake.get("analysis_as_of"))
        result = calc_bazi(
            context, subject.get("calculation_sex"),
            zi_hour_rule=args["zi_hour_rule"],
            analysis_as_of=intake.get("analysis_as_of"),
            timing_request=intake.get("timing_request"),
        )
        print(json.dumps(result, ensure_ascii=False, default=str))
    except Exception as exc:
        from _common import CalcError
        code = 2 if isinstance(exc, (InputError, FileNotFoundError, json.JSONDecodeError)) else 1
        print(json.dumps({"status": "error", "errors": [{
            "code": getattr(exc, "code", "calculation_error"),
            "path": getattr(exc, "path", ""),
            "message": getattr(exc, "message", str(exc)),
        }]}, ensure_ascii=False))
        print(f"bazi_calc: {exc}", file=sys.stderr)
        sys.exit(code)


if __name__ == "__main__":
    main()


