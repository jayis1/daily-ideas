# 📻 Morse Wave Translator

Encode and decode text as **visual Morse code waveforms** — dots and dashes rendered as animated ASCII sine waves and compact block-element oscilloscope traces. Optionally plays real audio beeps via SoX.

## ✨ Features

- **Encode** any text to Morse code with visual sine-wave waveform output
- **Decode** Morse code strings back to plain text
- **Compact mode** — retro oscilloscope-style rendering using Unicode block elements (░▒▓█)
- **Full waveform mode** — multi-row sine wave traces with ╱╲─ connectors
- **Animated mode** — watch the waveform being drawn in real-time, left-to-right
- **Audio playback** — plays actual tones via SoX (optional), with proper PARIS-standard timing
- **Interactive mode** — REPL for encoding, decoding, visualizing, and playing
- **Complete Morse alphabet** — A-Z, 0-9, and 30+ punctuation marks
- **Zero dependencies** — pure Python 3, no pip installs needed

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

## 🚀 How to Run

```bash
python3 morse_wave.py <command> [arguments]
```

## 📖 Usage Examples

### Encode text to Morse + waveform

```bash
$ python3 morse_wave.py encode "HELLO WORLD"
Text:  HELLO WORLD
Morse: .... . .-.. .-.. --- / .-- --- .-. .-.. -..

  ────      ────      ────            ────╲   ...
─╱    ─────╱    ─────╱    ───────────╱     ── ...
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

Block heights represent signal intensity: ░ (gap), ▒ (dot), ▓/█ (dash).

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
Playing...
Done.
```

Uses 700 Hz tones at 15 WPM by default.

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

1. **Encoding** — Each character is looked up in the ITU standard Morse code table and converted to dots/dashes.

2. **Waveform rendering** — Dots and dashes become "on" segments of varying width in a sine-wave canvas. Gaps between symbols, letters, and words become flat lines. The sine wave is calculated per-pixel with directional connectors (╱ rising, ╲ falling, ─ flat).

3. **Compact rendering** — Signal amplitude is mapped to Unicode block heights: gaps → ░, dots → ▒, dashes → ▓█, creating an oscilloscope-like display.

4. **Audio** — SoX generates sine-wave tones at 700 Hz. Timing follows the PARIS standard (1 unit = 1200/WPM ms): dot = 1 unit, dash = 3 units, symbol gap = 1 unit, letter gap = 3 units, word gap = 7 units.

## 📜 License

MIT