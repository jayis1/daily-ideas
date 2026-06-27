#!/usr/bin/env python3
"""
Terminal Crossword Puzzle — Generate and play interactive crossword puzzles in the terminal.

Features:
  - Procedural crossword generation from a word bank
  - Interactive TUI gameplay with cursor navigation
  - Static print mode for paper-style output
  - Difficulty levels (easy/medium/hard)
  - Save/load puzzle state to JSON files
  - Progress tracking (% complete)
  - Elapsed timer during gameplay
  - Hint system (reveal letter, reveal word)
  - Check puzzle for errors
  - Puzzle export to plain text
"""

import json
import random
import sys
import os
import time
import copy
from collections import defaultdict
from datetime import datetime

__version__ = "1.1.0"

# ─── Word Bank ────────────────────────────────────────────────────────────────

WORD_BANK = [
    ("ALGORITHM", "A step-by-step procedure for solving a problem"),
    ("PYTHON", "A popular programming language named after a comedy troupe"),
    ("BINARY", "A number system with only two digits"),
    ("CACHE", "Fast memory storage for frequently accessed data"),
    ("DEBUG", "The process of finding and removing errors in code"),
    ("ENCRYPT", "To convert data into a secret code"),
    ("FIBONACCI", "Sequence where each number is the sum of the two before it"),
    ("GATEWAY", "A network node that serves as an entrance to another network"),
    ("HASH", "A function that maps data to a fixed-size value"),
    ("ITERATE", "To repeat a process or set of instructions"),
    ("JAVA", "An island and a programming language"),
    ("KERNEL", "The core component of an operating system"),
    ("LAMBDA", "An anonymous function in many programming languages"),
    ("MATRIX", "A rectangular array of numbers or symbols"),
    ("NODE", "A connection point in a network or data structure"),
    ("OBJECT", "An instance of a class in OOP"),
    ("PIXEL", "The smallest addressable element of a screen"),
    ("QUERY", "A request for data or information from a database"),
    ("RECURSION", "A function that calls itself to solve smaller subproblems"),
    ("STACK", "A LIFO data structure"),
    ("TOKEN", "A small piece of data used for authentication"),
    ("URL", "The address of a resource on the internet"),
    ("VARIABLE", "A named storage location in programming"),
    ("WIDGET", "A small UI component in a graphical interface"),
    ("XOR", "A logical operation that outputs true when inputs differ"),
    ("YIELD", "A keyword that produces a value from a generator"),
    ("BOOLEAN", "A data type with only true or false values"),
    ("COMPILE", "To translate source code into machine code"),
    ("DOCKER", "A platform for containerizing applications"),
    ("ECHO", "A command that repeats input as output"),
    ("FORK", "To create a copy of a process or repository"),
    ("GIT", "A distributed version control system"),
    ("HEAP", "A specialized tree-based data structure"),
    ("INDEX", "A data structure that speeds up data retrieval"),
    ("JSON", "A lightweight data interchange format"),
    ("LOOP", "A sequence of instructions that repeats"),
    ("MODULE", "A self-contained unit of code in Python"),
    ("NEURAL", "Relating to networks inspired by the brain"),
    ("OUTPUT", "The result produced by a program or function"),
    ("PARSE", "To analyze a string according to grammatical rules"),
    ("QUEUE", "A FIFO data structure"),
    ("REGEX", "A pattern-matching language for text"),
    ("SYNTAX", "The set of rules defining valid statements in a language"),
    ("TUPLE", "An immutable sequence type in Python"),
    ("UNIT", "A small test that verifies a single piece of functionality"),
    ("VOID", "A return type indicating no value is returned"),
    ("WHILE", "A keyword for creating a loop with a condition"),
    ("ARRAY", "An ordered collection of elements"),
    ("BYTE", "A unit of digital information equal to eight bits"),
    ("CLASS", "A blueprint for creating objects"),
    ("DEQUE", "A double-ended queue data structure"),
    ("EXCEPT", "A keyword for handling errors in Python"),
    ("FLOAT", "A number with a decimal point"),
    ("GRAPH", "A data structure of nodes and edges"),
    ("INPUT", "Data received by a program"),
    ("LINUX", "An open-source operating system kernel"),
    ("PROXY", "An intermediary server that forwards requests"),
    ("ROUTE", "A path or course for network traffic"),
    ("SHELL", "A command-line interface to the operating system"),
    ("THREAD", "A lightweight unit of process execution"),
    ("CURSOR", "A pointer to a position in a database result set"),
    ("DEPTH", "A measure of nesting level in data structures"),
    ("MERGE", "To combine two sorted sequences into one"),
    ("SCOPE", "The region where a variable is accessible"),
    ("TURING", "Last name of the father of theoretical CS"),
    ("LOGIC", "The study of valid reasoning and inference"),
    ("PATCH", "A piece of software that fixes a bug"),
    ("SERIAL", "Sequential, one after another"),
    ("ABSTRACT", "A concept or idea not associated with any specific instance"),
    ("COMPUTE", "To calculate or determine by mathematical methods"),
    ("DYNAMIC", "Changing or evolving during execution"),
    ("FRAGMENT", "A small part broken off from a larger whole"),
    ("OVERFLOW", "When a value exceeds its allocated storage capacity"),
    ("RUNTIME", "The period when a program is executing"),
    ("VOLTAGE", "Electric potential difference measured in volts"),
    ("WIRELESS", "Communication without physical connections"),
]

# ─── Difficulty Presets ───────────────────────────────────────────────────────

DIFFICULTY_PRESETS = {
    "easy": {"max_words": 8, "min_word_len": 3, "grid_width": 18, "grid_height": 12},
    "medium": {"max_words": 12, "min_word_len": 4, "grid_width": 20, "grid_height": 14},
    "hard": {"max_words": 18, "min_word_len": 5, "grid_width": 24, "grid_height": 16},
}

# ─── Colors ───────────────────────────────────────────────────────────────────

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_WHITE = "\033[47m"
    BG_BLACK = "\033[40m"
    BG_GRAY = "\033[48;5;240m"
    BG_DARK = "\033[48;5;236m"
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_CYAN = "\033[46m"
    BG_MAGENTA = "\033[45m"
    BG_RED = "\033[41m"
    BLACK = "\033[30m"


class _NoColor:
    """No-op color replacement for terminals that don't support color."""
    RESET = ""
    BOLD = ""
    DIM = ""
    UNDERLINE = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""
    CYAN = ""
    WHITE = ""
    BG_WHITE = ""
    BG_BLACK = ""
    BG_GRAY = ""
    BG_DARK = ""
    BG_BLUE = ""
    BG_GREEN = ""
    BG_YELLOW = ""
    BG_CYAN = ""
    BG_MAGENTA = ""
    BG_RED = ""
    BLACK = ""


def supports_color():
    """Check if the terminal supports color output."""
    if not hasattr(sys.stdout, 'isatty'):
        return False
    if not sys.stdout.isatty():
        return False
    if os.environ.get('NO_COLOR') is not None:
        return False
    if os.environ.get('TERM') == 'dumb':
        return False
    return True


# ─── Crossword Generator ────────────────────────────────────────────────────

class CrosswordGenerator:
    """Generates crossword puzzles from a word bank."""

    def __init__(self, width=20, height=14):
        self.width = width
        self.height = height
        self.grid = [[' ' for _ in range(width)] for _ in range(height)]
        self.placed_words = []  # (word, row, col, direction) where direction is 'A' or 'D'

    def can_place(self, word, row, col, direction):
        """Check if a word can be placed at the given position.

        Validates:
          - Word fits within grid bounds
          - No conflicting letters at occupied cells
          - No unintended adjacent words formed
          - At least one intersection with existing words (except first word)
          - No word extensions (cells before/after must be empty)
        """
        dr, dc = (0, 1) if direction == 'A' else (1, 0)
        length = len(word)

        # Check bounds
        end_r = row + dr * (length - 1)
        end_c = col + dc * (length - 1)
        if end_r >= self.height or end_c >= self.width:
            return False
        if row < 0 or col < 0:
            return False

        # Check cell before the word start — must be empty to avoid extending another word
        before_r = row - dr
        before_c = col - dc
        if 0 <= before_r < self.height and 0 <= before_c < self.width:
            if self.grid[before_r][before_c] != ' ':
                return False

        # Check cell after the word end — must be empty to avoid extending another word
        after_r = row + dr * length
        after_c = col + dc * length
        if 0 <= after_r < self.height and 0 <= after_c < self.width:
            if self.grid[after_r][after_c] != ' ':
                return False

        # Check each cell along the word's path
        has_intersection = False
        for i in range(length):
            r = row + dr * i
            c = col + dc * i
            cell = self.grid[r][c]

            if cell != ' ':
                if cell != word[i]:
                    return False  # Letter conflict
                else:
                    has_intersection = True
            else:
                # New letter being placed — check perpendicular neighbors
                # to ensure we don't create unintended parallel words
                if direction == 'A':
                    # For across words, check vertical neighbors
                    above = 0
                    rr = r - 1
                    while rr >= 0 and self.grid[rr][c] != ' ':
                        above += 1
                        rr -= 1
                    below = 0
                    rr = r + 1
                    while rr < self.height and self.grid[rr][c] != ' ':
                        below += 1
                        rr += 1
                    if above > 0 or below > 0:
                        return False  # Would create an unintended vertical word
                else:
                    # For down words, check horizontal neighbors
                    left = 0
                    cc = c - 1
                    while cc >= 0 and self.grid[r][cc] != ' ':
                        left += 1
                        cc -= 1
                    right = 0
                    cc = c + 1
                    while cc < self.width and self.grid[r][cc] != ' ':
                        right += 1
                        cc += 1
                    if left > 0 or right > 0:
                        return False  # Would create an unintended horizontal word

        # First word doesn't need an intersection
        if len(self.placed_words) == 0:
            return True

        # All subsequent words must intersect at least one existing word
        return has_intersection

    def place_word(self, word, row, col, direction):
        """Place a word on the grid."""
        dr, dc = (0, 1) if direction == 'A' else (1, 0)
        for i in range(len(word)):
            r = row + dr * i
            c = col + dc * i
            self.grid[r][c] = word[i]
        self.placed_words.append((word, row, col, direction))

    def generate(self, max_words=15, seed=None, min_word_len=3):
        """Generate a crossword puzzle.

        Args:
            max_words: Maximum number of words to place.
            seed: Random seed for reproducibility.
            min_word_len: Minimum word length to include.

        Returns:
            self (for method chaining)
        """
        if seed is not None:
            random.seed(seed)

        # Deduplicate and filter by minimum length
        seen_words = set()
        unique_words = []
        for word, clue in WORD_BANK:
            if word not in seen_words and len(word) >= min_word_len:
                seen_words.add(word)
                unique_words.append((word, clue))

        words = list(unique_words)
        random.shuffle(words)
        # Prefer longer words first for better grid filling
        words.sort(key=lambda w: len(w[0]), reverse=True)

        # Place first word in the center (pick the first word that fits)
        if not words:
            return self

        first_word, first_clue = None, None
        for w, c in words:
            if len(w) <= self.width:
                first_word, first_clue = w, c
                break

        if first_word is None:
            # No words fit in the grid
            return self

        start_col = (self.width - len(first_word)) // 2
        start_row = self.height // 2
        self.place_word(first_word, start_row, start_col, 'A')

        # Try to place remaining words
        for word, clue in words[1:]:
            if len(self.placed_words) >= max_words:
                break

            best_placements = []

            for pw, pr, pc, pd in self.placed_words:
                for i in range(len(word)):
                    for j in range(len(pw)):
                        if word[i] == pw[j]:
                            # Try placing perpendicular to existing word
                            if pd == 'A':
                                # Existing word is across, try placing down
                                nr = pr - i
                                nc = pc + j
                                if self.can_place(word, nr, nc, 'D'):
                                    score = self._score_placement(word, nr, nc, 'D')
                                    best_placements.append((score, nr, nc, 'D'))
                            else:
                                # Existing word is down, try placing across
                                nr = pr + j
                                nc = pc - i
                                if self.can_place(word, nr, nc, 'A'):
                                    score = self._score_placement(word, nr, nc, 'A')
                                    best_placements.append((score, nr, nc, 'A'))

            if best_placements:
                best_placements.sort(reverse=True)
                # Pick from top candidates for variety
                top_n = min(3, len(best_placements))
                choice = random.randint(0, top_n - 1)
                _, br, bc, bd = best_placements[choice]
                self.place_word(word, br, bc, bd)

        return self

    def _score_placement(self, word, row, col, direction):
        """Score a placement position (higher is better).

        Prefers placements near the center of the grid and with more
        intersections with existing words.
        """
        dr, dc = (0, 1) if direction == 'A' else (1, 0)
        score = 0
        for i in range(len(word)):
            r = row + dr * i
            c = col + dc * i
            if self.grid[r][c] == word[i]:
                score += 10  # Intersection bonus
        # Prefer centered placements
        center_r = self.height / 2
        center_c = self.width / 2
        mid_r = row + dr * len(word) / 2
        mid_c = col + dc * len(word) / 2
        dist = abs(mid_r - center_r) + abs(mid_c - center_c)
        score -= dist
        return score

    def get_clues(self):
        """Get numbered clues for across and down.

        Returns:
            Tuple of (across_clues, down_clues, numbered_map)
            where each clue list contains (number, word, clue_text)
            and numbered_map maps (row, col) -> number.
        """
        across = []
        down = []

        for word, row, col, direction in self.placed_words:
            clue_text = ""
            for w, c in WORD_BANK:
                if w == word:
                    clue_text = c
                    break
            if direction == 'A':
                across.append((row, col, word, clue_text))
            else:
                down.append((row, col, word, clue_text))

        across.sort(key=lambda x: (x[0], x[1]))
        down.sort(key=lambda x: (x[0], x[1]))

        # Assign numbers based on position scan order (top-left to bottom-right)
        number = 1
        numbered = {}
        all_starts = sorted(set(
            [(r, c) for _, r, c, _ in self.placed_words]
        ), key=lambda x: (x[0], x[1]))

        for pos in all_starts:
            numbered[pos] = number
            number += 1

        across_numbered = []
        for r, c, w, cl in across:
            across_numbered.append((numbered[(r, c)], w, cl))

        down_numbered = []
        for r, c, w, cl in down:
            down_numbered.append((numbered[(r, c)], w, cl))

        return across_numbered, down_numbered, numbered

    def trim_grid(self):
        """Trim the grid to the minimum bounding box of placed words, with padding."""
        if not self.placed_words:
            return self

        min_r = min(r for _, r, c, _ in self.placed_words)
        max_r = max(r + (len(w) - 1 if d == 'D' else 0) for w, r, c, d in self.placed_words)
        min_c = min(c for _, r, c, _ in self.placed_words)
        max_c = max(c + (len(w) - 1 if d == 'A' else 0) for w, r, c, d in self.placed_words)

        # Add 1-cell padding
        min_r = max(0, min_r - 1)
        min_c = max(0, min_c - 1)
        max_r = min(self.height - 1, max_r + 1)
        max_c = min(self.width - 1, max_c + 1)

        new_grid = []
        for r in range(min_r, max_r + 1):
            row = []
            for c in range(min_c, max_c + 1):
                row.append(self.grid[r][c])
            new_grid.append(row)

        # Adjust placements
        new_placed = []
        for w, r, c, d in self.placed_words:
            new_placed.append((w, r - min_r, c - min_c, d))

        self.grid = new_grid
        self.height = max_r - min_r + 1
        self.width = max_c - min_c + 1
        self.placed_words = new_placed
        return self

    def to_dict(self):
        """Serialize the generator state to a dictionary for save/load."""
        return {
            "width": self.width,
            "height": self.height,
            "grid": self.grid,
            "placed_words": self.placed_words,
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruct a generator from a saved dictionary."""
        gen = cls(data["width"], data["height"])
        gen.grid = data["grid"]
        gen.placed_words = [tuple(pw) for pw in data["placed_words"]]
        return gen

    def export_text(self, show_answers=False):
        """Export the puzzle as a plain-text string (no ANSI codes).

        Args:
            show_answers: If True, fill in the solution letters.

        Returns:
            A string containing the full puzzle in plain text.
        """
        across_clues, down_clues, numbered = self.get_clues()
        number_map = {}
        for (r, c), num in numbered.items():
            number_map[(r, c)] = num

        lines = []
        lines.append("TERMINAL CROSSWORD PUZZLE")
        lines.append("=" * 40)
        lines.append("")

        # Grid
        cell_w = 3
        top = "   " + "+" + "---+" * self.width
        mid = "   " + "+" + "---+" * self.width
        bot = "   " + "+" + "---+" * self.width

        lines.append(top)
        for r in range(self.height):
            num_row = f"{r:2d} |"
            letter_row = "   |"
            for c in range(self.width):
                cell = self.grid[r][c]
                if cell == ' ':
                    num_row += "   |"
                    letter_row += "   |"
                else:
                    n = number_map.get((r, c), '')
                    if n:
                        num_row += f"{n:<3d}|"
                    else:
                        num_row += "   |"
                    if show_answers:
                        letter_row += f" {cell} |"
                    else:
                        letter_row += "   |"
            lines.append(num_row)
            lines.append(letter_row)
            if r < self.height - 1:
                lines.append(mid)
        lines.append(bot)

        # Clues
        lines.append("")
        lines.append("ACROSS")
        lines.append("-" * 40)
        for num, word, clue in across_clues:
            lines.append(f"  {num:2d}. {clue} ({len(word)})")

        lines.append("")
        lines.append("DOWN")
        lines.append("-" * 40)
        for num, word, clue in down_clues:
            lines.append(f"  {num:2d}. {clue} ({len(word)})")

        if show_answers:
            lines.append("")
            lines.append("ANSWERS")
            lines.append("-" * 40)
            for num, word, clue in across_clues:
                lines.append(f"  {num:2d}A: {word}")
            for num, word, clue in down_clues:
                lines.append(f"  {num:2d}D: {word}")

        return "\n".join(lines)


# ─── Crossword Game ──────────────────────────────────────────────────────────

class CrosswordGame:
    """Interactive terminal crossword puzzle game."""

    def __init__(self, generator):
        self.gen = generator
        self.player_grid = [[' ' for _ in range(generator.width)] for _ in range(generator.height)]
        self.cursor_r = 0
        self.cursor_c = 0
        self.direction = 'A'  # 'A' = across, 'D' = down
        self.solved = False
        self.message = ""
        self.message_timer = 0
        self.revealed = set()
        self.checked_cells = set()
        self.wrong_cells = set()
        self.start_time = time.time()
        self.hints_used = 0
        self.total_cells = 0
        self.filled_count = 0

        # Initialize player grid: mark cells that are part of the puzzle
        for r in range(generator.height):
            for c in range(generator.width):
                if generator.grid[r][c] != ' ':
                    self.player_grid[r][c] = '_'
                    self.total_cells += 1
                else:
                    self.player_grid[r][c] = ' '

        # Set cursor to first puzzle cell
        for r in range(generator.height):
            for c in range(generator.width):
                if generator.grid[r][c] != ' ':
                    self.cursor_r = r
                    self.cursor_c = c
                    break
            else:
                continue
            break

    def elapsed_time(self):
        """Return elapsed seconds since game start."""
        return time.time() - self.start_time

    def format_time(self, seconds):
        """Format seconds into MM:SS display."""
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"

    def progress_pct(self):
        """Calculate percentage of cells filled (not necessarily correctly)."""
        filled = sum(
            1 for r in range(self.gen.height)
            for c in range(self.gen.width)
            if self.gen.grid[r][c] != ' ' and self.player_grid[r][c] != '_'
        )
        if self.total_cells == 0:
            return 0
        return int(100 * filled / self.total_cells)

    def get_current_word_info(self):
        """Get the clue number and text for the current word at cursor.

        Returns:
            Tuple of (number, clue_text) or None if not on a word start.
        """
        across_clues, down_clues, numbered = self.gen.get_clues()
        # Find the word the cursor is currently on
        cells = self.get_current_word_cells()
        if not cells or len(cells) < 2:
            return None
        start_r, start_c = cells[0]
        num = numbered.get((start_r, start_c))
        if num is None:
            return None
        # Find the matching clue
        if self.direction == 'A':
            for n, w, cl in across_clues:
                if n == num:
                    return (num, cl)
        else:
            for n, w, cl in down_clues:
                if n == num:
                    return (num, cl)
        return None

    def get_current_word_cells(self):
        """Get all cells in the current word at cursor position."""
        dr, dc = (0, 1) if self.direction == 'A' else (1, 0)
        r, c = self.cursor_r, self.cursor_c

        # Find start of word
        while r - dr >= 0 and c - dc >= 0 and r - dr < self.gen.height and c - dc < self.gen.width:
            if self.gen.grid[r - dr][c - dc] != ' ':
                r -= dr
                c -= dc
            else:
                break

        # Collect all cells in word
        cells = []
        while 0 <= r < self.gen.height and 0 <= c < self.gen.width:
            if self.gen.grid[r][c] != ' ':
                cells.append((r, c))
                r += dr
                c += dc
            else:
                break

        if len(cells) <= 1:
            # Switch direction and try again
            self.direction = 'D' if self.direction == 'A' else 'A'
            return self.get_current_word_cells()

        return cells

    def type_letter(self, letter):
        """Type a letter at the current cursor position and advance."""
        if 0 <= self.cursor_r < self.gen.height and 0 <= self.cursor_c < self.gen.width:
            if self.gen.grid[self.cursor_r][self.cursor_c] != ' ':
                self.player_grid[self.cursor_r][self.cursor_c] = letter.upper()
                # Clear any check marks for this cell
                self.checked_cells.discard((self.cursor_r, self.cursor_c))
                self.wrong_cells.discard((self.cursor_r, self.cursor_c))
                # Advance cursor
                self.advance_cursor()

    def advance_cursor(self):
        """Move cursor to next empty cell in current direction."""
        dr, dc = (0, 1) if self.direction == 'A' else (1, 0)
        r = self.cursor_r + dr
        c = self.cursor_c + dc
        while 0 <= r < self.gen.height and 0 <= c < self.gen.width:
            if self.gen.grid[r][c] != ' ':
                self.cursor_r = r
                self.cursor_c = c
                return
            r += dr
            c += dc

    def backspace(self):
        """Delete letter and move cursor back."""
        if self.gen.grid[self.cursor_r][self.cursor_c] != ' ':
            if self.player_grid[self.cursor_r][self.cursor_c] == '_':
                # Move back
                self.retreat_cursor()
            else:
                self.player_grid[self.cursor_r][self.cursor_c] = '_'
                self.checked_cells.discard((self.cursor_r, self.cursor_c))
                self.wrong_cells.discard((self.cursor_r, self.cursor_c))

    def retreat_cursor(self):
        """Move cursor backward in current direction."""
        dr, dc = (0, 1) if self.direction == 'A' else (1, 0)
        r = self.cursor_r - dr
        c = self.cursor_c - dc
        while 0 <= r < self.gen.height and 0 <= c < self.gen.width:
            if self.gen.grid[r][c] != ' ':
                self.cursor_r = r
                self.cursor_c = c
                return
            r -= dr
            c -= dc

    def move_cursor(self, dr, dc):
        """Move cursor in an arbitrary direction, skipping non-puzzle cells."""
        nr = self.cursor_r + dr
        nc = self.cursor_c + dc
        while 0 <= nr < self.gen.height and 0 <= nc < self.gen.width:
            if self.gen.grid[nr][nc] != ' ':
                self.cursor_r = nr
                self.cursor_c = nc
                return
            nr += dr
            nc += dc

    def toggle_direction(self):
        """Toggle between across and down."""
        self.direction = 'D' if self.direction == 'A' else 'A'

    def check_puzzle(self):
        """Check if the puzzle is correctly filled.

        Marks correct cells green and incorrect cells red.
        Sets self.solved to True if puzzle is complete and correct.
        """
        all_correct = True
        any_filled = False
        self.checked_cells = set()
        self.wrong_cells = set()

        for r in range(self.gen.height):
            for c in range(self.gen.width):
                if self.gen.grid[r][c] != ' ':
                    if self.player_grid[r][c] != '_':
                        any_filled = True
                        if self.player_grid[r][c] == self.gen.grid[r][c]:
                            self.checked_cells.add((r, c))
                        else:
                            self.wrong_cells.add((r, c))
                            all_correct = False
                    else:
                        all_correct = False

        if not any_filled:
            self.message = "Fill in some letters first!"
            self.message_timer = 60
        elif all_correct and self._all_filled():
            self.solved = True
            self.message = "CONGRATULATIONS! Puzzle solved!"
            self.message_timer = 999
        elif all_correct:
            self.message = "All filled letters are correct! Keep going!"
            self.message_timer = 60
        else:
            wrong_count = len(self.wrong_cells)
            self.message = f"{wrong_count} incorrect letter(s) found"
            self.message_timer = 60

    def _all_filled(self):
        """Check if all puzzle cells are filled."""
        for r in range(self.gen.height):
            for c in range(self.gen.width):
                if self.gen.grid[r][c] != ' ':
                    if self.player_grid[r][c] == '_':
                        return False
        return True

    def reveal_letter(self):
        """Reveal the letter at the current cursor position."""
        if 0 <= self.cursor_r < self.gen.height and 0 <= self.cursor_c < self.gen.width:
            if self.gen.grid[self.cursor_r][self.cursor_c] != ' ':
                self.player_grid[self.cursor_r][self.cursor_c] = self.gen.grid[self.cursor_r][self.cursor_c]
                self.revealed.add((self.cursor_r, self.cursor_c))
                self.hints_used += 1
                self.checked_cells.discard((self.cursor_r, self.cursor_c))
                self.wrong_cells.discard((self.cursor_r, self.cursor_c))
                self.advance_cursor()

    def reveal_word(self):
        """Reveal the current word."""
        cells = self.get_current_word_cells()
        for r, c in cells:
            self.player_grid[r][c] = self.gen.grid[r][c]
            self.revealed.add((r, c))
            self.hints_used += 1
            self.checked_cells.discard((r, c))
            self.wrong_cells.discard((r, c))

    def to_dict(self):
        """Serialize game state for save/load."""
        return {
            "player_grid": self.player_grid,
            "cursor_r": self.cursor_r,
            "cursor_c": self.cursor_c,
            "direction": self.direction,
            "revealed": [list(r) for r in sorted(self.revealed)],
            "checked_cells": [list(c) for c in sorted(self.checked_cells)],
            "wrong_cells": [list(w) for w in sorted(self.wrong_cells)],
            "hints_used": self.hints_used,
            "elapsed_seconds": self.elapsed_time(),
        }

    @classmethod
    def from_dict(cls, generator, data):
        """Reconstruct a game from saved state and a generator."""
        game = cls.__new__(cls)
        game.gen = generator
        game.player_grid = data["player_grid"]
        game.cursor_r = data["cursor_r"]
        game.cursor_c = data["cursor_c"]
        game.direction = data["direction"]
        game.revealed = set(tuple(r) for r in data["revealed"])
        game.checked_cells = set(tuple(c) for c in data["checked_cells"])
        game.wrong_cells = set(tuple(w) for w in data["wrong_cells"])
        game.hints_used = data["hints_used"]
        game.start_time = time.time() - data.get("elapsed_seconds", 0)
        game.solved = False
        game.message = "Game restored from save."
        game.message_timer = 60
        game.total_cells = sum(
            1 for r in range(generator.height)
            for c in range(generator.width)
            if generator.grid[r][c] != ' '
        )
        game.filled_count = 0
        return game

    def render(self, use_color=True):
        """Render the crossword puzzle for the terminal.

        Args:
            use_color: If False, render without ANSI color codes.

        Returns:
            A string containing the rendered puzzle.
        """
        across_clues, down_clues, numbered = self.gen.get_clues()

        # Color/no-color helpers
        if use_color:
            C = Colors
        else:
            C = _NoColor()

        lines = []
        lines.append(f"\n{C.BOLD}{C.CYAN}{'=' * 42}{C.RESET}")
        lines.append(f"{C.BOLD}{C.CYAN}  TERMINAL CROSSWORD PUZZLE{C.RESET}")
        lines.append(f"{C.BOLD}{C.CYAN}{'=' * 42}{C.RESET}\n")

        # Direction indicator and stats
        dir_text = "ACROSS ->" if self.direction == 'A' else "DOWN v"
        pct = self.progress_pct()
        elapsed = self.format_time(self.elapsed_time())
        lines.append(f"  Direction: {C.BOLD}{C.YELLOW}{dir_text}{C.RESET}  |  "
                      f"Words: {len(self.gen.placed_words)}  |  "
                      f"Progress: {pct}%  |  "
                      f"Hints: {self.hints_used}  |  "
                      f"Time: {elapsed}")
        lines.append("")

        # Current clue display
        word_info = self.get_current_word_info()
        if word_info:
            num, clue = word_info
            direction_label = "Across" if self.direction == 'A' else "Down"
            lines.append(f"  {C.BOLD}{C.GREEN}>{C.RESET} {num}{direction_label[0]}: {clue}")
            lines.append("")

        # Build grid display
        number_map = {}
        for (r, c), num in numbered.items():
            number_map[(r, c)] = num

        for r in range(self.gen.height):
            row_str = ""
            for c in range(self.gen.width):
                cell_char = self.gen.grid[r][c]
                player_char = self.player_grid[r][c]

                if cell_char == ' ':
                    row_str += f"{C.BG_GRAY}  {C.RESET}"
                else:
                    is_cursor = (r == self.cursor_r and c == self.cursor_c)
                    is_in_word = False
                    word_cells = self.get_current_word_cells()
                    is_in_word = (r, c) in word_cells

                    is_checked = (r, c) in self.checked_cells
                    is_wrong = (r, c) in self.wrong_cells
                    is_revealed = (r, c) in self.revealed

                    # Number in top-left if present
                    num_str = ""
                    if (r, c) in number_map:
                        num_str = f"{C.DIM}{number_map[(r,c)]}{C.RESET}"

                    if is_cursor:
                        bg = C.BG_CYAN + C.BLACK
                    elif is_wrong:
                        bg = C.BG_RED + C.WHITE
                    elif is_checked:
                        bg = C.BG_GREEN + C.BLACK
                    elif is_revealed:
                        bg = C.BG_YELLOW + C.BLACK
                    elif is_in_word:
                        bg = C.BG_BLUE + C.WHITE
                    else:
                        bg = C.BG_WHITE + C.BLACK

                    display_char = player_char if player_char != '_' else ' '
                    if num_str:
                        row_str += f"{bg}{num_str}{display_char}{C.RESET}"
                    else:
                        row_str += f"{bg} {display_char}{C.RESET}"

            lines.append(row_str)

        # Message
        if self.message_timer > 0:
            if self.solved:
                lines.append(f"\n  {C.BOLD}{C.GREEN}{self.message}{C.RESET}")
            else:
                lines.append(f"\n  {C.BOLD}{self.message}{C.RESET}")
            self.message_timer -= 1
        else:
            lines.append("")

        # Helper: check if a word is fully and correctly filled
        def is_word_complete(word):
            for pw, pr, pc, pd in self.gen.placed_words:
                if pw == word:
                    dr, dc = (0, 1) if pd == 'A' else (1, 0)
                    for idx in range(len(pw)):
                        cell_r = pr + dr * idx
                        cell_c = pc + dc * idx
                        if self.player_grid[cell_r][cell_c] != pw[idx]:
                            return False
                    return True
            return False

        # Clues
        lines.append(f"\n{C.BOLD}{C.CYAN}-- ACROSS --{C.RESET}")
        for num, word, clue in across_clues:
            word_done = is_word_complete(word)
            marker = f"{C.GREEN}V{C.RESET}" if word_done else " "
            clue_display = f"{C.DIM}{clue}{C.RESET}" if word_done else clue
            lines.append(f"  {marker} {C.BOLD}{num:2d}.{C.RESET} {clue_display} ({len(word)})")

        lines.append(f"\n{C.BOLD}{C.CYAN}-- DOWN --{C.RESET}")
        for num, word, clue in down_clues:
            word_done = is_word_complete(word)
            marker = f"{C.GREEN}V{C.RESET}" if word_done else " "
            clue_display = f"{C.DIM}{clue}{C.RESET}" if word_done else clue
            lines.append(f"  {marker} {C.BOLD}{num:2d}.{C.RESET} {clue_display} ({len(word)})")

        # Controls
        lines.append(f"\n{C.BOLD}{C.CYAN}-- CONTROLS --{C.RESET}")
        lines.append(f"  {C.YELLOW}Arrows{C.RESET}      Move cursor     {C.YELLOW}Tab{C.RESET}        Toggle across/down")
        lines.append(f"  {C.YELLOW}Letters{C.RESET}     Type answer     {C.YELLOW}Backspace{C.RESET}  Delete letter")
        lines.append(f"  {C.YELLOW}C{C.RESET}          Check puzzle   {C.YELLOW}R{C.RESET}          Reveal letter")
        lines.append(f"  {C.YELLOW}W{C.RESET}          Reveal word     {C.YELLOW}S{C.RESET}          Save game")
        lines.append(f"  {C.YELLOW}Q{C.RESET}          Quit            {C.YELLOW}N{C.RESET}          New puzzle")

        return "\n".join(lines)


# ─── Simplified Terminal Input ───────────────────────────────────────────────

def get_key():
    """Read a single keypress from the terminal.

    Returns a string key identifier like 'UP', 'DOWN', 'TAB', etc.
    Falls back to basic input if termios is unavailable.
    """
    import tty
    import termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # Escape sequence
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
                elif ch3 == 'Z':
                    return 'SHIFT_TAB'
            return 'ESC'
        elif ch == '\t':
            return 'TAB'
        elif ch == '\x7f' or ch == '\x08':
            return 'BACKSPACE'
        elif ch == '\r' or ch == '\n':
            return 'ENTER'
        elif ch == '\x03':  # Ctrl+C
            return 'QUIT'
        elif ch.isalpha():
            return ch.upper()
        elif ch in '0123456789':
            return ch
        return ch
    except Exception:
        return 'QUIT'
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def clear_screen():
    """Clear the terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


# ─── Save / Load ──────────────────────────────────────────────────────────────

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".crossword_saves")


def save_game(generator, game, filename=None):
    """Save a game to a JSON file.

    Args:
        generator: The CrosswordGenerator instance.
        game: The CrosswordGame instance.
        filename: Optional filename; defaults to timestamp-based name.

    Returns:
        The path to the saved file.
    """
    os.makedirs(SAVE_DIR, exist_ok=True)
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crossword_{timestamp}.json"
    filepath = os.path.join(SAVE_DIR, filename)

    data = {
        "version": __version__,
        "generator": generator.to_dict(),
        "game": game.to_dict(),
    }
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    return filepath


def load_game(filepath):
    """Load a game from a JSON file.

    Args:
        filepath: Path to the saved game file.

    Returns:
        Tuple of (generator, game) instances.
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    generator = CrosswordGenerator.from_dict(data["generator"])
    game = CrosswordGame.from_dict(generator, data["game"])
    return generator, game


def list_saves():
    """List all saved games in the save directory.

    Returns:
        List of (filepath, timestamp_string) tuples sorted by newest first.
    """
    if not os.path.exists(SAVE_DIR):
        return []
    saves = []
    for fname in os.listdir(SAVE_DIR):
        if fname.endswith('.json'):
            filepath = os.path.join(SAVE_DIR, fname)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                saves.append((filepath, data.get("version", "?"), fname))
            except (json.JSONDecodeError, IOError):
                continue
    saves.sort(key=lambda x: x[2], reverse=True)
    return saves


# ─── Interactive Play ─────────────────────────────────────────────────────────

def play_interactive(generator, resume_game=None):
    """Play the crossword puzzle interactively.

    Args:
        generator: The CrosswordGenerator instance.
        resume_game: Optional CrosswordGame instance to resume.

    Returns:
        A string: 'new', 'done', or 'quit'.
    """
    if resume_game:
        game = resume_game
    else:
        game = CrosswordGame(generator)

    use_color = supports_color()

    try:
        while not game.solved:
            clear_screen()
            print(game.render(use_color=use_color))
            sys.stdout.flush()

            key = get_key()

            if key == 'QUIT' or key == 'q' or key == 'Q':
                break
            elif key == 'UP':
                game.move_cursor(-1, 0)
            elif key == 'DOWN':
                game.move_cursor(1, 0)
            elif key == 'LEFT':
                game.move_cursor(0, -1)
            elif key == 'RIGHT':
                game.move_cursor(0, 1)
            elif key == 'TAB' or key == 'SHIFT_TAB':
                game.toggle_direction()
            elif key == 'ENTER':
                game.toggle_direction()
            elif key == 'BACKSPACE':
                game.backspace()
            elif key == 'C':
                game.check_puzzle()
            elif key == 'R':
                game.reveal_letter()
            elif key == 'W':
                game.reveal_word()
            elif key == 'N':
                return 'new'
            elif key == 'S':
                filepath = save_game(generator, game)
                game.message = f"Game saved to {filepath}"
                game.message_timer = 60
            elif len(key) == 1 and key.isalpha():
                game.type_letter(key)

        clear_screen()
        print(game.render(use_color=use_color))
        if game.solved:
            elapsed = game.format_time(game.elapsed_time())
            print(f"\n  Puzzle Complete! Time: {elapsed} | Hints used: {game.hints_used}")
        return 'done'

    except KeyboardInterrupt:
        return 'quit'


# ─── Non-interactive (fallback) Mode ──────────────────────────────────────────

def print_puzzle(generator, show_answers=False):
    """Print the crossword puzzle in a static format using a clean box-drawing grid."""
    across_clues, down_clues, numbered = generator.get_clues()
    number_map = {}
    for (r, c), num in numbered.items():
        number_map[(r, c)] = num

    C = Colors

    print(f"\n{C.BOLD}{C.CYAN}{'=' * 42}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  TERMINAL CROSSWORD PUZZLE{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * 42}{C.RESET}\n")

    # Use a 2-line-per-row grid: top line for numbers, bottom line for letters
    top = "   " + "+" + "---+" * (generator.width - 1) + "---+"
    mid = "   " + "+" + "---+" * (generator.width - 1) + "---+"
    bot = "   " + "+" + "---+" * (generator.width - 1) + "---+"

    print(top)
    for r in range(generator.height):
        # Number row
        num_row = f"{r:2d} |"
        for c in range(generator.width):
            cell = generator.grid[r][c]
            if cell == ' ':
                num_row += f"{C.BG_GRAY}   {C.RESET}|"
            else:
                n = number_map.get((r, c), '')
                if n:
                    num_text = f"{n}"
                    num_row += f"{C.BG_DARK}{C.CYAN}{num_text:^3s}{C.RESET}|"
                else:
                    num_row += f"{C.BG_DARK}   {C.RESET}|"
        print(num_row)

        # Letter row
        letter_row = "   |"
        for c in range(generator.width):
            cell = generator.grid[r][c]
            if cell == ' ':
                letter_row += f"{C.BG_GRAY}   {C.RESET}|"
            else:
                if show_answers:
                    letter_row += f"{C.BG_WHITE}{C.BLACK}{C.BOLD} {cell} {C.RESET}|"
                else:
                    letter_row += f"{C.BG_WHITE}   {C.RESET}|"
        print(letter_row)

        if r < generator.height - 1:
            print(mid)
    print(bot)

    # Clues
    print(f"\n{C.BOLD}{C.CYAN}-- ACROSS --{C.RESET}")
    for num, word, clue in across_clues:
        print(f"  {C.BOLD}{num:2d}.{C.RESET} {clue} ({len(word)})")

    print(f"\n{C.BOLD}{C.CYAN}-- DOWN --{C.RESET}")
    for num, word, clue in down_clues:
        print(f"  {C.BOLD}{num:2d}.{C.RESET} {clue} ({len(word)})")

    if show_answers:
        print(f"\n{C.BOLD}{C.YELLOW}-- ANSWERS --{C.RESET}")
        for num, word, clue in across_clues:
            print(f"  {num:2d}A: {word}")
        for num, word, clue in down_clues:
            print(f"  {num:2d}D: {word}")


# ─── Puzzle Quality Checker ──────────────────────────────────────────────────

def is_good_puzzle(generator, min_words=6):
    """Check if the generated puzzle has enough words for a good experience.

    Args:
        generator: The CrosswordGenerator instance.
        min_words: Minimum number of placed words required.

    Returns:
        True if the puzzle meets the quality threshold.
    """
    return len(generator.placed_words) >= min_words


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    """Entry point for the terminal crossword puzzle CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Terminal Crossword Puzzle — Generate and play interactive crossword puzzles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                          Play interactively (default)
  %(prog)s --difficulty hard        Play a harder puzzle with more words
  %(prog)s --print                   Print puzzle without playing
  %(prog)s --answers                 Print puzzle with solutions shown
  %(prog)s --seed 42                 Use seed 42 for reproducible puzzles
  %(prog)s --export puzzle.txt       Export puzzle to a text file
  %(prog)s --load ~/.crossword_saves/crossword_20260627.json
                                    Resume a saved game
"""
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible puzzles")
    parser.add_argument("--words", type=int, default=None,
                        help="Maximum number of words (overrides difficulty)")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"],
                        default="medium",
                        help="Difficulty level: easy (8 words), medium (12), hard (18)")
    parser.add_argument("--answers", action="store_true",
                        help="Show answers (non-interactive)")
    parser.add_argument("--print", action="store_true", dest="print_puzzle",
                        help="Print puzzle without playing (non-interactive)")
    parser.add_argument("--interactive", action="store_true",
                        help="Force interactive mode")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Force non-interactive mode")
    parser.add_argument("--export", metavar="FILE", default=None,
                        help="Export puzzle to a plain-text file")
    parser.add_argument("--load", metavar="FILE", default=None,
                        help="Load and resume a saved game")
    args = parser.parse_args()

    # Determine difficulty settings
    preset = DIFFICULTY_PRESETS[args.difficulty]
    max_words = args.words if args.words is not None else preset["max_words"]
    min_word_len = preset["min_word_len"]
    grid_width = preset["grid_width"]
    grid_height = preset["grid_height"]

    # Load saved game if requested
    if args.load:
        try:
            generator, game = load_game(args.load)
            print(f"Loaded saved game from {args.load}")
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading saved game: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Generate a new puzzle
        seed = args.seed if args.seed else random.randint(1, 999999)
        # Try multiple seeds until we get a good puzzle
        for attempt in range(50):
            generator = CrosswordGenerator(grid_width, grid_height)
            generator.generate(max_words=max_words, seed=seed + attempt,
                               min_word_len=min_word_len)
            generator.trim_grid()
            if is_good_puzzle(generator):
                break

        game = None  # Will be created in interactive mode

    print(f"Generated crossword with {len(generator.placed_words)} words "
          f"(seed: {seed + attempt if args.seed or not args.load else 'loaded'}, "
          f"difficulty: {args.difficulty})\n")

    # Export mode
    if args.export:
        text = generator.export_text(show_answers=args.answers)
        try:
            with open(args.export, 'w') as f:
                f.write(text)
            print(f"Puzzle exported to {args.export}")
        except IOError as e:
            print(f"Error exporting puzzle: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Print/answers mode (non-interactive)
    if args.answers or args.print_puzzle:
        print_puzzle(generator, show_answers=args.answers)
        return

    # Interactive mode
    try:
        import tty
        import termios
        interactive = True
    except ImportError:
        interactive = False

    if args.no_interactive:
        interactive = False
    if args.interactive:
        interactive = True

    if interactive and sys.stdin.isatty():
        result = play_interactive(generator, resume_game=game)
        if result == 'new':
            # Regenerate with a new seed
            main()
    else:
        print_puzzle(generator, show_answers=False)
        print(f"\n(Run with --interactive to play, --answers to see solutions)")


if __name__ == "__main__":
    main()