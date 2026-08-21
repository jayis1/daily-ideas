import contextlib
import io
import unittest
from unittest import mock

from daily_ideas import cli


class CliTests(unittest.TestCase):
    def invoke(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = cli.main(args)
        return code, output.getvalue()

    def test_list_filter(self):
        code, output = self.invoke("list", "--category", "puzzle")
        self.assertEqual(0, code)
        self.assertIn("puzzle", output)

    def test_info(self):
        code, output = self.invoke("info", "ascii-dungeon-generator")
        self.assertEqual(0, code)
        self.assertIn("dungeon_generator.py", output)

    def test_unknown_app(self):
        code, output = self.invoke("info", "missing-app")
        self.assertEqual(2, code)
        self.assertIn("unknown app", output)

    @mock.patch("daily_ideas.cli.run_app", return_value=17)
    def test_run_forwards_arguments(self, runner):
        code, _ = self.invoke("run", "ascii-dungeon-generator", "--", "--help")
        self.assertEqual(17, code)
        self.assertEqual(["--help"], runner.call_args.args[2])
