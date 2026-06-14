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
"""

import sys
import time
import argparse
import random
from typing import List, Optional


# Grid dimensions for Befunge-93
COLS = 80
ROWS = 25

# Direction vectors: (dx, dy)
RIGHT = (1, 0)
LEFT = (-1, 0)
UP = (0, -1)
DOWN = (0, 1)


class Befunge93:
    """Complete Befunge-93 interpreter."""

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

    def load(self, program: str):
        """Load a Befunge-93 program from a string."""
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
        """Load a Befunge-93 program from a file."""
        with open(filename, 'r') as f:
            self.load(f.read())

    def push(self, val: int):
        """Push a value onto the stack."""
        self.stack.append(val)

    def pop(self) -> int:
        """Pop a value from the stack (returns 0 if empty)."""
        if not self.stack:
            return 0
        return self.stack.pop()

    def peek(self) -> int:
        """Peek at top of stack (returns 0 if empty)."""
        if not self.stack:
            return 0
        return self.stack[-1]

    def move(self):
        """Move the instruction pointer in the current direction, wrapping."""
        self.x = (self.x + self.dx) % COLS
        self.y = (self.y + self.dy) % ROWS

    def execute(self, instruction: str):
        """Execute a single Befunge-93 instruction."""
        if self.string_mode:
            if instruction == '"':
                self.string_mode = False
            else:
                self.push(ord(instruction))
            return

        # Stack manipulation
        if instruction.isdigit():
            self.push(int(instruction))
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
                self.push(0)
            else:
                # Python-style integer division with floor
                self.push(int(a / b))
        elif instruction == '%':
            b, a = self.pop(), self.pop()
            if b == 0:
                self.push(0)
            else:
                self.push(a % b)
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

        # Conditional
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
            val = self.pop()
            self.push(val)
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
            print(val, end=' ', flush=True)
        elif instruction == ',':
            val = self.pop()
            print(chr(val & 0xFF), end='', flush=True)
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
                    self.push(-1)
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

        # Everything else is a no-op
        else:
            pass

    def step(self) -> bool:
        """Execute one step of the interpreter. Returns False if program ended."""
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

    def run(self, max_steps: int = 1000000):
        """Run the program until it ends or max_steps is reached."""
        while self.running and self.step_count < max_steps:
            if not self.step():
                break

        if self.step_count >= max_steps:
            print(f"\n[Program did not terminate within {max_steps} steps]", file=sys.stderr)

    def _debug_print(self, instruction: str):
        """Print debug info for current step."""
        stack_str = ' '.join(str(s) for s in self.stack[-10:])
        direction = {(1, 0): '→', (-1, 0): '←', (0, -1): '↑', (0, 1): '↓'}
        d = direction.get((self.dx, self.dy), '?')
        print(f"[{self.step_count:4d}] ({self.x:2d},{self.y:2d}) {d} '{instruction}' stack=[{stack_str}]",
              file=sys.stderr)


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
}


def list_examples():
    """Print available example programs."""
    print("Available example programs:")
    print("-" * 50)
    for key, ex in EXAMPLES.items():
        print(f"  {key:12s}  {ex['name']}")
        print(f"  {'':12s}  {ex['description']}")
        print()
    print("Use: befunge93.py --example <name>")
    print("Use: befunge93.py --example <name> --debug  for step-by-step")


def show_example(name: str):
    """Show the source code of an example program."""
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
    """Run in interactive step-by-step mode with a visual display."""
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
        print(f"  Step: {interpreter.step_count}  Pos: ({interpreter.x},{interpreter.y})  Dir: {d}")
        print(f"  String mode: {'ON' if interpreter.string_mode else 'OFF'}")
        print(f"  Stack (top 10): [{stack_display}]")
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


def main():
    parser = argparse.ArgumentParser(
        description='Befunge-93 Esoteric Language Interpreter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s program.bf              Run a Befunge-93 program
  %(prog)s --example hello          Run the Hello World example
  %(prog)s --list                  List available examples
  %(prog)s --show hello            Show example source code
  %(prog)s --interactive            Run in step-by-step visual mode
  %(prog)s program.bf --debug      Run with debug output
        """
    )
    parser.add_argument('file', nargs='?', help='Befunge-93 source file to run')
    parser.add_argument('--example', '-e', help='Run a built-in example program')
    parser.add_argument('--list', '-l', action='store_true', help='List available example programs')
    parser.add_argument('--show', '-s', help='Show source code of an example program')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
    parser.add_argument('--delay', type=int, default=0, help='Delay in ms between steps')
    parser.add_argument('--max-steps', type=int, default=1000000, help='Maximum steps before forcing stop')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive step-by-step mode')
    parser.add_argument('--cat', '-c', action='store_true', help='Just display the program grid and exit')

    args = parser.parse_args()

    if args.list:
        list_examples()
        return

    if args.show:
        show_example(args.show)
        return

    interpreter = Befunge93(debug=args.debug, delay=args.delay)

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
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        print("\nNo program specified. Use --example <name> or provide a .bf file.")
        print("Use --list to see available examples.")
        sys.exit(1)

    if args.cat:
        # Just display the grid
        print("Befunge-93 Program Grid:")
        print("=" * (COLS + 2))
        for row in interpreter.grid:
            line = ''.join(row).rstrip()
            if line:
                print(f"|{line}|")
        print("=" * (COLS + 2))
        return

    if args.interactive:
        interactive_mode(interpreter)
    else:
        interpreter.run(max_steps=args.max_steps)


if __name__ == '__main__':
    main()