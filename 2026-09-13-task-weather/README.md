# Task Weather

Task Weather is a dependency-free Python CLI that reads a Markdown checklist and turns unfinished work into a small workload forecast. It is suitable for a terminal check, a README dashboard, or a script consuming JSON. The input is read-only and is never sent over the network.

## Features

- Parses indented `- [ ]`, `* [ ]`, and `+ [ ]` task lines.
- Recognizes completed tasks with `[x]` or `[X]`.
- Derives priority from up to three exclamation marks.
- Extracts valid ISO due dates and `#tags`; impossible calendar dates are ignored.
- Scores open work by status, priority, and due-date urgency.
- Maps pressure to clear skies, mostly clear, scattered clouds, heavy rain, or thunderstorm.
- Renders a compact Unicode dashboard with per-task pressure bars.
- Emits JSON containing tasks, scores, totals, and open-task tag counts.
- Supports deterministic scoring with `--as-of` and filtering with `--open-only`.
- Removes terminal control characters from titles before display, preventing checklist content from issuing terminal control sequences.
- Handles missing, unreadable, and invalid UTF-8 input files with a CLI error instead of a traceback.
- Provides `--help` and `--version`.

## Requirements

- Python 3.8 or newer
- No third-party runtime dependency
- `pytest` is needed only to run the test suite

## Installation

There is nothing to install. Clone or copy the project, then run it directly:

```bash
cd 2026-09-13-task-weather
python3 task_weather.py --help
```

Or make it executable:

```bash
chmod +x task_weather.py
./task_weather.py todo.md
```

## Input format

```markdown
# Launch checklist

- [ ] Fix the leaking pipe!!! 2026-09-14 #home
- [x] Buy a wrench
* [ ] Write notes #planning
+ [ ] Ship release due: 2026-09-20 #release
```

Dates must use `YYYY-MM-DD`. Only valid calendar dates are retained. Each open task starts with two pressure points. Each `!` contributes two points, capped at three marks. A due date adds five points when overdue, three when due today or tomorrow, one when due within three days, and zero otherwise. Completed tasks do not contribute to total pressure.

## Usage

Read a Markdown file:

```bash
python3 task_weather.py todo.md
```

Read from standard input:

```bash
printf '%s\n' '- [ ] Fix the leaking pipe!!! 2026-09-14 #home' '- [x] Buy a wrench' \
  | python3 task_weather.py
```

Show only unfinished tasks while retaining full forecast totals:

```bash
python3 task_weather.py todo.md --open-only
```

Pin date-sensitive scoring for repeatable output:

```bash
python3 task_weather.py todo.md --as-of 2026-09-13
```

Produce machine-readable output:

```bash
python3 task_weather.py todo.md --json --as-of 2026-09-13
```

Use a narrower dashboard or inspect the version:

```bash
python3 task_weather.py todo.md --width 44
python3 task_weather.py --version
```

The `--width` value is clamped to a usable minimum of 36 columns. `--open-only` affects displayed tasks only; the forecast still describes all parsed tasks.

## Forecast levels

| Pressure | Condition |
| ---: | --- |
| 0 open tasks | clear skies |
| 1–4 | mostly clear |
| 5–9 | scattered clouds |
| 10–17 | heavy rain |
| 18+ | thunderstorm |

## Tests

From this directory:

```bash
python3 -m pytest -q
```

The tests cover parsing, date validation, pinned-date scoring, rendering, and terminal-control-character handling.

## Changelog

### 1.1.1

- Removed C0/C1 control characters from parsed titles so rendered task text cannot alter terminal state.
- Converted invalid UTF-8 file errors into normal argparse errors.
- Added regression coverage for unsafe control characters.

### 1.1.0

- Added reproducible `--as-of` scoring, `--open-only`, `--version`, and open-task tag counts.
- Added impossible-date validation and expanded tests.
