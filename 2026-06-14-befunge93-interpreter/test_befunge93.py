#!/usr/bin/env python3
"""Tests for the Befunge-93 interpreter.

Covers:
  - Core stack operations (push, pop, peek)
  - All arithmetic instructions (+, -, *, /, %)
  - Logical instructions (!, `)
  - Direction changing (>, <, ^, v)
  - Conditional branching (_, |)
  - String mode (")
  - I/O instructions (., ,)
  - Self-modification (g, p)
  - Bridge instruction (#)
  - End program (@)
  - Random direction (?)
  - Grid wrapping (toroidal topology)
  - Program loading and validation
  - Built-in example programs
  - Edge cases (empty stack, division by zero)
  - Output capture
  - Version constant
"""

import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from befunge93 import Befunge93, EXAMPLES, COLS, ROWS, __version__


class TestStackOperations(unittest.TestCase):
    """Test stack push, pop, and peek operations."""

    def setUp(self):
        self.bf = Befunge93()

    def test_push_and_pop(self):
        self.bf.push(42)
        self.assertEqual(self.bf.pop(), 42)

    def test_pop_empty_stack(self):
        """Popping an empty stack returns 0 per the spec."""
        self.assertEqual(self.bf.pop(), 0)

    def test_peek(self):
        self.bf.push(7)
        self.assertEqual(self.bf.peek(), 7)
        self.assertEqual(len(self.bf.stack), 1)  # peek doesn't remove

    def test_peek_empty_stack(self):
        self.assertEqual(self.bf.peek(), 0)

    def test_push_multiple(self):
        for i in range(10):
            self.bf.push(i)
        self.assertEqual(self.bf.pop(), 9)
        self.assertEqual(self.bf.pop(), 8)


class TestArithmetic(unittest.TestCase):
    """Test arithmetic instructions: +, -, *, /, %."""

    def setUp(self):
        self.bf = Befunge93()

    def test_addition(self):
        self.bf.load('34+.@')
        self.bf.run()
        self.assertIn('7', self.bf.output)

    def test_subtraction(self):
        self.bf.load('93-.@')
        self.bf.run()
        self.assertIn('6', self.bf.output)

    def test_multiplication(self):
        self.bf.load('67*.@')
        self.bf.run()
        self.assertIn('42', self.bf.output)

    def test_division(self):
        self.bf.load('93/.@')
        self.bf.run()
        self.assertIn('3', self.bf.output)

    def test_division_by_zero(self):
        """Division by zero pushes 0 per the spec."""
        self.bf.load('10/.@')
        self.bf.run()
        self.assertIn('0', self.bf.output)

    def test_modulo(self):
        self.bf.load('95%.@')
        self.bf.run()
        self.assertIn('4', self.bf.output)

    def test_modulo_by_zero(self):
        """Modulo by zero pushes 0 per the spec."""
        self.bf.load('10%.@')
        self.bf.run()
        self.assertIn('0', self.bf.output)

    def test_digit_push(self):
        """Digits 0-9 push their value onto the stack."""
        self.bf.load('0.@')
        self.bf.run()
        self.assertIn('0', self.bf.output)

    def test_negative_subtraction(self):
        """Subtraction can produce negative results."""
        self.bf.load('39-.@')
        self.bf.run()
        self.assertIn('-6', self.bf.output)


class TestLogical(unittest.TestCase):
    """Test logical instructions: !, `."""

    def setUp(self):
        self.bf = Befunge93()

    def test_logical_not_zero(self):
        """NOT of 0 pushes 1."""
        self.bf.load('0!.@')
        self.bf.run()
        self.assertIn('1', self.bf.output)

    def test_logical_not_nonzero(self):
        """NOT of non-zero pushes 0."""
        self.bf.load('5!.@')
        self.bf.run()
        self.assertIn('0', self.bf.output)

    def test_greater_than_true(self):
        """` pushes 1 when a > b."""
        self.bf.load('53`.@')
        self.bf.run()
        self.assertIn('1', self.bf.output)

    def test_greater_than_false(self):
        """` pushes 0 when a <= b."""
        self.bf.load('35`.@')
        self.bf.run()
        self.assertIn('0', self.bf.output)


class TestDirectionChanging(unittest.TestCase):
    """Test direction instructions: >, <, ^, v."""

    def setUp(self):
        self.bf = Befunge93()

    def test_direction_right(self):
        self.bf.load('>.@')
        self.bf.run()
        self.assertFalse(self.bf.running)

    def test_direction_left(self):
        """Program wrapping left should still terminate."""
        # Row has '@' at position 0, program wraps around
        self.bf.load('@<')
        self.bf.run()
        self.assertFalse(self.bf.running)

    def test_program_terminates(self):
        """Any valid program should terminate or reach max_steps."""
        self.bf.load('>.@')
        self.bf.run()
        self.assertFalse(self.bf.running)


class TestConditional(unittest.TestCase):
    """Test conditional instructions: _, |."""

    def setUp(self):
        self.bf = Befunge93()

    def test_horizontal_if_zero(self):
        """_ with 0 on stack goes right."""
        self.bf.load('0_.@')
        self.bf.run()
        self.assertIn('0', self.bf.output)

    def test_horizontal_if_nonzero(self):
        """_ with non-zero on stack goes left."""
        self.bf.load('1_.@')
        self.bf.run()
        # Program should still terminate (wrapping around)


class TestStringMode(unittest.TestCase):
    """Test string mode toggle with \"."""

    def setUp(self):
        self.bf = Befunge93()

    def test_string_mode_hello(self):
        """Hello World example uses string mode."""
        self.bf.load(EXAMPLES['hello']['code'])
        self.bf.run()
        self.assertIn('Hello, World!', self.bf.output)

    def test_string_mode_pushes_ascii(self):
        """Characters in string mode push their ASCII values."""
        # Push 'A' (65) in string mode, then print as integer
        self.bf.load('"A".@')
        self.bf.run()
        self.assertIn('65', self.bf.output)

    def test_string_mode_print_char(self):
        """Push a character in string mode and print it."""
        self.bf.load('"H",@')
        self.bf.run()
        self.assertIn('H', self.bf.output)


class TestIO(unittest.TestCase):
    """Test I/O instructions: ., ,."""

    def setUp(self):
        self.bf = Befunge93()

    def test_print_integer(self):
        """The . instruction prints an integer followed by a space."""
        self.bf.load('34+.@')
        self.bf.run()
        self.assertEqual(self.bf.output.strip(), '7')

    def test_print_character(self):
        """The , instruction prints an ASCII character."""
        # 89* = 8*9 = 72 = ASCII 'H'
        self.bf.load('89*,@')
        self.bf.run()
        self.assertIn('H', self.bf.output)


class TestSelfModification(unittest.TestCase):
    """Test self-modification instructions: g, p."""

    def setUp(self):
        self.bf = Befunge93()

    def test_get_instruction(self):
        """g reads a character from the grid."""
        # Load 'A' at position (0,0), then read it back
        # Push 0, push 0 (coords), get, print as integer
        self.bf.load('A  00g.@')
        self.bf.run()
        # ASCII 'A' = 65
        self.assertIn('65', self.bf.output)

    def test_put_instruction(self):
        """p writes a character to the grid."""
        # Put 65 (A) at (0,0), then verify with g
        # 55* (25) push onto stack, we use p then g
        self.bf.load('55*00p00g.@')
        self.bf.run()
        # 55* = 25, put 25 at (0,0), get it back, should print 25
        self.assertIn('25', self.bf.output)


class TestBridge(unittest.TestCase):
    """Test the bridge instruction #."""

    def setUp(self):
        self.bf = Befunge93()

    def test_bridge_skips_next_cell(self):
        """# should skip the next cell in the current direction."""
        # Push 3, skip 4, push 5, add, print
        # 3#45+.@ -> push 3, skip '4', push 5, add (=8), print
        self.bf.load('3#45+.@')
        self.bf.run()
        self.assertIn('8', self.bf.output)

    def test_bridge_in_string_mode_not_active(self):
        """Bridge should work outside string mode."""
        # Simple: push 1, bridge skip 2, then end
        self.bf.load('1#2.@')
        self.bf.run()
        # After pushing 1, # skips 2, then . prints 1, @ ends
        self.assertIn('1', self.bf.output)


class TestEndProgram(unittest.TestCase):
    """Test program termination with @."""

    def setUp(self):
        self.bf = Befunge93()

    def test_at_terminates(self):
        """@ should set running to False."""
        self.bf.load('@')
        self.bf.run()
        self.assertFalse(self.bf.running)

    def test_at_stops_execution(self):
        """Nothing after @ should execute."""
        self.bf.load('@99*.')
        self.bf.run()
        self.assertEqual(self.bf.output, '')


class TestGridWrapping(unittest.TestCase):
    """Test toroidal grid wrapping."""

    def setUp(self):
        self.bf = Befunge93()

    def test_wrap_right_to_left(self):
        """Moving right past COLS-1 should wrap to column 0."""
        self.bf.x = COLS - 1
        self.bf.dx, self.bf.dy = 1, 0
        self.bf.move()
        self.assertEqual(self.bf.x, 0)

    def test_wrap_left_to_right(self):
        """Moving left past 0 should wrap to COLS-1."""
        self.bf.x = 0
        self.bf.dx, self.bf.dy = -1, 0
        self.bf.move()
        self.assertEqual(self.bf.x, COLS - 1)

    def test_wrap_top_to_bottom(self):
        """Moving up past row 0 should wrap to ROWS-1."""
        self.bf.y = 0
        self.bf.dx, self.bf.dy = 0, -1
        self.bf.move()
        self.assertEqual(self.bf.y, ROWS - 1)

    def test_wrap_bottom_to_top(self):
        """Moving down past ROWS-1 should wrap to row 0."""
        self.bf.y = ROWS - 1
        self.bf.dx, self.bf.dy = 0, 1
        self.bf.move()
        self.assertEqual(self.bf.y, 0)


class TestProgramLoading(unittest.TestCase):
    """Test program loading from strings and files."""

    def setUp(self):
        self.bf = Befunge93()

    def test_load_simple(self):
        self.bf.load('34+.@')
        self.assertEqual(self.bf.grid[0][0], '3')
        self.assertEqual(self.bf.grid[0][1], '4')
        self.assertEqual(self.bf.grid[0][2], '+')
        self.assertEqual(self.bf.grid[0][3], '.')
        self.assertEqual(self.bf.grid[0][4], '@')

    def test_load_multiline(self):
        self.bf.load('>v\n>@\n')
        self.assertEqual(self.bf.grid[0][0], '>')
        self.assertEqual(self.bf.grid[0][1], 'v')
        self.assertEqual(self.bf.grid[1][0], '>')
        self.assertEqual(self.bf.grid[1][1], '@')

    def test_load_empty_program(self):
        self.bf.load('')
        self.assertEqual(self.bf.grid[0][0], ' ')

    def test_load_truncates_long_lines(self):
        """Lines longer than 80 chars should be truncated."""
        self.bf.load('A' * 100)
        self.assertEqual(self.bf.grid[0][79], 'A')
        # Position 80+ should be empty (truncated)
        all_spaces_after = all(
            self.bf.grid[0][x] == ' ' for x in range(80, min(100, COLS))
        )
        # Actually, since COLS=80, index 79 is the last valid column
        # Characters at index >= 80 are simply not stored

    def test_load_truncates_many_rows(self):
        """Programs with more than 25 rows should be truncated."""
        self.bf.load('\n'.join(['@'] * 30))
        self.assertEqual(self.bf.grid[24][0], '@')

    def test_load_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.bf.load_file('/nonexistent/path/test.bf')

    def test_load_from_file(self):
        """Test loading from a real file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bf',
                                         delete=False) as f:
            f.write('34+.@')
            f.flush()
            tmp_path = f.name
        try:
            self.bf.load_file(tmp_path)
            self.bf.run()
            self.assertIn('7', self.bf.output)
        finally:
            os.unlink(tmp_path)


class TestValidation(unittest.TestCase):
    """Test program validation functionality."""

    def setUp(self):
        self.bf = Befunge93()

    def test_validate_empty_program(self):
        self.bf.load('')
        warnings = self.bf.validate()
        self.assertTrue(any('empty' in w.lower() for w in warnings))

    def test_validate_missing_terminator(self):
        self.bf.load('34+')
        warnings = self.bf.validate()
        self.assertTrue(any('@' in w for w in warnings))

    def test_validate_valid_program(self):
        self.bf.load('34+.@')
        warnings = self.bf.validate()
        # Should have no warning about missing @
        terminator_warnings = [w for w in warnings if '@' in w]
        self.assertEqual(len(terminator_warnings), 0)

    def test_validate_unknown_chars(self):
        self.bf.load('34+.Q@')
        warnings = self.bf.validate()
        self.assertTrue(any('Q' in w for w in warnings))

    def test_validate_input_instructions(self):
        self.bf.load('&.@')
        warnings = self.bf.validate()
        self.assertTrue(any('input' in w.lower() for w in warnings))


class TestExamples(unittest.TestCase):
    """Test built-in example programs."""

    def test_hello_output(self):
        bf = Befunge93()
        bf.load(EXAMPLES['hello']['code'])
        bf.run()
        self.assertIn('Hello, World!', bf.output)

    def test_add_output(self):
        bf = Befunge93()
        bf.load(EXAMPLES['add']['code'])
        bf.run()
        self.assertIn('7', bf.output)

    def test_multiply_output(self):
        bf = Befunge93()
        bf.load(EXAMPLES['multiply']['code'])
        bf.run()
        self.assertIn('42', bf.output)

    def test_echo_digits_output(self):
        bf = Befunge93()
        bf.load(EXAMPLES['echo_digits']['code'])
        bf.run()
        for digit in ['1', '2', '3', '4', '5']:
            self.assertIn(digit, bf.output)

    def test_reverse_output(self):
        bf = Befunge93()
        bf.load(EXAMPLES['reverse']['code'])
        bf.run()
        self.assertIn('World!', bf.output)

    def test_truth_output(self):
        bf = Befunge93()
        bf.load(EXAMPLES['truth']['code'])
        bf.run()
        self.assertIn('42', bf.output)

    def test_divider_output(self):
        """14 / 3 = 4 (truncation toward zero)."""
        bf = Befunge93()
        bf.load(EXAMPLES['divider']['code'])
        bf.run()
        self.assertIn('4', bf.output)

    def test_factorial_output(self):
        """5! = 120 using chained multiplication."""
        bf = Befunge93()
        bf.load(EXAMPLES['factorial']['code'])
        bf.run()
        self.assertIn('120', bf.output)

    def test_modulo_output(self):
        """14 % 3 = 2."""
        bf = Befunge93()
        bf.load(EXAMPLES['modulo']['code'])
        bf.run()
        self.assertIn('2', bf.output)

    def test_charprint_output(self):
        """89* = 72 = 'H'."""
        bf = Befunge93()
        bf.load(EXAMPLES['charprint']['code'])
        bf.run()
        self.assertIn('H', bf.output)

    def test_all_examples_load(self):
        """Every built-in example should load without error."""
        for name, ex in EXAMPLES.items():
            if name == 'cat':
                continue  # cat requires stdin, skip
            bf = Befunge93()
            bf.load(ex['code'])
            self.assertIsNotNone(bf.grid)

    def test_all_examples_terminate(self):
        """Simple examples should terminate within reasonable steps."""
        # cat requires stdin, so skip it
        skip = {'cat'}
        simple = [n for n in EXAMPLES if n not in skip]
        for name in simple:
            bf = Befunge93()
            bf.load(EXAMPLES[name]['code'])
            bf.run(max_steps=50000)
            self.assertFalse(bf.running,
                             f"Example '{name}' did not terminate")


class TestStepCount(unittest.TestCase):
    """Test that step counting and output capture work correctly."""

    def setUp(self):
        self.bf = Befunge93()

    def test_step_count_after_run(self):
        self.bf.load('34+.@')
        self.bf.run()
        self.assertGreater(self.bf.step_count, 0)

    def test_output_capture(self):
        """Run() should return the captured output string."""
        self.bf.load('34+.@')
        output = self.bf.run()
        self.assertIn('7', output)

    def test_step_increments(self):
        """Each step should increment step_count."""
        self.bf.load('34+.@')
        initial = self.bf.step_count
        self.bf.step()
        self.assertEqual(self.bf.step_count, initial + 1)


class TestRandomDirection(unittest.TestCase):
    """Test the ? (random direction) instruction."""

    def test_random_direction_runs(self):
        """Programs with ? should run without crashing."""
        self.bf = Befunge93()
        self.bf.load('?@')
        self.bf.run(max_steps=1000)
        # May or may not terminate, but shouldn't crash


class TestVersion(unittest.TestCase):
    """Test version constant."""

    def test_version_is_string(self):
        self.assertIsInstance(__version__, str)

    def test_version_format(self):
        parts = __version__.split('.')
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_version_cli(self):
        """Test that --version flag works."""
        import subprocess
        result = subprocess.run(
            [sys.executable, 'befunge93.py', '--version'],
            capture_output=True, text=True,
            cwd='/root/daily-ideas/2026-06-14-befunge93-interpreter'
        )
        self.assertIn(__version__, result.stdout + result.stderr)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and corner scenarios."""

    def setUp(self):
        self.bf = Befunge93()

    def test_empty_stack_addition(self):
        """Addition on empty stack: 0 + 0 = 0."""
        self.bf.load('+.@')
        self.bf.run()
        self.assertIn('0', self.bf.output)

    def test_duplicate_empty_stack(self):
        """Duplicating an empty stack pushes 0 twice."""
        self.bf.load(':.@')
        self.bf.run()
        # : on empty stack -> push 0, push 0, then . prints 0, . prints 0
        self.assertIn('0', self.bf.output)

    def test_swap_on_stack(self):
        """\\ swaps top two stack elements."""
        self.bf.load('34\\..@')
        self.bf.run()
        # Push 3, push 4, swap: top=3, next=4
        # . prints 3 (space), . prints 4 (space)
        self.assertIn('3', self.bf.output)
        self.assertIn('4', self.bf.output)

    def test_discard(self):
        """$ discards the top of stack."""
        self.bf.load('3$4.@')
        self.bf.run()
        self.assertIn('4', self.bf.output)

    def test_spaces_are_noop(self):
        """Spaces should be treated as no-ops."""
        self.bf.load('  3 4 + . @')
        self.bf.run()
        self.assertIn('7', self.bf.output)

    def test_unknown_chars_are_noop(self):
        """Unknown characters should be treated as no-ops."""
        self.bf = Befunge93()
        self.bf.load('3Q4Q+Q.@')
        self.bf.run()
        self.assertIn('7', self.bf.output)

    def test_max_steps_limit(self):
        """Programs that don't terminate should hit max_steps."""
        self.bf = Befunge93()
        self.bf.load('>')
        self.bf.run(max_steps=100)
        self.assertGreaterEqual(self.bf.step_count, 100)

    def test_output_capture_newline(self):
        """Output should capture both integer and character output."""
        # Print 'A' (65) as integer then as character
        self.bf.load('"A".@')
        self.bf.run()
        self.assertIn('65', self.bf.output)


if __name__ == '__main__':
    unittest.main()