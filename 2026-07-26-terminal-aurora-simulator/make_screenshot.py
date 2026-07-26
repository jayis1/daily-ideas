#!/usr/bin/env python3
"""Generate a static SVG 'screenshot' of the aurora for the README.

Rather than duplicating the renderer, this imports the real ``aurora`` module,
asks it for a single frame (a truecolor ANSI string), then parses the ANSI
escape sequences back into per-cell RGB colors and characters and emits an
SVG. This guarantees the screenshot matches what users actually see —
including the moon, lake reflection, and any future renderer changes.
"""
import html
import re
import sys

# import the sibling aurora module
sys.path.insert(0, "/root/daily-ideas/2026-07-26-terminal-aurora-simulator")
import aurora  # noqa: E402

WIDTH = 120
HEIGHT = 32
CELL = 8

# Regex for truecolor foreground: \033[38;2;R;G;Bm
COLOR_RE = re.compile(r"\x1b\[38;2;(\d+);(\d+);(\d+)m")
RESET_RE = re.compile(r"\x1b\[0m")
# Other escape sequences (cursor moves, clear, etc.) — we ignore them.
OTHER_ESC_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def parse_ansi_frame(frame: str, width: int, height: int):
    """Parse an ANSI truecolor frame into a (colors, chars) grid.

    ``colors[y][x]`` is an (r, g, b) tuple; ``chars[y][x]`` is a single char.

    ``build_frame`` emits ``HOME`` then, for each screen row, a content line
    followed by ``CLEAR_LINE``, and finally ``RESET``. Splitting on ``\\n``
    therefore yields ``2*height + 2`` lines whose content rows sit at the odd
    indices 1, 3, 5, .... We extract exactly those rows so the screenshot
    matches what the terminal actually displays.
    """
    colors = [[(6, 10, 20)] * width for _ in range(height)]
    chars = [[" "] * width for _ in range(height)]

    # Collect the content lines from the frame. ``build_frame`` joins lines
    # with \n, so each logical line is a separate entry after split. Lines
    # that are purely escape sequences (HOME, CLEAR_LINE, RESET) contain no
    # printable characters once the escapes are stripped and are skipped.
    content_lines = []
    for line in frame.split("\n"):
        if OTHER_ESC_RE.sub("", line) == "":
            continue
        content_lines.append(line)

    # The first content line is the top screen row, etc.
    for row_idx, line in enumerate(content_lines[:height]):
        col = 0
        cur_color = (6, 10, 20)
        i = 0
        while i < len(line) and col < width:
            ch = line[i]
            if ch == "\x1b":
                m = COLOR_RE.match(line, i)
                if m:
                    cur_color = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    i = m.end()
                    continue
                m = RESET_RE.match(line, i)
                if m:
                    cur_color = (6, 10, 20)
                    i = m.end()
                    continue
                m = OTHER_ESC_RE.match(line, i)
                if m:
                    i = m.end()
                    continue
                # unknown escape — skip the ESC
                i += 1
                continue
            # a normal printable character
            colors[row_idx][col] = cur_color
            chars[row_idx][col] = ch
            col += 1
            i += 1
    return colors, chars


def main():
    # Render a single frame from the real aurora renderer.
    state = aurora.init_state(WIDTH, HEIGHT, 42, "magnetic")
    state.time = 3.0
    frame = aurora.build_frame(state)
    colors, chars = parse_ansi_frame(frame, WIDTH, HEIGHT)

    svg_w = WIDTH * CELL
    svg_h = HEIGHT * CELL
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" '
        f'height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">'
    ]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="#06060f"/>')
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = colors[y][x]
            parts.append(
                f'<rect x="{x*CELL}" y="{y*CELL}" width="{CELL}" '
                f'height="{CELL}" fill="rgb({r},{g},{b})"/>'
            )
            ch = chars[y][x]
            if ch == " ":
                continue
            # text color: brighten the cell color so the glyph is visible
            tr = min(255, r + 80)
            tg = min(255, g + 80)
            tb = min(255, b + 80)
            parts.append(
                f'<text x="{x*CELL+CELL/2}" y="{y*CELL+CELL*0.8}" '
                f'font-family="monospace" font-size="{CELL*0.8}" '
                f'text-anchor="middle" '
                f'fill="rgb({tr},{tg},{tb})">{html.escape(ch)}</text>'
            )
    parts.append("</svg>")
    print("\n".join(parts))


if __name__ == "__main__":
    main()