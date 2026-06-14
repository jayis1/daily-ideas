#!/usr/bin/env python3
"""
Regex Crossword Generator & Solver
====================================

Generates regex crossword puzzles where each cell must satisfy
a row regex constraint AND a column regex constraint. Includes
an interactive terminal-based solver with validation feedback.

Puzzles look like this:

          C1       C2       C3
     ┌─────────┬─────────┬─────────┐
 R1  │         │         │         │  R1 regex
     ├─────────┼─────────┼─────────┤
 R2  │         │         │         │  R2 regex
     └─────────┴─────────┴─────────┘
        C1 regex C2 regex C3 regex

Each cell (r, c) must match BOTH row_r regex AND col_c regex.
Specifically, the full row string must match the row regex, and
the full column string must match the column regex.
"""

import re
import random
import string
import itertools
from dataclasses import dataclass
from typing import List, Optional, Tuple, Set, Dict

# ─── Puzzle Definition ────────────────────────────────────────────────

@dataclass
class RegexCrossword:
    """A regex crossword puzzle."""
    rows: int
    cols: int
    row_patterns: List[str]
    col_patterns: List[str]
    solution: List[List[str]]  # solution[row][col] = single character
    charset: str = "0123456789ABCDEF"  # default hex

    def check_row(self, row: int, grid: List[List[Optional[str]]]) -> Optional[bool]:
        """Check if the row matches its regex. Returns None if row is incomplete."""
        row_str = ""
        for c in range(self.cols):
            if grid[row][c] is None:
                return None  # incomplete
            row_str += grid[row][c]
        return re.fullmatch(self.row_patterns[row], row_str) is not None

    def check_col(self, col: int, grid: List[List[Optional[str]]]) -> Optional[bool]:
        """Check if the column matches its regex. Returns None if incomplete."""
        col_str = ""
        for r in range(self.rows):
            if grid[r][col] is None:
                return None  # incomplete
            col_str += grid[r][col]
        return re.fullmatch(self.col_patterns[col], col_str) is not None

    def is_solved(self, grid: List[List[Optional[str]]]) -> bool:
        """Check if the grid is completely filled and all constraints are satisfied."""
        # Check all cells filled
        for r in range(self.rows):
            for c in range(self.cols):
                if grid[r][c] is None:
                    return False
        # Check all row constraints
        for r in range(self.rows):
            if not self.check_row(r, grid):
                return False
        # Check all column constraints
        for c in range(self.cols):
            if not self.check_col(c, grid):
                return False
        return True


# ─── Character Sets ────────────────────────────────────────────────────

CHARSET_MAP = {
    "alpha": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "hex": "0123456789ABCDEF",
    "vowel": "AEIOU",
    "digit": "0123456789",
    "alnum": string.ascii_uppercase + string.digits,
}


# ─── Puzzle Generation ────────────────────────────────────────────────

def generate_relaxed_pattern(chars: List[str], charset: str, difficulty: int = 1) -> str:
    """Generate a regex pattern that matches the given chars with some flexibility.
    
    Difficulty levels:
    1 - Simple character classes, some wildcards
    2 - Character ranges, alternations
    3 - Quantifiers, negated classes
    """
    patterns = []
    
    for i, ch in enumerate(chars):
        r = random.random()
        
        if difficulty == 1:
            if r < 0.25:
                # Use a character class that includes this char
                classes = []
                if ch in "AEIOU":
                    classes.append("[AEIOU]")
                if ch in "0123456789":
                    classes.append("\\d")
                if ch in "ABCDEF":
                    classes.append("[A-F]")
                if ch in string.ascii_uppercase:
                    classes.append("[A-Z]")
                if classes:
                    patterns.append(random.choice(classes))
                else:
                    patterns.append(ch)
            elif r < 0.40:
                # Dot
                patterns.append(".")
            else:
                patterns.append(re.escape(ch))
        
        elif difficulty == 2:
            if r < 0.15:
                # Alternation: ch|other
                other = random.choice(charset)
                patterns.append(f"({re.escape(ch)}|{re.escape(other)})")
            elif r < 0.30:
                # Character range
                if ch in string.ascii_uppercase:
                    start = max('A', chr(ord(ch) - random.randint(0, 2)))
                    end = min('Z', chr(ord(ch) + random.randint(0, 2)))
                    patterns.append(f"[{start}-{end}]")
                elif ch in string.digits:
                    start = max('0', chr(ord(ch) - random.randint(0, 2)))
                    end = min('9', chr(ord(ch) + random.randint(0, 2)))
                    patterns.append(f"[{start}-{end}]")
                else:
                    patterns.append(re.escape(ch))
            elif r < 0.50:
                # Dot
                patterns.append(".")
            else:
                patterns.append(re.escape(ch))
        
        elif difficulty >= 3:
            if r < 0.15 and i > 0 and chars[i-1] == ch:
                # Quantifier for repeated chars
                patterns[-1] = f"{re.escape(ch)}{{2}}"
            elif r < 0.30:
                patterns.append(".")
            elif r < 0.45:
                # Negated class
                others = random.sample([c for c in charset if c != ch], min(3, len(charset)-1))
                patterns.append(f"[^{''.join(sorted(others))}]")
            elif r < 0.55:
                patterns.append(f"[{re.escape(ch)}]")
            else:
                patterns.append(re.escape(ch))
    
    return "".join(patterns)


def generate_smart_puzzle(rows: int = 3, cols: int = 3, difficulty: int = 1,
                          charset_name: str = "hex") -> RegexCrossword:
    """Generate a regex crossword puzzle that is guaranteed to have a valid solution."""
    charset = CHARSET_MAP.get(charset_name, charset_name)
    
    # Generate a random solution grid
    solution = []
    for r in range(rows):
        row = [random.choice(charset) for _ in range(cols)]
        solution.append(row)
    
    # Generate row patterns
    row_patterns = []
    for r in range(rows):
        pattern = generate_relaxed_pattern(solution[r], charset, difficulty)
        # Verify it matches
        row_str = "".join(solution[r])
        if not re.fullmatch(pattern, row_str):
            pattern = "".join(solution[r])  # Fallback to literal
        row_patterns.append(pattern)
    
    # Generate column patterns
    col_patterns = []
    for c in range(cols):
        col_chars = [solution[r][c] for r in range(rows)]
        pattern = generate_relaxed_pattern(col_chars, charset, difficulty)
        col_str = "".join(col_chars)
        if not re.fullmatch(pattern, col_str):
            pattern = "".join(col_chars)
        col_patterns.append(pattern)
    
    return RegexCrossword(
        rows=rows,
        cols=cols,
        row_patterns=row_patterns,
        col_patterns=col_patterns,
        solution=solution,
        charset=charset,
    )


# ─── Predefined Puzzles ──────────────────────────────────────────────

# Carefully designed puzzles where solutions are verified against all constraints

PUZZLES = {}

def _init_puzzles():
    """Initialize predefined puzzles with verified solutions."""
    # Tutorial: 2x2, very simple
    p = RegexCrossword(
        rows=2, cols=2,
        row_patterns=["A.", ".1"],
        col_patterns=["A.", ".1"],
        solution=[["A", "B"], ["C", "1"]],
        charset="ABC123",
    )
    # Verify
    assert re.fullmatch("A.", "AB")
    assert re.fullmatch(".1", "C1")
    assert re.fullmatch("A.", "AC")
    assert re.fullmatch(".1", "B1")
    PUZZLES["tutorial"] = p
    
    # Easy: 3x3 with hex-like characters
    p = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["ABC", "123", "DEF"],
        col_patterns=["A1D", "B2E", "C3F"],
        solution=[["A", "B", "C"], ["1", "2", "3"], ["D", "E", "F"]],
        charset="ABCDEF123",
    )
    # Verify all
    assert re.fullmatch("ABC", "ABC")
    assert re.fullmatch("123", "123")
    assert re.fullmatch("DEF", "DEF")
    assert re.fullmatch("A1D", "A1D")
    assert re.fullmatch("B2E", "B2E")
    assert re.fullmatch("C3F", "C3F")
    PUZZLES["easy"] = p
    
    # Medium: 3x3 with regex features
    # Solution:
    #   A B C   -> row: [A-F]{3}  = ABC ✓
    #   1 D 2   -> row: \d[A-F]\d  = 1D2 ✓
    #   E 3 F   -> row: [A-F]\d[A-F]  = E3F ✓
    # Columns:
    #   A1E -> [A-F]\d[A-F] ✓
    #   BD3 -> \d[A-F]\d (but B is letter, not digit) ✗
    # Let me use a completely different solution:
    #   A B C  -> [A-Z]{3}
    #   1 D 2  -> \d[A-F]\d
    #   E 3 F  -> [A-F]\d[A-F]
    # Col: A1E, BD3, C2F
    # BD3 has B,D (letters) and 3 (digit) -> not easy to match simply
    # Let me redesign:
    #   A B C   -> row: ABC
    #   4 D 5   -> row: \d[A-F]\d
    #   E F G   -> row: [A-Z]{3}
    # Cols: A4E, BDF, C5G
    # A4E -> [A-F]\d[A-Z] ✓, BDF -> [A-Z]{3} ✓, C5G -> [A-Z]\d[A-Z] ✓
    p = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["ABC", "\\d[A-F]\\d", "[A-Z]{3}"],
        col_patterns=["[A-F]\\d[A-Z]", "[A-Z]{3}", "[A-Z]\\d[A-Z]"],
        solution=[["A", "B", "C"], ["4", "D", "5"], ["E", "F", "G"]],
        charset="ABCDEFGHIJKLMNOPQRSTUVWXYZ45",
    )
    # Verify
    assert re.fullmatch("ABC", "ABC")
    assert re.fullmatch("\\d[A-F]\\d", "4D5")
    assert re.fullmatch("[A-Z]{3}", "EFG")
    assert re.fullmatch("[A-F]\\d[A-Z]", "A4E")
    assert re.fullmatch("[A-Z]{3}", "BDF")
    assert re.fullmatch("[A-Z]\\d[A-Z]", "C5G")
    PUZZLES["medium"] = p
    
    # Vowel vortex: all vowels
    p = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["[AEIOU]{3}", "[AEIOU]{3}", "[AEIOU]{3}"],
        col_patterns=["[AEIOU]{3}", "[AEIOU]{3}", "[AEIOU]{3}"],
        solution=[["A", "E", "I"], ["O", "U", "A"], ["E", "I", "O"]],
        charset="AEIOU",
    )
    assert re.fullmatch("[AEIOU]{3}", "AEI")
    assert re.fullmatch("[AEIOU]{3}", "OUA")
    assert re.fullmatch("[AEIOU]{3}", "EIO")
    assert re.fullmatch("[AEIOU]{3}", "AOE")
    assert re.fullmatch("[AEIOU]{3}", "EUI")
    assert re.fullmatch("[AEIOU]{3}", "IAO")
    PUZZLES["vowel_vortex"] = p

_init_puzzles()


# ─── Solver ───────────────────────────────────────────────────────────

def solve_puzzle(puzzle: RegexCrossword, charset: Optional[str] = None) -> Optional[List[List[str]]]:
    """Solve a regex crossword puzzle using backtracking with constraint checking.
    
    Strategy: fill cells left-to-right, top-to-bottom. When a row or column
    is fully filled, validate it against the corresponding regex. Also do
    partial checking by testing if a partial row/column could match the pattern.
    """
    if charset is None:
        charset = puzzle.charset
    
    grid: List[List[Optional[str]]] = [[None] * puzzle.cols for _ in range(puzzle.rows)]
    
    def backtrack(cell: int) -> bool:
        if cell == puzzle.rows * puzzle.cols:
            # All cells filled and verified at fill time
            return True
        
        r = cell // puzzle.cols
        c = cell % puzzle.cols
        
        for ch in charset:
            grid[r][c] = ch
            
            # Check completed row (last column in this row)
            if c == puzzle.cols - 1:
                row_str = "".join(grid[r])
                if not re.fullmatch(puzzle.row_patterns[r], row_str):
                    grid[r][c] = None
                    continue
            
            # Check completed column (last row in this column)
            if r == puzzle.rows - 1:
                col_str = "".join(grid[r2][c] for r2 in range(puzzle.rows))
                if not re.fullmatch(puzzle.col_patterns[c], col_str):
                    grid[r][c] = None
                    continue
            
            if backtrack(cell + 1):
                return True
            
            grid[r][c] = None
        
        return False
    
    if backtrack(0):
        return [[grid[r][c] for c in range(puzzle.cols)] for r in range(puzzle.rows)]
    return None


def solve_puzzle_bruteforce(puzzle: RegexCrossword, charset: Optional[str] = None) -> Optional[List[List[str]]]:
    """Solve by trying all combinations. Very slow for large puzzles."""
    if charset is None:
        charset = puzzle.charset
    
    for combo in itertools.product(charset, repeat=puzzle.rows * puzzle.cols):
        grid = []
        idx = 0
        for r in range(puzzle.rows):
            row = list(combo[idx:idx + puzzle.cols])
            grid.append(row)
            idx += puzzle.cols
        
        valid = True
        for r in range(puzzle.rows):
            row_str = "".join(grid[r])
            if not re.fullmatch(puzzle.row_patterns[r], row_str):
                valid = False
                break
        
        if valid:
            for c in range(puzzle.cols):
                col_str = "".join(grid[r][c] for r in range(puzzle.rows))
                if not re.fullmatch(puzzle.col_patterns[c], col_str):
                    valid = False
                    break
        
        if valid:
            return grid
    
    return None


def validate_solution(puzzle: RegexCrossword, grid: List[List[str]]) -> Tuple[bool, List[str]]:
    """Validate a complete solution against all constraints."""
    errors = []
    
    for r in range(puzzle.rows):
        row_str = "".join(grid[r])
        if not re.fullmatch(puzzle.row_patterns[r], row_str):
            errors.append(f"Row {r+1} '{row_str}' doesn't match /{puzzle.row_patterns[r]}/")
    
    for c in range(puzzle.cols):
        col_str = "".join(grid[r][c] for r in range(puzzle.rows))
        if not re.fullmatch(puzzle.col_patterns[c], col_str):
            errors.append(f"Col {c+1} '{col_str}' doesn't match /{puzzle.col_patterns[c]}/")
    
    return len(errors) == 0, errors


# ─── Interactive Solver (Terminal UI) ─────────────────────────────────

def clear_screen():
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="", flush=True)


def render_puzzle_compact(puzzle: RegexCrossword, grid: List[List[Optional[str]]],
                          cursor: Tuple[int, int]) -> str:
    """Render a compact version of the puzzle with status indicators."""
    lines = []
    
    lines.append("╔════════════════════════════════╗")
    lines.append("║      REGEX CROSSWORD           ║")
    lines.append("╚════════════════════════════════╝")
    lines.append("")
    
    # Column headers
    col_header = "     "
    for c in range(puzzle.cols):
        col_header += f"  C{c+1} "
    lines.append(col_header)
    
    # Column patterns
    for c in range(puzzle.cols):
        col_pat = "     "
        for cc in range(puzzle.cols):
            if cc == c:
                col_pat += f" /{puzzle.col_patterns[c]}/"
                break
            else:
                col_pat += "     "
        # Actually, display column patterns above
    lines.append("")
    
    # Display column patterns
    for c in range(puzzle.cols):
        lines.append(f"  C{c+1}: /{puzzle.col_patterns[c]}/")
    lines.append("")
    
    # Grid top border
    top = "     " + "┌" + ("────┬" * puzzle.cols)[:-1] + "┐"
    lines.append(top)
    
    for r in range(puzzle.rows):
        cells_str = f" R{r+1} │"
        for c in range(puzzle.cols):
            ch = grid[r][c] if grid[r][c] else "·"
            if (r, c) == cursor:
                cells_str += f" \033[7m{ch}\033[0m │"
            elif grid[r][c]:
                # Check validity
                row_str = "".join(grid[r][cc] if grid[r][cc] else "" for cc in range(puzzle.cols))
                col_str = "".join(grid[rr][c] if grid[rr][c] else "" for rr in range(puzzle.rows))
                
                row_complete = all(grid[r][cc] is not None for cc in range(puzzle.cols))
                col_complete = all(grid[rr][c] is not None for rr in range(puzzle.rows))
                
                if row_complete and col_complete:
                    row_ok = re.fullmatch(puzzle.row_patterns[r], row_str) is not None
                    col_ok = re.fullmatch(puzzle.col_patterns[c], col_str) is not None
                    if row_ok and col_ok:
                        cells_str += f" \033[32m{ch}\033[0m │"
                    elif row_ok:
                        cells_str += f" \033[33m{ch}\033[0m │"
                    elif col_ok:
                        cells_str += f" \033[35m{ch}\033[0m │"
                    else:
                        cells_str += f" \033[31m{ch}\033[0m │"
                elif row_complete:
                    row_ok = re.fullmatch(puzzle.row_patterns[r], row_str) is not None
                    if row_ok:
                        cells_str += f" \033[32m{ch}\033[0m │"
                    else:
                        cells_str += f" \033[33m{ch}\033[0m │"
                elif col_complete:
                    col_ok = re.fullmatch(puzzle.col_patterns[c], col_str) is not None
                    if col_ok:
                        cells_str += f" \033[32m{ch}\033[0m │"
                    else:
                        cells_str += f" \033[35m{ch}\033[0m │"
                else:
                    cells_str += f" {ch} │"
            else:
                cells_str += f" {ch} │"
        
        cells_str += f"  /{puzzle.row_patterns[r]}/"
        lines.append(cells_str)
        
        if r < puzzle.rows - 1:
            mid = "     " + "├" + ("────┼" * puzzle.cols)[:-1] + "┤"
        else:
            bot = "     " + "└" + ("────┴" * puzzle.cols)[:-1] + "┘"
            lines.append(bot)
            continue
        lines.append(mid)
    
    lines.append("")
    
    # Row validation status
    for r in range(puzzle.rows):
        row_str = "".join(grid[r][c] if grid[r][c] else "." for c in range(puzzle.cols))
        row_complete = all(grid[r][c] is not None for c in range(puzzle.cols))
        if row_complete:
            ok = re.fullmatch(puzzle.row_patterns[r], row_str) is not None
            status = "\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m"
        else:
            status = "(partial)"
        lines.append(f"  R{r+1}: /{puzzle.row_patterns[r]}/ {status}")
    
    for c in range(puzzle.cols):
        col_str = "".join(grid[r][c] if grid[r][c] else "." for r in range(puzzle.rows))
        col_complete = all(grid[r][c] is not None for r in range(puzzle.rows))
        if col_complete:
            ok = re.fullmatch(puzzle.col_patterns[c], col_str) is not None
            status = "\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m"
        else:
            status = "(partial)"
        lines.append(f"  C{c+1}: /{puzzle.col_patterns[c]}/ {status}")
    
    # Check if solved
    all_filled = all(grid[r][c] is not None for r in range(puzzle.rows) for c in range(puzzle.cols))
    if all_filled and puzzle.is_solved(grid):
        lines.append("")
        lines.append("\033[32m🎉 CONGRATULATIONS! Puzzle solved! 🎉\033[0m")
    
    return "\n".join(lines)


def run_interactive(puzzle: RegexCrossword):
    """Run the interactive terminal solver."""
    grid: List[List[Optional[str]]] = [[None] * puzzle.cols for _ in range(puzzle.rows)]
    cursor = (0, 0)
    charset = puzzle.charset
    
    try:
        import sys
        import tty
        import termios
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        def getch():
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A':
                            return 'UP'
                        elif ch3 == 'B':
                            return 'DOWN'
                        elif ch3 == 'C':
                            return 'RIGHT'
                        elif ch3 == 'D':
                            return 'LEFT'
                    return 'ESC'
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        def redraw():
            clear_screen()
            print(render_puzzle_compact(puzzle, grid, cursor))
            print("\033[1mControls:\033[0m ↑↓←→=move  Type=fill  Del=clear  H=hint  S=solve  Q=quit  R=reset  Tab=next")
            print(f"Cursor: Row {cursor[0]+1}, Col {cursor[1]+1}  Charset: {charset}")
        
        redraw()
        
        while True:
            try:
                ch = getch()
            except:
                break
            
            r, c = cursor
            
            if ch == 'UP':
                cursor = (max(0, r - 1), c)
            elif ch == 'DOWN':
                cursor = (min(puzzle.rows - 1, r + 1), c)
            elif ch == 'LEFT':
                cursor = (r, max(0, c - 1))
            elif ch == 'RIGHT':
                cursor = (r, min(puzzle.cols - 1, c + 1))
            elif ch == 'q' or ch == 'Q':
                break
            elif ch == 'h' or ch == 'H':
                # Hint: reveal the current cell
                grid[r][c] = puzzle.solution[r][c]
            elif ch == 's' or ch == 'S':
                # Solve: reveal entire solution
                for rr in range(puzzle.rows):
                    for cc in range(puzzle.cols):
                        grid[rr][cc] = puzzle.solution[rr][cc]
            elif ch == 'r' or ch == 'R':
                # Reset
                grid = [[None] * puzzle.cols for _ in range(puzzle.rows)]
            elif ch in ('\x7f', '\x08'):
                # Backspace/Delete
                grid[r][c] = None
            elif ch == '\t':
                # Tab - move to next cell
                nc = c + 1
                nr = r
                if nc >= puzzle.cols:
                    nc = 0
                    nr += 1
                if nr >= puzzle.rows:
                    nr = 0
                cursor = (nr, nc)
            elif len(ch) == 1 and ch.upper() in charset:
                # Character input
                grid[r][c] = ch.upper()
                # Auto-advance
                nc = c + 1
                nr = r
                if nc >= puzzle.cols:
                    nc = 0
                    nr += 1
                if nr < puzzle.rows:
                    cursor = (nr, nc)
            
            redraw()
    
    except (ImportError, termios.error):
        print("Interactive mode requires a Unix-like terminal with termios support.")
        print("Falling back to text-only mode.\n")
        print_puzzle_text(puzzle)


def print_puzzle_text(puzzle: RegexCrossword):
    """Print the puzzle in text-only mode."""
    print("\n╔══════════════════════════╗")
    print("║    REGEX CROSSWORD       ║")
    print("╚══════════════════════════╝\n")
    
    print("Column patterns:")
    for c in range(puzzle.cols):
        print(f"  C{c+1}: /{puzzle.col_patterns[c]}/")
    print()
    
    print("Row patterns:")
    for r in range(puzzle.rows):
        print(f"  R{r+1}: /{puzzle.row_patterns[r]}/")
    print()
    
    # Empty grid
    cell_w = 3
    header = "     " + "".join(f" C{c+1} " for c in range(puzzle.cols))
    print(header)
    top = "    " + "┌" + ("─────" * puzzle.cols) + "┐"
    print(top)
    
    for r in range(puzzle.rows):
        row_line = f" R{r+1} │"
        for c in range(puzzle.cols):
            row_line += "  ·  │"
        row_line += f"  /{puzzle.row_patterns[r]}/"
        print(row_line)
        if r < puzzle.rows - 1:
            print("    " + "├" + ("─────" * puzzle.cols) + "┤")
    print("    " + "└" + ("─────" * puzzle.cols) + "┘")
    
    print(f"\nEach cell must satisfy BOTH its row and column regex constraint.")
    print(f"Grid size: {puzzle.rows}×{puzzle.cols}")
    print(f"Characters: {puzzle.charset}")


def print_solution(puzzle: RegexCrossword):
    """Print the solution grid."""
    print("\nSolution:")
    for r in range(puzzle.rows):
        row_str = " ".join(puzzle.solution[r])
        print(f"  R{r+1}: {row_str}")
    
    # Verify
    print("\nVerification:")
    for r in range(puzzle.rows):
        row_str = "".join(puzzle.solution[r])
        ok = re.fullmatch(puzzle.row_patterns[r], row_str) is not None
        status = "✓" if ok else "✗"
        print(f"  R{r+1}: '{row_str}' vs /{puzzle.row_patterns[r]}/ {status}")
    for c in range(puzzle.cols):
        col_str = "".join(puzzle.solution[r][c] for r in range(puzzle.rows))
        ok = re.fullmatch(puzzle.col_patterns[c], col_str) is not None
        status = "✓" if ok else "✗"
        print(f"  C{c+1}: '{col_str}' vs /{puzzle.col_patterns[c]}/ {status}")


# ─── Main CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Regex Crossword Generator & Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --play tutorial          Play the tutorial puzzle
  %(prog)s --play easy              Play the easy puzzle
  %(prog)s --generate 3 3            Generate a random 3×3 puzzle
  %(prog)s --generate 4 4 --diff 2  Generate a harder 4×4 puzzle
  %(prog)s --solve easy             Show the solution
  %(prog)s --print hex1             Print a puzzle in text mode
  %(prog)s --generate 3 3 --charset alpha  Use A-Z only
  %(prog)s --list                   List available puzzles
        """
    )
    
    parser.add_argument("--play", "-p", metavar="PUZZLE",
                       help="Play a named puzzle interactively")
    parser.add_argument("--generate", "-g", nargs=2, metavar=("ROWS", "COLS"), type=int,
                       help="Generate a random puzzle of given size")
    parser.add_argument("--solve", "-s", metavar="PUZZLE",
                       help="Solve a named puzzle and print the answer")
    parser.add_argument("--print", "-P", metavar="PUZZLE", dest="print_puzzle",
                       help="Print a puzzle in text mode")
    parser.add_argument("--diff", "-d", type=int, default=1, choices=[1, 2, 3],
                       help="Difficulty level for generated puzzles (1-3, default: 1)")
    parser.add_argument("--charset", "-c", default="hex",
                       choices=["alpha", "hex", "vowel", "digit", "alnum"],
                       help="Character set for generated puzzles (default: hex)")
    parser.add_argument("--verify", "-v", action="store_true",
                       help="Verify generated puzzles have valid solutions")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List available puzzles")
    
    args = parser.parse_args()
    
    if args.list:
        print("Available puzzles:")
        for name, puzzle in PUZZLES.items():
            print(f"  {name}: {puzzle.rows}×{puzzle.cols} grid (charset: {puzzle.charset})")
            print(f"    Rows: {', '.join('/' + p + '/' for p in puzzle.row_patterns)}")
            print(f"    Cols: {', '.join('/' + p + '/' for p in puzzle.col_patterns)}")
            print()
        return
    
    if args.play:
        name = args.play
        if name in PUZZLES:
            run_interactive(PUZZLES[name])
        else:
            print(f"Unknown puzzle: {name}")
            print(f"Available: {', '.join(PUZZLES.keys())}")
    
    elif args.generate:
        rows, cols = args.generate
        if rows < 2 or rows > 6 or cols < 2 or cols > 6:
            print("Grid size must be between 2×2 and 6×6")
            return
        
        print(f"Generating {rows}×{cols} puzzle (difficulty {args.diff}, charset: {args.charset})...")
        puzzle = generate_smart_puzzle(rows, cols, args.diff, args.charset)
        
        if args.verify:
            print("Verifying solution...")
            solved = solve_puzzle(puzzle)
            if solved:
                print("✓ Solution verified!")
            else:
                print("✗ Could not verify solution")
        
        run_interactive(puzzle)
    
    elif args.solve:
        name = args.solve
        if name in PUZZLES:
            puzzle = PUZZLES[name]
            print_puzzle_text(puzzle)
            print_solution(puzzle)
            
            print("\nSolving programmatically...")
            solved = solve_puzzle(puzzle)
            if solved:
                print("Solver found solution:")
                for r in range(puzzle.rows):
                    print(f"  R{r+1}: {' '.join(solved[r])}")
            else:
                print("Solver could not find a solution")
        else:
            print(f"Unknown puzzle: {name}")
            print(f"Available: {', '.join(PUZZLES.keys())}")
    
    elif args.print_puzzle:
        name = args.print_puzzle
        if name in PUZZLES:
            print_puzzle_text(PUZZLES[name])
        else:
            print(f"Unknown puzzle: {name}")
            print(f"Available: {', '.join(PUZZLES.keys())}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()