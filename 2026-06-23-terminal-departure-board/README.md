# ✈ Terminal Departure Board

A real-time animated **flip-board style airport departure/arrival display** (FIDS) running entirely in the terminal. Watch flights get procedurally generated, scheduled, delayed, cancelled, and gate-changed — with the satisfying mechanical character-cycling animation effect that makes airport departure boards so mesmerizing.

![Terminal](https://img.shields.io/badge/terminal-yes-green) ![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![Version](https://img.shields.io/badge/version-1.1.0-orange) ![License](https://img.shields.io/badge/license-MIT-green) ![Tests](https://img.shields.io/badge/tests-41%20passing-brightgreen)

## Features

### Core Display
- **Authentic flip-board character cycling animation** — characters sweep through the alphabet/digits before settling on the target letter, just like real mechanical departure boards
- **Procedural flight generation** — 20 airlines, 30 destinations, realistic flight numbers, gates, and terminals
- **Live status evolution** — flights progress through ON TIME → GATE OPEN → BOARDING → FINAL CALL → DEPARTED, with random DELAYED, GATE CHANGE, and CANCELLED events
- **Color-coded status rows** — green (on time), yellow (boarding/delayed), red (cancelled/final call), cyan (gate change)
- **Blinking announcements** for final call and cancelled flights
- **Real-time simulation clock** that advances faster than wall time
- **Random airport announcements** — rotating helpful messages add immersion

### New in v1.1.0
- **Arrivals board mode** (`--arrivals`) — show incoming flights with EXPECTED → LANDED → ARRIVED lifecycle, belt numbers instead of gates, and arrival-specific announcements
- **Flight search** (`--flight BA117`) — look up a specific flight by flight number
- **Weather display** — random weather conditions shown in the board header (temperature, wind, visibility)
- **`--version` flag** — show program version
- **Improved state machine** — flight tick logic refactored into separate departure/arrival methods for cleaner code and better extensibility
- **Comprehensive test suite** — 41 unit tests covering Flight creation, state transitions, FlipBoard animation, board rendering, arrivals mode, static output, edge cases, and more

### Display Options
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

### Live Animated Departure Board (default)

```bash
python3 departure_board.py
```

This starts an interactive, full-screen animated departure board. The simulated clock advances ~2 minutes per tick. Flights change status over time — boarding calls appear, delays happen, gates change. Press **Ctrl+C** to exit.

### Live Arrivals Board

```bash
python3 departure_board.py --arrivals
```

Shows arriving flights with EXPECTED/LANDED/ARRIVED statuses and baggage belt numbers instead of gates.

### Options

| Flag | Description |
|------|-------------|
| `--arrivals` | Show arrivals board instead of departures |
| `--compact` | Show 8 flights instead of 14 |
| `--fast` | 2× speed for animation and time progression |
| `--slow` | 0.5× speed for a more relaxed view |
| `--no-animate` | Disable flip animation (instant updates) |
| `--no-color` | Strip all ANSI color codes |
| `--filter CODE` | Show only flights for a specific airline (e.g., `BA`, `UA`, `EK`) |
| `--destination CITY` | Show only flights to a city (e.g., `Tokyo`, `London`) |
| `--flight FLIGHT_NO` | Search for a specific flight number (e.g., `BA117`) |
| `--flights N` | Display N flights (default 14) |
| `--static` | Print a single snapshot and exit (for pipes/scripts) |
| `--demo` | Run just the flip animation demo |
| `--version` | Show version number |
| `--help` | Show full help message |

### Usage Examples

**Watch only British Airways flights:**
```bash
python3 departure_board.py --filter BA
```

**Show arrivals board:**
```bash
python3 departure_board.py --arrivals
```

**Search for a specific flight:**
```bash
python3 departure_board.py --flight BA117
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

**Arrivals board, static, no color:**
```bash
python3 departure_board.py --arrivals --static --no-color
```

**Just the flip animation demo:**
```bash
python3 departure_board.py --demo
```

**Pipe to a file (auto-disables color):**
```bash
python3 departure_board.py --static > board.txt
```

## Running Tests

```bash
python3 -m pytest test_departure_board.py -v
```

41 tests cover:
- Flight creation and attribute validation
- Departure and arrival state machine transitions
- FlipBoard animation engine (distances, frames, edge cases)
- DepartureBoard rendering and formatting
- Arrivals mode (column layout, belt numbers, status lifecycle)
- Static board output (departures, arrivals, filters)
- Version and metadata
- Edge cases (impossible filters, gate/terminal validation)

## How It Works

### Flight Lifecycle (Departures)

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

### Flight Lifecycle (Arrivals)

Arrival flights follow a different progression:

1. **EXPECTED** — flight is on its way
2. **LANDED** — flight has touched down
3. **ARRIVED** — at the gate, baggage on belt

Random events:
- **DELAYED** — arrival time pushed back
- **DIVERTED** — flight rerouted to another airport (rare)

### Flip Animation

The character cycling effect mimics real mechanical split-flap displays. Each character in a row transitions from its current letter to the target letter by sweeping through the character set (`ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-/.`). Characters that don't need to change stay fixed while their neighbors cycle, creating the signature "wave" effect.

### Weather Simulation

Random weather conditions are generated for the board header, including temperature, wind speed, and visibility. Weather updates periodically during the live board simulation.

### Procedural Generation

- **Airlines**: 20 real-world airline codes and names (BA, AA, UA, DL, LH, AF, EK, SQ, QF, JL, CX, TK, NH, SK, IB, KL, ET, QR, EY, VS)
- **Destinations**: 30 major airports worldwide with IATA codes
- **Gates**: A1–F15 across 5 terminals
- **Flight numbers**: Airline code + random 3-4 digit number
- **Baggage belts**: B1–B12 (arrivals mode)

## License

MIT