#!/usr/bin/env python3
"""
Terminal Spreadsheet — A fully interactive, curses-based mini spreadsheet.

Features:
  - Navigate cells with arrow keys or hjkl
  - Type values or formulas (formulas start with =)
  - Cell references like A1, B3, Z26
  - Arithmetic: +, -, *, /, ^, %
  - Functions: SUM, AVG, MIN, MAX, COUNT over ranges like A1:B3
  - Delete cells with Backspace/Delete
  - Press : to enter command mode (:q to quit, :w to resize)
  - Press e to edit the current cell
  - Status bar shows cell coordinate and formula

No external dependencies — uses only the Python standard library.
"""

import curses
import re
import sys
import copy
from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────

MAX_ROWS = 100
MAX_COLS = 26  # A–Z
COL_WIDTH = 10
ROW_HEADER_WIDTH = 4

# ── Helpers ──────────────────────────────────────────────────────────────────

def col_to_letter(col: int) -> str:
    """0 → A, 1 → B, …, 25 → Z"""
    return chr(ord('A') + col)


def letter_to_col(letter: str) -> int:
    """A → 0, B → 1, …, Z → 25"""
    return ord(letter.upper()) - ord('A')


def cell_name(row: int, col: int) -> str:
    """(0, 0) → 'A1'"""
    return f"{col_to_letter(col)}{row + 1}"


def parse_cell_name(name: str):
    """'A1' → (0, 0), 'Z26' → (25, 25)"""
    m = re.match(r'^([A-Za-z])(\d+)$', name)
    if not m:
        return None
    col = letter_to_col(m.group(1))
    row = int(m.group(2)) - 1
    if 0 <= row < MAX_ROWS and 0 <= col < MAX_COLS:
        return (row, col)
    return None


# ── Tokenizer / Parser ──────────────────────────────────────────────────────

def tokenize(expr: str):
    """Tokenize a formula expression into a list of tokens."""
    tokens = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        # Number (integer or float)
        if ch.isdigit() or (ch == '.' and i + 1 < len(expr) and expr[i + 1].isdigit()):
            j = i
            has_dot = False
            while j < len(expr) and (expr[j].isdigit() or (expr[j] == '.' and not has_dot)):
                if expr[j] == '.':
                    has_dot = True
                j += 1
            tokens.append(('NUM', float(expr[i:j])))
            i = j
        # Cell reference or range
        elif ch.isalpha():
            j = i
            while j < len(expr) and (expr[j].isalpha() or expr[j].isdigit()):
                j += 1
            word = expr[i:j]
            # Check if it's a function name
            if word.upper() in ('SUM', 'AVG', 'MIN', 'MAX', 'COUNT', 'ABS', 'INT', 'ROUND', 'SQRT', 'IF'):
                tokens.append(('FUNC', word.upper()))
            # Check for cell reference possibly part of a range
            elif re.match(r'^[A-Za-z]\d+$', word):
                tokens.append(('CELL', word.upper()))
            else:
                tokens.append(('NAME', word.upper()))
            i = j
        # Operators
        elif ch in '+-*/^%':
            tokens.append(('OP', ch))
            i += 1
        elif ch == '(':
            tokens.append(('LPAREN', '('))
            i += 1
        elif ch == ')':
            tokens.append(('RPAREN', ')'))
            i += 1
        elif ch == ':':
            tokens.append(('COLON', ':'))
            i += 1
        elif ch == ',':
            tokens.append(('COMMA', ','))
            i += 1
        elif ch == '=':
            tokens.append(('OP', '=='))
            i += 1
        elif ch == '<':
            if i + 1 < len(expr) and expr[i + 1] == '=':
                tokens.append(('OP', '<='))
                i += 2
            else:
                tokens.append(('OP', '<'))
                i += 1
        elif ch == '>':
            if i + 1 < len(expr) and expr[i + 1] == '=':
                tokens.append(('OP', '>='))
                i += 2
            else:
                tokens.append(('OP', '>'))
                i += 1
        elif ch == '!':
            # Boolean not
            tokens.append(('OP', '!'))
            i += 1
        else:
            i += 1  # skip unknown chars
    return tokens


def parse_range(tokens, pos):
    """Parse a range like A1:B3, returns (start_row, start_col, end_row, end_col) or None."""
    if pos >= len(tokens):
        return None, pos
    if tokens[pos][0] != 'CELL':
        return None, pos
    start = parse_cell_name(tokens[pos][1])
    if start is None:
        return None, pos
    if pos + 1 < len(tokens) and tokens[pos + 1][0] == 'COLON' and pos + 2 < len(tokens) and tokens[pos + 2][0] == 'CELL':
        end = parse_cell_name(tokens[pos + 2][1])
        if end is None:
            return None, pos
        return (start[0], start[1], end[0], end[1]), pos + 3
    # Single cell as range
    return (start[0], start[1], start[0], start[1]), pos + 1


# ── Spreadsheet Engine ───────────────────────────────────────────────────────

class Spreadsheet:
    def __init__(self):
        self.cells = {}   # (row, col) → raw string content
        self.cache = {}   # (row, col) → evaluated value
        self.error_cells = set()

    def set_cell(self, row: int, col: int, value: str):
        """Set a cell's raw content and clear caches."""
        key = (row, col)
        if value == '' or value is None:
            self.cells.pop(key, None)
            self.cache.pop(key, None)
            self.error_cells.discard(key)
        else:
            self.cells[key] = str(value)
            self._invalidate(key)

    def get_raw(self, row: int, col: int) -> str:
        return self.cells.get((row, col), '')

    def get_value(self, row: int, col: int) -> Any:
        """Get the evaluated value of a cell."""
        key = (row, col)
        if key in self.cache:
            return self.cache[key]
        if key not in self.cells:
            self.cache[key] = 0
            return 0
        raw = self.cells[key]
        if raw.startswith('='):
            val = self._evaluate_formula(raw[1:], key)
        else:
            val = self._coerce(raw)
        self.cache[key] = val
        return val

    def _invalidate(self, key):
        """Invalidate cache for a cell and all dependents (simple: invalidate all)."""
        self.cache.clear()
        self.error_cells.clear()

    def _coerce(self, s: str) -> Any:
        """Try to coerce a string to a number."""
        try:
            if '.' in s:
                return float(s)
            return int(s)
        except ValueError:
            return s

    def _evaluate_formula(self, expr: str, source_cell: tuple) -> Any:
        """Evaluate a formula string. source_cell is (row, col) for circular ref detection."""
        try:
            tokens = tokenize(expr)
            pos = [0]  # mutable position tracker
            result = self._parse_expression(tokens, pos, source_cell)
            return result
        except Exception as e:
            key = source_cell
            self.error_cells.add(key)
            return f"ERR: {e}"

    def _parse_expression(self, tokens, pos, source):
        """Parse addition / subtraction level."""
        left = self._parse_term(tokens, pos, source)
        while pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] in ('+', '-'):
            op = tokens[pos[0]][1]
            pos[0] += 1
            right = self._parse_term(tokens, pos, source)
            if op == '+':
                left = left + right
            else:
                left = left - right
        return left

    def _parse_term(self, tokens, pos, source):
        """Parse multiplication / division / modulo."""
        left = self._parse_power(tokens, pos, source)
        while pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] in ('*', '/', '%'):
            op = tokens[pos[0]][1]
            pos[0] += 1
            right = self._parse_power(tokens, pos, source)
            if op == '*':
                left = left * right
            elif op == '/':
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                left = left / right
            else:
                left = left % right
        return left

    def _parse_power(self, tokens, pos, source):
        """Parse exponentiation (right-associative)."""
        base = self._parse_unary(tokens, pos, source)
        if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '^':
            pos[0] += 1
            exp = self._parse_power(tokens, pos, source)  # right-associative
            return base ** exp
        return base

    def _parse_unary(self, tokens, pos, source):
        """Parse unary minus/plus."""
        if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '-':
            pos[0] += 1
            return -self._parse_unary(tokens, pos, source)
        if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '+':
            pos[0] += 1
            return self._parse_unary(tokens, pos, source)
        return self._parse_primary(tokens, pos, source)

    def _parse_primary(self, tokens, pos, source):
        """Parse primary expressions: numbers, cell refs, function calls, parens."""
        if pos[0] >= len(tokens):
            return 0

        tok = tokens[pos[0]]

        # Number literal
        if tok[0] == 'NUM':
            pos[0] += 1
            return tok[1]

        # Parenthesized expression
        if tok[0] == 'LPAREN':
            pos[0] += 1
            val = self._parse_expression(tokens, pos, source)
            if pos[0] < len(tokens) and tokens[pos[0]][0] == 'RPAREN':
                pos[0] += 1
            return val

        # Function call
        if tok[0] == 'FUNC':
            func_name = tok[1]
            pos[0] += 1
            # Expect LPAREN
            if pos[0] < len(tokens) and tokens[pos[0]][0] == 'LPAREN':
                pos[0] += 1
            args = []
            # Parse arguments
            rng, new_pos = parse_range(tokens, pos[0])
            if rng is not None:
                pos[0] = new_pos
                args = self._expand_range(rng, source)
                # Check for more comma-separated args
                while pos[0] < len(tokens) and tokens[pos[0]][0] == 'COMMA':
                    pos[0] += 1
                    rng2, new_pos2 = parse_range(tokens, pos[0])
                    if rng2 is not None:
                        pos[0] = new_pos2
                        args.extend(self._expand_range(rng2, source))
                    else:
                        args.append(self._parse_expression(tokens, pos, source))
            else:
                # Single expression as arg
                args.append(self._parse_expression(tokens, pos, source))
                while pos[0] < len(tokens) and tokens[pos[0]][0] == 'COMMA':
                    pos[0] += 1
                    args.append(self._parse_expression(tokens, pos, source))

            # Expect RPAREN
            if pos[0] < len(tokens) and tokens[pos[0]][0] == 'RPAREN':
                pos[0] += 1

            return self._apply_function(func_name, args, source)

        # Cell reference
        if tok[0] == 'CELL':
            cell = parse_cell_name(tok[1])
            if cell is None:
                raise ValueError(f"Invalid cell reference: {tok[1]}")
            # Circular reference detection
            if cell == source:
                raise ValueError("Circular reference")
            pos[0] += 1
            val = self.get_value(cell[0], cell[1])
            if isinstance(val, str) and str(val).startswith("ERR:"):
                raise ValueError(val)
            return val

        # String literal (shouldn't normally hit this)
        pos[0] += 1
        return 0

    def _expand_range(self, rng, source):
        """Expand a range (r1, c1, r2, c2) into a list of cell values."""
        r1, c1, r2, c2 = rng
        values = []
        for r in range(min(r1, r2), max(r1, r2) + 1):
            for c in range(min(c1, c2), max(c1, c2) + 1):
                if (r, c) == source:
                    raise ValueError("Circular reference")
                val = self.get_value(r, c)
                if isinstance(val, (int, float)):
                    values.append(val)
        return values

    def _apply_function(self, name: str, args: list, source) -> Any:
        """Apply a spreadsheet function to a list of arguments."""
        nums = []
        for a in args:
            if isinstance(a, (int, float)):
                nums.append(a)

        if name == 'SUM':
            return sum(nums) if nums else 0
        elif name == 'AVG':
            return sum(nums) / len(nums) if nums else 0
        elif name == 'MIN':
            return min(nums) if nums else 0
        elif name == 'MAX':
            return max(nums) if nums else 0
        elif name == 'COUNT':
            return len(nums)
        elif name == 'ABS':
            return abs(nums[0]) if nums else 0
        elif name == 'INT':
            return int(nums[0]) if nums else 0
        elif name == 'ROUND':
            if len(nums) >= 2:
                return round(nums[0], int(nums[1]))
            return round(nums[0]) if nums else 0
        elif name == 'SQRT':
            import math
            return math.sqrt(nums[0]) if nums and nums[0] >= 0 else 0
        elif name == 'IF':
            # IF(condition, true_val, false_val)
            if len(args) >= 3:
                cond = args[0]
                if isinstance(cond, str):
                    cond = cond.lower() in ('true', '1', 'yes')
                return args[1] if cond else args[2]
            return 0
        else:
            raise ValueError(f"Unknown function: {name}")


# ── Curses UI ────────────────────────────────────────────────────────────────

class SpreadsheetUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.sheet = Spreadsheet()
        self.cursor_row = 0
        self.cursor_col = 0
        self.scroll_row = 0
        self.scroll_col = 0
        self.mode = 'NAV'  # NAV, EDIT, COMMAND
        self.input_buf = ''
        self.cmd_buf = ''
        self.status_msg = ''
        self.clipboard = None
        self.modified = False

        # Pre-populate with sample data
        self._load_sample_data()

    def _load_sample_data(self):
        """Load some sample data so the spreadsheet isn't empty on first run."""
        s = self.sheet
        # A simple budget spreadsheet
        data = {
            'A1': 'Item', 'B1': 'Jan', 'C1': 'Feb', 'D1': 'Mar', 'E1': 'Total',
            'A2': 'Rent', 'B2': '1200', 'C2': '1200', 'D2': '1200',
            'A3': 'Food', 'B3': '450', 'C3': '520', 'D3': '380',
            'A4': 'Transport', 'B4': '200', 'C4': '180', 'D4': '220',
            'A5': 'Fun', 'B5': '150', 'C5': '200', 'D5': '170',
            'A6': 'Total', 'B6': '=SUM(B2:B5)', 'C6': '=SUM(C2:C5)', 'D6': '=SUM(D2:D5)',
            'E2': '=SUM(B2:D2)', 'E3': '=SUM(B3:D3)', 'E4': '=SUM(B4:D4)', 'E5': '=SUM(B5:D5)',
            'E6': '=SUM(E2:E5)',
            'A8': 'Average', 'B8': '=AVG(B2:B5)', 'C8': '=AVG(C2:C5)', 'D8': '=AVG(D2:D5)',
        }
        for name, val in data.items():
            cell = parse_cell_name(name)
            if cell:
                s.set_cell(cell[0], cell[1], val)

    def run(self):
        curses.curs_set(1)
        self.stdscr.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # header
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)     # selected cell
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)     # formulas
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)      # errors
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # numbers
        curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)    # strings
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)      # command mode

        while True:
            self._draw()
            ch = self.stdscr.getch()
            if self.mode == 'NAV':
                self._handle_nav(ch)
            elif self.mode == 'EDIT':
                self._handle_edit(ch)
            elif self.mode == 'COMMAND':
                self._handle_command(ch)

    def _handle_nav(self, ch):
        if ch == curses.KEY_UP or ch == ord('k'):
            self.cursor_row = max(0, self.cursor_row - 1)
        elif ch == curses.KEY_DOWN or ch == ord('j'):
            self.cursor_row = min(MAX_ROWS - 1, self.cursor_row + 1)
        elif ch == curses.KEY_LEFT or ch == ord('h'):
            self.cursor_col = max(0, self.cursor_col - 1)
        elif ch == curses.KEY_RIGHT or ch == ord('l'):
            self.cursor_col = min(MAX_COLS - 1, self.cursor_col + 1)
        elif ch == ord('e') or ch == curses.KEY_ENTER or ch == 10 or ch == 13:
            # Start editing current cell
            raw = self.sheet.get_raw(self.cursor_row, self.cursor_col)
            self.input_buf = raw
            self.mode = 'EDIT'
        elif ch == ord('i'):
            # Start editing with empty buffer
            self.input_buf = ''
            self.mode = 'EDIT'
        elif ch == ord(':'):
            self.cmd_buf = ''
            self.mode = 'COMMAND'
        elif ch == ord('x') or ch == curses.KEY_DC or ch == 127 or ch == curses.KEY_BACKSPACE:
            # Delete cell
            self.sheet.set_cell(self.cursor_row, self.cursor_col, '')
            self.status_msg = f'Deleted {cell_name(self.cursor_row, self.cursor_col)}'
        elif ch == ord('y'):
            # Yank (copy) cell
            self.clipboard = copy.deepcopy(self.sheet.get_raw(self.cursor_row, self.cursor_col))
            self.status_msg = f'Yanked {cell_name(self.cursor_row, self.cursor_col)}'
        elif ch == ord('p') and self.clipboard is not None:
            # Paste
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.clipboard)
            self.status_msg = f'Pasted to {cell_name(self.cursor_row, self.cursor_col)}'
        elif ch == ord('q'):
            raise SystemExit
        elif ch == ord('?') or ch == ord('H'):
            self.status_msg = 'e:edit i:insert x:del y:yank p:paste :=cmd q:quit ?:help'

    def _handle_edit(self, ch):
        if ch == 27:  # Escape
            self.mode = 'NAV'
        elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
            # Confirm edit
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.status_msg = f'{cell_name(self.cursor_row, self.cursor_col)} = {self.input_buf}'
            self.mode = 'NAV'
            # Move down
            self.cursor_row = min(MAX_ROWS - 1, self.cursor_row + 1)
        elif ch == 9:  # Tab - confirm and move right
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.status_msg = f'{cell_name(self.cursor_row, self.cursor_col)} = {self.input_buf}'
            self.mode = 'NAV'
            self.cursor_col = min(MAX_COLS - 1, self.cursor_col + 1)
        elif ch == curses.KEY_BACKSPACE or ch == 127:
            self.input_buf = self.input_buf[:-1]
        elif ch == curses.KEY_UP:
            # Confirm and move up
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.mode = 'NAV'
            self.cursor_row = max(0, self.cursor_row - 1)
        elif ch == curses.KEY_DOWN:
            # Confirm and move down
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.mode = 'NAV'
            self.cursor_row = min(MAX_ROWS - 1, self.cursor_row + 1)
        elif ch == curses.KEY_LEFT:
            # Confirm and move left
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.mode = 'NAV'
            self.cursor_col = max(0, self.cursor_col - 1)
        elif ch == curses.KEY_RIGHT:
            # Confirm and move right
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.mode = 'NAV'
            self.cursor_col = min(MAX_COLS - 1, self.cursor_col + 1)
        elif 32 <= ch < 127:
            self.input_buf += chr(ch)

    def _handle_command(self, ch):
        if ch == 27:  # Escape
            self.mode = 'NAV'
        elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
            self._execute_command(self.cmd_buf)
            self.mode = 'NAV'
        elif ch == curses.KEY_BACKSPACE or ch == 127:
            self.cmd_buf = self.cmd_buf[:-1]
            if self.cmd_buf == '' and False:  # keep in command mode
                self.mode = 'NAV'
        elif 32 <= ch < 127:
            self.cmd_buf += chr(ch)

    def _execute_command(self, cmd):
        cmd = cmd.strip().lower()
        if cmd in ('q', 'quit', 'exit'):
            raise SystemExit
        elif cmd in ('h', 'help'):
            self.status_msg = 'Commands: :q(uit) :h(elp) :clear :goto A1 :width N'
        elif cmd.startswith('goto '):
            cell = parse_cell_name(cmd[5:].strip().upper())
            if cell:
                self.cursor_row, self.cursor_col = cell
                self.status_msg = f'Jumped to {cell_name(*cell)}'
            else:
                self.status_msg = f'Invalid cell: {cmd[5:]}'
        elif cmd == 'clear':
            self.sheet = Spreadsheet()
            self.status_msg = 'Sheet cleared'
        elif cmd.startswith('width '):
            global COL_WIDTH
            try:
                COL_WIDTH = int(cmd[6:])
                self.status_msg = f'Column width set to {COL_WIDTH}'
            except ValueError:
                self.status_msg = 'Invalid width'
        else:
            self.status_msg = f'Unknown command: {cmd}'

    def _draw(self):
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()

        # Adjust scroll to keep cursor visible
        visible_rows = max_y - 3  # header + status + input
        visible_cols = (max_x - ROW_HEADER_WIDTH) // COL_WIDTH

        if self.cursor_row < self.scroll_row:
            self.scroll_row = self.cursor_row
        elif self.cursor_row >= self.scroll_row + visible_rows:
            self.scroll_row = self.cursor_row - visible_rows + 1

        if self.cursor_col < self.scroll_col:
            self.scroll_col = self.cursor_col
        elif self.cursor_col >= self.scroll_col + visible_cols:
            self.scroll_col = self.cursor_col - visible_cols + 1

        # Draw column headers
        for vc in range(visible_cols + 1):
            col = self.scroll_col + vc
            if col >= MAX_COLS:
                break
            x = ROW_HEADER_WIDTH + vc * COL_WIDTH
            if x + COL_WIDTH <= max_x:
                header = col_to_letter(col).center(COL_WIDTH)
                try:
                    self.stdscr.addstr(0, x, header, curses.color_pair(1))
                except curses.error:
                    pass

        # Draw row headers and cells
        for vr in range(visible_rows):
            row = self.scroll_row + vr
            if row >= MAX_ROWS:
                break
            y = vr + 1
            # Row header
            rh = f"{row + 1:>3} "
            try:
                self.stdscr.addstr(y, 0, rh, curses.color_pair(1))
            except curses.error:
                pass

            # Cells
            for vc in range(visible_cols + 1):
                col = self.scroll_col + vc
                if col >= MAX_COLS:
                    break
                x = ROW_HEADER_WIDTH + vc * COL_WIDTH
                if x + COL_WIDTH > max_x:
                    break

                raw = self.sheet.get_raw(row, col)
                val = self.sheet.get_value(row, col)

                # Format cell content
                if raw == '':
                    display = ''
                elif raw.startswith('='):
                    # Show formula in current cell, computed value elsewhere
                    if row == self.cursor_row and col == self.cursor_col and self.mode == 'NAV':
                        display = raw
                    else:
                        display = self._format_value(val)
                else:
                    display = self._format_value(val)

                # Determine color
                color = 0  # default
                if row == self.cursor_row and col == self.cursor_col:
                    color = curses.color_pair(2)  # highlighted
                elif raw.startswith('='):
                    color = curses.color_pair(3)  # formula cells
                elif isinstance(val, str) and str(val).startswith('ERR:'):
                    color = curses.color_pair(4)  # error
                elif isinstance(val, (int, float)) and raw != '' and not raw.startswith('='):
                    color = curses.color_pair(5)  # number cells
                elif isinstance(val, str) and raw != '':
                    color = curses.color_pair(6)  # string cells

                # Pad and truncate
                display = display[:COL_WIDTH - 1]
                if row == self.cursor_row and col == self.cursor_col:
                    display = display.ljust(COL_WIDTH - 1)
                else:
                    if isinstance(val, (int, float)) and raw != '' and not isinstance(val, bool):
                        display = display.rjust(COL_WIDTH - 1)
                    else:
                        display = display.ljust(COL_WIDTH - 1)

                try:
                    self.stdscr.addstr(y, x, display, color)
                except curses.error:
                    pass

        # Draw horizontal line under header
        try:
            self.stdscr.addstr(0, 0, "    " + " " * min(max_x - 4, visible_cols * COL_WIDTH), curses.color_pair(1))
            for vc in range(visible_cols + 1):
                col = self.scroll_col + vc
                if col >= MAX_COLS:
                    break
                x = ROW_HEADER_WIDTH + vc * COL_WIDTH
                if x + COL_WIDTH <= max_x:
                    header = col_to_letter(col).center(COL_WIDTH)
                    self.stdscr.addstr(0, x, header, curses.color_pair(1))
        except curses.error:
            pass

        # Status bar
        status_y = max_y - 2
        cell = cell_name(self.cursor_row, self.cursor_col)
        raw = self.sheet.get_raw(self.cursor_row, self.cursor_col)
        val = self.sheet.get_value(self.cursor_row, self.cursor_col)

        if self.mode == 'EDIT':
            status = f"  EDIT {cell}: {self.input_buf}_"
        elif self.mode == 'COMMAND':
            status = f"  :{self.cmd_buf}_"
        else:
            mode_label = "NAV"
            if raw.startswith('='):
                status = f"  {mode_label} | {cell}: {raw}  →  {val}"
            elif raw:
                status = f"  {mode_label} | {cell}: {raw}"
            else:
                status = f"  {mode_label} | {cell}: (empty)"

            if self.status_msg:
                status = f"  {self.status_msg}"

        try:
            self.stdscr.addstr(status_y, 0, status.ljust(max_x), curses.color_pair(1))
        except curses.error:
            pass

        # Help bar
        help_y = max_y - 1
        help_text = " e:edit i:insert x:del y:yank p:paste :=cmd ↑↓←→/hjkl:move q:quit"
        try:
            self.stdscr.addstr(help_y, 0, help_text.ljust(max_x), curses.color_pair(1))
        except curses.error:
            pass

        self.stdscr.refresh()

    def _format_value(self, val) -> str:
        if val == 0 and not isinstance(val, bool):
            return ''
        if isinstance(val, float):
            if val == int(val) and abs(val) < 1e10:
                return str(int(val))
            return f"{val:.2f}"
        if isinstance(val, str) and val.startswith('ERR:'):
            return val
        return str(val)


# ── Main ────────────────────────────────────────────────────────────────────

def main(stdscr):
    ui = SpreadsheetUI(stdscr)
    ui.run()


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass