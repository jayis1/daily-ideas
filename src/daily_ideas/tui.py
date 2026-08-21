"""Curses-based command center for exploring and launching the catalog."""

from __future__ import annotations

import curses
import random
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from .catalog import App, search
from .runner import run_app


@dataclass
class BrowserState:
    """UI-independent catalog filtering and selection state."""

    apps: Sequence[App]
    query: str = ""
    category: Optional[str] = None
    selected: int = 0
    offset: int = 0
    message: str = ""
    categories: List[str] = field(init=False)

    def __post_init__(self) -> None:
        self.categories = sorted({app.category for app in self.apps})

    @property
    def filtered(self) -> List[App]:
        items = search(self.apps, self.query) if self.query else list(self.apps)
        if self.category:
            items = [app for app in items if app.category == self.category]
        return items

    @property
    def current(self) -> Optional[App]:
        items = self.filtered
        return items[self.selected] if items else None

    def clamp(self) -> None:
        self.selected = max(0, min(self.selected, len(self.filtered) - 1))
        self.offset = min(self.offset, self.selected)

    def move(self, amount: int) -> None:
        self.selected += amount
        self.clamp()

    def set_query(self, query: str) -> None:
        self.query = query.strip()
        self.selected = self.offset = 0

    def cycle_category(self, amount: int = 1) -> None:
        choices = [None, *self.categories]
        index = choices.index(self.category)
        self.category = choices[(index + amount) % len(choices)]
        self.selected = self.offset = 0

    def choose_random(self, seed: Optional[int] = None) -> None:
        items = self.filtered
        if items:
            self.selected = random.Random(seed).randrange(len(items))
            self.message = f"Random pick: {items[self.selected].title}"


def _safe_add(window, y: int, x: int, value: str, width: int, attr: int = 0) -> None:
    if y < 0 or x < 0 or width <= 0:
        return
    try:
        window.addnstr(y, x, value, width, attr)
    except curses.error:
        pass


def _set_cursor(visibility: int) -> None:
    """Set cursor visibility when supported by the current terminal."""
    try:
        curses.curs_set(visibility)
    except curses.error:
        pass


def _prompt(stdscr, label: str, initial: str = "") -> str:
    height, width = stdscr.getmaxyx()
    curses.echo()
    _set_cursor(1)
    try:
        stdscr.move(height - 1, 0)
        stdscr.clrtoeol()
        _safe_add(stdscr, height - 1, 0, label, width - 1, curses.A_BOLD)
        _safe_add(stdscr, height - 1, len(label), initial, width - len(label) - 1)
        stdscr.refresh()
        raw = stdscr.getstr(height - 1, min(width - 1, len(label) + len(initial)), 120)
        return initial + raw.decode("utf-8", errors="replace")
    finally:
        curses.noecho()
        _set_cursor(0)


def _draw(stdscr, state: BrowserState) -> None:
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    if height < 12 or width < 60:
        _safe_add(stdscr, 0, 0, "Daily Ideas needs a terminal of at least 60x12.", width - 1)
        _safe_add(stdscr, 2, 0, f"Current size: {width}x{height}. Press q to quit.", width - 1)
        stdscr.refresh()
        return

    title = " DAILY IDEAS COMMAND CENTER "
    _safe_add(stdscr, 0, 0, title.center(width - 1, "═"), width - 1, curses.A_BOLD)
    category = state.category or "all"
    status = f" {len(state.filtered)}/{len(state.apps)} apps  category: {category}  search: {state.query or '—'}"
    _safe_add(stdscr, 1, 0, status, width - 1, curses.A_REVERSE)

    split = max(31, min(width // 2, 48))
    list_height = height - 5
    if state.selected < state.offset:
        state.offset = state.selected
    if state.selected >= state.offset + list_height:
        state.offset = state.selected - list_height + 1

    items = state.filtered
    for row, app in enumerate(items[state.offset:state.offset + list_height], start=3):
        index = state.offset + row - 3
        marker = "▶" if index == state.selected else " "
        label = f"{marker} {app.title}"
        attr = curses.A_REVERSE | curses.A_BOLD if index == state.selected else 0
        _safe_add(stdscr, row, 0, label, split - 2, attr)

    for row in range(2, height - 2):
        _safe_add(stdscr, row, split, "│", 1, curses.A_DIM)

    app = state.current
    if app:
        x, available = split + 2, width - split - 3
        _safe_add(stdscr, 3, x, app.title, available, curses.A_BOLD)
        _safe_add(stdscr, 5, x, f"ID: {app.id}", available)
        _safe_add(stdscr, 6, x, f"Category: {app.category}", available)
        _safe_add(stdscr, 7, x, f"Interface: {app.interface}", available)
        deps = ", ".join(app.dependencies) or "standard library"
        _safe_add(stdscr, 8, x, f"Dependencies: {deps}", available)
        _safe_add(stdscr, 10, x, "Description", available, curses.A_UNDERLINE)
        lines = textwrap.wrap(app.description, max(10, available))
        for row, line in enumerate(lines[:max(0, height - 15)], start=11):
            _safe_add(stdscr, row, x, line, available)
    else:
        _safe_add(stdscr, 4, split + 2, "No apps match the current filters.", width - split - 3)

    if state.message:
        _safe_add(stdscr, height - 2, 0, f" {state.message}", width - 1, curses.A_BOLD)
    controls = " ↑/↓ or j/k move  Enter run  / search  c category  r random  Esc clear  q quit "
    _safe_add(stdscr, height - 1, 0, controls.ljust(width - 1), width - 1, curses.A_REVERSE)
    stdscr.refresh()


def _main(stdscr, apps: Sequence[App], root: Path) -> int:
    state = BrowserState(apps)
    _set_cursor(0)
    stdscr.keypad(True)
    while True:
        _draw(stdscr, state)
        key = stdscr.getch()
        state.message = ""
        if key in (ord("q"), ord("Q")):
            return 0
        if key in (curses.KEY_UP, ord("k")):
            state.move(-1)
        elif key in (curses.KEY_DOWN, ord("j")):
            state.move(1)
        elif key == curses.KEY_PPAGE:
            state.move(-10)
        elif key == curses.KEY_NPAGE:
            state.move(10)
        elif key in (ord("c"), ord("C")):
            state.cycle_category(-1 if key == ord("C") else 1)
        elif key == ord("/"):
            state.set_query(_prompt(stdscr, "Search: "))
        elif key == 27:
            state.set_query("")
            state.category = None
        elif key in (ord("r"), ord("R")):
            state.choose_random()
        elif key in (curses.KEY_ENTER, 10, 13) and state.current:
            app = state.current
            curses.def_prog_mode()
            curses.endwin()
            print(f"\nLaunching {app.title} ({app.id})…\n")
            code = run_app(app, root)
            input(f"\n{app.title} exited with code {code}. Press Enter to return…")
            curses.reset_prog_mode()
            _set_cursor(0)
            stdscr.refresh()


def browse(apps: Sequence[App], root: Path) -> int:
    """Open the command center, returning a process-style status code."""
    if not __import__("sys").stdin.isatty() or not __import__("sys").stdout.isatty():
        raise ValueError("browse requires an interactive terminal (TTY)")
    return curses.wrapper(_main, apps, root)
