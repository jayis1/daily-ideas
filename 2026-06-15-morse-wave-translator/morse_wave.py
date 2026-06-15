#!/usr/bin/env python3
"""
Morse Wave Translator — Encode/decode text as visual Morse code waveforms.

Turns text into Morse code rendered as animated ASCII sine waves (dots = short
pulse, dashes = long pulse) and can decode visual Morse back to text. If `sox`
is installed it also plays real audio beeps.

Usage:
    python3 morse_wave.py encode "HELLO WORLD"
    python3 morse_wave.py decode ".../..././.-../.-../../---/....././.-../.-../---"
    python3 morse_wave.py wave "SOS"
    python3 morse_wave.py play "CQ CQ DE W1AW"
    python3 morse_wave.py interactive
"""

import sys
import os
import time
import math
import subprocess
import shutil

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
    "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-",
    "+": ".-.-.", "-": "-....-", "_": "..--.-", '"': ".-..-.",
    "$": "...-..-", "@": ".--.-.",
}

MORSE_DECODE = {v: k for k, v in MORSE_ENCODE.items()}


# ─── Encoding / Decoding ──────────────────────────────────────────────────────

def text_to_morse(text: str) -> str:
    """Convert plain text to Morse code string.
    Letters separated by single space, words by ' / '.
    """
    words = text.upper().strip().split()
    morse_words = []
    for word in words:
        morse_letters = []
        for ch in word:
            if ch in MORSE_ENCODE:
                morse_letters.append(MORSE_ENCODE[ch])
            else:
                morse_letters.append("?")  # unknown char
        morse_words.append(" ".join(morse_letters))
    return " / ".join(morse_words)


def morse_to_text(morse: str) -> str:
    """Convert Morse code string back to plain text."""
    morse = morse.strip()
    if not morse:
        return ""
    words = morse.split(" / ")
    result = []
    for word in words:
        letters = []
        for symbol in word.split():
            if symbol in MORSE_DECODE:
                letters.append(MORSE_DECODE[symbol])
            else:
                letters.append("?")
        result.append("".join(letters))
    return " ".join(result)


# ─── Waveform Rendering ───────────────────────────────────────────────────────

# Waveform characters (sine wave building blocks)
# Using block characters for a richer look
WAVE_HIGH = ["⣷", "⣾", "⣽", "⣻", "⢿", "⡿", "⣿"]  # unused for now

# Simpler ASCII approach — draw a sine wave in a 2-row buffer
def _make_sine_wave(width: int, amplitude: int = 2, frequency: float = 0.5,
                    offset: int = 0) -> list[str]:
    """Return a list of `width` characters that trace a sine wave
    across multiple lines. Returns rows top-to-bottom."""
    rows = 2 * amplitude + 1
    mid = amplitude
    lines = [[" "] * width for _ in range(rows)]
    for x in range(width):
        t = (x + offset) * frequency
        y = mid - round(amplitude * math.sin(t))
        # Pick a character depending on direction
        next_t = (x + 1 + offset) * frequency
        next_y = mid - round(amplitude * math.sin(next_t))
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
                    word_gap: int = 20) -> str:
    """Render Morse code as a visual sine-wave waveform.

    Dots produce a short burst of sine wave, dashes a long burst.
    Gaps between symbols/letters/words are flat lines.
    """
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

    # Now render each segment
    rows_needed = 2 * amplitude + 1
    mid = amplitude
    canvas = [[" "] * 0 for _ in range(rows_needed)]  # grow as needed
    x_offset = 0

    phase = 0
    for seg_type, seg_width in segments:
        if seg_type == "on":
            wave_rows = _make_sine_wave(seg_width, amplitude, wave_freq, offset=phase)
            for r in range(rows_needed):
                while len(canvas[r]) < x_offset + seg_width:
                    canvas[r].append(" ")
                for c in range(seg_width):
                    canvas[r][x_offset + c] = wave_rows[r][c]
            phase += seg_width
        else:
            # Flat line at the mid
            for c in range(seg_width):
                while len(canvas[mid]) < x_offset + c + 1:
                    canvas[mid].append(" ")
                canvas[mid][x_offset + c] = "─"
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

    return "\n".join(result_rows)


def render_compact_waveform(morse: str, width: int = 70) -> str:
    """Render a compact single-line waveform representation.
    Uses Unicode block elements for a retro oscilloscope look.
    """
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
    output = ""
    line = ""
    for val in signal:
        ch = chars[val]
        line += ch
        if len(line) >= width:
            output += line + "\n"
            line = ""
    if line:
        output += line + "\n"

    # Add Morse annotation below
    morse_line = ""
    count = 0
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
    
    wpm: words per minute (PARIS standard)
    freq: tone frequency in Hz
    volume: volume 0.0-1.0
    """
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

    vol_db = -6 * (1 - volume)  # crude dB mapping

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


# ─── Terminal Animation ──────────────────────────────────────────────────────

def animate_waveform(morse: str, amplitude: int = 2, speed: float = 0.05) -> None:
    """Animate the waveform being drawn in real-time, left-to-right."""
    full = render_waveform(morse, amplitude=amplitude)
    lines = full.split("\n")
    num_lines = len(lines)
    max_width = max(len(l) for l in lines) if lines else 0

    # Clear and set up
    sys.stdout.write("\033[2J\033[H")  # clear screen, home cursor
    sys.stdout.flush()

    # Draw line by line, character by character
    col = 0
    for col in range(max_width):
        for row_idx, line in enumerate(lines):
            if col < len(line):
                sys.stdout.write(f"\033[{row_idx + 1};{col + 1}H{line[col]}")
        sys.stdout.flush()
        if speed > 0:
            time.sleep(speed)

    # Move cursor below the waveform
    sys.stdout.write(f"\033[{num_lines + 1};1H")
    sys.stdout.flush()


# ─── Interactive Mode ─────────────────────────────────────────────────────────

def interactive() -> None:
    """Run an interactive Morse code translator."""
    print("╔══════════════════════════════════════════════════╗")
    print("║        📻  MORSE WAVE TRANSLATOR  📻             ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  Commands:                                       ║")
    print("║    <text>       Encode text → Morse + waveform    ║")
    print("║    d <morse>    Decode Morse → text               ║")
    print("║    w <text>     Show animated waveform           ║")
    print("║    p <text>     Play Morse as audio              ║")
    print("║    c <morse>    Show compact waveform             ║")
    print("║    q            Quit                              ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n73! (Best regards in ham radio 📡)")
            break

        if not raw:
            continue

        if raw.lower() == "q":
            print("73! 📡")
            break

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
                animate_waveform(morse, speed=0.02)
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
            print(render_compact_waveform(morse))
            print()

        else:
            # Default: encode
            text = raw
            morse = text_to_morse(text)
            print(f"  Text:  {text.upper()}")
            print(f"  Morse: {morse}")
            print()
            print(render_waveform(morse))
            print()


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

USAGE = """
Morse Wave Translator — encode/decode text as visual Morse code waveforms

Usage:
  morse_wave.py encode <text>        Encode text to Morse + waveform
  morse_wave.py decode <morse>        Decode Morse to text
  morse_wave.py wave <text>           Show animated waveform
  morse_wave.py play <text>          Play Morse as audio (needs SoX)
  morse_wave.py compact <text>       Show compact block-element waveform
  morse_wave.py interactive          Interactive mode
  morse_wave.py --help               Show this help

Morse format: dots and dashes separated by spaces, letters by double spaces,
              words by ' / '.
  Example: "... --- ..."  =  SOS
"""


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(USAGE)
        return

    cmd = args[0].lower()

    if cmd == "encode":
        if len(args) < 2:
            print("Usage: morse_wave.py encode <text>")
            return
        text = " ".join(args[1:])
        morse = text_to_morse(text)
        print(f"Text:  {text.upper()}")
        print(f"Morse: {morse}")
        print()
        print(render_waveform(morse))

    elif cmd == "decode":
        if len(args) < 2:
            print("Usage: morse_wave.py decode <morse>")
            return
        morse = " ".join(args[1:])
        text = morse_to_text(morse)
        print(f"Morse: {morse}")
        print(f"Text:  {text}")

    elif cmd == "wave":
        if len(args) < 2:
            print("Usage: morse_wave.py wave <text>")
            return
        text = " ".join(args[1:])
        morse = text_to_morse(text)
        print(f"Text:  {text.upper()}")
        print(f"Morse: {morse}")
        print()
        try:
            animate_waveform(morse, speed=0.02)
        except KeyboardInterrupt:
            print("\nInterrupted.")

    elif cmd == "play":
        if len(args) < 2:
            print("Usage: morse_wave.py play <text>")
            return
        text = " ".join(args[1:])
        morse = text_to_morse(text)
        print(f"Text:  {text.upper()}")
        print(f"Morse: {morse}")
        print("Playing... (Ctrl+C to stop)")
        try:
            play_morse(morse)
        except KeyboardInterrupt:
            pass
        print("Done.")

    elif cmd == "compact":
        if len(args) < 2:
            print("Usage: morse_wave.py compact <text>")
            return
        text = " ".join(args[1:])
        morse = text_to_morse(text)
        print(f"Text:  {text.upper()}")
        print(f"Morse: {morse}")
        print()
        print(render_compact_waveform(morse))

    elif cmd == "interactive":
        interactive()

    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)


if __name__ == "__main__":
    main()