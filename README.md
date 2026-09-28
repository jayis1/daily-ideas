# Daily Ideas

A growing collection of small, runnable coding projects by jayis1. Each dated directory is an independent experiment with its own source code, README, and (when practical) tests. The collection favors local-first programs that can be explored from a terminal without accounts or network services.

## Latest project

### Receipt Recomposer — `2026-09-28-receipt-recomposer/`

A dependency-free Python CLI that finds the combinations of receipt items that exactly match a mystery subtotal, using integer cents for exact results.

```bash
cd 2026-09-28-receipt-recomposer
python3 receipt_recomposer.py --target 5.00 'Tea=2.50' 'Cake=3.75' 'Pen=1.25'
```

Previous project: [Paperwork Panic](2026-09-25-paperwork-panic/), an absurd form-routing terminal game.

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
