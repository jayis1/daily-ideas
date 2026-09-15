# Assumption Switchboard

Assumption Switchboard is a dependency-free Python CLI for seeing whether a weighted decision is fragile. Give it a small JSON file of options, criterion weights, and scores; it prints the baseline ranking and reports which tested weight changes make a different option win.

## Features

- Weighted, normalized ranking with transparent scores.
- One-at-a-time sensitivity checks for every criterion.
- Helpful validation for missing scores, invalid weights, malformed JSON, ties, and empty options.
- Deterministic output and no network access or data uploads.
- A bundled synthetic travel example and unit tests.

## Requirements

- Python 3.8 or newer.
- No third-party package is required to run the CLI. `pytest` is needed only for the test command.

## Installation

Clone the repository and enter this project directory:

```bash
git clone https://github.com/jayis1/daily-ideas.git
cd daily-ideas/2026-09-15-assumption-switchboard
```

There is no package installation step. The script uses only the Python standard library.

## Run

```bash
python3 assumption_switchboard.py example.json
```

Actual output from the bundled example:

```text
Baseline winner: Night train

Ranking:
  1. Night train          6.60
  2. Road trip            5.90
  3. Budget flight        4.90

Winner changes when one weight is adjusted:
  cost: x0.25 -> Road trip
  cost: x0.5 -> Road trip
  comfort: x4 -> Road trip
  adventure: x2 -> Road trip
  adventure: x4 -> Road trip
Tested 12 one-criterion adjustments; this is not a guarantee outside them.
```

Use `--help` for command-line help. Invalid files produce an actionable error and exit with status 2.

## Input format

Each criterion has a non-negative weight. Every option must provide a numeric score for every criterion:

```json
{
  "criteria": {"speed": 4, "price": 2},
  "options": [
    {"name": "Fast", "scores": {"speed": 10, "price": 3}},
    {"name": "Cheap", "scores": {"speed": 6, "price": 10}}
  ]
}
```

Scores can use any consistent scale. The tool divides each weighted total by the sum of weights, so multiplying every weight by the same number does not change the ranking.

## What it does

The baseline winner is computed from the supplied weights. Then each criterion is independently multiplied by 0.25, 0.5, 2, and 4 while the other weights remain unchanged. A reported change means that scenario produced a different winner. This is a bounded sensitivity check, not a prediction or a guarantee of decision quality.

## Tests

From this directory, install `pytest` if it is not already available and run:

```bash
python3 -m pytest -q
```

## Limitations and privacy

The report tests only four fixed multipliers and does not search every possible weighting. It does not know whether scores are fair or accurate. Input is read locally and never sent anywhere; use synthetic data in shared repositories.

## License

This project is authored by jayis1 and inherits the licensing terms of the parent repository.
