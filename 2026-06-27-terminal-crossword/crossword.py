#!/usr/bin/env python3
"""
Terminal Crossword Puzzle — Generate and play interactive crossword puzzles in the terminal.
"""

import random
import sys
import os
import copy
from collections import defaultdict

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
    ("CACHE", "Temporary storage for quick data access"),
    ("ABSTRACT", "A concept or idea not associated with any specific instance"),
    ("COMPUTE", "To calculate or determine by mathematical methods"),
    ("DYNAMIC", "Changing or evolving during execution"),
    ("FRAGMENT", "A small part broken off from a larger whole"),
    ("OVERFLOW", "When a value exceeds its allocated storage capacity"),
    ("RUNTIME", "The period when a program is executing"),
    ("VOLTAGE", "Electric potential difference measured in volts"),
    ("WIRELESS", "Communication without physical connections"),
]

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


# ─── Crossword Generator ────────────────────────────────────────────────────

class CrosswordGenerator:
    """Generates crossword puzzles from a word bank."""

    def __init__(self, width=20, height=14):
        self.width = width
        self.height = height
        self.grid = [[' ' for _ in range(width)] for _ in range(height)]
        self.placed_words = []  # (word, row, col, direction) where direction is 'A' or 'D'

    def can_place(self, word, row, col, direction):
        """Check if a word can be placed at the given position."""
        dr, dc = (0, 1) if direction == 'A' else (1, 0)
        length = len(word)

        # Check bounds
        end_r = row + dr * (length - 1)
        end_c = col + dc * (length - 1)
        if end_r >= self.height or end_c >= self.width:
            return False
        if row < 0 or col < 0:
            return False

        # Check each cell
        has_intersection = False
        for i in range(length):
            r = row + dr * i
            c = col + dc * i
            cell = self.grid[r][c]

            if cell != ' ':
                if cell != word[i]:
                    return False  # Conflict
                else:
                    has_intersection = True
            else:
                # Check adjacent cells (no parallel adjacency unless intersecting)
                if direction == 'A':
                    # Check above and below
                    if r > 0 and self.grid[r-1][c] != ' ':
                        # Only ok if it's part of a vertical word crossing here
                        pass  # We'll validate intersections separately
                    if r < self.height - 1 and self.grid[r+1][c] != ' ':
                        pass
                else:
                    if c > 0 and self.grid[r][c-1] != ' ':
                        pass
                    if c < self.width - 1 and self.grid[r][c+1] != ' ':
                        pass

        # Check cell before and after word
        before_r = row - dr
        before_c = col - dc
        if 0 <= before_r < self.height and 0 <= before_c < self.width:
            if self.grid[before_r][before_c] != ' ':
                return False

        after_r = row + dr * length
        after_c = col + dc * length
        if 0 <= after_r < self.height and 0 <= after_c < self.width:
            if self.grid[after_r][after_c] != ' ':
                return False

        # For the first word, no intersection needed
        if len(self.placed_words) == 0:
            return True

        # Must intersect at least one existing word
        if not has_intersection:
            return False

        # Validate that adjacent cells don't create invalid words
        for i in range(length):
            r = row + dr * i
            c = col + dc * i
            cell = self.grid[r][c]

            if cell == ' ':
                # New letter being placed — check perpendicular neighbors
                if direction == 'A':
                    # Check if this creates an unintended vertical word
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
                        return False  # Would create partial vertical word
                else:
                    # Check if this creates an unintended horizontal word
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
                        return False

        return True

    def place_word(self, word, row, col, direction):
        """Place a word on the grid."""
        dr, dc = (0, 1) if direction == 'A' else (1, 0)
        for i in range(len(word)):
            r = row + dr * i
            c = col + dc * i
            self.grid[r][c] = word[i]
        self.placed_words.append((word, row, col, direction))

    def generate(self, max_words=15, seed=None):
        """Generate a crossword puzzle."""
        if seed is not None:
            random.seed(seed)

        words = list(set(WORD_BANK))
        random.shuffle(words)
        words.sort(key=lambda w: len(w[0]), reverse=True)

        # Place first word in the center
        if not words:
            return self

        first_word, first_clue = words[0]
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
                            # Try placing perpendicular
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
                _, br, bc, bd = best_placements[0]
                # Add some randomness for variety
                top_n = min(3, len(best_placements))
                choice = random.randint(0, top_n - 1)
                _, br, bc, bd = best_placements[choice]
                self.place_word(word, br, bc, bd)

        return self

    def _score_placement(self, word, row, col, direction):
        """Score a placement position (higher is better)."""
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
        """Get numbered clues for across and down."""
        # Find all word starts and assign numbers
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
        """Trim the grid to the minimum bounding box of placed words."""
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
        self.start_time = None
        self.hints_used = 0

        # Initialize player grid
        for r in range(generator.height):
            for c in range(generator.width):
                if generator.grid[r][c] != ' ':
                    self.player_grid[r][c] = '_'
                else:
                    self.player_grid[r][c] = ' '

        # Set cursor to first cell
        for r in range(generator.height):
            for c in range(generator.width):
                if generator.grid[r][c] != ' ':
                    self.cursor_r = r
                    self.cursor_c = c
                    break
            else:
                continue
            break

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
            # Switch direction
            self.direction = 'D' if self.direction == 'A' else 'A'
            return self.get_current_word_cells()

        return cells

    def type_letter(self, letter):
        """Type a letter at the current cursor position."""
        if 0 <= self.cursor_r < self.gen.height and 0 <= self.cursor_c < self.gen.width:
            if self.gen.grid[self.cursor_r][self.cursor_c] != ' ':
                self.player_grid[self.cursor_r][self.cursor_c] = letter.upper()
                # Clear any check marks
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
        """Move cursor in a direction."""
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
        """Check if the puzzle is correctly filled."""
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
            self.message = "🎉 CONGRATULATIONS! Puzzle solved! 🎉"
            self.message_timer = 999
        elif all_correct:
            self.message = "✓ All filled letters are correct! Keep going!"
            self.message_timer = 60
        else:
            wrong_count = len(self.wrong_cells)
            self.message = f"✗ {wrong_count} incorrect letter(s) found"
            self.message_timer = 60

    def _all_filled(self):
        """Check if all cells are filled."""
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

    def render(self):
        """Render the crossword puzzle for the terminal."""
        across_clues, down_clues, numbered = self.gen.get_clues()

        lines = []
        lines.append(f"\n{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════╗{Colors.RESET}")
        lines.append(f"{Colors.BOLD}{Colors.CYAN}║     📝 TERMINAL CROSSWORD PUZZLE      ║{Colors.RESET}")
        lines.append(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════╝{Colors.RESET}\n")

        # Direction indicator
        dir_text = "ACROSS →" if self.direction == 'A' else "DOWN ↓"
        lines.append(f"  Direction: {Colors.BOLD}{Colors.YELLOW}{dir_text}{Colors.RESET}  |  "
                      f"Words: {len(self.gen.placed_words)}  |  "
                      f"Hints: {self.hints_used}")
        lines.append("")

        # Build grid display using box-drawing characters (2 rows per puzzle row)
        number_map = {}
        for (r, c), num in numbered.items():
            number_map[(r, c)] = num

        # Pre-calculate which cells belong to current word
        word_cells = set()
        try:
            word_cells = set(self.get_current_word_cells())
        except Exception:
            pass

        top = "   " + "┌" + "───┬" * (self.gen.width - 1) + "───┐"
        mid = "   " + "├" + "───┼" * (self.gen.width - 1) + "───┤"
        bot = "   " + "└" + "───┴" * (self.gen.width - 1) + "───┘"

        lines.append(top)
        for r in range(self.gen.height):
            # Number row
            num_row = f"{Colors.DIM}{r:2d}{Colors.RESET} │"
            for c in range(self.gen.width):
                cell_char = self.gen.grid[r][c]
                if cell_char == ' ':
                    num_row += f"{Colors.BG_GRAY}   {Colors.RESET}│"
                else:
                    is_cursor = (r == self.cursor_r and c == self.cursor_c)
                    is_in_word = (r, c) in word_cells
                    is_checked = (r, c) in self.checked_cells
                    is_wrong = (r, c) in self.wrong_cells
                    is_revealed = (r, c) in self.revealed

                    if is_cursor:
                        bg = Colors.BG_CYAN + Colors.BLACK
                    elif is_wrong:
                        bg = Colors.BG_RED + Colors.WHITE
                    elif is_checked:
                        bg = Colors.BG_GREEN + Colors.BLACK
                    elif is_in_word:
                        bg = Colors.BG_BLUE + Colors.WHITE
                    elif is_revealed:
                        bg = Colors.BG_YELLOW + Colors.BLACK
                    else:
                        bg = Colors.BG_WHITE + Colors.BLACK

                    num = number_map.get((r, c), '')
                    if num:
                        num_text = f"{num}"
                        num_row += f"{bg}{Colors.DIM}{num_text:^3s}{Colors.RESET}│"
                    else:
                        num_row += f"{bg}   {Colors.RESET}│"
            lines.append(num_row)

            # Letter row
            letter_row = f"   │"
            for c in range(self.gen.width):
                cell_char = self.gen.grid[r][c]
                player_char = self.player_grid[r][c]
                if cell_char == ' ':
                    letter_row += f"{Colors.BG_GRAY}   {Colors.RESET}│"
                else:
                    is_cursor = (r == self.cursor_r and c == self.cursor_c)
                    is_in_word = (r, c) in word_cells
                    is_checked = (r, c) in self.checked_cells
                    is_wrong = (r, c) in self.wrong_cells
                    is_revealed = (r, c) in self.revealed

                    if is_cursor:
                        bg = Colors.BG_CYAN + Colors.BLACK
                    elif is_wrong:
                        bg = Colors.BG_RED + Colors.WHITE
                    elif is_checked:
                        bg = Colors.BG_GREEN + Colors.BLACK
                    elif is_in_word:
                        bg = Colors.BG_BLUE + Colors.WHITE
                    elif is_revealed:
                        bg = Colors.BG_YELLOW + Colors.BLACK
                    else:
                        bg = Colors.BG_WHITE + Colors.BLACK

                    display_char = player_char if player_char != '_' else ' '
                    letter_row += f"{bg}{Colors.BOLD} {display_char} {Colors.RESET}│"
            lines.append(letter_row)

            if r < self.gen.height - 1:
                lines.append(mid)
        lines.append(bot)

        # Message
        if self.message_timer > 0:
            lines.append(f"\n  {Colors.BOLD}{self.message}{Colors.RESET}")
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
        lines.append(f"\n{Colors.BOLD}{Colors.CYAN}── ACROSS ──────────────────────────────{Colors.RESET}")
        for num, word, clue in across_clues:
            word_done = is_word_complete(word)
            marker = f"{Colors.GREEN}✓{Colors.RESET}" if word_done else " "
            clue_display = f"{Colors.DIM}{clue}{Colors.RESET}" if word_done else clue
            lines.append(f"  {marker} {Colors.BOLD}{num:2d}.{Colors.RESET} {clue_display} ({len(word)})")

        lines.append(f"\n{Colors.BOLD}{Colors.CYAN}── DOWN ────────────────────────────────{Colors.RESET}")
        for num, word, clue in down_clues:
            word_done = is_word_complete(word)
            marker = f"{Colors.GREEN}✓{Colors.RESET}" if word_done else " "
            clue_display = f"{Colors.DIM}{clue}{Colors.RESET}" if word_done else clue
            lines.append(f"  {marker} {Colors.BOLD}{num:2d}.{Colors.RESET} {clue_display} ({len(word)})")

        # Controls
        lines.append(f"\n{Colors.BOLD}{Colors.CYAN}── CONTROLS ────────────────────────────{Colors.RESET}")
        lines.append(f"  {Colors.YELLOW}Arrow keys{Colors.RESET}  Move cursor     {Colors.YELLOW}Tab{Colors.RESET}        Toggle across/down")
        lines.append(f"  {Colors.YELLOW}Letters{Colors.RESET}     Type answer     {Colors.YELLOW}Backspace{Colors.RESET}  Delete letter")
        lines.append(f"  {Colors.YELLOW}C{Colors.RESET}          Check puzzle   {Colors.YELLOW}R{Colors.RESET}          Reveal letter")
        lines.append(f"  {Colors.YELLOW}W{Colors.RESET}          Reveal word     {Colors.YELLOW}Q{Colors.RESET}          Quit")
        lines.append(f"  {Colors.YELLOW}N{Colors.RESET}          New puzzle")

        return "\n".join(lines)


# ─── Simplified Terminal Input ───────────────────────────────────────────────

def get_key():
    """Read a single keypress from the terminal."""
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
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def clear_screen():
    """Clear the terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def play_interactive(generator):
    """Play the crossword puzzle interactively."""
    game = CrosswordGame(generator)

    try:
        while not game.solved:
            clear_screen()
            print(game.render())
            sys.stdout.flush()

            key = get_key()

            if key == 'QUIT' or key == 'q' or key == 'Q':
                # Confirm quit
                if key == 'Q':
                    break
                # Just q - quit
                break
            elif key == 'UP':
                game.move_cursor(-1, 0)
            elif key == 'DOWN':
                game.move_cursor(1, 0)
            elif key == 'LEFT':
                game.move_cursor(0, -1)
            elif key == 'RIGHT':
                game.move_cursor(0, 1)
            elif key == 'TAB':
                game.toggle_direction()
            elif key == 'SHIFT_TAB':
                game.toggle_direction()
            elif key == 'BACKSPACE':
                game.backspace()
            elif key == 'ENTER':
                game.toggle_direction()
            elif key == 'C':
                game.check_puzzle()
            elif key == 'R':
                game.reveal_letter()
            elif key == 'W':
                game.reveal_word()
            elif key == 'N':
                return 'new'
            elif len(key) == 1 and key.isalpha():
                game.type_letter(key)

        clear_screen()
        print(game.render())
        print(f"\n{Colors.BOLD}{Colors.GREEN}🏆 Puzzle Complete! Hints used: {game.hints_used}{Colors.RESET}")
        return 'done'

    except KeyboardInterrupt:
        return 'quit'


# ─── Non-interactive (fallback) Mode ─────────────────────────────────────────

def print_puzzle(generator, show_answers=False):
    """Print the crossword puzzle in a static format using a clean box-drawing grid."""
    across_clues, down_clues, numbered = generator.get_clues()
    number_map = {}
    for (r, c), num in numbered.items():
        number_map[(r, c)] = num

    print(f"\n{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║     📝 TERMINAL CROSSWORD PUZZLE      ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════╝{Colors.RESET}\n")

    # Use a 2-line-per-row grid: top line for numbers, bottom line for letters
    cell_w = 3  # width of each cell in characters

    # Top border
    top = "   " + "┌" + "───┬" * (generator.width - 1) + "───┐"
    mid = "   " + "├" + "───┼" * (generator.width - 1) + "───┤"
    bot = "   " + "└" + "───┴" * (generator.width - 1) + "───┘"

    # Row numbers on the left
    print(top)
    for r in range(generator.height):
        # Number row
        num_row = f"{r:2d} │"
        for c in range(generator.width):
            cell = generator.grid[r][c]
            if cell == ' ':
                num_row += f"{Colors.BG_GRAY}   {Colors.RESET}│"
            else:
                num = number_map.get((r, c), '')
                if num:
                    num_text = f"{num}"
                    num_row += f"{Colors.BG_DARK}{Colors.CYAN}{num_text:^3s}{Colors.RESET}│"
                else:
                    num_row += f"{Colors.BG_DARK}   {Colors.RESET}│"
        print(num_row)

        # Letter row
        letter_row = f"   │"
        for c in range(generator.width):
            cell = generator.grid[r][c]
            if cell == ' ':
                letter_row += f"{Colors.BG_GRAY}   {Colors.RESET}│"
            else:
                num = number_map.get((r, c), '')
                if show_answers:
                    letter_row += f"{Colors.BG_WHITE}{Colors.BLACK}{Colors.BOLD} {cell} {Colors.RESET}│"
                else:
                    letter_row += f"{Colors.BG_WHITE}   {Colors.RESET}│"
        print(letter_row)

        if r < generator.height - 1:
            print(mid)
    print(bot)

    # Clues
    print(f"\n{Colors.BOLD}{Colors.CYAN}── ACROSS ──────────────────────────────{Colors.RESET}")
    for num, word, clue in across_clues:
        print(f"  {Colors.BOLD}{num:2d}.{Colors.RESET} {clue} ({len(word)})")

    print(f"\n{Colors.BOLD}{Colors.CYAN}── DOWN ────────────────────────────────{Colors.RESET}")
    for num, word, clue in down_clues:
        print(f"  {Colors.BOLD}{num:2d}.{Colors.RESET} {clue} ({len(word)})")

    if show_answers:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}── ANSWERS ──────────────────────────────{Colors.RESET}")
        for num, word, clue in across_clues:
            print(f"  {num:2d}A: {word}")
        for num, word, clue in down_clues:
            print(f"  {num:2d}D: {word}")


# ─── Puzzle Quality Checker ─────────────────────────────────────────────────

def is_good_puzzle(generator, min_words=6):
    """Check if the generated puzzle has enough words."""
    return len(generator.placed_words) >= min_words


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Terminal Crossword Puzzle")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible puzzles")
    parser.add_argument("--words", type=int, default=12, help="Maximum number of words (default: 12)")
    parser.add_argument("--answers", action="store_true", help="Show answers (non-interactive)")
    parser.add_argument("--print", action="store_true", help="Print puzzle without playing (non-interactive)")
    parser.add_argument("--interactive", action="store_true", help="Force interactive mode")
    parser.add_argument("--no-interactive", action="store_true", help="Force non-interactive mode")
    args = parser.parse_args()

    seed = args.seed if args.seed else random.randint(1, 999999)

    # Generate until we get a good puzzle
    for attempt in range(50):
        gen = CrosswordGenerator(20, 14)
        gen.generate(max_words=args.words, seed=seed + attempt)
        gen.trim_grid()
        if is_good_puzzle(gen):
            break

    print(f"{Colors.DIM}Generated crossword with {len(gen.placed_words)} words (seed: {seed + attempt}){Colors.RESET}\n")

    if args.answers or args.print:
        print_puzzle(gen, show_answers=args.answers)
    else:
        # Try interactive mode
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
            result = play_interactive(gen)
            if result == 'new':
                # Regenerate
                main()
        else:
            print_puzzle(gen, show_answers=False)
            print(f"\n{Colors.DIM}(Run with --interactive to play, --answers to see solutions){Colors.RESET}")


if __name__ == "__main__":
    main()