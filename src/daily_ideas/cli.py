"""Command-line interface for the Daily Ideas collection."""

from __future__ import annotations

import argparse
import importlib.util
import os
import random
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

from . import __version__
from .catalog import App, load_apps, repository_root, search, validate_apps
from .runner import run_app


def _table(apps: Iterable[App]) -> None:
    rows = list(apps)
    if not rows:
        print("No matching apps.")
        return
    width = min(36, max(len(app.id) for app in rows))
    for app in rows:
        print(f"{app.id:<{width}}  {app.category:<11} {app.interface:<11} {app.description}")


def _find(apps: Sequence[App], app_id: str) -> App:
    exact = [app for app in apps if app.id == app_id]
    if exact:
        return exact[0]
    matches = search(apps, app_id)
    if len(matches) == 1:
        return matches[0]
    if matches:
        choices = ", ".join(app.id for app in matches[:8])
        raise ValueError(f"ambiguous app {app_id!r}; matches: {choices}")
    raise ValueError(f"unknown app: {app_id}")


def _info(app: App) -> None:
    print(app.title)
    print(f"id:           {app.id}")
    print(f"date:         {app.date}")
    print(f"category:     {app.category}")
    print(f"interface:    {app.interface}")
    print(f"entrypoint:   {app.path}/{app.entrypoint}")
    print(f"dependencies: {', '.join(app.dependencies) or 'none'}")
    print(f"tags:         {', '.join(app.tags) or 'none'}")
    print(f"description:  {app.description}")


def _doctor(apps: Sequence[App], root: Optional[Path]) -> int:
    problems = validate_apps(apps, root)
    print(f"Python:      {sys.version.split()[0]} ({sys.executable})")
    print(f"Repository:  {root or 'not found (run commands unavailable)'}")
    print(f"Terminal:    {'yes' if sys.stdin.isatty() and sys.stdout.isatty() else 'no'}")
    print(f"Size:        {shutil.get_terminal_size(fallback=(0, 0)).columns}x{shutil.get_terminal_size(fallback=(0, 0)).lines}")
    optional = sorted({dep for app in apps for dep in app.dependencies})
    for dep in optional:
        print(f"Dependency:  {dep} {'available' if importlib.util.find_spec(dep) else 'MISSING'}")
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    print(f"Catalog:     {len(apps)} apps, valid")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="daily-ideas", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="list catalog apps")
    listing.add_argument("--category")
    listing.add_argument("--interface")
    searching = commands.add_parser("search", help="search titles, descriptions, and tags")
    searching.add_argument("query", nargs="+")
    info = commands.add_parser("info", help="show app metadata")
    info.add_argument("app")
    run = commands.add_parser("run", help="run an app; place its arguments after --")
    run.add_argument("app")
    run.add_argument("app_args", nargs=argparse.REMAINDER)
    choose = commands.add_parser("random", help="choose and optionally run a random app")
    choose.add_argument("--category")
    choose.add_argument("--run", action="store_true")
    choose.add_argument("--seed", type=int)
    commands.add_parser("doctor", help="check the catalog and local capabilities")
    commands.add_parser("browse", help="open the full-screen command center")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    apps = load_apps()
    root = repository_root()
    try:
        if args.command == "list":
            selected = [a for a in apps if not args.category or a.category == args.category]
            selected = [a for a in selected if not args.interface or a.interface == args.interface]
            _table(selected)
        elif args.command == "search":
            _table(search(apps, " ".join(args.query)))
        elif args.command == "info":
            _info(_find(apps, args.app))
        elif args.command == "doctor":
            return _doctor(apps, root)
        elif args.command == "browse":
            if not root:
                raise ValueError("app sources not found; run from a source checkout")
            from .tui import browse
            return browse(apps, root)
        elif args.command in {"run", "random"}:
            if not root:
                raise ValueError("app sources not found; run from a source checkout")
            if args.command == "run":
                app = _find(apps, args.app)
                forwarded = args.app_args[1:] if args.app_args[:1] == ["--"] else args.app_args
                return run_app(app, root, forwarded)
            candidates = [a for a in apps if not args.category or a.category == args.category]
            if not candidates:
                raise ValueError("no apps match the requested category")
            app = random.Random(args.seed).choice(candidates)
            print(app.id, flush=True)
            if args.run:
                return run_app(app, root)
    except (ValueError, FileNotFoundError) as exc:
        print(f"daily-ideas: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
