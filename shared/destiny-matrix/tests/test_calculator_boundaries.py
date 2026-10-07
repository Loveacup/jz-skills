"""Consumer-visible calculator boundaries with independent documented anchors."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from _common import InputError, match_aspect, normalize_birth_time, resolve_orbs  # noqa: E402
from astro_calc import calc_chart  # noqa: E402
from bazi_calc import calc_bazi  # noqa: E402
from ziwei_calc import calc_ziwei  # noqa: E402


class CalculatorBoundaryTests(unittest.TestCase):
    def context(self, date, local_time, *, zone='Asia/Shanghai', offset=None,
                lat=31.23, lon=121.47, calculation_sex='m'):
        subject = {
            'birth_date': date, 'date_calendar': 'gregorian',
            'calculation_sex': calculation_sex,
            'location': {'latitude': lat, 'longitude': lon},
        }
        time_input = {
            'precision': 'minute', 'start': f'{date}T{local_time}', 'end': None,
            'branch_label': None, 'timezone_name': zone,
            'utc_offset_hours': offset, 'fold': None, 'clock_basis': 'civil',
        }
        return normalize_birth_time(subject, time_input, as_of='2026-01-15')

    @staticmethod
    def pillar_map(data):
        return {row['柱']: row['干支'] for row in data['四柱']}

    def test_lunar_python_zi_hour_sect_behavior_is_preserved(self):
        """Pinned probe from lunar-python 1.4.8, not values generated as test expectations."""
        context = self.context('2000-01-01', '23:30:00')
        midnight = calc_bazi(context, 'm', zi_hour_rule='midnight',
                              analysis_as_of='2026-01-15', timing_request={'systems': []})
        zi_start = calc_bazi(context, 'm', zi_hour_rule='zi_start',
                             analysis_as_of='2026-01-15', timing_request={'systems': []})
        self.assertEqual(self.pillar_map(midnight['data'])['日柱'], '戊午')
        self.assertEqual(self.pillar_map(midnight['data'])['时柱'], '甲子')
        self.assertEqual(self.pillar_map(zi_start['data'])['日柱'], '己未')
        self.assertEqual(self.pillar_map(zi_start['data'])['时柱'], '甲子')
        self.assertEqual(midnight['data']['子时规则'], 'midnight')
        self.assertEqual(zi_start['data']['子时规则'], 'zi_start')

    def test_same_instant_in_two_timezones_has_same_term_and_apparent_clock(self):
        shanghai = self.context('2024-02-04', '16:27:00', zone='Asia/Shanghai')
        utc = self.context('2024-02-04', '08:27:00', zone='UTC')
        self.assertEqual(shanghai['utc_instant'], utc['utc_instant'])
        self.assertEqual(shanghai['term_datetime'], utc['term_datetime'])
        self.assertEqual(shanghai['local_apparent_datetime'], utc['local_apparent_datetime'])
        first = calc_bazi(shanghai, 'm', analysis_as_of='2026-01-15',
                          timing_request={'systems': []})['data']
        second = calc_bazi(utc, 'm', analysis_as_of='2026-01-15',
                           timing_request={'systems': []})['data']
        for name in ('年柱', '月柱'):
            self.assertEqual(self.pillar_map(first)[name], self.pillar_map(second)[name])
        self.assertEqual(first['节气时间轴'], second['节气时间轴'])

    def test_annual_and_monthly_validity_uses_exact_term_instants(self):
        """HKO publishes 2024 Lichun at 16:27 and 2026 at 04:02, UTC+08, minute precision."""
        context = self.context('2000-01-15', '12:00:00')
        result = calc_bazi(
            context, 'm', analysis_as_of='2026-01-15',
            timing_request={'years': [2024, 2026], 'months': [{'year': 2026, 'month': 2}],
                            'systems': ['bazi']},
        )['data']
        years = {row['year']: row for row in result['流年']}
        for year, expected in ((2024, '2024-02-04T16:27:00+08:00'),
                               (2026, '2026-02-04T04:02:00+08:00')):
            actual = datetime.fromisoformat(years[year]['validity']['start'])
            target = datetime.fromisoformat(expected)
            self.assertLessEqual(abs((actual - target).total_seconds()), 60)
            self.assertEqual(years[year]['validity']['timezone'], 'UTC+08:00')
            self.assertLess(years[year]['validity']['start'], years[year]['validity']['end'])
        february = result['流月查询'][0]
        self.assertEqual(february['gregorian_month']['start'], '2026-02-01T00:00:00+08:00')
        self.assertEqual(february['gregorian_month']['end'], '2026-03-01T00:00:00+08:00')
        boundary = february['solar_term_month_segments'][0]['validity']['end']
        actual = datetime.fromisoformat(boundary)
        target = datetime.fromisoformat('2026-02-04T04:02:00+08:00')
        self.assertLessEqual(abs((actual - target).total_seconds()), 60)

    def test_uncertain_range_exposes_distinct_discrete_candidates(self):
        subject = {
            'birth_date': '1991-04-03', 'date_calendar': 'gregorian',
            'calculation_sex': 'm',
            'location': {'latitude': 30, 'longitude': 121},
        }
        time_input = {
            'precision': 'range', 'start': '1991-04-03T06:50:00',
            'end': '1991-04-03T07:10:00', 'branch_label': None,
            'timezone_name': 'Asia/Shanghai', 'utc_offset_hours': None,
            'fold': None, 'clock_basis': 'civil',
        }
        context = normalize_birth_time(subject, time_input, as_of='2026-01-15')
        bazi = calc_bazi(context, 'm', analysis_as_of='2026-01-15',
                         timing_request={'systems': []})
        self.assertEqual(bazi['status'], 'partial')
        self.assertIsNone(bazi['data'])
        branches = {row['data']['四柱'][3]['地支'] for row in bazi['candidates']}
        self.assertEqual(branches, {'卯', '辰'})
        self.assertTrue(all(row['validity'] for row in bazi['candidates']))
        ziwei = calc_ziwei(context, 'm', '2026-01-15')
        self.assertEqual(ziwei['status'], 'partial')
        self.assertIsNone(ziwei['data'])
        self.assertGreaterEqual(len(ziwei['candidates']), 2)
        astro = calc_chart(context)
        self.assertEqual(astro['status'], 'partial')
        self.assertIsNone(astro['data'])

    def test_timing_system_filter_does_not_invent_bazi_months(self):
        context = self.context('2000-01-15', '12:00:00')
        result = calc_bazi(
            context, 'm', analysis_as_of='2026-01-15',
            timing_request={'years': [2026], 'months': [{'year': 2026, 'month': 2}],
                            'systems': ['ziwei']},
        )['data']
        self.assertEqual(result['流年'], [])
        self.assertEqual(result['流月查询'], [])

    def test_missing_calculation_sex_never_defaults_yun(self):
        context = self.context('2000-01-15', '12:00:00', calculation_sex=None)
        result = calc_bazi(context, None, analysis_as_of='2026-01-15',
                           timing_request={'systems': []})
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['data']['起运']['status'], 'unavailable')
        self.assertIn('不默认性别', result['data']['起运']['reason'])
        ziwei = calc_ziwei(context, None, '2026-01-15')
        self.assertEqual(ziwei['status'], 'missing_input')

    def test_placidus_failure_keeps_angles_without_switching_house_system(self):
        """Polar Placidus can fail while house-independent ASC/MC remain computable."""
        context = self.context('2024-06-01', '12:00:00', zone='UTC', lat=89.9, lon=0)
        placidus = calc_chart(context, house_system='placidus')
        whole_sign = calc_chart(context, house_system='whole_sign')
        self.assertEqual(placidus['status'], 'partial')
        self.assertEqual(placidus['data']['requested_house_system'], 'placidus')
        self.assertEqual(placidus['data']['宫位制'], 'unavailable')
        self.assertTrue(any('Placidus 宫位不可用' in item for item in placidus['limitations']))
        self.assertIsNotNone(placidus['data']['ASC_MC_原始黄经'])
        self.assertTrue(all(
            0 <= placidus['data']['ASC_MC_原始黄经'][key] < 360
            for key in ('ASC', 'MC')
        ))
        self.assertIn('上升', placidus['data']['三轴心'])
        self.assertIn('天顶MC', placidus['data']['三轴心'])
        self.assertIsNone(placidus['data']['十二宫始黄经'])
        self.assertEqual(whole_sign['status'], 'ok')
        self.assertEqual(whole_sign['data']['宫位制'], 'Whole Sign')
        cusps = whole_sign['data']['十二宫始黄经']
        self.assertEqual(len(cusps), 12)
        self.assertTrue(all(0 <= value < 360 for value in cusps))

    def test_ziwei_uses_the_original_lunar_leap_date(self):
        """HKO 2023 calendar: 2023-03-22 is leap-second-month day 1."""
        subject = {
            'birth_date': None, 'date_calendar': 'gregorian',
            'lunar_date': {
                'year': 2023, 'month': 2, 'day': 1, 'is_leap_month': True,
            },
            'calculation_sex': 'm',
            'location': {'latitude': 43.8, 'longitude': 87.6},
        }
        time_input = {
            'precision': 'minute', 'start': '2023-03-22T01:00:00',
            'end': None, 'branch_label': None, 'timezone_name': None,
            'utc_offset_hours': 8.0, 'fold': None, 'clock_basis': 'civil',
        }
        context = normalize_birth_time(subject, time_input, as_of='2026-01-15')
        result = calc_ziwei(context, 'm', '2026-01-15')
        self.assertEqual(result['status'], 'ok')
        self.assertIn('闰二月初一', result['data']['基础信息']['农历日期'])

    def test_aspect_boundary_uses_unrounded_angle_and_known_keys(self):
        profile_id, default_orbs = resolve_orbs(None)
        self.assertEqual(profile_id, 'standard-v1')
        self.assertEqual(default_orbs['conjunction'], 8.0)
        exact_boundary = match_aspect(0, 8.0, default_orbs)
        self.assertEqual(exact_boundary['aspect'], 'conjunction')
        self.assertEqual(exact_boundary['exact_diff'], 8.0)
        wraparound = match_aspect(359, 1, {'conjunction': 2, 'opposition': 0,
                                           'trine': 0, 'square': 0, 'sextile': 0})
        self.assertEqual(wraparound['angle'], 2.0)
        self.assertIsNone(match_aspect(0, 8.0001, default_orbs))
        with self.assertRaises(InputError):
            resolve_orbs({'unknown': 2})
        with self.assertRaises(InputError):
            resolve_orbs({'conjunction': float('nan')})

    def test_astro_reports_actual_flags_and_optional_points(self):
        context = self.context('2000-01-15', '12:00:00')
        result = calc_chart(context)
        self.assertIn(result['status'], {'ok', 'partial'})
        self.assertIn('莉莉丝', result['data']['十大行星+北交+凯龙+莉莉丝'])
        for planet in ('太阳', '月亮', '水星', '北交点'):
            method = result['methods']['planets'][planet]
            self.assertIn('requested_flags', method)
            self.assertIn('returned_flags', method)
            self.assertIn(method['engine'], {'SWIEPH', 'MOSEPH'})
        cusps = result['data']['十二宫始黄经']
        if cusps is not None:
            self.assertEqual(len(cusps), 12)
            self.assertTrue(all(math.isfinite(value) and 0 <= value < 360 for value in cusps))

    def test_child_cli_uses_structured_error_and_exit_two_for_bad_arguments(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'bazi_calc.py'), '--unknown'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['status'], 'error')
        self.assertEqual(payload['errors'][0]['code'], 'unknown_argument')
        self.assertTrue(result.stderr.strip())


if __name__ == '__main__':
    unittest.main()
