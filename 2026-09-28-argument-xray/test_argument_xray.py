import io
import json
import shlex
import unittest
from contextlib import redirect_stdout
from typing import List, cast

from argument_xray import (
    build_report,
    classify,
    inspect_argument,
    main,
    render_text,
    shell_quote,
)


class ArgumentXRayTests(unittest.TestCase):
    def test_shell_quote_leaves_safe_text_unquoted(self):
        self.assertEqual(shell_quote("docs/report-1.txt"), "docs/report-1.txt")

    def test_shell_quote_handles_empty_spaces_and_apostrophes(self):
        self.assertEqual(shell_quote(""), "''")
        self.assertEqual(shell_quote("two words"), "'two words'")
        self.assertEqual(shell_quote("can't"), "'can'\"'\"'t'")

    def test_replay_round_trips_through_posix_parser(self):
        values = ["", "two words", "*.txt", "can't", "caf\N{LATIN SMALL LETTER E WITH ACUTE}"]
        replay = str(build_report(values, "demo tool")["replay"])
        self.assertEqual(shlex.split(replay), ["demo tool", *values])

    def test_classifies_notable_properties_in_stable_order(self):
        self.assertEqual(classify(""), ["empty"])
        self.assertEqual(classify("--dry-run"), ["option-like"])
        self.assertEqual(classify("a b$"), ["whitespace", "shell-sensitive"])
        self.assertEqual(classify("caf\N{LATIN SMALL LETTER E WITH ACUTE}"), ["non-ascii"])
        self.assertEqual(classify("plain"), ["plain"])

    def test_control_character_is_visible(self):
        item = inspect_argument(2, "line\nbreak")
        self.assertEqual(item["characters"], 10)
        self.assertEqual(item["flags"], ["whitespace", "control"])
        self.assertEqual(cast(List[str], item["codepoints"])[4], "U+000A")
        self.assertIn("'line\\nbreak'", render_text({"argument_count": 1, "arguments": [item]}))

    def test_reports_unicode_character_and_byte_counts(self):
        item = inspect_argument(0, "\N{SNOWMAN}")
        self.assertEqual(item["characters"], 1)
        self.assertEqual(item["utf8_bytes"], 3)
        self.assertEqual(item["codepoints"], ["U+2603"])

    def test_text_cli_shows_arguments_and_replay(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--command", "demo", "", "two words", "*.txt"])
        self.assertEqual(status, 0)
        self.assertIn("Argument X-Ray: 3 arguments", output.getvalue())
        self.assertIn("[0] ''", output.getvalue())
        self.assertIn("demo '' 'two words' '*.txt'", output.getvalue())

    def test_codepoint_option_expands_text_output(self):
        output = io.StringIO()
        with redirect_stdout(output):
            main(["--codepoints", "Az"])
        self.assertIn("code points: U+0041 U+007A", output.getvalue())

    def test_json_cli_has_machine_readable_report(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--json", "--command", "demo", "--", "-n"])
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["argument_count"], 1)
        self.assertEqual(payload["arguments"][0]["flags"], ["option-like"])
        self.assertEqual(payload["replay"], "demo -n")

    def test_zero_arguments_is_valid(self):
        report = build_report([])
        self.assertEqual(report, {"argument_count": 0, "arguments": []})


if __name__ == "__main__":
    unittest.main()
