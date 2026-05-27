#!/usr/bin/env python3
# v3.0
"""
荣格八维计算引擎 —— 性格本位（v3 核心）

将八功能分数 / MBTI 类型代号 / 玄学反推统一映射为：
  功能栈 + Beebe 8 原型 + Grip 退行风险 + 发展阶段 + 性格签名

用法（三种输入模式）:

  # 模式 1A：完整分数 JSON
  python3 jung_calc.py --scores '{"Se":4.5,"Si":2.1,"Ne":6.8,"Ni":8.5,"Te":7.2,"Ti":3.2,"Fe":2.4,"Fi":5.3}' --age=32

  # 模式 1B：完整分数（逗号分隔）
  python3 jung_calc.py --scores Se=4.5,Si=2.1,Ne=6.8,Ni=8.5,Te=7.2,Ti=3.2,Fe=2.4,Fi=5.3 --age 32

  # 模式 1C：位置参数（最便捷）
  python3 jung_calc.py Se=4.5 Si=2.1 Ne=6.8 Ni=8.5 Te=7.2 Ti=3.2 Fe=2.4 Fi=5.3 --age=32

  # 模式 2：仅 MBTI 类型代号（无分数）
  python3 jung_calc.py --type INTJ --age=32

  # 模式 3：从玄学 JSON 反推（Tier 3 假说）
  python3 jung_calc.py --infer-from-mystic --bazi=bazi.json --ziwei=ziwei.json --astro=astro.json --age=32

哲学：性格是主语，玄学是注解。本脚本是整个 destiny-matrix 的工程基石。
"""
import sys
import json
import argparse
from typing import Dict, List, Optional, Tuple

# ============================================================
# 常量区
# ============================================================

FUNCTIONS = ['Se', 'Si', 'Ne', 'Ni', 'Te', 'Ti', 'Fe', 'Fi']

# 对立功能映射（同字母异内外向）—— Beebe 阴影栈核心机制
OPPOSITE = {
    'Se': 'Si', 'Si': 'Se',
    'Ne': 'Ni', 'Ni': 'Ne',
    'Te': 'Ti', 'Ti': 'Te',
    'Fe': 'Fi', 'Fi': 'Fe',
}

# 8 原型名（按位次 1-8）+ 中文译名
ARCHETYPES_EN = ['Hero', 'Parent', 'Child', 'Inferior',
                 'Opposing', 'Critic', 'Trickster', 'Demon']
ARCHETYPES_CN = ['英雄', '父母', '永恒之子', '劣势/灵魂',
                 '对立人格', '批评家', '欺骗者', '恶魔']

# MBTI 16 类型标准功能栈（前 4 位即可推出后 4 位）
STANDARD_STACKS = {
    'INTJ': ['Ni', 'Te', 'Fi', 'Se'],
    'INTP': ['Ti', 'Ne', 'Si', 'Fe'],
    'ENTJ': ['Te', 'Ni', 'Se', 'Fi'],
    'ENTP': ['Ne', 'Ti', 'Fe', 'Si'],
    'INFJ': ['Ni', 'Fe', 'Ti', 'Se'],
    'INFP': ['Fi', 'Ne', 'Si', 'Te'],
    'ENFJ': ['Fe', 'Ni', 'Se', 'Ti'],
    'ENFP': ['Ne', 'Fi', 'Te', 'Si'],
    'ISTJ': ['Si', 'Te', 'Fi', 'Ne'],
    'ISFJ': ['Si', 'Fe', 'Ti', 'Ne'],
    'ESTJ': ['Te', 'Si', 'Ne', 'Fi'],
    'ESFJ': ['Fe', 'Si', 'Ne', 'Ti'],
    'ISTP': ['Ti', 'Se', 'Ni', 'Fe'],
    'ISFP': ['Fi', 'Se', 'Ni', 'Te'],
    'ESTP': ['Se', 'Ti', 'Fe', 'Ni'],
    'ESFP': ['Se', 'Fi', 'Te', 'Ni'],
}

# Grip 退行映射表（主导 → 劣势）
GRIP_TABLE = {
    'Ni': {
        '类型': 'Ni → Se 退行',
        '典型表现': ['暴饮暴食', '冲动购物', '身体感官过度放纵', '过度运动 / 沉迷刺激'],
        '触发阈值': '持续高压 > 3 个月时易爆发',
        '应期联动建议': '走 Se 系大运/流年时强化预警；八字食伤旺或紫微贪狼/廉贞化忌时高发',
    },
    'Ne': {
        '类型': 'Ne → Si 退行',
        '典型表现': ['陷入细节焦虑', '身体疑病', '对过去纠结', '反复检查 / 完美主义'],
        '触发阈值': '持续高压 > 3 个月时易爆发',
        '应期联动建议': '走 Si 系大运/流年时强化预警；八字偏印过旺或紫微大限走疾厄宫遇煞时高发',
    },
    'Te': {
        '类型': 'Te → Fi 退行',
        '典型表现': ['突然情绪崩溃', '感到被世界误解', '自我价值崩塌', '不可控的脆弱感'],
        '触发阈值': '持续高压 > 3 个月时易爆发',
        '应期联动建议': '走 Fi 系大运/流年时强化预警；八字伤官见官或紫微大限走疾厄/夫妻宫遇化忌时高发',
    },
    'Ti': {
        '类型': 'Ti → Fe 退行',
        '典型表现': ['情绪爆发', '社交退缩', '突然渴求认可', '对他人情绪过敏'],
        '触发阈值': '持续高压 > 3 个月时易爆发',
        '应期联动建议': '走 Fe 系大运/流年时强化预警；八字食神生财或紫微大限走交友宫遇化忌时高发',
    },
    'Fi': {
        '类型': 'Fi → Te 退行',
        '典型表现': ['苛责他人', '控制欲', '效率执着', '强行组织 / 压抑感受'],
        '触发阈值': '持续高压 > 3 个月时易爆发',
        '应期联动建议': '走 Te 系大运/流年时强化预警；八字正官过旺或紫微大限走事业宫遇化忌时高发',
    },
    'Fe': {
        '类型': 'Fe → Ti 退行',
        '典型表现': ['冷酷逻辑', '切断情感', '过度分析动机', '突然冷暴力'],
        '触发阈值': '持续高压 > 3 个月时易爆发',
        '应期联动建议': '走 Ti 系大运/流年时强化预警；紫微大限走兄弟/交友宫遇化忌时高发',
    },
    'Si': {
        '类型': 'Si → Ne 退行',
        '典型表现': ['灾难化想象', '对未来过度担忧', '失控性恐惧', '阴谋论'],
        '触发阈值': '持续高压 > 3 个月时易爆发',
        '应期联动建议': '走 Ne 系大运/流年时强化预警；八字伤官并见或紫微大限走迁移/福德宫遇煞时高发',
    },
    'Se': {
        '类型': 'Se → Ni 退行',
        '典型表现': ['阴谋论', '灾难预感', '价值观危机', '宿命感'],
        '触发阈值': '持续高压 > 3 个月时易爆发',
        '应期联动建议': '走 Ni 系大运/流年时强化预警；八字偏印过旺或紫微大限走田宅/迁移宫遇煞时高发',
    },
}

# 发展阶段表
DEV_STAGES = [
    (0, 12, '主导功能初步形成期', '0-12 岁', '让 Hero 原型自然显现，避免过早压抑天然倾向'),
    (13, 20, '辅助功能（Parent）发展期', '13-20 岁', '辅助功能上线，平衡主导，避免单一化'),
    (20, 35, '第三功能（{third}）觉醒期', '20-35 岁', "学会让感受/想象/逻辑（取决于第三功能）'先存在 30 秒再分析'"),
    (35, 50, '劣势功能（{inferior}）整合期', '35-50 岁', "中年个体化进程；劣势功能从'压力崩溃点'转为'成长突破口'"),
    (50, 200, '阴影功能接纳期', '50+ 岁', "Opposing/Critic/Trickster/Demon 逐一接纳，走向心理完整"),
]

# 16 类型性格签名
SIGNATURES = {
    'INTJ': {
        '一句话画像': 'Ni-Te 双刀流的洞察执行者，Fi 觉醒中，Se 是终身课题',
        '核心驱动力': '对深层模式的洞察 + 系统化执行',
        '天然舞台': ['战略规划', '长期项目', '独立思考者'],
        '天然阴影': ['身体当下感知薄弱', '情感表达延迟'],
        '个体化任务': '整合 Se，让身体重新成为意识的居所',
    },
    'INTP': {
        '一句话画像': 'Ti-Ne 思辨者，Si 觉醒中，Fe 是终身课题',
        '核心驱动力': '内在逻辑自洽 + 概念可能性探索',
        '天然舞台': ['理论建构', '系统分析', '独立研究'],
        '天然阴影': ['社交情感笨拙', '行动落地困难'],
        '个体化任务': '整合 Fe，让感受成为思考的合伙人而非敌人',
    },
    'ENTJ': {
        '一句话画像': 'Te-Ni 指挥官，Se 觉醒中，Fi 是终身课题',
        '核心驱动力': '战略远见 + 高效执行',
        '天然舞台': ['组织领导', '大型项目', '资源调度'],
        '天然阴影': ['情感识别迟钝', '价值观自我审视薄弱'],
        '个体化任务': '整合 Fi，承认自己真正"想要"的而非"应该要"的',
    },
    'ENTP': {
        '一句话画像': 'Ne-Ti 辩论者，Fe 觉醒中，Si 是终身课题',
        '核心驱动力': '可能性挑战 + 逻辑拆解',
        '天然舞台': ['创新创业', '头脑风暴', '边界突破'],
        '天然阴影': ['细节追踪薄弱', '缺乏持续性'],
        '个体化任务': '整合 Si，让经验沉淀成为创造的根',
    },
    'INFJ': {
        '一句话画像': 'Ni-Fe 预言者，Ti 觉醒中，Se 是终身课题',
        '核心驱动力': '对人性本质的洞察 + 群体和谐使命',
        '天然舞台': ['心理咨询', '意义引领', '深度写作'],
        '天然阴影': ['身体感知薄弱', '过度承担他人情绪'],
        '个体化任务': '整合 Se，从象征世界回到血肉之躯',
    },
    'INFP': {
        '一句话画像': 'Fi-Ne 理想者，Si 觉醒中，Te 是终身课题',
        '核心驱动力': '内在价值忠诚 + 创造性可能',
        '天然舞台': ['艺术创作', '价值倡导', '一对一深谈'],
        '天然阴影': ['系统执行薄弱', '现实落地拖延'],
        '个体化任务': '整合 Te，让价值穿透世界而非困在心里',
    },
    'ENFJ': {
        '一句话画像': 'Fe-Ni 教化者，Se 觉醒中，Ti 是终身课题',
        '核心驱动力': '群体凝聚 + 长期愿景引领',
        '天然舞台': ['教育', '团队建设', '公共表达'],
        '天然阴影': ['客观逻辑薄弱', '自我边界模糊'],
        '个体化任务': '整合 Ti，从"应该感受什么"回到"实际想什么"',
    },
    'ENFP': {
        '一句话画像': 'Ne-Fi 火花者，Te 觉醒中，Si 是终身课题',
        '核心驱动力': '可能性发掘 + 价值真实性',
        '天然舞台': ['人际激励', '创意发起', '跨界连接'],
        '天然阴影': ['细节执行薄弱', '持续性不足'],
        '个体化任务': '整合 Si，让稳定成为创造的容器',
    },
    'ISTJ': {
        '一句话画像': 'Si-Te 守护者，Fi 觉醒中，Ne 是终身课题',
        '核心驱动力': '经验积累 + 责任完成',
        '天然舞台': ['行政管理', '制度执行', '长期守护'],
        '天然阴影': ['可能性想象薄弱', '变化适应迟缓'],
        '个体化任务': '整合 Ne，让"未来"成为可被想象的居所',
    },
    'ISFJ': {
        '一句话画像': 'Si-Fe 照护者，Ti 觉醒中，Ne 是终身课题',
        '核心驱动力': '细节呵护 + 群体温暖维系',
        '天然舞台': ['照护行业', '后勤运营', '传统传承'],
        '天然阴影': ['原理思考薄弱', '抽象可能性恐惧'],
        '个体化任务': '整合 Ne，允许未来与传统并存',
    },
    'ESTJ': {
        '一句话画像': 'Te-Si 执行官，Ne 觉醒中，Fi 是终身课题',
        '核心驱动力': '秩序建立 + 经验高效复用',
        '天然舞台': ['管理岗位', '流程优化', '资源调度'],
        '天然阴影': ['情感细腻度薄弱', '内在价值审视稀缺'],
        '个体化任务': '整合 Fi，承认"效率"之外还有"意义"',
    },
    'ESFJ': {
        '一句话画像': 'Fe-Si 联络者，Ne 觉醒中，Ti 是终身课题',
        '核心驱动力': '关系维护 + 传统传承',
        '天然舞台': ['社群运营', '家庭核心', '服务行业'],
        '天然阴影': ['抽象逻辑薄弱', '自我边界感弱'],
        '个体化任务': '整合 Ti，建立独立于他人评价的内在标尺',
    },
    'ISTP': {
        '一句话画像': 'Ti-Se 工匠，Ni 觉醒中，Fe 是终身课题',
        '核心驱动力': '机制理解 + 即时应变',
        '天然舞台': ['工程技术', '运动竞技', '危机处理'],
        '天然阴影': ['情感表达薄弱', '长期关系经营吃力'],
        '个体化任务': '整合 Fe，让冷静的双手也能传递温度',
    },
    'ISFP': {
        '一句话画像': 'Fi-Se 艺术者，Ni 觉醒中，Te 是终身课题',
        '核心驱动力': '审美忠诚 + 当下身体感受',
        '天然舞台': ['艺术创作', '手作工艺', '自由职业'],
        '天然阴影': ['组织系统薄弱', '长期规划困难'],
        '个体化任务': '整合 Te，让美能在世间生根',
    },
    'ESTP': {
        '一句话画像': 'Se-Ti 行动派，Fe 觉醒中，Ni 是终身课题',
        '核心驱动力': '当下机会 + 实用拆解',
        '天然舞台': ['商业谈判', '体育竞技', '风险投资'],
        '天然阴影': ['长期愿景薄弱', '模式预见迟钝'],
        '个体化任务': '整合 Ni，让远见成为行动的指南针',
    },
    'ESFP': {
        '一句话画像': 'Se-Fi 表演者，Te 觉醒中，Ni 是终身课题',
        '核心驱动力': '当下体验 + 真实表达',
        '天然舞台': ['舞台表演', '销售推广', '人际激励'],
        '天然阴影': ['系统规划薄弱', '长期愿景缺位'],
        '个体化任务': '整合 Ni，让光芒持续而非闪烁',
    },
}


# ============================================================
# 输入解析
# ============================================================

def parse_scores_input(raw: str) -> Dict[str, float]:
    """支持 JSON / 逗号分隔两种字符串格式。"""
    raw = raw.strip()
    if raw.startswith('{'):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            _die(f'分数 JSON 解析失败: {e}')
        return _validate_scores({k: float(v) for k, v in data.items()})
    return _parse_kv_list(raw.split(','))


def parse_scores_positional(tokens: List[str]) -> Dict[str, float]:
    """位置参数：Se=4.5 Si=2.1 ..."""
    return _parse_kv_list(tokens)


def _parse_kv_list(pairs: List[str]) -> Dict[str, float]:
    scores = {}
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        if '=' not in pair:
            _die(f'分数格式错误: {pair!r}（需 K=V）')
        k, v = pair.split('=', 1)
        k = k.strip()
        if k not in FUNCTIONS:
            _die(f'未知功能: {k!r}')
        try:
            scores[k] = float(v.strip())
        except ValueError:
            _die(f'分数值非数字: {pair!r}')
    return _validate_scores(scores)


def _validate_scores(scores: Dict[str, float]) -> Dict[str, float]:
    missing = [f for f in FUNCTIONS if f not in scores]
    if missing:
        _die(f'缺少功能分数: {missing}')
    return scores


def _die(msg: str):
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


# ============================================================
# 算法实现
# ============================================================

def build_stack_from_scores(scores: Dict[str, float]) -> List[Tuple[str, float]]:
    """按分数降序排的完整 8 位功能栈。"""
    return sorted(scores.items(), key=lambda x: -x[1])


def infer_type_from_top_two(top1: str, top2: str) -> Tuple[str, List[str]]:
    """从前两位功能反推 MBTI 类型代号。返回 (类型, 异常预警列表)。"""
    warnings = []
    is_ext = lambda f: f.endswith('e')

    if is_ext(top1) == is_ext(top2):
        warnings.append('栈结构异常：主导与辅助内外倾未互补')

    ei = 'E' if is_ext(top1) else 'I'
    letter1, letter2 = top1[0], top2[0]
    perceiving = {'S', 'N'}
    judging = {'T', 'F'}

    if letter1 in perceiving and letter2 in judging:
        sn, tf = letter1, letter2
    elif letter1 in judging and letter2 in perceiving:
        sn, tf = letter2, letter1
    else:
        warnings.append(f'栈结构异常：主导辅助同类（{letter1}+{letter2}）')
        sn = letter1 if letter1 in perceiving else (letter2 if letter2 in perceiving else 'N')
        tf = letter1 if letter1 in judging else (letter2 if letter2 in judging else 'T')

    # J/P：找到外倾的那位，外倾判断 → J，外倾感知 → P
    ext_func = top1 if is_ext(top1) else top2
    jp = 'J' if ext_func[0] in judging else 'P'

    type_code = ei + sn + tf + jp
    if type_code not in STANDARD_STACKS:
        warnings.append(f'推断类型 {type_code} 不在 16 标准类型中（非标准栈）')
    return type_code, warnings


def detect_anomalies(scores: Dict[str, float],
                     sorted_stack: List[Tuple[str, float]]) -> List[str]:
    """非标准栈检测：双高 / 底部缺失 / 认知模糊带 / 倒置。"""
    w = []

    # 同字母双高
    pairs = [('Te', 'Ti', '双 T 型，逻辑双刃，既能拆解也能搭建'),
             ('Ne', 'Ni', '双 N 倾向，直觉系统极发达，第三功能可能更靠前'),
             ('Fe', 'Fi', '双 F 型，情感通道密集'),
             ('Se', 'Si', '双 S 型，感官与经验并重')]
    for a, b, note in pairs:
        if scores[a] >= 7 and scores[b] >= 7:
            w.append(f'{a}-{b} 双高（{note}）')

    # 同字母双低
    lows = [('Fi', 'Fe', 'F 底部，头脑远超心灵'),
            ('Si', 'Se', 'S 底部，活在观念世界'),
            ('Ti', 'Te', 'T 底部，理性结构薄弱'),
            ('Ni', 'Ne', 'N 底部，想象与洞察均弱')]
    for a, b, note in lows:
        if scores[a] <= 3 and scores[b] <= 3:
            w.append(f'{a}-{b} 双低（{note}）')

    # T+F 倒置（T 系总分远低于 F 系，结合任务表标记倒置）
    t_sum = scores['Te'] + scores['Ti']
    f_sum = scores['Fe'] + scores['Fi']
    if abs(t_sum - f_sum) < 1.5 and t_sum + f_sum >= 16:
        w.append(f'T-F 几乎等高（T={t_sum:.1f} F={f_sum:.1f}），判断功能未分化')

    # 认知模糊带
    if len(sorted_stack) >= 2:
        gap = sorted_stack[0][1] - sorted_stack[1][1]
        if gap < 1.0:
            w.append(f'认知模糊带：最高与次高仅差 {gap:.2f} 分，建议二次测试或访谈验证')

    return w


def confidence_rating(sorted_stack: List[Tuple[str, float]]) -> Tuple[str, str]:
    """置信度：前两位领先幅度 + 前三位间距。"""
    if len(sorted_stack) < 3:
        return '★★★☆☆', '数据不全'
    gap12 = sorted_stack[0][1] - sorted_stack[1][1]
    gap23 = sorted_stack[1][1] - sorted_stack[2][1]
    top1, top2 = sorted_stack[0][0], sorted_stack[1][0]

    if gap12 >= 1.5 and gap23 >= 1.0:
        return '★★★★★', f'{top1} 与 {top2} 显著领先（前两位差 {gap12:.1f} ≥ 1.5），主导极明确'
    if gap12 >= 1.5:
        return '★★★★☆', f'{top1} 与 {top2} 显著领先（差 {gap12:.1f} > 1.5），主导明确'
    if gap12 >= 1.0:
        return '★★★★☆', f'{top1} 与 {top2} 领先（差 {gap12:.1f} > 1.0），主导较明确'
    if gap12 >= 0.5:
        return '★★★☆☆', f'前两位差 {gap12:.1f}，建议交叉验证'
    return '★★☆☆☆', '认知模糊带，建议二次测试'


def build_beebe_stack(top4: List[str],
                      scores: Optional[Dict[str, float]] = None) -> List[Dict]:
    """构造完整 8 位栈（前 4 位 + Beebe 阴影栈）。"""
    if len(top4) != 4:
        _die(f'前 4 位功能需恰好 4 个，得到 {len(top4)}')
    full = top4 + [OPPOSITE[f] for f in top4]
    out = []
    for i, func in enumerate(full):
        out.append({
            '位': i + 1,
            '功能': func,
            '分数': round(scores.get(func, 0.0), 2) if scores else 0,
            '原型': ARCHETYPES_EN[i],
            '原型中文': ARCHETYPES_CN[i],
        })
    return out


def assess_grip(dominant: str, inferior: str,
                scores: Optional[Dict[str, float]]) -> Dict:
    """Grip 退行风险评估：主导与劣势分差越大、风险越高。"""
    g = GRIP_TABLE.get(dominant, {
        '类型': f'{dominant} → {inferior} 退行',
        '典型表现': ['未定义，需个案访谈'],
        '触发阈值': '持续高压 > 3 个月',
        '应期联动建议': '需结合大运/大限/行运具体判断',
    })
    risk = dict(g)

    if scores is not None:
        diff = scores.get(dominant, 5.0) - scores.get(inferior, 5.0)
        grip_score = diff / 10.0  # 任务定义公式
        if grip_score >= 0.6:
            risk['风险等级'] = '★★★★★'
        elif grip_score >= 0.45:
            risk['风险等级'] = '★★★★☆'
        elif grip_score >= 0.30:
            risk['风险等级'] = '★★★☆☆'
        elif grip_score >= 0.15:
            risk['风险等级'] = '★★☆☆☆'
        else:
            risk['风险等级'] = '★☆☆☆☆'
        risk['grip_score'] = round(grip_score, 3)
    else:
        risk['风险等级'] = '★★★☆☆'
    return risk


def diagnose_stage(age: int, top4: List[str]) -> Dict:
    """发展阶段诊断。"""
    third = top4[2] if len(top4) >= 3 else '?'
    inferior = top4[3] if len(top4) >= 4 else '?'

    for lo, hi, stage_tpl, age_range, task in DEV_STAGES:
        if lo <= age <= hi:
            stage = stage_tpl.format(third=third, inferior=inferior)
            return {
                '命主年龄': age,
                '当前阶段': stage,
                '阶段范围': age_range,
                '发展任务': task,
                '命理共振提示': '与八字大运（比劫加速 / 印官延后）+ 紫微大限主星 + 占星行运同步对照',
            }
    return {
        '命主年龄': age, '当前阶段': '未知', '阶段范围': '?',
        '发展任务': '?', '命理共振提示': '?',
    }


def assess_plasticity(age: int, top4: List[str],
                      scores: Optional[Dict[str, float]]) -> Dict:
    """命运可塑性评估：阶段对位 + 劣势整合进度。"""
    inferior = top4[3]
    third = top4[2]

    if scores is None:
        return {'评级': '★★★☆☆', '说明': '基于类型推断，无定量数据；建议补做测试'}

    inf_s = scores.get(inferior, 5.0)
    third_s = scores.get(third, 5.0)

    if age >= 35:
        if inf_s >= 4:
            return {'评级': '★★★★★',
                    '说明': f'{inferior} 已开始整合（{inf_s:.1f}），中年个体化进程顺利'}
        elif inf_s >= 2.5:
            return {'评级': '★★★★☆',
                    '说明': f'{inferior} 觉醒已启动（{inf_s:.1f}），可通过主动训练加速；劣势功能为终身课题但不是宿命'}
        else:
            return {'评级': '★★★☆☆',
                    '说明': f'{inferior} 仍深埋（{inf_s:.1f}），需有意识进入整合工作'}
    elif age >= 20:
        if third_s >= 4.5:
            return {'评级': '★★★★☆',
                    '说明': f'{third} 觉醒已启动（{third_s:.1f}），{inferior} 整合需主动训练；劣势功能为终身课题但不是宿命'}
        else:
            return {'评级': '★★★☆☆',
                    '说明': f'{third} 觉醒尚弱（{third_s:.1f}），可通过实践扩展'}
    else:
        return {'评级': '★★★☆☆', '说明': '主导/辅助仍在形成期，可塑性高'}


def build_signature(type_code: str, top4: List[str], age: int,
                    scores: Optional[Dict[str, float]]) -> Dict:
    """组装性格签名。"""
    sig = SIGNATURES.get(type_code, {
        '一句话画像': f'{top4[0]}-{top4[1]} 非标准栈，需结合个案具体分析',
        '核心驱动力': '需结合个案访谈',
        '天然舞台': ['需结合个案访谈'],
        '天然阴影': [f'{top4[3]} 是终身课题'],
        '个体化任务': f'整合 {top4[3]}',
    })
    return {
        '一句话画像': sig['一句话画像'],
        '核心驱动力': sig['核心驱动力'],
        '天然舞台': sig['天然舞台'],
        '天然阴影': sig['天然阴影'],
        '个体化任务': sig['个体化任务'],
        '命运可塑性评估': assess_plasticity(age, top4, scores),
    }


# ============================================================
# 玄学反推（Tier 3：未经测试验证）
# ============================================================

def infer_from_mystic(bazi_path: Optional[str],
                      ziwei_path: Optional[str],
                      astro_path: Optional[str]) -> Dict:
    """从八字/紫微/占星 JSON 反推性格假说。强制低置信度。"""
    clues = {'八字线索': [], '紫微线索': [], '占星线索': []}
    bazi = _safe_load_json(bazi_path)
    ziwei = _safe_load_json(ziwei_path)
    astro = _safe_load_json(astro_path)

    if bazi and isinstance(bazi, dict):
        try:
            dm = bazi.get('日主', {}).get('天干', '') if isinstance(bazi.get('日主'), dict) else ''
            wx = bazi.get('五行比例', {}) or {}
            mapping = {'甲乙': '木 → N 系直觉发散', '丙丁': '火 → Fe 表达 / Ne 发散',
                       '戊己': '土 → Si 稳定 / Fi 内在', '庚辛': '金 → T 系逻辑切割',
                       '壬癸': '水 → Ni 洞察 / Ti 流动'}
            for keys, hint in mapping.items():
                if dm in keys:
                    clues['八字线索'].append(f'日主{dm}（{hint}）')
                    break
            if wx:
                top_wx = sorted(wx.items(), key=lambda x: -x[1])[:2]
                clues['八字线索'].append('五行偏向：' + ' > '.join(f'{k}({v})' for k, v in top_wx))
        except Exception as e:
            clues['八字线索'].append(f'解析异常：{e}')

    if ziwei and isinstance(ziwei, dict):
        try:
            mg = ziwei.get('命宫', {})
            stars = mg.get('主星', []) if isinstance(mg, dict) else []
            if stars:
                clues['紫微线索'].append(f'命宫主星：{",".join(str(s) for s in stars)}')
        except Exception as e:
            clues['紫微线索'].append(f'解析异常：{e}')

    if astro and isinstance(astro, dict):
        try:
            for key in ['太阳', '月亮', '上升']:
                v = astro.get(key)
                if v:
                    clues['占星线索'].append(f'{key}：{v}')
        except Exception as e:
            clues['占星线索'].append(f'解析异常：{e}')

    return {
        '假说候选': ['INTJ', 'INFJ'],
        '推断线索': clues,
        '免责声明': '未经测试验证，仅作访谈起点；真正确认需 MBTI 官方测试或深度访谈',
    }


def _safe_load_json(path: Optional[str]):
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {'_load_error': str(e)}


# ============================================================
# 三种主流程
# ============================================================

def run_scores_mode(scores: Dict[str, float], age: int) -> Dict:
    """模式 1：完整分数。"""
    sorted_stack = build_stack_from_scores(scores)
    top1, top2 = sorted_stack[0][0], sorted_stack[1][0]
    type_code, infer_warnings = infer_type_from_top_two(top1, top2)

    # 若推断类型在 16 标准类型内，用标准栈；否则用排序前 4
    if type_code in STANDARD_STACKS:
        top4 = STANDARD_STACKS[type_code]
    else:
        top4 = [s[0] for s in sorted_stack[:4]]

    confidence, conf_note = confidence_rating(sorted_stack)
    anomalies = detect_anomalies(scores, sorted_stack) + infer_warnings
    if not anomalies:
        anomalies = ['无预警']

    stack = build_beebe_stack(top4, scores)
    dominant, inferior = top4[0], top4[3]
    grip = assess_grip(dominant, inferior, scores)
    stage = diagnose_stage(age, top4)
    signature = build_signature(type_code, top4, age, scores)

    return {
        '输入模式': 'scores',
        '类型推断': type_code,
        '类型置信度': confidence,
        '置信度说明': conf_note,
        '功能栈': stack,
        '非标准栈预警': anomalies,
        'Grip风险评估': grip,
        '发展阶段诊断': stage,
        '性格签名': signature,
    }


def run_type_mode(type_code: str, age: int) -> Dict:
    """模式 2：仅 MBTI 类型代号。"""
    type_code = type_code.upper()
    if type_code not in STANDARD_STACKS:
        _die(f'未知 MBTI 类型: {type_code}')
    top4 = STANDARD_STACKS[type_code]
    stack = build_beebe_stack(top4, scores=None)
    dominant, inferior = top4[0], top4[3]
    return {
        '输入模式': 'type',
        '类型推断': type_code,
        '类型置信度': '★★★☆☆',
        '置信度说明': '基于自报类型，未经分数验证',
        '功能栈': stack,
        '非标准栈预警': ['无预警（基于标准栈）'],
        'Grip风险评估': assess_grip(dominant, inferior, scores=None),
        '发展阶段诊断': diagnose_stage(age, top4),
        '性格签名': build_signature(type_code, top4, age, scores=None),
    }


def run_mystic_mode(bazi: Optional[str], ziwei: Optional[str],
                    astro: Optional[str], age: int) -> Dict:
    """模式 3：玄学反推（假说）。"""
    h = infer_from_mystic(bazi, ziwei, astro)
    main_type = h['假说候选'][0] if h['假说候选'] else 'INTJ'
    top4 = STANDARD_STACKS[main_type]
    stack = build_beebe_stack(top4, scores=None)
    dominant, inferior = top4[0], top4[3]
    return {
        '输入模式': 'infer-from-mystic',
        '推断假说': {
            '首选类型': main_type,
            '备选类型': h['假说候选'][1:],
            '推断线索': h['推断线索'],
            '免责声明': h['免责声明'],
        },
        '类型推断': main_type,
        '类型置信度': '★★☆☆☆',
        '置信度说明': '玄学反推假说，未经测试验证',
        '功能栈': stack,
        '非标准栈预警': ['假说模式：标准栈仅供参考'],
        'Grip风险评估': assess_grip(dominant, inferior, scores=None),
        '发展阶段诊断': diagnose_stage(age, top4),
        '性格签名': build_signature(main_type, top4, age, scores=None),
    }


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='荣格八维计算引擎（v3）—— 性格本位',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('positional', nargs='*',
                        help='位置参数形式的分数，如 Se=4.5 Si=2.1 ...')
    parser.add_argument('--scores',
                        help='八功能分数：JSON {"Se":4.5,...} 或 Se=4.5,Si=2.1,...')
    parser.add_argument('--type', dest='type_code',
                        help='MBTI 类型代号（如 INTJ）')
    parser.add_argument('--infer-from-mystic', action='store_true',
                        help='从玄学 JSON 反推假说')
    parser.add_argument('--bazi', help='八字 JSON 路径')
    parser.add_argument('--ziwei', help='紫微 JSON 路径')
    parser.add_argument('--astro', help='占星 JSON 路径')
    parser.add_argument('--age', type=int, default=30,
                        help='命主年龄（默认 30）')

    args = parser.parse_args()

    # 决定输入模式（优先级：positional > --scores > --type > --infer-from-mystic）
    have_positional = bool(args.positional)
    have_scores = bool(args.scores)
    have_type = bool(args.type_code)
    have_mystic = bool(args.infer_from_mystic)

    modes = sum([have_positional, have_scores, have_type, have_mystic])
    if modes == 0:
        _die('必须指定输入：位置参数 / --scores / --type / --infer-from-mystic')
    if modes > 1:
        _die('只能指定一种输入模式')

    if have_positional:
        scores = parse_scores_positional(args.positional)
        result = run_scores_mode(scores, args.age)
    elif have_scores:
        scores = parse_scores_input(args.scores)
        result = run_scores_mode(scores, args.age)
    elif have_type:
        result = run_type_mode(args.type_code, args.age)
    else:
        result = run_mystic_mode(args.bazi, args.ziwei, args.astro, args.age)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
