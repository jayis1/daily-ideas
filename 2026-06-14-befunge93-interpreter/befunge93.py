#!/usr/bin/env python3
"""
Befunge-93 Interpreter
=======================
A complete interpreter for the Befunge-93 esoteric programming language.

Befunge-93 is a 2D language where instructions are laid out on an 80x25 grid.
The instruction pointer (IP) moves in one of four cardinal directions
(left, right, up, down), and can be redirected by instructions.
It features a stack-based computation model with self-modifying code.

Specification: https://esolangs.org/wiki/Befunge

Features:
  - Full Befunge-93 specification (all 37 instructions)
  - Interactive step-by-step visual mode
  - Debug mode with stack tracing
  - Built-in example programs
  - Program validation (--validate)
  - Step counter and output capture
  - Configurable step limit and delay
  - --version and --help CLI flags
"""

import sys
import time
import argparse
import random
from typing import List, Optional

__version__ = "1.1.0"

# Grid dimensions for Befunge-93
COLS = 80
ROWS = 25

# Direction vectors: (dx, dy)
RIGHT = (1, 0)
LEFT = (-1, 0)
UP = (0, -1)
DOWN = (0, 1)

# Valid Befunge-93 instructions (for validation)
VALID_INSTRUCTIONS = set("0123456789+-*/%!`><^v?:.\\$_@\"#gp&~")


class Befunge93:
    """Complete Befunge-93 interpreter with debug and validation support.

    Attributes:
        grid: 2D list of single-character strings representing the program.
        stack: List of integers used as the operand stack.
        x, y: Current instruction pointer position.
        dx, dy: Current direction vector.
        running: Whether the program is still executing.
        string_mode: Whether string mode is active (pushing ASCII values).
        output: Captured output from . and , instructions.
        step_count: Number of steps executed so far.
        debug: Whether to print debug traces to stderr.
        delay: Milliseconds to pause between steps (for visualization).
    """

    def __init__(self, debug: bool = False, delay: int = 0):
        self.grid: List[List[str]] = []
        self.stack: List[int] = []
        self.x = 0
        self.y = 0
        self.dx, self.dy = RIGHT
        self.running = True
        self.string_mode = False
        self.debug = debug
        self.delay = delay  # milliseconds between steps
        self.step_count = 0
        self.output = ""  # captured program output

    def load(self, program: str):
        """Load a Befunge-93 program from a string.

        Programs longer than 80 columns or 25 rows are silently truncated
        to fit the Befunge-93 grid dimensions.

        Args:
            program: The Befunge-93 source code as a string.
        """
        self.grid = [[' '] * COLS for _ in range(ROWS)]
        lines = program.split('\n')
        for y, line in enumerate(lines):
            if y >= ROWS:
                break
            for x, ch in enumerate(line):
                if x >= COLS:
                    break
                self.grid[y][x] = ch

    def load_file(self, filename: str):
        """Load a Befunge-93 program from a file.

        Args:
            filename: Path to the .bf source file.

        Raises:
            FileNotFoundError: If the file does not exist.
            UnicodeDecodeError: If the file cannot be decoded as UTF-8.
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.load(f.read())
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: File not found: {filename}")

    def push(self, val: int):
        """Push a value onto the stack.

        Args:
            val: Integer value to push.
        """
        self.stack.append(val)

    def pop(self) -> int:
        """Pop a value from the stack.

        Returns 0 if the stack is empty, per the Befunge-93 specification.

        Returns:
            The top value of the stack, or 0 if empty.
        """
        if not self.stack:
            return 0
        return self.stack.pop()

    def peek(self) -> int:
        """Peek at the top of the stack without removing it.

        Returns 0 if the stack is empty, per the Befunge-93 specification.

        Returns:
            The top value of the stack, or 0 if empty.
        """
        if not self.stack:
            return 0
        return self.stack[-1]

    def move(self):
        """Move the instruction pointer in the current direction, wrapping.

        The grid is toroidal: moving past the right edge wraps to the left,
        moving past the bottom wraps to the top, etc.
        """
        self.x = (self.x + self.dx) % COLS
        self.y = (self.y + self.dy) % ROWS

    def execute(self, instruction: str):
        """Execute a single Befunge-93 instruction.

        Implements the full Befunge-93 specification including:
        - Digit push (0-9)
        - Arithmetic (+, -, *, /, %)
        - Logical (!, `)
        - Direction change (>, <, ^, v, ?)
        - Conditionals (_, |)
        - Stack manipulation (:, \\, $)
        - I/O (., ,, &, ~)
        - String mode (")
        - Self-modification (g, p)
        - Bridge (#)
        - End (@)

        Args:
            instruction: A single character representing the instruction.
        """
        if self.string_mode:
            if instruction == '"':
                self.string_mode = False
            else:
                self.push(ord(instruction))
            return

        # Digit push
        if instruction.isdigit():
            self.push(int(instruction))

        # Arithmetic
        elif instruction == '+':
            b, a = self.pop(), self.pop()
            self.push(a + b)
        elif instruction == '-':
            b, a = self.pop(), self.pop()
            self.push(a - b)
        elif instruction == '*':
            b, a = self.pop(), self.pop()
            self.push(a * b)
        elif instruction == '/':
            b, a = self.pop(), self.pop()
            if b == 0:
                # Befunge-93 spec: division by zero pushes 0
                self.push(0)
            else:
                # Use truncation toward zero (C-style), matching the spec
                result = abs(a) // abs(b)
                if (a < 0) != (b < 0) and result != 0:
                    result = -result
                self.push(result)
        elif instruction == '%':
            b, a = self.pop(), self.pop()
            if b == 0:
                self.push(0)
            else:
                # C-style modulo: result has same sign as dividend
                result = a % b
                # Python's % gives result with same sign as divisor;
                # Befunge uses C-style where result sign matches dividend
                if a < 0 and result > 0:
                    result -= abs(b)
                elif a > 0 and result < 0:
                    result += abs(b)
                self.push(result)

        # Logical
        elif instruction == '!':
            val = self.pop()
            self.push(1 if val == 0 else 0)
        elif instruction == '`':
            b, a = self.pop(), self.pop()
            self.push(1 if a > b else 0)

        # Direction changing
        elif instruction == '>':
            self.dx, self.dy = RIGHT
        elif instruction == '<':
            self.dx, self.dy = LEFT
        elif instruction == '^':
            self.dx, self.dy = UP
        elif instruction == 'v':
            self.dx, self.dy = DOWN
        elif instruction == '?':
            # Random direction
            direction = random.choice([RIGHT, LEFT, UP, DOWN])
            self.dx, self.dy = direction

        # Conditionals
        elif instruction == '_':
            val = self.pop()
            if val == 0:
                self.dx, self.dy = RIGHT
            else:
                self.dx, self.dy = LEFT
        elif instruction == '|':
            val = self.pop()
            if val == 0:
                self.dx, self.dy = DOWN
            else:
                self.dx, self.dy = UP

        # Stack manipulation
        elif instruction == ':':
            val = self.peek()
            self.push(val)
        elif instruction == '\\':
            b, a = self.pop(), self.pop()
            self.push(b)
            self.push(a)
        elif instruction == '$':
            self.pop()

        # I/O
        elif instruction == '.':
            val = self.pop()
            text = f"{val} "
            self.output += text
            print(text, end='', flush=True)
        elif instruction == ',':
            val = self.pop()
            ch = chr(val & 0xFF)
            self.output += ch
            print(ch, end='', flush=True)
        elif instruction == '&':
            try:
                val = int(input())
                self.push(val)
            except (ValueError, EOFError):
                self.push(0)
        elif instruction == '~':
            try:
                ch = sys.stdin.read(1)
                if ch:
                    self.push(ord(ch))
                else:
                    self.push(-1)  # EOF
            except EOFError:
                self.push(-1)

        # String mode
        elif instruction == '"':
            self.string_mode = True

        # Self-modification / get/put
        elif instruction == 'g':
            y_val = self.pop()
            x_val = self.pop()
            if 0 <= x_val < COLS and 0 <= y_val < ROWS:
                self.push(ord(self.grid[y_val][x_val]))
            else:
                self.push(0)
        elif instruction == 'p':
            y_val = self.pop()
            x_val = self.pop()
            val = self.pop()
            if 0 <= x_val < COLS and 0 <= y_val < ROWS:
                self.grid[y_val][x_val] = chr(val & 0xFF)

        # Bridge (skip next cell)
        elif instruction == '#':
            self.move()

        # No-op
        elif instruction == ' ':
            pass

        # End program
        elif instruction == '@':
            self.running = False

        # Unknown instructions are treated as no-ops (per spec)
        else:
            pass

    def step(self) -> bool:
        """Execute one step of the interpreter.

        Returns:
            True if the program should continue, False if it has ended.
        """
        if not self.running:
            return False

        instruction = self.grid[self.y][self.x]
        self.execute(instruction)

        if not self.running:
            return False

        self.move()
        self.step_count += 1

        if self.debug:
            self._debug_print(instruction)

        if self.delay > 0:
            time.sleep(self.delay / 1000.0)

        return True

    def run(self, max_steps: int = 1000000) -> str:
        """Run the program until it ends or max_steps is reached.

        Args:
            max_steps: Maximum number of steps before forcing termination.

        Returns:
            The captured output string from the program.
        """
        while self.running and self.step_count < max_steps:
            if not self.step():
                break

        if self.step_count >= max_steps:
            print(f"\n[Program did not terminate within {max_steps} steps]",
                  file=sys.stderr)

        return self.output

    def _debug_print(self, instruction: str):
        """Print debug info for current step to stderr.

        Args:
            instruction: The instruction character just executed.
        """
        stack_str = ' '.join(str(s) for s in self.stack[-10:])
        direction = {(1, 0): '→', (-1, 0): '←', (0, -1): '↑', (0, 1): '↓'}
        d = direction.get((self.dx, self.dy), '?')
        print(f"[{self.step_count:4d}] ({self.x:2d},{self.y:2d}) {d} "
              f"'{instruction}' stack=[{stack_str}]",
              file=sys.stderr)

    def validate(self) -> List[str]:
        """Validate the loaded program and return a list of warnings.

        Checks for common issues like missing @ terminator, programs
        that might be infinite loops, and other potential problems.

        Returns:
            List of warning messages (empty if no issues found).
        """
        warnings = []

        # Check if program has any non-space content
        has_content = False
        has_terminator = False
        instruction_chars = set()

        for y in range(ROWS):
            for x in range(COLS):
                ch = self.grid[y][x]
                if ch != ' ':
                    has_content = True
                    instruction_chars.add(ch)
                    if ch == '@':
                        has_terminator = True

        if not has_content:
            warnings.append("Program grid is empty — nothing to execute.")
            return warnings

        if not has_terminator:
            warnings.append(
                "No '@' (end) instruction found. "
                "Program may run until max_steps is reached."
            )

        # Check for unknown characters (potential typos)
        unknown = instruction_chars - VALID_INSTRUCTIONS - {' '}
        if unknown:
            warnings.append(
                f"Unknown characters treated as no-ops: "
                f"{', '.join(repr(c) for c in sorted(unknown))}"
            )

        # Check for potential issues with input instructions
        if '&' in instruction_chars or '~' in instruction_chars:
            warnings.append(
                "Program contains input instructions (& or ~). "
                "Make sure to provide input when running."
            )

        return warnings


# ============================================================
# Example Befunge-93 programs
# ============================================================

EXAMPLES = {
    "hello": {
        "name": "Hello, World!",
        "description": "Classic Hello World using Befunge string mode",
        "code": r'0"!dlroW ,olleH">:#,_@',
    },
    "add": {
        "name": "Add Two Numbers",
        "description": "Adds 3 and 4 and prints the result (7)",
        "code": '34+.@',
    },
    "multiply": {
        "name": "Multiply Two Numbers",
        "description": "Multiplies 6 and 7 and prints the result (42)",
        "code": '67*.@',
    },
    "echo_digits": {
        "name": "Echo Digits",
        "description": "Prints digits 1 through 5",
        "code": '1.2.3.4.5.@',
    },
    "double": {
        "name": "Double Numbers",
        "description": "Prints 2, 8, 18, 32 (squares of 1,2,3,4 times 2)",
        "code": '12*. 24*. 36*. 48*.@',
    },
    "reverse": {
        "name": "Reverse Print",
        "description": "Pushes '!dlroW' backwards and prints it reversed",
        "code": r'0"!dlroW">:#,_@',
    },
    "truth": {
        "name": "The Answer",
        "description": "Prints 42 — the answer to life, the universe, and everything",
        "code": '67*.@',
    },
    "countdown": {
        "name": "Countdown",
        "description": "Counts down from 5 using string mode tricks",
        "code": '55*1-. 55*2-. 55*3-. 55*4-. 55*5-.@',
    },
    "factorial": {
        "name": "Factorial",
        "description": "Computes and prints 5! = 120 using chained multiplication",
        "code": '54*3*2*1*.@',
    },
    "divider": {
        "name": "Division",
        "description": "Divides 14 by 3, producing 4 (truncation toward zero)",
        "code": '77+3/.@',
    },
    "modulo": {
        "name": "Modulo",
        "description": "Computes 14 mod 3 = 2",
        "code": '77+3%.@',
    },
    "charprint": {
        "name": "Character Print",
        "description": "Prints the letter 'H' using multiplication and char output",
        "code": '89*,@',
    },
    "cat": {
        "name": "Cat Program",
        "description": "Echoes input until EOF (Befunge 'cat')",
        "code": '~:,25*,@',
    },
}


def list_examples():
    """Print a formatted list of available example programs."""
    print("Available example programs:")
    print("-" * 50)
    for key, ex in EXAMPLES.items():
        print(f"  {key:12s}  {ex['name']}")
        print(f"  {'':12s}  {ex['description']}")
        print()


def show_example(name: str):
    """Show the source code of an example program.

    Args:
        name: The example key (e.g., 'hello', 'add').
    """
    if name not in EXAMPLES:
        print(f"Unknown example: {name}")
        print(f"Available: {', '.join(EXAMPLES.keys())}")
        return
    ex = EXAMPLES[name]
    print(f"--- {ex['name']} ---")
    print(ex['description'])
    print()
    for i, line in enumerate(ex['code'].split('\n')):
        print(f"  {i:2d} | {line}")
    print()


def interactive_mode(interpreter: Befunge93):
    """Run in interactive step-by-step mode with a visual display.

    Displays the program grid with the current instruction pointer
    highlighted, along with stack contents and step counter.

    Controls:
        Enter  — Step one instruction
        number — Step that many instructions
        r      — Run to completion
        d      — Toggle debug output
        q      — Quit

    Args:
        interpreter: A loaded Befunge93 instance ready to execute.
    """
    import shutil

    def render():
        """Render the current grid state with IP highlighted."""
        term_w = shutil.get_terminal_size((80, 24)).columns
        # Show a portion of the grid around the IP
        view_w = min(60, term_w - 4)
        view_h = 15

        start_x = max(0, min(interpreter.x - view_w // 2, COLS - view_w))
        start_y = max(0, min(interpreter.y - view_h // 2, ROWS - view_h))

        print("\033[2J\033[H", end='')  # Clear screen

        print("╔" + "═" * view_w + "╗")
        for dy in range(view_h):
            y = start_y + dy
            if y >= ROWS:
                break
            row = ""
            for dx in range(view_w):
                x = start_x + dx
                if x >= COLS:
                    break
                ch = interpreter.grid[y][x]
                if x == interpreter.x and y == interpreter.y:
                    row += f"\033[7m{ch}\033[0m"  # Reverse video for IP
                elif ch != ' ':
                    row += ch
                else:
                    row += ' '
            print(f"║{row:<{view_w}}║")

        print("╚" + "═" * view_w + "╝")

        direction = {(1, 0): '→', (-1, 0): '←', (0, -1): '↑', (0, 1): '↓'}
        d = direction.get((interpreter.dx, interpreter.dy), '?')
        stack_display = ' '.join(str(s) for s in interpreter.stack[-10:])
        print(f"  Step: {interpreter.step_count}  "
              f"Pos: ({interpreter.x},{interpreter.y})  Dir: {d}")
        print(f"  String mode: {'ON' if interpreter.string_mode else 'OFF'}")
        print(f"  Stack (top 10): [{stack_display}]")
        if interpreter.output:
            preview = interpreter.output[-40:]
            print(f"  Output: ...{preview}")
        print()
        print("  [Enter] Step  [R] Run  [Q] Quit  [D] Toggle debug")

    print("Befunge-93 Interactive Mode")
    print("===========================")
    print()

    while interpreter.running:
        render()
        try:
            cmd = input("> ").strip().lower()
        except EOFError:
            break

        if cmd == 'q':
            break
        elif cmd == 'r':
            # Run to completion
            interpreter.run()
            break
        elif cmd == 'd':
            interpreter.debug = not interpreter.debug
        elif cmd == '':
            # Single step
            if not interpreter.step():
                break
        else:
            # Step N times
            try:
                n = int(cmd)
                for _ in range(n):
                    if not interpreter.step():
                        break
            except ValueError:
                pass

    if not interpreter.running:
        print(f"\nProgram ended after {interpreter.step_count} steps.")
        if interpreter.output:
            print(f"Output: {interpreter.output}")


def main():
    """Entry point for the Befunge-93 interpreter CLI."""
    parser = argparse.ArgumentParser(
        prog='befunge93',
        description='Befunge-93 Esoteric Language Interpreter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s program.bf              Run a Befunge-93 program
  %(prog)s --example hello          Run the Hello World example
  %(prog)s --list                  List available examples
  %(prog)s --show hello            Show example source code
  %(prog)s --interactive program.bf   Step-by-step visual mode
  %(prog)s program.bf --debug      Run with debug output
  %(prog)s program.bf --validate   Check program for issues
  %(prog)s --version               Show version
        """
    )
    parser.add_argument('file', nargs='?', help='Befunge-93 source file to run')
    parser.add_argument('--example', '-e', help='Run a built-in example program')
    parser.add_argument('--list', '-l', action='store_true',
                        help='List available example programs')
    parser.add_argument('--show', '-s', help='Show source code of an example')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug output (traces every step)')
    parser.add_argument('--delay', type=int, default=0,
                        help='Delay in ms between steps (for visualization)')
    parser.add_argument('--max-steps', type=int, default=1000000,
                        help='Maximum steps before forcing stop (default: 1000000)')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Interactive step-by-step mode')
    parser.add_argument('--cat', '-c', action='store_true',
                        help='Display the program grid and exit')
    parser.add_argument('--validate', '-V', action='store_true',
                        help='Validate the program and show warnings')
    parser.add_argument('--version', action='version',
                        version=f'Befunge-93 Interpreter v{__version__}')

    args = parser.parse_args()

    if args.list:
        list_examples()
        return

    if args.show:
        show_example(args.show)
        return

    interpreter = Befunge93(debug=args.debug, delay=args.delay)

    # Load program from file or example
    if args.example:
        if args.example not in EXAMPLES:
            print(f"Unknown example: {args.example}")
            print(f"Available: {', '.join(EXAMPLES.keys())}")
            sys.exit(1)
        interpreter.load(EXAMPLES[args.example]['code'])
        print(f"--- Running: {EXAMPLES[args.example]['name']} ---")
        print(f"{EXAMPLES[args.example]['description']}")
        print()
    elif args.file:
        try:
            interpreter.load_file(args.file)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except UnicodeDecodeError:
            print(f"Error: File {args.file} is not valid UTF-8 text.",
                  file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        print("\nNo program specified. Use --example <name> or provide a .bf file.")
        print("Use --list to see available examples.")
        sys.exit(1)

    # Validate mode
    if args.validate:
        warnings = interpreter.validate()
        if warnings:
            print(f"Program validation for {args.file or 'example'}:")
            for w in warnings:
                print(f"  ⚠ {w}")
        else:
            print("Program looks valid. No issues found.")
        return

    # Cat mode — just display the grid
    if args.cat:
        print("Befunge-93 Program Grid:")
        print("=" * (COLS + 2))
        for row in interpreter.grid:
            line = ''.join(row).rstrip()
            if line:
                print(f"|{line}|")
        print("=" * (COLS + 2))
        return

    # Run mode
    if args.interactive:
        interactive_mode(interpreter)
    else:
        interpreter.run(max_steps=args.max_steps)
        print()  # Ensure newline after program output
        if args.debug:
            print(f"\n[Program finished in {interpreter.step_count} steps]",
                  file=sys.stderr)
            print(f"[Output length: {len(interpreter.output)} chars]",
                  file=sys.stderr)


if __name__ == '__main__':
    main()