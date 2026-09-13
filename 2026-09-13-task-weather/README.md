# Task Weather

Task Weather is a dependency-free Python CLI that turns a Markdown checklist into a tiny workload forecast. It reads ordinary `- [ ]` and `- [x]` task lines, estimates pressure from unfinished work, urgency, and `!` priority marks, then renders a weather report in the terminal.

It is deliberately playful, but the parser and JSON output make it useful in scripts, pre-commit dashboards, or a personal README. No network access, configuration file, or third-party package is required.

## Features

- Parses Markdown checklists without changing the source file.
- Recognizes completed tasks, up to three `!` priority marks, ISO due dates, and `#tags`.
- Produces a deterministic forecast based on open-task pressure:
  - clear skies: no open tasks
  - mostly clear: light workload
  - scattered clouds: moderate workload
  - heavy rain: substantial workload
  - thunderstorm: urgent or overdue workload
- Displays a compact Unicode terminal dashboard with per-task pressure bars.
- Supports `--json` for automation and `--width` for narrow terminals.
- Includes tests for parsing, scoring, forecasting, and rendering.

## Requirements

- Python 3.8 or newer
- A terminal with UTF-8 support for the weather icons and box drawing (the JSON mode works everywhere)

## Installation

No package installation is needed. Copy or clone this directory and run the script with Python:

```bash
cd 2026-09-13-task-weather
python3 task_weather.py --help
```

To use it from anywhere, make the script executable and put the directory on your `PATH`:

```bash
chmod +x task_weather.py
./task_weather.py todo.md
```

## How to run

Read a Markdown file:

```bash
python3 task_weather.py todo.md
```

Or pipe a checklist through standard input:

```bash
printf '%s\n' '- [ ] Fix the leaking pipe!!! 2026-09-14 #home' '- [x] Buy a wrench' \
  | python3 task_weather.py
```

Use JSON when another program needs the result:

```bash
python3 task_weather.py todo.md --json
```

Adjust the dashboard width for a small terminal:

```bash
python3 task_weather.py todo.md --width 44
```

Run the test suite from this directory:

```bash
python3 -m unittest discover -v
```

Pytest also works if it is installed:

```bash
pytest -q
```

## Input format

Any line matching this shape is treated as a task:

```markdown
- [ ] Open task
- [x] Completed task
* [ ] High priority!!! 2026-09-20 #release
+ [ ] Another task due: 2026-09-13
```

Dates must use `YYYY-MM-DD`. A task's pressure is calculated only while it is open. Each `!` contributes priority, open tasks receive a base cost, and due dates add urgency when they are overdue or within three days. Other Markdown content is ignored.

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

The exact pressure and condition depend on today's date when due dates are present. The tool never sends task contents anywhere and never edits the input file.
