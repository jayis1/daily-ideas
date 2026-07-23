# Terminal Cuckoo Clock Simulator

A self-contained ASCII-art cuckoo clock for your terminal. It keeps real
time (or any speed you choose) and puts on a little show: a wooden case with
a peaked roof, a dial with hour/minute/second hands, two interlocking gears
that turn at meshed speeds, a swinging pendulum, Westminster quarter chimes,
and a cuckoo bird that pops out of its little door and cuckoos once for each
hour.

No third-party dependencies — pure Python 3 stdlib (`curses` + `time`).

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

- **Live dial** with smoothly drawn hour, minute, and second hands driven
  from the simulated clock.
- **Westminster quarter chimes** — at :15, :30, and :45 the clock plays a
  short motif using the terminal bell (`\a`); the motif is logged in the
  side panel so you can see it even in silent mode.
- **Hourly cuckoo strike** — on the top of the hour the cuckoo door swings
  open, the bird emerges with an open/closed beak animation, and cuckoos
  once for each hour (1–12). Each cuckoo sounds the terminal bell.
- **Interlocking gears** — two spur gears rendered procedurally with a
  tooth-modulated radius; the escape wheel and great wheel turn in
  opposite directions because they're meshed.
- **Swinging pendulum** — a damped harmonic swing that traces a tilted rod
  and bob below the case.
- **Time-warp mode** — accelerate the clock by any factor so you can watch
  a whole day in a minute. Great for demoing the hourly strike.
- **`--once`** mode — fast-forwards to the next top of the hour, fires a
  single strike, and exits. Handy for smoke-testing or for a one-shot
  cuckoo in a shell prompt.
- **Manual trigger** — press `Space` while running to fire the cuckoo on
  demand.
- **`--silent`** — suppress the terminal bell if your terminal doesn't
  support it or you find it annoying.

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

# One-shot: jump to the next top of the hour, cuckoo, and exit
python3 cuckoo_clock.py --once

# No bell at all (chime motifs still logged in the side panel)
python3 cuckoo_clock.py --silent
```

### In-program keys

| Key | Action |
|-----|--------|
| `q` / `Esc` | Quit |
| `Space` | Fire the cuckoo manually (cuckoos once per current hour) |

## Usage examples

```bash
# Let it run on a second monitor at real speed
python3 cuckoo_clock.py

# Demo for a screenshot — warp to the next hour strike, then exit
python3 cuckoo_clock.py --once --silent

# Test all the chimes in 30 seconds
python3 cuckoo_clock.py --warp 4800 --silent
```

## What it does

1. Seeds its simulated clock from the system wall clock at startup, so the
   dial and readout match your local time.
2. Each frame advances the simulation by `dt * warp` seconds, so `--warp 1`
   is real-time and `--warp 3600` is one hour per second.
3. The pendulum angle is `sin(t·π)·0.35` — a 1 Hz swing with ~20° amplitude.
4. The two gears rotate at fixed rates (escape wheel 8× faster than the
   great wheel) and in opposite directions to look meshed.
5. Whenever the simulated minute crosses a 15-minute boundary, the
   corresponding Westminster motif is logged and a bell is struck.
6. On the top of the hour the cuckoo door opens and the bird alternates an
   open-beak and closed-beak glyph once for each strike count
   (1 at 1:00/13:00, …, 12 at noon/midnight).
7. A side panel keeps a scrolling log of chimes and cuckoos so you can see
   the history of what the clock has done.

## Files

- `cuckoo_clock.py` — the simulator (single file, stdlib only).
- `test_cuckoo_clock.py` — pure-logic unit tests for the time math, gear
  rendering, overlay clipping, and cuckoo state machine. Run with
  `python3 test_cuckoo_clock.py`.

## Notes

- Requires a terminal at least 90×30 for the full clock to render; smaller
  terminals show a "too small" message instead of garbling.
- The bell (`\a`) works in most Unix terminals but may be silent or visual-
  only in some — use `--silent` if it's bothersome or unsupported.
- `--once` jumps to `ceil(now/3600)*3600`, so if you start it at 10:37 it
  will cuckoo 11 times (for 11:00) and exit.