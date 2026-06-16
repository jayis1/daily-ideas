#!/usr/bin/env python3
"""
🎰 Terminal Slot Machine — Emoji Edition
A fully-featured animated slot machine in your terminal with spinning reels,
paylines, betting, credit management, win celebrations, and ANSI graphics.

Usage:
    python3 slots.py                  # Interactive mode (default)
    python3 slots.py --credits 500    # Start with 500 credits
    python3 slots.py --auto 20        # Auto-spin 20 times
    python3 slots.py --version        # Show version info
    python3 slots.py --help           # Show help message
"""

import curses
import random
import time
import sys
import os
import argparse

__version__ = "1.3.0"

# ─── Symbol Definitions ─────────────────────────────────────────────────────

# Each symbol: (name, emoji, payout_multiplier, weight)
# Payout multiplier is for 3-of-a-kind on a single line.
# Weight controls how often the symbol appears (higher = more common).
SYMBOLS = [
    ("CHERRY",  "🍒",  3,   8),
    ("LEMON",   "🍋",  4,   7),
    ("ORANGE",  "🍊",  5,   6),
    ("PLUM",    "🍇",  8,   5),
    ("BELL",    "🔔",  15,  4),
    ("BAR",     "📊",  25,  3),
    ("SEVEN",   "7️⃣",  50,  2),
    ("DIAMOND", "💎", 100,  1),
]

SYMBOL_NAMES  = [s[0] for s in SYMBOLS]
SYMBOL_EMOJIS = [s[1] for s in SYMBOLS]
SYMBOL_PAYOUTS = {s[0]: s[2] for s in SYMBOLS}
SYMBOL_WEIGHTS  = [s[3] for s in SYMBOLS]

# Build a weighted reel strip
WEIGHTED_REEL = []
for sym, emoji, payout, weight in SYMBOLS:
    WEIGHTED_REEL.extend([sym] * weight)

NUM_REELS = 3
REEL_HEIGHT = 3  # visible rows per reel (top, middle, bottom; middle = payline)

# ─── Color Pairs ────────────────────────────────────────────────────────────

CLR_BG         = 1
CLR_REEL_BG    = 2
CLR_BORDER     = 3
CLR_CHERRY     = 4
CLR_LEMON      = 5
CLR_ORANGE     = 6
CLR_PLUM       = 7
CLR_BELL       = 8
CLR_BAR        = 9
CLR_SEVEN      = 10
CLR_DIAMOND    = 11
CLR_WIN        = 12
CLR_CREDIT     = 13
CLR_BET        = 14
CLR_DIM        = 15
CLR_JACKPOT    = 16
CLR_TITLE      = 17

SYMBOL_COLORS = {
    "CHERRY":  CLR_CHERRY,
    "LEMON":   CLR_LEMON,
    "ORANGE":  CLR_ORANGE,
    "PLUM":    CLR_PLUM,
    "BELL":    CLR_BELL,
    "BAR":     CLR_BAR,
    "SEVEN":   CLR_SEVEN,
    "DIAMOND": CLR_DIAMOND,
}

# ─── Reel Class ──────────────────────────────────────────────────────────────

class Reel:
    """A single slot machine reel that spins and stops with animation."""

    def __init__(self, reel_id: int):
        self.reel_id = reel_id
        self.strip = list(WEIGHTED_REEL)
        random.shuffle(self.strip)
        self.position = random.randint(0, len(self.strip) - 1)
        self.spinning = False
        self.stop_time = 0
        self.target_symbol = None
        self.bounce_phase = 0

    def get_visible(self) -> list:
        """Return the 3 visible symbols (top, middle, bottom)."""
        result = []
        for offset in range(-1, 2):
            idx = (self.position + offset) % len(self.strip)
            result.append(self.strip[idx])
        return result

    def get_payline(self) -> str:
        """Return the symbol on the payline (middle row)."""
        return self.strip[self.position % len(self.strip)]

    def spin(self, target_symbol: str, delay_ms: int):
        """Start spinning; will stop after delay_ms milliseconds showing target_symbol."""
        self.spinning = True
        self.target_symbol = target_symbol
        self.stop_time = time.time() + delay_ms / 1000.0
        self.bounce_phase = 0

    def update(self) -> bool:
        """Advance reel by one step. Returns True if reel just stopped."""
        if not self.spinning:
            return False

        # Advance position
        self.position = (self.position + 1) % len(self.strip)

        # Check if it's time to stop
        if time.time() >= self.stop_time:
            # Snap to target symbol
            for i, sym in enumerate(self.strip):
                if sym == self.target_symbol:
                    self.position = i
                    break
            self.spinning = False
            self.bounce_phase = 3  # bounce animation frames
            return True

        return False

    def update_bounce(self) -> bool:
        """Update bounce animation after stopping. Returns True when bounce is done."""
        if self.bounce_phase > 0:
            self.bounce_phase -= 1
            return self.bounce_phase == 0
        return True


# ─── Slot Machine Game ──────────────────────────────────────────────────────

class SlotMachine:
    """Main slot machine game logic and rendering state."""

    DEFAULT_CREDITS = 100

    def __init__(self, stdscr, starting_credits=None):
        self.stdscr = stdscr
        self.credits = starting_credits if starting_credits is not None else self.DEFAULT_CREDITS
        self.bet = 1
        self.max_bet = 10
        self.reels = [Reel(i) for i in range(NUM_REELS)]
        self.spinning = False
        self.win_amount = 0
        self.win_lines = []  # list of (row, symbol, multiplier)
        self.win_flash_counter = 0
        self.message = "Press SPACE to spin! 🎰"
        self.total_spins = 0
        self.total_won = 0
        self.total_bet = 0
        self.history = []  # recent spin results
        self.nudge_offset = [0, 0, 0]  # bounce visual offset
        self.jackpot = False
        self.game_over = False  # True when credits hit 0

        # Extended statistics
        self.biggest_win = 0
        self.current_win_streak = 0
        self.current_loss_streak = 0
        self.best_win_streak = 0
        self.worst_loss_streak = 0
        self.peak_credits = self.credits

        self._setup_colors()
        self._calc_layout()

    def _setup_colors(self):
        """Initialize curses color pairs for the game display."""
        curses.start_color()
        curses.use_default_colors()

        # Background and UI colors
        curses.init_pair(CLR_BG,       curses.COLOR_WHITE,  17)       # dark blue bg
        curses.init_pair(CLR_REEL_BG,  curses.COLOR_WHITE,  235)      # reel background
        curses.init_pair(CLR_BORDER,   curses.COLOR_CYAN,  17)       # borders
        curses.init_pair(CLR_WIN,      curses.COLOR_BLACK,  curses.COLOR_GREEN)
        curses.init_pair(CLR_CREDIT,   curses.COLOR_GREEN,  17)
        curses.init_pair(CLR_BET,      curses.COLOR_YELLOW, 17)
        curses.init_pair(CLR_DIM,      curses.COLOR_WHITE,  240)
        curses.init_pair(CLR_JACKPOT,  curses.COLOR_RED,    curses.COLOR_YELLOW)
        curses.init_pair(CLR_TITLE,    curses.COLOR_YELLOW,  curses.COLOR_RED)

        # Symbol colors on dark reel background
        curses.init_pair(CLR_CHERRY,   curses.COLOR_RED,    235)
        curses.init_pair(CLR_LEMON,    curses.COLOR_YELLOW, 235)
        curses.init_pair(CLR_ORANGE,   curses.COLOR_RED,    235)  # orange not always available
        curses.init_pair(CLR_PLUM,     curses.COLOR_MAGENTA, 235)
        curses.init_pair(CLR_BELL,     curses.COLOR_YELLOW, 235)
        curses.init_pair(CLR_BAR,      curses.COLOR_CYAN,   235)
        curses.init_pair(CLR_SEVEN,    curses.COLOR_RED,    235)
        curses.init_pair(CLR_DIAMOND,  curses.COLOR_CYAN,   235)

    def _calc_layout(self):
        """Calculate screen layout positions based on terminal size."""
        self.h, self.w = self.stdscr.getmaxyx()

        # Reel display dimensions
        self.reel_w = 9   # width of each reel column
        self.reel_h = 5   # height of each reel (border + 3 rows + border)
        self.reel_gap = 3  # gap between reels

        total_reel_width = NUM_REELS * self.reel_w + (NUM_REELS - 1) * self.reel_gap
        self.reel_x_start = (self.w - total_reel_width) // 2
        self.reel_y_start = max(2, (self.h - 20) // 2)

    def _determine_result(self) -> list:
        """Determine the final symbols for each reel based on weighted probabilities."""
        return [random.choice(WEIGHTED_REEL) for _ in range(NUM_REELS)]

    def spin(self):
        """Start a spin, deducting the current bet from credits."""
        if self.spinning:
            return
        if self.game_over:
            self.message = "💔 Game over! Press R to rebuy (100 credits)."
            return
        if self.credits < self.bet:
            if self.credits <= 0:
                self.game_over = True
                self.message = "💀 Bankrupt! Press R to rebuy (100 credits)."
            else:
                self.message = "❌ Not enough credits! Lower your bet or press R to rebuy."
            return

        # Deduct bet
        self.credits -= self.bet
        self.total_bet += self.bet
        self.total_spins += 1
        self.win_amount = 0
        self.win_lines = []
        self.win_flash_counter = 0
        self.jackpot = False
        self.game_over = False
        self.message = "Spinning..."

        # Determine outcomes
        results = self._determine_result()

        # Start each reel spinning with staggered stop times
        for i, reel in enumerate(self.reels):
            reel.spin(results[i], delay_ms=800 + i * 500)

        self.spinning = True

    def rebuy(self):
        """Give the player more credits when they're bankrupt or can't afford the current bet."""
        if self.credits <= 0 or self.credits < self.bet:
            self.credits = self.DEFAULT_CREDITS
            self.game_over = False
            # Lower bet only if new credits can't cover it
            if self.bet > self.credits:
                self.bet = self.credits
            self.message = f"💰 Rebuy! {self.credits} credits added. Good luck!"

    def check_wins(self):
        """Check for winning combinations on all paylines."""
        # Get the 3x3 visible grid
        grid = []
        for reel in self.reels:
            grid.append(reel.get_visible())

        # grid[col][row] → transpose to grid_rows[row][col]
        rows = []
        for row in range(3):
            rows.append([grid[col][row] for col in range(NUM_REELS)])

        wins = []

        # ─── Line 1: Middle row (main payline) ───
        mid = rows[1]
        if mid[0] == mid[1] == mid[2]:
            mult = SYMBOL_PAYOUTS[mid[0]]
            wins.append((1, mid[0], mult))

        # ─── Line 2: Top row ───
        top = rows[0]
        if top[0] == top[1] == top[2]:
            mult = SYMBOL_PAYOUTS[top[0]]
            wins.append((0, top[0], mult))

        # ─── Line 3: Bottom row ───
        bot = rows[2]
        if bot[0] == bot[1] == bot[2]:
            mult = SYMBOL_PAYOUTS[bot[0]]
            wins.append((2, bot[0], mult))

        # ─── Line 4: Diagonal top-left to bottom-right ───
        diag1 = [rows[0][0], rows[1][1], rows[2][2]]
        if diag1[0] == diag1[1] == diag1[2]:
            mult = SYMBOL_PAYOUTS[diag1[0]]
            wins.append((3, diag1[0], mult))

        # ─── Line 5: Diagonal bottom-left to top-right ───
        diag2 = [rows[2][0], rows[1][1], rows[0][2]]
        if diag2[0] == diag2[1] == diag2[2]:
            mult = SYMBOL_PAYOUTS[diag2[0]]
            wins.append((4, diag2[0], mult))

        # ─── Two-of-a-kind on payline (small win) ───
        mid = rows[1]
        if mid[0] == mid[1] or mid[1] == mid[2]:
            if mid[0] != mid[1] or mid[1] != mid[2]:  # not 3-of-a-kind
                sym = mid[1]  # middle symbol
                small_mult = max(1, SYMBOL_PAYOUTS[sym] // 5)
                wins.append((1, sym, small_mult))

        # Calculate total win
        total_win = 0
        for _, sym, mult in wins:
            total_win += mult * self.bet

        if total_win > 0:
            self.win_amount = total_win
            self.credits += total_win
            self.total_won += total_win
            self.win_lines = wins
            self.win_flash_counter = 20

            # Track extended statistics
            if total_win > self.biggest_win:
                self.biggest_win = total_win
            self.current_win_streak += 1
            self.current_loss_streak = 0
            if self.current_win_streak > self.best_win_streak:
                self.best_win_streak = self.current_win_streak

            # Check for jackpot (3 diamonds on payline)
            payline = [reel.get_payline() for reel in self.reels]
            if payline[0] == payline[1] == payline[2] == "DIAMOND":
                self.jackpot = True
                self.message = f"💎💎💎 JACKPOT! +{total_win} credits! 💎💎💎"
            else:
                self.message = f"🎉 WIN! +{total_win} credits!"
        else:
            self.message = "No win. Spin again!"
            self.current_win_streak = 0
            self.current_loss_streak += 1
            if self.current_loss_streak > self.worst_loss_streak:
                self.worst_loss_streak = self.current_loss_streak

        # Track peak credits
        if self.credits > self.peak_credits:
            self.peak_credits = self.credits

        # Check for bankruptcy
        if self.credits <= 0:
            self.game_over = True
            self.message = "💀 Bankrupt! Press R to rebuy (100 credits)."

        # Add to history
        payline_syms = [reel.get_payline() for reel in self.reels]
        self.history.append((payline_syms[:], total_win))
        if len(self.history) > 10:
            self.history.pop(0)

    def change_bet(self, delta: int):
        """Increase or decrease the current bet by delta."""
        if self.spinning:
            return
        new_bet = self.bet + delta
        if 1 <= new_bet <= self.max_bet:
            self.bet = new_bet
            self.message = f"Bet changed to {self.bet}"
        elif new_bet > self.max_bet:
            self.message = f"Maximum bet is {self.max_bet}"
        elif new_bet < 1:
            self.message = "Minimum bet is 1"

    def draw(self):
        """Render the entire game screen."""
        stdscr = self.stdscr
        stdscr.clear()
        h, w = self.h, self.w

        # ─── Title ───────────────────────────────────────────────────────
        title = "🎰 LUCKY TERMINAL SLOTS 🎰"
        title_x = (w - len(title)) // 2
        if h > 2 and title_x >= 0:
            try:
                stdscr.addstr(0, title_x, title, curses.color_pair(CLR_TITLE) | curses.A_BOLD)
            except curses.error:
                pass

        # ─── Machine Frame ──────────────────────────────────────────────
        frame_top = self.reel_y_start - 1
        frame_left = self.reel_x_start - 2
        frame_right = self.reel_x_start + NUM_REELS * self.reel_w + (NUM_REELS - 1) * self.reel_gap + 1
        frame_bottom = self.reel_y_start + self.reel_h + 8

        # Draw top/bottom borders
        if frame_top >= 0 and frame_left >= 0 and frame_right < w:
            border_line = "═" * (frame_right - frame_left + 1)
            try:
                stdscr.addstr(frame_top, frame_left, border_line, curses.color_pair(CLR_BORDER))
            except curses.error:
                pass
            try:
                stdscr.addstr(frame_bottom, frame_left, border_line, curses.color_pair(CLR_BORDER))
            except curses.error:
                pass

        # Draw side borders
        for y in range(frame_top + 1, frame_bottom):
            if y < h and frame_left >= 0:
                try:
                    stdscr.addstr(y, frame_left, "║", curses.color_pair(CLR_BORDER))
                except curses.error:
                    pass
            if y < h and frame_right < w:
                try:
                    stdscr.addstr(y, frame_right, "║", curses.color_pair(CLR_BORDER))
                except curses.error:
                    pass

        # ─── Reels ──────────────────────────────────────────────────────
        for i, reel in enumerate(self.reels):
            rx = self.reel_x_start + i * (self.reel_w + self.reel_gap)
            ry = self.reel_y_start

            visible = reel.get_visible()
            bounce = 0
            if reel.bounce_phase > 0:
                bounce = 1 if reel.bounce_phase in (3, 1) else -1

            # Draw reel border
            try:
                stdscr.addstr(ry, rx - 1, "┌" + "─" * self.reel_w + "┐",
                              curses.color_pair(CLR_BORDER))
            except curses.error:
                pass

            # Draw 3 visible rows
            for row_idx in range(3):
                sym_name = visible[row_idx]
                sym_idx = SYMBOL_NAMES.index(sym_name) if sym_name in SYMBOL_NAMES else 0
                sym_emoji = SYMBOL_EMOJIS[sym_idx]
                sym_clr = SYMBOL_COLORS.get(sym_name, CLR_REEL_BG)

                # Determine if this cell is part of a winning line
                is_win = False
                if self.win_flash_counter > 0 and not self.spinning:
                    # Check if this row is part of a horizontal win
                    for win_row, win_sym, _ in self.win_lines:
                        if win_row == row_idx:
                            is_win = True
                            break
                    # Check if this cell is part of a diagonal win
                    if not is_win:
                        for win_row, win_sym, _ in self.win_lines:
                            if win_row == 3:  # diagonal ↘ (top-left to bottom-right)
                                # Cells: (col=0,row=0), (col=1,row=1), (col=2,row=2)
                                if row_idx == 0 and i == 0:
                                    is_win = True
                                elif row_idx == 1 and i == 1:
                                    is_win = True
                                elif row_idx == 2 and i == 2:
                                    is_win = True
                            elif win_row == 4:  # diagonal ↗ (bottom-left to top-right)
                                # Cells: (col=0,row=2), (col=1,row=1), (col=2,row=0)
                                if row_idx == 2 and i == 0:
                                    is_win = True
                                elif row_idx == 1 and i == 1:
                                    is_win = True
                                elif row_idx == 0 and i == 2:
                                    is_win = True

                y_pos = ry + 1 + row_idx + bounce

                if is_win and self.win_flash_counter % 4 < 2:
                    color = curses.color_pair(CLR_WIN) | curses.A_BOLD
                else:
                    color = curses.color_pair(sym_clr)

                # Center the emoji in the reel width
                display = f" {sym_emoji} "
                display = display.center(self.reel_w)

                try:
                    stdscr.addstr(y_pos, rx, display, color)
                except curses.error:
                    pass

            # Bottom border
            try:
                stdscr.addstr(ry + 4, rx - 1, "└" + "─" * self.reel_w + "┘",
                              curses.color_pair(CLR_BORDER))
            except curses.error:
                pass

            # Payline marker (arrows on the sides)
            if ry + 2 < h:
                try:
                    stdscr.addstr(ry + 2, rx - 2, "►", curses.color_pair(CLR_WIN) | curses.A_BOLD)
                except curses.error:
                    pass
                try:
                    end_x = rx + self.reel_w + 1
                    if end_x < w:
                        stdscr.addstr(ry + 2, end_x, "◄",
                                      curses.color_pair(CLR_WIN) | curses.A_BOLD)
                except curses.error:
                    pass

        # ─── Info Panel ──────────────────────────────────────────────────
        info_y = self.reel_y_start + self.reel_h + 1

        # Credits
        credit_str = f"CREDITS: {self.credits:>5}"
        try:
            stdscr.addstr(info_y, self.reel_x_start, credit_str,
                          curses.color_pair(CLR_CREDIT) | curses.A_BOLD)
        except curses.error:
            pass

        # Bet
        bet_str = f"BET: {self.bet:>2}"
        try:
            stdscr.addstr(info_y, self.reel_x_start + 22, bet_str,
                          curses.color_pair(CLR_BET) | curses.A_BOLD)
        except curses.error:
            pass

        # Win
        if self.win_amount > 0:
            win_str = f"WIN: {self.win_amount:>5}"
            color = curses.color_pair(CLR_JACKPOT) if self.jackpot else curses.color_pair(CLR_WIN)
            try:
                stdscr.addstr(info_y, self.reel_x_start + 35, win_str, color | curses.A_BOLD)
            except curses.error:
                pass

        # ─── Message ────────────────────────────────────────────────────
        msg_y = info_y + 2
        try:
            if self.jackpot and self.win_flash_counter > 0:
                stdscr.addstr(msg_y, self.reel_x_start, self.message,
                              curses.color_pair(CLR_JACKPOT) | curses.A_BOLD)
            elif self.win_amount > 0 and self.win_flash_counter > 0:
                stdscr.addstr(msg_y, self.reel_x_start, self.message,
                              curses.color_pair(CLR_WIN) | curses.A_BOLD)
            elif self.game_over:
                stdscr.addstr(msg_y, self.reel_x_start, self.message,
                              curses.color_pair(CLR_JACKPOT) | curses.A_BOLD)
            else:
                stdscr.addstr(msg_y, self.reel_x_start, self.message,
                              curses.color_pair(CLR_BORDER))
        except curses.error:
            pass

        # ─── Controls ───────────────────────────────────────────────────
        ctrl_y = msg_y + 2
        if self.game_over:
            controls = "[R] Rebuy  [q] Quit"
        else:
            controls = "[SPACE] Spin  [↑/↓] Bet  [q] Quit"
        try:
            stdscr.addstr(ctrl_y, self.reel_x_start, controls,
                          curses.color_pair(CLR_DIM))
        except curses.error:
            pass

        # ─── Pay Table ──────────────────────────────────────────────────
        pay_y = ctrl_y + 2
        try:
            stdscr.addstr(pay_y, self.reel_x_start, "─── PAY TABLE (×bet) ───",
                          curses.color_pair(CLR_BORDER))
        except curses.error:
            pass

        for idx, (name, emoji, payout, _) in enumerate(SYMBOLS):
            row_y = pay_y + 1 + idx
            line = f" {emoji} {emoji} {emoji}  {name:<8} ×{payout:>3}"
            try:
                stdscr.addstr(row_y, self.reel_x_start, line,
                              curses.color_pair(SYMBOL_COLORS.get(name, CLR_REEL_BG)))
            except curses.error:
                pass

        # ─── Stats ─────────────────────────────────────────────────────
        stats_y = pay_y + 1 + len(SYMBOLS) + 1
        if self.total_spins > 0:
            payback = (self.total_won / self.total_bet * 100) if self.total_bet > 0 else 0
            stats = f"Spins:{self.total_spins} Won:{self.total_won} Payback:{payback:.1f}%"
            try:
                stdscr.addstr(stats_y, self.reel_x_start, stats,
                              curses.color_pair(CLR_DIM))
            except curses.error:
                pass

        # ─── Extended stats line ──────────────────────────────────────
        ext_y = stats_y + 1
        if self.total_spins > 0:
            ext = f"Best win:{self.biggest_win} Peak:{self.peak_credits} Streak:W{self.best_win_streak}/L{self.worst_loss_streak}"
            try:
                stdscr.addstr(ext_y, self.reel_x_start, ext,
                              curses.color_pair(CLR_DIM))
            except curses.error:
                pass

        # ─── Jackpot Flash ──────────────────────────────────────────────
        if self.jackpot and self.win_flash_counter > 0 and self.win_flash_counter % 2 == 0:
            # Flash the entire screen border
            for y in range(0, h, 2):
                try:
                    stdscr.addstr(y, 0, " " * w, curses.color_pair(CLR_JACKPOT))
                except curses.error:
                    pass

        stdscr.refresh()

    def update(self):
        """Update game state (reel animation, flash counters, etc.)."""
        if self.spinning:
            for reel in self.reels:
                reel.update()
                if not reel.spinning and reel.bounce_phase > 0:
                    reel.update_bounce()

            # Check if all reels have stopped
            if all(not reel.spinning for reel in self.reels):
                # Wait for bounces to finish
                if all(reel.bounce_phase == 0 for reel in self.reels):
                    self.spinning = False
                    self.check_wins()

        if self.win_flash_counter > 0:
            self.win_flash_counter -= 1


# ─── Auto-Spin Mode ────────────────────────────────────────────────────────

def auto_spin(stdscr, num_spins, starting_credits):
    """Run an auto-spin session that plays automatically without user input."""
    game = SlotMachine(stdscr, starting_credits=starting_credits)

    spin_counter = 0

    while spin_counter < num_spins:
        # Handle quit key
        try:
            key = stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break
        except Exception:
            pass

        # If not spinning and not bankrupt, spin
        if not game.spinning and not game.game_over and game.credits >= game.bet:
            game.spin()
            spin_counter += 1
        elif game.game_over or game.credits < game.bet:
            # Can't continue, show final state and wait
            game.message = f"Auto-spin done! {spin_counter}/{num_spins} spins. Press Q to exit."
            game.draw()
            break

        game.update()
        game.draw()
        time.sleep(0.08)

    # Show final screen
    game.message = f"Auto-spin complete! {spin_counter}/{num_spins} spins. Press Q to exit."
    game.draw()

    # Wait for user to quit
    while True:
        try:
            key = stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break
        except Exception:
            pass
        time.sleep(0.05)


# ─── Main Loop ───────────────────────────────────────────────────────────────

def main(stdscr):
    """Main interactive game loop."""
    # Read starting credits from environment variable (set by argparse)
    try:
        starting_credits = int(os.environ.get("SLOT_CREDITS", "100"))
        auto_spins = int(os.environ.get("SLOT_AUTO", "0"))
    except ValueError:
        starting_credits = 100
        auto_spins = 0

    curses.curs_set(0)       # hide cursor
    stdscr.nodelay(True)     # non-blocking input
    stdscr.timeout(80)       # refresh rate in ms

    if auto_spins > 0:
        auto_spin(stdscr, auto_spins, starting_credits)
        return

    game = SlotMachine(stdscr, starting_credits=starting_credits)

    while True:
        # Handle input
        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        if key == ord(' ') or key == ord('s') or key == ord('S'):
            game.spin()
        elif key == curses.KEY_UP or key == ord('+') or key == ord('='):
            game.change_bet(1)
        elif key == curses.KEY_DOWN or key == ord('-'):
            game.change_bet(-1)
        elif key == ord('r') or key == ord('R'):
            game.rebuy()
        elif key == ord('q') or key == ord('Q'):
            break

        game.update()
        game.draw()

    # ─── Game Over Screen ───────────────────────────────────────────────
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    payback_pct = (game.total_won / game.total_bet * 100) if game.total_bet > 0 else 0.0
    lines = [
        "🎰 Thanks for playing! 🎰",
        "",
        f"Final Credits: {game.credits}",
        f"Total Spins:   {game.total_spins}",
        f"Total Won:     {game.total_won}",
        f"Total Bet:     {game.total_bet}",
        f"Payback Rate:  {payback_pct:.1f}%",
        f"Biggest Win:    {game.biggest_win}",
        f"Peak Credits:   {game.peak_credits}",
        f"Best Win Streak: {game.best_win_streak}",
        f"Worst Loss Streak: {game.worst_loss_streak}",
        "",
        "Press any key to exit..."
    ]
    for i, line in enumerate(lines):
        y = (h - len(lines)) // 2 + i
        x = (w - len(line)) // 2
        if 0 <= y < h and 0 <= x < w:
            try:
                stdscr.addstr(y, max(0, x), line,
                              curses.color_pair(CLR_CREDIT) | curses.A_BOLD)
            except curses.error:
                pass
    stdscr.refresh()
    stdscr.getch()


def run_interactive(starting_credits=100):
    """Entry point for running the interactive game with argparse options."""
    curses.wrapper(main)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🎰 Terminal Slot Machine — Spin the reels right in your terminal!",
        epilog="Try 'python3 slots.py --credits 500' for a high-roller session!"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--credits", type=int, default=100,
                        help="Starting credits (default: 100)")
    parser.add_argument("--auto", type=int, default=0,
                        help="Auto-spin N times instead of interactive play (default: 0 = interactive)")

    args = parser.parse_args()

    # Validate inputs
    if args.credits < 1:
        parser.error("--credits must be at least 1")
    if args.auto < 0:
        parser.error("--auto must be 0 or greater")

    # Pass settings through environment variables to the curses main function
    os.environ["SLOT_CREDITS"] = str(args.credits)
    os.environ["SLOT_AUTO"] = str(args.auto)

    curses.wrapper(main)