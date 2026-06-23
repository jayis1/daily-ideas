# ✈ Terminal Departure Board

A real-time animated **flip-board style airport departure display** (FIDS) running entirely in the terminal. Watch flights get procedurally generated, scheduled, delayed, cancelled, and gate-changed — with the satisfying mechanical character-cycling animation effect that makes airport departure boards so mesmerizing.

![Terminal](https://img.shields.io/badge/terminal-yes-green) ![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Authentic flip-board character cycling animation** — characters sweep through the alphabet/digits before settling on the target letter, just like real mechanical departure boards
- **Procedural flight generation** — 20 airlines, 30 destinations, realistic flight numbers, gates, and terminals
- **Live status evolution** — flights progress through ON TIME → GATE OPEN → BOARDING → FINAL CALL → DEPARTED, with random DELAYED, GATE CHANGE, and CANCELLED events
- **Color-coded status rows** — green (on time), yellow (boarding/delayed), red (cancelled/final call), cyan (gate change)
- **Blinking announcements** for final call and cancelled flights
- **Real-time simulation clock** that advances faster than wall time
- **Flight filtering** by airline code or destination city
- **Compact mode** for smaller terminals
- **Static snapshot mode** for piped/non-TTY output
- **Flip animation demo** showcasing the character cycling effect

## Installation

No dependencies beyond Python 3.8+ and a standard library:

```bash
git clone https://github.com/youruser/daily-ideas.git
cd daily-ideas/2026-06-23-terminal-departure-board
```

## How to Run

### Live Animated Board (default)

```bash
python3 departure_board.py
```

This starts an interactive, full-screen animated departure board. The simulated clock advances ~2 minutes per tick. Flights will change status over time — boarding calls appear, delays happen, gates change. Press **Ctrl+C** to exit.

### Options

| Flag | Description |
|------|-------------|
| `--compact` | Show 8 flights instead of 14 |
| `--fast` | 2× speed for animation and time progression |
| `--slow` | 0.5× speed for a more relaxed view |
| `--no-animate` | Disable flip animation (instant updates) |
| `--no-color` | Strip all ANSI color codes |
| `--filter CODE` | Show only flights for a specific airline (e.g., `BA`, `UA`, `EK`) |
| `--destination CITY` | Show only flights to a city (e.g., `Tokyo`, `London`) |
| `--flights N` | Display N flights (default 14) |
| `--static` | Print a single snapshot and exit (for pipes/scripts) |
| `--demo` | Run just the flip animation demo |

### Usage Examples

**Watch only British Airways flights:**
```bash
python3 departure_board.py --filter BA
```

**Filter flights to Tokyo:**
```bash
python3 departure_board.py --destination Tokyo
```

**Quick compact view with faster updates:**
```bash
python3 departure_board.py --compact --fast
```

**Static snapshot (works in piped output):**
```bash
python3 departure_board.py --static
```

**Just the flip animation demo:**
```bash
python3 departure_board.py --demo
```

**Pipe to a file (auto-disables color):**
```bash
python3 departure_board.py --static > board.txt
```

## How It Works

### Flight Lifecycle

Each procedurally-generated flight follows a realistic lifecycle based on simulated time:

1. **ON TIME** — flight is scheduled and on schedule
2. **GATE OPEN** — gate has been assigned and opened (~20 min before departure)
3. **BOARDING** — passengers are boarding (~15 min before departure)
4. **FINAL CALL** — last boarding call (~10 min before departure)
5. **DEPARTED** — flight has left

Random events can occur at any stage:
- **DELAYED** — estimated departure time pushed back by 15–120 minutes
- **GATE CHANGE** — reassigned to a different gate
- **CANCELLED** — flight cancelled (highlighted in red)

### Flip Animation

The character cycling effect mimics real mechanical split-flap displays. Each character in a row transitions from its current letter to the target letter by sweeping through the character set (`ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-/.`). Characters that don't need to change stay fixed while their neighbors cycle, creating the signature "wave" effect.

### Procedural Generation

- **Airlines**: 20 real-world airline codes and names (BA, AA, UA, DL, LH, AF, EK, SQ, QF, JL, CX, TK, NH, SK, IB, KL, ET, QR, EY, VS)
- **Destinations**: 30 major airports worldwide with IATA codes
- **Gates**: A1–F15 across 5 terminals
- **Flight numbers**: Airline code + random 3-4 digit number

## License

MIT