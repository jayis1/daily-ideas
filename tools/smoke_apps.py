#!/usr/bin/env python3
"""Run bounded, non-interactive catalog smoke commands."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    apps = json.loads((ROOT / "src/daily_ideas/apps.json").read_text(encoding="utf-8"))["apps"]
    apps = [app for app in apps if app["smoke_args"]]
    if args.limit:
        apps = apps[:args.limit]
    failures = []
    with tempfile.TemporaryDirectory(prefix="daily-ideas-smoke-") as data:
        env = os.environ.copy()
        env.update({"DAILY_IDEAS_DATA_HOME": data, "TERM": "dumb", "NO_COLOR": "1"})
        for app in apps:
            command = [sys.executable, app["entrypoint"], *app["smoke_args"]]
            try:
                result = subprocess.run(command, cwd=ROOT / app["path"], env=env,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.PIPE, timeout=args.timeout, text=True)
                if result.returncode:
                    failures.append(f"{app['id']}: exit {result.returncode}: {result.stderr[-200:].strip()}")
            except subprocess.TimeoutExpired:
                failures.append(f"{app['id']}: timed out after {args.timeout}s")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"smoke checks passed: {len(apps)} apps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
