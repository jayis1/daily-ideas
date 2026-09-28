# Daily Ideas

A growing collection of small, runnable coding projects by jayis1. Each dated directory is an independent experiment with its own source code, README, and (when practical) tests. The collection favors local-first programs that can be explored from a terminal without accounts or network services.

## Latest project

### Retry Budget Planner — `2026-09-28-retry-budget-planner/`

A dependency-free Python CLI that turns retry and exponential-backoff settings into a concrete timeline bounded by a deadline.

```bash
cd 2026-09-28-retry-budget-planner
python3 retry_budget_planner.py --deadline 30 --attempt-timeout 2 --initial-delay 1 --max-delay 8
```

Previous project: [Argument X-Ray](2026-09-28-argument-xray/), an inspector for exact command-line argument boundaries and safe POSIX replay commands.

## Running projects

Browse the dated directories to find terminal games, generators, simulations, puzzles, visualizations, and utilities. Each project README documents its exact requirements and launch command. Most Python projects run directly with Python 3.8+; check the local README for exceptions.

## Repository layout

```text
daily-ideas/
├── README.md                         # Collection index
├── YYYY-MM-DD-project-name/          # Independent project
│   ├── README.md
│   ├── program files
│   └── tests (where included)
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
