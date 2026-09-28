# Daily Ideas

A growing collection of small, runnable coding projects by jayis1. Each dated directory is an independent experiment with its own source code, README, and (when practical) tests. The collection favors local-first programs that can be explored from a terminal without accounts or network services.

## Latest project

### Calendar Gap Finder — `2026-09-28-calendar-gap-finder/`

A dependency-free Python CLI that finds shared free time from compact busy-window descriptions, without calendar accounts or network access.

```bash
cd 2026-09-28-calendar-gap-finder
python3 calendar_gap_finder.py --person 'Ada=09:00-10:00,13:00-14:00' --person 'Grace=10:30-11:30,13:30-15:00' --minutes 45
```

Previous project: [Receipt Recomposer](2026-09-28-receipt-recomposer/), an exact-subtotal finder for itemized receipts.

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
