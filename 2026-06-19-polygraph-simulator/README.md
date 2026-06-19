# 🔍 Terminal Polygraph Simulator

An interactive lie detector simulation that analyzes your **keystroke dynamics** — typing speed, rhythm consistency, hesitations, and corrections — to estimate whether you're being deceptive.

## How It Works

The simulator uses real behavioral science principles (simplified for entertainment):

1. **Baseline Calibration** — You answer simple factual questions to establish your truthful typing pattern
2. **Keystroke Analysis** — During the exam, it measures:
   - Typing speed (characters per second)
   - Rhythm consistency (standard deviation of inter-key intervals)
   - Hesitation pauses (gaps longer than 0.5 seconds)
   - Correction rate (backspace frequency)
3. **Deviation Scoring** — Your exam responses are compared against your baseline using z-scores
4. **Visual Verdict** — Results displayed with ASCII polygraph traces, meter bars, and detailed indicator breakdowns

## Features

- **Two modes**: Full examination (4 baseline + 6 exam questions) and quick mode (single question)
- **ASCII polygraph trace visualization** — Sine-wave-based traces that react to deception scores
- **Detailed indicator analysis** — See which behavioral metrics triggered suspicion
- **Baseline normalization** — Compares against YOUR typing patterns, not generic averages
- **Rich terminal UI** — Color-coded meters, verdict banners, and summary tables
- **20 provocative exam questions** — Randomly selected each session
- **Reproducible results** — Same person, same baseline ≈ similar scores

## Installation

No external dependencies needed — uses only Python standard library:

```bash
# Just clone and run
git clone <repo-url>
cd 2026-06-19-polygraph-simulator
```

Requires Python 3.6+.

## Usage

### Full Examination

```bash
python3 polygraph.py
```

This will:
1. Walk you through 4 calibration questions (establish baseline)
2. Ask 6 exam questions with provocative prompts
3. Analyze each response against your baseline
4. Produce a full report with overall deception index

### Quick Mode

```bash
python3 polygraph.py --quick
```

Single question mode: type the alphabet for calibration, then answer one question.

### Custom Question Count

```bash
python3 polygraph.py --questions 10
```

## Example Session

```
╔════════════════════════════════════════════════════════╗
║          🔍  TERMINAL POLYGRAPH SIMULATOR  🔍          ║
╚════════════════════════════════════════════════════════╝

  Phase 1: Baseline Calibration
  Calibration Question 1/4
  What is your first name?
  > Alice
  ✓ Response recorded

  Phase 2: Truth Examination
  Question 1/6
  Have you ever told a lie in your life?
  > Well I try not to...

  ──────────────────────────────────────────────────────────

  ⬤  VERDICT: LIKELY DECEPTIVE  ⬤

  Deception Level      ████████████████░░░░░░░░░░░░░░░░░  48%
  Confidence           ██████████████████████░░░░░░░░░░░░  56%

  ⚡ Key Indicators:
    ▓▓░ More inconsistent rhythm (z=+0.82)
    ▓░░ Slower typing than baseline (z=+0.34)

  ┌─ Detailed Analysis ─────────────────────────────────────┐
  │  Some deviation from baseline detected, but within      │
  │  normal variation range. Cannot conclusively determine   │
  │  truthfulness from keystroke data alone.                 │
  └──────────────────────────────────────────────────────────┘
```

## How the Analysis Works

| Metric | What It Measures | Deception Signal |
|--------|----------------|------------------|
| Avg key interval | Overall typing speed | Slower = more thinking |
| Std key interval | Rhythm variation | Inconsistent = stress |
| Correction rate | Backspace frequency | More corrections = self-doubt |
| Pause count | Hesitation frequency | More pauses = constructing answers |
| Avg pause length | How long you pause | Longer pauses = cognitive load |
| Rhythm consistency | Coefficient of variation | Lower = more automatic (truthful) |

Each metric is compared against your baseline using z-scores, then weighted and combined into an overall deception index.

## Disclaimer

This is a **simulation for entertainment purposes only**. Real polygraph tests are scientifically controversial, and keystroke-dynamic lie detection is not proven reliable. Don't take the results seriously! 🙂

## License

MIT