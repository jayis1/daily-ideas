#!/usr/bin/env python3
"""Smoke / correctness tests for the regex engine visualizer.

Run with:  python3 test_regex_viz.py
Exits 0 if all tests pass.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from regex_viz import run_match, Parser, ParseError, __version__  # noqa: E402


def check(name, pattern, text, expect_match, expect_span=None):
    ok, ctx = run_match(pattern, text)
    if ctx is None:
        print(f"FAIL {name}: parse returned None")
        return False
    if ok != expect_match:
        print(f"FAIL {name}: expected match={expect_match}, got {ok}")
        return False
    if expect_match and expect_span is not None:
        span = (ctx.match_start, ctx.match_end)
        if span != expect_span:
            print(f"FAIL {name}: expected span {expect_span}, got {span}")
            return False
    print(f"ok   {name}")
    return True


def check_parse_error(name, pattern):
    try:
        Parser(pattern).parse()
    except ParseError:
        print(f"ok   {name} (correctly rejected)")
        return True
    print(f"FAIL {name}: should have raised ParseError")
    return False


def check_version(name):
    if __version__ and __version__.count(".") >= 1:
        print(f"ok   {name} ({__version__})")
        return True
    print(f"FAIL {name}: invalid version {__version__!r}")
    return False


def main():
    tests = [
        # --- original engine features ---
        ("literal", "hello", "hello world", True, (0, 5)),
        ("literal-nomatch", "xyz", "hello world", False, None),
        ("star-greedy", "a*b", "aaaab", True, (0, 5)),
        ("star-zero", "a*b", "b", True, (0, 1)),
        ("plus-required", "a+b", "b", False, None),
        ("plus-one", "a+b", "ab", True, (0, 2)),
        ("opt-present", "colou?r", "colour", True, (0, 6)),
        ("opt-absent", "colou?r", "color", True, (0, 5)),
        ("charclass", "[0-9]+", "year 2026", True, (5, 9)),
        ("charclass-negated", r"[^0-9]+", "abc123", True, (0, 3)),
        ("dotstar-greedy", "a.*z", "abczxyz", True, (0, 7)),
        ("dotstar-lazy", "a.*?z", "abczxyz", True, (0, 4)),
        ("anchored-start", "^foo", "foobar", True, (0, 3)),
        ("anchored-start-fail", "^foo", "xfoo", False, None),
        ("anchored-end", "bar$", "foobar", True, (3, 6)),
        ("anchored-both", "^foo$", "foo", True, (0, 3)),
        ("anchored-both-fail", "^foo$", "food", False, None),
        ("group", "(ab)+", "ababab", True, (0, 6)),
        ("alternation-1", "cat|dog", "I have a cat", True, (9, 12)),
        ("alternation-2", "cat|dog", "I have a dog", True, (9, 12)),
        ("alternation-none", "cat|dog", "I have a fish", False, None),
        ("escape-digit", r"\d+", "abc123def", True, (3, 6)),
        ("escape-word", r"\w+", "  hello  ", True, (2, 7)),
        ("escape-space", r"\s+", "a   b", True, (1, 4)),
        ("escaped-dot", r"a\.b", "a.b", True, (0, 3)),
        ("escaped-dot-nomatch", r"a\.b", "axb", False, None),
        ("empty-pattern", "", "abc", True, (0, 0)),
        ("match-empty-input", "a?", "", True, (0, 0)),

        # --- bug fixes: uppercase shorthands (\D \W \S) standalone ---
        ("D-upper", r"\D+", "abc123", True, (0, 3)),
        ("S-upper", r"\S+", "   abc", True, (3, 6)),
        ("W-upper", r"\W+", "abc!!!", True, (3, 6)),
        ("D-single", r"\D", "a", True, (0, 1)),
        ("D-nomatch-digit", r"\D", "5", False, None),

        # --- bug fixes: lazy quantifiers actually lazy ---
        ("lazy-plus", r"a+?", "aaa", True, (0, 1)),
        ("lazy-opt", r"a??", "a", True, (0, 0)),
        ("lazy-opt-then-lit", r"a??b", "ab", True, (0, 2)),

        # --- new feature: bounded repetition {n}, {n,}, {n,m} ---
        ("repeat-exact", r"a{3}", "aaaa", True, (0, 3)),
        ("repeat-range", r"a{2,4}", "aaaaa", True, (0, 4)),
        ("repeat-open", r"a{2,}", "aaaaa", True, (0, 5)),
        ("repeat-lazy", r"a{2,4}?", "aaaaa", True, (0, 2)),
        ("repeat-zero", r"a{0,2}", "bbb", True, (0, 0)),
        ("repeat-not-enough", r"a{3}", "aa", False, None),
        ("repeat-on-group", r"(ab){2}", "ababab", True, (0, 4)),

        # --- new feature: word boundary \b / \B ---
        ("word-boundary", r"\bfoo\b", "a foo b", True, (2, 5)),
        ("word-boundary-start", r"\bfoo", "foobar foo", True, (0, 3)),
        ("word-boundary-neg", r"\Bfoo", "afoob", True, (1, 4)),
        ("word-boundary-nomatch", r"\bfoo\b", "foobar", False, None),

        # --- new feature: negated shorthands inside character classes ---
        ("D-in-class", r"[\D]", "a", True, (0, 1)),
        ("D-in-class-nomatch", r"[\D]", "5", False, None),
        ("S-in-class", r"[\s]", " ", True, (0, 1)),
        ("class-union", r"[\d\s]+", "12 34", True, (0, 5)),
        ("neg-class-shorthand", r"[^\d]+", "abc123", True, (0, 3)),

        # --- misc edge cases ---
        ("literal-brace", "a{", "a{", True, (0, 2)),
        ("escape-brace", r"a\{2\}", "a{2}", True, (0, 4)),
        ("complex-phone", r"\d{3}-\d{4}", "call 555-1234", True, (5, 13)),
    ]
    passed = 0
    for t in tests:
        if check(*t):
            passed += 1

    parse_tests = [
        ("unterminated-group", "(foo"),
        ("unterminated-class", "[abc"),
        ("trailing-backslash", "\\"),
        ("repeat-min-gt-max", "a{3,2}"),
        ("trailing-backslash-class", "[a\\"),
    ]
    for t in parse_tests:
        if check_parse_error(*t):
            passed += 1

    if check_version("version-string"):
        passed += 1

    total = len(tests) + len(parse_tests) + 1
    print(f"\n{passed}/{total} tests passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())