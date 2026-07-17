#!/usr/bin/env python3
"""
Terminal Typewriter Simulator
Simulates a vintage typewriter in your terminal with:
- Realistic keystroke-by-keystroke output with variable speed
- Ink density variation (some letters fainter, some darker)
- Carriage return animation at margins
- The classic "ding" at the end of a line
- Manual carriage return with Enter
- Strikethrough/overprint for corrections
- Multiple typewriter models with different feels
- Typewriter bell and margin sounds (terminal bell)
- Paper texture and margins rendered in ASCII
- Word count and character count tracking
- Export typed content to a file
- Speed multiplier for auto-type mode
- Paper jam random events
- Timestamp stamping (Ctrl+T)
- Version: 1.1.0
"""

import sys
import os
import random
import time
import shutil
import curses
import string
import argparse
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from datetime import datetime

__version__ = "1.1.0"


class TypewriterModel(Enum):
    """Different typewriter models with different characteristics."""
    UNDERWOOD = "Underwood No. 5"
    REMINGTON = "Remington Portable"
    OLIVETTI = "Olivetti Lettera 32"
    IBM_SELECTRIC = "IBM Selectric II"
    ROYAL = "Royal Quiet De Luxe"


# Model characteristics: (min_delay, max_delay, ink_variance, ding_at, name)
MODEL_PROPS = {
    TypewriterModel.UNDERWOOD: {
        "min_delay": 0.03, "max_delay": 0.09, "ink_variance": 0.25,
        "ding_at": 65, "description": "The classic workhorse. Heavy keys, satisfying clack.",
        "key_weight": 0.06,
        "jam_chance": 0.002,  # Chance of paper jam per character
    },
    TypewriterModel.REMINGTON: {
        "min_delay": 0.025, "max_delay": 0.07, "ink_variance": 0.20,
        "ding_at": 60, "description": "Light and portable. Quick keystrokes.",
        "key_weight": 0.04,
        "jam_chance": 0.001,
    },
    TypewriterModel.OLIVETTI: {
        "min_delay": 0.02, "max_delay": 0.06, "ink_variance": 0.15,
        "ding_at": 70, "description": "Italian design. Smooth and precise.",
        "key_weight": 0.03,
        "jam_chance": 0.0008,
    },
    TypewriterModel.IBM_SELECTRIC: {
        "min_delay": 0.015, "max_delay": 0.05, "ink_variance": 0.10,
        "ding_at": 75, "description": "The electric revolution. Fast and consistent.",
        "key_weight": 0.02,
        "jam_chance": 0.0003,
    },
    TypewriterModel.ROYAL: {
        "min_delay": 0.035, "max_delay": 0.10, "ink_variance": 0.30,
        "ding_at": 62, "description": "Elegant but temperamental. Beautiful but moody ink.",
        "key_weight": 0.07,
        "jam_chance": 0.004,
    },
}

# ANSI ink density levels (from faint to bold)
INK_SHADES = [
    "\033[2m",      # dim/faint
    "\033[22m",     # normal
    "\033[1m",      # bold
]

INK_COLORS = {
    "black": "",
    "red": "\033[31m",
    "blue": "\033[34m",
    "green": "\033[32m",
}

RESET = "\033[0m"


@dataclass
class TypewriterState:
    """Current state of the typewriter simulation."""
    col: int = 1
    line: int = 1
    ink_density: float = 1.0
    ribbon_wear: float = 0.0  # 0 = fresh ribbon, 1 = worn out
    lines: list = field(default_factory=lambda: [deque()])
    model: TypewriterModel = TypewriterModel.UNDERWOOD
    ink_color: str = "black"
    margin_left: int = 5
    margin_right: int = 5
    page_width: int = 72
    last_was_space: bool = False
    total_chars: int = 0
    caps_lock: bool = False
    paper_offset: int = 0  # vertical scroll offset
    jammed: bool = False    # Paper jam state
    jam_timer: int = 0      # Frames remaining for jam animation
    export_path: str = ""   # File path to export typed content


class TerminalTypewriter:
    """Interactive typewriter simulator using curses."""

    def __init__(self, stdscr, model=TypewriterModel.UNDERWOOD, color="black",
                 auto_mode=False, auto_text=None, speed=1.0, export_path=""):
        self.stdscr = stdscr
        self.state = TypewriterState(model=model, ink_color=color)
        self.state.lines = [deque()]
        self.state.export_path = export_path
        self.auto_mode = auto_mode
        self.auto_text = auto_text or ""
        self.auto_index = 0
        self.speed = max(0.1, min(10.0, speed))  # Clamp speed between 0.1x and 10x
        self.sound_enabled = True
        self.show_header = True
        self.paused = False
        self._setup_curses()

    def _setup_curses(self):
        """Initialize curses settings and color pairs."""
        curses.curs_set(0)  # hide cursor
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        if curses.has_colors():
            curses.start_color()
            # Define color pairs for ink and UI
            curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
            curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_WHITE)
            curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_WHITE)
            curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(7, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLACK)
            # Color pair 9: red on black for jam warnings
            curses.init_pair(9, curses.COLOR_RED, curses.COLOR_BLACK)
            # Color pair 10: green on white for status highlights
            curses.init_pair(10, curses.COLOR_GREEN, curses.COLOR_WHITE)

    def _get_ink_pair(self):
        """Return the curses color pair number for the current ink color."""
        color_map = {
            "black": 4, "red": 1, "blue": 2, "green": 3
        }
        return color_map.get(self.state.ink_color, 4)

    def _bell(self):
        """Ring the terminal bell."""
        if self.sound_enabled:
            try:
                curses.beep()
            except curses.error:
                # Not all terminals support beep; silently ignore
                pass

    def _type_delay(self):
        """Simulate the mechanical delay between key presses, adjusted by speed."""
        props = MODEL_PROPS[self.state.model]
        base_delay = random.uniform(props["min_delay"], props["max_delay"])
        # Add occasional longer delays (finger repositioning)
        if random.random() < 0.03:
            base_delay += random.uniform(0.1, 0.3)
        # Apply speed multiplier (higher speed = shorter delay)
        adjusted = base_delay / self.speed
        time.sleep(max(0.001, adjusted))

    def _get_ink_density(self):
        """Calculate ink density based on ribbon wear and randomness."""
        props = MODEL_PROPS[self.state.model]
        base = 1.0 - self.state.ribbon_wear * 0.6
        variance = props["ink_variance"]
        # Random variation per character
        variation = random.gauss(0, variance * 0.3)
        density = max(0.2, min(1.0, base + variation))
        return density

    def _check_jam(self):
        """Check for a random paper jam event. Returns True if jammed."""
        if self.state.jammed:
            return True
        props = MODEL_PROPS[self.state.model]
        if random.random() < props["jam_chance"]:
            self.state.jammed = True
            self.state.jam_timer = 8  # Flash for 8 frames
            return True
        return False

    def _resolve_jam(self):
        """Resolve a paper jam (user pressed Ctrl+J)."""
        self.state.jammed = False
        self.state.jam_timer = 0
        self._bell()  # Acknowledge with a ding

    def _type_char(self, ch):
        """Type a single character onto the page."""
        # If jammed, skip typing
        if self.state.jammed:
            return False

        line_idx = self.state.line - 1
        if line_idx >= len(self.state.lines):
            for _ in range(line_idx - len(self.state.lines) + 1):
                self.state.lines.append(deque())
            line_idx = len(self.state.lines) - 1

        current_line = self.state.lines[line_idx]

        # Check if we hit the margin - DING!
        props = MODEL_PROPS[self.state.model]
        if self.state.col >= props["ding_at"] and ch != ' ':
            self._bell()
            # Small pause after the ding
            time.sleep(0.15 / self.speed)

        # Ink density affects display
        density = self._get_ink_density()

        if ch == ' ':
            current_line.append((' ', density))
            self.state.last_was_space = True
        else:
            if self.state.caps_lock and ch.isalpha():
                ch = ch.upper()
            current_line.append((ch, density))
            self.state.last_was_space = False

        self.state.col += 1
        self.state.total_chars += 1

        # Increment ribbon wear slightly
        self.state.ribbon_wear = min(1.0, self.state.ribbon_wear + 0.0002)

        # Check for paper jam
        self._check_jam()
        return True

    def _new_line(self):
        """Carriage return + line feed."""
        self.state.line += 1
        self.state.col = 1
        if self.state.line - 1 >= len(self.state.lines):
            self.state.lines.append(deque())

    def _carriage_return(self):
        """Carriage return animation."""
        self.state.col = 1

    def _backspace(self):
        """Simulate backspace/overprint for corrections."""
        line_idx = self.state.line - 1
        if line_idx < len(self.state.lines) and self.state.lines[line_idx]:
            # Replace last char with correction marker (strikethrough)
            last = self.state.lines[line_idx].pop()
            self.state.lines[line_idx].append(('⌫', 0.5))
            self.state.col = max(1, self.state.col - 1)
            return True
        return False

    def _insert_timestamp(self):
        """Insert a timestamp line at the current position."""
        stamp = f"--- {datetime.now().strftime('%Y-%m-%d %H:%M')} ---"
        for ch in stamp:
            self._type_char(ch)

    def _get_word_count(self):
        """Count words across all typed lines."""
        text = self._get_full_text()
        words = text.split()
        return len(words)

    def _get_full_text(self):
        """Reconstruct the full text from all typed lines."""
        lines = []
        for line in self.state.lines:
            line_text = "".join(ch for ch, _ in line)
            lines.append(line_text)
        return "\n".join(lines)

    def _export_to_file(self):
        """Export typed content to the configured export file."""
        path = self.state.export_path
        if not path:
            return False
        try:
            text = self._get_full_text()
            with open(path, 'w') as f:
                f.write(text)
            return True
        except (IOError, OSError):
            return False

    def _render_page(self):
        """Render the typewriter page on screen."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        props = MODEL_PROPS[self.state.model]

        # Header
        header_lines = []
        if self.show_header:
            model_name = props["description"]
            header_lines.append(f" ╔{'═' * (w - 4)}╗")
            title = f"  ⌨  {self.state.model.value}  ⌨  "
            desc = f"  {model_name}  "
            header_lines.append(f" ║{title:^{w-4}}║")
            header_lines.append(f" ║{desc:^{w-4}}║")

            # Status bar with word count and ribbon info
            word_count = self._get_word_count()
            status_parts = [
                f"Ln {self.state.line}",
                f"Col {self.state.col}",
                f"Words {word_count}",
                f"Ribbon {int((1 - self.state.ribbon_wear) * 100)}%",
                f"CAPS {'ON' if self.state.caps_lock else 'off'}",
                f"Speed {self.speed:.1f}x",
            ]
            if self.state.export_path:
                status_parts.append(f"Export: {os.path.basename(self.state.export_path)}")
            status = " │ ".join(status_parts)
            header_lines.append(f" ║{status:^{w-4}}║")

            # Controls
            ctrl = "Enter=↵  BS=⌫  ^U=newline  ^R=CR  ^D=ding  ^N=ribbon  ^T=stamp  ^J=unjam  ^P=pause  ^C=CAPS  Q=quit"
            header_lines.append(f" ║{ctrl:^{w-4}}║")

            # Jam warning
            if self.state.jammed:
                jam_msg = "⚠ PAPER JAM! Press Ctrl+J to clear ⚠"
                header_lines.append(f" ║{jam_msg:^{w-4}}║")

            header_lines.append(f" ╚{'═' * (w - 4)}╝")

        # Calculate available lines for paper
        header_height = len(header_lines)
        paper_top = header_height + 1
        available_height = h - paper_top - 3

        # Render header
        for i, line in enumerate(header_lines):
            if i < h:
                try:
                    if self.state.jammed and "PAPER JAM" in line:
                        # Flash jam warning in red
                        self.stdscr.addstr(i, 0, line[:w], curses.color_pair(9) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(i, 0, line[:w])
                except curses.error:
                    pass

        # Paper border
        paper_left = 2
        paper_right = min(w - 3, self.state.page_width + self.state.margin_left + self.state.margin_right + 4)
        paper_width = paper_right - paper_left - 2

        # Draw paper top
        try:
            self.stdscr.addstr(paper_top, paper_left, f"┌{'─' * paper_width}┐")
        except curses.error:
            pass

        # Render paper lines
        visible_lines = available_height - 2
        visible_lines = max(1, visible_lines)
        scroll_offset = max(0, self.state.line - visible_lines)
        self.state.paper_offset = scroll_offset

        for i in range(visible_lines):
            line_idx = scroll_offset + i
            screen_row = paper_top + 1 + i

            # Left margin
            margin_str = " " * self.state.margin_left

            if line_idx < len(self.state.lines):
                line_content = ""
                for ch, density in self.state.lines[line_idx]:
                    line_content += ch

                # Pad line to fill paper width
                display_line = margin_str + line_content
                display_line = display_line[:paper_width]
            else:
                display_line = " " * paper_width

            try:
                # Paper background
                ink_pair = self._get_ink_pair()
                if line_idx == self.state.line - 1:
                    # Highlight current line
                    self.stdscr.addstr(screen_row, paper_left, f"│", curses.color_pair(5))
                    # Render characters with ink density
                    x = paper_left + 1
                    cursor_drawn = False
                    if line_idx < len(self.state.lines):
                        char_pos = 0
                        for ch, density in self.state.lines[line_idx]:
                            if x < paper_left + paper_width and x < w - 1:
                                if char_pos == len(self.state.lines[line_idx]) - 1:
                                    # Last char on current line - show cursor after it
                                    try:
                                        self.stdscr.addstr(screen_row, x, ch, curses.color_pair(ink_pair) | curses.A_BOLD)
                                    except curses.error:
                                        pass
                                    cursor_drawn = True
                                else:
                                    if density > 0.8:
                                        attr = curses.color_pair(ink_pair) | curses.A_BOLD
                                    elif density > 0.5:
                                        attr = curses.color_pair(ink_pair)
                                    else:
                                        attr = curses.color_pair(ink_pair) | curses.A_DIM
                                    try:
                                        self.stdscr.addstr(screen_row, x, ch, attr)
                                    except curses.error:
                                        pass
                            x += 1
                            char_pos += 1

                        # Draw cursor
                        if not cursor_drawn:
                            cursor_x = paper_left + 1 + self.state.margin_left + len(self.state.lines[line_idx])
                            if cursor_x < paper_left + paper_width and cursor_x < w - 1:
                                try:
                                    self.stdscr.addstr(screen_row, cursor_x, "█", curses.color_pair(5))
                                except curses.error:
                                    pass

                    # Fill rest of line with paper background
                    remaining_start = x
                    for px in range(remaining_start, paper_left + paper_width + 1):
                        if px < w - 1:
                            try:
                                self.stdscr.addstr(screen_row, px, " ", curses.color_pair(5))
                            except curses.error:
                                pass

                    self.stdscr.addstr(screen_row, paper_left + paper_width, f"│", curses.color_pair(5))
                else:
                    # Non-current lines
                    self.stdscr.addstr(screen_row, paper_left, f"│", curses.color_pair(4))
                    # Render with ink density
                    if line_idx < len(self.state.lines):
                        x = paper_left + 1
                        for ch, density in self.state.lines[line_idx]:
                            if x < paper_left + paper_width and x < w - 1:
                                if density > 0.8:
                                    attr = curses.color_pair(ink_pair) | curses.A_BOLD
                                elif density > 0.5:
                                    attr = curses.color_pair(ink_pair)
                                else:
                                    attr = curses.color_pair(ink_pair) | curses.A_DIM
                                try:
                                    self.stdscr.addstr(screen_row, x, ch, attr)
                                except curses.error:
                                    pass
                            x += 1

                    self.stdscr.addstr(screen_row, paper_left + paper_width, f"│", curses.color_pair(4))
            except curses.error:
                pass

        # Draw paper bottom
        bottom_row = paper_top + 1 + visible_lines
        try:
            self.stdscr.addstr(bottom_row, paper_left, f"└{'─' * paper_width}┘")
        except curses.error:
            pass

        # Draw typewriter roller decoration
        roller_row = bottom_row + 1
        if roller_row < h:
            roller = "▓" * (paper_width + 2)
            try:
                self.stdscr.addstr(roller_row, paper_left, roller, curses.color_pair(5))
            except curses.error:
                pass

        # Draw footer with jam status
        footer_row = roller_row + 1
        if footer_row < h and self.state.jammed:
            try:
                flash = self.state.jam_timer % 2 == 0
                msg = "!! PAPER JAM !!  Press Ctrl+J to clear"
                if flash:
                    self.stdscr.addstr(footer_row, 2, msg, curses.color_pair(9) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(footer_row, 2, msg, curses.color_pair(9))
                self.state.jam_timer -= 1
                if self.state.jam_timer <= 0:
                    # Reset timer but keep jammed until user clears
                    self.state.jam_timer = 8
            except curses.error:
                pass

        self.stdscr.refresh()

    def _auto_type(self):
        """Auto-type from provided text."""
        if self.auto_index < len(self.auto_text):
            ch = self.auto_text[self.auto_index]
            self.auto_index += 1

            if ch == '\n':
                self._carriage_return()
                self._new_line()
            elif ch == '\t':
                for _ in range(4):
                    self._type_char(' ')
            else:
                self._type_char(ch)
            self._type_delay()

    def run(self):
        """Main typewriter loop."""
        while True:
            self._render_page()

            if self.auto_mode:
                if not self.paused and self.auto_index < len(self.auto_text):
                    self._auto_type()
                    continue

            # Check for input
            try:
                key = self.stdscr.getch()
            except curses.error:
                key = -1

            if key == -1:
                time.sleep(0.01)
                continue

            # Quit
            if key == ord('q') or key == ord('Q'):
                # Auto-export on quit if export path is set
                if self.state.export_path:
                    self._export_to_file()
                break

            # Enter = carriage return + line feed
            if key == curses.KEY_ENTER or key == 10 or key == 13:
                self._carriage_return()
                self._new_line()
                # Typewriter return sound
                time.sleep(0.05 / max(0.1, self.speed))
                continue

            # Backspace
            if key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                self._backspace()
                continue

            # Ctrl+U = new line
            if key == 21:
                self._carriage_return()
                self._new_line()
                continue

            # Ctrl+R = carriage return only (no line feed)
            if key == 18:
                self._carriage_return()
                continue

            # Ctrl+D = ding bell manually
            if key == 4:
                self._bell()
                continue

            # Ctrl+N = new ribbon
            if key == 14:
                self.state.ribbon_wear = 0.0
                continue

            # Ctrl+P = pause/resume auto-type
            if key == 16:
                self.paused = not self.paused
                continue

            # Ctrl+C = caps lock toggle (overrides default interrupt)
            if key == 3:
                self.state.caps_lock = not self.state.caps_lock
                continue

            # Ctrl+J = clear paper jam
            if key == 10:
                if self.state.jammed:
                    self._resolve_jam()
                continue

            # Ctrl+T = insert timestamp
            if key == 20:
                self._insert_timestamp()
                continue

            # Ctrl+E = export now
            if key == 5:
                if self.state.export_path:
                    success = self._export_to_file()
                    # Brief flash to indicate success/failure would be nice
                    # but we just continue for now
                continue

            # Escape sequences for arrow keys etc.
            if key == 27:
                # Skip escape sequences
                time.sleep(0.05)
                try:
                    _ = self.stdscr.getch()
                except curses.error:
                    pass
                continue

            # Regular character
            if 32 <= key <= 126:
                ch = chr(key)
                self._type_char(ch)
                self._type_delay()


def print_help():
    """Print usage help."""
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           ⌨  TERMINAL TYPEWRITER SIMULATOR  ⌨           ║
║                    v{__version__}                             ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Usage: python typewriter.py [options]                   ║
║                                                          ║
║  Options:                                                ║
║    -m, --model MODEL   Typewriter model                  ║
║                         underwood (default)              ║
║                         remington                        ║
║                         olivetti                         ║
║                         ibm                              ║
║                         royal                            ║
║                                                          ║
║    -c, --color COLOR   Ink color: black,red,blue,green   ║
║    -t, --text TEXT     Auto-type text (use quotes)       ║
║    -f, --file FILE     Auto-type from file               ║
║    -s, --speed FLOAT   Auto-type speed multiplier (0.1-10)║
║    -e, --export FILE   Export typed text to file on exit ║
║    -q, --quiet         Disable bell sounds               ║
║    -v, --version       Show version                      ║
║    -h, --help          Show this help                    ║
║                                                          ║
║  Interactive Controls (while running):                    ║
║    Enter           Carriage return + line feed           ║
║    Backspace       Overstrike last character              ║
║    Ctrl+U          New line                              ║
║    Ctrl+R          Carriage return (no line feed)        ║
║    Ctrl+D          Ring bell manually                     ║
║    Ctrl+N          Install new ribbon                    ║
║    Ctrl+P          Pause/resume auto-type                ║
║    Ctrl+C          Toggle CAPS LOCK                      ║
║    Ctrl+T          Insert timestamp                      ║
║    Ctrl+J          Clear paper jam                       ║
║    Ctrl+E          Export to file (if --export set)      ║
║    Q               Quit                                  ║
║                                                          ║
║  The typewriter bell rings when you approach the right    ║
║  margin, just like a real typewriter! Ink density        ║
║  varies with ribbon wear — install a new ribbon with     ║
║  Ctrl+N when the text gets too faint. Paper jams can    ║
║  occur randomly — press Ctrl+J to clear them.            ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Terminal Typewriter Simulator — v" + __version__,
        add_help=False
    )
    parser.add_argument('-m', '--model', default='underwood',
                       choices=['underwood', 'remington', 'olivetti', 'ibm', 'royal'],
                       help='Typewriter model (default: underwood)')
    parser.add_argument('-c', '--color', default='black',
                       choices=['black', 'red', 'blue', 'green'],
                       help='Ink color (default: black)')
    parser.add_argument('-t', '--text', default=None,
                       help='Text to auto-type')
    parser.add_argument('-f', '--file', default=None,
                       help='File to auto-type from')
    parser.add_argument('-s', '--speed', type=float, default=1.0,
                       help='Auto-type speed multiplier 0.1-10.0 (default: 1.0)')
    parser.add_argument('-e', '--export', default=None,
                       help='Export typed text to file on exit')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Disable bell sounds')
    parser.add_argument('--demo', action='store_true',
                       help='Run non-interactive demo mode')
    parser.add_argument('-v', '--version', action='store_true',
                       help='Show version and exit')
    parser.add_argument('-h', '--help', action='store_true',
                       help='Show help and exit')

    args = parser.parse_args()

    if args.help:
        print_help()
        sys.exit(0)

    if args.version:
        print(f"Terminal Typewriter Simulator v{__version__}")
        sys.exit(0)

    # Demo mode — non-interactive
    if args.demo:
        demo_text = """The quick brown fox jumps over the lazy dog.
Every letter of the alphabet, typed with care.
A typewriter is a mechanical marvel!
DING! The margin bell rings."""
        demo_typewriter(demo_text)
        sys.exit(0)

    model_map = {
        'underwood': TypewriterModel.UNDERWOOD,
        'remington': TypewriterModel.REMINGTON,
        'olivetti': TypewriterModel.OLIVETTI,
        'ibm': TypewriterModel.IBM_SELECTRIC,
        'royal': TypewriterModel.ROYAL,
    }

    model = model_map[args.model]

    auto_text = args.text
    if args.file:
        try:
            with open(args.file, 'r') as f:
                auto_text = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.")
            sys.exit(1)
        except PermissionError:
            print(f"Error: Permission denied reading '{args.file}'.")
            sys.exit(1)

    export_path = args.export or ""

    def run_typewriter(stdscr):
        tw = TerminalTypewriter(
            stdscr,
            model=model,
            color=args.color,
            auto_mode=auto_text is not None,
            auto_text=auto_text,
            speed=args.speed,
            export_path=export_path
        )
        if args.quiet:
            tw.sound_enabled = False
        tw.run()

    try:
        curses.wrapper(run_typewriter)
    except KeyboardInterrupt:
        pass


# ─── Demo mode: non-interactive ASCII output for README examples ───

def demo_typewriter(text, model_name="underwood"):
    """Non-interactive demo that prints typewriter-styled text to stdout."""
    model_map = {
        'underwood': TypewriterModel.UNDERWOOD,
        'remington': TypewriterModel.REMINGTON,
        'olivetti': TypewriterModel.OLIVETTI,
        'ibm': TypewriterModel.IBM_SELECTRIC,
        'royal': TypewriterModel.ROYAL,
    }
    model = model_map.get(model_name, TypewriterModel.UNDERWOOD)
    props = MODEL_PROPS[model]

    print()
    print(f"  ╔{'═' * 68}╗")
    print(f"  ║  ⌨  {model.value:^62}  ║")
    print(f"  ╚{'═' * 68}╝")
    print()
    print(f"  ┌{'─' * 68}┐")

    lines = text.split('\n')
    for line in lines:
        output = "  │ "
        for ch in line:
            density = max(0.2, min(1.0, 1.0 + random.gauss(0, props["ink_variance"] * 0.3)))
            if density > 0.5:
                output += ch
            else:
                # Use a similar-looking but "fainter" character for demo
                faint_map = {
                    'a': 'ɑ', 'e': 'ɛ', 'o': 'ο', 'A': 'Α', 'O': 'Ο',
                    'l': 'ǀ', 'I': 'Ι', 'H': 'Η'
                }
                output += faint_map.get(ch, ch)

        # Pad line
        output = output[:72]
        output += " " * max(0, 72 - len(output))
        output += "│"
        print(output)

    print(f"  └{'─' * 68}┘")
    print()
    print(f"  {'▓' * 70}")
    print()


if __name__ == "__main__":
    main()