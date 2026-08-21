"""Safe subprocess execution for independently developed applications."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

from .catalog import App


def data_home() -> Path:
    override = os.environ.get("DAILY_IDEAS_DATA_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return base / "daily-ideas"


def run_app(app: App, root: Path, args: Sequence[str] = (),
            python: Optional[str] = None) -> int:
    app_dir = (root / app.path).resolve()
    entrypoint = (app_dir / app.entrypoint).resolve()
    if app_dir not in entrypoint.parents or not entrypoint.is_file():
        raise FileNotFoundError(f"invalid entrypoint for {app.id}: {entrypoint}")

    env = os.environ.copy()
    app_data = data_home() / app.id
    app_data.mkdir(parents=True, exist_ok=True)
    env["DAILY_IDEAS_APP_ID"] = app.id
    env["DAILY_IDEAS_APP_DATA"] = str(app_data)
    command = [python or sys.executable, str(entrypoint), *args]
    try:
        return subprocess.call(command, cwd=str(app_dir), env=env)
    except KeyboardInterrupt:
        return 130
