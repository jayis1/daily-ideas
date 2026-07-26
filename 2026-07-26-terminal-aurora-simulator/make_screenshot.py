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


def parse_ansi_frame(frame: str, width: int, height: int):
    """Parse an ANSI truecolor frame into a (colors, chars) grid.

    ``colors[y][x]`` is an (r, g, b) tuple; ``chars[y][x]`` is a single char.
    """
    # split into "lines" — the frame uses \n between rows
    lines = frame.split("\n")
    colors = [[(6, 10, 20)] * width for _ in range(height)]
    chars = [[" "] * width for _ in range(height)]
    # regex for truecolor foreground: \033[38;2;R;G;Bm
    color_re = re.compile(r"\x1b\[38;2;(\d+);(\d+);(\d+)m")
    reset_re = re.compile(r"\x1b\[0m")
    # other escape sequences (cursor moves, clear, etc.) — we ignore them
    other_esc_re = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

    for row_idx, line in enumerate(lines[:height]):
        col = 0
        cur_color = (6, 10, 20)
        i = 0
        while i < len(line) and col < width:
            ch = line[i]
            if ch == "\x1b":
                # parse an escape sequence
                m = color_re.match(line, i)
                if m:
                    cur_color = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    i = m.end()
                    continue
                m = reset_re.match(line, i)
                if m:
                    cur_color = (6, 10, 20)
                    i = m.end()
                    continue
                m = other_esc_re.match(line, i)
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