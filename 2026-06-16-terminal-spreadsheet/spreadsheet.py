#!/usr/bin/env python3
"""
Terminal Spreadsheet — A fully interactive, curses-based mini spreadsheet.

Features:
  - Navigate cells with arrow keys or hjkl
  - Type values or formulas (formulas start with =)
  - Cell references like A1, B3, Z26
  - Arithmetic: +, -, *, /, ^, %, comparison operators
  - Functions: SUM, AVG, MIN, MAX, COUNT, MEDIAN, STDEV, ABS, INT, ROUND, SQRT, IF, CONCAT over ranges
  - Undo/Redo (u / Ctrl+R)
  - CSV load/save (:load filename.csv, :save filename.csv)
  - Search cells with / pattern
  - Delete cells with x or Backspace/Delete
  - Press : to enter command mode (:q to quit, :goto A1, :clear, :width N, :help)
  - Press e to edit the current cell, i to insert with empty buffer
  - Status bar shows cell coordinate, raw value, and computed result
  - Yank/Paste with y/p

No external dependencies — uses only the Python standard library.
"""

import argparse
import csv
import curses
import math
import os
import re
import sys
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

# ── Version ──────────────────────────────────────────────────────────────────

__version__ = "1.1.0"

# ── Constants ────────────────────────────────────────────────────────────────

MAX_ROWS = 100
MAX_COLS = 26  # A–Z
DEFAULT_COL_WIDTH = 10
ROW_HEADER_WIDTH = 4
MAX_UNDO_HISTORY = 50


# ── Helpers ──────────────────────────────────────────────────────────────────

def col_to_letter(col: int) -> str:
    """Convert a zero-based column index to a letter. 0→A, 1→B, …, 25→Z."""
    if not 0 <= col < MAX_COLS:
        raise ValueError(f"Column index {col} out of range [0, {MAX_COLS})")
    return chr(ord('A') + col)


def letter_to_col(letter: str) -> int:
    """Convert a column letter to a zero-based index. A→0, B→1, …, Z→25."""
    result = ord(letter.upper()) - ord('A')
    if not 0 <= result < MAX_COLS:
        raise ValueError(f"Column letter '{letter}' out of range")
    return result


def cell_name(row: int, col: int) -> str:
    """Convert zero-based (row, col) to spreadsheet notation. (0,0)→'A1'."""
    return f"{col_to_letter(col)}{row + 1}"


def parse_cell_name(name: str) -> Optional[Tuple[int, int]]:
    """Parse a cell name like 'A1' to (row, col). Returns None on failure."""
    m = re.match(r'^([A-Za-z])(\d+)$', name)
    if not m:
        return None
    col = letter_to_col(m.group(1))
    row = int(m.group(2)) - 1
    if 0 <= row < MAX_ROWS:
        return (row, col)
    return None


# ── Tokenizer / Parser ──────────────────────────────────────────────────────

# Supported function names
BUILTIN_FUNCTIONS = frozenset({
    'SUM', 'AVG', 'MIN', 'MAX', 'COUNT',
    'MEDIAN', 'STDEV',
    'ABS', 'INT', 'ROUND', 'SQRT',
    'IF', 'CONCAT',
})


def tokenize(expr: str) -> List[Tuple[str, Any]]:
    """Tokenize a formula expression into a list of (type, value) tokens."""
    tokens: List[Tuple[str, Any]] = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        # Skip whitespace
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
        # String literal (double-quoted)
        elif ch == '"':
            j = i + 1
            while j < len(expr) and expr[j] != '"':
                j += 1
            tokens.append(('STR', expr[i + 1:j]))
            i = j + 1 if j < len(expr) else j
        # Identifiers: cell refs, function names, or unknown names
        elif ch.isalpha():
            j = i
            while j < len(expr) and (expr[j].isalpha() or expr[j].isdigit()):
                j += 1
            word = expr[i:j]
            if word.upper() in BUILTIN_FUNCTIONS:
                tokens.append(('FUNC', word.upper()))
            elif re.match(r'^[A-Za-z]\d+$', word):
                tokens.append(('CELL', word.upper()))
            else:
                tokens.append(('NAME', word.upper()))
            i = j
        # Two-character operators
        elif ch == '<' and i + 1 < len(expr) and expr[i + 1] == '=':
            tokens.append(('OP', '<='))
            i += 2
        elif ch == '>' and i + 1 < len(expr) and expr[i + 1] == '=':
            tokens.append(('OP', '>='))
            i += 2
        elif ch == '=' and i + 1 < len(expr) and expr[i + 1] == '=':
            tokens.append(('OP', '=='))
            i += 2
        elif ch == '!' and i + 1 < len(expr) and expr[i + 1] == '=':
            tokens.append(('OP', '!='))
            i += 2
        elif ch == '&' and i + 1 < len(expr) and expr[i + 1] == '&':
            tokens.append(('OP', '&&'))
            i += 2
        # Single-character operators and delimiters
        elif ch in '+-*/^%':
            tokens.append(('OP', ch))
            i += 1
        elif ch == '=':
            tokens.append(('OP', '=='))
            i += 1
        elif ch == '<':
            tokens.append(('OP', '<'))
            i += 1
        elif ch == '>':
            tokens.append(('OP', '>'))
            i += 1
        elif ch == '!':
            tokens.append(('OP', '!'))
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
        else:
            i += 1  # skip unknown chars
    return tokens


def parse_range(tokens: List[Tuple[str, Any]], pos: int) -> Tuple[Optional[Tuple[int, int, int, int]], int]:
    """Parse a cell reference or range (e.g. A1 or A1:B3).

    Returns ((r1, c1, r2, c2), new_pos) or (None, pos) on failure.
    """
    if pos >= len(tokens):
        return None, pos
    if tokens[pos][0] != 'CELL':
        return None, pos
    start = parse_cell_name(tokens[pos][1])
    if start is None:
        return None, pos
    if (pos + 2 < len(tokens)
            and tokens[pos + 1][0] == 'COLON'
            and tokens[pos + 2][0] == 'CELL'):
        end = parse_cell_name(tokens[pos + 2][1])
        if end is None:
            return None, pos
        return (start[0], start[1], end[0], end[1]), pos + 3
    # Single cell as a 1×1 range
    return (start[0], start[1], start[0], start[1]), pos + 1


# ── Spreadsheet Engine ───────────────────────────────────────────────────────

class Spreadsheet:
    """Core spreadsheet data model with formula evaluation, caching, and undo."""

    def __init__(self):
        self.cells: Dict[Tuple[int, int], str] = {}
        self.cache: Dict[Tuple[int, int], Any] = {}
        self.error_cells: Set[Tuple[int, int]] = set()
        # Undo/Redo stacks store snapshots of self.cells
        self._undo_stack: List[Dict[Tuple[int, int], str]] = []
        self._redo_stack: List[Dict[Tuple[int, int], str]] = []

    # ── Public API ──────────────────────────────────────────────────────

    def set_cell(self, row: int, col: int, value: str, record_undo: bool = True):
        """Set a cell's raw content. Use record_undo=False for programmatic loads."""
        if record_undo:
            self._push_undo()
        key = (row, col)
        if value == '' or value is None:
            self.cells.pop(key, None)
            self.cache.pop(key, None)
            self.error_cells.discard(key)
        else:
            self.cells[key] = str(value)
            self._invalidate(key)

    def get_raw(self, row: int, col: int) -> str:
        """Return the raw (unevaluated) content of a cell."""
        return self.cells.get((row, col), '')

    def get_value(self, row: int, col: int) -> Any:
        """Return the evaluated value of a cell, using cache when possible."""
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

    def undo(self) -> bool:
        """Undo the last change. Returns True if successful."""
        if not self._undo_stack:
            return False
        self._redo_stack.append(dict(self.cells))
        self.cells = self._undo_stack.pop()
        self.cache.clear()
        self.error_cells.clear()
        return True

    def redo(self) -> bool:
        """Redo the last undone change. Returns True if successful."""
        if not self._redo_stack:
            return False
        self._undo_stack.append(dict(self.cells))
        self.cells = self._redo_stack.pop()
        self.cache.clear()
        self.error_cells.clear()
        return True

    def load_csv(self, filepath: str) -> str:
        """Load cells from a CSV file. Returns a status message."""
        try:
            with open(filepath, newline='') as f:
                reader = csv.reader(f)
                self._push_undo()
                row_idx = 0
                for row_vals in reader:
                    if row_idx >= MAX_ROWS:
                        break
                    for col_idx, val in enumerate(row_vals):
                        if col_idx >= MAX_COLS:
                            break
                        val = val.strip()
                        if val:
                            self.set_cell(row_idx, col_idx, val, record_undo=False)
                    row_idx += 1
                self.cache.clear()
                self.error_cells.clear()
            return f"Loaded {filepath}"
        except FileNotFoundError:
            return f"File not found: {filepath}"
        except Exception as e:
            return f"Error loading {filepath}: {e}"

    def save_csv(self, filepath: str) -> str:
        """Save cells to a CSV file. Returns a status message."""
        if not self.cells:
            return "Nothing to save"
        max_row = max(r for r, c in self.cells) + 1
        max_col = max(c for r, c in self.cells) + 1
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                for r in range(max_row):
                    row_data = []
                    for c in range(max_col):
                        row_data.append(self.get_raw(r, c))
                    writer.writerow(row_data)
            return f"Saved to {filepath}"
        except Exception as e:
            return f"Error saving: {e}"

    def search(self, pattern: str) -> Optional[Tuple[int, int]]:
        """Search for a cell whose raw content contains the pattern (case-insensitive).
        Returns the first matching cell after the current position, or None."""
        regex = re.compile(re.escape(pattern), re.IGNORECASE)
        for r in range(MAX_ROWS):
            for c in range(MAX_COLS):
                raw = self.get_raw(r, c)
                if raw and regex.search(raw):
                    return (r, c)
        return None

    def search_after(self, pattern: str, after_row: int, after_col: int) -> Optional[Tuple[int, int]]:
        """Search starting after (after_row, after_col), wrapping around."""
        regex = re.compile(re.escape(pattern), re.IGNORECASE)
        # Search from (after_row, after_col+1) forward, then wrap
        started = False
        for r in range(MAX_ROWS):
            for c in range(MAX_COLS):
                if not started:
                    if r == after_row and c > after_col:
                        started = True
                    elif r > after_row:
                        started = True
                    continue
                raw = self.get_raw(r, c)
                if raw and regex.search(raw):
                    return (r, c)
        # Wrap around from the beginning
        for r in range(MAX_ROWS):
            for c in range(MAX_COLS):
                if r == after_row and c == after_col:
                    return None  # back to start, no match found
                raw = self.get_raw(r, c)
                if raw and regex.search(raw):
                    return (r, c)
        return None

    # ── Internal ────────────────────────────────────────────────────────

    def _push_undo(self):
        """Save current state to undo stack, clearing redo."""
        self._undo_stack.append(dict(self.cells))
        if len(self._undo_stack) > MAX_UNDO_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _invalidate(self, key: Tuple[int, int]):
        """Invalidate cache for a cell and all dependents."""
        self.cache.clear()
        self.error_cells.clear()

    def _coerce(self, s: str) -> Any:
        """Try to coerce a string to a number (int or float)."""
        try:
            if '.' in s:
                return float(s)
            return int(s)
        except ValueError:
            return s

    def _evaluate_formula(self, expr: str, source_cell: Tuple[int, int],
                         _eval_stack: Optional[set] = None) -> Any:
        """Evaluate a formula string with transitive circular-reference detection."""
        if _eval_stack is None:
            _eval_stack = set()
        if source_cell in _eval_stack:
            self.error_cells.add(source_cell)
            return "ERR: Circular reference"
        _eval_stack = _eval_stack | {source_cell}
        try:
            tokens = tokenize(expr)
            pos = [0]
            result = self._parse_expression(tokens, pos, source_cell, _eval_stack)
            return result
        except Exception as e:
            self.error_cells.add(source_cell)
            return f"ERR: {e}"

    def _parse_expression(self, tokens, pos, source, eval_stack):
        """Parse addition / subtraction / concatenation level."""
        left = self._parse_comparison(tokens, pos, source, eval_stack)
        while pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] in ('+', '-'):
            op = tokens[pos[0]][1]
            pos[0] += 1
            right = self._parse_comparison(tokens, pos, source, eval_stack)
            if op == '+':
                # Support string + number concatenation
                if isinstance(left, str) or isinstance(right, str):
                    left = str(left) + str(right)
                else:
                    left = left + right
            else:
                left = left - right
        return left

    def _parse_comparison(self, tokens, pos, source, eval_stack):
        """Parse comparison operators: ==, !=, <, <=, >, >="""
        left = self._parse_term(tokens, pos, source, eval_stack)
        if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] in ('==', '!=', '<', '<=', '>', '>='):
            op = tokens[pos[0]][1]
            pos[0] += 1
            right = self._parse_term(tokens, pos, source, eval_stack)
            if op == '==':
                left = 1 if left == right else 0
            elif op == '!=':
                left = 1 if left != right else 0
            elif op == '<':
                left = 1 if left < right else 0
            elif op == '<=':
                left = 1 if left <= right else 0
            elif op == '>':
                left = 1 if left > right else 0
            elif op == '>=':
                left = 1 if left >= right else 0
        return left

    def _parse_term(self, tokens, pos, source, eval_stack):
        """Parse multiplication / division / modulo."""
        left = self._parse_power(tokens, pos, source, eval_stack)
        while pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] in ('*', '/', '%'):
            op = tokens[pos[0]][1]
            pos[0] += 1
            right = self._parse_power(tokens, pos, source, eval_stack)
            if op == '*':
                left = left * right
            elif op == '/':
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                left = left / right
            else:
                if right == 0:
                    raise ZeroDivisionError("Modulo by zero")
                left = left % right
        return left

    def _parse_power(self, tokens, pos, source, eval_stack):
        """Parse exponentiation (right-associative)."""
        base = self._parse_unary(tokens, pos, source, eval_stack)
        if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '^':
            pos[0] += 1
            exp = self._parse_power(tokens, pos, source, eval_stack)  # right-associative
            return base ** exp
        return base

    def _parse_unary(self, tokens, pos, source, eval_stack):
        """Parse unary minus/plus/not."""
        if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '-':
            pos[0] += 1
            return -self._parse_unary(tokens, pos, source, eval_stack)
        if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '+':
            pos[0] += 1
            return self._parse_unary(tokens, pos, source, eval_stack)
        if pos[0] < len(tokens) and tokens[pos[0]][0] == 'OP' and tokens[pos[0]][1] == '!':
            pos[0] += 1
            val = self._parse_unary(tokens, pos, source, eval_stack)
            return 0 if val else 1
        return self._parse_primary(tokens, pos, source, eval_stack)

    def _parse_primary(self, tokens, pos, source, eval_stack):
        """Parse primary expressions: numbers, strings, cell refs, function calls, parens."""
        if pos[0] >= len(tokens):
            return 0

        tok = tokens[pos[0]]

        # Number literal
        if tok[0] == 'NUM':
            pos[0] += 1
            return tok[1]

        # String literal
        if tok[0] == 'STR':
            pos[0] += 1
            return tok[1]

        # Parenthesized expression
        if tok[0] == 'LPAREN':
            pos[0] += 1
            val = self._parse_expression(tokens, pos, source, eval_stack)
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
            args: List[Any] = []
            # Parse comma-separated arguments.
            # Each argument is either:
            #   (a) an explicit range like CELL:CELL (for aggregate functions), OR
            #   (b) a general expression (which may include cell refs, operators, etc.)
            while pos[0] < len(tokens) and tokens[pos[0]][0] != 'RPAREN':
                # Check for an explicit range: CELL followed by COLON followed by CELL
                if (tokens[pos[0]][0] == 'CELL'
                        and pos[0] + 2 < len(tokens)
                        and tokens[pos[0] + 1][0] == 'COLON'
                        and tokens[pos[0] + 2][0] == 'CELL'):
                    rng, new_pos = parse_range(tokens, pos[0])
                    if rng is not None:
                        pos[0] = new_pos
                        args.extend(self._expand_range(rng, source, eval_stack))
                else:
                    args.append(self._parse_expression(tokens, pos, source, eval_stack))
                # Comma between arguments
                if pos[0] < len(tokens) and tokens[pos[0]][0] == 'COMMA':
                    pos[0] += 1

            # Expect RPAREN
            if pos[0] < len(tokens) and tokens[pos[0]][0] == 'RPAREN':
                pos[0] += 1

            return self._apply_function(func_name, args, source)

        # Cell reference
        if tok[0] == 'CELL':
            cell = parse_cell_name(tok[1])
            if cell is None:
                raise ValueError(f"Invalid cell reference: {tok[1]}")
            # Transitive circular reference detection
            if cell in eval_stack:
                raise ValueError("Circular reference")
            pos[0] += 1
            val = self.get_value_with_stack(cell[0], cell[1], eval_stack)
            if isinstance(val, str) and str(val).startswith("ERR:"):
                raise ValueError(val)
            return val

        # Unknown token — skip
        pos[0] += 1
        return 0

    def get_value_with_stack(self, row: int, col: int, parent_stack: set) -> Any:
        """Get value with circular reference tracking via eval stack."""
        key = (row, col)
        if key in self.cache:
            return self.cache[key]
        if key not in self.cells:
            self.cache[key] = 0
            return 0
        raw = self.cells[key]
        if raw.startswith('='):
            val = self._evaluate_formula(raw[1:], key, parent_stack)
        else:
            val = self._coerce(raw)
        self.cache[key] = val
        return val

    def _expand_range(self, rng: Tuple[int, int, int, int],
                     source: Tuple[int, int], eval_stack: set) -> List[Any]:
        """Expand a range (r1, c1, r2, c2) into a list of cell values."""
        r1, c1, r2, c2 = rng
        values: List[Any] = []
        for r in range(min(r1, r2), max(r1, r2) + 1):
            for c in range(min(c1, c2), max(c1, c2) + 1):
                if (r, c) in eval_stack:
                    raise ValueError("Circular reference")
                val = self.get_value_with_stack(r, c, eval_stack)
                values.append(val)
        return values

    def _apply_function(self, name: str, args: List[Any], source: Tuple[int, int]) -> Any:
        """Apply a spreadsheet function to a list of arguments."""
        # Separate numeric args from string args
        nums = [a for a in args if isinstance(a, (int, float))]
        strs = [a for a in args if isinstance(a, str)]

        if name == 'SUM':
            return sum(nums) if nums else 0
        elif name == 'AVG':
            return sum(nums) / len(nums) if nums else 0
        elif name == 'MEDIAN':
            if not nums:
                return 0
            s = sorted(nums)
            mid = len(s) // 2
            if len(s) % 2 == 0:
                return (s[mid - 1] + s[mid]) / 2
            return s[mid]
        elif name == 'STDEV':
            if len(nums) < 2:
                return 0
            mean = sum(nums) / len(nums)
            variance = sum((x - mean) ** 2 for x in nums) / (len(nums) - 1)
            return math.sqrt(variance)
        elif name == 'MIN':
            return min(nums) if nums else 0
        elif name == 'MAX':
            return max(nums) if nums else 0
        elif name == 'COUNT':
            return len([a for a in args if a != 0 or isinstance(a, (int, float))])
        elif name == 'ABS':
            return abs(nums[0]) if nums else 0
        elif name == 'INT':
            return int(nums[0]) if nums else 0
        elif name == 'ROUND':
            if len(nums) >= 2:
                return round(nums[0], int(nums[1]))
            return round(nums[0]) if nums else 0
        elif name == 'SQRT':
            if nums and nums[0] >= 0:
                return math.sqrt(nums[0])
            return 0
        elif name == 'IF':
            # IF(condition, true_val, false_val)
            if len(args) >= 3:
                cond = args[0]
                if isinstance(cond, str):
                    cond = cond.lower() in ('true', '1', 'yes')
                return args[1] if cond else args[2]
            return 0
        elif name == 'CONCAT':
            # CONCAT(val1, val2, ...) — concatenate all args as strings
            return ''.join(str(a) for a in args)
        else:
            raise ValueError(f"Unknown function: {name}")


# ── Curses UI ────────────────────────────────────────────────────────────────

class SpreadsheetUI:
    """Full-screen curses interface for the terminal spreadsheet."""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.sheet = Spreadsheet()
        self.cursor_row = 0
        self.cursor_col = 0
        self.scroll_row = 0
        self.scroll_col = 0
        self.col_width = DEFAULT_COL_WIDTH  # instance variable, not global
        self.mode = 'NAV'  # NAV, EDIT, COMMAND, SEARCH
        self.input_buf = ''
        self.cmd_buf = ''
        self.status_msg = ''
        self.clipboard: Optional[str] = None
        self.modified = False
        self.search_pattern = ''
        self.search_dir_forward = True

        # Pre-populate with sample data
        self._load_sample_data()

    def _load_sample_data(self):
        """Load sample data so the spreadsheet isn't empty on first run."""
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
            'A9': 'Median', 'B9': '=MEDIAN(B2:B5)', 'C9': '=MEDIAN(C2:C5)', 'D9': '=MEDIAN(D2:D5)',
        }
        for name, val in data.items():
            cell = parse_cell_name(name)
            if cell:
                s.set_cell(cell[0], cell[1], val, record_undo=False)

    def run(self):
        """Main event loop."""
        curses.curs_set(1)
        self.stdscr.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)     # header
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)     # selected cell
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)     # formulas
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)       # errors
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # numbers
        curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)    # strings
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)       # command/search mode

        while True:
            self._draw()
            ch = self.stdscr.getch()
            if self.mode == 'NAV':
                self._handle_nav(ch)
            elif self.mode == 'EDIT':
                self._handle_edit(ch)
            elif self.mode == 'COMMAND':
                self._handle_command(ch)
            elif self.mode == 'SEARCH':
                self._handle_search(ch)

    def _handle_nav(self, ch):
        """Handle key presses in navigation mode."""
        if ch == curses.KEY_UP or ch == ord('k'):
            self.cursor_row = max(0, self.cursor_row - 1)
        elif ch == curses.KEY_DOWN or ch == ord('j'):
            self.cursor_row = min(MAX_ROWS - 1, self.cursor_row + 1)
        elif ch == curses.KEY_LEFT or ch == ord('h'):
            self.cursor_col = max(0, self.cursor_col - 1)
        elif ch == curses.KEY_RIGHT or ch == ord('l'):
            self.cursor_col = min(MAX_COLS - 1, self.cursor_col + 1)
        elif ch == ord('e') or ch == curses.KEY_ENTER or ch == 10 or ch == 13:
            # Start editing current cell (with existing content)
            raw = self.sheet.get_raw(self.cursor_row, self.cursor_col)
            self.input_buf = raw
            self.mode = 'EDIT'
        elif ch == ord('i'):
            # Start editing with empty buffer (insert mode)
            self.input_buf = ''
            self.mode = 'EDIT'
        elif ch == ord(':'):
            self.cmd_buf = ''
            self.mode = 'COMMAND'
        elif ch == ord('/'):
            # Start search
            self.search_pattern = ''
            self.mode = 'SEARCH'
        elif ch == ord('n') and self.search_pattern:
            # Find next match
            result = self.sheet.search_after(
                self.search_pattern, self.cursor_row, self.cursor_col)
            if result:
                self.cursor_row, self.cursor_col = result
                self.status_msg = f'Found at {cell_name(*result)}'
            else:
                self.status_msg = 'No more matches'
        elif ch == ord('x') or ch == curses.KEY_DC or ch == 127 or ch == curses.KEY_BACKSPACE:
            # Delete cell
            self.sheet.set_cell(self.cursor_row, self.cursor_col, '')
            self.status_msg = f'Deleted {cell_name(self.cursor_row, self.cursor_col)}'
        elif ch == ord('y'):
            # Yank (copy) cell
            self.clipboard = self.sheet.get_raw(self.cursor_row, self.cursor_col)
            self.status_msg = f'Yanked {cell_name(self.cursor_row, self.cursor_col)}'
        elif ch == ord('p') and self.clipboard is not None:
            # Paste
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.clipboard)
            self.status_msg = f'Pasted to {cell_name(self.cursor_row, self.cursor_col)}'
        elif ch == ord('u'):
            # Undo
            if self.sheet.undo():
                self.status_msg = 'Undo'
            else:
                self.status_msg = 'Nothing to undo'
        elif ch == ord('q'):
            raise SystemExit
        elif ch == ord('?') or ch == ord('H'):
            self.status_msg = 'e:edit i:insert x:del y:yank p:paste u:undo /:search n:next q:quit ?:help'

    def _handle_edit(self, ch):
        """Handle key presses in edit mode."""
        if ch == 27:  # Escape
            self.mode = 'NAV'
        elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
            # Confirm edit and move down
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.status_msg = f'{cell_name(self.cursor_row, self.cursor_col)} = {self.input_buf}'
            self.mode = 'NAV'
            self.cursor_row = min(MAX_ROWS - 1, self.cursor_row + 1)
        elif ch == 9:  # Tab — confirm and move right
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.status_msg = f'{cell_name(self.cursor_row, self.cursor_col)} = {self.input_buf}'
            self.mode = 'NAV'
            self.cursor_col = min(MAX_COLS - 1, self.cursor_col + 1)
        elif ch == curses.KEY_BACKSPACE or ch == 127:
            self.input_buf = self.input_buf[:-1]
        elif ch == curses.KEY_UP:
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.mode = 'NAV'
            self.cursor_row = max(0, self.cursor_row - 1)
        elif ch == curses.KEY_DOWN:
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.mode = 'NAV'
            self.cursor_row = min(MAX_ROWS - 1, self.cursor_row + 1)
        elif ch == curses.KEY_LEFT:
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.mode = 'NAV'
            self.cursor_col = max(0, self.cursor_col - 1)
        elif ch == curses.KEY_RIGHT:
            self.sheet.set_cell(self.cursor_row, self.cursor_col, self.input_buf)
            self.mode = 'NAV'
            self.cursor_col = min(MAX_COLS - 1, self.cursor_col + 1)
        elif 32 <= ch < 127:
            self.input_buf += chr(ch)

    def _handle_command(self, ch):
        """Handle key presses in command mode (entered with :)."""
        if ch == 27:  # Escape
            self.mode = 'NAV'
        elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
            self._execute_command(self.cmd_buf)
            self.mode = 'NAV'
        elif ch == curses.KEY_BACKSPACE or ch == 127:
            self.cmd_buf = self.cmd_buf[:-1]
            if self.cmd_buf == '':
                self.mode = 'NAV'
        elif 32 <= ch < 127:
            self.cmd_buf += chr(ch)

    def _handle_search(self, ch):
        """Handle key presses in search mode (entered with /)."""
        if ch == 27:  # Escape
            self.mode = 'NAV'
        elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
            # Execute search
            if self.search_pattern:
                result = self.sheet.search_after(
                    self.search_pattern, self.cursor_row, self.cursor_col - 1)
                if result:
                    self.cursor_row, self.cursor_col = result
                    self.status_msg = f'Found at {cell_name(*result)}'
                else:
                    self.status_msg = 'Not found'
            self.mode = 'NAV'
        elif ch == curses.KEY_BACKSPACE or ch == 127:
            self.search_pattern = self.search_pattern[:-1]
            if self.search_pattern == '':
                self.mode = 'NAV'
        elif 32 <= ch < 127:
            self.search_pattern += chr(ch)

    def _execute_command(self, cmd: str):
        """Parse and execute a command entered in command mode."""
        cmd = cmd.strip()
        cmd_lower = cmd.lower()

        if cmd_lower in ('q', 'quit', 'exit'):
            raise SystemExit
        elif cmd_lower in ('h', 'help'):
            self.status_msg = 'Commands: :q(uit) :h(elp) :clear :goto A1 :width N :save f :load f'
        elif cmd_lower.startswith('goto '):
            cell = parse_cell_name(cmd[5:].strip().upper())
            if cell:
                self.cursor_row, self.cursor_col = cell
                self.status_msg = f'Jumped to {cell_name(*cell)}'
            else:
                self.status_msg = f'Invalid cell: {cmd[5:]}'
        elif cmd_lower == 'clear':
            self.sheet._push_undo()
            self.sheet.cells.clear()
            self.sheet.cache.clear()
            self.sheet.error_cells.clear()
            self.status_msg = 'Sheet cleared'
        elif cmd_lower.startswith('width '):
            try:
                w = int(cmd[6:])
                if 4 <= w <= 30:
                    self.col_width = w
                    self.status_msg = f'Column width set to {w}'
                else:
                    self.status_msg = 'Width must be 4-30'
            except ValueError:
                self.status_msg = 'Invalid width'
        elif cmd_lower.startswith('save '):
            filepath = cmd[5:].strip()
            self.status_msg = self.sheet.save_csv(filepath)
        elif cmd_lower.startswith('load '):
            filepath = cmd[5:].strip()
            self.status_msg = self.sheet.load_csv(filepath)
        elif cmd_lower == 'version':
            self.status_msg = f'terminal-spreadsheet v{__version__}'
        else:
            self.status_msg = f'Unknown command: {cmd}'

    def _draw(self):
        """Render the full spreadsheet display."""
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()

        # Compute viewport dimensions
        visible_rows = max_y - 3  # header + status + help
        visible_cols = (max_x - ROW_HEADER_WIDTH) // self.col_width

        # Adjust scroll to keep cursor visible
        if self.cursor_row < self.scroll_row:
            self.scroll_row = self.cursor_row
        elif self.cursor_row >= self.scroll_row + visible_rows:
            self.scroll_row = self.cursor_row - visible_rows + 1

        if self.cursor_col < self.scroll_col:
            self.scroll_col = self.cursor_col
        elif self.cursor_col >= self.scroll_col + visible_cols:
            self.scroll_col = self.cursor_col - visible_cols + 1

        # ── Draw column headers ──
        try:
            self.stdscr.addstr(0, 0, "    " + " " * min(max_x - 4, visible_cols * self.col_width),
                               curses.color_pair(1))
        except curses.error:
            pass
        for vc in range(visible_cols + 1):
            col = self.scroll_col + vc
            if col >= MAX_COLS:
                break
            x = ROW_HEADER_WIDTH + vc * self.col_width
            if x + self.col_width <= max_x:
                header = col_to_letter(col).center(self.col_width)
                try:
                    self.stdscr.addstr(0, x, header, curses.color_pair(1))
                except curses.error:
                    pass

        # ── Draw rows and cells ──
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

            for vc in range(visible_cols + 1):
                col = self.scroll_col + vc
                if col >= MAX_COLS:
                    break
                x = ROW_HEADER_WIDTH + vc * self.col_width
                if x + self.col_width > max_x:
                    break

                raw = self.sheet.get_raw(row, col)
                val = self.sheet.get_value(row, col)

                # Format cell content
                if raw == '':
                    display = ''
                elif raw.startswith('='):
                    if row == self.cursor_row and col == self.cursor_col and self.mode == 'NAV':
                        display = raw
                    else:
                        display = self._format_value(val)
                else:
                    display = self._format_value(val)

                # Determine color
                color = 0  # default
                if row == self.cursor_row and col == self.cursor_col:
                    color = curses.color_pair(2)  # highlighted cell
                elif raw.startswith('='):
                    color = curses.color_pair(3)  # formula cells
                elif isinstance(val, str) and str(val).startswith('ERR:'):
                    color = curses.color_pair(4)  # error
                elif isinstance(val, (int, float)) and raw != '':
                    color = curses.color_pair(5)  # number cells
                elif isinstance(val, str) and raw != '':
                    color = curses.color_pair(6)  # string cells

                # Pad / justify
                display = display[:self.col_width - 1]
                if row == self.cursor_row and col == self.cursor_col:
                    display = display.ljust(self.col_width - 1)
                elif isinstance(val, (int, float)) and raw != '' and not isinstance(val, bool):
                    display = display.rjust(self.col_width - 1)
                else:
                    display = display.ljust(self.col_width - 1)

                try:
                    self.stdscr.addstr(y, x, display, color)
                except curses.error:
                    pass

        # ── Status bar ──
        status_y = max_y - 2
        cell = cell_name(self.cursor_row, self.cursor_col)
        raw = self.sheet.get_raw(self.cursor_row, self.cursor_col)
        val = self.sheet.get_value(self.cursor_row, self.cursor_col)

        if self.mode == 'EDIT':
            status = f"  EDIT {cell}: {self.input_buf}_"
        elif self.mode == 'COMMAND':
            status = f"  :{self.cmd_buf}_"
        elif self.mode == 'SEARCH':
            status = f"  /{self.search_pattern}_"
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
            self.stdscr.addstr(status_y, 0, status.ljust(max_x)[:max_x], curses.color_pair(1))
        except curses.error:
            pass

        # ── Help bar ──
        help_y = max_y - 1
        help_text = " e:edit i:insert x:del y:yank p:paste u:undo /:search n:next :=cmd q:quit ?:help"
        try:
            self.stdscr.addstr(help_y, 0, help_text.ljust(max_x)[:max_x], curses.color_pair(1))
        except curses.error:
            pass

        self.stdscr.refresh()

    def _format_value(self, val) -> str:
        """Format a cell value for display in the grid."""
        if val == 0 and not isinstance(val, bool):
            return ''
        if isinstance(val, float):
            if val == int(val) and abs(val) < 1e10:
                return str(int(val))
            return f"{val:.4f}"
        if isinstance(val, str) and val.startswith('ERR:'):
            return val
        return str(val)


# ── CLI & Main ──────────────────────────────────────────────────────────────

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='spreadsheet',
        description='Terminal Spreadsheet — A fully interactive, curses-based mini spreadsheet.')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--load', metavar='FILE', help='Load a CSV file on startup')
    return parser.parse_args()


def main(stdscr):
    ui = SpreadsheetUI(stdscr)
    ui.run()


if __name__ == '__main__':
    args = parse_args()
    try:
        def main_with_args(stdscr):
            ui = SpreadsheetUI(stdscr)
            if args.load:
                msg = ui.sheet.load_csv(args.load)
                ui.status_msg = msg
            ui.run()
        curses.wrapper(main_with_args)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass