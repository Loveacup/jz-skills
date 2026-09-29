"""Derived astrology and Zi Wei structure fields checked against standard tables."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import astro_structure as astro  # noqa: E402
import ziwei_structure as ziwei  # noqa: E402
from _common import normalize_birth_time  # noqa: E402
from astro_calc import calc_chart  # noqa: E402
from ziwei_calc import calc_ziwei  # noqa: E402

BUNDLE = json.loads((ROOT / 'tests/fixtures/chart_bundle.example.json').read_text(encoding='utf-8'))


def point(sign, degree=15.0, speed=1.0, house=None):
    longitude = astro.SIGNS.index(sign) * 30 + degree
    row = {'黄经': longitude, '星座': sign, '宫内度数': degree, '黄经日速': speed}
    if house:
        row['落宫'] = house
    return row


def context():
    subject = {'birth_date': '2000-01-15', 'date_calendar': 'gregorian',
               'calculation_sex': 'm', 'location': {'latitude': 30.0, 'longitude': 120.0}}
    time_input = {'precision': 'minute', 'start': '2000-01-15T12:00', 'end': None,
                  'branch_label': None, 'timezone_name': None, 'utc_offset_hours': 8,
                  'fold': None, 'clock_basis': 'civil'}
    return normalize_birth_time(subject, time_input, as_of='2026-01-15')


class AstroStructureTests(unittest.TestCase):
    def test_essential_dignity_table(self):
        table = {
            ('太阳', '狮子'): ['入庙'], ('太阳', '白羊'): ['擢升'],
            ('太阳', '水瓶'): ['失势'], ('太阳', '天秤'): ['落陷'],
            ('月亮', '巨蟹'): ['入庙'], ('月亮', '天蝎'): ['落陷'],
            ('水星', '处女'): ['入庙', '擢升'], ('水星', '双鱼'): ['失势', '落陷'],
            ('金星', '双鱼'): ['擢升'], ('金星', '白羊'): ['失势'],
            ('火星', '天蝎'): ['入庙'], ('火星', '巨蟹'): ['落陷'],
            ('木星', '双鱼'): ['入庙'], ('木星', '摩羯'): ['落陷'],
            ('土星', '水瓶'): ['入庙'], ('土星', '白羊'): ['落陷'],
            ('土星', '双子'): [], ('冥王星', '天蝎'): [],
        }
        for (planet, sign), expected in table.items():
            self.assertEqual(astro.dignity(planet, sign), expected, (planet, sign))

    def test_dispositor_chain_and_mutual_reception(self):
        signs = {'太阳': '巨蟹', '月亮': '狮子', '水星': '巨蟹', '金星': '金牛',
                 '火星': '天秤', '木星': '天蝎', '土星': '射手',
                 '天王星': '水瓶', '海王星': '双鱼', '冥王星': '白羊'}
        positions = {name: point(sign) for name, sign in signs.items()}
        result = astro.build_structure(positions, None, None, None, [], 8.0)
        traditional = result['守护']['传统守护']
        self.assertEqual(traditional['互容'], [{'行星': ['太阳', '月亮'], '星座': ['巨蟹', '狮子']}])
        self.assertEqual(traditional['定位星链']['水星']['类型'], '循环')
        self.assertEqual(traditional['定位星链']['水星']['循环成员'], ['月亮', '太阳'])
        self.assertEqual(traditional['定位星链']['火星'],
                         {'链': ['火星', '金星'], '终点': '金星', '类型': '入庙星'})
        self.assertEqual(traditional['定位星']['木星'], '火星')
        self.assertEqual(result['守护']['现代守护']['定位星']['木星'], '冥王星')
        self.assertEqual(traditional['终点定位星'], ['金星'])
        self.assertIn('海王星', result['守护']['现代守护']['终点定位星'])

    def test_element_and_mode_counts(self):
        signs = dict(zip(astro.TEN_PLANETS, ['白羊', '狮子', '射手', '金牛', '双子',
                                             '巨蟹', '天蝎', '双鱼', '摩羯', '天秤']))
        result = astro.build_structure({n: point(s) for n, s in signs.items()},
                                       None, None, None, [], 8.0)
        self.assertEqual({k: v['数量'] for k, v in result['元素分布'].items()},
                         {'火': 3, '土': 2, '风': 2, '水': 3})
        self.assertEqual({k: v['数量'] for k, v in result['模式分布'].items()},
                         {'开创': 4, '固定': 3, '变动': 3})
        self.assertEqual(result['星群'], [])

    def test_sect_follows_horizon_not_house_system(self):
        positions = {'太阳': point('摩羯', 24.3)}
        day = astro.build_structure(positions, None, 33.66, 292.15, [], 8.0)
        self.assertEqual(day['盘别'], '日盘')
        night = astro.build_structure(positions, None, 213.66, 112.15, [], 8.0)
        self.assertEqual(night['盘别'], '夜盘')

    def test_aspect_trend_uses_relative_speed(self):
        fast = {'黄经': 10.0, '黄经日速': 13.0}
        slow = {'黄经': 15.0, '黄经日速': 1.0}
        self.assertEqual(astro.aspect_trend('合相', 0.0, fast, slow), '入相')
        self.assertEqual(astro.aspect_trend('合相', 0.0, slow, fast), '入相')
        passed = {'黄经': 20.0, '黄经日速': 13.0}
        self.assertEqual(astro.aspect_trend('合相', 0.0, passed, slow), '出相')
        retro = {'黄经': 108.0, '黄经日速': -0.5}
        base = {'黄经': 15.0, '黄经日速': 0.1}
        self.assertEqual(astro.aspect_trend('四分', 90.0, base, retro), '入相')
        self.assertIsNone(astro.aspect_trend('合相', 0.0, {'黄经': 1.0}, slow))
        same = {'黄经': 61.0, '黄经日速': 1.0}
        self.assertEqual(astro.aspect_trend('六合', 60.0, {'黄经': 0.0, '黄经日速': 1.0}, same), '持平')
        exact = {'黄经': 60.0, '黄经日速': 1.0}
        self.assertEqual(astro.aspect_trend('六合', 60.0, {'黄经': 0.0, '黄经日速': 2.0}, exact), '正相位')
        wrap_a = {'黄经': 358.0, '黄经日速': 1.0}
        wrap_b = {'黄经': 3.0, '黄经日速': 0.1}
        self.assertEqual(astro.aspect_trend('合相', 0.0, wrap_a, wrap_b), '入相')

    def test_grand_cross_does_not_repeat_its_t_squares(self):
        def leg(a, b, kind):
            return {'行星A': a, '行星B': b, '相位': kind, '偏差': 1.0}
        aspects = [leg('太阳', '月亮', '对冲'), leg('木星', '土星', '对冲'),
                   leg('太阳', '木星', '四分'), leg('太阳', '土星', '四分'),
                   leg('月亮', '木星', '四分'), leg('月亮', '土星', '四分'),
                   leg('火星', '太阳', '四分'), leg('火星', '月亮', '四分')]
        positions = {name: point('白羊') for name in astro.TEN_PLANETS}
        found = astro.build_structure(positions, None, None, None, aspects, 8.0)['相位图形']
        self.assertEqual([(r['类型'], r['成员']) for r in found], [
            ('T三角', ['太阳', '月亮', '火星']),
            ('大十字', ['太阳', '月亮', '木星', '土星']),
        ])

    def test_whole_sign_sect_agrees_between_fortune_and_structure(self):
        subject = {'birth_date': '2000-01-15', 'date_calendar': 'gregorian',
                   'calculation_sex': 'm', 'location': {'latitude': 30.0, 'longitude': 120.0}}
        for clock, expected in (('07:20', '日盘'), ('17:40', '夜盘')):
            time_input = {'precision': 'minute', 'start': f'2000-01-15T{clock}', 'end': None,
                          'branch_label': None, 'timezone_name': None, 'utc_offset_hours': 8,
                          'fold': None, 'clock_basis': 'civil'}
            ctx = normalize_birth_time(subject, time_input, as_of='2026-01-15')
            for system in ('placidus', 'whole_sign'):
                data = calc_chart(ctx, house_system=system)['data']
                self.assertEqual(data['结构']['盘别'], expected, (clock, system))
                self.assertEqual(data['扩展配点']['福点']['盘别'], expected, (clock, system))

    def test_patterns_require_every_leg(self):
        def leg(a, b, kind, diff):
            return {'行星A': a, '行星B': b, '相位': kind, '偏差': diff}
        aspects = [leg('月亮', '水星', '三合', 1.0), leg('月亮', '天王星', '三合', 2.0),
                   leg('水星', '天王星', '三合', 6.5), leg('木星', '冥王星', '对冲', 1.0),
                   leg('木星', '天王星', '四分', 3.0), leg('天王星', '冥王星', '四分', 2.0),
                   leg('太阳', '月亮', '三合', 1.0), leg('太阳', '北交点', '三合', 1.0)]
        positions = {name: point('白羊') for name in astro.TEN_PLANETS}
        found = astro.build_structure(positions, None, None, None, aspects, 8.0)['相位图形']
        self.assertEqual(found, [
            {'类型': '大三角', '成员': ['月亮', '水星', '天王星'], '最宽偏差': 6.5},
            {'类型': 'T三角', '成员': ['木星', '天王星', '冥王星'], '顶点': '天王星',
             '对冲两端': ['木星', '冥王星'], '最宽偏差': 3.0},
        ])

    def test_calc_chart_structure_matches_its_own_positions(self):
        data = calc_chart(context())['data']
        structure = data['结构']
        self.assertEqual(structure['盘别'], data['扩展配点']['福点']['盘别'])
        self.assertEqual(structure['命主星']['上升星座'], '金牛')
        self.assertEqual(structure['命主星']['传统守护']['行星'], '金星')
        self.assertEqual(structure['先天尊贵']['月亮'], {'星座': '金牛', '状态': ['擢升']})
        self.assertEqual(sum(v['数量'] for v in structure['元素分布'].values()), 10)
        self.assertEqual(len(structure['相位趋势']), len(data['主要相位']))
        self.assertEqual([r['宫位'] for r in structure['宫主落宫']], list(range(1, 13)))
        placed = sorted(n for members in structure['宫内行星'].values() for n in members)
        self.assertEqual(placed, sorted(astro.TEN_PLANETS))
        for row in structure['宫界距离'].values():
            self.assertGreaterEqual(row['距本宫宫头'], 0)
            self.assertGreater(row['距下一宫宫头'], 0)
        angles = {(r['行星'], r['轴点']) for r in structure['轴点合相']}
        self.assertIn(('月亮', '上升'), angles)
        self.assertIn(('太阳', '天顶'), angles)


class ZiweiStructureTests(unittest.TestCase):
    def setUp(self):
        self.data = BUNDLE['dimensions']['ziwei']['data']
        self.structure = ziwei.build_structure(self.data['十二宫'], self.data['运限'])

    def relation(self, name):
        return next(r for r in self.structure['宫位关系'] if r['宫位'] == name)

    def test_three_directions_follow_branch_trines_and_opposition(self):
        ming = self.relation('命宫')
        self.assertEqual(ming['地支'], '未')
        self.assertEqual((ming['对宫']['宫位'], ming['对宫']['地支']), ('迁移宫', '丑'))
        self.assertEqual(sorted((p['宫位'], p['地支']) for p in ming['三合宫']),
                         [('官禄宫', '亥'), ('财帛宫', '卯')])
        self.assertEqual([p['地支'] for p in ming['邻宫']], ['午', '申'])
        for row in self.structure['宫位关系']:
            branches = {row['地支'], row['对宫']['地支'], *(p['地支'] for p in row['三合宫'])}
            self.assertEqual(len(branches), 4)

    def test_natal_mutagens_and_their_palaces(self):
        found = [(r['四化'], r['星曜'], r['宫位']) for r in self.structure['生年四化']]
        self.assertEqual(found, [('禄', '武曲', '田宅宫'), ('权', '贪狼', '子女宫'),
                                 ('科', '天梁', '命宫'), ('忌', '文曲', '田宅宫')])
        self.assertEqual(self.relation('命宫')['三方四正四化'],
                         [{'四化': '科', '星曜': '天梁', '宫位': '命宫'}])

    def test_period_mutagens_locate_natal_palaces(self):
        yearly = self.structure['当前流年四化']
        self.assertEqual(yearly['命宫所在本命宫'], '夫妻宫')
        self.assertEqual([(r['四化'], r['星曜'], r['本命落宫']['宫位']) for r in yearly['四化']],
                         [('禄', '天机', '迁移宫'), ('权', '天梁', '命宫'),
                          ('科', '紫微', '疾厄宫'), ('忌', '太阴', '财帛宫')])

    def test_empty_palace_borrows_opposite_major_stars(self):
        palaces = json.loads(json.dumps(self.data['十二宫']))
        target = next(p for p in palaces if p['宫位'] == '命宫')
        target['主星'] = []
        structure = ziwei.build_structure(palaces, None)
        row = next(r for r in structure['宫位关系'] if r['宫位'] == '命宫')
        self.assertTrue(row['空宫'])
        self.assertEqual([s['名称'] for s in row['借对宫主星']], ['天机'])
        self.assertEqual(structure['空宫'], ['命宫'])
        self.assertIsNone(self.relation('命宫')['借对宫主星'])
        self.assertIsNone(structure['当前流年四化'])

    def test_body_palace_and_incomplete_input(self):
        self.assertEqual(self.structure['身宫'], {'所在宫位': '命宫', '地支': '未'})
        with self.assertRaises(ValueError):
            ziwei.build_structure(self.data['十二宫'][:11], None)

    def test_calc_ziwei_exposes_structure(self):
        data = calc_ziwei(context(), 'm', '2026-01-15')['data']
        self.assertEqual(len(data['结构']['宫位关系']), 12)
        self.assertEqual({r['四化'] for r in data['结构']['生年四化']}, {'禄', '权', '科', '忌'})


if __name__ == '__main__':
    unittest.main()
