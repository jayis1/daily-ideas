# 🔍 Terminal Polygraph Simulator

An interactive lie detector simulation that analyzes your **keystroke dynamics** — typing speed, rhythm consistency, hesitations, corrections, stress indicators, and burst patterns — to estimate whether you're being deceptive.

> **Disclaimer:** This is a simulation for entertainment purposes only. Real polygraph tests are scientifically controversial, and keystroke-dynamic lie detection is not proven reliable. Don't take the results seriously! 🙂

## How It Works

The simulator uses real behavioral science principles (simplified for entertainment):

1. **Baseline Calibration** — You answer simple factual questions to establish your truthful typing pattern
2. **Keystroke Analysis** — During the exam, it measures:
   - Typing speed (characters per second)
   - Rhythm consistency (standard deviation of inter-key intervals)
   - Hesitation pauses (gaps longer than 0.5 seconds)
   - Correction rate (backspace frequency)
   - Stress index (composite of pauses, corrections, and rhythm disruption)
   - Burst count (rapid-fire key groups — more bursts = more cognitive load)
   - Initial latency (time before first keypress)
3. **Deviation Scoring** — Your exam responses are compared against your baseline using z-scores
4. **Visual Verdict** — Results displayed with ASCII polygraph traces, meter bars, and detailed indicator breakdowns

## Features

### Core
- **Two modes**: Full examination (4 baseline + 6 exam questions) and quick mode (single question)
- **ASCII polygraph trace visualization** — Sine-wave-based traces that react to deception scores
- **Detailed indicator analysis** — See which behavioral metrics triggered suspicion
- **Baseline normalization** — Compares against YOUR typing patterns, not generic averages
- **Rich terminal UI** — Color-coded meters, verdict banners, and summary tables

### New in v2.0
- **`--version` flag** — Show version number
- **`--seed SEED`** — Reproducible question selection for consistent sessions
- **`--json` / `-j`** — Output results as JSON for programmatic use and scripting
- **`--quiet`** — Reduce delays and animations for faster experience
- **`--baseline N`** — Customize number of calibration questions (2–6)
- **`--questions N`** — Customize number of exam questions (1–10)
- **Stress index** — New composite metric combining pauses, corrections, and rhythm disruption
- **Burst analysis** — Counts rapid-fire key groups (more bursts = more cognitive load)
- **Initial latency tracking** — Measures hesitation before starting to type
- **Per-question min/max** — Final report highlights your most and least deceptive answers
- **Better input fallback** — Simulates natural keystroke timing variation when raw terminal isn't available
- **Improved error handling** — Handles edge cases like empty responses, single-char answers, and zero-variance baselines
- **43 unit tests** — Comprehensive test coverage for all core functionality

## Installation

No external dependencies needed — uses only Python standard library:

```bash
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

### JSON Output

```bash
python3 polygraph.py --json
```

Outputs structured JSON with all analysis data — useful for scripting, logging, or piping to other tools:

```json
{
  "version": "2.0.0",
  "baseline_samples": 4,
  "results": [
    {
      "question": "Have you ever told a lie in your life?",
      "response": "Well I try not to...",
      "deception_score": 0.48,
      "confidence": 0.56,
      "verdict": "INCONCLUSIVE",
      "indicators": [...]
    }
  ],
  "overall_deception_score": 0.48,
  "overall_verdict": "INCONCLUSIVE"
}
```

### Reproducible Sessions

```bash
python3 polygraph.py --seed 42
```

Use `--seed` to get the same question order across runs.

### All Options

```
python3 polygraph.py [OPTIONS]

Options:
  -h, --help            Show help message and exit
  --version             Show version number and exit
  --quick, -q           Quick mode: single question examination
  --questions, -n N     Number of exam questions (default: 6, range: 1-10)
  --baseline, -b N      Number of baseline calibration questions (default: 4, range: 2-6)
  --seed, -s SEED       Random seed for reproducible question selection
  --quiet               Reduce delays and animations for faster experience
  --json, -j            Output results as JSON (for programmatic use)
```

### Combinations

```bash
# Quick JSON output with reproducible seed
python3 polygraph.py --quick --json --seed 42

# 10-question exam with 6 baseline questions, quiet mode
python3 polygraph.py -n 10 -b 6 --quiet

# 3-question exam with JSON output
python3 polygraph.py -n 3 --json
```

## Example Session

```
╔════════════════════════════════════════════════════════╗
║                                                        ║
║          🔍  TERMINAL POLYGRAPH SIMULATOR  🔍          ║
║                                                        ║
║        Interactive Lie Detection via Keystroke         ║
║              Dynamics Analysis Engine                  ║
║                                                        ║
╚════════════════════════════════════════════════════════╝

  Analyzes typing speed, rhythm, corrections, and hesitation
  to detect deviations from your truthful baseline.

           ⚠  TRUTH VERIFICATION PROTOCOL  ⚠

  This system analyzes keystroke dynamics to detect
  physiological stress patterns associated with deception.

  ──────────────────────────────────────────────────────────

  ⬤  VERDICT: LIKELY DECEPTIVE  ⬤

  Deception Level      ████████████████░░░░░░░░░░░░░░░░░  48%
  Confidence           ██████████████████████░░░░░░░░░░░░  56%
  Stress Indicator     ██████████████░░░░░░░░░░░░░░░░░░░░  32%

  ⚡ Key Indicators:
    ▓▓░ More inconsistent rhythm (z=+0.82)
    ▓░░ Slower typing than baseline (z=+0.34)

  ┌─ Detailed Analysis ─────────────────────────────────────┐
  │  Some deviation from baseline detected, but within      │
  │  normal variation range. Cannot conclusively determine   │
  │  truthfulness from keystroke data alone.                 │
  └──────────────────────────────────────────────────────────┘
```

## Analysis Metrics

| Metric | What It Measures | Deception Signal |
|--------|----------------|------------------|
| Avg key interval | Overall typing speed | Slower = more thinking |
| Std key interval | Rhythm variation | Inconsistent = stress |
| Correction rate | Backspace frequency | More corrections = self-doubt |
| Pause count | Hesitation frequency | More pauses = constructing answers |
| Avg pause length | How long you pause | Longer pauses = cognitive load |
| Rhythm consistency | Coefficient of variation | Lower = more automatic (truthful) |
| Stress index | Composite metric | Higher = overall stress response |
| Burst count | Rapid-fire key groups | More bursts = more cognitive load |
| Initial latency | Time before first key | Longer = thinking before answering |

Each metric is compared against your baseline using z-scores, then weighted and combined into an overall deception index.

## Running Tests

```bash
python3 -m pytest test_polygraph.py -v
```

43 tests covering:
- KeystrokeAnalyzer metrics computation
- PolygraphEngine baseline and analysis
- Edge cases (empty data, zero-variance baselines, negative intervals)
- Visual components (traces, bars, labels)
- CLI argument parsing (--version, --quick, --seed, --json, etc.)
- JSON export structure
- Reproducibility with seed

## License

MIT