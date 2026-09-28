# Retry Budget Planner

Retry Budget Planner is a dependency-free Python CLI that lays out an exponential-backoff retry schedule and shows how many complete attempts fit before a deadline.

## Why

Retry settings are often chosen one number at a time, making it easy to create a policy whose later attempts can never finish inside the caller's timeout. This tool turns the policy into a concrete timeline without making any network requests.

## Requirements

- Python 3.8 or newer
- No third-party packages or network access

## Run

From the repository root:

```bash
cd 2026-09-28-retry-budget-planner
python3 retry_budget_planner.py \
  --deadline 30 \
  --attempt-timeout 2 \
  --initial-delay 1 \
  --multiplier 2 \
  --max-delay 8
```

Verified output:

```text
Retry budget: 5 attempts fit in 30s
- attempt 1: start immediately; run 0s-2s
- attempt 2: wait 1s; run 3s-5s
- attempt 3: wait 2s; run 7s-9s
- attempt 4: wait 4s; run 13s-15s
- attempt 5: wait 8s; run 23s-25s
Unused budget: 5s
```

Only complete attempts are included. A delay is counted only when the following attempt also fits. Use `--max-attempts` to model a hard attempt limit and `--json` for machine-readable output:

```bash
python3 retry_budget_planner.py \
  --deadline 10 --attempt-timeout 1 --initial-delay 0.5 \
  --max-attempts 3 --json
```

All durations are seconds and may be fractional. The deadline, attempt timeout, initial delay, multiplier, and optional delay cap must be positive finite numbers.

## Tests

Run the focused suite from this directory:

```bash
python3 -m unittest -v
```

The tests cover capped exponential schedules, exact deadline boundaries, partial attempts, hard attempt limits, fractional durations, invalid values, text rendering, JSON serialization, and CLI behavior.
