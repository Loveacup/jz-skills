"""Verified input-time normalization behavior and independent calendar anchors."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from _common import InputError, normalize_birth_time  # noqa: E402


class TimePipelineTests(unittest.TestCase):
    def normalize(self, start, *, zone=None, offset=None, date=None,
                  precision='minute', end=None, fold=None, branch=None,
                  lat=40.7, lon=-74.0, basis='civil', calendar='gregorian'):
        date = date or start[:10]
        subject = {
            'birth_date': date, 'date_calendar': calendar,
            'location': {'latitude': lat, 'longitude': lon},
        }
        time_input = {
            'precision': precision, 'start': start, 'end': end,
            'branch_label': branch, 'timezone_name': zone,
            'utc_offset_hours': offset, 'fold': fold, 'clock_basis': basis,
        }
        return normalize_birth_time(subject, time_input, as_of='2026-01-15')

    @staticmethod
    def elapsed_hours(context):
        total = 0.0
        for interval in context['candidate_intervals']:
            start = datetime.fromisoformat(interval['start_utc'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(interval['end_utc'].replace('Z', '+00:00'))
            total += (end - start).total_seconds() / 3600
        return total

    def test_chicago_time_equation_matches_recorded_independent_probe(self):
        """NOAA local-solar formula; literal Swiss Ephemeris probe recorded in approved plan."""
        context = self.normalize('1990-07-15T12:00:00', zone='America/Chicago',
                                 lat=41.88, lon=-87.63)
        self.assertEqual(context['utc_instant'], '1990-07-15T17:00:00Z')
        self.assertAlmostEqual(context['equation_of_time_seconds'], -355.97356, delta=0.02)
        apparent = datetime.fromisoformat(context['local_apparent_datetime'])
        expected = datetime.fromisoformat('1990-07-15T11:03:32.826438')
        self.assertLessEqual(abs((apparent - expected).total_seconds()), 0.03)
        self.assertEqual(context['timezone']['resolution'], 'explicit_iana')

    def test_solar_clock_inputs_are_not_corrected_twice(self):
        wall = '2024-06-01T12:00:00'
        mean = self.normalize(wall, zone='Asia/Shanghai', lat=31.23, lon=121.47,
                              basis='local_mean_solar')
        apparent = self.normalize(wall, zone='Asia/Shanghai', lat=31.23, lon=121.47,
                                  basis='local_apparent_solar')
        self.assertEqual(mean['local_mean_datetime'], '2024-06-01T12:00:00.000000')
        apparent_wall = datetime.fromisoformat(apparent['local_apparent_datetime'])
        expected_wall = datetime.fromisoformat(wall)
        self.assertLessEqual(abs((apparent_wall - expected_wall).total_seconds()), 0.1)
        self.assertEqual(mean['timezone']['utc_offset_hours'], 8.0)
        self.assertEqual(apparent['timezone']['utc_offset_hours'], 8.0)

    def test_explicit_offset_is_fixed_and_equivalent_at_this_instant(self):
        iana = self.normalize('1990-07-15T12:00:00', zone='America/Chicago',
                              lat=41.88, lon=-87.63)
        fixed = self.normalize('1990-07-15T12:00:00', offset=-5,
                               lat=41.88, lon=-87.63)
        self.assertEqual(fixed['utc_instant'], iana['utc_instant'])
        self.assertIsNone(fixed['timezone']['name'])
        self.assertEqual(fixed['timezone']['resolution'], 'explicit_offset')

    def test_dst_gap_and_fold_are_not_guessed(self):
        with self.assertRaises(InputError) as gap:
            self.normalize('2024-03-10T02:30:00', zone='America/New_York')
        self.assertEqual(gap.exception.code, 'nonexistent_local_time')
        with self.assertRaises(InputError) as ambiguous:
            self.normalize('2024-11-03T01:30:00', zone='America/New_York')
        self.assertEqual(ambiguous.exception.code, 'ambiguous_local_time')
        first = self.normalize('2024-11-03T01:30:00', zone='America/New_York', fold=0)
        second = self.normalize('2024-11-03T01:30:00', zone='America/New_York', fold=1)
        self.assertEqual(first['utc_instant'], '2024-11-03T05:30:00Z')
        self.assertEqual(second['utc_instant'], '2024-11-03T06:30:00Z')

    def test_unknown_local_day_preserves_dst_23_and_25_hour_spans(self):
        spring = self.normalize(None, date='2024-03-10', zone='America/New_York',
                                precision='unknown')
        fall = self.normalize(None, date='2024-11-03', zone='America/New_York',
                              precision='unknown')
        self.assertAlmostEqual(self.elapsed_hours(spring), 23.0, places=8)
        self.assertAlmostEqual(self.elapsed_hours(fall), 25.0, places=8)
        self.assertEqual(len(spring['candidate_intervals']), 2)
        self.assertEqual(len(fall['candidate_intervals']), 2)
        self.assertIsNone(spring['utc_instant'])
        self.assertTrue(all('start_utc' in row and 'end_utc' in row
                            for row in fall['candidate_intervals']))

    def test_range_skips_gap_and_includes_closed_end(self):
        context = self.normalize('2024-03-10T01:30:00', end='2024-03-10T03:30:00',
                                 zone='America/New_York', precision='range')
        self.assertAlmostEqual(self.elapsed_hours(context), 1 + 1 / 3_600_000_000,
                               places=8)
        self.assertEqual(len(context['candidate_intervals']), 2)
        self.assertTrue(all(row['end_inclusive'] for row in context['candidate_intervals']))

    def test_branch_interval_keeps_left_closed_right_open_clock_range(self):
        context = self.normalize(None, date='2024-01-15', zone='Asia/Shanghai',
                                 precision='branch', branch='子', lat=31.23, lon=121.47)
        rows = context['candidate_intervals']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['local_start'], '2024-01-15T23:00:00.000000')
        self.assertEqual(rows[0]['local_end'], '2024-01-16T01:00:00.000000')
        self.assertFalse(rows[0]['end_inclusive'])

    def test_range_uses_iana_across_offset_change_without_overriding_it(self):
        context = self.normalize(
            '2024-03-10T01:30:00', end='2024-03-10T03:30:00',
            zone='America/New_York', offset=-5, precision='range',
        )
        self.assertAlmostEqual(self.elapsed_hours(context),
                               1 + 1 / 3_600_000_000, places=8)
        self.assertEqual({row['utc_offset_hours'] for row in context['candidate_intervals']},
                         {-5.0, -4.0})
        self.assertIsNone(context['timezone']['utc_offset_hours'])
        with self.assertRaises(InputError) as mismatch:
            self.normalize('2024-03-10T03:30:00', end='2024-03-10T04:00:00',
                           zone='America/New_York', offset=-5, precision='range')
        self.assertEqual(mismatch.exception.code, 'offset_zone_conflict')

    def test_offset_only_does_not_reintroduce_dst(self):
        context = self.normalize(None, date='2024-03-10', offset=-5,
                                 precision='unknown', lat=40.7, lon=-74.0)
        self.assertEqual(self.elapsed_hours(context), 24.0)
        self.assertEqual({row['utc_offset_hours'] for row in context['candidate_intervals']}, {-5.0})

    def test_invalid_and_ambiguous_inputs_have_structured_codes(self):
        with self.assertRaises(InputError) as missing_calendar:
            self.normalize('1472-10-31T22:00:00', zone='Asia/Shanghai',
                           date='1472-10-31', calendar=None)
        self.assertEqual(missing_calendar.exception.code, 'invalid_calendar')
        with self.assertRaises(InputError) as bad_coords:
            normalize_birth_time({'birth_date': '2000-01-01', 'date_calendar': 'gregorian',
                                  'location': {'latitude': float('nan'), 'longitude': 0}},
                                 {'precision': 'minute', 'start': '2000-01-01T12:00:00',
                                  'timezone_name': 'UTC', 'clock_basis': 'civil'})
        self.assertEqual(bad_coords.exception.code, 'invalid_coordinates')
        with self.assertRaises(InputError) as unconfirmed_old_date:
            normalize_birth_time({'birth_date': '1472-10-31',
                                  'location': {'latitude': 30, 'longitude': 120}},
                                 {'precision': 'minute', 'start': '1472-10-31T12:00:00',
                                  'timezone_name': 'Asia/Shanghai', 'clock_basis': 'civil'})
        self.assertEqual(unconfirmed_old_date.exception.code,
                         'calendar_confirmation_required')

    def test_explicit_julian_date_is_converted_through_julian_day(self):
        """Calendar identity: 1582-10-04 Julian is 1582-10-14 proleptic Gregorian."""
        context = self.normalize('1582-10-04T12:00:00', zone='UTC',
                                 date='1582-10-04', lat=0, lon=0, calendar='julian')
        self.assertEqual(context['utc_instant'], '1582-10-14T12:00:00Z')
        self.assertEqual(context['input']['subject']['birth_date'], '1582-10-04')
        self.assertEqual(context['calendar'], 'julian')

    def test_zone_database_historical_dst_and_fractional_offset(self):
        """IANA TZDB rules: 1988 China summer time; Sydney summer; Kathmandu UTC+05:45."""
        beijing = self.normalize('1988-07-15T12:00:00', zone='Asia/Shanghai',
                                 date='1988-07-15', lat=39.9, lon=116.4)
        sydney = self.normalize('2024-01-15T12:00:00', zone='Australia/Sydney',
                                date='2024-01-15', lat=-33.87, lon=151.21)
        kathmandu = self.normalize('2024-01-15T12:00:00', zone='Asia/Kathmandu',
                                   date='2024-01-15', lat=27.72, lon=85.32)
        self.assertEqual(beijing['timezone']['utc_offset_hours'], 9.0)
        self.assertEqual(sydney['timezone']['utc_offset_hours'], 11.0)
        self.assertEqual(kathmandu['timezone']['utc_offset_hours'], 5.75)

    def test_hko_lunar_new_year_boundary_precision(self):
        """HKO calendar: 2024-02-04 16:27; HKO term table: 2026-02-04 04:02, UTC+08."""
        from lunar_python import Solar

        anchors = ((2024, 2, 4, 16, 27), (2026, 2, 4, 4, 2))
        for year, month, day, hour, minute in anchors:
            with self.subTest(year=year):
                term = Solar.fromYmdHms(year, 2, 4, 12, 0, 0).getLunar().getJieQiTable()['立春']
                actual = datetime.fromisoformat(term.toYmdHms())
                expected = datetime(year, month, day, hour, minute)
                self.assertLessEqual(abs((actual - expected).total_seconds()), 60)


    def test_leap_month_input_converts_with_lunar_python_and_preserves_source(self):
        """HKO 2023 calendar table: https://www.hko.gov.hk/tc/gts/time/calendar/text/files/T2023c.txt."""
        lunar_date = {
            'year': 2023, 'month': 2, 'day': 1, 'is_leap_month': True,
        }
        subject = {
            'birth_date': None, 'date_calendar': 'gregorian',
            'lunar_date': lunar_date,
            'location': {'latitude': 31.23, 'longitude': 121.47},
        }
        time_input = {
            'precision': 'minute', 'start': '2023-03-22T12:00:00',
            'end': None, 'branch_label': None,
            'timezone_name': 'Asia/Shanghai', 'utc_offset_hours': None,
            'fold': None, 'clock_basis': 'civil',
        }
        context = normalize_birth_time(subject, time_input, as_of='2026-01-15')
        conversion = context['lunar_date_conversion']
        self.assertEqual(conversion['input'], lunar_date)
        self.assertEqual(conversion['solar_date'], '2023-03-22')
        self.assertEqual(conversion['solar_calendar'], 'gregorian')
        self.assertEqual(conversion['library'], 'lunar-python')
        self.assertEqual(conversion['library_version'], '1.4.8')
        self.assertIn('Lunar.fromYmd', conversion['rule'])
        self.assertEqual(context['input']['subject']['lunar_date'], lunar_date)

        matching = dict(subject, birth_date='2023-03-22')
        normalize_birth_time(matching, time_input, as_of='2026-01-15')
        with self.assertRaises(InputError) as mismatch:
            normalize_birth_time(dict(subject, birth_date='2023-03-23'),
                                 time_input, as_of='2026-01-15')
        self.assertEqual(mismatch.exception.code, 'date_conflict')

    def test_nonexistent_leap_month_is_a_structured_input_error(self):
        """Lunar.fromYmd must reject a leap month absent from the requested year."""
        subject = {
            'birth_date': None, 'date_calendar': 'gregorian',
            'lunar_date': {
                'year': 2024, 'month': 2, 'day': 1, 'is_leap_month': True,
            },
            'location': {'latitude': 31.23, 'longitude': 121.47},
        }
        time_input = {
            'precision': 'minute', 'start': '2024-03-10T12:00:00',
            'end': None, 'branch_label': None,
            'timezone_name': 'Asia/Shanghai', 'utc_offset_hours': None,
            'fold': None, 'clock_basis': 'civil',
        }
        with self.assertRaises(InputError) as invalid:
            normalize_birth_time(subject, time_input, as_of='2026-01-15')
        self.assertEqual(invalid.exception.code, 'invalid_lunar_date')

if __name__ == '__main__':
    unittest.main()
