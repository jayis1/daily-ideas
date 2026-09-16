# Assumption Switchboard

Assumption Switchboard is a dependency-free Python command-line tool for testing whether a weighted decision is sensitive to its assumptions. It ranks options from a JSON file, then changes one criterion weight at a time and reports when a different option becomes the winner.

The project is authored by jayis1 and inherits the licensing terms of the parent repository.

## Features

- Computes a deterministic, normalized weighted ranking.
- Tests each criterion independently with configurable positive multipliers.
- Uses stable alphabetical ordering to break equal-score ties.
- Rejects malformed JSON, missing scores, unknown criteria, invalid weights, non-finite numbers, and empty option lists with a useful error and exit code 2.
- Provides `--help` and `--version` flags.
- Runs entirely locally with no network access or data uploads.

## Requirements

- Python 3.9 or newer.
- No runtime dependencies. `pytest` is needed only to run the test suite.

## Installation

Clone the repository and enter the project directory:

    git clone https://github.com/jayis1/daily-ideas.git
    cd daily-ideas/2026-09-15-assumption-switchboard

No package installation is required; the program uses the Python standard library.

## Quick start

Run the bundled example:

    python3 assumption_switchboard.py example.json

The output includes the baseline ranking and the tested sensitivity scenarios. To inspect all available options:

    python3 assumption_switchboard.py --help
    python3 assumption_switchboard.py --version

Try a narrower or more extreme sensitivity sweep by supplying your own comma-separated multipliers:

    python3 assumption_switchboard.py --multipliers 0.1,0.5,2,10 example.json

Multipliers must be finite numbers greater than zero. The default is `0.25,0.5,2,4`.

## Input format

The input must be a JSON object with a non-empty `criteria` object and an `options` list. Every option must score every criterion exactly once. Scores may use any consistent numeric scale.

    {
      "criteria": {"speed": 4, "price": 2},
      "options": [
        {"name": "Fast", "scores": {"speed": 10, "price": 3}},
        {"name": "Cheap", "scores": {"speed": 6, "price": 10}}
      ]
    }

Criteria weights must be non-negative, with at least one positive weight. The score for an option is the sum of `score × weight`, divided by the sum of all weights. Multiplying every weight by the same number therefore does not change the ranking.

## How sensitivity analysis works

First, the tool calculates the baseline winner from the supplied weights. It then adjusts each criterion independently by every requested multiplier while leaving the other weights unchanged. A reported change means that scenario produced a different winner. This is a bounded exploration of the supplied assumptions, not a guarantee that the scores are fair, accurate, or complete.

## Tests

From this directory, run:

    python3 -m pytest -q

The tests cover baseline ranking, weight normalization, malformed input, custom multipliers, and the version flag.

## Limitations and privacy

The tool does not search every possible weighting, infer whether a score is reasonable, or validate decision quality. Input files are read locally and never sent anywhere. Avoid committing sensitive decision data to a shared repository.
