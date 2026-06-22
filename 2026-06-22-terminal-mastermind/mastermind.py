#!/usr/bin/env python3
"""
Terminal Mastermind — A beautiful code-breaking game for the terminal.
Inspired by the classic Mastermind board game (Mordecai Meirowitz, 1970).

Break the secret color code! After each guess you get feedback:
  ● = correct color in correct position (black peg)
  ○ = correct color in wrong position (white peg)

Features:
  - Multiple difficulty levels
  - Auto-solver (Knuth's algorithm) demonstration mode
  - Game statistics tracking
  - Undo support
  - Configurable code length & color count
"""

import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# ─── ANSI Helpers ──────────────────────────────────────────────────────────

class Ansi:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    ITALIC  = "\033[3m"
    UNDER   = "\033[4m"
    REV     = "\033[7m"

    @staticmethod
    def fg(n): return f"\033[38;5;{n}m"
    @staticmethod
    def bg(n): return f"\033[48;5;{n}m"
    @staticmethod
    def rgb_fg(r, g, b): return f"\033[38;2;{r};{g};{b}m"
    @staticmethod
    def rgb_bg(r, g, b): return f"\033[48;2;{r};{g};{b}m"
    @staticmethod
    def cursor_up(n=1): return f"\033[{n}A"
    @staticmethod
    def cursor_down(n=1): return f"\033[{n}B"
    @staticmethod
    def cursor_left(n=1): return f"\033[{n}D"
    @staticmethod
    def cursor_right(n=1): return f"\033[{n}C"
    @staticmethod
    def clear_screen(): return "\033[2J\033[H"
    @staticmethod
    def hide_cursor(): return "\033[?25l"
    @staticmethod
    def show_cursor(): return "\033[?25h"
    @staticmethod
    def save_cursor(): return "\033[s"
    @staticmethod
    def restore_cursor(): return "\033[u"

# ─── Peg Colors ─────────────────────────────────────────────────────────────

# Each color: (name, fg_ansi_code, bg_ansi_code, symbol)
COLORS = [
    ("Red",    "196", "1",   "R"),
    ("Green",  "46",  "2",   "G"),
    ("Blue",   "21",  "4",   "B"),
    ("Yellow", "226", "11",  "Y"),
    ("Magenta","201", "5",   "M"),
    ("Cyan",   "51",  "6",   "C"),
    ("Orange", "208", "3",   "O"),
    ("White",  "255", "15",  "W"),
    ("Purple", "93",  "54",  "P"),
    ("Pink",   "213", "13",  "K"),
]

MAX_COLORS = len(COLORS)

# Feedback pegs
BLACK_PEG = "●"  # correct color, correct position
WHITE_PEG = "○"  # correct color, wrong position
EMPTY_PEG = "·"  # no match

# ─── Difficulty Presets ─────────────────────────────────────────────────────

DIFFICULTIES = {
    "easy":   {"code_length": 4, "num_colors": 6, "max_guesses": 12},
    "medium": {"code_length": 4, "num_colors": 8, "max_guesses": 10},
    "hard":   {"code_length": 5, "num_colors": 8, "max_guesses": 10},
    "expert": {"code_length": 6, "num_colors": 10, "max_guesses": 10},
}

# ─── Game State ─────────────────────────────────────────────────────────────

@dataclass
class Guess:
    """A single guess with feedback."""
    code: List[int]
    black: int = 0
    white: int = 0

@dataclass
class GameConfig:
    """Configuration for a game."""
    code_length: int = 4
    num_colors: int = 6
    max_guesses: int = 10
    secret: List[int] = field(default_factory=list)
    seed: Optional[int] = None

@dataclass
class GameStats:
    """Persistent game statistics."""
    games_played: int = 0
    games_won: int = 0
    current_streak: int = 0
    best_streak: int = 0
    total_guesses: int = 0
    guess_history: List[int] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.games_won / max(self.games_played, 1)

    @property
    def avg_guesses(self) -> float:
        if not self.guess_history:
            return 0.0
        return sum(self.guess_history) / len(self.guess_history)

STATS_FILE = Path.home() / ".mastermind_stats.json"

def load_stats() -> GameStats:
    if STATS_FILE.exists():
        try:
            data = json.loads(STATS_FILE.read_text())
            return GameStats(**data)
        except (json.JSONDecodeError, TypeError):
            pass
    return GameStats()

def save_stats(stats: GameStats):
    STATS_FILE.write_text(json.dumps(stats.__dict__, indent=2))

# ─── Game Logic ─────────────────────────────────────────────────────────────

def evaluate_guess(guess: List[int], secret: List[int]) -> Tuple[int, int]:
    """
    Evaluate a guess against the secret code.
    Returns (black_pegs, white_pegs).
    Black = correct color in correct position.
    White = correct color in wrong position.
    """
    black = sum(g == s for g, s in zip(guess, secret))
    # For white pegs, count matching colors minus black pegs
    guess_counts = Counter(guess)
    secret_counts = Counter(secret)
    total_matches = sum((guess_counts & secret_counts).values())
    white = total_matches - black
    return black, white

def is_valid_guess(code: List[int], code_length: int, num_colors: int) -> bool:
    return (
        len(code) == code_length
        and all(0 <= c < num_colors for c in code)
    )

# ─── Knuth's Algorithm (Auto-Solver) ────────────────────────────────────────

def generate_all_codes(code_length: int, num_colors: int) -> List[List[int]]:
    """Generate all possible codes."""
    if code_length == 0:
        return [[]]
    smaller = generate_all_codes(code_length - 1, num_colors)
    return [c + [i] for c in smaller for i in range(num_colors)]

def knuth_minimax_solver(code_length: int, num_colors: int, secret: List[int],
                          max_guesses: int = 10, reveal: bool = False) -> List[Guess]:
    """
    Solve a Mastermind game using Knuth's minimax algorithm.
    Returns list of guesses made.
    If reveal=True, print each step as it goes.
    """
    all_codes = generate_all_codes(code_length, num_colors)
    remaining = list(all_codes)
    guesses = []
    
    # First guess: 1,1,2,2,... pattern (Knuth's recommended start)
    first = []
    for i in range(code_length):
        first.append((i // 2) % num_colors)
    
    guess = first
    
    for turn in range(max_guesses):
        if reveal:
            print(f"\n  Turn {turn + 1}: ", end="", flush=True)
        
        black, white = evaluate_guess(guess, secret)
        g = Guess(code=guess[:], black=black, white=white)
        guesses.append(g)
        
        if reveal:
            color_str = " ".join(format_color_peg(c, num_colors) for c in guess)
            fb_str = format_feedback(black, white, code_length)
            print(f"{color_str}  {fb_str}")
        
        if black == code_length:
            return guesses
        
        # Filter remaining codes
        remaining = [
            c for c in remaining
            if evaluate_guess(guess, c) == (black, white)
        ]
        
        if not remaining:
            break
        
        if len(remaining) == 1:
            guess = remaining[0]
        else:
            # Minimax: choose the guess that minimizes the maximum remaining set size
            best_guess = None
            best_worst = len(all_codes) + 1
            
            # Prefer remaining codes as guesses (could be the answer)
            candidates = remaining
            
            for candidate in candidates:
                # Count how many remaining codes would give each feedback
                feedback_counts = Counter()
                for code in remaining:
                    fb = evaluate_guess(candidate, code)
                    feedback_counts[fb] += 1
                
                worst_case = max(feedback_counts.values())
                if worst_case < best_worst:
                    best_worst = worst_case
                    best_guess = candidate
            
            guess = best_guess if best_guess is not None else remaining[0]
    
    return guesses

# ─── Display Helpers ────────────────────────────────────────────────────────

def format_color_peg(color_idx: int, num_colors: int) -> str:
    """Format a single color peg with ANSI background."""
    name, _, bg, sym = COLORS[color_idx]
    # Use a colored block
    return f"{Ansi.bg(bg)} {sym} {Ansi.RESET}"

def format_feedback(black: int, white: int, code_length: int) -> str:
    """Format feedback pegs."""
    parts = []
    for _ in range(black):
        parts.append(f"{Ansi.fg(15)}{Ansi.bg(0)}{BLACK_PEG}{Ansi.RESET}")
    for _ in range(white):
        parts.append(f"{Ansi.fg(0)}{Ansi.bg(7)}{WHITE_PEG}{Ansi.RESET}")
    remaining = code_length - black - white
    for _ in range(remaining):
        parts.append(f"{Ansi.DIM}{EMPTY_PEG}{Ansi.RESET}")
    return " ".join(parts)

def format_color_name(color_idx: int) -> str:
    """Get the colored name of a color."""
    name, fg, _, _ = COLORS[color_idx]
    return f"{Ansi.fg(fg)}{Ansi.BOLD}{name}{Ansi.RESET}"

def color_menu(num_colors: int) -> str:
    """Build a color selection menu string."""
    parts = []
    for i in range(num_colors):
        name, _, bg, sym = COLORS[i]
        parts.append(f" {Ansi.bg(bg)} {sym} {Ansi.RESET}={name}")
    return "  ".join(parts)

def draw_board(guesses: List[Guess], config: GameConfig, current_input: List[Optional[int]],
               cursor_pos: int, message: str = "", reveal_secret: bool = False) -> str:
    """Build the full game board as a string."""
    lines = []
    
    # Title
    title = f"{Ansi.BOLD}{Ansi.fg(213)}╔══════════════════════════════╗"
    title += f"\n║   {Ansi.fg(226)}MASTERMIND{Ansi.fg(213)}  Code Breaker   ║"
    title += f"\n╚══════════════════════════════╝{Ansi.RESET}"
    lines.append(title)
    
    # Config info
    info = f"  {Ansi.DIM}Code length: {config.code_length}  |  Colors: {config.num_colors}  |  "
    info += f"Guesses: {len(guesses)}/{config.max_guesses}{Ansi.RESET}"
    lines.append(info)
    
    # Color legend
    lines.append(f"  {Ansi.DIM}Colors:{Ansi.RESET} {color_menu(config.num_colors)}")
    lines.append("")
    
    # Previous guesses
    for i, guess in enumerate(guesses):
        num = f"{Ansi.DIM}{i+1:>2}.{Ansi.RESET}"
        pegs = " ".join(format_color_peg(c, config.num_colors) for c in guess.code)
        fb = format_feedback(guess.black, guess.white, config.code_length)
        lines.append(f"  {num}  {pegs}  {fb}")
    
    # Current input line
    remaining = config.max_guesses - len(guesses)
    if remaining > 0 and not reveal_secret:
        num = f"{Ansi.BOLD}{Ansi.fg(213)} >.{Ansi.RESET}"
        
        # Add cursor indicator
        pegs_list = []
        for i in range(config.code_length):
            val = current_input[i] if i < len(current_input) else None
            if val is not None:
                pegs_list.append(format_color_peg(val, config.num_colors))
            elif i == cursor_pos:
                pegs_list.append(f"{Ansi.REV}{Ansi.DIM}[ ]{Ansi.RESET}")
            else:
                pegs_list.append(f"{Ansi.DIM}[ ]{Ansi.RESET}")
        
        pegs = " ".join(pegs_list)
        lines.append(f"  {num}  {pegs}")
    
    # Separator
    lines.append(f"  {Ansi.DIM}{'─' * 40}{Ansi.RESET}")
    
    # Secret code (revealed or hidden)
    if reveal_secret:
        secret_str = " ".join(format_color_peg(c, config.num_colors) for c in config.secret)
        lines.append(f"  {Ansi.BOLD}Secret:{Ansi.RESET}  {secret_str}")
    else:
        hidden = " ".join(f"{Ansi.DIM}?{Ansi.RESET}" for _ in config.secret)
        lines.append(f"  {Ansi.BOLD}Secret:{Ansi.RESET}  {hidden}")
    
    # Message
    if message:
        lines.append(f"  {message}")
    
    return "\n".join(lines)

# ─── Interactive Game ────────────────────────────────────────────────────────

def play_interactive(config: GameConfig) -> Tuple[bool, int]:
    """
    Play an interactive game. Returns (won, num_guesses).
    """
    guesses: List[Guess] = []
    current_input: List[Optional[int]] = []
    cursor_pos = 0
    message = ""
    message_timer = 0
    
    # Enable raw mode for single-key input
    import tty
    import termios
    old_settings = termios.tcgetattr(sys.stdin)
    
    def clear_msg():
        nonlocal message, message_timer
        message = ""
        message_timer = 0
    
    try:
        tty.setraw(sys.stdin.fileno())
        print(Ansi.hide_cursor(), end="", flush=True)
        
        while True:
            # Draw
            print(Ansi.clear_screen(), end="")
            board = draw_board(guesses, config, current_input, cursor_pos,
                             message, reveal_secret=False)
            print(board)
            print(f"\n  {Ansi.DIM}Keys: 1-{min(config.num_colors,9)}=place color  ←→=move  "
                  f"Bksp=delete  Enter=submit  q=quit  u=undo  h=hint{Ansi.RESET}")
            
            # Get key
            ch = sys.stdin.read(1)
            
            # Handle escape sequences
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'C':  # Right arrow
                        cursor_pos = min(cursor_pos + 1, config.code_length - 1)
                        clear_msg()
                    elif ch3 == 'D':  # Left arrow
                        cursor_pos = max(cursor_pos - 1, 0)
                        clear_msg()
                    elif ch3 == 'A':  # Up arrow
                        pass
                    elif ch3 == 'B':  # Down arrow
                        pass
                continue
            
            # Number keys: place color
            if ch in '123456789' and int(ch) <= config.num_colors:
                color_idx = int(ch) - 1
                if cursor_pos < len(current_input):
                    current_input[cursor_pos] = color_idx
                else:
                    current_input.append(color_idx)
                cursor_pos = min(cursor_pos + 1, config.code_length - 1)
                # Pad with None up to cursor_pos
                while len(current_input) < cursor_pos + 1:
                    current_input.append(None)
                clear_msg()
                continue
            
            # 0 maps to color 10 (index 9) if available
            if ch == '0' and config.num_colors >= 10:
                color_idx = 9
                if cursor_pos < len(current_input):
                    current_input[cursor_pos] = color_idx
                else:
                    current_input.append(color_idx)
                cursor_pos = min(cursor_pos + 1, config.code_length - 1)
                while len(current_input) < cursor_pos + 1:
                    current_input.append(None)
                clear_msg()
                continue
            
            # Letter keys for colors beyond 9
            letter_map = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4,
                         'f': 5, 'g': 6, 'h': 7, 'i': 8, 'j': 9}
            if ch.lower() in letter_map:
                color_idx = letter_map[ch.lower()]
                if color_idx < config.num_colors:
                    if cursor_pos < len(current_input):
                        current_input[cursor_pos] = color_idx
                    else:
                        current_input.append(color_idx)
                    cursor_pos = min(cursor_pos + 1, config.code_length - 1)
                    while len(current_input) < cursor_pos + 1:
                        current_input.append(None)
                    clear_msg()
                    continue
            
            # Backspace
            if ch in ('\x7f', '\x08'):
                if current_input:
                    if cursor_pos > 0:
                        cursor_pos -= 1
                    if cursor_pos < len(current_input):
                        current_input.pop(cursor_pos)
                clear_msg()
                continue
            
            # Enter: submit guess
            if ch in ('\r', '\n'):
                # Fill in any None values
                filled = [c for c in current_input if c is not None]
                if len(filled) != config.code_length:
                    message = f"{Ansi.fg(196)}Fill all {config.code_length} positions!{Ansi.RESET}"
                    continue
                
                black, white = evaluate_guess(filled, config.secret)
                guess = Guess(code=filled, black=black, white=white)
                guesses.append(guess)
                current_input = []
                cursor_pos = 0
                
                if black == config.code_length:
                    message = f"{Ansi.fg(46)}{Ansi.BOLD}🎉 YOU WIN! Cracked in {len(guesses)} guesses!{Ansi.RESET}"
                    # Show victory screen
                    print(Ansi.clear_screen(), end="")
                    print(draw_board(guesses, config, [], 0, message, reveal_secret=True))
                    print(f"\n  {Ansi.DIM}Press any key to continue...{Ansi.RESET}")
                    sys.stdin.read(1)
                    return True, len(guesses)
                elif len(guesses) >= config.max_guesses:
                    message = f"{Ansi.fg(196)}{Ansi.BOLD}💀 GAME OVER! Out of guesses.{Ansi.RESET}"
                    print(Ansi.clear_screen(), end="")
                    print(draw_board(guesses, config, [], 0, message, reveal_secret=True))
                    print(f"\n  {Ansi.DIM}Press any key to continue...{Ansi.RESET}")
                    sys.stdin.read(1)
                    return False, len(guesses)
                else:
                    message = f"{Ansi.fg(226)}{black}{Ansi.RESET} ● black  {Ansi.fg(255)}{white}{Ansi.RESET} ○ white"
                continue
            
            # Quit
            if ch.lower() == 'q':
                print(Ansi.clear_screen(), end="")
                print(f"  {Ansi.DIM}Game abandoned. The secret was:{Ansi.RESET}")
                secret_str = " ".join(format_color_peg(c, config.num_colors) for c in config.secret)
                print(f"  {secret_str}")
                return False, len(guesses)
            
            # Undo
            if ch.lower() == 'u':
                if guesses:
                    guesses.pop()
                    current_input = []
                    cursor_pos = 0
                    message = f"{Ansi.fg(226)}Last guess undone.{Ansi.RESET}"
                else:
                    message = f"{Ansi.DIM}Nothing to undo.{Ansi.RESET}"
                continue
            
            # Hint
            if ch.lower() == 'h':
                if config.secret:
                    unrevealed = [i for i in range(config.code_length)
                                 if i >= len(guesses) or guesses[-1].code[i] != config.secret[i]]
                    if unrevealed:
                        pos = random.choice(unrevealed)
                        message = (f"{Ansi.fg(51)}Hint: Position {pos+1} is "
                                  f"{format_color_name(config.secret[pos])}{Ansi.RESET}")
                    else:
                        message = f"{Ansi.fg(51)}You already know it all!{Ansi.RESET}"
                continue
            
            # Delete at cursor
            if ch.lower() == 'd':
                if cursor_pos < len(current_input) and current_input:
                    current_input.pop(cursor_pos)
                clear_msg()
                continue
    
    finally:
        # Restore terminal
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print(Ansi.show_cursor(), end="", flush=True)

# ─── Non-interactive / Demo Mode ────────────────────────────────────────────

def play_auto_solve(config: GameConfig, animate: bool = True) -> Tuple[bool, int]:
    """Run Knuth's algorithm to auto-solve, with optional animation."""
    print(Ansi.clear_screen(), end="")
    print(f"  {Ansi.BOLD}{Ansi.fg(213)}Mastermind — Auto-Solver (Knuth's Algorithm){Ansi.RESET}")
    print(f"  {Ansi.DIM}Code length: {config.code_length}  |  Colors: {config.num_colors}{Ansi.RESET}")
    print()
    
    secret_str = " ".join(format_color_peg(c, config.num_colors) for c in config.secret)
    print(f"  {Ansi.BOLD}Secret:{Ansi.RESET}  {secret_str}")
    print(f"  {Ansi.DIM}{'─' * 40}{Ansi.RESET}")
    
    guesses = knuth_minimax_solver(
        config.code_length, config.num_colors, config.secret,
        config.max_guesses, reveal=True
    )
    
    print()
    if guesses and guesses[-1].black == config.code_length:
        print(f"  {Ansi.fg(46)}{Ansi.BOLD}✓ Solved in {len(guesses)} guesses!{Ansi.RESET}")
        return True, len(guesses)
    else:
        print(f"  {Ansi.fg(196)}{Ansi.BOLD}✗ Could not solve within {config.max_guesses} guesses.{Ansi.RESET}")
        return False, len(guesses)

def play_batch_solve(config: GameConfig, num_games: int = 100) -> dict:
    """Run the solver on many random codes and gather statistics."""
    results = []
    for _ in range(num_games):
        secret = [random.randint(0, config.num_colors - 1) for _ in range(config.code_length)]
        guesses = knuth_minimax_solver(config.code_length, config.num_colors, secret, config.max_guesses, reveal=False)
        won = guesses[-1].black == config.code_length if guesses else False
        results.append((won, len(guesses)))
    
    wins = sum(1 for w, _ in results if w)
    turns = [g for _, g in results]
    
    return {
        "total": num_games,
        "wins": wins,
        "win_rate": wins / num_games,
        "avg_guesses": sum(turns) / len(turns),
        "max_guesses": max(turns),
        "min_guesses": min(turns),
    }

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Terminal Mastermind — A beautiful code-breaking game",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Play with easy defaults (4 pegs, 6 colors)
  %(prog)s --difficulty hard         Play on hard (5 pegs, 8 colors)
  %(prog)s --code-length 5 --colors 8   Custom game
  %(prog)s --solve                   Watch the AI solve it
  %(prog)s --solve --benchmark 50    Benchmark the solver over 50 games
  %(prog)s --stats                   Show your game statistics
        """
    )
    parser.add_argument("-d", "--difficulty", choices=list(DIFFICULTIES.keys()),
                       default="easy", help="Difficulty preset (default: easy)")
    parser.add_argument("-l", "--code-length", type=int,
                       help="Number of pegs in the code (overrides difficulty)")
    parser.add_argument("-c", "--colors", type=int,
                       help="Number of colors available (overrides difficulty)")
    parser.add_argument("-g", "--max-guesses", type=int,
                       help="Maximum guesses allowed (overrides difficulty)")
    parser.add_argument("-s", "--secret", type=str,
                       help="Set a specific secret code (e.g. 'R G B Y')")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--solve", action="store_true",
                       help="Auto-solve with Knuth's algorithm (demo)")
    parser.add_argument("--benchmark", type=int, metavar="N",
                       help="Benchmark solver over N random games")
    parser.add_argument("--stats", action="store_true",
                       help="Show game statistics")
    parser.add_argument("--reset-stats", action="store_true",
                       help="Reset game statistics")
    parser.add_argument("--version", action="version", version="Mastermind 1.0.0")

    args = parser.parse_args()

    # Handle stats
    if args.reset_stats:
        save_stats(GameStats())
        print("Statistics reset.")
        return

    if args.stats:
        stats = load_stats()
        print(f"{Ansi.BOLD}{Ansi.fg(213)}Mastermind Statistics{Ansi.RESET}")
        print(f"  Games played:    {stats.games_played}")
        print(f"  Games won:       {stats.games_won}")
        print(f"  Win rate:        {stats.win_rate:.1%}")
        print(f"  Current streak:  {stats.current_streak}")
        print(f"  Best streak:     {stats.best_streak}")
        print(f"  Avg guesses:     {stats.avg_guesses:.1f}")
        return

    # Build config
    preset = DIFFICULTIES[args.difficulty]
    config = GameConfig(
        code_length=args.code_length or preset["code_length"],
        num_colors=args.colors or preset["num_colors"],
        max_guesses=args.max_guesses or preset["max_guesses"],
        seed=args.seed,
    )

    if config.num_colors > MAX_COLORS:
        print(f"Maximum {MAX_COLORS} colors supported.")
        return
    if config.code_length < 1 or config.code_length > 10:
        print(f"Code length must be 1-10.")
        return
    if config.num_colors < 2:
        print("Need at least 2 colors.")
        return

    # Set random seed
    if config.seed is not None:
        random.seed(config.seed)

    # Parse secret code
    if args.secret:
        sym_to_idx = {COLORS[i][3]: i for i in range(MAX_COLORS)}
        try:
            config.secret = [sym_to_idx[s.upper()] for s in args.secret.split()]
        except KeyError as e:
            print(f"Unknown color symbol: {e}")
            print(f"Valid symbols: {' '.join(c[3] for c in COLORS[:config.num_colors])}")
            return
    else:
        config.secret = [random.randint(0, config.num_colors - 1) for _ in range(config.code_length)]

    # Benchmark mode
    if args.benchmark:
        n = args.benchmark
        print(f"Benchmarking solver over {n} games...")
        print(f"  Code length: {config.code_length}, Colors: {config.num_colors}")
        results = play_batch_solve(config, n)
        print(f"\n{Ansi.BOLD}Results:{Ansi.RESET}")
        print(f"  Games:      {results['total']}")
        print(f"  Wins:       {results['wins']} ({results['win_rate']:.1%})")
        print(f"  Avg turns:  {results['avg_guesses']:.2f}")
        print(f"  Min turns:  {results['min_guesses']}")
        print(f"  Max turns:  {results['max_guesses']}")
        return

    # Auto-solve mode
    if args.solve:
        won, num_guesses = play_auto_solve(config)
        stats = load_stats()
        stats.games_played += 1
        if won:
            stats.games_won += 1
            stats.current_streak += 1
            stats.best_streak = max(stats.best_streak, stats.current_streak)
            stats.guess_history.append(num_guesses)
            stats.total_guesses += num_guesses
        else:
            stats.current_streak = 0
        save_stats(stats)
        return

    # Interactive game
    # Check if terminal is available
    if not sys.stdin.isatty():
        print("Interactive mode requires a terminal. Use --solve for non-interactive mode.")
        return

    print(Ansi.clear_screen(), end="")
    print(f"  {Ansi.BOLD}{Ansi.fg(213)}Welcome to Mastermind!{Ansi.RESET}")
    print(f"  {Ansi.DIM}Difficulty: {args.difficulty} ({config.code_length} pegs, "
          f"{config.num_colors} colors, {config.max_guesses} guesses){Ansi.RESET}")
    print(f"  {Ansi.DIM}Press any key to start...{Ansi.RESET}")
    
    won, num_guesses = play_interactive(config)
    
    # Update stats
    stats = load_stats()
    stats.games_played += 1
    if won:
        stats.games_won += 1
        stats.current_streak += 1
        stats.best_streak = max(stats.best_streak, stats.current_streak)
        stats.guess_history.append(num_guesses)
        stats.total_guesses += num_guesses
    else:
        stats.current_streak = 0
    save_stats(stats)

if __name__ == "__main__":
    main()