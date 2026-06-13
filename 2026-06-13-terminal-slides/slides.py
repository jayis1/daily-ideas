#!/usr/bin/env python3
"""
Terminal Slides — A terminal-based presentation tool.
Feed it a Markdown file and it renders beautiful slides in your terminal.

Supports:
  - Slide separators (---)
  - Headers, bold, italic, inline code, code blocks
  - Ordered & unordered lists
  - Blockquotes
  - Theming (dark/light/monochrome)
  - Progress bar and slide counter
  - Keyboard navigation (arrows, space, q to quit)
  - Auto-play mode with configurable interval
  - Export slides to PNG (optional)
"""

import sys
import os
import re
import shutil
import argparse
import textwrap

# ──────────────────────────────────────────────
# ANSI helpers
# ──────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"

# Color palette
COLORS = {
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "bright_black":   "\033[90m",
    "bright_red":     "\033[91m",
    "bright_green":   "\033[92m",
    "bright_yellow":  "\033[93m",
    "bright_blue":    "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan":    "\033[96m",
    "bright_white":   "\033[97m",
}

BG_COLORS = {
    "black":   "\033[40m",
    "red":     "\033[41m",
    "green":   "\033[42m",
    "yellow":  "\033[43m",
    "blue":    "\033[44m",
    "magenta": "\033[45m",
    "cyan":    "\033[46m",
    "white":   "\033[47m",
}

# ──────────────────────────────────────────────
# Themes
# ──────────────────────────────────────────────

THEMES = {
    "dark": {
        "title":       ("bright_cyan",  "bold"),
        "subtitle":    ("cyan",         "bold"),
        "heading2":    ("bright_green", "bold"),
        "heading3":    ("green",        "bold"),
        "body":        ("white",        "normal"),
        "dim":         ("bright_black", "dim"),
        "code_inline": ("bright_yellow","normal"),
        "code_block":  ("bright_green", "normal"),
        "quote":       ("bright_magenta","italic"),
        "quote_bar":   ("magenta",      "normal"),
        "bullet":      ("bright_yellow","bold"),
        "number":      ("bright_yellow","bold"),
        "bold":        ("bright_white", "bold"),
        "italic":      ("bright_cyan",  "italic"),
        "link":        ("bright_blue",  "underline"),
        "progress":    ("cyan",         "normal"),
        "progress_bg": ("bright_black", "normal"),
        "slide_num":   ("bright_black", "dim"),
    },
    "light": {
        "title":       ("blue",         "bold"),
        "subtitle":    ("blue",         "normal"),
        "heading2":    ("green",        "bold"),
        "heading3":    ("green",        "normal"),
        "body":        ("black",        "normal"),
        "dim":         ("bright_black", "dim"),
        "code_inline": ("magenta",      "normal"),
        "code_block":  ("green",        "normal"),
        "quote":       ("magenta",      "italic"),
        "quote_bar":   ("magenta",      "normal"),
        "bullet":      ("red",          "bold"),
        "number":      ("red",          "bold"),
        "bold":        ("black",        "bold"),
        "italic":      ("blue",         "italic"),
        "link":        ("blue",         "underline"),
        "progress":    ("blue",         "normal"),
        "progress_bg": ("bright_black", "normal"),
        "slide_num":   ("bright_black", "dim"),
    },
    "monochrome": {
        "title":       ("white",        "bold"),
        "subtitle":    ("white",        "normal"),
        "heading2":    ("white",        "bold"),
        "heading3":    ("white",        "underline"),
        "body":        ("white",        "normal"),
        "dim":         ("bright_black", "dim"),
        "code_inline": ("white",        "bold"),
        "code_block":  ("white",        "normal"),
        "quote":       ("bright_black", "italic"),
        "quote_bar":   ("bright_black", "normal"),
        "bullet":      ("white",        "bold"),
        "number":      ("white",        "bold"),
        "bold":        ("white",        "bold"),
        "italic":      ("white",        "italic"),
        "link":        ("white",        "underline"),
        "progress":    ("white",        "normal"),
        "progress_bg": ("bright_black", "normal"),
        "slide_num":   ("bright_black", "dim"),
    },
}

# ──────────────────────────────────────────────
# Slide parser
# ──────────────────────────────────────────────

class SlideParser:
    """Parse a Markdown string into a list of slides."""

    HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
    BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
    ITALIC_RE = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)')
    CODE_INLINE_RE = re.compile(r'`(.+?)`')
    QUOTE_RE = re.compile(r'^>\s?(.*)$')
    UNORDERED_RE = re.compile(r'^[\s]*[-*+]\s+(.+)$')
    ORDERED_RE = re.compile(r'^[\s]*(\d+)\.\s+(.+)$')
    HORIZONTAL_RE = re.compile(r'^---+\s*$')
    CODE_FENCE_RE = re.compile(r'^```(\w*)$')

    def __init__(self, text: str):
        self.slides: list[list[dict]] = []
        self._parse(text)

    def _parse(self, text: str):
        raw_slides = re.split(r'\n---\n|\n---\s*$', text)
        for raw in raw_slides:
            slide = self._parse_slide(raw.strip())
            if slide:
                self.slides.append(slide)

    def _parse_slide(self, text: str) -> list[dict]:
        lines = text.split('\n')
        elements = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Code fence
            m = self.CODE_FENCE_RE.match(line)
            if m:
                lang = m.group(1)
                code_lines = []
                i += 1
                while i < len(lines) and not self.CODE_FENCE_RE.match(lines[i]):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # skip closing ```
                elements.append({"type": "code_block", "lang": lang, "text": "\n".join(code_lines)})
                continue

            # Heading
            m = self.HEADING_RE.match(line)
            if m:
                level = len(m.group(1))
                content = m.group(2)
                elements.append({"type": f"heading{min(level, 3)}", "text": self._inline_format(content)})
                i += 1
                continue

            # Blockquote
            m = self.QUOTE_RE.match(line)
            if m:
                quote_lines = [m.group(1)]
                i += 1
                while i < len(lines):
                    m2 = self.QUOTE_RE.match(lines[i])
                    if m2:
                        quote_lines.append(m2.group(1))
                        i += 1
                    else:
                        break
                elements.append({"type": "quote", "text": self._inline_format(" ".join(quote_lines))})
                continue

            # Unordered list
            m = self.UNORDERED_RE.match(line)
            if m:
                items = [m.group(1)]
                i += 1
                while i < len(lines):
                    m2 = self.UNORDERED_RE.match(lines[i])
                    if m2:
                        items.append(m2.group(1))
                        i += 1
                    else:
                        break
                elements.append({"type": "unordered_list", "items": [self._inline_format(it) for it in items]})
                continue

            # Ordered list
            m = self.ORDERED_RE.match(line)
            if m:
                items = [(int(m.group(1)), m.group(2))]
                i += 1
                while i < len(lines):
                    m2 = self.ORDERED_RE.match(lines[i])
                    if m2:
                        items.append((int(m2.group(1)), m2.group(2)))
                        i += 1
                    else:
                        break
                elements.append({"type": "ordered_list", "items": [(n, self._inline_format(t)) for n, t in items]})
                continue

            # Horizontal rule (skip)
            if self.HORIZONTAL_RE.match(line):
                i += 1
                continue

            # Blank line
            if line.strip() == '':
                i += 1
                continue

            # Regular text
            elements.append({"type": "text", "text": self._inline_format(line)})
            i += 1

        return elements

    def _inline_format(self, text: str) -> str:
        """Store inline format markers; we'll render them later with theme colors."""
        # We use sentinel markers that won't appear in normal text
        BOLD_OPEN = "<<BOLD>>"
        BOLD_CLOSE = "<</BOLD>>"
        ITALIC_OPEN = "<<ITALIC>>"
        ITALIC_CLOSE = "<</ITALIC>>"
        CODE_OPEN = "<<CODE>>"
        CODE_CLOSE = "<</CODE>>"
        text = self.BOLD_RE.sub(BOLD_OPEN + r'\1' + BOLD_CLOSE, text)
        text = self.ITALIC_RE.sub(ITALIC_OPEN + r'\1' + ITALIC_CLOSE, text)
        text = self.CODE_INLINE_RE.sub(CODE_OPEN + r'\1' + CODE_CLOSE, text)
        return text


# ──────────────────────────────────────────────
# Renderer
# ──────────────────────────────────────────────

class Renderer:
    def __init__(self, theme_name: str = "dark"):
        self.theme_name = theme_name
        self.theme = THEMES.get(theme_name, THEMES["dark"])
        self.cols, self.rows = shutil.get_terminal_size((80, 24))
        self.cols = max(self.cols, 40)
        self.rows = max(self.rows, 12)

    def _color(self, element: str) -> str:
        color_name, style = self.theme.get(element, ("white", "normal"))
        prefix = COLORS.get(color_name, COLORS["white"])
        if style == "bold":
            prefix += BOLD
        elif style == "dim":
            prefix += DIM
        elif style == "italic":
            prefix += ITALIC
        elif style == "underline":
            prefix += UNDERLINE
        return prefix

    def _render_inline(self, text: str) -> str:
        """Replace inline format markers with ANSI sequences."""
        text = text.replace('<<BOLD>>', self._color("bold"))
        text = text.replace('<</BOLD>>', self._color("body"))
        text = text.replace('<<ITALIC>>', self._color("italic"))
        text = text.replace('<</ITALIC>>', self._color("body"))
        text = text.replace('<<CODE>>', self._color("code_inline"))
        text = text.replace('<</CODE>>', self._color("body"))
        return text

    def _center(self, line: str, width: int = 0) -> str:
        """Center a line in the terminal, accounting for ANSI codes."""
        # Strip ANSI to measure visible width
        visible = re.sub(r'\033\[[0-9;]*m', '', line)
        vis_len = len(visible)
        target_w = width or self.cols
        pad = max(0, (target_w - vis_len) // 2)
        return " " * pad + line

    def render_slide(self, slide: list[dict], slide_num: int, total: int) -> str:
        lines = []
        body_color = self._color("body")
        dim_color = self._color("dim")

        # Top padding
        lines.append("")

        for elem in slide:
            if elem["type"] == "heading1":
                text = self._render_inline(elem["text"])
                lines.append(self._center(f"{self._color('title')}{BOLD}{text}{RESET}"))
                lines.append(self._center(f"{dim_color}{'━' * min(40, self.cols - 4)}{RESET}"))
                lines.append("")

            elif elem["type"] == "heading2":
                text = self._render_inline(elem["text"])
                lines.append(f"  {self._color('heading2')}{BOLD}{text}{RESET}")
                lines.append("")

            elif elem["type"] == "heading3":
                text = self._render_inline(elem["text"])
                lines.append(f"  {self._color('heading3')}{UNDERLINE}{text}{RESET}")
                lines.append("")

            elif elem["type"] == "text":
                text = self._render_inline(elem["text"])
                lines.append(f"  {body_color}{text}{RESET}")

            elif elem["type"] == "code_block":
                lang = elem.get("lang", "")
                code = elem["text"]
                bar = f"  {self._color('code_inline')}┌{'─' * (self.cols - 6)}┐{RESET}"
                lines.append(f"  {dim_color}{lang}{RESET}")
                lines.append(bar)
                for code_line in code.split('\n'):
                    vis_len = len(code_line)
                    max_w = self.cols - 8
                    if vis_len > max_w:
                        code_line = code_line[:max_w-1] + "…"
                        vis_len = len(code_line)
                    pad = max(0, self.cols - 6 - vis_len)
                    lines.append(f"  {self._color('code_block')}│ {code_line}{' ' * pad}│{RESET}")
                bar2 = f"  {self._color('code_inline')}└{'─' * (self.cols - 6)}┘{RESET}"
                lines.append(bar2)
                lines.append("")

            elif elem["type"] == "quote":
                text = self._render_inline(elem["text"])
                bar_char = f"{self._color('quote_bar')}┃{RESET}"
                # Wrap long quotes
                max_w = self.cols - 6
                wrapped = textwrap.wrap(re.sub(r'\033\[[0-9;]*m', '', text), width=max_w)
                for w_line in wrapped:
                    lines.append(f"  {bar_char} {self._color('quote')}{w_line}{RESET}")
                lines.append("")

            elif elem["type"] == "unordered_list":
                bullet = f"{self._color('bullet')}•{RESET}"
                for item in elem["items"]:
                    item_rendered = self._render_inline(item)
                    lines.append(f"    {bullet} {body_color}{item_rendered}{RESET}")
                lines.append("")

            elif elem["type"] == "ordered_list":
                for num, item_text in elem["items"]:
                    item_rendered = self._render_inline(item_text)
                    lines.append(f"    {self._color('number')}{num}.{RESET} {body_color}{item_rendered}{RESET}")
                lines.append("")

        # Add vertical fill
        while len(lines) < self.rows - 3:
            lines.append("")

        # Progress bar
        pct = (slide_num + 1) / total if total > 0 else 0
        bar_w = self.cols - 20
        filled = int(pct * bar_w)
        empty = bar_w - filled
        progress = (
            f"  {self._color('progress')}{'█' * filled}{self._color('progress_bg')}{'░' * empty}{RESET}"
            f"  {self._color('slide_num')}{slide_num + 1}/{total}{RESET}"
        )
        lines.append(progress)

        return "\n".join(lines)


# ──────────────────────────────────────────────
# Terminal input (no curses dependency)
# ──────────────────────────────────────────────

def _get_key() -> str:
    """Read a single keypress from stdin without echo."""
    import tty, termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            seq = sys.stdin.read(2)
            if seq == '[A':
                return 'UP'
            elif seq == '[B':
                return 'DOWN'
            elif seq == '[C':
                return 'RIGHT'
            elif seq == '[D':
                return 'LEFT'
            return 'ESC'
        elif ch == 'q' or ch == '\x03':  # q or Ctrl-C
            return 'QUIT'
        elif ch == ' ':
            return 'NEXT'
        elif ch == '\n' or ch == '\r':
            return 'NEXT'
        elif ch == 'h' or ch == 'b':
            return 'PREV'
        elif ch == 'j':
            return 'NEXT'
        elif ch == 'k':
            return 'PREV'
        elif ch == 'g':
            return 'FIRST'
        elif ch == 'G':
            return 'LAST'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ──────────────────────────────────────────────
# Presentation runner
# ──────────────────────────────────────────────

class Presenter:
    def __init__(self, slides: list[list[dict]], theme: str = "dark", auto: float = 0):
        self.slides = slides
        self.theme = theme
        self.auto = auto
        self.current = 0

    def run(self):
        renderer = Renderer(self.theme)

        # Save cursor & switch to alternate screen
        sys.stdout.write("\033[?1049h")  # alternate screen buffer
        sys.stdout.write("\033[?25l")     # hide cursor
        sys.stdout.flush()

        try:
            if self.auto > 0:
                self._auto_play(renderer)
            else:
                self._interactive(renderer)
        finally:
            sys.stdout.write("\033[?25h")   # show cursor
            sys.stdout.write("\033[?1049l") # back to main screen
            sys.stdout.flush()

    def _draw(self, renderer: Renderer):
        sys.stdout.write("\033[H\033[J")  # clear screen
        content = renderer.render_slide(self.slides[self.current], self.current, len(self.slides))
        sys.stdout.write(content)
        sys.stdout.flush()

    def _interactive(self, renderer: Renderer):
        self._draw(renderer)
        while True:
            key = _get_key()
            if key == 'QUIT':
                break
            elif key in ('NEXT', 'RIGHT', 'DOWN'):
                if self.current < len(self.slides) - 1:
                    self.current += 1
                    self._draw(renderer)
                else:
                    break  # past last slide = end
            elif key in ('PREV', 'LEFT', 'UP'):
                if self.current > 0:
                    self.current -= 1
                    self._draw(renderer)
            elif key == 'FIRST':
                self.current = 0
                self._draw(renderer)
            elif key == 'LAST':
                self.current = len(self.slides) - 1
                self._draw(renderer)

    def _auto_play(self, renderer: Renderer):
        import time
        for i in range(len(self.slides)):
            self.current = i
            self._draw(renderer)
            if i < len(self.slides) - 1:
                time.sleep(self.auto)
        # Pause at the end briefly
        time.sleep(2)


# ──────────────────────────────────────────────
# Demo slides (built-in sample)
# ──────────────────────────────────────────────

DEMO_SLIDES = """\
# Terminal Slides

A presentation tool that runs entirely in your terminal

---

## Why Terminal Slides?

* No GUI required — works over SSH
* Distraction-free presenting
* Markdown-based — use your favorite editor
* Lightweight and fast

---

## Features

1. **Multiple themes** — dark, light, monochrome
2. `Inline code` highlighting
3. Code blocks with language labels
4. Beautiful blockquotes
5. Ordered and unordered lists

---

> The best presentations are the ones where the tool gets out of the way and lets your ideas shine.

---

## Code Blocks

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

print(greet("Terminal Slides"))
```

---

## Keyboard Navigation

* `→` or `Space` — next slide
* `←` or `h` — previous slide
* `g` — first slide
* `G` — last slide
* `q` — quit

---

# Thank You!

Built with ❤️ and ANSI escape codes

Try: `python slides.py demo --theme light`
"""

# ──────────────────────────────────────────────
# Export to plain text
# ──────────────────────────────────────────────

def export_text(slides: list[list[dict]], output: str, theme: str = "dark"):
    """Export slides to a plain-text file."""
    renderer = Renderer(theme)
    lines = []
    for i, slide in enumerate(slides):
        rendered = renderer.render_slide(slide, i, len(slides))
        # Strip ANSI codes for plain text
        clean = re.sub(r'\033\[[0-9;]*m', '', rendered)
        lines.append(clean)
        lines.append("\n" + "=" * 60 + "\n")
    with open(output, 'w') as f:
        f.write('\n'.join(lines))
    print(f"Exported {len(slides)} slides to {output}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Terminal Slides — Present Markdown slides in your terminal"
    )
    parser.add_argument("file", nargs="?", help="Markdown file with slides (separated by ---)")
    parser.add_argument("--theme", choices=list(THEMES.keys()), default="dark", help="Color theme")
    parser.add_argument("--auto", type=float, default=0, help="Auto-advance interval in seconds (0 = manual)")
    parser.add_argument("--export", metavar="FILE", help="Export slides to plain text file instead of presenting")
    parser.add_argument("--demo", action="store_true", help="Run the built-in demo presentation")

    args = parser.parse_args()

    if args.demo:
        md_text = DEMO_SLIDES
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                md_text = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    parser_obj = SlideParser(md_text)
    slides = parser_obj.slides

    if not slides:
        print("No slides found. Separate slides with --- in your Markdown.", file=sys.stderr)
        sys.exit(1)

    if args.export:
        export_text(slides, args.export, args.theme)
    else:
        presenter = Presenter(slides, args.theme, args.auto)
        presenter.run()


if __name__ == "__main__":
    main()