# Daily Ideas

A growing collection of small, runnable coding projects by jayis1. Each dated directory is an independent experiment with its own source code, README, and (when practical) tests. The collection favors local-first programs that can be explored from a terminal without accounts or network services.

## Latest project

### Assumption Switchboard — `2026-09-15-assumption-switchboard/`

A standard-library Python CLI that ranks options using weighted criteria and exposes how the winner changes when one assumption is adjusted. It includes deterministic example data, validation, and tests.

```bash
cd 2026-09-15-assumption-switchboard
python3 assumption_switchboard.py example.json
```

## Running projects

Browse the dated directories to find terminal games, generators, simulations, puzzles, visualizations, utilities, and hardware explorations. Each project README documents its exact requirements and launch command. Most Python projects run directly with Python 3.8+; check the local README for exceptions.

## Repository layout

```text
daily-ideas/
├── README.md                         # Collection index
├── YYYY-MM-DD-project-name/          # Independent project
│   ├── README.md
│   ├── program files
│   └── tests (where included)
├── systems/                          # Open hardware integrations
└── .github/workflows/                # Repository validation
```

## Principles

- Keep each idea small enough to understand and run in one sitting.
- Prefer deterministic, dependency-light, offline demos.
- Document real commands and observed behavior rather than placeholders.
- Keep projects independent so an experiment can be reused without a shared framework.

## Requirements

Python 3.8+ covers most projects. Individual READMEs are authoritative for additional runtimes or optional dependencies.

## License

Projects are authored by jayis1 and inherit the licensing terms established by the repository.
