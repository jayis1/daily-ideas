#!/usr/bin/env python3
"""Tests for the Mechanical Calculator simulator."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mechanical_calculator import MechanicalCalculator, CalculatorDisplay


def test_basic_addition():
    calc = MechanicalCalculator()
    calc.set_number(4287)
    calc.crank(1)
    assert calc.read_result() == 4287, f"Expected 4287, got {calc.read_result()}"

    calc.set_number(3156)
    calc.crank(1)
    assert calc.read_result() == 7443, f"Expected 7443, got {calc.read_result()}"
    print("✓ Basic addition: 4287 + 3156 = 7443")


def test_subtraction():
    calc = MechanicalCalculator()
    calc.set_number(9000)
    calc.crank(1)
    assert calc.read_result() == 9000

    calc.set_number(3456)
    calc.crank_reverse(1)
    assert calc.read_result() == 5544, f"Expected 5544, got {calc.read_result()}"
    print("✓ Subtraction: 9000 - 3456 = 5544")


def test_multiplication_via_carriage():
    calc = MechanicalCalculator()
    calc.set_number(123)

    # 123 × 6 at position 0
    calc.set_carriage(0)
    calc.clear_counter()
    calc.crank(6)
    assert calc.read_result() == 738, f"Expected 738, got {calc.read_result()}"

    # 123 × 50 at position 1
    calc.set_carriage(1)
    calc.clear_counter()
    calc.crank(5)
    intermediate = calc.read_result()
    # 738 + 123*5*10 = 738 + 6150 = 6888
    assert intermediate == 6888, f"Expected 6888, got {intermediate}"

    # 123 × 400 at position 2
    calc.set_carriage(2)
    calc.clear_counter()
    calc.crank(4)
    assert calc.read_result() == 56088, f"Expected 56088, got {calc.read_result()}"
    print("✓ Multiplication: 123 × 456 = 56088")


def test_carriage_shift():
    calc = MechanicalCalculator()
    calc.set_number(7)

    calc.set_carriage(0)
    calc.crank(1)
    assert calc.read_result() == 7

    calc.clear_result()
    calc.clear_counter()

    calc.set_carriage(2)
    calc.crank(1)
    assert calc.read_result() == 700, f"Expected 700, got {calc.read_result()}"
    print("✓ Carriage shift: 7 × 10^2 = 700")


def test_counter_increments():
    calc = MechanicalCalculator()
    calc.set_number(42)
    calc.crank(5)
    assert calc.read_counter() == 5, f"Expected counter 5, got {calc.read_counter()}"
    assert calc.read_result() == 210, f"Expected result 210, got {calc.read_result()}"
    print("✓ Counter increments: 42 × 5 = 210")


def test_counter_reverse():
    calc = MechanicalCalculator()
    calc.set_number(100)
    calc.crank(3)
    assert calc.read_counter() == 3
    calc.crank_reverse(1)
    assert calc.read_counter() == 2, f"Expected counter 2, got {calc.read_counter()}"
    assert calc.read_result() == 200, f"Expected result 200, got {calc.read_result()}"
    print("✓ Counter reverse: 3 cranks - 1 reverse = 2 counter, result 200")


def test_clear_operations():
    calc = MechanicalCalculator()
    calc.set_number(42)
    calc.crank(3)

    calc.clear_counter()
    assert calc.read_counter() == 0
    assert calc.read_result() == 126  # Result unchanged

    calc.clear_result()
    assert calc.read_result() == 0
    assert calc.read_setting() == 42  # Setting unchanged

    calc.clear_all()
    assert calc.read_setting() == 0
    assert calc.read_counter() == 0
    assert calc.read_result() == 0
    print("✓ Clear operations work correctly")


def test_large_numbers():
    calc = MechanicalCalculator()
    calc.set_number(99999999999)  # Max setting
    assert calc.read_setting() == 99999999999
    print("✓ Large numbers: setting = 99999999999")


def test_zero_operations():
    calc = MechanicalCalculator()
    calc.set_number(0)
    calc.crank(5)
    assert calc.read_result() == 0
    assert calc.read_counter() == 5
    print("✓ Zero operations: 0 × 5 = 0")


def test_display_renders():
    calc = MechanicalCalculator()
    calc.set_number(4287)
    calc.crank(1)
    display = CalculatorDisplay(calc)
    output = display.render_full()
    assert "CURTA" in output
    assert "4287" in output
    print("✓ Display renders without error")


def test_compact_display():
    calc = MechanicalCalculator()
    calc.set_number(123)
    calc.crank(1)
    display = CalculatorDisplay(calc)
    output = display.render_compact()
    assert "CURTA" in output
    print("✓ Compact display renders without error")


def test_carry_propagation():
    calc = MechanicalCalculator()
    calc.set_number(999)
    calc.crank(1)
    assert calc.read_result() == 999

    calc.set_number(1)
    calc.crank(1)
    assert calc.read_result() == 1000, f"Expected 1000, got {calc.read_result()}"
    print("✓ Carry propagation: 999 + 1 = 1000")


def test_repeated_carry():
    calc = MechanicalCalculator()
    calc.set_number(1)
    calc.crank(999)
    assert calc.read_result() == 999, f"Expected 999, got {calc.read_result()}"
    print("✓ Repeated cranking: 1 × 999 = 999")


if __name__ == "__main__":
    print("Running Mechanical Calculator tests...\n")
    test_basic_addition()
    test_subtraction()
    test_multiplication_via_carriage()
    test_carriage_shift()
    test_counter_increments()
    test_counter_reverse()
    test_clear_operations()
    test_large_numbers()
    test_zero_operations()
    test_display_renders()
    test_compact_display()
    test_carry_propagation()
    test_repeated_carry()
    print("\n✅ All tests passed!")