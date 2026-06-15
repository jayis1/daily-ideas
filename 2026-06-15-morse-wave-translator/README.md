# 📻 Morse Wave Translator

Encode and decode text as **visual Morse code waveforms** — dots and dashes rendered as animated ASCII sine waves, compact block-element oscilloscope traces, and optional real audio tones. Features full prosign support, transmission statistics, color output, and file I/O.

## ✨ Features

- **Encode** any text to Morse code with visual sine-wave waveform output
- **Decode** Morse code strings back to plain text
- **Compact mode** — retro oscilloscope-style rendering using Unicode block elements (░▒▓█)
- **Full waveform mode** — multi-row sine wave traces with ╱╲─ connectors
- **Animated mode** — watch the waveform being drawn in real-time, left-to-right
- **Audio playback** — plays actual tones via SoX (optional), with proper PARIS-standard timing
- **Transmission statistics** — dot/dash counts, timing breakdown, WPM calculations
- **Prosign support** — ham radio procedural signals like `<AR>`, `<SK>`, `<BK>`, `<CQ>`
- **Color output** — `--color` flag for ANSI-colored waveforms and stats
- **File I/O** — read input from files (`--file`), write output to files (`--output`), pipe-friendly stdin
- **Interactive mode** — REPL for encoding, decoding, visualizing, and playing
- **Configurable** — adjustable amplitude, WPM, frequency, volume, display width
- **Proper CLI** — argparse-based with `--help`, `--version`, subcommands, and flags
- **Complete Morse alphabet** — A-Z, 0-9, and 30+ punctuation marks
- **Zero dependencies** — pure Python 3, no pip installs needed
- **54 passing tests** — comprehensive pytest suite covering encoding, decoding, waveforms, stats, I/O, and edge cases

## 📦 Installation

No installation needed beyond Python 3.8+:

```bash
# Just clone and run
git clone <repo-url>
cd 2026-06-15-morse-wave-translator
python3 morse_wave.py --help
```

### Optional: Audio Support

For real audio playback, install [SoX](http://sox.sourceforge.net/):

```bash
# Debian/Ubuntu
sudo apt install sox

# macOS
brew install sox
```

Without SoX, the `play` command falls back to visual-only output.

### Optional: Run Tests

```bash
pip install pytest   # if not already installed
pytest test_morse_wave.py -v
```

## 🚀 How to Run

```bash
python3 morse_wave.py <command> [options] [arguments]
```

### Commands

| Command | Description |
|---|---|
| `encode` | Encode text to Morse + waveform |
| `decode` | Decode Morse to text |
| `wave` | Show animated waveform |
| `play` | Play Morse as audio (needs SoX) |
| `compact` | Show compact block-element waveform |
| `stats` | Show transmission statistics |
| `interactive` | Interactive REPL mode |

### Global Options

| Option | Description |
|---|---|
| `--help`, `-h` | Show help message |
| `--version` | Show version number |

## 📖 Usage Examples

### Encode text to Morse + waveform

```bash
$ python3 morse_wave.py encode "HELLO WORLD"
Text:  HELLO WORLD
Morse: .... . .-.. .-.. --- / .-- --- .-. .-.. -..

  ────      ────      ────            ────╲   ...
─╱    ─────╱    ─────╱    ───────────╱     ── ...
```

With color and custom amplitude:
```bash
$ python3 morse_wave.py encode "SOS" --color --amplitude 3
```

### Decode Morse to text

```bash
$ python3 morse_wave.py decode ".... . .-.. .-.. --- / .-- --- .-. .-.. -.."
Morse: .... . .-.. .-.. --- / .-- --- .-. .-.. -..
Text:  HELLO WORLD
```

### Compact oscilloscope-style waveform

```bash
$ python3 morse_wave.py compact "SOS"
Text:  SOS
Morse: ... --- ...

░░ ░░ ░░  ▒▒▒▒▒▒ ▒▒▒▒▒▒ ▒▒▒▒▒▒  ░░ ░░ ░░

. . .  - - -  . . .
```

Block heights represent signal intensity: ░ (gap), ▒ (dot), ▓/█ (dash). With `--color`, gaps appear dim, dots in green, dashes in yellow.

### Transmission statistics

```bash
$ python3 morse_wave.py stats "HELLO WORLD"
Text:  HELLO WORLD
Morse: .... . .-.. .-.. --- / .-- --- .-. .-.. -..

╔══════════════════════════════════════════╗
║        📊  Transmission Statistics       ║
╠══════════════════════════════════════════╣
║  Characters:        10   ( Morse symbols )   ║
║  Words:              2                        ║
║  Dots (·):          19                        ║
║  Dashes (−):        13                        ║
║  Symbol gaps:       22                        ║
║  Letter gaps:        8                        ║
║  Word gaps:          1                        ║
╠══════════════════════════════════════════╣
║  Speed:           15.0  WPM                  ║
║  Unit length:    80.00  ms                  ║
║  Dot time:      1520.0  ms                  ║
║  Dash time:     3120.0  ms                  ║
║  Total time:    8880.0  ms (8.88s)          ║
╚══════════════════════════════════════════╝
```

Custom WPM for timing calculations:
```bash
$ python3 morse_wave.py stats "SOS" --wpm 25
```

### Animated waveform

```bash
$ python3 morse_wave.py wave "CQ CQ DE W1AW"
```

Draws the sine-wave waveform character by character in real-time — press Ctrl+C to interrupt.

### Audio playback

```bash
$ python3 morse_wave.py play "SOS"
Text:  SOS
Morse: ... --- ...
Speed: 15 WPM, Frequency: 700 Hz
Playing...
Done.
```

Custom speed and frequency:
```bash
$ python3 morse_wave.py play "CQ CQ" --wpm 20 --freq 800 --volume 0.3
```

### File input/output

```bash
# Read text from a file
$ python3 morse_wave.py encode --file message.txt

# Save output to a file
$ python3 morse_wave.py encode "HELLO" --output output.txt

# Pipe input
$ echo "SOS" | python3 morse_wave.py decode "$(python3 morse_wave.py encode 'SOS' | grep 'Morse:' | cut -d' ' -f2-)"
```

### Prosigns (ham radio procedural signals)

```bash
$ python3 morse_wave.py encode "<AR> END OF MESSAGE"
$ python3 morse_wave.py encode "CQ CQ DE W1AW <SK>"
```

Supported prosigns: `<AA>`, `<AR>`, `<AS>`, `<BK>`, `<BT>`, `<CL>`, `<CQ>`, `<KN>`, `<SK>`, `<SN>`.

### Interactive mode

```bash
$ python3 morse_wave.py interactive
╔══════════════════════════════════════════════════╗
║        📻  MORSE WAVE TRANSLATOR  📻             ║
╠══════════════════════════════════════════════════╣
║  Commands:                                       ║
║    <text>       Encode text → Morse + waveform    ║
║    d <morse>    Decode Morse → text               ║
║    w <text>     Show animated waveform           ║
║    p <text>     Play Morse as audio              ║
║    c <text>     Show compact waveform             ║
║    s <text>     Show transmission statistics       ║
║    h            Show help                         ║
║    q            Quit                              ║
╚══════════════════════════════════════════════════╝

> HELLO
  Text:  HELLO
  Morse: .... . .-.. .-.. ---
  [waveform rendered]
```

## 🔧 Morse Code Format

| Element | Representation |
|---|---|
| Dot | `.` |
| Dash | `-` |
| Symbol gap | space between dots/dashes |
| Letter gap | double space between letters |
| Word gap | ` / ` between words |

Example: `... --- ...` = SOS, `.... . .-.. .-.. --- / .-- --- .-. .-.. -..` = HELLO WORLD

## 🏗️ How It Works

1. **Encoding** — Each character is looked up in the ITU standard Morse code table and converted to dots/dashes. Prosigns in angle brackets (`<AR>`, etc.) are recognized and expanded.

2. **Decoding** — Morse sequences are looked up in the reverse table. Prosigns are decoded when their Morse sequence is unique (some overlap with punctuation like `+` = `.-.-.` which is also `<AR>`).

3. **Waveform rendering** — Dots and dashes become "on" segments of varying width in a sine-wave canvas. Gaps between symbols, letters, and words become flat lines. The sine wave is calculated per-pixel with directional connectors (╱ rising, ╲ falling, ─ flat).

4. **Compact rendering** — Signal amplitude is mapped to Unicode block heights: gaps → ░, dots → ▒, dashes → ▓█, creating an oscilloscope-like display.

5. **Statistics** — Element counts and PARIS-standard timing calculations: 1 unit = 1200/WPM ms, dot = 1 unit, dash = 3 units, symbol gap = 1 unit, letter gap = 3 units, word gap = 7 units.

6. **Audio** — SoX generates sine-wave tones at the configured frequency. Timing follows the PARIS standard.

7. **Color** — ANSI escape sequences color the waveform (cyan), compact display (green dots, yellow dashes), and statistics panel when `--color` is passed and the terminal supports it. Respects `NO_COLOR` environment variable.

## 📜 License

MIT