#!/usr/bin/env python3
"""
Terminal Polygraph Simulator
=============================
An interactive lie detector simulation that analyzes your typing patterns
(speed, consistency, corrections, pauses) to determine if you're lying.

Uses real keystroke dynamics to detect deviations from your baseline.

Features:
  - Full examination mode (baseline calibration + exam questions)
  - Quick single-question mode
  - JSON export of results (--json)
  - Reproducible sessions (--seed)
  - Adjustable question counts
  - Stress-level and response-length analysis metrics
  - Comprehensive ASCII polygraph trace visualization

Usage:
  python3 polygraph.py              # Full examination
  python3 polygraph.py --quick      # Quick single-question mode
  python3 polygraph.py --json       # Output results as JSON
  python3 polygraph.py --version    # Show version
"""

import time
import sys
import random
import statistics
import math
import os
import json
import argparse

__version__ = "2.0.0"

# ─── ANSI Helpers ──────────────────────────────────────────────────────────

def clear():
    """Clear the terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')

def reset():
    """Reset ANSI formatting."""
    print('\033[0m', end='')

def bold():
    """Enable bold text."""
    print('\033[1m', end='')

def dim():
    """Enable dim text."""
    print('\033[2m', end='')

def red():
    """Set text color to red."""
    print('\033[31m', end='')

def green():
    """Set text color to green."""
    print('\033[32m', end='')

def yellow():
    """Set text color to yellow."""
    print('\033[33m', end='')

def cyan():
    """Set text color to cyan."""
    print('\033[36m', end='')

def magenta():
    """Set text color to magenta."""
    print('\033[35m', end='')

def move_up(n=1):
    """Move cursor up n lines."""
    print(f'\033[{n}A', end='')

def erase_line():
    """Erase the current line."""
    print('\033[2K\r', end='')

def center(text, width=70):
    """Center text within a given width."""
    return text.center(width)


def print_banner():
    """Display the polygraph simulator title banner."""
    clear()
    cyan(); bold()
    print(center("╔════════════════════════════════════════════════════════╗"))
    print(center("║                                                        ║"))
    print(center("║          🔍  TERMINAL POLYGRAPH SIMULATOR  🔍          ║"))
    print(center("║                                                        ║"))
    print(center("║        Interactive Lie Detection via Keystroke         ║"))
    print(center("║              Dynamics Analysis Engine                  ║"))
    print(center("║                                                        ║"))
    print(center("╚════════════════════════════════════════════════════════╝"))
    reset()
    print()
    dim()
    print(center("Analyzes typing speed, rhythm, corrections, and hesitation"))
    print(center("to detect deviations from your truthful baseline."))
    reset()
    print()


# ─── Question Bank ──────────────────────────────────────────────────────────

BASELINE_QUESTIONS = [
    "What is your first name?",
    "What city were you born in?",
    "What color is the sky on a clear day?",
    "How many fingers does a typical person have?",
    "What day comes after Friday?",
    "What is 2 plus 2?",
    "What planet do we live on?",
    "What season comes after winter?",
    "What is the opposite of hot?",
    "How many legs does a cat have?",
    "What is the capital of your country?",
    "What color is grass?",
    "What is your favorite food?",
    "What day is it today?",
    "What language are we speaking?",
]

EXAM_QUESTIONS = [
    ("Have you ever told a lie in your life?", 0.92),
    ("Did you finish all your homework as a kid?", 0.70),
    ("Have you ever pretended to be sick to avoid something?", 0.80),
    ("Do you think you're a good liar?", 0.65),
    ("Have you ever taken credit for someone else's work?", 0.60),
    ("Would you lie to protect a friend?", 0.85),
    ("Have you ever lied on a resume or application?", 0.55),
    ("Do you always tell the complete truth?", 0.90),
    ("Have you ever cheated on a test or game?", 0.65),
    ("Would your friends say you're trustworthy?", 0.75),
    ("Have you ever eaten the last cookie and blamed someone else?", 0.50),
    ("Do you always return borrowed items on time?", 0.60),
    ("Have you ever said 'I'm fine' when you weren't?", 0.88),
    ("Did you ever fake a compliment?", 0.78),
    ("Have you ever snooped through someone's phone?", 0.45),
    ("Do you always wash your hands after using the restroom?", 0.72),
    ("Have you ever replied 'nice!' without actually reading the message?", 0.82),
    ("Would you rather be honest and hurt someone, or lie and spare their feelings?", 0.70),
    ("Have you ever recycled a gift someone gave you?", 0.40),
    ("Did you ever agree with an opinion you actually disagreed with?", 0.85),
    ("Have you ever exaggerated your skills on a dating profile?", 0.73),
    ("Do you always slow down when you see a speed limit sign?", 0.58),
    ("Have you ever laughed at a joke you didn't find funny?", 0.87),
    ("Have you ever blocked someone instead of telling them why?", 0.62),
    ("Did you ever read someone else's diary or journal?", 0.48),
]


# ─── Keystroke Analyzer ─────────────────────────────────────────────────────

class KeystrokeAnalyzer:
    """Collects and analyzes keystroke dynamics for a single response.

    Tracks timing between keystrokes, backspace corrections, pauses,
    and computes metrics like typing speed, rhythm consistency,
    and hesitation patterns.

    Can operate in two modes:
      - Raw mode: record_key() / record_backspace() called per keystroke
      - Synthetic mode: set from timed input() with simulated keystroke timing
    """

    PAUSE_THRESHOLD = 0.5  # seconds between keys to count as a pause

    def __init__(self):
        self.start_time = None
        self.key_times = []       # list of (timestamp, char_or_label)
        self.backspaces = 0
        self.total_chars = 0
        self.finished = False
        self.response = ""

    def start(self):
        """Begin recording keystroke timing."""
        self.start_time = time.time()
        self.key_times = [(self.start_time, None)]

    def record_key(self, char):
        """Record a regular keypress with its timestamp."""
        now = time.time()
        self.key_times.append((now, char))
        self.total_chars += 1
        self.response += char

    def record_backspace(self):
        """Record a backspace keypress."""
        now = time.time()
        self.key_times.append((now, 'BACKSPACE'))
        self.backspaces += 1
        if self.response:
            self.response = self.response[:-1]

    def finish(self):
        """Mark the recording as finished."""
        self.finished = True

    def get_metrics(self):
        """Compute keystroke dynamics metrics from recorded data.

        Returns a dict with metrics, or None if insufficient data
        (fewer than 2 key events or empty response).
        """
        if not self.key_times or len(self.key_times) < 2:
            return None

        durations = []      # inter-key intervals that are NOT pauses
        pauses = []          # inter-key intervals that ARE pauses
        between_keys = []    # all inter-key intervals

        for i in range(1, len(self.key_times)):
            dt = self.key_times[i][0] - self.key_times[i - 1][0]
            # Ignore non-positive intervals (clock skew / synthetic data)
            if dt <= 0:
                dt = 0.001
            between_keys.append(dt)
            if dt > self.PAUSE_THRESHOLD:
                pauses.append(dt)
            else:
                durations.append(dt)

        if not between_keys:
            return None

        total_time = self.key_times[-1][0] - self.key_times[0][0]
        if total_time <= 0:
            total_time = 0.001
        response_len = len(self.response)
        if response_len == 0:
            return None

        metrics = {
            'total_time': total_time,
            'response_length': response_len,
            'avg_key_interval': statistics.mean(between_keys),
            'median_key_interval': statistics.median(between_keys),
            'std_key_interval': statistics.stdev(between_keys) if len(between_keys) > 1 else 0,
            'backspaces': self.backspaces,
            'correction_rate': self.backspaces / max(self.total_chars, 1),
            'pause_count': len(pauses),
            'pause_total': sum(pauses),
            'avg_pause': statistics.mean(pauses) if pauses else 0,
            'typing_speed_cps': response_len / max(total_time, 0.01),
            'rhythm_consistency': 0,
            'burst_count': self._count_bursts(between_keys),
            'initial_latency': between_keys[0] if between_keys else 0,
        }

        # Rhythm consistency: lower std relative to mean = more consistent
        if metrics['avg_key_interval'] > 0:
            cv = metrics['std_key_interval'] / metrics['avg_key_interval']
            metrics['rhythm_consistency'] = max(0, 1 - cv)

        # Stress index: composite of pauses, corrections, and rhythm disruption
        pause_factor = min(metrics['pause_count'] / max(response_len * 0.3, 1), 1)
        correction_factor = min(metrics['correction_rate'] * 2, 1)
        rhythm_factor = 1 - metrics['rhythm_consistency']
        metrics['stress_index'] = (pause_factor * 0.3 + correction_factor * 0.3 + rhythm_factor * 0.4)

        return metrics

    @staticmethod
    def _count_bursts(intervals, gap_threshold=0.3):
        """Count the number of rapid-fire 'burst' groups in the typing.

        A burst is a sequence of keys typed in quick succession (under gap_threshold).
        More bursts with pauses between them can indicate cognitive load.
        """
        if not intervals:
            return 0
        bursts = 1
        for dt in intervals:
            if dt > gap_threshold:
                bursts += 1
        return bursts


class PolygraphEngine:
    """Compares response metrics against baseline to estimate deception.

    The engine collects baseline metrics from truthful calibration questions,
    then analyzes each exam response for deviations from that baseline using
    z-scores. Higher deviations indicate potential deception.
    """

    # Weights for each deception indicator (metric_name, indicator_label,
    # higher_means_suspicious, description, weight)
    CHECKS = [
        ('avg_key_interval', 'typing_speed_slower', True,
         'Slower typing than baseline', 0.18),
        ('avg_key_interval', 'typing_speed_faster', False,
         'Faster typing than baseline (rushed response)', 0.12),
        ('std_key_interval', 'rhythm_variation', True,
         'More inconsistent rhythm', 0.20),
        ('correction_rate', 'corrections', True,
         'More corrections (second-guessing)', 0.12),
        ('pause_count', 'hesitation', True,
         'More pauses (thinking before answering)', 0.14),
        ('avg_pause', 'long_hesitation', True,
         'Longer pauses detected', 0.06),
        ('rhythm_consistency', 'smoothness', False,
         'Less smooth typing rhythm', 0.06),
        ('stress_index', 'stress', True,
         'Higher overall stress indicators', 0.08),
        ('initial_latency', 'start_hesitation', True,
         'Longer delay before starting to type', 0.04),
    ]

    def __init__(self):
        self.baseline_metrics = []
        self.exam_results = []

    def add_baseline(self, metrics):
        """Add a baseline (truthful) metrics sample."""
        if metrics:
            self.baseline_metrics.append(metrics)

    def add_result(self, result):
        """Add an exam result for later reporting."""
        self.exam_results.append(result)

    def get_baseline_stats(self):
        """Compute mean and std for each metric across all baseline samples.

        Returns a dict keyed by metric name, each containing 'mean', 'std',
        and 'values', or None if no baseline data.
        """
        if not self.baseline_metrics:
            return None

        keys = self.baseline_metrics[0].keys()
        stats = {}
        for key in keys:
            values = [m[key] for m in self.baseline_metrics if key in m]
            if values:
                stats[key] = {
                    'mean': statistics.mean(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0,
                    'values': values,
                }
        return stats

    def analyze(self, metrics):
        """Analyze a single response against the baseline.

        Returns a dict with:
          - deception_score: float 0.0–1.0
          - confidence: float 0.0–1.0
          - indicators: list of (description, score, z_score) tuples
          - metric_zscores: dict of per-metric z-scores
        """
        baseline = self.get_baseline_stats()
        if not baseline or not metrics:
            return {
                'deception_score': 0.5,
                'confidence': 0.1,
                'indicators': ['Insufficient baseline data'],
                'metric_zscores': {},
            }

        indicators = []
        scores = []
        metric_zscores = {}

        total_weight = 0

        for metric_name, indicator_label, higher_means_suspicious, description, weight in self.CHECKS:
            if metric_name not in baseline or metric_name not in metrics:
                continue

            b_mean = baseline[metric_name]['mean']
            b_std = baseline[metric_name]['std']
            value = metrics[metric_name]

            if b_std == 0:
                b_std = b_mean * 0.1  # Small fallback for zero-variance baselines

            # Z-score: how many standard deviations from baseline
            z_score = (value - b_mean) / max(b_std, 0.001)
            metric_zscores[metric_name] = z_score

            if higher_means_suspicious:
                score = min(max(z_score / 3.0, 0), 1)
            else:
                score = min(max(-z_score / 3.0, 0), 1)

            if score > 0.3:
                indicators.append((description, score, z_score))

            scores.append(score)
            total_weight += weight

        # Weighted average deception score
        if scores and total_weight > 0:
            used_weights = [w for (_, _, _, _, w) in self.CHECKS[:len(scores)]]
            # Only use weights for checks that were actually applied
            applied_weights = []
            idx = 0
            for metric_name, indicator_label, higher_means_suspicious, description, weight in self.CHECKS:
                if metric_name in baseline and metric_name in metrics:
                    applied_weights.append(weight)
            deception_score = sum(s * w for s, w in zip(scores, applied_weights)) / sum(applied_weights)
        else:
            deception_score = 0.5

        # Confidence based on baseline sample size
        confidence = min(len(self.baseline_metrics) / 5.0, 0.95)

        # Add small noise for realism (less noise with more baseline data)
        noise = random.gauss(0, 0.05 * (1 - confidence))
        deception_score = max(0, min(1, deception_score + noise))

        return {
            'deception_score': deception_score,
            'confidence': confidence,
            'indicators': indicators,
            'metric_zscores': metric_zscores,
        }


# ─── Visual Components ─────────────────────────────────────────────────────

def draw_polygraph_trace(scores, width=60, height=8):
    """Draw an animated polygraph-style trace based on deception scores.

    Returns a list of strings, one per line of the trace.
    """
    lines = []
    for y in range(height):
        row = ""
        for x in range(width):
            t = x / width
            # Combine sine waves for realistic polygraph look
            val = (
                0.4 * math.sin(t * 6 + y * 0.3) +
                0.3 * math.sin(t * 13 + y * 0.5) +
                0.2 * math.sin(t * 23 + y * 0.7)
            )
            # Modulate based on average score
            if scores:
                avg = sum(scores) / len(scores)
                val += (avg - 0.5) * math.sin(t * 30 + y)

            val = (val + 1) / 2  # Normalize to 0-1
            threshold = y / height

            if abs(val - threshold) < 0.08:
                row += "█"
            elif abs(val - threshold) < 0.15:
                row += "▓"
            elif abs(val - threshold) < 0.22:
                row += "░"
            else:
                row += " "
        lines.append(row)
    return lines


def draw_bar(value, width=40):
    """Draw a horizontal meter bar as a string with ANSI colors.

    Returns the formatted bar string (not printed).
    """
    filled = int(max(0, min(value, 1)) * width)
    empty = width - filled

    if value < 0.3:
        col = '\033[32m'
    elif value < 0.6:
        col = '\033[33m'
    else:
        col = '\033[31m'

    return col + "█" * filled + "\033[90m" + "░" * empty + "\033[0m"


def format_deception_label(score):
    """Return a human-readable deception label and ANSI color code for a score."""
    if score < 0.25:
        return "TRUTHFUL", '\033[32m'
    elif score < 0.45:
        return "LIKELY TRUTHFUL", '\033[32m'
    elif score < 0.55:
        return "INCONCLUSIVE", '\033[33m'
    elif score < 0.75:
        return "LIKELY DECEPTIVE", '\033[31m'
    else:
        return "DECEPTIVE", '\033[31m'


def print_deception_result(result, quiet=False):
    """Print the polygraph analysis result with visual flair.

    Args:
        result: dict from PolygraphEngine.analyze()
        quiet: if True, skip the animation delay
    """
    score = result['deception_score']
    confidence = result['confidence']

    if not quiet:
        print()
        print("─" * 70)
        print()

    # Polygraph trace
    scores = [score]
    trace = draw_polygraph_trace(scores, width=60, height=6)
    cyan(); dim()
    for line in trace:
        print("    " + line)
    reset()
    print()

    # Verdict
    verdict, color = format_deception_label(score)
    if score < 0.35 or score >= 0.75:
        bold()
    print(color + center(f"⬤  VERDICT: {verdict}  ⬤"))
    reset()
    print()

    # Score bars
    def print_bar(label, val, width=50):
        bar = draw_bar(val, width)
        pct = f"{val * 100:.0f}%"
        print(f"  {label:<20} {bar} {pct}")

    print_bar("Deception Level", score)
    print_bar("Confidence", confidence)

    # Stress index if available
    if 'metric_zscores' in result:
        stress_z = result['metric_zscores'].get('stress_index')
        if stress_z is not None:
            stress_val = min(max(abs(stress_z) / 3.0, 0), 1)
            print_bar("Stress Indicator", stress_val)
    print()

    # Indicators
    if result['indicators']:
        magenta(); bold()
        print("  ⚡ Key Indicators:")
        reset()
        sorted_indicators = sorted(result['indicators'], key=lambda x: -x[1])
        for desc, sc, z in sorted_indicators[:5]:
            intensity = "▓▓▓" if sc > 0.6 else "▓▓░" if sc > 0.4 else "▓░░"
            bar_color = '\033[31m' if sc > 0.6 else '\033[33m' if sc > 0.4 else '\033[32m'
            print(f"    {bar_color}{intensity}\033[0m {desc} (z={z:+.2f})")
    print()

    # Detailed breakdown
    dim()
    print("  ┌─ Detailed Analysis ─────────────────────────────────────┐")
    if score < 0.35:
        print("  │  Response patterns closely match baseline truthful       │")
        print("  │  behavior. Consistent rhythm, natural pacing, and       │")
        print("  │  typical correction patterns observed.                  │")
    elif score < 0.55:
        print("  │  Some deviation from baseline detected, but within      │")
        print("  │  normal variation range. Cannot conclusively determine   │")
        print("  │  truthfulness from keystroke data alone.                 │")
    elif score < 0.75:
        print("  │  Notable deviations from baseline detected. Irregular   │")
        print("  │  rhythm, increased pauses, or atypical correction       │")
        print("  │  patterns suggest possible deception.                    │")
    else:
        print("  │  Significant deviations from baseline truth pattern.    │")
        print("  │  Erratic rhythm, extended pauses, and unusual           │")
        print("  │  correction patterns strongly suggest deception.        │")
    print("  └──────────────────────────────────────────────────────────┘")
    reset()
    print()


# ─── Input Collection ───────────────────────────────────────────────────────

def get_typed_input(prompt_text, quiet=False):
    """Collect typed input with keystroke timing using raw terminal mode.

    Falls back to timed input() if termios is unavailable.

    Args:
        prompt_text: The question to display
        quiet: if True, suppress some output

    Returns:
        (line, analyzer) tuple, or (None, analyzer) on cancellation
    """
    analyzer = KeystrokeAnalyzer()

    cyan(); bold()
    print(f"  {prompt_text}")
    reset()
    print("  ", end="", flush=True)

    analyzer.start()

    line = ""
    try:
        import termios, tty
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            tty.setcbreak(sys.stdin.fileno())

            while True:
                ch = sys.stdin.read(1)

                if ch == '\n' or ch == '\r':
                    break
                elif ch == '\x7f' or ch == '\x08':  # backspace
                    if line:
                        line = line[:-1]
                        analyzer.record_backspace()
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif ch == '\x03':  # Ctrl+C
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    raise KeyboardInterrupt
                elif ch >= ' ' or ch == '\t':
                    line += ch
                    analyzer.record_key(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    except (ImportError, AttributeError):
        # Fallback for environments without termios (e.g., Windows, pipes)
        line, analyzer = _get_typed_input_fallback(prompt_text, quiet)
        return line, analyzer

    except KeyboardInterrupt:
        print()
        return None, analyzer

    print()
    analyzer.finish()
    return line, analyzer


def get_typed_input_simple(prompt_text, quiet=False):
    """Simpler input collection using timed input().

    Since we can't capture individual keystrokes in this mode, we simulate
    keystroke timing by distributing keys evenly across the total response time.

    Args:
        prompt_text: The question to display
        quiet: if True, suppress some output

    Returns:
        (line, analyzer) tuple, or (None, analyzer) on cancellation
    """
    analyzer = KeystrokeAnalyzer()

    cyan(); bold()
    print(f"  {prompt_text}")
    reset()
    sys.stdout.write("  > ")
    sys.stdout.flush()

    analyzer.start()
    start = time.time()

    try:
        line = input()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, analyzer

    # Simulate keystroke timing based on response length and total time
    total_time = time.time() - start
    per_char = total_time / max(len(line), 1)

    # Add slight natural variation to simulated keystroke timings
    for i, ch in enumerate(line):
        # Simulate slightly uneven keystroke timing
        variation = random.gauss(0, per_char * 0.1)
        t = start + per_char * (i + 1) + variation
        analyzer.key_times.append((t, ch))
        analyzer.total_chars += 1
        analyzer.response += ch

    analyzer.finish()
    return line, analyzer


def _get_typed_input_fallback(prompt_text, quiet=False):
    """Fallback input for environments without termios."""
    analyzer = KeystrokeAnalyzer()
    analyzer.start()
    start = time.time()

    try:
        line = input()
    except (EOFError, KeyboardInterrupt):
        return None, analyzer

    total_time = time.time() - start
    per_char = total_time / max(len(line), 1)

    for i, ch in enumerate(line):
        t = start + per_char * (i + 1)
        analyzer.key_times.append((t, ch))
        analyzer.total_chars += 1
        analyzer.response += ch

    analyzer.finish()
    return line, analyzer


# ─── Main Exam Flow ─────────────────────────────────────────────────────────

def run_polygraph(num_questions=6, num_baseline=4, quiet=False, json_output=False):
    """Main polygraph exam flow.

    Args:
        num_questions: number of exam questions (1–10)
        num_baseline: number of baseline calibration questions (2–6)
        quiet: if True, reduce delays and animations
        json_output: if True, collect results and return as JSON dict
    """
    num_questions = max(1, min(10, num_questions))
    num_baseline = max(2, min(6, num_baseline))

    if not json_output:
        print_banner()

        yellow(); bold()
        print(center("⚠  TRUTH VERIFICATION PROTOCOL  ⚠"))
        reset()
        print()
        print(center("This system analyzes keystroke dynamics to detect"))
        print(center("physiological stress patterns associated with deception."))
        print()
        dim()
        print(center("Answer each question naturally. Type your response and"))
        print(center("press Enter. The system will establish a baseline using"))
        print(center("simple factual questions before the real exam begins."))
        reset()
        print()
        bold()
        print(center("Press Enter to begin the examination..."))
        reset()
        input()

    engine = PolygraphEngine()

    # ── Phase 1: Baseline ──
    if not json_output:
        clear()
        cyan(); bold()
        print(center("╔════════════════════════════════════════════════════════╗"))
        print(center("║         PHASE 1: BASELINE CALIBRATION                 ║"))
        print(center("╚════════════════════════════════════════════════════════╝"))
        reset()
        print()
        dim()
        print(center("Answer these questions naturally and truthfully."))
        print(center("This establishes your typing baseline for comparison."))
        reset()
        print()

    baseline_questions = random.sample(BASELINE_QUESTIONS, min(num_baseline, len(BASELINE_QUESTIONS)))

    for i, question in enumerate(baseline_questions):
        if not json_output:
            print()
            yellow()
            print(f"  Calibration Question {i + 1}/{len(baseline_questions)}")
            reset()

        line, analyzer = get_typed_input_simple(question, quiet=quiet)
        if line is None:
            if not json_output:
                print("\n  Examination terminated.")
            return None

        metrics = analyzer.get_metrics()
        if metrics and metrics['response_length'] >= 1:
            engine.add_baseline(metrics)
            if not json_output:
                green(); print("  ✓ Response recorded"); reset()
        else:
            if not json_output:
                red(); print("  ✗ Response too short, skipping"); reset()

    # Brief calibration analysis
    if not json_output:
        print()
        dim()
        print(center("Analyzing baseline patterns..."))
        reset()
        time.sleep(0.5 if quiet else 1.5)

    baseline_stats = engine.get_baseline_stats()
    if baseline_stats and not json_output:
        print()
        green()
        print(center(f"✓ Baseline established from {len(engine.baseline_metrics)} samples"))
        avg_speed = baseline_stats.get('typing_speed_cps', {}).get('mean', 0)
        avg_rhythm = baseline_stats.get('rhythm_consistency', {}).get('mean', 0)
        reset(); dim()
        print(center(f"  Average typing speed: {avg_speed:.1f} chars/sec"))
        print(center(f"  Rhythm consistency: {avg_rhythm:.1%}"))
        reset()
    elif not baseline_stats and not json_output:
        print()
        red()
        print(center("⚠ Insufficient baseline data. Results may be unreliable."))
        reset()

    if not json_output:
        print()
        bold()
        print(center("Press Enter to begin the examination..."))
        reset()
        input()

    # ── Phase 2: Examination ──
    if not json_output:
        clear()
        cyan(); bold()
        print(center("╔════════════════════════════════════════════════════════╗"))
        print(center("║            PHASE 2: TRUTH EXAMINATION                 ║"))
        print(center("╚════════════════════════════════════════════════════════╝"))
        reset()
        print()
        red(); bold()
        print(center("⚠  You are under examination. Answer truthfully.  ⚠"))
        reset()
        print()

    exam_questions = random.sample(EXAM_QUESTIONS, min(num_questions, len(EXAM_QUESTIONS)))
    results = []

    for i, (question, truth_prob) in enumerate(exam_questions):
        if not json_output:
            print()
            magenta(); bold()
            print(f"  Question {i + 1}/{len(exam_questions)}")
            reset()

        line, analyzer = get_typed_input_simple(question, quiet=quiet)
        if line is None:
            if not json_output:
                print("\n  Examination terminated.")
            break

        metrics = analyzer.get_metrics()
        if metrics and metrics['response_length'] >= 1:
            result = engine.analyze(metrics)
            result['question'] = question
            result['response'] = line
            result['truth_probability'] = truth_prob
            result['response_length'] = metrics['response_length']
            result['typing_speed'] = metrics['typing_speed_cps']
            results.append(result)
            engine.add_result(result)

            # Brief processing animation
            if not json_output:
                dim()
                print(center("Analyzing response patterns..."))
                reset()
                time.sleep(0.3 if quiet else 0.8 + random.random() * 0.7)
                print_deception_result(result, quiet=quiet)

            # Small delay between questions
            if not json_output and i < len(exam_questions) - 1:
                dim()
                print(center("Press Enter for next question..."))
                reset()
                input()
                clear()
                cyan(); bold()
                print(center("╔════════════════════════════════════════════════════════╗"))
                print(center("║            PHASE 2: TRUTH EXAMINATION                 ║"))
                print(center("╚════════════════════════════════════════════════════════╝"))
                reset()
                print()
        else:
            if not json_output:
                red(); print("  ✗ Response too short, skipping"); reset()

    # ── Phase 3: Final Report ──
    if not results:
        if not json_output:
            print("\n  No valid responses collected. Examination inconclusive.")
        return None

    # JSON output mode
    if json_output:
        json_data = {
            'version': __version__,
            'baseline_samples': len(engine.baseline_metrics),
            'results': [],
        }
        if baseline_stats:
            json_data['baseline'] = {
                k: {'mean': v['mean'], 'std': v['std']}
                for k, v in baseline_stats.items()
            }
        for r in results:
            json_data['results'].append({
                'question': r['question'],
                'response': r['response'],
                'response_length': r.get('response_length', 0),
                'typing_speed_cps': r.get('typing_speed', 0),
                'deception_score': round(r['deception_score'], 4),
                'confidence': round(r['confidence'], 4),
                'verdict': format_deception_label(r['deception_score'])[0],
                'truth_probability': r.get('truth_probability', 0),
                'indicators': [
                    {'description': desc, 'score': round(sc, 4), 'z_score': round(z, 4)}
                    for desc, sc, z in r['indicators']
                ],
                'metric_zscores': {
                    k: round(v, 4) for k, v in r.get('metric_zscores', {}).items()
                },
            })

        avg_deception = statistics.mean([r['deception_score'] for r in results])
        json_data['overall_deception_score'] = round(avg_deception, 4)
        json_data['overall_verdict'] = format_deception_label(avg_deception)[0]

        return json_data

    # ── Display final report ──
    clear()
    cyan(); bold()
    print(center("╔════════════════════════════════════════════════════════╗"))
    print(center("║           EXAMINATION COMPLETE — REPORT               ║"))
    print(center("╚════════════════════════════════════════════════════════╝"))
    reset()
    print()

    # Overall score
    avg_deception = statistics.mean([r['deception_score'] for r in results])
    avg_confidence = statistics.mean([r['confidence'] for r in results])

    # Polygraph trace with all scores
    all_scores = [r['deception_score'] for r in results]
    trace = draw_polygraph_trace(all_scores, width=60, height=8)
    cyan(); dim()
    for line in trace:
        print("    " + line)
    reset()
    print()

    # Overall verdict
    overall, color = format_deception_label(avg_deception)
    if avg_deception < 0.35 or avg_deception >= 0.75:
        bold()
    print(color + center(f"OVERALL: {overall}"))
    reset()
    print()

    # Summary table
    print("  ┌─────┬─────────────────────────────────────┬──────────────┐")
    print("  │  #  │ Question                             │ Deception    │")
    print("  ├─────┼─────────────────────────────────────┼──────────────┤")

    for i, result in enumerate(results):
        q = result['question']
        if len(q) > 37:
            q = q[:35] + ".."
        score = result['deception_score']

        if score < 0.35:
            marker = "▓▓░░ TRUTH  "
            col = '\033[32m'
        elif score < 0.55:
            marker = "▓▓▓░ MAYBE  "
            col = '\033[33m'
        elif score < 0.75:
            marker = "▓▓▓▓ RISKY  "
            col = '\033[31m'
        else:
            marker = "▓▓▓▓▓ LIE!!!"
            col = '\033[31;1m'

        print(f"  │ {i + 1:<3} │ {q:<37} │ {col}{marker}\033[0m │")

    print("  └─────┴─────────────────────────────────────┴──────────────┘")
    print()

    # Stats
    def print_bar(label, val, width=50):
        bar = draw_bar(val, width)
        pct = f"{val * 100:.0f}%"
        print(f"  {label:<25} {bar} {pct}")

    bold()
    print("  Aggregate Scores:")
    reset()
    print_bar("Overall Deception Index", avg_deception)
    print_bar("Analysis Confidence", avg_confidence)

    # Per-question min/max
    if len(results) > 1:
        best = min(results, key=lambda r: r['deception_score'])
        worst = max(results, key=lambda r: r['deception_score'])
        print()
        dim()
        print(f"  Most truthful answer: \"{best['question'][:45]}\" (score: {best['deception_score']:.0%})")
        print(f"  Most deceptive answer: \"{worst['question'][:45]}\" (score: {worst['deception_score']:.0%})")
        reset()

    print()

    # Fun disclaimer
    dim()
    print(center("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    print()
    print(center(" DISCLAIMER: This is a simulation for entertainment purposes."))
    print(center(" Real polygraph tests are scientifically controversial and"))
    print(center(" keystroke-dynamic lie detection is not proven reliable."))
    print(center(" Don't take the results too seriously! 🙂"))
    print()
    print(center("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    reset()
    print()

    return results


# ─── Quick Mode ─────────────────────────────────────────────────────────────

def quick_mode(quiet=False, json_output=False):
    """Single-question quick examination mode.

    Args:
        quiet: if True, reduce delays
        json_output: if True, return results as JSON dict
    """
    if not json_output:
        print_banner()

        yellow()
        print(center("⚡ QUICK EXAM — Single Question Mode ⚡"))
        reset()
        print()
        dim()
        print(center("Answer one question. The system will analyze your"))
        print(center("response characteristics in real-time."))
        reset()
        print()

    question, _ = random.choice(EXAM_QUESTIONS)

    engine = PolygraphEngine()

    # Quick baseline: type the alphabet
    if not json_output:
        print()
        cyan(); bold()
        print("  Step 1: Type the alphabet (a-z) as fast as you can for calibration:")
        reset()
        print("  > ", end="", flush=True)

    start = time.time()
    try:
        alphabet_input = input()
    except (EOFError, KeyboardInterrupt):
        if not json_output:
            print("\n  Cancelled.")
        return None

    elapsed = time.time() - start
    analyzer = KeystrokeAnalyzer()
    analyzer.start()
    analyzer.key_times.append((start, None))
    per_char = elapsed / max(len(alphabet_input), 1)
    for i, ch in enumerate(alphabet_input):
        variation = random.gauss(0, per_char * 0.05)
        analyzer.key_times.append((start + per_char * (i + 1) + variation, ch))
        analyzer.total_chars += 1
        analyzer.response += ch
    analyzer.finish()

    baseline_metrics = analyzer.get_metrics()
    if baseline_metrics:
        engine.add_baseline(baseline_metrics)
        if not json_output:
            green(); print("  ✓ Baseline captured"); reset()
    else:
        if not json_output:
            red(); print("  ✗ Baseline failed"); reset()

    if not json_output:
        print()
        bold()
        print(center("Press Enter for your exam question..."))
        reset()
        input()

        clear()
        cyan(); bold()
        print(center("╔════════════════════════════════════════════════════════╗"))
        print(center("║                 EXAMINATION QUESTION                  ║"))
        print(center("╚════════════════════════════════════════════════════════╝"))
        reset()
        print()

        magenta(); bold()
        print(f"  {question}")
        reset()
        print("  > ", end="", flush=True)

    start = time.time()
    try:
        response = input()
    except (EOFError, KeyboardInterrupt):
        if not json_output:
            print("\n  Cancelled.")
        return None

    elapsed = time.time() - start

    analyzer = KeystrokeAnalyzer()
    analyzer.start()
    analyzer.key_times.append((start, None))
    per_char = elapsed / max(len(response), 1)
    for i, ch in enumerate(response):
        variation = random.gauss(0, per_char * 0.05)
        analyzer.key_times.append((start + per_char * (i + 1) + variation, ch))
        analyzer.total_chars += 1
        analyzer.response += ch
    analyzer.finish()

    metrics = analyzer.get_metrics()
    if metrics:
        result = engine.analyze(metrics)
        result['question'] = question
        result['response'] = response
        result['response_length'] = metrics['response_length']
        result['typing_speed'] = metrics['typing_speed_cps']
        result['truth_probability'] = _

        if json_output:
            json_data = {
                'version': __version__,
                'mode': 'quick',
                'baseline_samples': len(engine.baseline_metrics),
                'results': [{
                    'question': question,
                    'response': response,
                    'response_length': result.get('response_length', 0),
                    'typing_speed_cps': result.get('typing_speed', 0),
                    'deception_score': round(result['deception_score'], 4),
                    'confidence': round(result['confidence'], 4),
                    'verdict': format_deception_label(result['deception_score'])[0],
                    'indicators': [
                        {'description': desc, 'score': round(sc, 4), 'z_score': round(z, 4)}
                        for desc, sc, z in result['indicators']
                    ],
                    'metric_zscores': {
                        k: round(v, 4) for k, v in result.get('metric_zscores', {}).items()
                    },
                }],
            }
            return json_data

        dim()
        print(center("Analyzing..."))
        reset()
        time.sleep(0.5 if quiet else 1.5)

        print_deception_result(result, quiet=quiet)

    if not json_output:
        dim()
        print(center("Press Enter to exit..."))
        reset()
        input()

    return result


# ─── Entry Point ────────────────────────────────────────────────────────────

def main():
    """Parse CLI arguments and launch the polygraph simulator."""
    parser = argparse.ArgumentParser(
        description="Terminal Polygraph Simulator — Interactive Lie Detection via Keystroke Dynamics",
        epilog="Example: python3 polygraph.py --quick --seed 42"
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--quick', '-q', action='store_true',
                        help='Quick mode: single question examination')
    parser.add_argument('--questions', '-n', type=int, default=6,
                        help='Number of exam questions (default: 6, range: 1-10)')
    parser.add_argument('--baseline', '-b', type=int, default=4,
                        help='Number of baseline calibration questions (default: 4, range: 2-6)')
    parser.add_argument('--seed', '-s', type=int, default=None,
                        help='Random seed for reproducible question selection')
    parser.add_argument('--quiet', action='store_true',
                        help='Reduce delays and animations for faster experience')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output results as JSON (for programmatic use)')

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # Clamp question counts to valid ranges
    args.questions = max(1, min(10, args.questions))
    args.baseline = max(2, min(6, args.baseline))

    try:
        if args.quick:
            result = quick_mode(quiet=args.quiet, json_output=args.json)
            if args.json and result:
                print(json.dumps(result, indent=2))
        else:
            result = run_polygraph(
                num_questions=args.questions,
                num_baseline=args.baseline,
                quiet=args.quiet,
                json_output=args.json,
            )
            if args.json and result:
                print(json.dumps(result, indent=2))
    except KeyboardInterrupt:
        print("\n\n  Examination terminated by subject. 🚪")
        sys.exit(0)


if __name__ == '__main__':
    main()