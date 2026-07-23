# Terminal Cuckoo Clock Simulator

A self-contained, zero-dependency ASCII-art cuckoo clock for your terminal. It
keeps real time (or any speed you choose) and puts on a little show: a wooden
case with a peaked roof, a dial with hour/minute/second hands, two interlocking
gears that turn at meshed speeds, a swinging pendulum, Westminster quarter
chimes played **note-by-note**, and a cuckoo bird that pops out of its little
door and cuckoos once for each hour.

Optional curses color brings the case, dial, hands, gears, bird, pendulum, and
chime indicator to life — and the display degrades gracefully to plain ASCII on
terminals without color support.

Pure Python 3 standard library — only `curses`, `math`, `time`, `argparse`,
and `dataclasses`. Nothing to install.

```
                 ▲
                ╱^╲
        ╔══════════════════════════════════════════╗
        ║          · CUCKOO ·                       ║
        ║         ___                              ║
        ║        / o \                             ║
        ║       | \_/ |                            ║
        ║        \___/     •••                     ║
        ║          vvv    • 12 •                   ║
        ║        •• 1   ▌   3 ••                   ║
        ║        • 1    ✚    4 •                   ║
        ║        •• 9 5 ••                          ║
        ║        •• 8     6 ● •                    ║
        ║          •• 7 ••                         ║
        ║   #  ##· ·+· #        ## #|# · ·+·|#|    ║
        ║        ····+·#···       |                 ║
        ║  ##···O·· ##+···O···    |                 ║
        ╚═══#══·····══════════════#═+······+═══════╝
            ##  #|# · ·+·|#|        |
                |                    |
                |                    |
               (===)                 |
                                    (===)
        ⏰  12:00:00    (top of hour)
        🐦 CUCKOO!  (12 left)
```

## Features

### Visual
- **Live dial** with smoothly drawn hour, minute, and second hands driven from
  the simulated clock.
- **Interlocking gears** — two spur gears rendered procedurally with a
  tooth-modulated radius; the escape wheel and great wheel turn in opposite
  directions because they're meshed.
- **Swinging pendulum** — a damped harmonic swing (`sin(t·π)·0.35`, a 1 Hz swing
  with ~20° amplitude) that traces a tilted rod and bob below the case.
- **Wooden case** with box-drawing characters, a peaked roof apex, and a
  "· CUCKOO ·" plaque.
- **Curses color** (when the terminal supports it): yellow case, cyan dial,
  white hands, red bird, green gears, magenta pendulum, blue log, and a yellow
  chime indicator. Falls back to plain ASCII automatically.

### Sound & animation
- **Westminster quarter chimes** — at :15, :30, and :45 the clock plays the
  Westminster motif **note-by-note**, spacing the terminal-bell taps at
  note-appropriate intervals (lower notes ring longer). The current note and
  progress (`🔔 Chime: E4  (2/7)`) is shown live in the status line.
- **Hourly cuckoo strike** — on the top of the hour the cuckoo door swings
  open, the bird emerges with an alternating open/closed beak animation, and
  cuckoos once for each hour (1–12). Each cuckoo sounds the terminal bell.
- **Bell (`\a`)** is used for all chimes; the bell character works in most Unix
  terminals.

### Interaction & options
- **`--warp SPEED`** — accelerate the clock by any factor so you can watch a
  whole day in a minute. `1` = real-time, `3600` = one hour per second.
- **`--once`** — fast-forwards to the next top of the hour, fires a single
  strike, and exits. Handy for smoke-testing or a one-shot cuckoo in a shell
  prompt.
- **`--start HH:MM:SS`** — begin the clock at a custom time (e.g. `11:00` or
  `23:59:30`). Useful for demoing a specific strike count.
- **`--silent`** — suppress the terminal bell. Chime motifs are still sequenced
  and logged in the side panel, so you can see what would have played.
- **`--version` / `--help`** — standard flags.

### In-program keys

| Key | Action |
|-----|--------|
| `q` / `Esc` | Quit |
| `Space` | Fire the cuckoo manually (cuckoos once per current hour) |
| `h` | Toggle 12-hour / 24-hour digital readout |
| `c` | Manually trigger the current quarter chime (15/30/45) |

## Install

No install needed beyond Python 3.9+:

```bash
git clone https://github.com/<you>/daily-ideas.git
cd daily-ideas/2026-07-23-terminal-cuckoo-clock
python3 cuckoo_clock.py
```

That's it. The project only uses the standard library (`curses`, `math`,
`time`, `argparse`, `dataclasses`).

## How to run

```bash
# Real time, with bell chimes (default)
python3 cuckoo_clock.py

# 60× speed — see a quarter chime every 15 seconds
python3 cuckoo_clock.py --warp 60

# 3600× speed — a full hour every second (great for demoing strikes)
python3 cuckoo_clock.py --warp 3600 --silent

# Start at a specific time and run in real time
python3 cuckoo_clock.py --start 11:00:00

# Start at 23:59 and warp so you can watch the midnight 12-cuckoo strike
python3 cuckoo_clock.py --start 23:59 --warp 60 --silent

# One-shot: jump to the next top of the hour, cuckoo, and exit
python3 cuckoo_clock.py --once

# No bell at all (chime motifs still logged in the side panel)
python3 cuckoo_clock.py --silent

# Show the version
python3 cuckoo_clock.py --version
```

### Quick demo

```bash
# Start 5 seconds before noon, warp 60×, watch the 12-cuckoo strike
python3 cuckoo_clock.py --start 11:59:55 --warp 60 --silent
```

## Usage examples

```bash
# Let it run on a second monitor at real speed
python3 cuckoo_clock.py

# Demo for a screenshot — warp to the next hour strike, then exit
python3 cuckoo_clock.py --once --silent

# Test all the chimes in 30 seconds
python3 cuckoo_clock.py --warp 4800 --silent

# Run as a one-shot cuckoo at the top of every hour (cron-style)
0 * * * * python3 /path/to/cuckoo_clock.py --once
```

## What it does

1. Seeds its simulated clock from the system wall clock at startup (or from
   `--start`), so the dial and readout match your chosen time.
2. Each frame advances the simulation by `dt * warp` seconds, so `--warp 1` is
   real-time and `--warp 3600` is one hour per second.
3. The pendulum angle is `sin(t·π)·0.35` — a 1 Hz swing with ~20° amplitude.
4. The two gears rotate at fixed rates (escape wheel faster than the great
   wheel) and in opposite directions to look meshed.
5. Whenever the simulated minute crosses a 15-minute boundary, the
   corresponding Westminster motif is started on the chime sequencer. The
   sequencer plays each note in turn, spacing bell taps by the note's
   pitch-derived duration, and logs the motif in the side panel.
6. On the top of the hour the cuckoo door opens and the bird alternates an
   open-beak and closed-beak glyph once for each strike count
   (1 at 1:00/13:00, …, 12 at noon/midnight).
7. A side panel keeps a scrolling log of chimes and cuckoos so you can see the
   history of what the clock has done.

## Testing

Pure-logic unit tests (no curses required) cover the time math, gear
rendering, overlay clipping, cuckoo state machine, chime sequencer,
note-interval timing, time formatting, and `--start` parsing:

```bash
python3 -m pytest test_cuckoo_clock.py        # via pytest
python3 test_cuckoo_clock.py                  # standalone runner
```

## Files

- `cuckoo_clock.py` — the simulator (single file, stdlib only).
- `test_cuckoo_clock.py` — pure-logic unit tests (21 tests).

## Notes

- Requires a terminal at least 60×24 for the clock to render; smaller terminals
  show a "Terminal too small" message instead of garbling.
- The bell (`\a`) works in most Unix terminals but may be silent or visual-only
  in some — use `--silent` if it's bothersome or unsupported.
- `--once` jumps to `ceil(now/3600)*3600`, so if you start it at 10:37 it will
  cuckoo 11 times (for 11:00) and exit.
- `--start` accepts `HH:MM` or `HH:MM:SS`; out-of-range values are rejected
  with a clear error before the clock starts.
- Color is enabled automatically when the terminal advertises color support;
  no flag is needed.