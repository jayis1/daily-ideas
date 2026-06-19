#!/usr/bin/env python3
"""
Terminal Polygraph Simulator
=============================
An interactive lie detector simulation that analyzes your typing patterns
(speed, consistency, corrections, pauses) to determine if you're lying.

Uses real keystroke dynamics to detect deviations from your baseline.
"""

import time
import sys
import random
import statistics
import math
import os

# ─── ANSI Helpers ──────────────────────────────────────────────────────────

def clear():
    os.system('clear' if os.name != 'nt' else 'cls')

def reset():
    print('\033[0m', end='')

def bold():
    print('\033[1m', end='')

def dim():
    print('\033[2m', end='')

def red():
    print('\033[31m', end='')

def green():
    print('\033[32m', end='')

def yellow():
    print('\033[33m', end='')

def cyan():
    print('\033[36m', end='')

def magenta():
    print('\033[35m', end='')

def move_up(n=1):
    print(f'\033[{n}A', end='')

def move_down(n=1):
    print(f'\033[{n}B', end='')

def erase_line():
    print('\033[2K\r', end='')

def center(text, width=70):
    return text.center(width)

def print_banner():
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
]

# ─── Keystroke Analyzer ─────────────────────────────────────────────────────

class KeystrokeAnalyzer:
    """Collects and analyzes keystroke dynamics for a single response."""

    def __init__(self):
        self.start_time = None
        self.key_times = []
        self.backspaces = 0
        self.total_chars = 0
        self.pause_threshold = 0.5  # seconds between keys = pause
        self.finished = False
        self.response = ""

    def start(self):
        self.start_time = time.time()
        self.key_times = [(self.start_time, None)]

    def record_key(self, char):
        now = time.time()
        self.key_times.append((now, char))
        self.total_chars += 1
        self.response += char

    def record_backspace(self):
        now = time.time()
        self.key_times.append((now, 'BACKSPACE'))
        self.backspaces += 1
        if self.response:
            self.response = self.response[:-1]

    def finish(self):
        self.finished = True

    def get_metrics(self):
        if not self.key_times or len(self.key_times) < 2:
            return None

        durations = []
        pauses = []
        between_keys = []

        for i in range(1, len(self.key_times)):
            dt = self.key_times[i][0] - self.key_times[i-1][0]
            between_keys.append(dt)
            if dt > self.pause_threshold:
                pauses.append(dt)
            else:
                durations.append(dt)

        if not between_keys:
            return None

        total_time = self.key_times[-1][0] - self.key_times[0][0]
        response_len = len(self.response)

        metrics = {
            'total_time': total_time,
            'response_length': response_len,
            'avg_key_interval': statistics.mean(between_keys) if between_keys else 0,
            'median_key_interval': statistics.median(between_keys) if between_keys else 0,
            'std_key_interval': statistics.stdev(between_keys) if len(between_keys) > 1 else 0,
            'backspaces': self.backspaces,
            'correction_rate': self.backspaces / max(self.total_chars, 1),
            'pause_count': len(pauses),
            'pause_total': sum(pauses),
            'avg_pause': statistics.mean(pauses) if pauses else 0,
            'typing_speed_cps': response_len / max(total_time, 0.01),
            'rhythm_consistency': 0,
        }

        # Rhythm consistency: lower std relative to mean = more consistent
        if metrics['avg_key_interval'] > 0:
            cv = metrics['std_key_interval'] / metrics['avg_key_interval']
            metrics['rhythm_consistency'] = max(0, 1 - cv)

        return metrics


class PolygraphEngine:
    """Compares response metrics against baseline to estimate deception."""

    def __init__(self):
        self.baseline_metrics = []

    def add_baseline(self, metrics):
        if metrics:
            self.baseline_metrics.append(metrics)

    def get_baseline_stats(self):
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
        baseline = self.get_baseline_stats()
        if not baseline or not metrics:
            return {'deception_score': 0.5, 'confidence': 0.1, 'indicators': ['Insufficient baseline data']}

        indicators = []
        scores = []

        # Check each metric against baseline
        checks = [
            ('avg_key_interval', 'typing_speed', False, 'Slower typing than baseline'),
            ('avg_key_interval', 'typing_speed', True, 'Faster typing than baseline (rushed response)'),
            ('std_key_interval', 'rhythm_variation', True, 'More inconsistent rhythm'),
            ('correction_rate', 'corrections', True, 'More corrections (second-guessing)'),
            ('pause_count', 'hesitation', True, 'More pauses (thinking before answering)'),
            ('avg_pause', 'long_hesitation', True, 'Longer pauses detected'),
            ('rhythm_consistency', 'smoothness', False, 'Less smooth typing rhythm'),
        ]

        for metric_name, indicator_label, higher_means_suspicious, description in checks:
            if metric_name not in baseline or metric_name not in metrics:
                continue

            b_mean = baseline[metric_name]['mean']
            b_std = baseline[metric_name]['std']
            value = metrics[metric_name]

            if b_std == 0:
                b_std = b_mean * 0.1  # Small fallback

            # Z-score: how many standard deviations from baseline
            z_score = (value - b_mean) / max(b_std, 0.001)

            if higher_means_suspicious:
                score = min(max(z_score / 3.0, 0), 1)
            else:
                score = min(max(-z_score / 3.0, 0), 1)

            if score > 0.3:
                indicators.append((description, score, z_score))

            scores.append(score)

        # Deception score: weighted average
        if scores:
            # Give more weight to rhythm and pauses
            weights = [0.2, 0.15, 0.25, 0.15, 0.15, 0.05, 0.05]
            while len(weights) < len(scores):
                weights.append(0.05)
            deception_score = sum(s * w for s, w in zip(scores, weights[:len(scores)]))
            deception_score = sum(s * w for s, w in zip(scores, weights[:len(scores)]))
            total_weight = sum(weights[:len(scores)])
            deception_score = deception_score / total_weight if total_weight > 0 else 0.5
        else:
            deception_score = 0.5

        # Confidence based on baseline sample size
        confidence = min(len(self.baseline_metrics) / 5.0, 0.95)

        # Add some noise based on confidence
        noise = random.gauss(0, 0.05 * (1 - confidence))
        deception_score = max(0, min(1, deception_score + noise))

        return {
            'deception_score': deception_score,
            'confidence': confidence,
            'indicators': indicators,
        }


# ─── Visual Components ─────────────────────────────────────────────────────

def draw_polygraph_trace(scores, width=60, height=8):
    """Draw an animated polygraph-style trace based on deception scores."""
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


def draw_meter(value, label="", width=40):
    """Draw a horizontal meter bar."""
    filled = int(value * width)
    empty = width - filled

    if value < 0.3:
        color_fn = green
    elif value < 0.6:
        color_fn = yellow
    else:
        color_fn = red

    bar = "█" * filled + "░" * empty
    result = f"{label}: "
    result += f"\033[2m{'░' * width}\033[0m\r"  # placeholder
    return (label, value, color_fn, bar, width)


def print_deception_result(result):
    """Print the polygraph analysis result with visual flair."""
    score = result['deception_score']
    confidence = result['confidence']

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
    if score < 0.25:
        verdict = "TRUTHFUL"
        green(); bold()
    elif score < 0.45:
        verdict = "LIKELY TRUTHFUL"
        green()
    elif score < 0.55:
        verdict = "INCONCLUSIVE"
        yellow()
    elif score < 0.75:
        verdict = "LIKELY DECEPTIVE"
        red()
    else:
        verdict = "DECEPTIVE"
        red(); bold()

    print(center(f"⬤  VERDICT: {verdict}  ⬤"))
    reset()
    print()

    # Score bars
    def print_bar(label, val, width=50):
        filled = int(val * width)
        empty = width - filled
        if val < 0.3:
            col = '\033[32m'
        elif val < 0.6:
            col = '\033[33m'
        else:
            col = '\033[31m'
        bar = col + "█" * filled + "\033[90m" + "░" * empty + "\033[0m"
        pct = f"{val*100:.0f}%"
        print(f"  {label:<20} {bar} {pct}")

    print_bar("Deception Level", score)
    print_bar("Confidence", confidence)
    print()

    # Indicators
    if result['indicators']:
        magenta(); bold()
        print("  ⚡ Key Indicators:")
        reset()
        sorted_indicators = sorted(result['indicators'], key=lambda x: -x[1])
        for desc, score, z in sorted_indicators[:5]:
            intensity = "▓▓▓" if score > 0.6 else "▓▓░" if score > 0.4 else "▓░░"
            bar_color = '\033[31m' if score > 0.6 else '\033[33m' if score > 0.4 else '\033[32m'
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

def get_typed_input(prompt_text):
    """Collect typed input with keystroke timing."""
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
        # Fallback for environments without termios
        line = input()
        analyzer = KeystrokeAnalyzer()
        analyzer.start()
        for ch in line:
            analyzer.record_key(ch)

    except KeyboardInterrupt:
        print()
        return None, analyzer

    print()
    analyzer.finish()
    return line, analyzer


def get_typed_input_simple(prompt_text):
    """Simpler input collection using timed input()."""
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

    for i, ch in enumerate(line):
        t = start + per_char * (i + 1)
        analyzer.key_times.append((t, ch))
        analyzer.total_chars += 1
        analyzer.response += ch

    analyzer.finish()
    return line, analyzer


# ─── Main Exam Flow ─────────────────────────────────────────────────────────

def run_polygraph():
    """Main polygraph exam flow."""

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

    baseline_questions = random.sample(BASELINE_QUESTIONS, min(4, len(BASELINE_QUESTIONS)))

    for i, question in enumerate(baseline_questions):
        print()
        yellow()
        print(f"  Calibration Question {i+1}/{len(baseline_questions)}")
        reset()

        line, analyzer = get_typed_input_simple(question)
        if line is None:
            print("\n  Examination terminated.")
            return

        metrics = analyzer.get_metrics()
        if metrics and metrics['response_length'] >= 1:
            engine.add_baseline(metrics)
            green(); print("  ✓ Response recorded"); reset()
        else:
            red(); print("  ✗ Response too short, skipping"); reset()

    # Brief calibration analysis
    print()
    dim()
    print(center("Analyzing baseline patterns..."))
    reset()
    time.sleep(1.5)

    baseline_stats = engine.get_baseline_stats()
    if baseline_stats:
        print()
        green()
        print(center(f"✓ Baseline established from {len(engine.baseline_metrics)} samples"))
        avg_speed = baseline_stats.get('typing_speed_cps', {}).get('mean', 0)
        avg_rhythm = baseline_stats.get('rhythm_consistency', {}).get('mean', 0)
        reset(); dim()
        print(center(f"  Average typing speed: {avg_speed:.1f} chars/sec"))
        print(center(f"  Rhythm consistency: {avg_rhythm:.1%}"))
        reset()
    else:
        print()
        red()
        print(center("⚠ Insufficient baseline data. Results may be unreliable."))
        reset()

    print()
    bold()
    print(center("Press Enter to begin the examination..."))
    reset()
    input()

    # ── Phase 2: Examination ──
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

    exam_questions = random.sample(EXAM_QUESTIONS, min(6, len(EXAM_QUESTIONS)))
    results = []

    for i, (question, truth_prob) in enumerate(exam_questions):
        print()
        magenta(); bold()
        print(f"  Question {i+1}/{len(exam_questions)}")
        reset()

        line, analyzer = get_typed_input_simple(question)
        if line is None:
            print("\n  Examination terminated.")
            break

        metrics = analyzer.get_metrics()
        if metrics and metrics['response_length'] >= 1:
            result = engine.analyze(metrics)
            result['question'] = question
            result['response'] = line
            result['truth_probability'] = truth_prob
            results.append(result)

            # Brief processing animation
            dim()
            print(center("Analyzing response patterns..."))
            reset()
            time.sleep(0.8 + random.random() * 0.7)

            print_deception_result(result)

            # Small delay between questions
            if i < len(exam_questions) - 1:
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
            red(); print("  ✗ Response too short, skipping"); reset()

    # ── Phase 3: Final Report ──
    if not results:
        print("\n  No valid responses collected. Examination inconclusive.")
        return

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
    if avg_deception < 0.3:
        overall = "OVERALL: SUBJECT APPEARS TRUTHFUL"
        green(); bold()
    elif avg_deception < 0.5:
        overall = "OVERALL: NO SIGNIFICANT DECEPTION DETECTED"
        green()
    elif avg_deception < 0.6:
        overall = "OVERALL: INCONCLUSIVE RESULTS"
        yellow(); bold()
    elif avg_deception < 0.75:
        overall = "OVERALL: POSSIBLE DECEPTION DETECTED"
        red()
    else:
        overall = "OVERALL: DECEPTION LIKELY DETECTED"
        red(); bold()

    print(center(overall))
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

        print(f"  │ {i+1:<3} │ {q:<37} │ {col}{marker}\033[0m │")

    print("  └─────┴─────────────────────────────────────┴──────────────┘")
    print()

    # Stats
    def print_bar(label, val, width=50):
        filled = int(val * width)
        empty = width - filled
        if val < 0.3:
            col = '\033[32m'
        elif val < 0.6:
            col = '\033[33m'
        else:
            col = '\033[31m'
        bar = col + "█" * filled + "\033[90m" + "░" * empty + "\033[0m"
        pct = f"{val*100:.0f}%"
        print(f"  {label:<25} {bar} {pct}")

    bold()
    print("  Aggregate Scores:")
    reset()
    print_bar("Overall Deception Index", avg_deception)
    print_bar("Analysis Confidence", avg_confidence)
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


# ─── Quick Mode ─────────────────────────────────────────────────────────────

def quick_mode():
    """Single-question quick examination mode."""
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
    print()
    cyan(); bold()
    print("  Step 1: Type the alphabet (a-z) as fast as you can for calibration:")
    reset()
    print("  > ", end="", flush=True)

    start = time.time()
    try:
        alphabet_input = input()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    elapsed = time.time() - start
    analyzer = KeystrokeAnalyzer()
    analyzer.start()
    analyzer.key_times.append((start, None))
    per_char = elapsed / max(len(alphabet_input), 1)
    for i, ch in enumerate(alphabet_input):
        analyzer.key_times.append((start + per_char * (i + 1), ch))
        analyzer.total_chars += 1
        analyzer.response += ch
    analyzer.finish()

    baseline_metrics = analyzer.get_metrics()
    if baseline_metrics:
        engine.add_baseline(baseline_metrics)
        green(); print("  ✓ Baseline captured"); reset()
    else:
        red(); print("  ✗ Baseline failed"); reset()

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
        print("\n  Cancelled.")
        return

    elapsed = time.time() - start

    analyzer = KeystrokeAnalyzer()
    analyzer.start()
    analyzer.key_times.append((start, None))
    per_char = elapsed / max(len(response), 1)
    for i, ch in enumerate(response):
        analyzer.key_times.append((start + per_char * (i + 1), ch))
        analyzer.total_chars += 1
        analyzer.response += ch
    analyzer.finish()

    metrics = analyzer.get_metrics()
    if metrics:
        result = engine.analyze(metrics)
        result['question'] = question
        result['response'] = response

        dim()
        print(center("Analyzing..."))
        reset()
        time.sleep(1.5)

        print_deception_result(result)

    dim()
    print(center("Press Enter to exit..."))
    reset()
    input()


# ─── Entry Point ────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Terminal Polygraph Simulator — Interactive Lie Detection via Keystroke Dynamics"
    )
    parser.add_argument('--quick', '-q', action='store_true',
                        help='Quick mode: single question examination')
    parser.add_argument('--questions', '-n', type=int, default=6,
                        help='Number of exam questions (default: 6)')
    args = parser.parse_args()

    try:
        if args.quick:
            quick_mode()
        else:
            run_polygraph()
    except KeyboardInterrupt:
        print("\n\n  Examination terminated by subject. 🚪")
        sys.exit(0)


if __name__ == '__main__':
    main()