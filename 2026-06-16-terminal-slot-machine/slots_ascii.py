#!/usr/bin/env python3
"""
🎰 Terminal Slot Machine
A fully-featured animated slot machine in your terminal with spinning reels,
paylines, betting, credit management, win celebrations, and ANSI graphics.

This version uses ASCII art symbols as fallback for terminals without emoji support.
"""

import curses
import random
import time
import sys
import os

# ─── Symbol Definitions ─────────────────────────────────────────────────────

# Each symbol: (name, ascii_art_3line, payout_multiplier, weight, color_pair)
# ascii_art_3line is a tuple of 3 strings, each 7 chars wide
SYMBOLS = [
    ("CHERRY", (
        "  .-. ",
        " (   )",
        "  '-' "
    ), 3, 8, 4),

    ("LEMON", (
        " .--. ",
        "/ _. \\",
        "'----'",
    ), 4, 7, 5),

    ("ORANGE", (
        " .--. ",
        "| ().|",
        " '--' ",
    ), 5, 6, 6),

    ("PLUM", (
        " .##. ",
        " |##| ",
        " '##' ",
    ), 8, 5, 7),

    ("BELL", (
        "  _O_ ",
        " / | \\",
        "/__|__\\",
    ), 15, 4, 8),

    ("BAR", (
        "======",
        " BAR  ",
        "======",
    ), 25, 3, 9),

    ("SEVEN", (
        " /\\7\\ ",
        "/ 7 7\\",
        "7___7 ",
    ), 50, 2, 10),

    ("DIAMOND", (
        "  /\\  ",
        " /  \\ ",
        "/____\\",
    ), 100, 1, 11),
]

SYMBOL_NAMES   = [s[0] for s in SYMBOLS]
SYMBOL_ART     = {s[0]: s[1] for s in SYMBOLS}
SYMBOL_PAYOUTS = {s[0]: s[2] for s in SYMBOLS}
SYMBOL_WEIGHTS = [s[3] for s in SYMBOLS]
SYMBOL_CLRS    = {s[0]: s[4] for s in SYMBOLS}

WEIGHTED_REEL = []
for sym, _, _, weight, _ in SYMBOLS:
    WEIGHTED_REEL.extend([sym] * weight)

NUM_REELS = 3

# ─── Color Pairs ────────────────────────────────────────────────────────────

CLR_BG       = 1
CLR_BORDER   = 3
CLR_WIN      = 12
CLR_CREDIT   = 13
CLR_BET      = 14
CLR_DIM      = 15
CLR_JACKPOT  = 16
CLR_TITLE    = 17
CLR_REEL_BG  = 18

# ─── Reel Class ──────────────────────────────────────────────────────────────

class Reel:
    def __init__(self, reel_id: int):
        self.reel_id = reel_id
        self.strip = list(WEIGHTED_REEL)
        random.shuffle(self.strip)
        self.position = random.randint(0, len(self.strip) - 1)
        self.spinning = False
        self.stop_time = 0
        self.target_symbol = None
        self.bounce_phase = 0
        self.spin_speed = 1

    def get_visible(self) -> list:
        result = []
        for offset in range(-1, 2):
            idx = (self.position + offset) % len(self.strip)
            result.append(self.strip[idx])
        return result

    def get_payline(self) -> str:
        return self.strip[self.position % len(self.strip)]

    def spin(self, target_symbol: str, delay_ms: int):
        self.spinning = True
        self.target_symbol = target_symbol
        self.stop_time = time.time() + delay_ms / 1000.0
        self.bounce_phase = 0

    def update(self) -> bool:
        if not self.spinning:
            return False
        self.position = (self.position + 1) % len(self.strip)
        if time.time() >= self.stop_time:
            for i, sym in enumerate(self.strip):
                if sym == self.target_symbol:
                    self.position = i
                    break
            self.spinning = False
            self.bounce_phase = 3
            return True
        return False

    def update_bounce(self) -> bool:
        if self.bounce_phase > 0:
            self.bounce_phase -= 1
            return self.bounce_phase == 0
        return True


# ─── Slot Machine Game ──────────────────────────────────────────────────────

class SlotMachine:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.credits = 100
        self.bet = 1
        self.max_bet = 10
        self.reels = [Reel(i) for i in range(NUM_REELS)]
        self.spinning = False
        self.win_amount = 0
        self.win_lines = []
        self.win_flash_counter = 0
        self.message = "Press SPACE to spin!"
        self.total_spins = 0
        self.total_won = 0
        self.total_bet = 0
        self.history = []
        self.jackpot = False
        self.last_spin_frame = 0

        self._setup_colors()
        self._calc_layout()

    def _setup_colors(self):
        curses.start_color()
        curses.use_default_colors()

        curses.init_pair(CLR_BG,      curses.COLOR_WHITE, 17)
        curses.init_pair(CLR_REEL_BG, curses.COLOR_WHITE, 236)
        curses.init_pair(CLR_BORDER,  curses.COLOR_CYAN,  17)
        curses.init_pair(CLR_WIN,     curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(CLR_CREDIT,  curses.COLOR_GREEN, 17)
        curses.init_pair(CLR_BET,     curses.COLOR_YELLOW, 17)
        curses.init_pair(CLR_DIM,     curses.COLOR_WHITE, 240)
        curses.init_pair(CLR_JACKPOT, curses.COLOR_RED,   curses.COLOR_YELLOW)
        curses.init_pair(CLR_TITLE,   curses.COLOR_YELLOW, curses.COLOR_RED)

        # Symbol colors on dark reel background
        curses.init_pair(4,  curses.COLOR_RED,    236)     # CHERRY
        curses.init_pair(5,  curses.COLOR_YELLOW, 236)     # LEMON
        curses.init_pair(6,  curses.COLOR_RED,    236)     # ORANGE
        curses.init_pair(7,  curses.COLOR_MAGENTA, 236)    # PLUM
        curses.init_pair(8,  curses.COLOR_YELLOW, 236)     # BELL
        curses.init_pair(9,  curses.COLOR_CYAN,   236)     # BAR
        curses.init_pair(10, curses.COLOR_RED,    236)     # SEVEN
        curses.init_pair(11, curses.COLOR_CYAN,   236)     # DIAMOND

    def _calc_layout(self):
        self.h, self.w = self.stdscr.getmaxyx()
        self.reel_w = 9
        self.reel_art_h = 3   # 3 lines per symbol
        self.reel_h = self.reel_art_h * 3 + 2  # 3 symbols + borders
        self.reel_gap = 5
        total_reel_width = NUM_REELS * self.reel_w + (NUM_REELS - 1) * self.reel_gap
        self.reel_x_start = max(1, (self.w - total_reel_width) // 2)
        self.reel_y_start = max(2, (self.h - 30) // 2)

    def _determine_result(self) -> list:
        return [random.choice(WEIGHTED_REEL) for _ in range(NUM_REELS)]

    def spin(self):
        if self.spinning:
            return
        if self.credits < self.bet:
            self.message = "Not enough credits! Lower your bet."
            return
        self.credits -= self.bet
        self.total_bet += self.bet
        self.total_spins += 1
        self.win_amount = 0
        self.win_lines = []
        self.win_flash_counter = 0
        self.jackpot = False
        self.message = "Spinning..."
        results = self._determine_result()
        for i, reel in enumerate(self.reels):
            reel.spin(results[i], delay_ms=600 + i * 450)
        self.spinning = True

    def check_wins(self):
        grid = []
        for reel in self.reels:
            grid.append(reel.get_visible())

        rows = []
        for row in range(3):
            rows.append([grid[col][row] for col in range(NUM_REELS)])

        wins = []

        # 3-of-a-kind checks for 5 paylines
        payline_checks = [
            (1, rows[1]),                    # middle row
            (0, rows[0]),                    # top row
            (2, rows[2]),                    # bottom row
            (3, [rows[0][0], rows[1][1], rows[2][2]]),  # diagonal \
            (4, [rows[2][0], rows[1][1], rows[0][2]]),  # diagonal /
        ]

        for line_id, line_syms in payline_checks:
            if line_syms[0] == line_syms[1] == line_syms[2]:
                mult = SYMBOL_PAYOUTS[line_syms[0]]
                wins.append((line_id, line_syms[0], mult))

        # 2-of-a-kind on payline (small win)
        mid = rows[1]
        if mid[0] == mid[1] or mid[1] == mid[2]:
            if not (mid[0] == mid[1] == mid[2]):
                sym = mid[1]
                small_mult = max(1, SYMBOL_PAYOUTS[sym] // 5)
                wins.append((1, sym, small_mult))

        total_win = sum(mult * self.bet for _, sym, mult in wins)

        if total_win > 0:
            self.win_amount = total_win
            self.credits += total_win
            self.total_won += total_win
            self.win_lines = wins
            self.win_flash_counter = 24

            payline = [reel.get_payline() for reel in self.reels]
            if payline[0] == payline[1] == payline[2] == "DIAMOND":
                self.jackpot = True
                self.message = f"JACKPOT! +{total_win} credits!"
            else:
                self.message = f"WIN! +{total_win} credits!"
        else:
            self.message = "No win. Spin again!"

        payline_syms = [reel.get_payline() for reel in self.reels]
        self.history.append((payline_syms[:], total_win))
        if len(self.history) > 10:
            self.history.pop(0)

    def change_bet(self, delta: int):
        if self.spinning:
            return
        new_bet = self.bet + delta
        if 1 <= new_bet <= self.max_bet:
            self.bet = new_bet
            self.message = f"Bet: {self.bet}"

    def draw(self):
        stdscr = self.stdscr
        stdscr.clear()
        h, w = self.h, self.w

        # ─── Title ───
        title = "*** LUCKY TERMINAL SLOTS ***"
        title_x = (w - len(title)) // 2
        if h > 2 and title_x >= 0:
            try:
                stdscr.addstr(0, title_x, title, curses.color_pair(CLR_TITLE) | curses.A_BOLD)
            except curses.error:
                pass

        # ─── Machine Frame ───
        frame_top = self.reel_y_start - 1
        frame_left = self.reel_x_start - 2
        frame_right = self.reel_x_start + NUM_REELS * self.reel_w + (NUM_REELS - 1) * self.reel_gap + 1
        frame_bottom = self.reel_y_start + self.reel_h + 6

        if frame_left >= 0 and frame_right < w:
            border = "+" + "-" * (frame_right - frame_left - 1) + "+"
            try:
                stdscr.addstr(frame_top, frame_left, border, curses.color_pair(CLR_BORDER))
            except curses.error:
                pass
            try:
                stdscr.addstr(frame_bottom, frame_left, border, curses.color_pair(CLR_BORDER))
            except curses.error:
                pass

        for y in range(frame_top + 1, frame_bottom):
            if 0 <= y < h and frame_left >= 0:
                try:
                    stdscr.addstr(y, frame_left, "|", curses.color_pair(CLR_BORDER))
                except curses.error:
                    pass
            if 0 <= y < h and frame_right < w:
                try:
                    stdscr.addstr(y, frame_right, "|", curses.color_pair(CLR_BORDER))
                except curses.error:
                    pass

        # ─── Reels ───
        for i, reel in enumerate(self.reels):
            rx = self.reel_x_start + i * (self.reel_w + self.reel_gap)
            ry = self.reel_y_start

            visible = reel.get_visible()
            bounce = 0
            if reel.bounce_phase > 0:
                bounce = 1 if reel.bounce_phase in (3, 1) else -1

            # Reel top border
            try:
                stdscr.addstr(ry, rx - 1, "+" + "-" * self.reel_w + "+",
                              curses.color_pair(CLR_BORDER))
            except curses.error:
                pass

            # Draw 3 visible symbols (each 3 lines tall)
            for sym_idx in range(3):
                sym_name = visible[sym_idx]
                art = SYMBOL_ART[sym_name]
                sym_clr = SYMBOL_CLRS.get(sym_name, CLR_REEL_BG)

                is_win = False
                if self.win_flash_counter > 0 and not self.spinning:
                    for win_row, _, _ in self.win_lines:
                        if win_row == sym_idx:
                            is_win = True
                            break

                for art_line in range(3):
                    y_pos = ry + 1 + sym_idx * self.reel_art_h + art_line + bounce
                    if 0 <= y_pos < h:
                        if is_win and self.win_flash_counter % 4 < 2:
                            color = curses.color_pair(CLR_WIN) | curses.A_BOLD
                        else:
                            color = curses.color_pair(sym_clr)

                        line_str = f" {art[art_line]} "
                        line_str = line_str.center(self.reel_w)
                        try:
                            stdscr.addstr(y_pos, rx, line_str, color)
                        except curses.error:
                            pass

            # Separator lines between symbols
            for sep in range(1, 3):
                y_sep = ry + 1 + sep * self.reel_art_h
                if 0 <= y_sep < h:
                    try:
                        stdscr.addstr(y_sep, rx - 1, "|" + "-" * self.reel_w + "|",
                                      curses.color_pair(CLR_BORDER))
                    except curses.error:
                        pass

            # Bottom border
            y_bot = ry + 1 + 3 * self.reel_art_h
            if 0 <= y_bot < h:
                try:
                    stdscr.addstr(y_bot, rx - 1, "+" + "-" * self.reel_w + "+",
                                  curses.color_pair(CLR_BORDER))
                except curses.error:
                    pass

            # Payline arrows
            payline_y = ry + 1 + 1 * self.reel_art_h + 1 + bounce  # middle of middle symbol
            if 0 <= payline_y < h:
                try:
                    stdscr.addstr(payline_y, rx - 2, ">>", curses.color_pair(CLR_WIN) | curses.A_BOLD)
                except curses.error:
                    pass
                end_x = rx + self.reel_w + 1
                if end_x + 1 < w:
                    try:
                        stdscr.addstr(payline_y, end_x, "<<", curses.color_pair(CLR_WIN) | curses.A_BOLD)
                    except curses.error:
                        pass

        # ─── Info Panel ───
        info_y = self.reel_y_start + self.reel_h + 2

        credit_str = f"CREDITS: {self.credits:>5}"
        try:
            stdscr.addstr(info_y, self.reel_x_start, credit_str,
                          curses.color_pair(CLR_CREDIT) | curses.A_BOLD)
        except curses.error:
            pass

        bet_str = f"BET: {self.bet:>2}"
        try:
            stdscr.addstr(info_y, self.reel_x_start + 20, bet_str,
                          curses.color_pair(CLR_BET) | curses.A_BOLD)
        except curses.error:
            pass

        if self.win_amount > 0:
            win_str = f"WIN: {self.win_amount:>5}"
            color = curses.color_pair(CLR_JACKPOT) if self.jackpot else curses.color_pair(CLR_WIN)
            try:
                stdscr.addstr(info_y, self.reel_x_start + 30, win_str, color | curses.A_BOLD)
            except curses.error:
                pass

        # ─── Message ───
        msg_y = info_y + 1
        try:
            if self.jackpot and self.win_flash_counter > 0:
                stdscr.addstr(msg_y, self.reel_x_start, self.message,
                              curses.color_pair(CLR_JACKPOT) | curses.A_BOLD)
            elif self.win_amount > 0 and self.win_flash_counter > 0:
                stdscr.addstr(msg_y, self.reel_x_start, self.message,
                              curses.color_pair(CLR_WIN) | curses.A_BOLD)
            else:
                stdscr.addstr(msg_y, self.reel_x_start, self.message,
                              curses.color_pair(CLR_BORDER))
        except curses.error:
            pass

        # ─── Controls ───
        ctrl_y = msg_y + 1
        controls = "[SPACE] Spin  [Up/Down] Bet  [q] Quit"
        try:
            stdscr.addstr(ctrl_y, self.reel_x_start, controls, curses.color_pair(CLR_DIM))
        except curses.error:
            pass

        # ─── Pay Table ───
        pay_y = ctrl_y + 2
        try:
            stdscr.addstr(pay_y, self.reel_x_start, "--- PAY TABLE (xbet) ---",
                          curses.color_pair(CLR_BORDER))
        except curses.error:
            pass

        for idx, (name, art, payout, _, clr) in enumerate(SYMBOLS):
            row_y = pay_y + 1 + idx
            line = f" {art[1]} x3  {name:<8} x{payout:>3}"
            try:
                stdscr.addstr(row_y, self.reel_x_start, line, curses.color_pair(clr))
            except curses.error:
                pass

        # ─── Stats ───
        stats_y = pay_y + 1 + len(SYMBOLS) + 1
        if self.total_spins > 0:
            payback = (self.total_won / self.total_bet * 100) if self.total_bet > 0 else 0
            stats = f"Spins:{self.total_spins} Won:{self.total_won} Payback:{payback:.1f}%"
            try:
                stdscr.addstr(stats_y, self.reel_x_start, stats, curses.color_pair(CLR_DIM))
            except curses.error:
                pass

        # ─── Jackpot Flash ───
        if self.jackpot and self.win_flash_counter > 0 and self.win_flash_counter % 3 == 0:
            for y in range(0, h, 3):
                try:
                    stdscr.addstr(y, 0, " " * w, curses.color_pair(CLR_JACKPOT))
                except curses.error:
                    pass

        stdscr.refresh()

    def update(self):
        if self.spinning:
            for reel in self.reels:
                reel.update()
                if not reel.spinning and reel.bounce_phase > 0:
                    reel.update_bounce()

            if all(not reel.spinning for reel in self.reels):
                if all(reel.bounce_phase == 0 for reel in self.reels):
                    self.spinning = False
                    self.check_wins()

        if self.win_flash_counter > 0:
            self.win_flash_counter -= 1


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(60)

    game = SlotMachine(stdscr)

    while True:
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
        elif key == ord('q') or key == ord('Q'):
            break

        game.update()
        game.draw()

    # Game Over
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    lines = [
        "Thanks for playing!",
        "",
        f"Final Credits: {game.credits}",
        f"Total Spins:   {game.total_spins}",
        f"Total Won:     {game.total_won}",
        f"Total Bet:     {game.total_bet}",
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


if __name__ == "__main__":
    curses.wrapper(main)