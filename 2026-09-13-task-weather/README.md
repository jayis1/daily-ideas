# Task Weather

Task Weather is a dependency-free Python command-line tool that reads a Markdown checklist and turns the unfinished work into a small weather forecast. It is useful for a quick terminal check, a README dashboard, or a script that needs structured task data. It never edits the input file or sends its contents over the network.

## Features

- Parses `- [ ]`, `* [ ]`, and `+ [ ]` Markdown task lines, including indented lists.
- Recognizes completed tasks (`[x]` or `[X]`), up to three `!` priority marks, ISO dates, and `#tags`.
- Rejects impossible calendar dates instead of reporting them as due dates.
- Scores open work from task status, priority, and due-date urgency.
- Maps total pressure to five conditions: clear skies, mostly clear, scattered clouds, heavy rain, or thunderstorm.
- Renders a compact Unicode dashboard with per-task pressure bars.
- Provides JSON output with task scores, totals, and counts of open tasks by tag.
- Supports reproducible date evaluation with `--as-of`.
- Can hide completed tasks with `--open-only`.
- Includes `--help` and `--version` flags.
- Has tests covering parsing, date validation, scoring, forecasting, and rendering.

## Requirements

- Python 3.8 or newer
- No third-party runtime dependencies
- UTF-8 terminal for the icons and box drawing (use `--json` in other environments)

## Installation

Clone or copy this directory. There is nothing to install:

```bash
cd 2026-09-13-task-weather
python3 task_weather.py --help
```

For direct execution:

```bash
chmod +x task_weather.py
./task_weather.py todo.md
```

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

Show only unfinished tasks, while retaining the full forecast totals:

```bash
python3 task_weather.py todo.md --open-only
```

Pin date-sensitive scoring for a repeatable report:

```bash
python3 task_weather.py todo.md --as-of 2026-09-13
```

Use JSON in another program:

```bash
python3 task_weather.py todo.md --json --as-of 2026-09-13
```

Use a narrower dashboard:

```bash
python3 task_weather.py todo.md --width 44
```

Check the installed script version:

```bash
python3 task_weather.py --version
```

## Input format

```markdown
# Launch checklist

- [ ] Fix the leaking pipe!!! 2026-09-14 #home
- [x] Buy a wrench
* [ ] Write notes #planning
+ [ ] Ship release due: 2026-09-20 #release
```

Dates must use `YYYY-MM-DD`; only valid calendar dates are retained. Each open task starts with two pressure points. Each `!` contributes two points, capped at three exclamation marks. A due date adds five points when overdue, three when due today or tomorrow, and one when due within three days. Completed tasks contribute no total pressure.

## Forecast levels

| Pressure | Condition |
| ---: | --- |
| 0 open tasks | clear skies |
| 1–4 | mostly clear |
| 5–9 | scattered clouds |
| 10–17 | heavy rain |
| 18+ | thunderstorm |

## Example output

```text
┌────────────────────────────────────────────────────────┐
│ TASK WEATHER                                           │
│  🌧  HEAVY RAIN                                        │
│  pressure 12  •  2 open / 3 total                     │
├────────────────────────────────────────────────────────┤
│  • Fix the leaking pipe!!! 2026-09-14 #home            │
│  ████████████  pressure 12                             │
│  ✓ Buy a wrench                                        │
└────────────────────────────────────────────────────────┘
```

The exact score for a due date depends on the evaluation date. The `--as-of` option makes it deterministic for automation and tests.

## Tests

From this directory, run:

```bash
python3 -m pytest -q
```

The suite uses only the standard library and pytest's test discovery conventions; install pytest separately if it is not already available.
