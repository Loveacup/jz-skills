"""Derived Jung profile structure checked against hand-written type tables and hand arithmetic."""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from jung_structure import (  # noqa: E402
    build_structure, build_type_structure, full_stack, parse_type_code,
)

# 通行对照表：每型八个位置的功能（Beebe 八原型模型的排列），逐型手写
EIGHT_POSITIONS = {
    'ISTJ': 'Si Te Fi Ne Se Ti Fe Ni', 'ISFJ': 'Si Fe Ti Ne Se Fi Te Ni',
    'INFJ': 'Ni Fe Ti Se Ne Fi Te Si', 'INTJ': 'Ni Te Fi Se Ne Ti Fe Si',
    'ISTP': 'Ti Se Ni Fe Te Si Ne Fi', 'ISFP': 'Fi Se Ni Te Fe Si Ne Ti',
    'INFP': 'Fi Ne Si Te Fe Ni Se Ti', 'INTP': 'Ti Ne Si Fe Te Ni Se Fi',
    'ESTP': 'Se Ti Fe Ni Si Te Fi Ne', 'ESFP': 'Se Fi Te Ni Si Fe Ti Ne',
    'ENFP': 'Ne Fi Te Si Ni Fe Ti Se', 'ENTP': 'Ne Ti Fe Si Ni Te Fi Se',
    'ESTJ': 'Te Si Ne Fi Ti Se Ni Fe', 'ESFJ': 'Fe Si Ne Ti Fi Se Ni Te',
    'ENFJ': 'Fe Ni Se Ti Fi Ne Si Te', 'ENTJ': 'Te Ni Se Fi Ti Ne Si Fe',
}
TEMPLATE = [42, 37, 33, 24, 31, 31, 20, 22]
INTJ_LIKE = {'Ni': 28, 'Te': 25, 'Fi': 20, 'Se': 8, 'Ne': 18, 'Ti': 17, 'Fe': 6, 'Si': 9}


def profile_for(type_code, values=TEMPLATE):
    return dict(zip(EIGHT_POSITIONS[type_code].split(), values))


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / 'jung_calc.py'), *args],
                          cwd=ROOT, text=True, capture_output=True, check=False)


class StackTableTests(unittest.TestCase):
    def test_eight_positions_match_handwritten_table(self):
        for type_code, row in EIGHT_POSITIONS.items():
            self.assertEqual(full_stack(type_code), row.split(), type_code)

    def test_type_only_structure_names_pair_and_axes(self):
        result = build_type_structure('ENFJ')
        self.assertEqual(result['主辅搭配'], 'Fe-Ni')
        self.assertEqual(result['主导轴'], 'Ti–Fe')
        self.assertEqual(result['辅助轴'], 'Se–Ni')
        self.assertEqual([row['功能'] for row in result['功能栈']], EIGHT_POSITIONS['ENFJ'].split())
        self.assertEqual(result['功能栈'][3]['位置名'], '劣势')


class ProfileArithmeticTests(unittest.TestCase):
    def setUp(self):
        self.result = build_structure(INTJ_LIKE, 30)

    def test_ranking_gaps_and_range(self):
        ranked = self.result['排序']
        self.assertEqual([row['功能'] for row in ranked],
                         [['Ni'], ['Te'], ['Fi'], ['Ne'], ['Ti'], ['Si'], ['Se'], ['Fe']])
        self.assertEqual([row['与下一名差'] for row in ranked], [3, 5, 2, 1, 8, 1, 2, None])
        self.assertEqual(self.result['极差']['差'], 22)
        self.assertEqual(self.result['极差']['差占量程'], round(22 / 30, 4))

    def test_tiers_cut_at_two_largest_gaps(self):
        # 最大两处分差：Ti→Si 的 8 与 Te→Fi 的 5
        layers = self.result['分层']
        self.assertEqual([layer['功能'] for layer in layers],
                         [['Ni', 'Te'], ['Fi', 'Ne', 'Ti'], ['Si', 'Se', 'Fe']])
        self.assertEqual([layer['与下一层差'] for layer in layers], [5, 8, None])

    def test_axes_and_totals(self):
        axes = {row['轴']: row for row in self.result['对立轴']}
        self.assertEqual((axes['Te–Fi']['差'], axes['Te–Fi']['偏向']), (5, 'Te'))
        self.assertEqual((axes['Ti–Fe']['差'], axes['Ti–Fe']['偏向']), (11, 'Ti'))
        self.assertEqual((axes['Se–Ni']['差'], axes['Se–Ni']['偏向']), (-20, 'Ni'))
        self.assertEqual((axes['Si–Ne']['差'], axes['Si–Ne']['偏向']), (-9, 'Ne'))
        totals = self.result['合计']
        self.assertEqual(totals['态度']['外倾功能合计'], 57)
        self.assertEqual(totals['态度']['内倾功能合计'], 74)
        self.assertEqual(totals['判断与知觉']['判断功能合计'], 68)
        self.assertEqual(totals['判断与知觉']['知觉功能合计'], 63)
        self.assertEqual(totals['感觉与直觉']['偏向'], '直觉合计')
        self.assertEqual(totals['思考与情感']['偏向'], '思考合计')

    def test_tied_ranks_share_a_place(self):
        scores = dict(INTJ_LIKE, Te=28)
        ranked = build_structure(scores, 30)['排序']
        self.assertEqual(ranked[0]['功能'], ['Ni', 'Te'])
        self.assertEqual(ranked[1]['名次'], 3)


class TypeFitTests(unittest.TestCase):
    def test_every_type_template_profile_returns_that_type_with_fit_one(self):
        for type_code in EIGHT_POSITIONS:
            fit = build_structure(profile_for(type_code), 60)['类型贴合度']
            self.assertEqual(fit['首选'], [type_code])
            self.assertEqual(fit['候选'][0]['贴合度'], 1.0)
            self.assertEqual(len(fit['候选']), 16)
            self.assertGreaterEqual(len(fit['备选']), 2)

    def test_fit_is_pearson_correlation_and_ignores_linear_rescaling(self):
        halved = profile_for('ENFP', [value / 2 + 3 for value in TEMPLATE])
        self.assertEqual(build_structure(halved, 30)['类型贴合度']['候选'][0]['贴合度'], 1.0)
        mirrored = profile_for('ENFP', [62 - value for value in TEMPLATE])
        rows = {row['类型']: row for row in build_structure(mirrored, 60)['类型贴合度']['候选']}
        self.assertEqual(rows['ENFP']['贴合度'], -1.0)
        fit = {row['类型']: row['贴合度'] for row in build_structure(INTJ_LIKE, 30)['类型贴合度']['候选']}
        for type_code in ('INTJ', 'ENTJ', 'ESFP'):
            actual = [INTJ_LIKE[f] for f in EIGHT_POSITIONS[type_code].split()]
            self.assertAlmostEqual(fit[type_code], statistics.correlation(actual, TEMPLATE), places=4)

    def test_clear_profile_names_dominant_auxiliary_and_neighbours(self):
        fit = build_structure(INTJ_LIKE, 30)['类型贴合度']
        self.assertEqual(fit['首选'], ['INTJ'])
        self.assertFalse(fit['并列'])
        top = fit['候选'][0]
        self.assertEqual((top['主导'], top['辅助'], top['第三'], top['劣势']), ('Ni', 'Te', 'Fi', 'Se'))
        self.assertEqual(top['主辅搭配'], 'Ni-Te')
        self.assertEqual(fit['首选主辅分差'], 3)
        self.assertEqual(fit['首选主导劣势分差'], 20)
        near = {row['关系']: row for row in fit['邻近型辨析']}
        self.assertEqual(near['主辅对调']['类型'], 'ENTJ')
        self.assertEqual(near['主辅对调']['判别'], {'首选一侧': 'Ni', '邻近型一侧': 'Te', '差': 3, '偏向': '首选'})
        self.assertEqual(near['同主导换辅助']['类型'], 'INFJ')
        self.assertEqual(near['同主导换辅助']['判别']['差'], 25 - 6)
        self.assertEqual(near['同辅助换主导']['类型'], 'ISTJ')
        self.assertEqual(near['同辅助换主导']['判别']['差'], 28 - 9)

    def test_symmetric_profile_gives_joint_hypothesis(self):
        # Fe=Si、Ne=Ti、Ni=Te、Se=Fi：ESFJ 与 ISFJ 的八个位置逐位同分，贴合度必然相等
        scores = {'Fe': 25, 'Si': 25, 'Ne': 15, 'Ti': 15, 'Fi': 18, 'Se': 18, 'Ni': 6, 'Te': 6}
        fit = build_structure(scores, 30)['类型贴合度']
        self.assertTrue(fit['并列'])
        self.assertEqual(sorted(fit['首选']), ['ESFJ', 'ISFJ'])
        self.assertEqual(fit['首选与次选贴合度差'], 0)

    def test_joint_hypothesis_expands_every_first_choice(self):
        scores = {'Fe': 25, 'Si': 25, 'Ne': 15, 'Ti': 15, 'Fi': 18, 'Se': 18, 'Ni': 6, 'Te': 6}
        fit = build_structure(scores, 30)['类型贴合度']
        self.assertEqual(sorted(row['类型'] for row in fit['各首选展开']), ['ESFJ', 'ISFJ'])
        self.assertEqual(fit['展开类型'], fit['首选'][0])
        by_type = {row['类型']: row for row in fit['各首选展开']}
        self.assertEqual([r['功能'] for r in by_type['ISFJ']['功能栈']], EIGHT_POSITIONS['ISFJ'].split())
        self.assertEqual(by_type['ISFJ']['主导劣势分差'], 25 - 15)
        self.assertEqual(fit['首选功能栈'], by_type[fit['展开类型']]['功能栈'])

    def test_flat_profile_gives_no_hypothesis(self):
        result = build_structure({name: 12 for name in INTJ_LIKE}, 30)
        self.assertEqual(result['类型贴合度']['候选'], [])
        self.assertEqual(result['类型贴合度']['首选'], [])
        self.assertFalse(result['类型贴合度']['可定假说'])
        self.assertIn('全部相同', result['类型贴合度']['说明'])
        self.assertEqual(result['分层'], [])
        self.assertEqual(len(result['排序']), 1)

    def test_nearly_flat_profiles_give_no_first_choice(self):
        one_up = {name: 20.0 for name in INTJ_LIKE}
        one_up['Fe'] = 20.001
        drift = {name: 20.0 + index * 0.00001 for index, name in enumerate(INTJ_LIKE)}
        below = dict({name: 10.0 for name in INTJ_LIKE}, Ni=11.9)   # 极差 1.9，量程 40，占 0.0475
        for scores in (one_up, drift, below):
            result = build_structure(scores, 40)
            fit = result['类型贴合度']
            self.assertFalse(fit['可定假说'])
            self.assertEqual((fit['首选'], fit['备选'], fit['各首选展开']), ([], [], []))
            self.assertIn('拉不开', fit['说明'])
            self.assertNotIn('全部相同', fit['说明'])
            self.assertEqual(result['分层'], [])
        at_threshold = dict({name: 10.0 for name in INTJ_LIKE}, Ni=12.0)  # 极差 2，占 0.05
        self.assertTrue(build_structure(at_threshold, 40)['类型贴合度']['可定假说'])

    def test_fit_keys_are_the_same_in_every_case(self):
        keys = {'可定假说', '说明', '候选', '首选', '并列', '首选与次选贴合度差', '备选', '展开类型',
                '首选功能栈', '首选主辅分差', '首选主导劣势分差', '邻近型辨析', '各首选展开'}
        cases = [INTJ_LIKE, {name: 12 for name in INTJ_LIKE},
                 dict({name: 20.0 for name in INTJ_LIKE}, Fe=20.001),
                 {'Fe': 25, 'Si': 25, 'Ne': 15, 'Ti': 15, 'Fi': 18, 'Se': 18, 'Ni': 6, 'Te': 6}]
        for scores in cases:
            self.assertEqual(set(build_structure(scores, 30)['类型贴合度']), keys)
        clear = build_structure(INTJ_LIKE, 30)['类型贴合度']
        self.assertIsNone(clear['说明'])
        flat = build_structure({name: 12 for name in INTJ_LIKE}, 30)['类型贴合度']
        self.assertEqual((flat['首选功能栈'], flat['邻近型辨析'], flat['展开类型'],
                          flat['首选主辅分差'], flat['首选与次选贴合度差']), ([], [], None, None, None))


class SubtypeTests(unittest.TestCase):
    SCORES = {
        'NiO': 14, 'NiB': 26, 'FeA': 16, 'FeH': 22, 'TiA': 13, 'TiH': 11, 'SeO': 9, 'SeB': 11,
        'NeO': 15, 'NeB': 19, 'FiA': 14, 'FiH': 16, 'TeA': 10, 'TeH': 12, 'SiO': 15, 'SiB': 15,
    }

    def setUp(self):
        self.result = build_structure(None, 30, scores16=self.SCORES, reported_type='INFJBH')

    def test_function_scores_are_pair_means_with_sums_listed(self):
        scores = self.result['功能分']
        self.assertEqual(scores['来源'], '两亚型均值')
        self.assertEqual(scores['各功能'], {'Se': 10, 'Si': 15, 'Ne': 17, 'Ni': 20,
                                         'Te': 11, 'Ti': 12, 'Fe': 19, 'Fi': 15})
        self.assertEqual(scores['两亚型合计']['Ni'], 40)
        self.assertIn('约定', self.result['取法']['功能分'])

    def test_pair_direction_and_group_totals(self):
        pairs = {row['功能']: row for row in self.result['亚型']['各功能']}
        self.assertEqual((pairs['Ni']['差'], pairs['Ni']['偏向'], pairs['Ni']['差的方向']), (12, 'B', 'B−O'))
        self.assertEqual((pairs['Ti']['差'], pairs['Ti']['偏向']), (-2, 'A'))
        self.assertEqual((pairs['Si']['差'], pairs['Si']['偏向']), (0, '持平'))
        self.assertEqual((pairs['Fe']['差'], pairs['Fe']['差的方向']), (6, 'H−A'))
        self.assertEqual(self.result['亚型']['十六项合计'], 238)
        self.assertTrue(self.result['亚型']['合计偏离240'])
        perceiving = self.result['亚型']['知觉四功能']
        self.assertEqual((perceiving['主体O合计'], perceiving['背景B合计'], perceiving['偏向']), (53, 71, 'B'))
        self.assertFalse(perceiving['四功能同向'])
        judging = self.result['亚型']['判断四功能']
        self.assertEqual((judging['分析A合计'], judging['整体H合计'], judging['偏向']), (53, 61, 'H'))
        self.assertFalse(judging['四功能同向'])

    def test_total_flag_only_for_subtype_input_and_within_tolerance(self):
        on_target = dict(self.SCORES, SiB=17)   # 合计 240
        self.assertFalse(build_structure(None, 30, scores16=on_target)['亚型']['合计偏离240'])
        rounding = dict(self.SCORES, SiB=16.2)  # 合计 239.2，属四舍五入范围
        self.assertFalse(build_structure(None, 30, scores16=rounding)['亚型']['合计偏离240'])
        self.assertNotIn('亚型', build_structure(INTJ_LIKE, 30))

    def test_suffix_follows_leading_perceiving_and_judging_functions(self):
        self.assertEqual(self.result['类型贴合度']['首选'], ['INFJ'])
        suffix = self.result['亚型']['候选后缀'][0]
        self.assertEqual((suffix['主要知觉功能'], suffix['第五字母']), ('Ni', 'B'))
        self.assertEqual((suffix['主要判断功能'], suffix['第六字母']), ('Fe', 'H'))
        self.assertEqual(suffix['六字母'], 'INFJBH')

    def test_reported_type_is_compared_not_recomputed(self):
        reported = self.result['测验自带类型']
        self.assertEqual((reported['四字母'], reported['后缀']), ('INFJ', 'BH'))
        self.assertTrue(reported['与首选一致'])
        self.assertTrue(reported['后缀一致'])
        self.assertEqual(reported['在候选中的名次'], 1)
        other = build_structure(None, 30, scores16=self.SCORES, reported_type='ESTP')['测验自带类型']
        self.assertFalse(other['与首选一致'])
        self.assertGreater(other['在候选中的名次'], 3)
        unknown = build_structure(None, 30, scores16=self.SCORES, reported_type='调停者')['测验自带类型']
        self.assertFalse(unknown['可识别'])

    def test_type_code_parser(self):
        self.assertEqual(parse_type_code('entpoa'), {'四字母': 'ENTP', '后缀': 'OA'})
        self.assertEqual(parse_type_code('INTJ'), {'四字母': 'INTJ', '后缀': None})
        for bad in ('ENTPO', 'ENTPAO', 'XNTP', 'INTJ-A', '', None):
            self.assertIsNone(parse_type_code(bad), bad)


class CliTests(unittest.TestCase):
    def test_scores16_adds_structure_and_keeps_existing_keys(self):
        result = run_cli('--scores16', json.dumps(SubtypeTests.SCORES), '--scale', '30',
                         '--reported-type', 'INFJBH')
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertIsNone(output['derived_functions'])
        self.assertEqual(len(output['pairs']), 8)
        self.assertEqual(output['结构']['类型贴合度']['首选'], ['INFJ'])
        self.assertEqual(output['结构']['测验自带类型']['原文'], 'INFJBH')
        serialized = json.dumps(output, ensure_ascii=False).lower()
        for forbidden in ('confidence', '置信度', '能力薄弱', '弱项', '低能力'):
            self.assertNotIn(forbidden, serialized)

    def test_scores8_adds_structure_without_reported_type(self):
        result = run_cli('--scores', json.dumps(INTJ_LIKE), '--scale', '30')
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output['结构']['功能分']['来源'], '原始八功能分')
        self.assertNotIn('测验自带类型', output['结构'])
        self.assertNotIn('亚型', output['结构'])
        self.assertIn('ranked_tiers', output)

    def test_type_mode_gets_stack_structure_and_rejects_reported_type(self):
        result = run_cli('--type', 'ISFP')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['结构']['主辅搭配'], 'Fi-Se')
        self.assertIsNone(json.loads(result.stdout)['结构']['后缀'])
        six = run_cli('--type', 'entjoa')
        self.assertEqual(six.returncode, 0, six.stderr)
        output = json.loads(six.stdout)
        self.assertEqual(output['self_reported_type'], 'ENTJ')
        self.assertEqual((output['结构']['原文'], output['结构']['后缀']), ('ENTJOA', 'OA'))
        self.assertEqual([row['function'] for row in output['theory_mapping']['stack']],
                         EIGHT_POSITIONS['ENTJ'].split())
        for bad in ('ENTJO', 'ENTJAO', 'WXYZ'):
            self.assertEqual(run_cli('--type', bad).returncode, 2, bad)
        rejected = run_cli('--type', 'ISFP', '--reported-type', 'ISFP')
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(json.loads(rejected.stdout)['status'], 'error')


if __name__ == '__main__':
    unittest.main()
