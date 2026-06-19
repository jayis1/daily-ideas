# 🔍 Terminal Polygraph Simulator v2.1.0

An interactive lie detector simulation that analyzes your **keystroke dynamics** — typing speed, rhythm consistency, hesitations, and corrections — to estimate whether you're being deceptive.

## What's New in v2.1.0

- **Bug fix**: `record_backspace()` no longer increments the backspace counter when the response is empty, preventing `correction_rate` from exceeding 1.0
- **Bug fix**: Replaced fragile `_` throwaway variable with explicit `truth_prob` in `quick_mode()` — prevents `UnboundLocalError` or incorrect `truth_probability` values
- **Bug fix**: `quick_mode()` no longer crashes with `UnboundLocalError` when the response is too short for analysis — returns `None` gracefully
- **Bug fix**: Empty response after all backspaces is properly handled — returns `None` metrics instead of crashing
- **New feature**: `--auto` / `-a` flag for fully non-interactive mode with simulated responses (no stdin required) — perfect for CI/CD and scripting
- **New feature**: `KeystrokeAnalyzer.from_response()` class method for creating synthetic keystroke analyzers programmatically
- **14 new tests** covering all bug fixes and new features

## How It Works

The simulator uses behavioral science principles (simplified for entertainment):

1. **Baseline Calibration** — You answer simple factual questions to establish your truthful typing pattern
2. **Keystroke Analysis** — During the exam, it measures:
   - Typing speed (characters per second)
   - Rhythm consistency (standard deviation of inter-key intervals)
   - Hesitation pauses (gaps longer than 0.5 seconds)
   - Correction rate (backspace frequency)
   - Initial latency (delay before starting to type)
   - Stress index (composite of pause, correction, and rhythm disruption)
3. **Deviation Scoring** — Your exam responses are compared against your baseline using z-scores
4. **Visual Verdict** — Results displayed with ASCII polygraph traces, meter bars, and detailed indicator breakdowns

## Features

- **Two interactive modes**: Full examination (4 baseline + 6 exam questions) and quick mode (single question)
- **Non-interactive mode**: `--auto` flag runs simulated responses with no stdin required
- **JSON export**: `--json` for programmatic use; `--auto` implies `--json`
- **ASCII polygraph trace visualization** — Sine-wave-based traces that react to deception scores
- **Detailed indicator analysis** — See which behavioral metrics triggered suspicion
- **Baseline normalization** — Compares against YOUR typing patterns, not generic averages
- **Rich terminal UI** — Color-coded meters, verdict banners, and summary tables
- **25 provocative exam questions** — Randomly selected each session
- **Reproducible results** — `--seed` for deterministic question selection and simulated typing
- **Adjustable question counts** — `--questions` and `--baseline` flags

## Installation

No external dependencies — uses only the Python standard library:

```bash
git clone <repo-url>
cd 2026-06-19-polygraph-simulator
```

Requires Python 3.6+.

## Usage

### Full Examination (Interactive)

```bash
python3 polygraph.py
```

This will:
1. Walk you through 4 calibration questions (establish baseline)
2. Ask 6 exam questions with provocative prompts
3. Analyze each response against your baseline
4. Produce a full report with overall deception index

### Quick Mode (Interactive)

```bash
python3 polygraph.py --quick
```

Single question mode: type the alphabet for calibration, then answer one question.

### Auto Mode (Non-Interactive)

```bash
python3 polygraph.py --auto --seed 42
```

Runs a complete simulation with synthetic responses — no user input required. Outputs structured JSON. Perfect for:

- CI/CD pipelines
- Scripting and automation
- Testing and benchmarking
- Demo screenshots

```bash
# Custom question count in auto mode
python3 polygraph.py --auto --questions 3 --baseline 2 --seed 42

# Pretty-print JSON output
python3 polygraph.py --auto --seed 42 | python3 -m json.tool
```

### JSON Output (Interactive)

```bash
python3 polygraph.py --json
```

Outputs results as JSON after the interactive session completes.

### All CLI Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--auto` | `-a` | Non-interactive mode with simulated responses (implies `--json`) |
| `--quick` | `-q` | Quick mode: single question examination |
| `--questions N` | `-n N` | Number of exam questions (default: 6, range: 1–10) |
| `--baseline N` | `-b N` | Number of baseline questions (default: 4, range: 2–6) |
| `--seed N` | `-s N` | Random seed for reproducible question selection |
| `--json` | `-j` | Output results as JSON |
| `--quiet` | | Reduce delays and animations |
| `--version` | | Show version number |
| `--help` | `-h` | Show help message |

## Example Output

### Interactive Session

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
```

### Auto Mode JSON

```bash
$ python3 polygraph.py --auto --seed 42 --questions 2 --baseline 2
```

```json
{
  "version": "2.1.0",
  "mode": "auto",
  "baseline_samples": 2,
  "results": [
    {
      "question": "Have you ever cheated on a test or game?",
      "response": "Yes I have but only small ones",
      "deception_score": 0.4922,
      "confidence": 0.4,
      "verdict": "INCONCLUSIVE",
      "truth_probability": 0.65,
      "indicators": [...]
    }
  ],
  "overall_deception_score": 0.3812,
  "overall_verdict": "LIKELY TRUTHFUL",
  "baseline": { ... }
}
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
| Stress index | Composite indicator | Higher = more stress |
| Initial latency | Time to first keystroke | Longer = more hesitation |

Each metric is compared against your baseline using z-scores, then weighted and combined into an overall deception index.

## Bugs Fixed in v2.1.0

1. **Backspace on empty response inflated correction rate** — `record_backspace()` now only increments `backspaces` when there's actually a character to delete. Previously, pressing backspace on an empty response would increment the counter, making `correction_rate` exceed 1.0.

2. **Fragile `_` variable for truth_probability** — `quick_mode()` used `question, _ = random.choice(...)` then later `result['truth_probability'] = _`. The `_` throwaway variable was replaced with the explicit `truth_prob` variable name.

3. **UnboundLocalError in quick_mode** — When metrics were None (empty response), the `result` variable was never assigned but was still referenced at `return result`, causing a crash. Now `result` is initialized to `None` before the conditional.

4. **No non-interactive mode** — `--json` still required interactive stdin, making it unusable for automation. Added `--auto` flag with `KeystrokeAnalyzer.from_response()` class method for fully synthetic keystroke simulation.

## Running Tests

```bash
python3 -m pytest test_polygraph.py -v
```

57 tests covering KeystrokeAnalyzer, PolygraphEngine, visual components, CLI arguments, JSON export, reproducibility, edge cases, all bug fixes, and the new auto mode.

## Disclaimer

This is a **simulation for entertainment purposes only**. Real polygraph tests are scientifically controversial, and keystroke-dynamic lie detection is not proven reliable. Don't take the results seriously! 🙂

## License

MIT