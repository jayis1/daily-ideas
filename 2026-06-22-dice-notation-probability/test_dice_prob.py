"""Tests for dice_prob.py"""
import json
import random as _r
import subprocess
import sys
import math

sys.path.insert(0, '.')
from dice_prob import (
    parse_notation, format_notation, roll, roll_detailed,
    exact_distribution, monte_carlo_distribution,
    ascii_histogram, compute_stats, compare_notations
)
from fractions import Fraction


# ── Parser tests ──────────────────────────────────────────────────────────

def test_parse_simple():
    p = parse_notation("2d6")
    assert p['count'] == 2
    assert p['sides'] == 6
    assert p['mode'] == 'sum'
    assert p['modifier'] == 0


def test_parse_modifier_plus():
    p = parse_notation("2d6+3")
    assert p['count'] == 2
    assert p['sides'] == 6
    assert p['modifier'] == 3


def test_parse_modifier_minus():
    p = parse_notation("3d8-2")
    assert p['count'] == 3
    assert p['sides'] == 8
    assert p['modifier'] == -2


def test_parse_kh():
    p = parse_notation("4d6kh3")
    assert p['count'] == 4
    assert p['sides'] == 6
    assert p['mode'] == 'kh'
    assert p['mode_param'] == 3


def test_parse_kl():
    p = parse_notation("4d6kl2")
    assert p['mode'] == 'kl'
    assert p['mode_param'] == 2


def test_parse_dh():
    p = parse_notation("4d6dh1")
    assert p['mode'] == 'dh'
    assert p['mode_param'] == 1


def test_parse_dl():
    p = parse_notation("4d6dl1")
    assert p['mode'] == 'dl'
    assert p['mode_param'] == 1


def test_parse_gt():
    p = parse_notation("10d6>4")
    assert p['mode'] == '>'
    assert p['mode_param'] == 4


def test_parse_gte():
    p = parse_notation("10d6>=5")
    assert p['mode'] == '>='
    assert p['mode_param'] == 5


def test_parse_lt():
    p = parse_notation("10d6<3")
    assert p['mode'] == '<'
    assert p['mode_param'] == 3


def test_parse_lte():
    p = parse_notation("10d6<=2")
    assert p['mode'] == '<='
    assert p['mode_param'] == 2


def test_parse_whitespace():
    p = parse_notation(" 2d6 + 3 ")
    assert p['count'] == 2
    assert p['sides'] == 6
    assert p['modifier'] == 3


def test_parse_case_insensitive():
    p = parse_notation("2D6KH1")
    assert p['count'] == 2
    assert p['sides'] == 6
    assert p['mode'] == 'kh'


def test_parse_invalid():
    try:
        parse_notation("invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_parse_sides_too_low():
    try:
        parse_notation("2d1")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_parse_count_zero():
    try:
        parse_notation("0d6")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_parse_kh_too_high():
    try:
        parse_notation("2d6kh5")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ── Format notation tests ─────────────────────────────────────────────────

def test_format_simple():
    p = parse_notation("2d6")
    assert format_notation(p) == "2d6"


def test_format_modifier():
    p = parse_notation("2d6+3")
    assert format_notation(p) == "2d6+3"


def test_format_kh():
    p = parse_notation("4d6kh3")
    assert format_notation(p) == "4d6kh3"


# ── Rolling tests ─────────────────────────────────────────────────────────

def test_roll_simple():
    rng = _r.Random(42)
    results = [roll(parse_notation("1d6"), rng) for _ in range(100)]
    assert all(1 <= r <= 6 for r in results)


def test_roll_2d6():
    rng = _r.Random(42)
    results = [roll(parse_notation("2d6"), rng) for _ in range(100)]
    assert all(2 <= r <= 12 for r in results)


def test_roll_modifier():
    rng = _r.Random(42)
    results = [roll(parse_notation("1d6+5"), rng) for _ in range(100)]
    assert all(6 <= r <= 11 for r in results)


def test_roll_modifier_neg():
    rng = _r.Random(42)
    results = [roll(parse_notation("1d6-3"), rng) for _ in range(100)]
    assert all(-2 <= r <= 3 for r in results)


def test_roll_kh():
    rng = _r.Random(42)
    # 4d6kh3: sum of highest 3 of 4d6 → range [3, 18]
    results = [roll(parse_notation("4d6kh3"), rng) for _ in range(100)]
    assert all(3 <= r <= 18 for r in results)


def test_roll_kh1():
    rng = _r.Random(42)
    # 3d6kh1: highest of 3d6 → range [1, 6]
    results = [roll(parse_notation("3d6kh1"), rng) for _ in range(100)]
    assert all(1 <= r <= 6 for r in results)


def test_roll_kl():
    rng = _r.Random(42)
    # 4d6kl1: lowest die → range [1, 6]
    results = [roll(parse_notation("4d6kl1"), rng) for _ in range(100)]
    assert all(1 <= r <= 6 for r in results)


def test_roll_dh():
    rng = _r.Random(42)
    # 4d6dh1: drop highest, sum rest → range [3, 18]
    results = [roll(parse_notation("4d6dh1"), rng) for _ in range(100)]
    assert all(3 <= r <= 18 for r in results)


def test_roll_dl():
    rng = _r.Random(42)
    # 4d6dl1: drop lowest, sum rest → range [3, 18]
    results = [roll(parse_notation("4d6dl1"), rng) for _ in range(100)]
    assert all(3 <= r <= 18 for r in results)


def test_roll_gt():
    rng = _r.Random(42)
    # 10d6>4: count successes (>4, i.e. 5 or 6) → range [0, 10]
    results = [roll(parse_notation("10d6>4"), rng) for _ in range(100)]
    assert all(0 <= r <= 10 for r in results)


def test_roll_gte():
    rng = _r.Random(42)
    results = [roll(parse_notation("10d6>=5"), rng) for _ in range(100)]
    assert all(0 <= r <= 10 for r in results)


def test_roll_lt():
    rng = _r.Random(42)
    results = [roll(parse_notation("10d6<3"), rng) for _ in range(100)]
    assert all(0 <= r <= 10 for r in results)


def test_roll_lte():
    rng = _r.Random(42)
    results = [roll(parse_notation("10d6<=2"), rng) for _ in range(100)]
    assert all(0 <= r <= 10 for r in results)


# ── Detailed roll tests ───────────────────────────────────────────────────

def test_roll_detailed_simple():
    rng = _r.Random(42)
    detail = roll_detailed(parse_notation("2d6"), rng)
    assert 'dice' in detail
    assert len(detail['dice']) == 2
    assert detail['total'] == sum(detail['dice'])
    assert detail['modifier'] == 0


def test_roll_detailed_kh():
    rng = _r.Random(42)
    detail = roll_detailed(parse_notation("4d6kh3"), rng)
    assert len(detail['kept']) == 3
    assert len(detail['dropped']) == 1
    assert detail['total'] == sum(detail['kept'])


def test_roll_detailed_success():
    rng = _r.Random(42)
    detail = roll_detailed(parse_notation("10d6>=5"), rng)
    assert detail['total'] == len(detail['kept'])
    assert len(detail['kept']) + len(detail['dropped']) == 10


# ── Exact distribution tests ──────────────────────────────────────────────

def test_exact_1d6():
    dist = exact_distribution(parse_notation("1d6"))
    assert len(dist) == 6
    for k in range(1, 7):
        assert k in dist
        assert dist[k] == Fraction(1, 6)


def test_exact_2d6():
    dist = exact_distribution(parse_notation("2d6"))
    assert dist[2] == Fraction(1, 36)
    assert dist[7] == Fraction(6, 36)
    assert dist[12] == Fraction(1, 36)
    # Total probabilities sum to 1
    assert sum(dist.values()) == Fraction(1)


def test_exact_1d6_plus_3():
    dist = exact_distribution(parse_notation("1d6+3"))
    assert 4 in dist
    assert 9 in dist
    assert dist[4] == Fraction(1, 6)
    assert dist[9] == Fraction(1, 6)


def test_exact_4d6kh3():
    dist = exact_distribution(parse_notation("4d6kh3"))
    # Min = 3 (all 1s, keep 3 ones)
    assert 3 in dist
    # Max = 18 (all 6s, keep 3 sixes)
    assert 18 in dist
    # Total probability = 1
    assert sum(dist.values()) == Fraction(1)


def test_exact_success():
    dist = exact_distribution(parse_notation("2d6>=5"))
    # Each die has 2/6 chance of >=5 (5 or 6)
    assert dist[0] == Fraction(4, 9)  # (4/6)^2
    assert dist[2] == Fraction(1, 9)  # (2/6)^2
    assert sum(dist.values()) == Fraction(1)


def test_exact_too_many_dice():
    try:
        exact_distribution(parse_notation("10d6"))
        assert False, "Should raise ValueError for too many dice"
    except ValueError:
        pass


# ── Monte Carlo tests ────────────────────────────────────────────────────

def test_monte_carlo_basic():
    dist = monte_carlo_distribution(parse_notation("2d6"), trials=10000, seed=42)
    # Should cover range [2, 12]
    assert min(dist.keys()) >= 2
    assert max(dist.keys()) <= 12
    # Most probable outcome should be around 7
    mode = max(dist, key=dist.get)
    assert 6 <= mode <= 8
    # Probabilities should sum to ~1
    assert abs(sum(dist.values()) - 1.0) < 0.01


# ── Statistics tests ─────────────────────────────────────────────────────

def test_stats_1d6():
    dist = exact_distribution(parse_notation("1d6"))
    stats = compute_stats(dist)
    assert abs(stats['mean'] - 3.5) < 0.01
    assert stats['min'] == 1
    assert stats['max'] == 6
    assert stats['range'] == 5


def test_stats_2d6():
    dist = exact_distribution(parse_notation("2d6"))
    stats = compute_stats(dist)
    assert abs(stats['mean'] - 7.0) < 0.01
    assert stats['min'] == 2
    assert stats['max'] == 12


# ── Histogram tests ──────────────────────────────────────────────────────

def test_histogram_output():
    dist = exact_distribution(parse_notation("1d6"))
    hist = ascii_histogram(dist, width=20)
    assert "1" in hist
    assert "6" in hist
    assert "█" in hist


def test_histogram_title():
    dist = exact_distribution(parse_notation("1d6"))
    hist = ascii_histogram(dist, width=20, title="Test Histogram")
    assert "Test Histogram" in hist


# ── Comparison tests ─────────────────────────────────────────────────────

def test_compare():
    result = compare_notations(["2d6", "1d12"], trials=10000, seed=42)
    assert "2d6" in result
    assert "1d12" in result
    assert "Mean" in result
    assert "Head-to-head" in result


# ── CLI integration tests ────────────────────────────────────────────────

def test_cli_roll():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "2d6", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "Result" in result.stdout


def test_cli_multiple_rolls():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "2d6", "--roll", "5", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "Rolled 5 times" in result.stdout


def test_cli_dist():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "2d6", "--dist", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "Exact Distribution" in result.stdout
    assert "█" in result.stdout


def test_cli_stats():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "2d6", "--stats", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "Mean" in result.stdout
    assert "StdDev" in result.stdout


def test_cli_json():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "2d6", "--dist", "--json"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "notation" in data
    assert "distribution" in data
    assert data['notation'] == "2d6"


def test_cli_mc():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "10d6", "--dist", "--mc",
         "--mc-trials", "5000", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "Monte Carlo" in result.stdout


def test_cli_compare():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "2d6", "1d12", "--compare",
         "--mc-trials", "5000", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "Head-to-head" in result.stdout


def test_cli_kh():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "4d6kh3", "--dist", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "4d6kh3" in result.stdout


def test_cli_success_count():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "10d6>=5", "--dist", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "10d6>=5" in result.stdout


def test_cli_modifier():
    result = subprocess.run(
        [sys.executable, "dice_prob.py", "2d6+3", "--dist", "--seed", "42"],
        capture_output=True, text=True, cwd="."
    )
    assert result.returncode == 0
    assert "5" in result.stdout


# ── Run all tests ────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  ✓ {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)