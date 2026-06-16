#!/usr/bin/env python3
"""Tests for the terminal spreadsheet engine (non-curses logic only)."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from spreadsheet import Spreadsheet, cell_name, parse_cell_name, col_to_letter, letter_to_col, tokenize, parse_range


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


def test_set_and_get():
    s = Spreadsheet()
    s.set_cell(0, 0, '42')
    assert s.get_value(0, 0) == 42
    s.set_cell(1, 0, 'hello')
    assert s.get_value(1, 0) == 'hello'
    s.set_cell(2, 0, '3.14')
    assert abs(s.get_value(2, 0) - 3.14) < 0.001


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


def test_formulas_cell_refs():
    s = Spreadsheet()
    s.set_cell(0, 0, '100')
    s.set_cell(0, 1, '200')
    s.set_cell(1, 0, '=A1+B1')
    assert s.get_value(1, 0) == 300


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


def test_multi_column_range():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(0, 1, '20')
    s.set_cell(1, 0, '30')
    s.set_cell(1, 1, '40')
    s.set_cell(2, 0, '=SUM(A1:B2)')
    assert s.get_value(2, 0) == 100


def test_nested_formulas():
    s = Spreadsheet()
    s.set_cell(0, 0, '=1+2')
    s.set_cell(1, 0, '=A1*3')
    assert s.get_value(1, 0) == 9


def test_delete_cell():
    s = Spreadsheet()
    s.set_cell(0, 0, '42')
    assert s.get_value(0, 0) == 42
    s.set_cell(0, 0, '')
    assert s.get_value(0, 0) == 0


def test_circular_reference():
    s = Spreadsheet()
    s.set_cell(0, 0, '=A1')
    val = s.get_value(0, 0)
    assert isinstance(val, str) and 'ERR' in str(val)


def test_division_by_zero():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '0')
    s.set_cell(2, 0, '=A1/A2')
    val = s.get_value(2, 0)
    assert isinstance(val, str) and 'ERR' in str(val)


def test_update_propagation():
    s = Spreadsheet()
    s.set_cell(0, 0, '10')
    s.set_cell(1, 0, '=A1*2')
    assert s.get_value(1, 0) == 20
    s.set_cell(0, 0, '20')
    assert s.get_value(1, 0) == 40


def test_complex_formulas():
    s = Spreadsheet()
    s.set_cell(0, 0, '5')
    s.set_cell(1, 0, '3')
    s.set_cell(2, 0, '=(A1+A2)*2')
    assert s.get_value(2, 0) == 16
    s.set_cell(3, 0, '=A1^2+A2^2')
    assert s.get_value(3, 0) == 34


def test_functions_abs_sqrt():
    s = Spreadsheet()
    s.set_cell(0, 0, '-42')
    s.set_cell(1, 0, '=ABS(A1)')
    assert s.get_value(1, 0) == 42
    s.set_cell(2, 0, '16')
    s.set_cell(3, 0, '=SQRT(A3)')
    assert s.get_value(3, 0) == 4.0


def test_tokenize():
    tokens = tokenize('A1+B2*3')
    assert tokens[0] == ('CELL', 'A1')
    assert tokens[1] == ('OP', '+')
    assert tokens[2] == ('CELL', 'B2')
    assert tokens[3] == ('OP', '*')
    assert tokens[4] == ('NUM', 3.0)


def test_parse_range():
    tokens = tokenize('A1:B3')
    rng, pos = parse_range(tokens, 0)
    assert rng == (0, 0, 2, 1)


def test_empty_cells():
    s = Spreadsheet()
    assert s.get_value(0, 0) == 0
    assert s.get_value(99, 25) == 0


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
    test_division_by_zero()
    test_update_propagation()
    test_complex_formulas()
    test_functions_abs_sqrt()
    test_tokenize()
    test_parse_range()
    test_empty_cells()
    print("All tests passed!")