# 📻 ASCII Morse Broadcasting Station

A terminal-based vintage shortwave radio station simulator that broadcasts Morse code in real time. Watch as it cycles through station identifications, news bulletins, weather reports, and occasional emergency alerts — all transmitted in properly-timed International Morse Code with a live radio receiver UI.

## ✨ Features

- **Real-time Morse code transmission** using PARIS-standard timing (1200/WPM milliseconds per dot)
- **Full shortwave receiver UI** with VFO frequency display, S-meter, signal strength bars, and tuning indicator
- **Live waveform visualization** — animated ASCII waveform that responds to signal strength
- **Decoded message readout** — see the Morse symbols and their decoded text in real time
- **Broadcast log** — timestamped log of all transmitted segments
- **Dynamic segment cycling** — station IDs, news headlines, weather reports, emergency alerts, and dead air/static
- **41 vintage news headlines** covering retro topics like steamships, airships, telegraphy, and ticker tape parades
- **16 weather report templates** with temperature, wind, and barometric readings
- **8 emergency alert templates** for dramatic broadcasts
- **20 amateur radio call signs** to choose from
- **NATO phonetic alphabet** support for station IDs
- **Optional audio output** via SoX/play (Linux) or terminal bell
- **WAV file export** — save the first broadcast segment as a `.wav` file with proper sine-wave Morse tones
- **Adjustable WPM speed** (default 20 WPM) and broadcast speed multiplier
- **Static/noise simulation** between segments with fluctuating signal levels
- **Q-codes** (QSL, QTH, QRX, QRM, QSB, CQ, DE, AR, SK) used authentically

## 📦 Installation

### Prerequisites

- Python 3.8+ (no external packages required!)
- A terminal with ANSI color support

### Optional: Audio support (Linux)

```bash
# For audio beeps via SoX:
sudo apt install sox     # Debian/Ubuntu
# or
sudo dnf install sox     # Fedora
```

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/daily-ideas.git
cd daily-ideas/2026-08-19-ascii-morse-broadcasting
```

No `pip install` needed — the project uses only Python standard library modules.

## 🚀 How to Run

```bash
# Default: random call sign, 20 WPM, no audio
python3 main.py

# Custom call sign at 25 WPM
python3 main.py --callsign WBSQ --wpm 25

# Slow broadcast for easy reading (0.5x speed)
python3 main.py -c KXRT -w 15 -s 0.5

# With audio beeps (requires SoX)
python3 main.py --audio

# Save broadcast as WAV file
python3 main.py --wav

# List available call signs
python3 main.py --callsign-list

# Show help
python3 main.py --help
```

**Press `Ctrl+C` to stop broadcasting.**

## 📖 Usage Examples

### Start a broadcast with a specific call sign

```bash
python3 main.py --callsign WNYC --wpm 22 --speed 0.8
```

This starts station WNYC broadcasting at 22 WPM with a slightly slower pace (0.8x speed multiplier), making the Morse code easier to follow for learners.

### Enable audio and save WAV

```bash
python3 main.py -c WCBS --audio --wav
```

Broadcasts station WCBS with audio beeps enabled and saves the first segment as `broadcast.wav` in the project directory. The WAV file contains proper sine-wave Morse code tones at 600 Hz with fade in/out envelopes to prevent clicks.

### Slow Morse for learning

```bash
python3 main.py -c KQED -w 12 -s 0.3
```

Broadcasts at 12 WPM with 0.3x speed — very slow, perfect for learning to copy Morse code by ear or eye.

## 🎛️ What It Does

When you launch the station, it simulates a vintage shortwave radio broadcasting station going through its programming cycle:

1. **Station Identification** — Transmits `CQ CQ CQ DE <callsign> <callsign> <callsign> AR` (calling all stations, this is `<callsign>`)
2. **News Bulletin** — Broadcasts a random vintage news headline (e.g., `MARKETS RALLY AS DOW HITS RECORD HIGH`)
3. **Weather Report** — Transmits weather conditions with `WX` prefix (e.g., `WX CLEAR SKIES PREVAIL TEMPERATURE 72`)
4. **Emergency Alert** (occasionally) — Dramatic urgent messages with `URGENT` prefix
5. **Static / Dead Air** — Simulates radio static with low, fluctuating signal strength
6. **Repeat** — The cycle continues with new random content each time

The receiver UI displays:
- **VFO (Variable Frequency Oscillator)** — Shows the current frequency, mode (CW), and band (SHORTWAVE)
- **S-Meter** — Signal strength meter from S0 to S9+20dB with a live bar graph
- **Morse Transmission** — The raw Morse code symbols (dots and dashes) as they're transmitted
- **Decoded Message** — The human-readable text being decoded from Morse
- **Waveform** — Animated 4-line ASCII waveform that pulses with signal strength
- **Broadcast Log** — Timestamped log of all segments
- **Static Line** — Random noise characters simulating radio static

### Morse Code Timing

The simulator follows the international PARIS standard:
- **Dot** = 1 unit (1200/WPM ms)
- **Dash** = 3 units
- **Intra-character gap** = 1 unit (between dots/dashes within a letter)
- **Inter-character gap** = 3 units (between letters)
- **Inter-word gap** = 7 units (between words)

At 20 WPM, one dot = 60ms. The speed multiplier (`-s`) scales all timings.

## 📁 Project Structure

```
2026-08-19-ascii-morse-broadcasting/
├── main.py          # Complete station simulator (single file, no dependencies)
└── README.md        # This file
```

## 🔧 Technical Details

- **No external dependencies** — Uses only Python standard library (`os`, `sys`, `time`, `random`, `math`, `wave`, `struct`, `argparse`, `threading`, `datetime`)
- **ANSI escape codes** for colors, cursor positioning, and screen clearing
- **WAV generation** uses raw `struct.pack` for 16-bit PCM samples at 8 kHz sample rate
- **Morse code table** includes all 26 letters, 10 digits, and 18 punctuation marks
- **Authentic Q-codes** used in amateur radio: CQ (calling all stations), DE (from), AR (end of message), SK (end of contact), QSL (acknowledge), QRM (interference), QSB (fading), QTH (location), QRX (stand by)

## 📜 License

This project is part of the daily-ideas collection. Free to use and modify.

---

*73, and thanks for listening! 📡*