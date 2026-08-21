import tempfile
import unittest
from pathlib import Path
from unittest import mock

from daily_ideas.catalog import App
from daily_ideas.runner import run_app


class RunnerTests(unittest.TestCase):
    def test_runner_uses_app_directory_and_no_shell(self):
        app = App("demo", "Demo", "Demo", "2026-01-01", "2026-01-01-demo", "demo.py", "utility", "cli")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / app.path
            directory.mkdir()
            (directory / app.entrypoint).write_text("print('ok')", encoding="utf-8")
            with mock.patch.dict("os.environ", {"DAILY_IDEAS_DATA_HOME": str(root / "data")}):
                with mock.patch("daily_ideas.runner.subprocess.call", return_value=0) as call:
                    self.assertEqual(0, run_app(app, root, ("--help",)))
                self.assertEqual(str(directory), call.call_args.kwargs["cwd"])
                self.assertNotIn("shell", call.call_args.kwargs)
