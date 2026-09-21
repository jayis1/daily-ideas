# Assumption Switchboard

Assumption Switchboard is a small, dependency-free Python CLI for finding out whether a weighted decision changes when one criterion becomes more or less important. Give it a JSON decision file; it ranks the options, sweeps a bounded set of weight multipliers, and reports any winner changes.

Authored by jayis1. The project inherits the licensing terms of the parent repository.

## Features

- Computes normalized weighted scores for every option.
- Uses deterministic, case-insensitive alphabetical tie-breaking.
- Tests each criterion independently with configurable positive multipliers.
- Prints a human-readable report or machine-readable JSON with `--json`.
- Validates malformed JSON, missing or extra scores, invalid weights, non-finite values, empty names, duplicate option names, and empty option lists.
- Handles oversized JSON integers as normal validation errors instead of an uncaught traceback.
- Provides `--help` and `--version`.
- Runs locally without network access or data uploads.

## Requirements

- Python 3.9 or newer.
- No runtime dependencies.
- `pytest` is needed only for the test suite.

## Installation

Clone the parent repository and enter this project directory:

    git clone https://github.com/jayis1/daily-ideas.git
    cd daily-ideas/2026-09-15-assumption-switchboard

No package installation is required. For tests, install or otherwise provide `pytest` in your development environment.

## Quick start

Run the bundled example:

    python3 assumption_switchboard.py example.json

Inspect the command options and version:

    python3 assumption_switchboard.py --help
    python3 assumption_switchboard.py --version

Use a custom sensitivity sweep:

    python3 assumption_switchboard.py --multipliers 0.1,0.5,2,10 example.json

Produce structured JSON for another program:

    python3 assumption_switchboard.py --json example.json

Multipliers must be finite numbers greater than zero. The default is `0.25,0.5,2,4`. Invalid input or multipliers return exit code 2; successful reports return 0.

## Input format

The input is a JSON object with a non-empty `criteria` object and an `options` list. Every option must score every criterion exactly once. Scores may use any consistent numeric scale.

    {
      "criteria": {"speed": 4, "price": 2},
      "options": [
        {"name": "Fast", "scores": {"speed": 10, "price": 3}},
        {"name": "Cheap", "scores": {"speed": 6, "price": 10}}
      ]
    }

Criteria weights must be non-negative, with at least one positive weight. Option names are trimmed and must be unique without regard to case. The score is the sum of `score × weight`, divided by the sum of all weights.

## Sensitivity analysis

The tool first calculates the baseline winner. It then adjusts each criterion independently by every requested multiplier while leaving the other weights unchanged. A reported change means that scenario produced a different winner. This is a bounded exploration of the supplied assumptions, not a guarantee that the scores are fair, accurate, or complete.

The JSON report contains `baseline`, `winner`, `changes`, `steps`, and `tested`. Baseline entries are objects with `name` and `score` fields.

## Tests

From this directory, run:

    python3 -m pytest -q

The tests cover ranking and weight normalization, malformed and oversized numeric input, duplicate-name validation, custom multipliers, JSON serialization, CLI validation, and the version flag. The source also passes Python bytecode compilation.

## Known limitations

- The tool does not search every possible weighting.
- It does not infer whether a score or weighting is reasonable.
- It does not validate decision quality.
- Input files are read locally and never sent anywhere; avoid committing sensitive decision data to a shared repository.

## Changelog

### 2026-09-21

- Fixed a crash when a JSON integer was too large for `math.isfinite()` to convert safely; it is now rejected with the documented validation error.
- Updated the regression suite and CLI version to 1.1.1.
- Rechecked the example report, JSON output, help/version paths, invalid multipliers, missing files, compilation, and the full pytest suite.
