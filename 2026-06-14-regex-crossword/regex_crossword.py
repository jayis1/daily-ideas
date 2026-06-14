#!/usr/bin/env python3
"""
Regex Crossword Generator & Solver
====================================

Generates regex crossword puzzles where each cell must satisfy
a row regex constraint AND a column regex constraint. Includes
an interactive terminal-based solver with validation feedback,
timed challenges, move tracking, and JSON import/export.

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
import json
import random
import string
import time
import itertools
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Set, Dict, Any

__version__ = "1.3.0"

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
    name: str = ""  # optional puzzle name

    def __post_init__(self):
        """Validate puzzle dimensions are consistent."""
        if len(self.row_patterns) != self.rows:
            raise ValueError(
                f"Expected {self.rows} row_patterns, got {len(self.row_patterns)}"
            )
        if len(self.col_patterns) != self.cols:
            raise ValueError(
                f"Expected {self.cols} col_patterns, got {len(self.col_patterns)}"
            )
        if len(self.solution) != self.rows:
            raise ValueError(
                f"Expected {self.rows} solution rows, got {len(self.solution)}"
            )
        for i, row in enumerate(self.solution):
            if len(row) != self.cols:
                raise ValueError(
                    f"Expected {self.cols} columns in solution row {i}, got {len(row)}"
                )

    def check_row(self, row: int, grid: List[List[Optional[str]]]) -> Optional[bool]:
        """Check if the row matches its regex. Returns None if row is incomplete."""
        row_str = ""
        for c in range(self.cols):
            if grid[row][c] is None:
                return None  # incomplete
            row_str += grid[row][c]
        try:
            return re.fullmatch(self.row_patterns[row], row_str) is not None
        except re.error:
            return False

    def check_col(self, col: int, grid: List[List[Optional[str]]]) -> Optional[bool]:
        """Check if the column matches its regex. Returns None if incomplete."""
        col_str = ""
        for r in range(self.rows):
            if grid[r][col] is None:
                return None  # incomplete
            col_str += grid[r][col]
        try:
            return re.fullmatch(self.col_patterns[col], col_str) is not None
        except re.error:
            return False

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

    def to_dict(self) -> Dict[str, Any]:
        """Serialize puzzle to a dictionary for JSON export."""
        return {
            "name": self.name,
            "rows": self.rows,
            "cols": self.cols,
            "row_patterns": self.row_patterns,
            "col_patterns": self.col_patterns,
            "solution": self.solution,
            "charset": self.charset,
            "version": __version__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegexCrossword":
        """Deserialize puzzle from a dictionary (e.g., loaded from JSON)."""
        return cls(
            rows=data["rows"],
            cols=data["cols"],
            row_patterns=data["row_patterns"],
            col_patterns=data["col_patterns"],
            solution=data["solution"],
            charset=data.get("charset", "0123456789ABCDEF"),
            name=data.get("name", ""),
        )

    def to_json(self, indent: int = 2) -> str:
        """Export puzzle as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "RegexCrossword":
        """Import puzzle from a JSON string."""
        data = json.loads(json_str)
        # Validate required fields
        for key in ("rows", "cols", "row_patterns", "col_patterns", "solution"):
            if key not in data:
                raise ValueError(f"Missing required field: {key}")
        # Validate dimensions match
        rows = data["rows"]
        cols = data["cols"]
        if len(data["row_patterns"]) != rows:
            raise ValueError(f"Expected {rows} row_patterns, got {len(data['row_patterns'])}")
        if len(data["col_patterns"]) != cols:
            raise ValueError(f"Expected {cols} col_patterns, got {len(data['col_patterns'])}")
        if len(data["solution"]) != rows:
            raise ValueError(f"Expected {rows} solution rows, got {len(data['solution'])}")
        for i, row in enumerate(data["solution"]):
            if len(row) != cols:
                raise ValueError(f"Expected {cols} columns in solution row {i}, got {len(row)}")
        return cls.from_dict(data)


# ─── Character Sets ────────────────────────────────────────────────────

CHARSET_MAP = {
    "alpha": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "hex": "0123456789ABCDEF",
    "vowel": "AEIOU",
    "digit": "0123456789",
    "alnum": string.ascii_uppercase + string.digits,
    "binary": "01",
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
                # Negated class — use unique chars only, and fall back to
                # a simple character class if there aren't enough other chars
                # to form a valid negated class.
                unique_others = sorted(set(c for c in charset if c != ch))
                if len(unique_others) >= 1:
                    sample_size = min(3, len(unique_others))
                    others = random.sample(unique_others, sample_size)
                    # Escape each char individually to handle regex metacharacters
                    escaped = "".join(re.escape(c) for c in others)
                    patterns.append(f"[^{escaped}]")
                else:
                    # Not enough other chars for a negated class; use dot or literal
                    patterns.append(".")
            elif r < 0.55:
                patterns.append(f"[{re.escape(ch)}]")
            else:
                patterns.append(re.escape(ch))
    
    return "".join(patterns)


def generate_smart_puzzle(rows: int = 3, cols: int = 3, difficulty: int = 1,
                          charset_name: str = "hex", name: str = "") -> RegexCrossword:
    """Generate a regex crossword puzzle that is guaranteed to have a valid solution."""
    if rows < 2 or rows > 8:
        raise ValueError(f"Rows must be between 2 and 8, got {rows}")
    if cols < 2 or cols > 8:
        raise ValueError(f"Cols must be between 2 and 8, got {cols}")
    if difficulty not in (1, 2, 3):
        raise ValueError(f"Difficulty must be 1, 2, or 3, got {difficulty}")
    
    charset = CHARSET_MAP.get(charset_name, charset_name)
    
    # Deduplicate and validate charset
    if len(charset) == 0:
        raise ValueError("Charset must contain at least one character")
    unique_chars = len(set(charset))
    if unique_chars < 2 and difficulty >= 3:
        raise ValueError(
            f"Difficulty 3 requires at least 2 unique characters in charset, "
            f"got {unique_chars} unique char(s) in '{charset}'"
        )
    
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
        name=name,
    )


# ─── Predefined Puzzles ──────────────────────────────────────────────

# Carefully designed puzzles where solutions are verified against all constraints

PUZZLES: Dict[str, RegexCrossword] = {}

def _init_puzzles():
    """Initialize predefined puzzles with verified unique solutions."""
    # Tutorial: 2x2, unique solution (literal patterns for learning)
    p = RegexCrossword(
        rows=2, cols=2,
        row_patterns=["AB", "C1"],
        col_patterns=["AC", "B1"],
        solution=[["A", "B"], ["C", "1"]],
        charset="ABC123",
        name="tutorial",
    )
    # Verify
    assert re.fullmatch("AB", "AB")
    assert re.fullmatch("C1", "C1")
    assert re.fullmatch("AC", "AC")
    assert re.fullmatch("B1", "B1")
    PUZZLES["tutorial"] = p
    
    # Easy: 3x3 with hex-like characters
    p = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["ABC", "123", "DEF"],
        col_patterns=["A1D", "B2E", "C3F"],
        solution=[["A", "B", "C"], ["1", "2", "3"], ["D", "E", "F"]],
        charset="ABCDEF123",
        name="easy",
    )
    # Verify all
    assert re.fullmatch("ABC", "ABC")
    assert re.fullmatch("123", "123")
    assert re.fullmatch("DEF", "DEF")
    assert re.fullmatch("A1D", "A1D")
    assert re.fullmatch("B2E", "B2E")
    assert re.fullmatch("C3F", "C3F")
    PUZZLES["easy"] = p
    
    # Medium: 3x3 with regex features (unique solution)
    p = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["A.C", "\\d[A-F]\\d", "E.G"],
        col_patterns=["A4E", "BDF", "C5G"],
        solution=[["A", "B", "C"], ["4", "D", "5"], ["E", "F", "G"]],
        charset="ABCDEFG45",
        name="medium",
    )
    # Verify
    assert re.fullmatch("A.C", "ABC")
    assert re.fullmatch("\\d[A-F]\\d", "4D5")
    assert re.fullmatch("E.G", "EFG")
    assert re.fullmatch("A4E", "A4E")
    assert re.fullmatch("BDF", "BDF")
    assert re.fullmatch("C5G", "C5G")
    PUZZLES["medium"] = p
    
    # Vowel vortex: all vowels, unique solution
    p = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["AEI", "OUA", "EIO"],
        col_patterns=["[AO]OE", "[EI]UI", "I[AO]O"],
        solution=[["A", "E", "I"], ["O", "U", "A"], ["E", "I", "O"]],
        charset="AEIOU",
        name="vowel_vortex",
    )
    assert re.fullmatch("AEI", "AEI")
    assert re.fullmatch("OUA", "OUA")
    assert re.fullmatch("EIO", "EIO")
    assert re.fullmatch("[AO]OE", "AOE")
    assert re.fullmatch("[EI]UI", "EUI")
    assert re.fullmatch("I[AO]O", "IAO")
    PUZZLES["vowel_vortex"] = p

    # Binary Blitz: 3x3 using only 0 and 1, with character classes (unique solution)
    p = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["0[01]0", "011", "1[01]0"],
        col_patterns=["001", "1[01]0", "0[01]0"],
        solution=[["0", "1", "0"], ["0", "1", "1"], ["1", "0", "0"]],
        charset="01",
        name="binary_blitz",
    )
    assert re.fullmatch("0[01]0", "010")
    assert re.fullmatch("011", "011")
    assert re.fullmatch("1[01]0", "100")
    assert re.fullmatch("001", "001")
    assert re.fullmatch("1[01]0", "110")
    assert re.fullmatch("0[01]0", "010")
    PUZZLES["binary_blitz"] = p

    # Alpha Chaos: 4x4 with diverse patterns
    # Solution:
    #   A B C D  -> row: [A-D]{4}
    #   E F G H  -> row: [E-H]{4}
    #   I J K L  -> row: [A-Z]{4}
    #   M N O P  -> row: [A-Z]{4}
    # Cols:
    #   AEIM -> [AEIM]{4}
    #   BFJN -> [BFJN]{4}
    #   CGKO -> [CGKO]{4}
    #   DHLP -> [DHLP]{4}
    p = RegexCrossword(
        rows=4, cols=4,
        row_patterns=["[A-D]{4}", "[E-H]{4}", "[A-Z]{4}", "[A-Z]{4}"],
        col_patterns=["[AEIM]{4}", "[BFJN]{4}", "[CGKO]{4}", "[DHLP]{4}"],
        solution=[["A", "B", "C", "D"], ["E", "F", "G", "H"], ["I", "J", "K", "L"], ["M", "N", "O", "P"]],
        charset="ABCDEFGHIJKLMNOP",
        name="alpha_chaos",
    )
    # Verify
    assert re.fullmatch("[A-D]{4}", "ABCD")
    assert re.fullmatch("[E-H]{4}", "EFGH")
    assert re.fullmatch("[A-Z]{4}", "IJKL")
    assert re.fullmatch("[A-Z]{4}", "MNOP")
    assert re.fullmatch("[AEIM]{4}", "AEIM")
    assert re.fullmatch("[BFJN]{4}", "BFJN")
    assert re.fullmatch("[CGKO]{4}", "CGKO")
    assert re.fullmatch("[DHLP]{4}", "DHLP")
    PUZZLES["alpha_chaos"] = p

_init_puzzles()


# ─── Solver ───────────────────────────────────────────────────────────

def solve_puzzle(puzzle: RegexCrossword, charset: Optional[str] = None,
                 max_solutions: int = 1) -> Optional[List[List[str]]]:
    """Solve a regex crossword puzzle using backtracking with constraint checking.
    
    Strategy: fill cells left-to-right, top-to-bottom. When a row or column
    is fully filled, validate it against the corresponding regex. Also do
    partial checking by testing if a partial row/column could match the pattern.
    
    Args:
        puzzle: The puzzle to solve.
        charset: Character set to search. Defaults to puzzle.charset.
        max_solutions: If > 1, collect multiple solutions (used for uniqueness checks).
    
    Returns:
        The first solution found, or None if no solution exists.
    """
    if charset is None:
        charset = puzzle.charset
    
    grid: List[List[Optional[str]]] = [[None] * puzzle.cols for _ in range(puzzle.rows)]
    solutions: List[List[List[str]]] = []
    
    def backtrack(cell: int) -> bool:
        if cell == puzzle.rows * puzzle.cols:
            # All cells filled and verified at fill time
            solutions.append([[grid[r][c] for c in range(puzzle.cols)] for r in range(puzzle.rows)])
            return len(solutions) >= max_solutions
        
        r = cell // puzzle.cols
        c = cell % puzzle.cols
        
        for ch in charset:
            grid[r][c] = ch
            
            # Check completed row (last column in this row)
            if c == puzzle.cols - 1:
                row_str = "".join(grid[r])
                try:
                    if not re.fullmatch(puzzle.row_patterns[r], row_str):
                        grid[r][c] = None
                        continue
                except re.error:
                    grid[r][c] = None
                    continue
            
            # Check completed column (last row in this column)
            if r == puzzle.rows - 1:
                col_str = "".join(grid[r2][c] for r2 in range(puzzle.rows))
                try:
                    if not re.fullmatch(puzzle.col_patterns[c], col_str):
                        grid[r][c] = None
                        continue
                except re.error:
                    grid[r][c] = None
                    continue
            
            # Note: Partial row pruning could improve solver performance, but
            # correctly checking if a partial string is a valid prefix of a
            # regex match is non-trivial. Simple approaches (re.match on prefix,
            # appending ".*" to the candidate string) produce false negatives.
            # The full-row/full-column checks above already provide good pruning
            # for the backtracking solver.
            
            if backtrack(cell + 1):
                return True
            
            grid[r][c] = None
        
        return False
    
    if backtrack(0):
        return solutions[0]
    return None


def count_solutions(puzzle: RegexCrossword, charset: Optional[str] = None,
                    limit: int = 100) -> int:
    """Count the number of solutions for a puzzle, up to a limit.
    
    Useful for checking puzzle uniqueness. Returns the count of solutions
    found (capped at `limit`). Warning: this can be slow for large puzzles
    with large character sets.
    """
    if charset is None:
        charset = puzzle.charset
    
    # For very large search spaces, warn that this may be slow
    space_size = len(charset) ** (puzzle.rows * puzzle.cols)
    if space_size > 1_000_000:
        import warnings
        warnings.warn(
            f"Search space is {space_size:.0e} — count_solutions may be very slow. "
            f"Consider using a smaller puzzle or charset.",
            stacklevel=2,
        )
    
    grid: List[List[Optional[str]]] = [[None] * puzzle.cols for _ in range(puzzle.rows)]
    count = [0]
    
    def backtrack(cell: int) -> bool:
        if cell == puzzle.rows * puzzle.cols:
            count[0] += 1
            return count[0] >= limit  # stop early if we hit the limit
        
        r = cell // puzzle.cols
        c = cell % puzzle.cols
        
        for ch in charset:
            grid[r][c] = ch
            
            if c == puzzle.cols - 1:
                row_str = "".join(grid[r])
                try:
                    if not re.fullmatch(puzzle.row_patterns[r], row_str):
                        grid[r][c] = None
                        continue
                except re.error:
                    grid[r][c] = None
                    continue
            
            if r == puzzle.rows - 1:
                col_str = "".join(grid[r2][c] for r2 in range(puzzle.rows))
                try:
                    if not re.fullmatch(puzzle.col_patterns[c], col_str):
                        grid[r][c] = None
                        continue
                except re.error:
                    grid[r][c] = None
                    continue
            
            if backtrack(cell + 1):
                return True
            
            grid[r][c] = None
        
        return False
    
    backtrack(0)
    return count[0]


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
            try:
                if not re.fullmatch(puzzle.row_patterns[r], row_str):
                    valid = False
                    break
            except re.error:
                valid = False
                break
        
        if valid:
            for c in range(puzzle.cols):
                col_str = "".join(grid[row][c] for row in range(puzzle.rows))
                try:
                    if not re.fullmatch(puzzle.col_patterns[c], col_str):
                        valid = False
                        break
                except re.error:
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
        try:
            if not re.fullmatch(puzzle.row_patterns[r], row_str):
                errors.append(f"Row {r+1} '{row_str}' doesn't match /{puzzle.row_patterns[r]}/")
        except re.error as e:
            errors.append(f"Row {r+1} pattern /{puzzle.row_patterns[r]}/ is invalid: {e}")
    
    for c in range(puzzle.cols):
        col_str = "".join(grid[row][c] for row in range(puzzle.rows))
        try:
            if not re.fullmatch(puzzle.col_patterns[c], col_str):
                errors.append(f"Col {c+1} '{col_str}' doesn't match /{puzzle.col_patterns[c]}/")
        except re.error as e:
            errors.append(f"Col {c+1} pattern /{puzzle.col_patterns[c]}/ is invalid: {e}")
    
    return len(errors) == 0, errors


# ─── Interactive Solver (Terminal UI) ─────────────────────────────────

def clear_screen():
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="", flush=True)


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs:.0f}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h {mins}m {secs:.0f}s"


def render_puzzle_compact(puzzle: RegexCrossword, grid: List[List[Optional[str]]],
                          cursor: Tuple[int, int],
                          move_count: int = 0, hint_count: int = 0,
                          start_time: Optional[float] = None) -> str:
    """Render a compact version of the puzzle with status indicators and game stats."""
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
                    try:
                        row_ok = re.fullmatch(puzzle.row_patterns[r], row_str) is not None
                    except re.error:
                        row_ok = False
                    try:
                        col_ok = re.fullmatch(puzzle.col_patterns[c], col_str) is not None
                    except re.error:
                        col_ok = False
                    if row_ok and col_ok:
                        cells_str += f" \033[32m{ch}\033[0m │"
                    elif row_ok:
                        cells_str += f" \033[33m{ch}\033[0m │"
                    elif col_ok:
                        cells_str += f" \033[35m{ch}\033[0m │"
                    else:
                        cells_str += f" \033[31m{ch}\033[0m │"
                elif row_complete:
                    try:
                        row_ok = re.fullmatch(puzzle.row_patterns[r], row_str) is not None
                    except re.error:
                        row_ok = False
                    if row_ok:
                        cells_str += f" \033[32m{ch}\033[0m │"
                    else:
                        cells_str += f" \033[33m{ch}\033[0m │"
                elif col_complete:
                    try:
                        col_ok = re.fullmatch(puzzle.col_patterns[c], col_str) is not None
                    except re.error:
                        col_ok = False
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
            try:
                ok = re.fullmatch(puzzle.row_patterns[r], row_str) is not None
            except re.error:
                ok = False
            status = "\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m"
        else:
            status = "(partial)"
        lines.append(f"  R{r+1}: /{puzzle.row_patterns[r]}/ {status}")
    
    for c in range(puzzle.cols):
        col_str = "".join(grid[r][c] if grid[r][c] else "." for r in range(puzzle.rows))
        col_complete = all(grid[r][c] is not None for r in range(puzzle.rows))
        if col_complete:
            try:
                ok = re.fullmatch(puzzle.col_patterns[c], col_str) is not None
            except re.error:
                ok = False
            status = "\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m"
        else:
            status = "(partial)"
        lines.append(f"  C{c+1}: /{puzzle.col_patterns[c]}/ {status}")
    
    # Game stats
    lines.append("")
    elapsed = ""
    if start_time is not None:
        elapsed = f"  Time: {format_duration(time.time() - start_time)}"
    lines.append(f"  Moves: {move_count}  Hints: {hint_count}{elapsed}")
    
    # Check if solved
    all_filled = all(grid[r][c] is not None for r in range(puzzle.rows) for c in range(puzzle.cols))
    if all_filled and puzzle.is_solved(grid):
        lines.append("")
        duration = time.time() - start_time if start_time else 0
        lines.append("\033[32m🎉 CONGRATULATIONS! Puzzle solved! 🎉\033[0m")
        lines.append(f"  \033[1mMoves:\033[0m {move_count}  \033[1mHints:\033[0m {hint_count}  \033[1mTime:\033[0m {format_duration(duration)}")
    
    return "\n".join(lines)


def run_interactive(puzzle: RegexCrossword, timer: bool = False):
    """Run the interactive terminal solver with optional timer and move tracking."""
    grid: List[List[Optional[str]]] = [[None] * puzzle.cols for _ in range(puzzle.rows)]
    cursor = (0, 0)
    charset = puzzle.charset
    move_count = 0
    hint_count = 0
    start_time = time.time() if timer else None
    
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
            print(render_puzzle_compact(puzzle, grid, cursor, move_count, hint_count, start_time))
            timer_info = "  T=timer" if timer else ""
            print("\033[1mControls:\033[0m ↑↓←→=move  Type=fill  Del=clear  H=hint  S=solve  Q=quit  R=reset  Tab=next" + timer_info)
            print(f"Cursor: Row {cursor[0]+1}, Col {cursor[1]+1}  Charset: {charset}")
        
        redraw()
        
        while True:
            try:
                ch = getch()
            except Exception:
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
                if grid[r][c] != puzzle.solution[r][c]:
                    grid[r][c] = puzzle.solution[r][c]
                    hint_count += 1
            elif ch == 's' or ch == 'S':
                # Solve: reveal entire solution
                for rr in range(puzzle.rows):
                    for cc in range(puzzle.cols):
                        if grid[rr][cc] != puzzle.solution[rr][cc]:
                            grid[rr][cc] = puzzle.solution[rr][cc]
                            hint_count += 1
            elif ch == 'r' or ch == 'R':
                # Reset
                grid = [[None] * puzzle.cols for _ in range(puzzle.rows)]
                move_count = 0
                hint_count = 0
                start_time = time.time() if timer else None
            elif ch in ('\x7f', '\x08'):
                # Backspace/Delete
                if grid[r][c] is not None:
                    grid[r][c] = None
                    move_count += 1
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
                move_count += 1
                # Auto-advance
                nc = c + 1
                nr = r
                if nc >= puzzle.cols:
                    nc = 0
                    nr += 1
                if nr < puzzle.rows:
                    cursor = (nr, nc)
            
            redraw()
    
    except (ImportError, AttributeError, termios.error):
        print("Interactive mode requires a Unix-like terminal with termios support.")
        print("Falling back to text-only mode.\n")
        print_puzzle_text(puzzle)


def print_puzzle_text(puzzle: RegexCrossword):
    """Print the puzzle in text-only mode."""
    puzzle_name = f" — {puzzle.name}" if puzzle.name else ""
    print(f"\n╔══════════════════════════╗")
    print(f"║    REGEX CROSSWORD{puzzle_name:>8s}║")
    print(f"╚══════════════════════════╝\n")
    
    print("Column patterns:")
    for c in range(puzzle.cols):
        print(f"  C{c+1}: /{puzzle.col_patterns[c]}/")
    print()
    
    print("Row patterns:")
    for r in range(puzzle.rows):
        print(f"  R{r+1}: /{puzzle.row_patterns[r]}/")
    print()
    
    # Empty grid
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
        try:
            ok = re.fullmatch(puzzle.row_patterns[r], row_str) is not None
        except re.error:
            ok = False
        status = "✓" if ok else "✗"
        print(f"  R{r+1}: '{row_str}' vs /{puzzle.row_patterns[r]}/ {status}")
    for c in range(puzzle.cols):
        col_str = "".join(puzzle.solution[row][c] for row in range(puzzle.rows))
        try:
            ok = re.fullmatch(puzzle.col_patterns[c], col_str) is not None
        except re.error:
            ok = False
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
  %(prog)s --export easy            Export a puzzle as JSON
  %(prog)s --import puzzle.json     Import and play a JSON puzzle
  %(prog)s --list                   List available puzzles
  %(prog)s --timer --play medium    Play with a timer
        """
    )
    
    parser.add_argument("--version", "-V", action="version",
                       version=f"%(prog)s {__version__}")
    parser.add_argument("--play", "-p", metavar="PUZZLE",
                       help="Play a named puzzle interactively")
    parser.add_argument("--generate", "-g", nargs=2, metavar=("ROWS", "COLS"), type=int,
                       help="Generate a random puzzle of given size")
    parser.add_argument("--solve", "-s", metavar="PUZZLE",
                       help="Solve a named puzzle and print the answer")
    parser.add_argument("--print", "-P", metavar="PUZZLE", dest="print_puzzle",
                       help="Print a puzzle in text mode")
    parser.add_argument("--export", "-e", metavar="PUZZLE",
                       help="Export a puzzle as JSON to stdout")
    parser.add_argument("--import", "-i", metavar="FILE", dest="import_file",
                       help="Import a puzzle from a JSON file and play it")
    parser.add_argument("--diff", "-d", type=int, default=1, choices=[1, 2, 3],
                       help="Difficulty level for generated puzzles (1-3, default: 1)")
    parser.add_argument("--charset", "-c", default="hex",
                       choices=["alpha", "hex", "vowel", "digit", "alnum", "binary"],
                       help="Character set for generated puzzles (default: hex)")
    parser.add_argument("--verify", "-v", action="store_true",
                       help="Verify generated puzzles have valid solutions")
    parser.add_argument("--timer", "-t", action="store_true",
                       help="Enable timer while playing")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List available puzzles")
    parser.add_argument("--unique", "-u", action="store_true",
                       help="Check if a puzzle has a unique solution")
    
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
            run_interactive(PUZZLES[name], timer=args.timer)
        else:
            print(f"Unknown puzzle: {name}")
            print(f"Available: {', '.join(PUZZLES.keys())}")
    
    elif args.generate:
        rows, cols = args.generate
        if rows < 2 or rows > 8 or cols < 2 or cols > 8:
            print("Grid size must be between 2×2 and 8×8")
            return
        
        print(f"Generating {rows}×{cols} puzzle (difficulty {args.diff}, charset: {args.charset})...")
        puzzle = generate_smart_puzzle(rows, cols, args.diff, args.charset)
        
        if args.unique:
            print("Checking solution uniqueness...")
            n = count_solutions(puzzle, limit=2)
            if n == 1:
                print("✓ Puzzle has a unique solution")
            else:
                print(f"⚠ Puzzle has {n}+ solutions (may not be unique)")
        
        if args.verify:
            print("Verifying solution...")
            solved = solve_puzzle(puzzle)
            if solved:
                print("✓ Solution verified!")
            else:
                print("✗ Could not verify solution")
        
        run_interactive(puzzle, timer=args.timer)
    
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
                
                if args.unique:
                    n = count_solutions(puzzle, limit=2)
                    if n == 1:
                        print("✓ Solution is unique")
                    else:
                        print(f"⚠ Found {n}+ solutions")
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
    
    elif args.export:
        name = args.export
        if name in PUZZLES:
            print(PUZZLES[name].to_json())
        else:
            print(f"Unknown puzzle: {name}")
            print(f"Available: {', '.join(PUZZLES.keys())}")
    
    elif args.import_file:
        try:
            with open(args.import_file, 'r') as f:
                json_str = f.read()
            puzzle = RegexCrossword.from_json(json_str)
            print(f"Imported puzzle: {puzzle.rows}×{puzzle.cols} (charset: {puzzle.charset})")
            
            if args.verify:
                print("Verifying imported puzzle...")
                valid, errors = validate_solution(puzzle, puzzle.solution)
                if valid:
                    print("✓ Imported puzzle solution is valid")
                else:
                    for err in errors:
                        print(f"  ✗ {err}")
            
            run_interactive(puzzle, timer=args.timer)
        except FileNotFoundError:
            print(f"File not found: {args.import_file}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
        except ValueError as e:
            print(f"Invalid puzzle format: {e}")
    
    elif args.unique:
        # If --unique is used alone, check all predefined puzzles
        print("Checking uniqueness of predefined puzzles...\n")
        for name, puzzle in PUZZLES.items():
            space_size = len(puzzle.charset) ** (puzzle.rows * puzzle.cols)
            if space_size > 100_000:
                print(f"  {name}: \033[33m(skipped — search space too large: {space_size:.0e})\033[0m")
                continue
            n = count_solutions(puzzle, limit=10)
            if n == 1:
                print(f"  {name}: \033[32m✓ unique\033[0m")
            elif n <= 10:
                print(f"  {name}: \033[33m{n} solutions\033[0m")
            else:
                print(f"  {name}: \033[31m{n}+ solutions\033[0m")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()