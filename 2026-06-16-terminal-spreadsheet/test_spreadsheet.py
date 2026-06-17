#!/usr/bin/env python3
"""Tests for the terminal spreadsheet engine (non-curses logic only)."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from spreadsheet import (
    Spreadsheet, cell_name, parse_cell_name, col_to_letter, letter_to_col,
    tokenize, parse_range, __version__
)


# ── Cell name helpers ─────────────────────────────────────────────────────

def test_cell_name_helpers():
    assert cell_name(0, 0) == 'A1'
    assert cell_name(0, 1) == 'B1'
    assert cell_name(25, 25) == 'Z26'
    assert parse_cell_name('A1') == (0, 0)
    assert parse_cell_name('Z26') == (25, 25)
    assert parse_cell_name('AA1') is None  # only single letters supported
    assert col_to_letter(0) == 'A'
    assert col_to_letter(25) == 'Z'
    assert letter_to_col('A') == 0
    assert letter_to_col('Z') == 25


# ── Basic set / get ────────────────────────────────────────────────────────

def test_set_and_get():
    s = Spreadsheet()
    s.set_cell(0, 0, '42')
    assert s.get_value(0, 0) == 42
    s.set_cell(1, 0, 'hello')
    assert s.get_value(1, 0) == 'hello'
    s.set_cell(2, 0, '3.14')
    assert abs(s.get_value(2, 0) - 3.14) < 0.001


# ── Arithmetic formulas ────────────────────────────────────────────────────

def test_formulas_arithmetic():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '20')
    s.set_cell(2, 0, '=A1+A2')
    assert s.get_value(2, 0) == 30

    s.set_cell(3, 0, '=A1*A2')
    assert s.get_value(3, 0) == 200

    s.set_cell(4, 0, '=A1/A2')
    assert s.get_value(4, 0) == 0.5

    s.set_cell(5, 0, '=A1^2')
    assert s.get_value(5, 0) == 100

    s.set_cell(6, 0, '=-A1+5')
    assert s.get_value(6, 0) == -5


# ── Cell references ────────────────────────────────────────────────────────

def test_formulas_cell_refs():
    s = Spreadsheet()
    s.set_cell(0, 0, '100')
    s.set_cell(0, 1, '200')
    s.set_cell(1, 0, '=A1+B1')
    assert s.get_value(1, 0) == 300


# ── Aggregate functions ────────────────────────────────────────────────────

def test_sum_function():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '20')
    s.set_cell(2, 0, '30')
    s.set_cell(3, 0, '=SUM(A1:A3)')
    assert s.get_value(3, 0) == 60


def test_avg_function():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '20')
    s.set_cell(2, 0, '30')
    s.set_cell(3, 0, '=AVG(A1:A3)')
    assert s.get_value(3, 0) == 20


def test_min_max_count():
    s = Spreadsheet()
    s.set_cell(0, 0, '5')
    s.set_cell(1, 0, '15')
    s.set_cell(2, 0, '25')
    s.set_cell(3, 0, '=MIN(A1:A3)')
    assert s.get_value(3, 0) == 5
    s.set_cell(4, 0, '=MAX(A1:A3)')
    assert s.get_value(4, 0) == 25
    s.set_cell(5, 0, '=COUNT(A1:A3)')
    assert s.get_value(5, 0) == 3


# ── Multi-column ranges ───────────────────────────────────────────────────

def test_multi_column_range():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(0, 1, '20')
    s.set_cell(1, 0, '30')
    s.set_cell(1, 1, '40')
    s.set_cell(2, 0, '=SUM(A1:B2)')
    assert s.get_value(2, 0) == 100


# ── Nested formulas ───────────────────────────────────────────────────────

def test_nested_formulas():
    s = Spreadsheet()
    s.set_cell(0, 0, '=1+2')
    s.set_cell(1, 0, '=A1*3')
    assert s.get_value(1, 0) == 9


# ── Deletion ───────────────────────────────────────────────────────────────

def test_delete_cell():
    s = Spreadsheet()
    s.set_cell(0, 0, '42')
    assert s.get_value(0, 0) == 42
    s.set_cell(0, 0, '')
    assert s.get_value(0, 0) == 0


# ── Circular references ────────────────────────────────────────────────────

def test_circular_reference():
    s = Spreadsheet()
    s.set_cell(0, 0, '=A1')
    val = s.get_value(0, 0)
    assert isinstance(val, str) and 'ERR' in str(val)


def test_transitive_circular_reference():
    """A1 refers to B1, B1 refers to A1 — should detect the cycle."""
    s = Spreadsheet()
    s.set_cell(0, 0, '=B1')
    s.set_cell(0, 1, '=A1')
    val = s.get_value(0, 0)
    assert isinstance(val, str) and 'ERR' in str(val)


# ── Division by zero ───────────────────────────────────────────────────────

def test_division_by_zero():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '0')
    s.set_cell(2, 0, '=A1/A2')
    val = s.get_value(2, 0)
    assert isinstance(val, str) and 'ERR' in str(val)


# ── Live recalculation ─────────────────────────────────────────────────────

def test_update_propagation():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '=A1*2')
    assert s.get_value(1, 0) == 20
    s.set_cell(0, 0, '20')
    assert s.get_value(1, 0) == 40


# ── Complex formulas ───────────────────────────────────────────────────────

def test_complex_formulas():
    s = Spreadsheet()
    s.set_cell(0, 0, '5')
    s.set_cell(1, 0, '3')
    s.set_cell(2, 0, '=(A1+A2)*2')
    assert s.get_value(2, 0) == 16
    s.set_cell(3, 0, '=A1^2+A2^2')
    assert s.get_value(3, 0) == 34


# ── Scalar functions ───────────────────────────────────────────────────────

def test_functions_abs_sqrt():
    s = Spreadsheet()
    s.set_cell(0, 0, '-42')
    s.set_cell(1, 0, '=ABS(A1)')
    assert s.get_value(1, 0) == 42
    s.set_cell(2, 0, '16')
    s.set_cell(3, 0, '=SQRT(A3)')
    assert s.get_value(3, 0) == 4.0


# ── MEDIAN and STDEV ───────────────────────────────────────────────────────

def test_median():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '20')
    s.set_cell(2, 0, '30')
    s.set_cell(3, 0, '=MEDIAN(A1:A3)')
    assert s.get_value(3, 0) == 20  # odd count → middle

    # Even count: 10, 20, 30, 40 → median = 25
    s2 = Spreadsheet()
    s2.set_cell(0, 0, '10')
    s2.set_cell(1, 0, '20')
    s2.set_cell(2, 0, '30')
    s2.set_cell(3, 0, '40')
    s2.set_cell(5, 0, '=MEDIAN(A1:A4)')
    assert s2.get_value(5, 0) == 25.0  # even count → average of middle two


def test_stdev():
    # Data: 2, 4, 4, 4, 5, 5, 7 → sample stdev ≈ 1.512
    s = Spreadsheet()
    s.set_cell(0, 0, '2')
    s.set_cell(1, 0, '4')
    s.set_cell(2, 0, '4')
    s.set_cell(3, 0, '4')
    s.set_cell(4, 0, '5')
    s.set_cell(5, 0, '5')
    s.set_cell(6, 0, '7')
    s.set_cell(8, 0, '=STDEV(A1:A7)')
    result = s.get_value(8, 0)
    assert abs(result - 1.512) < 0.01

    # Single value: stdev should be 0
    s2 = Spreadsheet()
    s2.set_cell(0, 0, '42')
    s2.set_cell(1, 0, '=STDEV(A1:A1)')
    assert s2.get_value(1, 0) == 0


# ── Comparison operators ───────────────────────────────────────────────────

def test_comparison_operators():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '20')
    s.set_cell(2, 0, '=A1<A2')
    assert s.get_value(2, 0) == 1  # true
    s.set_cell(3, 0, '=A1>A2')
    assert s.get_value(3, 0) == 0  # false
    s.set_cell(4, 0, '=A1==10')
    assert s.get_value(4, 0) == 1


# ── IF function ────────────────────────────────────────────────────────────

def test_if_function():
    s = Spreadsheet()
    s.set_cell(0, 0, '150')
    s.set_cell(1, 0, '=IF(A1>100,A1,0)')
    assert s.get_value(1, 0) == 150

    s.set_cell(0, 0, '50')
    # Need to invalidate cache (setting cell does this)
    s.set_cell(1, 0, '=IF(A1>100,A1,0)')
    assert s.get_value(1, 0) == 0


# ── CONCAT function ────────────────────────────────────────────────────────

def test_concat_function():
    s = Spreadsheet()
    s.set_cell(0, 0, 'Hello')
    s.set_cell(1, 0, 'World')
    s.set_cell(2, 0, '=CONCAT(A1," ",A2)')
    assert s.get_value(2, 0) == 'Hello World'


# ── Tokenizer ──────────────────────────────────────────────────────────────

def test_tokenize():
    tokens = tokenize('A1+B2*3')
    assert tokens[0] == ('CELL', 'A1')
    assert tokens[1] == ('OP', '+')
    assert tokens[2] == ('CELL', 'B2')
    assert tokens[3] == ('OP', '*')
    assert tokens[4] == ('NUM', 3.0)


def test_tokenize_comparison():
    tokens = tokenize('A1>=10')
    assert tokens[0] == ('CELL', 'A1')
    assert tokens[1] == ('OP', '>=')
    assert tokens[2] == ('NUM', 10.0)


def test_tokenize_string():
    tokens = tokenize('"hello"')
    assert tokens[0] == ('STR', 'hello')


# ── Parse range ────────────────────────────────────────────────────────────

def test_parse_range():
    tokens = tokenize('A1:B3')
    rng, pos = parse_range(tokens, 0)
    assert rng == (0, 0, 2, 1)


# ── Empty cells ────────────────────────────────────────────────────────────

def test_empty_cells():
    s = Spreadsheet()
    assert s.get_value(0, 0) == 0
    assert s.get_value(99, 25) == 0


# ── Undo / Redo ────────────────────────────────────────────────────────────

def test_undo_redo():
    s = Spreadsheet()
    s.set_cell(0, 0, '42')
    assert s.get_value(0, 0) == 42

    # Undo should revert to empty
    assert s.undo() is True
    assert s.get_value(0, 0) == 0

    # Redo should restore
    assert s.redo() is True
    assert s.get_value(0, 0) == 42

    # Second undo should work again
    assert s.undo() is True
    assert s.get_value(0, 0) == 0

    # Undo with empty stack returns False
    assert s.undo() is False


def test_undo_multiple_cells():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '=A1*2')
    assert s.get_value(1, 0) == 20

    s.set_cell(0, 0, '30')
    assert s.get_value(1, 0) == 60

    # Undo should revert A1 back to 10
    assert s.undo() is True
    assert s.get_value(0, 0) == 10
    assert s.get_value(1, 0) == 20


# ── CSV save / load ───────────────────────────────────────────────────────

def test_csv_save_load():
    s = Spreadsheet()
    s.set_cell(0, 0, 'Name')
    s.set_cell(0, 1, 'Value')
    s.set_cell(1, 0, 'Alice')
    s.set_cell(1, 1, '42')

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        filepath = f.name

    try:
        # Save
        msg = s.save_csv(filepath)
        assert 'Saved' in msg

        # Load into a fresh spreadsheet
        s2 = Spreadsheet()
        msg2 = s2.load_csv(filepath)
        assert 'Loaded' in msg2
        assert s2.get_raw(0, 0) == 'Name'
        assert s2.get_raw(1, 1) == '42'
    finally:
        os.unlink(filepath)


def test_csv_load_not_found():
    s = Spreadsheet()
    msg = s.load_csv('/nonexistent/path/file.csv')
    assert 'not found' in msg.lower() or 'error' in msg.lower()


# ── Search ─────────────────────────────────────────────────────────────────

def test_search():
    s = Spreadsheet()
    s.set_cell(0, 0, 'Hello')
    s.set_cell(2, 3, 'World')
    result = s.search('World')
    assert result == (2, 3)
    result2 = s.search('xyz')
    assert result2 is None


def test_search_after():
    s = Spreadsheet()
    s.set_cell(0, 0, 'Alpha')
    s.set_cell(0, 1, 'Beta')
    s.set_cell(1, 0, 'Alpha2')
    # Search for "alpha" after (0, 0)
    result = s.search_after('alpha', 0, 0)
    assert result == (1, 0)  # wraps to row 1


# ── Modulo operator ────────────────────────────────────────────────────────

def test_modulo():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '=A1%3')
    assert s.get_value(1, 0) == 1


# ── Version ────────────────────────────────────────────────────────────────

def test_version():
    assert __version__
    # Should be a string like "1.1.0"
    parts = __version__.split('.')
    assert len(parts) >= 2


# ── Bug-fix regression tests ──────────────────────────────────────────────

def test_count_excludes_empty_cells():
    """COUNT should not count empty cells (Bug: empty cells returned 0, which
    was counted as numeric). Fixed with _EMPTY_CELL sentinel."""
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(2, 0, '20')
    # A2 is empty
    s.set_cell(5, 0, '=COUNT(A1:A4)')
    assert s.get_value(5, 0) == 2, f"Expected 2 (skip empty), got {s.get_value(5, 0)}"


def test_count_empty_range():
    """COUNT of a fully empty range should return 0."""
    s = Spreadsheet()
    s.set_cell(5, 0, '=COUNT(A1:A4)')
    assert s.get_value(5, 0) == 0


def test_cache_invalidation_on_delete():
    """Deleting a cell should clear the entire cache so dependent formulas
    recalculate. (Bug: only the deleted cell's cache was cleared.)"""
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '=A1*2')
    assert s.get_value(1, 0) == 20
    s.set_cell(0, 0, '')  # Delete A1
    assert s.get_value(1, 0) == 0, f"After deleting A1, A2 should be 0, got {s.get_value(1, 0)}"


def test_concat_float_formatting():
    """CONCAT should format whole-number floats cleanly (3.0 → '3').
    (Bug: str(3.0) gave '3.0' instead of '3'.)"""
    s = Spreadsheet()
    s.set_cell(0, 0, '=CONCAT(1, "+", 2, "=", 3)')
    assert s.get_value(0, 0) == '1+2=3', f"Expected '1+2=3', got {s.get_value(0, 0)!r}"


def test_sqrt_negative():
    """SQRT of a negative number should return an error, not silently return 0.
    (Bug: SQRT(-4) returned 0 with no indication of error.)"""
    s = Spreadsheet()
    s.set_cell(0, 0, '-4')
    s.set_cell(1, 0, '=SQRT(A1)')
    val = s.get_value(1, 0)
    assert isinstance(val, str) and 'ERR' in val, f"Expected ERR, got {val!r}"


def test_logical_and():
    """The && operator should work as logical AND.
    (Bug: && was tokenized but never parsed, giving silently wrong results.)"""
    s = Spreadsheet()
    s.set_cell(0, 0, '=1&&1')
    assert s.get_value(0, 0) == 1
    s.set_cell(1, 0, '=1&&0')
    assert s.get_value(1, 0) == 0
    s.set_cell(2, 0, '=0&&1')
    assert s.get_value(2, 0) == 0
    s.set_cell(3, 0, '=0&&0')
    assert s.get_value(3, 0) == 0


def test_string_plus_number_formatting():
    """String + number via + operator should format whole floats cleanly.
    (Bug: 'hello'+5 gave 'hello5.0' instead of 'hello5'.)"""
    s = Spreadsheet()
    s.set_cell(0, 0, 'hello')
    s.set_cell(1, 0, '=A1+5')
    assert s.get_value(1, 0) == 'hello5', f"Expected 'hello5', got {s.get_value(1, 0)!r}"


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_cell_name_helpers()
    test_set_and_get()
    test_formulas_arithmetic()
    test_formulas_cell_refs()
    test_sum_function()
    test_avg_function()
    test_min_max_count()
    test_multi_column_range()
    test_nested_formulas()
    test_delete_cell()
    test_circular_reference()
    test_transitive_circular_reference()
    test_division_by_zero()
    test_update_propagation()
    test_complex_formulas()
    test_functions_abs_sqrt()
    test_median()
    test_stdev()
    test_comparison_operators()
    test_if_function()
    test_concat_function()
    test_tokenize()
    test_tokenize_comparison()
    test_tokenize_string()
    test_parse_range()
    test_empty_cells()
    test_undo_redo()
    test_undo_multiple_cells()
    test_csv_save_load()
    test_csv_load_not_found()
    test_search()
    test_search_after()
    test_modulo()
    test_version()
    # ── Bug-fix regression tests ─────────────────────────────────────────
    test_count_excludes_empty_cells()
    test_count_empty_range()
    test_cache_invalidation_on_delete()
    test_concat_float_formatting()
    test_sqrt_negative()
    test_logical_and()
    test_string_plus_number_formatting()
    print("All tests passed!")