import io
import json
import unittest
from contextlib import redirect_stdout

from calendar_gap_finder import (
    Window,
    find_gaps,
    format_clock,
    main,
    merge_windows,
    parse_clock,
    parse_person,
    parse_window,
)


class CalendarGapFinderTests(unittest.TestCase):
    def test_clock_round_trip(self):
        self.assertEqual(parse_clock("09:05"), 545)
        self.assertEqual(format_clock(545), "09:05")
        self.assertEqual(format_clock(1440), "24:00")

    def test_clock_rejects_loose_or_impossible_values(self):
        for value in ("9:00", "24:00", "12:60", "noon"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_clock(value)

    def test_window_requires_forward_time(self):
        self.assertEqual(parse_window("09:00-10:15"), Window(540, 615))
        for value in ("09:00", "10:00-10:00", "11:00-10:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_window(value)

    def test_person_supports_multiple_and_empty_schedules(self):
        name, windows = parse_person("Ada=09:00-10:00, 12:00-12:30")
        self.assertEqual(name, "Ada")
        self.assertEqual(windows, [Window(540, 600), Window(720, 750)])
        self.assertEqual(parse_person("Grace="), ("Grace", []))

    def test_merge_clips_overlaps_and_adjacent_windows(self):
        windows = [Window(480, 570), Window(560, 600), Window(600, 630), Window(1080, 1140)]
        self.assertEqual(merge_windows(windows, 540, 1020), [Window(540, 630)])

    def test_finds_only_gaps_shared_by_everyone(self):
        schedules = {
            "Ada": [Window(540, 600), Window(780, 840)],
            "Grace": [Window(630, 690), Window(810, 900)],
        }
        self.assertEqual(
            find_gaps(schedules, Window(540, 1020), 30),
            [Window(600, 630), Window(690, 780), Window(900, 1020)],
        )

    def test_minimum_filters_short_gaps(self):
        schedules = {"Ada": [Window(600, 630)]}
        self.assertEqual(find_gaps(schedules, Window(540, 660), 45), [Window(540, 600)])

    def test_empty_schedule_and_invalid_minimum(self):
        self.assertEqual(find_gaps({"Ada": []}, Window(540, 600), 30), [Window(540, 600)])
        with self.assertRaises(ValueError):
            find_gaps({}, Window(540, 600), 30)
        with self.assertRaises(ValueError):
            find_gaps({"Ada": []}, Window(540, 600), 0)

    def test_cli_text_output(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main([
                "--person", "Ada=09:00-10:00,13:00-14:00",
                "--person", "Grace=10:30-11:30,13:30-15:00",
                "--minutes", "45",
            ])
        self.assertEqual(status, 0)
        self.assertIn("11:30-13:00 (90 minutes)", output.getvalue())
        self.assertIn("15:00-17:00 (120 minutes)", output.getvalue())

    def test_cli_json_output(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--person", "Ada=10:00-16:00", "--minutes", "30", "--json"])
        self.assertEqual(status, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["people"], ["Ada"])
        self.assertEqual(payload["gaps"][0], {"start": "09:00", "end": "10:00", "minutes": 60})

    def test_cli_no_match(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--person", "Ada=09:00-17:00"])
        self.assertEqual(status, 0)
        self.assertIn("No shared free window", output.getvalue())


if __name__ == "__main__":
    unittest.main()
