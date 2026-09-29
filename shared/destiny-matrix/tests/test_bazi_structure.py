"""Derived BaZi structure fields checked against standard lookup tables, not implementation output."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from _common import normalize_birth_time  # noqa: E402
from bazi_calc import calc_bazi  # noqa: E402
from bazi_structure import (  # noqa: E402
    build_structure, changsheng_stage, incoming_relations, lu_branch,
    month_state, yangren_branch,
)


def kinds(rows):
    return sorted((row['类型'], ''.join(row.get('地支', row.get('天干', [])))) for row in rows)


class BaziStructureTests(unittest.TestCase):
    def test_twelve_stages_follow_yang_forward_yin_backward_table(self):
        table = {
            ('甲', '亥'): '长生', ('甲', '卯'): '帝旺', ('甲', '未'): '墓', ('甲', '申'): '绝',
            ('乙', '午'): '长生', ('乙', '卯'): '临官', ('乙', '寅'): '帝旺', ('乙', '戌'): '墓',
            ('丙', '寅'): '长生', ('戊', '寅'): '长生', ('丙', '戌'): '墓',
            ('丁', '酉'): '长生', ('己', '酉'): '长生', ('丁', '丑'): '墓',
            ('庚', '巳'): '长生', ('庚', '丑'): '墓', ('辛', '子'): '长生', ('辛', '辰'): '墓',
            ('壬', '申'): '长生', ('壬', '辰'): '墓', ('癸', '卯'): '长生', ('癸', '未'): '墓',
        }
        for (gan, zhi), stage in table.items():
            self.assertEqual(changsheng_stage(gan, zhi), stage, (gan, zhi))

    def test_lu_and_yangren_tables(self):
        lu = dict(zip('甲乙丙丁戊己庚辛壬癸', '寅卯巳午巳午申酉亥子'))
        for gan, zhi in lu.items():
            self.assertEqual(lu_branch(gan), zhi, gan)
        ren = {'甲': '卯', '丙': '午', '戊': '午', '庚': '酉', '壬': '子'}
        for gan in '甲乙丙丁戊己庚辛壬癸':
            self.assertEqual(yangren_branch(gan), ren.get(gan), gan)

    def test_month_state_matches_spring_wood_rule(self):
        # 春月木旺、火相、水休、金囚、土死
        expected = {'木': '旺', '火': '相', '水': '休', '金': '囚', '土': '死'}
        for wx, state in expected.items():
            self.assertEqual(month_state(wx, '木'), state, wx)

    def test_natal_relations_for_known_pillars(self):
        # 丁亥 丙午 壬午 癸卯
        result = build_structure(list('丁丙壬癸'), list('亥午午卯'))
        relations = result['原局关系']
        self.assertEqual(kinds(relations['天干']), [('五合', '丁壬'), ('相冲', '丁癸'), ('相冲', '丙壬')])
        self.assertEqual(kinds(relations['地支']), [
            ('半合', '亥卯'), ('同支', '午午'), ('相破', '午卯'), ('相破', '午卯'),
            ('自刑', '午午'),
        ])
        self.assertEqual(relations['三支成组'], [])
        self.assertEqual(relations['同柱'], [])
        self.assertEqual(result['禄刃']['禄'], {'地支': '亥', '位置': ['年柱']})
        self.assertEqual(result['禄刃']['羊刃'], {'地支': '子', '位置': []})
        self.assertEqual(result['月令']['日主月令状态'], '囚')
        self.assertEqual(result['月令']['本气十神'], '正财')
        self.assertEqual(result['天干通根'][3]['自坐十二长生'], '长生')
        day_roots = [(row['地支'], row['藏干'], row['层']) for row in result['天干通根'][2]['根']]
        self.assertEqual(day_roots, [('亥', '壬', '本气')])

    def test_hidden_stem_layers_and_transparency(self):
        result = build_structure(list('丁丙壬癸'), list('亥午午卯'))
        wu = result['藏干明细'][1]['藏干']
        self.assertEqual([(r['天干'], r['层'], r['权重']) for r in wu],
                         [('丁', '本气', 0.7), ('己', '中气', 0.3)])
        self.assertEqual(wu[0]['透干'], ['年柱'])
        self.assertEqual(wu[1]['透干'], [])

    def test_full_groups_and_pair_overlaps(self):
        result = build_structure(list('甲丙戊庚'), list('寅巳申子'))
        relations = result['原局关系']
        self.assertIn(('三刑全', '寅巳申'), kinds(relations['三支成组']))
        pair = [row['类型'] for row in relations['地支'] if set(row['地支']) == {'巳', '申'}]
        self.assertEqual(sorted(pair), ['六合', '相破'])
        gong = [row for row in build_structure(list('甲丙戊庚'), list('申辰午戌'))['原局关系']['地支']
                if set(row['地支']) == {'申', '辰'}]
        self.assertEqual([(r['类型'], r['缺']) for r in gong], [('拱合', '子')])

    def test_completed_group_suppresses_its_partial_pairs(self):
        # 庚午 癸未 辛巳 甲午：巳午未三会齐全
        relations = build_structure(list('庚癸辛甲'), list('午未巳午'))['原局关系']
        self.assertEqual(kinds(relations['三支成组']), [('三会方', '巳午未')])
        self.assertEqual(kinds(relations['地支']),
                         [('六合', '午未'), ('六合', '未午'), ('同支', '午午'), ('自刑', '午午')])
        liuhe = next(r for r in relations['地支'] if r['类型'] == '六合')
        self.assertEqual(liuhe['合化五行'], ['火', '土'])

    def test_storage_branch_layers_and_seasonal_state(self):
        # 辰：乙为春木余气、癸为水库中气；戌丑未同理
        expected = {'辰': [('戊', '本气'), ('乙', '余气'), ('癸', '中气')],
                    '戌': [('戊', '本气'), ('辛', '余气'), ('丁', '中气')],
                    '丑': [('己', '本气'), ('癸', '余气'), ('辛', '中气')],
                    '未': [('己', '本气'), ('丁', '余气'), ('乙', '中气')],
                    '寅': [('甲', '本气'), ('丙', '中气'), ('戊', '余气')]}
        for zhi, layers in expected.items():
            rows = build_structure(list('甲丙甲丙'), [zhi] * 4)['藏干明细'][0]['藏干']
            self.assertEqual([(r['天干'], r['层']) for r in rows], layers, zhi)
        month = build_structure(list('丙戊甲庚'), list('子辰午申'))['月令']
        self.assertEqual((month['日主月令状态'], month['季月'], month['所属季节五行'],
                          month['按季节五行状态']), ('囚', True, '木', '旺'))
        plain = build_structure(list('丙戊甲庚'), list('子卯午申'))['月令']
        self.assertEqual((plain['季月'], plain['日主月令状态'], plain['按季节五行状态']),
                         (False, '旺', '旺'))

    def test_gong_hui_same_branch_and_natal_fuyin(self):
        relations = build_structure(list('甲丙甲庚'), list('寅辰寅子'))['原局关系']
        pair = [r for r in relations['地支'] if set(r['地支']) == {'寅', '辰'}]
        self.assertEqual({(r['类型'], r['缺']) for r in pair}, {('拱会', '卯')})
        self.assertIn(('同支', '寅寅'), kinds(relations['地支']))
        self.assertNotIn(('自刑', '寅寅'), kinds(relations['地支']))
        self.assertEqual([(r['干支'], r['位置']) for r in relations['同柱']],
                         [('甲寅', ['年柱', '日柱'])])
        full = build_structure(list('甲丙戊庚'), list('寅巳申子'))['原局关系']
        self.assertNotIn('相刑', [r['类型'] for r in full['地支']])

    def test_incoming_relations_list_only_new_groups(self):
        gans, zhis = list('丁丙壬癸'), list('亥午午卯')
        row = incoming_relations('乙未', gans, zhis)
        self.assertEqual([g['地支'] for g in row['三支成组']], ['亥卯未'])
        self.assertIn(('六合', '午'), [(r['类型'], r['对应']) for r in row['地支']])
        same = incoming_relations('壬午', gans, zhis)['同柱']
        self.assertEqual(same, [{'类型': '伏吟', '位置': '日柱'}])
        clash = incoming_relations('丙子', gans, zhis)['同柱']
        self.assertEqual(clash, [{'类型': '天干地支俱冲', '位置': '日柱'}])

    def test_calc_bazi_exposes_structure_consistent_with_pillars(self):
        subject = {'birth_date': '2000-01-15', 'date_calendar': 'gregorian',
                   'calculation_sex': 'm', 'location': {'latitude': 30.0, 'longitude': 120.0}}
        time_input = {'precision': 'minute', 'start': '2000-01-15T12:00', 'end': None,
                      'branch_label': None, 'timezone_name': None, 'utc_offset_hours': 8,
                      'fold': None, 'clock_basis': 'civil'}
        context = normalize_birth_time(subject, time_input, as_of='2026-01-15')
        data = calc_bazi(context, 'm', timing_request={'years': [2026], 'months': [],
                                                        'systems': ['bazi']})['data']
        structure = data['结构']
        self.assertEqual([r['地支'] for r in structure['藏干明细']],
                         [p['地支'] for p in data['四柱']])
        self.assertEqual(structure['月令']['月支'], data['四柱'][1]['地支'])
        self.assertEqual([r['干支'] for r in structure['大运与原局']],
                         [r['干支'] for r in data['大运']])
        self.assertEqual([r['year'] for r in structure['流年与原局']], [2026])
        for verdict in ('旺衰', '身强', '身弱', '格局', '用神', '喜神', '忌神'):
            self.assertNotIn(verdict, structure)


if __name__ == '__main__':
    unittest.main()
