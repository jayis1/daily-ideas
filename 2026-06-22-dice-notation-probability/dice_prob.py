#!/usr/bin/env python3
"""
Dice Notation Roller & Probability Analyzer

Parses standard and advanced dice notation, rolls dice, computes exact
probability distributions, and renders ASCII histograms.

Supported notation:
  NdS           - roll N S-sided dice, sum them
  NdS+M         - add modifier M
  NdS-M         - subtract modifier M
  NdSkhK        - keep highest K dice
  NdSklK        - keep lowest K dice
  NdSdhK        - drop highest K dice
  NdSdlK        - drop lowest K dice
  NdS>R         - count dice showing > R
  NdS>=R        - count dice showing >= R
  NdS<R         - count dice showing < R
  NdS<=R        - count dice showing <= R

Examples:
  2d6           → sum of 2 six-sided dice
  4d6kh3        → roll 4d6, keep highest 3 (D&D stat rolling)
  2d6+3         → roll 2d6, add 3
  10d6>=5       → count how many of 10d6 show 5 or more
"""

import argparse
import re
import sys
import itertools
import random
from collections import Counter
from fractions import Fraction


# ── Dice notation parser ─────────────────────────────────────────────────

_DICE_RE = re.compile(
    r'^'
    r'(?P<count>\d+)d(?P<sides>\d+)'
    r'(?:kh(?P<keep_hi>\d+)|kl(?P<keep_lo>\d+)'
    r'|dh(?P<drop_hi>\d+)|dl(?P<drop_lo>\d+)'
    r'|(?:>(?P<gt>\d+)|>=(?P<gte>\d+)|<(?P<lt>\d+)|<=(?P<lte>\d+)))?'
    r'(?P<mod_sign>[+-])?(?P<mod_val>\d+)?'
    r'$'
)


def parse_notation(notation: str):
    """Parse a dice notation string into a dict of components.

    Returns dict with keys: count, sides, mode, mode_param, modifier
    or raises ValueError.
    """
    m = _DICE_RE.match(notation.lower().replace(' ', ''))
    if not m:
        raise ValueError(f"Invalid notation: {notation!r}")

    count = int(m.group('count'))
    sides = int(m.group('sides'))
    if count < 1:
        raise ValueError("Dice count must be ≥ 1")
    if sides < 2:
        raise ValueError("Die sides must be ≥ 2")

    mode = 'sum'
    mode_param = None

    if m.group('keep_hi'):
        mode = 'kh'
        mode_param = int(m.group('keep_hi'))
    elif m.group('keep_lo'):
        mode = 'kl'
        mode_param = int(m.group('keep_lo'))
    elif m.group('drop_hi'):
        mode = 'dh'
        mode_param = int(m.group('drop_hi'))
    elif m.group('drop_lo'):
        mode = 'dl'
        mode_param = int(m.group('drop_lo'))
    elif m.group('gt') is not None:
        mode = '>'
        mode_param = int(m.group('gt'))
    elif m.group('gte') is not None:
        mode = '>='
        mode_param = int(m.group('gte'))
    elif m.group('lt') is not None:
        mode = '<'
        mode_param = int(m.group('lt'))
    elif m.group('lte') is not None:
        mode = '<='
        mode_param = int(m.group('lte'))

    # Keep/drop validation
    if mode in ('kh', 'kl'):
        if mode_param < 1 or mode_param > count:
            raise ValueError(f"Keep count must be 1..{count}")
    if mode in ('dh', 'dl'):
        if mode_param < 0 or mode_param >= count:
            raise ValueError(f"Drop count must be 0..{count-1}")

    modifier = 0
    if m.group('mod_sign') and m.group('mod_val'):
        modifier = int(m.group('mod_val'))
        if m.group('mod_sign') == '-':
            modifier = -modifier

    return {
        'count': count,
        'sides': sides,
        'mode': mode,
        'mode_param': mode_param,
        'modifier': modifier,
    }


def format_notation(parsed: dict) -> str:
    """Reconstruct a human-readable notation string from parsed dict."""
    n, s = parsed['count'], parsed['sides']
    mode = parsed['mode']
    mp = parsed['mode_param']
    mod = parsed['modifier']

    base = f"{n}d{s}"
    if mode == 'kh':
        base += f"kh{mp}"
    elif mode == 'kl':
        base += f"kl{mp}"
    elif mode == 'dh':
        base += f"dh{mp}"
    elif mode == 'dl':
        base += f"dl{mp}"
    elif mode in ('>', '>=', '<', '<='):
        base += f"{mode}{mp}"

    if mod > 0:
        base += f"+{mod}"
    elif mod < 0:
        base += f"{mod}"

    return base


# ── Rolling ───────────────────────────────────────────────────────────────

def roll(parsed: dict, rng: random.Random = None) -> int:
    """Roll dice according to parsed notation and return the result."""
    if rng is None:
        rng = random.Random()
    n = parsed['count']
    s = parsed['sides']
    mode = parsed['mode']
    mp = parsed['mode_param']
    mod = parsed['modifier']

    dice = [rng.randint(1, s) for _ in range(n)]

    if mode == 'sum':
        result = sum(dice)
    elif mode == 'kh':
        result = sum(sorted(dice, reverse=True)[:mp])
    elif mode == 'kl':
        result = sum(sorted(dice)[:mp])
    elif mode == 'dh':
        result = sum(sorted(dice)[:n - mp])
    elif mode == 'dl':
        result = sum(sorted(dice, reverse=True)[:n - mp])
    elif mode == '>':
        result = sum(1 for d in dice if d > mp)
    elif mode == '>=':
        result = sum(1 for d in dice if d >= mp)
    elif mode == '<':
        result = sum(1 for d in dice if d < mp)
    elif mode == '<=':
        result = sum(1 for d in dice if d <= mp)
    else:
        result = sum(dice)

    result += mod
    return result


def roll_detailed(parsed: dict, rng: random.Random = None) -> dict:
    """Roll dice and return detailed results (individual dice, etc.)."""
    if rng is None:
        rng = random.Random()
    n = parsed['count']
    s = parsed['sides']
    mode = parsed['mode']
    mp = parsed['mode_param']
    mod = parsed['modifier']

    dice = [rng.randint(1, s) for _ in range(n)]
    kept = list(dice)
    dropped = []

    if mode == 'kh':
        sorted_dice = sorted(enumerate(dice), key=lambda x: x[1], reverse=True)
        kept_idx = set(i for i, _ in sorted_dice[:mp])
        kept = [d for i, d in enumerate(dice) if i in kept_idx]
        dropped = [d for i, d in enumerate(dice) if i not in kept_idx]
    elif mode == 'kl':
        sorted_dice = sorted(enumerate(dice), key=lambda x: x[1])
        kept_idx = set(i for i, _ in sorted_dice[:mp])
        kept = [d for i, d in enumerate(dice) if i in kept_idx]
        dropped = [d for i, d in enumerate(dice) if i not in kept_idx]
    elif mode == 'dh':
        sorted_dice = sorted(enumerate(dice), key=lambda x: x[1], reverse=True)
        dropped_idx = set(i for i, _ in sorted_dice[:mp])
        kept = [d for i, d in enumerate(dice) if i not in dropped_idx]
        dropped = [d for i, d in enumerate(dice) if i in dropped_idx]
    elif mode == 'dl':
        sorted_dice = sorted(enumerate(dice), key=lambda x: x[1])
        dropped_idx = set(i for i, _ in sorted_dice[:mp])
        kept = [d for i, d in enumerate(dice) if i not in dropped_idx]
        dropped = [d for i, d in enumerate(dice) if i in dropped_idx]

    if mode in ('>', '>=', '<', '<='):
        if mode == '>':
            kept = [d for d in dice if d > mp]
            dropped = [d for d in dice if d <= mp]
        elif mode == '>=':
            kept = [d for d in dice if d >= mp]
            dropped = [d for d in dice if d < mp]
        elif mode == '<':
            kept = [d for d in dice if d < mp]
            dropped = [d for d in dice if d >= mp]
        elif mode == '<=':
            kept = [d for d in dice if d <= mp]
            dropped = [d for d in dice if d > mp]

    # Compute result from the already-rolled dice
    if mode == 'sum':
        result = sum(dice) + mod
    elif mode == 'kh':
        result = sum(kept) + mod
    elif mode == 'kl':
        result = sum(kept) + mod
    elif mode == 'dh':
        result = sum(kept) + mod
    elif mode == 'dl':
        result = sum(kept) + mod
    elif mode in ('>', '>=', '<', '<='):
        result = len(kept) + mod
    else:
        result = sum(dice) + mod

    return {
        'notation': format_notation(parsed),
        'dice': dice,
        'kept': kept,
        'dropped': dropped,
        'modifier': mod,
        'total': result,
        'mode': mode,
    }


# ── Exact probability distribution ────────────────────────────────────────

def exact_distribution(parsed: dict) -> dict[int, Fraction]:
    """Compute exact probability distribution for a dice notation.

    Returns dict mapping outcome → Fraction probability.
    Only feasible for small dice counts (≤ ~8 dice).
    """
    n = parsed['count']
    s = parsed['sides']
    mode = parsed['mode']
    mp = parsed['mode_param']
    mod = parsed['modifier']

    if n > 8:
        raise ValueError(
            f"Exact distribution not feasible for {n} dice (max 8). "
            "Use --monte-carlo instead."
        )

    total_outcomes = s ** n
    dist: dict[int, int] = Counter()

    # Generate all possible outcomes
    for rolls in itertools.product(range(1, s + 1), repeat=n):
        if mode == 'sum':
            val = sum(rolls)
        elif mode == 'kh':
            val = sum(sorted(rolls, reverse=True)[:mp])
        elif mode == 'kl':
            val = sum(sorted(rolls)[:mp])
        elif mode == 'dh':
            val = sum(sorted(rolls)[:n - mp])
        elif mode == 'dl':
            val = sum(sorted(rolls, reverse=True)[:n - mp])
        elif mode == '>':
            val = sum(1 for d in rolls if d > mp)
        elif mode == '>=':
            val = sum(1 for d in rolls if d >= mp)
        elif mode == '<':
            val = sum(1 for d in rolls if d < mp)
        elif mode == '<=':
            val = sum(1 for d in rolls if d <= mp)
        else:
            val = sum(rolls)

        dist[val + mod] += 1

    return {k: Fraction(v, total_outcomes) for k, v in sorted(dist.items())}


# ── Monte Carlo distribution ─────────────────────────────────────────────

def monte_carlo_distribution(parsed: dict, trials: int = 100_000,
                             seed=None) -> dict[int, float]:
    """Approximate the probability distribution via Monte Carlo simulation."""
    rng = random.Random(seed)
    results = Counter(roll(parsed, rng) for _ in range(trials))
    return {k: results[k] / trials for k in sorted(results)}


# ── ASCII histogram ──────────────────────────────────────────────────────

def ascii_histogram(dist: dict, width: int = 50, title: str = "",
                    show_pct: bool = True) -> str:
    """Render a probability distribution as an ASCII bar chart."""
    if not dist:
        return "(empty distribution)"

    keys = sorted(dist.keys())
    vals = [dist[k] for k in keys]
    max_val = max(vals)

    # Format value labels
    max_key_len = max(len(str(k)) for k in keys)
    val_fmt_len = 7  # e.g., " 12.34%"

    lines = []
    if title:
        lines.append(title)
        lines.append("─" * (max_key_len + 3 + width + val_fmt_len + 2))

    for k, v in zip(keys, vals):
        if isinstance(v, Fraction):
            pct = float(v) * 100
        else:
            pct = float(v) * 100

        bar_len = int(round(float(v) / float(max_val) * width)) if max_val > 0 else 0
        bar_len = max(bar_len, 1) if v > 0 else 0
        bar = "█" * bar_len

        label = str(k).rjust(max_key_len)
        pct_str = f"{pct:6.2f}%" if show_pct else ""

        lines.append(f" {label} │{bar:<{width}} {pct_str}")

    return "\n".join(lines)


# ── Statistics helpers ────────────────────────────────────────────────────

def compute_stats(dist: dict) -> dict:
    """Compute mean, stddev, min, max, median from a distribution."""
    keys = sorted(dist.keys())

    if isinstance(list(dist.values())[0], Fraction):
        mean = sum(k * dist[k] for k in keys)
        variance = sum((k - mean) ** 2 * dist[k] for k in keys)
        mean_f = float(mean)
        stddev_f = float(variance) ** 0.5
    else:
        mean_f = sum(k * dist[k] for k in keys)
        variance = sum((k - mean_f) ** 2 * dist[k] for k in keys)
        stddev_f = variance ** 0.5

    # Cumulative for median and percentiles
    total = sum(dist[k] for k in keys)
    cumulative = 0.0
    median = keys[0]
    p10 = keys[0]
    p90 = keys[0]
    for k in keys:
        cumulative += float(dist[k])
        if cumulative >= 0.5 and median == keys[0]:
            median = k
        if cumulative >= 0.1 and p10 == keys[0]:
            p10 = k
        if cumulative >= 0.9 and p90 == keys[0]:
            p90 = k

    mode_val = max(keys, key=lambda k: float(dist[k]))

    return {
        'mean': mean_f,
        'stddev': stddev_f,
        'min': keys[0],
        'max': keys[-1],
        'median': median,
        'mode': mode_val,
        'p10': p10,
        'p90': p90,
        'range': keys[-1] - keys[0],
    }


def format_stats(stats: dict) -> str:
    """Format stats dict into a nice string."""
    lines = [
        f"  Mean:    {stats['mean']:.2f}",
        f"  StdDev:  {stats['stddev']:.2f}",
        f"  Median:  {stats['median']}",
        f"  Mode:    {stats['mode']}",
        f"  Min:     {stats['min']}",
        f"  Max:     {stats['max']}",
        f"  Range:   {stats['range']}",
        f"  P10:     {stats['p10']}",
        f"  P90:     {stats['p90']}",
    ]
    return "\n".join(lines)


# ── Comparison ───────────────────────────────────────────────────────────

def compare_notations(notations: list[str], trials: int = 100_000,
                      seed: int | None = None) -> str:
    """Compare multiple dice notations with Monte Carlo side-by-side."""
    rng = random.Random(seed)
    all_results: dict[str, list[int]] = {}

    for notation in notations:
        parsed = parse_notation(notation)
        results = [roll(parsed, rng) for _ in range(trials)]
        all_results[notation] = results

    lines = []
    lines.append(f"{'Notation':<20} {'Mean':>8} {'StdDev':>8} {'Min':>5} {'Max':>5} {'Median':>7}")
    lines.append("─" * 58)

    for notation, results in all_results.items():
        mean = sum(results) / len(results)
        variance = sum((r - mean) ** 2 for r in results) / len(results)
        stddev = variance ** 0.5
        mn = min(results)
        mx = max(results)
        sr = sorted(results)
        median = sr[len(sr) // 2]
        lines.append(f"{notation:<20} {mean:>8.2f} {stddev:>8.2f} {mn:>5} {mx:>5} {median:>7}")

    # Win probabilities (which notation rolls highest)
    if len(notations) == 2:
        a, b = notations
        res_a = all_results[a]
        res_b = all_results[b]
        wins_a = sum(1 for x, y in zip(res_a, res_b) if x > y)
        wins_b = sum(1 for x, y in zip(res_a, res_b) if y > x)
        ties = sum(1 for x, y in zip(res_a, res_b) if x == y)
        lines.append("")
        lines.append(f"Head-to-head ({trials:,} trials):")
        lines.append(f"  {a} wins: {wins_a/trials*100:.1f}%")
        lines.append(f"  {b} wins: {wins_b/trials*100:.1f}%")
        lines.append(f"  Ties:    {ties/trials*100:.1f}%")

    return "\n".join(lines)


# ── Main CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🎲 Dice Notation Roller & Probability Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 2d6                    Roll 2d6
  %(prog)s 4d6kh3                 Roll 4d6 keep highest 3 (D&D stats)
  %(prog)s 2d6+3 --roll 5         Roll 2d6+3 five times
  %(prog)s 2d6 --dist             Show exact probability distribution
  %(prog)s 10d6 --dist --mc       Show exact dist + Monte Carlo overlay
  %(prog)s 4d6kh3 --stats         Show statistics
  %(prog)s 10d6>=5 --dist         Count successes distribution
  %(prog)s 2d6 3d6 --compare      Compare two notations
  %(prog)s 2d6 --dist --json      Output distribution as JSON
"""
    )
    parser.add_argument('notations', nargs='+', help='Dice notation(s) to evaluate')
    parser.add_argument('--roll', '-r', type=int, default=None,
                        help='Number of times to roll (default: 1)')
    parser.add_argument('--dist', '-d', action='store_true',
                        help='Show probability distribution histogram')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='Show statistics (mean, stddev, etc.)')
    parser.add_argument('--mc', action='store_true',
                        help='Use Monte Carlo simulation (for large dice pools)')
    parser.add_argument('--mc-trials', type=int, default=100_000,
                        help='Number of Monte Carlo trials (default: 100000)')
    parser.add_argument('--compare', '-c', action='store_true',
                        help='Compare multiple notations head-to-head')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    parser.add_argument('--json', action='store_true',
                        help='Output distribution as JSON')
    parser.add_argument('--width', type=int, default=50,
                        help='Histogram bar width (default: 50)')

    args = parser.parse_args()

    # Compare mode
    if args.compare and len(args.notations) >= 2:
        print(compare_notations(args.notations, args.mc_trials, args.seed))
        return

    # Parse all notations
    parsed_list = []
    for notation in args.notations:
        try:
            p = parse_notation(notation)
            parsed_list.append(p)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # For single notation, process it
    for parsed, notation in zip(parsed_list, args.notations):
        pretty = format_notation(parsed)

        # In JSON mode, only output JSON
        if args.json:
            if args.mc or parsed['count'] > 8:
                dist = monte_carlo_distribution(
                    parsed, args.mc_trials, args.seed)
            else:
                dist = exact_distribution(parsed)
            import json
            out = {
                'notation': pretty,
                'distribution': {
                    str(k): float(v) for k, v in dist.items()
                }
            }
            if args.stats:
                out['stats'] = compute_stats(dist)
            print(json.dumps(out, indent=2))
            continue

        print(f"\n🎲 {pretty}")
        print("═" * (len(pretty) + 3))

        # Rolling
        if args.roll is not None or (not args.dist and not args.stats):
            num_rolls = args.roll if args.roll is not None else 1
            rng = random.Random(args.seed)
            results = []
            for i in range(num_rolls):
                detail = roll_detailed(parsed, rng)
                results.append(detail)

            if num_rolls == 1:
                detail = results[0]
                dice_str = ", ".join(str(d) for d in detail['dice'])
                print(f"\n  Dice: [{dice_str}]")

                if detail['dropped']:
                    kept_str = ", ".join(str(d) for d in detail['kept'])
                    drop_str = ", ".join(str(d) for d in detail['dropped'])
                    print(f"  Kept: [{kept_str}]  Dropped: [{drop_str}]")

                if detail['mode'] in ('>', '>=', '<', '<='):
                    success_str = ", ".join(str(d) for d in detail['kept'])
                    fail_str = ", ".join(str(d) for d in detail['dropped'])
                    print(f"  Successes: [{success_str}]  Failures: [{fail_str}]")

                if detail['modifier']:
                    print(f"  Modifier: {detail['modifier']:+d}")

                print(f"\n  ══► Result: {detail['total']} ◄══")
            else:
                totals = [r['total'] for r in results]
                print(f"\n  Rolled {num_rolls} times:")
                # Show in columns
                cols = min(10, num_rolls)
                for i in range(0, num_rolls, cols):
                    chunk = totals[i:i+cols]
                    print(f"    {' '.join(f'{v:>4}' for v in chunk)}")
                if num_rolls > 1:
                    print(f"\n  Summary: min={min(totals)}  max={max(totals)}  "
                          f"avg={sum(totals)/len(totals):.1f}  "
                          f"median={sorted(totals)[len(totals)//2]}")

        # Distribution
        if args.dist or args.stats:
            try:
                if args.mc or parsed['count'] > 8:
                    dist = monte_carlo_distribution(
                        parsed, args.mc_trials, args.seed)
                    label = f"Distribution (Monte Carlo, {args.mc_trials:,} trials)"
                else:
                    dist = exact_distribution(parsed)
                    label = "Exact Distribution"

                if args.dist:
                    print(f"\n{label}:")
                    print(ascii_histogram(dist, args.width, title=""))

                if args.stats:
                    stats = compute_stats(dist)
                    print(f"\n📊 Statistics:")
                    print(format_stats(stats))

                    # Probability of key thresholds
                    if parsed['mode'] == 'sum' or parsed['mode'] in ('kh', 'kl', 'dh', 'dl'):
                        threshold = stats['mean']
                        at_or_above = sum(float(dist[k]) for k in dist if k >= threshold)
                        print(f"\n  P(≥ mean {stats['mean']:.1f}): {at_or_above*100:.1f}%")

            except ValueError as e:
                if "Exact distribution" in str(e):
                    print(f"\n  {e}")
                    print("  Try: --mc for Monte Carlo approximation")
                    sys.exit(1)
                raise


if __name__ == '__main__':
    main()