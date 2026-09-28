import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import Dict, List, cast

from retry_budget_planner import Attempt, main, plan_retries, render_text, serializable


class RetryBudgetPlannerTests(unittest.TestCase):
    def test_exponential_schedule_with_cap(self):
        plan = plan_retries(30, 2, 1, multiplier=2, max_delay=8)
        self.assertEqual(
            plan["attempts"],
            [
                Attempt(1, 0.0, 2.0, 0.0),
                Attempt(2, 3.0, 5.0, 1),
                Attempt(3, 7.0, 9.0, 2),
                Attempt(4, 13.0, 15.0, 4),
                Attempt(5, 23.0, 25.0, 8),
            ],
        )
        self.assertEqual(plan["unused"], 5.0)

    def test_attempt_ending_exactly_at_deadline_fits(self):
        plan = plan_retries(5, 2, 1)
        self.assertEqual(plan["attempt_count"], 2)
        self.assertEqual(plan["elapsed"], 5.0)
        self.assertEqual(plan["unused"], 0.0)

    def test_partial_attempt_is_not_scheduled(self):
        plan = plan_retries(1.5, 2, 1)
        self.assertEqual(plan["attempts"], [])
        self.assertEqual(plan["unused"], 1.5)

    def test_max_attempts_stops_early(self):
        plan = plan_retries(100, 1, 1, max_attempts=3)
        self.assertEqual(plan["attempt_count"], 3)
        self.assertEqual(plan["elapsed"], 6.0)
        self.assertEqual(plan["unused"], 94.0)

    def test_fractional_values_are_preserved(self):
        plan = plan_retries(2.5, 0.5, 0.25, multiplier=1.5)
        attempts = plan["attempts"]
        self.assertEqual(len(attempts), 3)
        self.assertAlmostEqual(attempts[2].start, 1.625)
        self.assertAlmostEqual(plan["unused"], 0.375)

    def test_rejects_invalid_numbers_and_attempt_limit(self):
        bad_cases = [
            {"deadline": 0},
            {"attempt_timeout": -1},
            {"initial_delay": float("inf")},
            {"multiplier": float("nan")},
            {"max_delay": 0},
            {"max_attempts": 0},
        ]
        defaults = dict(deadline=10, attempt_timeout=1, initial_delay=1)
        for changes in bad_cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                plan_retries(**dict(defaults, **changes))

    def test_text_render_includes_schedule_and_unused_budget(self):
        output = render_text(plan_retries(5, 2, 1))
        self.assertIn("Retry budget: 2 attempts fit in 5s", output)
        self.assertIn("attempt 2: wait 1s; run 3s-5s", output)
        self.assertIn("Unused budget: 0s", output)

    def test_serializable_converts_attempts_and_whole_floats(self):
        payload = serializable(plan_retries(5, 2, 1))
        self.assertEqual(payload["deadline"], 5)
        attempts = cast(List[Dict[str, object]], payload["attempts"])
        self.assertEqual(attempts[1]["start"], 3)

    def test_json_cli(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main([
                "--deadline", "5", "--attempt-timeout", "2",
                "--initial-delay", "1", "--json",
            ])
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["attempt_count"], 2)
        self.assertEqual(payload["attempts"][1]["wait_before"], 1)

    def test_cli_reports_invalid_values(self):
        error = io.StringIO()
        with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
            main(["--deadline", "0", "--attempt-timeout", "2", "--initial-delay", "1"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("deadline must be a positive finite number", error.getvalue())


if __name__ == "__main__":
    unittest.main()
