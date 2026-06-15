#!/usr/bin/env python3
"""
Morse Wave Translator — Encode/decode text as visual Morse code waveforms.

Turns text into Morse code rendered as animated ASCII sine waves (dots = short
pulse, dashes = long pulse) and can decode visual Morse back to text. If `sox`
is installed it also plays real audio beeps. Supports color output, statistics,
file I/O, and configurable wave parameters.

Usage:
    python3 morse_wave.py encode "HELLO WORLD"
    python3 morse_wave.py decode "... --- ..."
    python3 morse_wave.py wave "SOS"
    python3 morse_wave.py play "CQ CQ DE W1AW"
    python3 morse_wave.py stats "HELLO WORLD"
    python3 morse_wave.py compact "SOS"
    python3 morse_wave.py interactive
"""

import sys
import os
import time
import math
import subprocess
import shutil
import argparse

__version__ = "1.1.0"

# ─── ANSI Color Codes ────────────────────────────────────────────────────────

class Colors:
    """ANSI color codes for terminal output."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[32m"
    CYAN    = "\033[36m"
    YELLOW  = "\033[33m"
    MAGENTA = "\033[35m"
    RED     = "\033[31m"
    WHITE   = "\033[37m"
    BG_GREEN = "\033[42m"
    BG_CYAN  = "\033[46m"

    @staticmethod
    def supports_color() -> bool:
        """Check if the terminal supports ANSI colors."""
        if os.environ.get("NO_COLOR"):
            return False
        if not hasattr(sys.stdout, "isatty"):
            return False
        if not sys.stdout.isatty():
            return False
        term = os.environ.get("TERM", "")
        if term in ("dumb", "unknown"):
            return False
        return True


# ─── Morse Code Tables ───────────────────────────────────────────────────────

MORSE_ENCODE = {
    "A": ".-",    "B": "-...",  "C": "-.-.",  "D": "-..",   "E": ".",
    "F": "..-.",  "G": "--.",   "H": "....",  "I": "..",    "J": ".---",
    "K": "-.-",  "L": ".-..",  "M": "--",    "N": "-.",    "O": "---",
    "P": ".--.", "Q": "--.-",  "R": ".-.",   "S": "...",   "T": "-",
    "U": "..-",  "V": "...-",  "W": ".--",  "X": "-..-",  "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.",
    "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-",
    "&": ".-...",  ":": "---...", ";": "-.-.-.", "=": "-...-",
    "+": ".-.-.",  "-": "-....-", "_": "..--.-", '"': ".-..-.",
    "$": "...-..-", "@": ".--.-.",
}

MORSE_DECODE = {v: k for k, v in MORSE_ENCODE.items()}

# Prosigns (procedural signals) used in ham radio
PROSIGNS = {
    "<AA>": ".-.-",    # New line / end of message
    "<AR>": ".-.-.",   # End of transmission
    "<AS>": ".-...",   # Wait
    "<BK>": "-...-.-", # Break
    "<BT>": "-...-",   # Separator
    "<CL>": "-.-..-..",# Closing station
    "<CQ>": "-.-.--.-",# General call
    "<KN>": "-.--.",   # Invitation to transmit (specific)
    "<SK>": "...-.-",  # End of work
    "<SN>": "...-.",    # Understood
}


# ─── Encoding / Decoding ──────────────────────────────────────────────────────

def text_to_morse(text: str) -> str:
    """Convert plain text to Morse code string.

    Letters separated by single space, words by ' / '.
    Unknown characters are represented as '?' in the output.
    Handles prosigns like <AR>, <SK>, etc.

    Args:
        text: Plain text string to encode.

    Returns:
        Morse code string with ' / ' between words.
    """
    if not text or not text.strip():
        return ""

    words = text.upper().strip().split()
    morse_words = []
    for word in words:
        morse_letters = []
        # Check for prosigns embedded in angle brackets
        i = 0
        while i < len(word):
            if word[i] == "<":
                # Try to find matching >
                end = word.find(">", i)
                if end != -1:
                    prosign = word[i:end + 1]
                    if prosign in PROSIGNS:
                        morse_letters.append(PROSIGNS[prosign])
                        i = end + 1
                        continue
                    # Not a known prosign — treat '<' as unknown
            ch = word[i]
            if ch in MORSE_ENCODE:
                morse_letters.append(MORSE_ENCODE[ch])
            else:
                morse_letters.append("?")  # unknown char placeholder
            i += 1
        morse_words.append(" ".join(morse_letters))
    return " / ".join(morse_words)


def morse_to_text(morse: str) -> str:
    """Convert Morse code string back to plain text.

    Handles prosigns: if a Morse sequence matches a prosign, the prosign
    notation (e.g. <AR>) is returned instead of the raw letter.

    Args:
        morse: Morse code string with ' / ' between words.

    Returns:
        Decoded plain text string (uppercase).
    """
    morse = morse.strip()
    if not morse:
        return ""

    # Build reverse prosign lookup
    prosign_decode = {v: k for k, v in PROSIGNS.items()}

    words = morse.split(" / ")
    result = []
    for word in words:
        letters = []
        for symbol in word.split():
            if symbol in MORSE_DECODE:
                letters.append(MORSE_DECODE[symbol])
            elif symbol in prosign_decode:
                letters.append(prosign_decode[symbol])
            else:
                letters.append("?")
        result.append("".join(letters))
    return " ".join(result)


# ─── Statistics ─────────────────────────────────────────────────────────────────

def compute_stats(morse: str, wpm: float = 15.0) -> dict:
    """Compute statistics about a Morse code transmission.

    Args:
        morse: Morse code string.
        wpm: Words per minute (PARIS standard) for timing.

    Returns:
        Dictionary with transmission statistics.
    """
    unit_ms = 1200.0 / wpm  # milliseconds per unit

    dot_count = 0
    dash_count = 0
    symbol_gaps = 0
    letter_gaps = 0
    word_gaps = 0
    char_count = 0

    words = morse.split(" / ")
    for i, word in enumerate(words):
        if i > 0:
            word_gaps += 1
        symbols = word.split()
        for j, sym in enumerate(symbols):
            if j > 0:
                letter_gaps += 1
            char_count += 1
            for k, element in enumerate(sym):
                if k > 0:
                    symbol_gaps += 1
                if element == ".":
                    dot_count += 1
                elif element == "-":
                    dash_count += 1

    # Timing calculations
    dot_time = dot_count * unit_ms
    dash_time = dash_count * 3 * unit_ms
    symbol_gap_time = symbol_gaps * unit_ms
    letter_gap_time = letter_gaps * 3 * unit_ms
    word_gap_time = word_gaps * 7 * unit_ms
    total_time = dot_time + dash_time + symbol_gap_time + letter_gap_time + word_gap_time

    return {
        "characters": char_count,
        "words": len(words),
        "dots": dot_count,
        "dashes": dash_count,
        "symbol_gaps": symbol_gaps,
        "letter_gaps": letter_gaps,
        "word_gaps": word_gaps,
        "wpm": wpm,
        "unit_ms": round(unit_ms, 2),
        "dot_time_ms": round(dot_time, 1),
        "dash_time_ms": round(dash_time, 1),
        "total_time_ms": round(total_time, 1),
        "total_time_s": round(total_time / 1000.0, 2),
    }


def format_stats(stats: dict, use_color: bool = False) -> str:
    """Format statistics dictionary into a readable string.

    Args:
        stats: Statistics dictionary from compute_stats().
        use_color: Whether to use ANSI color codes.

    Returns:
        Formatted multi-line string.
    """
    c = Colors
    if use_color:
        label = c.CYAN + c.BOLD
        value = c.GREEN
        reset = c.RESET
        dim = c.DIM
    else:
        label = value = reset = dim = ""

    lines = [
        f"{label}╔══════════════════════════════════════════╗{reset}",
        f"{label}║{reset}        📊  Transmission Statistics       {label}║{reset}",
        f"{label}╠══════════════════════════════════════════╣{reset}",
        f"{label}║{reset}  Characters:    {value}{stats['characters']:>6}{reset}   {dim}( Morse symbols ){dim}   {label}║{reset}",
        f"{label}║{reset}  Words:         {value}{stats['words']:>6}{reset}                        {label}║{reset}",
        f"{label}║{reset}  Dots (·):      {value}{stats['dots']:>6}{reset}                        {label}║{reset}",
        f"{label}║{reset}  Dashes (−):    {value}{stats['dashes']:>6}{reset}                        {label}║{reset}",
        f"{label}║{reset}  Symbol gaps:   {value}{stats['symbol_gaps']:>6}{reset}                        {label}║{reset}",
        f"{label}║{reset}  Letter gaps:   {value}{stats['letter_gaps']:>6}{reset}                        {label}║{reset}",
        f"{label}║{reset}  Word gaps:     {value}{stats['word_gaps']:>6}{reset}                        {label}║{reset}",
        f"{label}╠══════════════════════════════════════════╣{reset}",
        f"{label}║{reset}  Speed:         {value}{stats['wpm']:>6.1f}{reset}  {dim}WPM{dim}                  {label}║{reset}",
        f"{label}║{reset}  Unit length:   {value}{stats['unit_ms']:>6.2f}{reset}  {dim}ms{dim}                  {label}║{reset}",
        f"{label}║{reset}  Dot time:      {value}{stats['dot_time_ms']:>6.1f}{reset}  {dim}ms{dim}                  {label}║{reset}",
        f"{label}║{reset}  Dash time:     {value}{stats['dash_time_ms']:>6.1f}{reset}  {dim}ms{dim}                  {label}║{reset}",
        f"{label}║{reset}  Total time:    {value}{stats['total_time_ms']:>6.1f}{reset}  {dim}ms ({stats['total_time_s']:.2f}s){dim}  {label}║{reset}",
        f"{label}╚══════════════════════════════════════════╝{reset}",
    ]
    return "\n".join(lines)


# ─── Waveform Rendering ───────────────────────────────────────────────────────

def _make_sine_wave(width: int, amplitude: int = 2, frequency: float = 0.5,
                    offset: int = 0) -> list[str]:
    """Return a list of `width` characters that trace a sine wave
    across multiple lines. Returns rows top-to-bottom.

    Args:
        width: Number of horizontal characters.
        amplitude: Vertical amplitude in rows.
        frequency: Wave frequency (cycles per character).
        offset: Phase offset for continuity.

    Returns:
        List of strings, one per row, each `width` characters long.
    """
    if width <= 0:
        return []
    rows = 2 * amplitude + 1
    mid = amplitude
    lines = [[" "] * width for _ in range(rows)]
    for x in range(width):
        t = (x + offset) * frequency
        y = mid - round(amplitude * math.sin(t))
        # Clamp y to valid range
        y = max(0, min(rows - 1, y))
        # Pick a character depending on direction
        next_t = (x + 1 + offset) * frequency
        next_y = mid - round(amplitude * math.sin(next_t))
        next_y = max(0, min(rows - 1, next_y))
        if y < next_y:
            ch = "╲"
        elif y > next_y:
            ch = "╱"
        else:
            ch = "─"
        lines[y][x] = ch
    return ["".join(row) for row in lines]


def render_waveform(morse: str, amplitude: int = 2, wave_freq: float = 0.4,
                    dot_width: int = 6, dash_width: int = 18,
                    symbol_gap: int = 4, letter_gap: int = 10,
                    word_gap: int = 20, use_color: bool = False) -> str:
    """Render Morse code as a visual sine-wave waveform.

    Dots produce a short burst of sine wave, dashes a long burst.
    Gaps between symbols/letters/words are flat lines.

    Args:
        morse: Morse code string.
        amplitude: Vertical amplitude of the sine wave.
        wave_freq: Frequency of the sine wave.
        dot_width: Width of a dot in characters.
        dash_width: Width of a dash in characters.
        symbol_gap: Gap between dots/dashes within a letter.
        letter_gap: Gap between letters.
        word_gap: Gap between words.
        use_color: Whether to color the waveform.

    Returns:
        Multi-line string with the rendered waveform.
    """
    if not morse or not morse.strip():
        return ""

    # Build a sequence of (type, width) segments
    segments = []  # list of ("on"/"off", pixel_width)

    for i, word in enumerate(morse.split(" / ")):
        if i > 0:
            segments.append(("off", word_gap))
        for j, symbol in enumerate(word.split()):
            if j > 0:
                segments.append(("off", letter_gap))
            for k, element in enumerate(symbol):
                if k > 0:
                    segments.append(("off", symbol_gap))
                if element == ".":
                    segments.append(("on", dot_width))
                elif element == "-":
                    segments.append(("on", dash_width))
                else:
                    segments.append(("off", 2))

    if not segments:
        return ""

    # Now render each segment
    rows_needed = 2 * amplitude + 1
    mid = amplitude
    canvas = [[" "] * 0 for _ in range(rows_needed)]  # grow as needed
    x_offset = 0

    # Track which cells are "on" for coloring
    on_cells = set()  # (row, col) pairs

    phase = 0
    for seg_type, seg_width in segments:
        if seg_type == "on":
            wave_rows = _make_sine_wave(seg_width, amplitude, wave_freq, offset=phase)
            for r in range(rows_needed):
                while len(canvas[r]) < x_offset + seg_width:
                    canvas[r].append(" ")
                for c in range(seg_width):
                    canvas[r][x_offset + c] = wave_rows[r][c]
                    if wave_rows[r][c] != " ":
                        on_cells.add((r, x_offset + c))
            phase += seg_width
        else:
            # Flat line at the mid
            for c in range(seg_width):
                while len(canvas[mid]) < x_offset + c + 1:
                    canvas[mid].append(" ")
                canvas[mid][x_offset + c] = "─"
                on_cells.add((mid, x_offset + c))
            # Make sure other rows exist
            for r in range(rows_needed):
                while len(canvas[r]) < x_offset + seg_width:
                    canvas[r].append(" ")
            phase = 0  # reset phase after silence
        x_offset += seg_width

    # Trim trailing spaces from each row and remove empty bottom rows
    result_rows = []
    for row in canvas:
        line = "".join(row).rstrip()
        result_rows.append(line)

    # Remove trailing empty rows
    while result_rows and not result_rows[-1].strip():
        result_rows.pop()

    # Apply color if requested
    if use_color and Colors.supports_color():
        colored_rows = []
        for r, line in enumerate(result_rows):
            colored_line = ""
            for c, ch in enumerate(line):
                if (r, c) in on_cells:
                    colored_line += Colors.CYAN + ch + Colors.RESET
                else:
                    colored_line += ch
            colored_rows.append(colored_line)
        result_rows = colored_rows

    return "\n".join(result_rows)


def render_compact_waveform(morse: str, width: int = 70,
                            use_color: bool = False) -> str:
    """Render a compact single-line waveform representation.

    Uses Unicode block elements for a retro oscilloscope look.

    Args:
        morse: Morse code string.
        width: Maximum width before wrapping to new line.
        use_color: Whether to color the output.

    Returns:
        Multi-line string with compact waveform and Morse annotation.
    """
    if not morse or not morse.strip():
        return ""

    # Build signal: list of amplitudes (0=off, 1=dot-level, 2=dash-level)
    signal = []
    for i, word in enumerate(morse.split(" / ")):
        if i > 0:
            signal.extend([0] * 3)  # word gap
        for j, sym in enumerate(word.split()):
            if j > 0:
                signal.extend([0] * 2)  # letter gap
            for k, element in enumerate(sym):
                if k > 0:
                    signal.extend([0] * 1)  # symbol gap
                if element == ".":
                    signal.extend([1] * 2)
                elif element == "-":
                    signal.extend([2] * 6)

    if not signal:
        return ""

    # Map signal to visual characters per column
    chars = " ░▒▓█"
    color_map = {
        0: Colors.DIM,
        1: Colors.GREEN,
        2: Colors.YELLOW + Colors.BOLD,
    }

    output = ""
    line = ""
    for val in signal:
        if use_color and Colors.supports_color():
            ch = color_map.get(val, Colors.RESET) + chars[val] + Colors.RESET
        else:
            ch = chars[val]
        line += ch
        if len(line) >= width:
            output += line + "\n"
            line = ""
    if line:
        output += line + "\n"

    # Add Morse annotation below (always plain, no color)
    morse_line = ""
    for i, word in enumerate(morse.split(" / ")):
        if i > 0:
            morse_line += "   "
        for j, sym in enumerate(word.split()):
            if j > 0:
                morse_line += "  "
            for k, element in enumerate(sym):
                if k > 0:
                    morse_line += " "
                morse_line += element
    output += "\n" + morse_line

    return output


# ─── Audio Playback ───────────────────────────────────────────────────────────

def has_sox() -> bool:
    """Check if SoX (play command) is available for audio."""
    return shutil.which("play") is not None


def play_morse(morse: str, wpm: float = 15.0, freq: int = 700,
               volume: float = 0.5) -> None:
    """Play Morse code as audio tones using SoX.

    Args:
        morse: Morse code string.
        wpm: Words per minute (PARIS standard).
        freq: Tone frequency in Hz.
        volume: Volume 0.0-1.0.

    Raises:
        RuntimeError: If SoX is not available (falls back to visual).
    """
    if not morse or not morse.strip():
        print("Nothing to play.")
        return

    if not has_sox():
        print("⚠  SoX not found — install with: apt install sox  (or brew install sox)")
        print("   Falling back to visual-only mode.\n")
        print(render_compact_waveform(morse))
        return

    # Timing (PARIS standard): 1 unit = 1200/wpm ms
    unit_ms = 1200.0 / wpm
    dot_ms = unit_ms
    dash_ms = 3 * unit_ms
    symbol_gap_ms = unit_ms
    letter_gap_ms = 3 * unit_ms
    word_gap_ms = 7 * unit_ms

    for i, word in enumerate(morse.split(" / ")):
        if i > 0:
            time.sleep(word_gap_ms / 1000.0)
        for j, sym in enumerate(word.split()):
            if j > 0:
                time.sleep(letter_gap_ms / 1000.0)
            for k, element in enumerate(sym):
                if k > 0:
                    time.sleep(symbol_gap_ms / 1000.0)
                duration = dot_ms if element == "." else dash_ms
                dur_s = duration / 1000.0
                try:
                    subprocess.run(
                        ["play", "-q", "-n", "synth", str(dur_s), "sine",
                         str(freq), "vol", f"{volume:.2f}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except FileNotFoundError:
                    print("⚠  play command failed")
                    return
                except OSError as e:
                    print(f"⚠  play command error: {e}")
                    return


# ─── Terminal Animation ──────────────────────────────────────────────────────

def animate_waveform(morse: str, amplitude: int = 2, speed: float = 0.05,
                     use_color: bool = False) -> None:
    """Animate the waveform being drawn in real-time, left-to-right.

    Args:
        morse: Morse code string.
        amplitude: Vertical amplitude of the sine wave.
        speed: Delay between drawing characters (seconds).
        use_color: Whether to color the animation.
    """
    full = render_waveform(morse, amplitude=amplitude, use_color=use_color)
    if not full:
        return
    lines = full.split("\n")
    num_lines = len(lines)
    max_width = max(len(l) for l in lines) if lines else 0

    # Strip ANSI codes for width calculation but keep them for display
    def strip_ansi(s: str) -> str:
        """Remove ANSI escape sequences for length calculation."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', s)

    # Clear and set up
    sys.stdout.write("\033[2J\033[H")  # clear screen, home cursor
    sys.stdout.flush()

    # Draw character by character
    col = 0
    for col in range(max_width):
        for row_idx, line in enumerate(lines):
            # Account for ANSI codes when positioning
            if col < len(strip_ansi(line)):
                # Find the actual character at display position col
                display_pos = 0
                actual_pos = 0
                in_escape = False
                char_at_col = " "
                while actual_pos < len(line) and display_pos <= col:
                    if line[actual_pos] == '\033':
                        in_escape = True
                    if in_escape:
                        if line[actual_pos] == 'm' and actual_pos > 0:
                            in_escape = False
                        actual_pos += 1
                        continue
                    if display_pos == col:
                        char_at_col = line[actual_pos]
                        break
                    display_pos += 1
                    actual_pos += 1
                sys.stdout.write(f"\033[{row_idx + 1};{col + 1}H{char_at_col}")
        sys.stdout.flush()
        if speed > 0:
            time.sleep(speed)

    # Move cursor below the waveform
    sys.stdout.write(f"\033[{num_lines + 1};1H")
    sys.stdout.flush()


# ─── Interactive Mode ─────────────────────────────────────────────────────────

def interactive(use_color: bool = False) -> None:
    """Run an interactive Morse code translator.

    Args:
        use_color: Whether to use ANSI colors.
    """
    c = Colors
    if use_color:
        border = c.CYAN
        title = c.YELLOW + c.BOLD
        cmd_color = c.GREEN
        reset = c.RESET
    else:
        border = title = cmd_color = reset = ""

    print(f"{border}╔══════════════════════════════════════════════════╗{reset}")
    print(f"{border}║{reset}        {title}📻  MORSE WAVE TRANSLATOR  📻{reset}             {border}║{reset}")
    print(f"{border}╠══════════════════════════════════════════════════╣{reset}")
    print(f"{border}║{reset}  {cmd_color}Commands:{reset}                                       {border}║{reset}")
    print(f"{border}║{reset}    {cmd_color}<text>{reset}       Encode text → Morse + waveform    {border}║{reset}")
    print(f"{border}║{reset}    {cmd_color}d <morse>{reset}    Decode Morse → text               {border}║{reset}")
    print(f"{border}║{reset}    {cmd_color}w <text>{reset}     Show animated waveform           {border}║{reset}")
    print(f"{border}║{reset}    {cmd_color}p <text>{reset}     Play Morse as audio              {border}║{reset}")
    print(f"{border}║{reset}    {cmd_color}c <text>{reset}     Show compact waveform             {border}║{reset}")
    print(f"{border}║{reset}    {cmd_color}s <text>{reset}     Show transmission statistics       {border}║{reset}")
    print(f"{border}║{reset}    {cmd_color}h{reset}            Show this help                   {border}║{reset}")
    print(f"{border}║{reset}    {cmd_color}q{reset}            Quit                              {border}║{reset}")
    print(f"{border}╚══════════════════════════════════════════════════╝{reset}")
    print()

    history = []  # Track recent commands

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n73! (Best regards in ham radio 📡)")
            break

        if not raw:
            continue

        history.append(raw)

        if raw.lower() == "q":
            print("73! 📡")
            break

        if raw.lower() == "h":
            print(f"  {cmd_color}Commands:{reset}")
            print(f"    {cmd_color}<text>{reset}       Encode text → Morse + waveform")
            print(f"    {cmd_color}d <morse>{reset}    Decode Morse → text")
            print(f"    {cmd_color}w <text>{reset}     Show animated waveform")
            print(f"    {cmd_color}p <text>{reset}     Play Morse as audio")
            print(f"    {cmd_color}c <text>{reset}     Show compact waveform")
            print(f"    {cmd_color}s <text>{reset}     Show transmission statistics")
            print(f"    {cmd_color}h{reset}            Show this help")
            print(f"    {cmd_color}q{reset}            Quit")
            print()
            continue

        if raw.startswith("d "):
            morse = raw[2:]
            text = morse_to_text(morse)
            print(f"  Decoded: {text}")
            print()

        elif raw.startswith("w "):
            text = raw[2:]
            morse = text_to_morse(text)
            print(f"  Morse: {morse}")
            print(f"  Text:  {text.upper()}")
            print()
            try:
                animate_waveform(morse, speed=0.02, use_color=use_color)
            except KeyboardInterrupt:
                print("\n  Animation interrupted.")
            print()

        elif raw.startswith("p "):
            text = raw[2:]
            morse = text_to_morse(text)
            print(f"  Morse: {morse}")
            print(f"  Playing... (Ctrl+C to stop)")
            try:
                play_morse(morse)
            except KeyboardInterrupt:
                pass
            print("  Done.")
            print()

        elif raw.startswith("c "):
            text = raw[2:]
            morse = text_to_morse(text)
            print(f"  Morse: {morse}")
            print(render_compact_waveform(morse, use_color=use_color))
            print()

        elif raw.startswith("s "):
            text = raw[2:]
            morse = text_to_morse(text)
            stats = compute_stats(morse)
            print(f"  Morse: {morse}")
            print()
            print(format_stats(stats, use_color=use_color))
            print()

        else:
            # Default: encode
            text = raw
            morse = text_to_morse(text)
            print(f"  Text:  {text.upper()}")
            print(f"  Morse: {morse}")
            print()
            print(render_waveform(morse, use_color=use_color))
            print()


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="morse_wave",
        description="Morse Wave Translator — encode/decode text as visual Morse code waveforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Morse format: dots and dashes separated by spaces, letters by double spaces,
              words by ' / '.

Examples:
  morse_wave.py encode "HELLO WORLD"      Encode text to Morse + waveform
  morse_wave.py decode "... --- ..."       Decode Morse to text
  morse_wave.py wave "SOS"                 Show animated waveform
  morse_wave.py play "CQ CQ DE W1AW"       Play Morse as audio (needs SoX)
  morse_wave.py compact "SOS"              Show compact block-element waveform
  morse_wave.py stats "HELLO WORLD"        Show transmission statistics
  morse_wave.py interactive                Interactive mode
  morse_wave.py encode --file input.txt   Encode text from a file
  morse_wave.py encode --output out.txt "HELLO"  Save output to file
""",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # encode
    p_encode = subparsers.add_parser("encode", help="Encode text to Morse + waveform")
    p_encode.add_argument("text", nargs="*", help="Text to encode")
    p_encode.add_argument("--file", "-f", type=str, help="Read input text from a file")
    p_encode.add_argument("--output", "-o", type=str, help="Write output to a file")
    p_encode.add_argument("--amplitude", "-a", type=int, default=2, help="Wave amplitude (default: 2)")
    p_encode.add_argument("--color", action="store_true", help="Enable color output")

    # decode
    p_decode = subparsers.add_parser("decode", help="Decode Morse to text")
    p_decode.add_argument("morse", nargs="*", help="Morse code to decode")
    p_decode.add_argument("--file", "-f", type=str, help="Read Morse input from a file")
    p_decode.add_argument("--output", "-o", type=str, help="Write output to a file")

    # wave (animated)
    p_wave = subparsers.add_parser("wave", help="Show animated waveform")
    p_wave.add_argument("text", nargs="*", help="Text to animate")
    p_wave.add_argument("--file", "-f", type=str, help="Read input text from a file")
    p_wave.add_argument("--amplitude", "-a", type=int, default=2, help="Wave amplitude (default: 2)")
    p_wave.add_argument("--color", action="store_true", help="Enable color output")

    # play
    p_play = subparsers.add_parser("play", help="Play Morse as audio (needs SoX)")
    p_play.add_argument("text", nargs="*", help="Text to play")
    p_play.add_argument("--file", "-f", type=str, help="Read input text from a file")
    p_play.add_argument("--wpm", "-w", type=float, default=15.0, help="Words per minute (default: 15)")
    p_play.add_argument("--freq", type=int, default=700, help="Tone frequency in Hz (default: 700)")
    p_play.add_argument("--volume", "-v", type=float, default=0.5, help="Volume 0.0-1.0 (default: 0.5)")

    # compact
    p_compact = subparsers.add_parser("compact", help="Show compact block-element waveform")
    p_compact.add_argument("text", nargs="*", help="Text to show")
    p_compact.add_argument("--file", "-f", type=str, help="Read input text from a file")
    p_compact.add_argument("--output", "-o", type=str, help="Write output to a file")
    p_compact.add_argument("--width", type=int, default=70, help="Display width (default: 70)")
    p_compact.add_argument("--color", action="store_true", help="Enable color output")

    # stats
    p_stats = subparsers.add_parser("stats", help="Show transmission statistics")
    p_stats.add_argument("text", nargs="*", help="Text to analyze")
    p_stats.add_argument("--file", "-f", type=str, help="Read input text from a file")
    p_stats.add_argument("--wpm", "-w", type=float, default=15.0, help="Words per minute (default: 15)")
    p_stats.add_argument("--color", action="store_true", help="Enable color output")

    # interactive
    p_interactive = subparsers.add_parser("interactive", help="Interactive mode")
    p_interactive.add_argument("--color", action="store_true", help="Enable color output")

    return parser


def _read_input(args_text: list, file_path: str | None = None) -> str:
    """Read input text from arguments or a file, or fall back to stdin.

    Args:
        args_text: List of text arguments (joined with spaces).
        file_path: Optional file path to read from.

    Returns:
        Input text string.
    """
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            sys.exit(1)

    if args_text:
        return " ".join(args_text)

    # Try reading from stdin if it's not a TTY (piped input)
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    return ""


def _write_output(content: str, output_path: str | None = None) -> None:
    """Write output content to stdout or a file.

    Args:
        content: The string content to output.
        output_path: Optional file path to write to.
    """
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            print(f"Output written to: {output_path}")
        except OSError as e:
            print(f"Error writing to {output_path}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(content)


def main():
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cmd = args.command.lower()

    if cmd == "encode":
        text = _read_input(args.text, getattr(args, "file", None))
        if not text:
            print("Error: No text provided. Use 'morse_wave.py encode <text>' or --file <path>",
                  file=sys.stderr)
            sys.exit(1)
        morse = text_to_morse(text)
        use_color = getattr(args, "color", False)
        amplitude = getattr(args, "amplitude", 2)
        output_path = getattr(args, "output", None)

        header = f"Text:  {text.upper()}\nMorse: {morse}\n"
        waveform = render_waveform(morse, amplitude=amplitude, use_color=use_color)
        full_output = header + "\n" + waveform

        if output_path:
            _write_output(full_output, output_path)
        else:
            print(header)
            print(waveform)

    elif cmd == "decode":
        morse = _read_input(args.morse, getattr(args, "file", None))
        if not morse:
            print("Error: No Morse code provided.", file=sys.stderr)
            sys.exit(1)
        text = morse_to_text(morse)
        output_path = getattr(args, "output", None)

        full_output = f"Morse: {morse}\nText:  {text}"
        if output_path:
            _write_output(full_output, output_path)
        else:
            print(f"Morse: {morse}")
            print(f"Text:  {text}")

    elif cmd == "wave":
        text = _read_input(args.text, getattr(args, "file", None))
        if not text:
            print("Error: No text provided.", file=sys.stderr)
            sys.exit(1)
        morse = text_to_morse(text)
        use_color = getattr(args, "color", False)
        amplitude = getattr(args, "amplitude", 2)

        print(f"Text:  {text.upper()}")
        print(f"Morse: {morse}")
        print()
        try:
            animate_waveform(morse, amplitude=amplitude, speed=0.02,
                             use_color=use_color)
        except KeyboardInterrupt:
            print("\nInterrupted.")

    elif cmd == "play":
        text = _read_input(args.text, getattr(args, "file", None))
        if not text:
            print("Error: No text provided.", file=sys.stderr)
            sys.exit(1)
        morse = text_to_morse(text)
        wpm = getattr(args, "wpm", 15.0)
        freq = getattr(args, "freq", 700)
        volume = getattr(args, "volume", 0.5)

        # Validate parameters
        if wpm <= 0:
            print("Error: WPM must be positive.", file=sys.stderr)
            sys.exit(1)
        if freq <= 0:
            print("Error: Frequency must be positive.", file=sys.stderr)
            sys.exit(1)
        if not 0.0 <= volume <= 1.0:
            print("Error: Volume must be between 0.0 and 1.0.", file=sys.stderr)
            sys.exit(1)

        print(f"Text:  {text.upper()}")
        print(f"Morse: {morse}")
        print(f"Speed: {wpm} WPM, Frequency: {freq} Hz")
        print("Playing... (Ctrl+C to stop)")
        try:
            play_morse(morse, wpm=wpm, freq=freq, volume=volume)
        except KeyboardInterrupt:
            pass
        print("Done.")

    elif cmd == "compact":
        text = _read_input(args.text, getattr(args, "file", None))
        if not text:
            print("Error: No text provided.", file=sys.stderr)
            sys.exit(1)
        morse = text_to_morse(text)
        use_color = getattr(args, "color", False)
        width = getattr(args, "width", 70)
        output_path = getattr(args, "output", None)

        header = f"Text:  {text.upper()}\nMorse: {morse}\n"
        waveform = render_compact_waveform(morse, width=width, use_color=use_color)
        full_output = header + "\n" + waveform

        if output_path:
            _write_output(full_output, output_path)
        else:
            print(header)
            print(waveform)

    elif cmd == "stats":
        text = _read_input(args.text, getattr(args, "file", None))
        if not text:
            print("Error: No text provided.", file=sys.stderr)
            sys.exit(1)
        morse = text_to_morse(text)
        wpm = getattr(args, "wpm", 15.0)
        use_color = getattr(args, "color", False)

        if wpm <= 0:
            print("Error: WPM must be positive.", file=sys.stderr)
            sys.exit(1)

        stats = compute_stats(morse, wpm=wpm)
        print(f"Text:  {text.upper()}")
        print(f"Morse: {morse}")
        print()
        print(format_stats(stats, use_color=use_color))

    elif cmd == "interactive":
        use_color = getattr(args, "color", False)
        interactive(use_color=use_color)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()