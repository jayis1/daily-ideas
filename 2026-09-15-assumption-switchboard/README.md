# Assumption Switchboard

Assumption Switchboard is a dependency-free Python CLI for checking whether a weighted decision changes when one criterion becomes more or less important. It ranks options from a JSON file, runs a bounded sensitivity sweep, and reports both human-readable and machine-readable results.

Authored by jayis1. The project inherits the licensing terms of the parent repository.

## Features

- Calculates a normalized weighted score for every option.
- Uses deterministic, case-insensitive alphabetical tie-breaking.
- Tests each criterion independently with configurable positive multipliers.
- Emits a readable report or structured JSON with `--json`.
- Validates malformed JSON, missing or extra scores, invalid weights, non-finite numbers, empty names, duplicate option names, and empty option lists.
- Includes `--help` and `--version` flags.
- Runs locally with no network access or data uploads.

## Requirements

- Python 3.9 or newer.
- No runtime dependencies.
- `pytest` is needed only for the test suite.

## Installation

Clone the repository and enter the project directory:

    git clone https://github.com/jayis1/daily-ideas.git
    cd daily-ideas/2026-09-15-assumption-switchboard

No package installation is required.

## Quick start

Run the bundled example:

    python3 assumption_switchboard.py example.json

Inspect available options:

    python3 assumption_switchboard.py --help
    python3 assumption_switchboard.py --version

Use a custom sensitivity sweep:

    python3 assumption_switchboard.py --multipliers 0.1,0.5,2,10 example.json

Produce JSON for another program to consume:

    python3 assumption_switchboard.py --json example.json

Multipliers must be finite numbers greater than zero. The default is `0.25,0.5,2,4`.

## Input format

Input is a JSON object with a non-empty `criteria` object and an `options` list. Every option must score every criterion exactly once. Scores may use any consistent numeric scale.

    {
      "criteria": {"speed": 4, "price": 2},
      "options": [
        {"name": "Fast", "scores": {"speed": 10, "price": 3}},
        {"name": "Cheap", "scores": {"speed": 6, "price": 10}}
      ]
    }

Criteria weights must be non-negative, with at least one positive weight. Option names are trimmed and must be unique without regard to case. The score is the sum of `score × weight`, divided by the sum of all weights.

## How sensitivity analysis works

The tool first calculates the baseline winner. It then adjusts each criterion independently by every requested multiplier while leaving other weights unchanged. A reported change means that scenario produced a different winner. This is a bounded exploration of the supplied assumptions, not a guarantee that the scores are fair, accurate, or complete.

The JSON report contains `baseline`, `winner`, `changes`, `steps`, and `tested` fields. Baseline entries are objects with `name` and `score` fields so the output is straightforward to consume from scripts.

## Errors and exit codes

Invalid input or multipliers are written to standard error and return exit code 2. Successful reports return 0. `--help` and `--version` do not read the input file.

## Tests

From this directory, run:

    python3 -m pytest -q

The tests cover ranking, weight normalization, malformed input, duplicate-name validation, custom multipliers, JSON serialization, and the version flag.

## Limitations and privacy

The tool does not search every possible weighting, infer whether a score is reasonable, or validate decision quality. Input files are read locally and never sent anywhere. Avoid committing sensitive decision data to a shared repository.
