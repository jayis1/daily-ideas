# Calendar Gap Finder

Calendar Gap Finder is a dependency-free Python CLI that compares compact busy-time lists and prints the windows when everyone is free. Calendar data stays local, and no account, API, or exported calendar file is required.

## Why

Finding a meeting time in a short chat thread should not require copying everyone into a scheduling service. This tool handles the small case directly: describe each person's busy windows, choose a minimum duration, and get the common gaps.

## Requirements

- Python 3.8 or newer
- No third-party packages or network access

## Run

From the repository root:

```bash
cd 2026-09-28-calendar-gap-finder
python3 calendar_gap_finder.py \
  --person 'Ada=09:00-10:00,13:00-14:00' \
  --person 'Grace=10:30-11:30,13:30-15:00' \
  --minutes 45
```

Verified output:

```text
Shared free windows (2 people, 45+ minutes):
- 11:30-13:00 (90 minutes)
- 15:00-17:00 (120 minutes)
```

The default search day is `09:00-17:00`. Set different bounds with `--day`:

```bash
python3 calendar_gap_finder.py \
  --day 08:00-12:00 \
  --person 'Ada=08:30-09:00' \
  --person 'Grace=' \
  --minutes 30
```

Use `--json` for scripts or `--help` for every option:

```bash
python3 calendar_gap_finder.py --person 'Ada=10:00-11:00' --json
python3 calendar_gap_finder.py --help
```

## Input rules

- Repeat `--person` once per participant using `NAME=WINDOWS`.
- Separate a person's busy windows with commas.
- Use strict 24-hour `HH:MM-HH:MM` times; overnight windows are not supported.
- Use an empty schedule such as `Grace=` for someone free all day.
- Busy windows are clipped to the selected day, then overlapping and adjacent windows are merged.
- Duplicate participant names, backward windows, and non-positive minimum durations are rejected.

## Tests

Run the focused suite from this directory:

```bash
python3 -m unittest -v
```

The tests cover strict time parsing, formatting, schedule parsing, clipping and merging, common-gap calculation, minimum durations, text and JSON output, empty schedules, and no-match behavior.
