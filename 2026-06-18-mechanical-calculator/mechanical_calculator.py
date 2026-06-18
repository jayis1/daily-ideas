#!/usr/bin/env python3
"""
Terminal Mechanical Calculator
===============================
A simulation of a vintage mechanical calculator (inspired by the Curta Type II)
with visible gear mechanisms, carry propagation, and animated operations in ASCII.

The Curta was a remarkable hand-cranked mechanical calculator invented by
Curt Herzstark in 1943. This simulation recreates the experience of using one,
showing the setting sliders, result dial, counter dial, and the internal gear
mechanism as operations are cranked through.
"""

import sys
import time
import argparse
import shutil
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ─── ANSI Helpers ──────────────────────────────────────────────────────────────

def esc(code: str) -> str:
    return f"\033[{code}"

def move_cursor(row: int, col: int) -> str:
    return esc(f"{row};{col}H")

def clear_screen() -> str:
    return esc("2J") + esc("H")

def bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"

def dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"

def colored(text: str, color: str) -> str:
    colors = {
        "red": "31", "green": "32", "yellow": "33", "blue": "34",
        "magenta": "35", "cyan": "36", "white": "37",
        "bright_red": "91", "bright_green": "92", "bright_yellow": "93",
        "bright_blue": "94", "bright_magenta": "95", "bright_cyan": "96",
    }
    c = colors.get(color, "37")
    return f"\033[{c}m{text}\033[0m"

def bg_colored(text: str, color: str) -> str:
    bgs = {
        "red": "41", "green": "42", "yellow": "43", "blue": "44",
        "magenta": "45", "cyan": "46", "white": "47",
    }
    b = bgs.get(color, "47")
    return f"\033[{b}m{text}\033[0m"


# ─── Gear Drawing ──────────────────────────────────────────────────────────────

GEAR_FRAMES = [
    # 7x7 gear frames rotating through positions
    [
        "  ╱─╲ ",
        "╱│ ● │╲",
        "╲│   │╱",
        "  ╲─╱ ",
    ],
    [
        "  ╱─╲ ",
        "╱│ ● │╲",
        "╲│   │╱",
        "  ╲─╱ ",
    ],
    [
        " ┌──┐ ",
        "│ ●  │",
        "│    │",
        " └──┘ ",
    ],
    [
        "  ╱─╲ ",
        "╱│ ● │╲",
        "╲│   │╱",
        "  ╲─╱ ",
    ],
    [
        "  ╱─╲ ",
        "╱│ ● │╲",
        "╲│   │╱",
        "  ╲─╱ ",
    ],
    [
        " ┌──┐ ",
        "│  ● │",
        "│    │",
        " └──┘ ",
    ],
]


# ─── Core Calculator ───────────────────────────────────────────────────────────

@dataclass
class MechanicalCalculator:
    """
    Simulates a Curta Type II mechanical calculator.

    Registers:
      - setting: 11 digits, the number you set on the sliders (multiplicand)
      - counter:  8 digits, revolution counter (multiplier)
      - result:  15 digits, accumulator (product / sum)

    Operations:
      - crank:  add setting to result, increment counter
      - crank_reverse: subtract setting from result, decrement counter
      - clear:  zero out registers
    """
    setting: List[int] = field(default_factory=lambda: [0] * 11)
    counter: List[int] = field(default_factory=lambda: [0] * 8)
    result: List[int] = field(default_factory=lambda: [0] * 15)
    carriage_pos: int = 0          # 0–8, shifts setting left by this many places
    crank_angle: int = 0            # animation state for the crank
    carry_queue: List[Tuple[int, int]] = field(default_factory=list)
    operation_log: List[str] = field(default_factory=list)

    # ── Setting ────────────────────────────────────────────────────────────

    def set_digit(self, position: int, value: int):
        """Set a digit on the input slider (position 0=units, 10=highest)."""
        if 0 <= position < 11 and 0 <= value <= 9:
            self.setting[position] = value
            self.operation_log.append(f"Set pos {position} → {value}")

    def set_number(self, n: int):
        """Set the setting register to an integer."""
        n = abs(n)
        self.setting = [0] * 11
        s = str(n).zfill(11)
        for i in range(11):
            self.setting[i] = int(s[11 - 1 - i])

    # ── Carriage ───────────────────────────────────────────────────────────

    def set_carriage(self, pos: int):
        """Move the carriage to position 0–8 (shifts setting by 10^pos)."""
        if 0 <= pos <= 8:
            self.carriage_pos = pos
            self.operation_log.append(f"Carriage → pos {pos}")

    # ── Add / Subtract with Carry ───────────────────────────────────────────

    def _add_to_result(self, value: int, subtract: bool = False):
        """Add (or subtract) a value to the result register with carry propagation."""
        self.carry_queue = []
        current = self.read_result()
        if subtract:
            new_val = current - value
        else:
            new_val = current + value
        # Clamp to 15-digit range (0 to 999999999999999)
        if new_val < 0:
            new_val = 0  # On a real Curta, result can't go negative
        if new_val > 999999999999999:
            new_val = 999999999999999
        s = str(new_val).zfill(15)[-15:]
        for i in range(15):
            old_digit = self.result[i]
            new_digit = int(s[14 - i])
            if old_digit != new_digit:
                self.carry_queue.append((i, True))
            self.result[i] = new_digit

    def _add_to_counter(self, value: int = 1, subtract: bool = False):
        """Increment (or decrement) the counter register."""
        # Simple approach: read counter as int, modify, write back
        current = self.read_counter()
        if subtract:
            new_val = current - value
        else:
            new_val = current + value
        # Write back
        if new_val < 0:
            # Counter can't go negative on a real Curta; wrap around
            # But for our purposes, we store the absolute value and note sign separately
            new_val = new_val & ((1 << 32) - 1)  # allow large unsigned
        s = str(abs(new_val)).zfill(8)[-8:]
        for i in range(8):
            self.counter[i] = int(s[7 - i])

    # ── Crank Operations ───────────────────────────────────────────────────

    def crank(self, times: int = 1):
        """Crank forward: add setting * 10^carriage_pos to result, times times."""
        for _ in range(times):
            shifted_value = self._shifted_setting_value()
            self._add_to_result(shifted_value, subtract=False)
            self._add_to_counter(1, subtract=False)
            self.crank_angle = (self.crank_angle + 1) % 6
            val = shifted_value
            self.operation_log.append(f"Crank +{val}")

    def crank_reverse(self, times: int = 1):
        """Crank in reverse: subtract setting * 10^carriage_pos from result."""
        for _ in range(times):
            shifted_value = self._shifted_setting_value()
            self._add_to_result(shifted_value, subtract=True)
            self._add_to_counter(1, subtract=True)
            self.crank_angle = (self.crank_angle + 1) % 6
            val = shifted_value
            self.operation_log.append(f"Crank -{val}")

    def _shifted_setting_value(self) -> int:
        """Compute setting * 10^carriage_pos as an integer."""
        value = 0
        for i in range(11):
            value += self.setting[i] * (10 ** i)
        return value * (10 ** self.carriage_pos)

    # ── Clear ──────────────────────────────────────────────────────────────

    def clear_result(self):
        self.result = [0] * 15
        self.operation_log.append("Clear result")

    def clear_counter(self):
        self.counter = [0] * 8
        self.operation_log.append("Clear counter")

    def clear_all(self):
        self.setting = [0] * 11
        self.counter = [0] * 8
        self.result = [0] * 15
        self.carriage_pos = 0
        self.operation_log.append("Clear all")

    # ── Read Registers ────────────────────────────────────────────────────

    def read_setting(self) -> int:
        value = 0
        for i in range(11):
            value += self.setting[i] * (10 ** i)
        return value

    def read_counter(self) -> int:
        value = 0
        for i in range(8):
            value += self.counter[i] * (10 ** i)
        return value

    def read_result(self) -> int:
        value = 0
        for i in range(15):
            value += self.result[i] * (10 ** i)
        return value


# ─── Display ───────────────────────────────────────────────────────────────────

class CalculatorDisplay:
    """Renders the mechanical calculator in the terminal with animations."""

    def __init__(self, calc: MechanicalCalculator):
        self.calc = calc
        self.term_width = 80
        self.term_height = 36
        self.gear_offset = 0
        self.last_log_count = 0

    def _center(self, text: str, width: int = None) -> str:
        w = width or self.term_width
        return text.center(w)

    def _draw_frame(self, top: str, bottom: str) -> str:
        return f"╔{top}╗\n║{bottom}║\n╚{bottom[:1]}{'═'*(len(top)-2)}{bottom[-1:] if len(bottom)>0 else ''}╝"

    def render_header(self) -> str:
        lines = []
        lines.append(colored("╔══════════════════════════════════════════════════════════════════════════╗", "bright_cyan"))
        lines.append(colored("║", "bright_cyan") + bold("           ⚙  CURTA TYPE II — MECHANICAL CALCULATOR  ⚙           ".center(72)) + colored("║", "bright_cyan"))
        lines.append(colored("║", "bright_cyan") + dim("    Inspired by Curt Herzstark's masterpiece (1948)                ".center(72)) + colored("║", "bright_cyan"))
        lines.append(colored("╚══════════════════════════════════════════════════════════════════════════╝", "bright_cyan"))
        return "\n".join(lines)

    def render_setting_sliders(self) -> str:
        """Render the 11 setting sliders with their current values."""
        calc = self.calc
        lines = []
        lines.append(colored(" ┌─ SETTING REGISTER (input sliders) ─────────────────────────────────┐", "yellow"))
        
        # Position labels (reversed for display: highest on left)
        pos_labels = []
        for i in range(10, -1, -1):
            pos_labels.append(f"{i:2d}")
        lines.append(colored(" │ ", "yellow") + "  ".join(pos_labels) + colored("  │", "yellow"))
        lines.append(colored(" │ ", "yellow") + "───".join(["╺" if calc.setting[i] > 0 else "╌" for i in range(10, -1, -1)]) + colored("  │", "yellow"))

        # Slider values
        digits = []
        for i in range(10, -1, -1):
            v = calc.setting[i]
            if v > 0:
                digits.append(colored(f" {v} ", "bright_green"))
            else:
                digits.append(dim(f" {v} "))
        lines.append(colored(" │ ", "yellow") + "".join(digits) + colored(" │", "yellow"))
        lines.append(colored(" │ ", "yellow") + "───".join(["╺" if calc.setting[i] > 0 else "╌" for i in range(10, -1, -1)]) + colored("  │", "yellow"))
        lines.append(colored(" └────────────────────────────────────────────────────────────────────┘", "yellow"))
        return "\n".join(lines)

    def render_carriage(self) -> str:
        """Render the carriage position indicator."""
        calc = self.calc
        lines = []
        lines.append(colored(" ┌─ CARRIAGE POSITION ────────────────────────────────────────────────┐", "magenta"))
        pos_str = ""
        for i in range(9):
            if i == calc.carriage_pos:
                pos_str += colored(f" ▶{i} ", "bright_magenta")
            else:
                pos_str += dim(f"  {i} ")
            if i < 8:
                pos_str += "│"
        lines.append(colored(" │ ", "magenta") + pos_str + colored("  │", "magenta"))
        shift_desc = f"× 10^{calc.carriage_pos}" if calc.carriage_pos > 0 else "× 1"
        lines.append(colored(" │ ", "magenta") + f"Shift: {shift_desc}".ljust(66) + colored("│", "magenta"))
        lines.append(colored(" └────────────────────────────────────────────────────────────────────┘", "magenta"))
        return "\n".join(lines)

    def render_dials(self) -> str:
        """Render the result and counter dials side by side."""
        calc = self.calc

        lines = []
        lines.append(colored(" ┌─ RESULT DIAL ────────────────────────────────────┐", "bright_cyan") + 
                     colored(" ┌─ COUNTER DIAL ──────────────────────────┐", "green"))
        
        # Result digits (15 digits)
        result_digits = []
        for i in range(14, -1, -1):
            v = calc.result[i]
            if v != 0:
                result_digits.append(colored(f"{v}", "bright_cyan"))
            else:
                result_digits.append(dim("0"))

        # Counter digits (8 digits)
        counter_digits = []
        for i in range(7, -1, -1):
            v = calc.counter[i]
            if v != 0:
                counter_digits.append(colored(f"{v}", "bright_green"))
            else:
                counter_digits.append(dim("0"))

        # Format result as groups
        result_str = ""
        for idx, d in enumerate(result_digits):
            if idx > 0 and (15 - idx) % 3 == 0:
                result_str += dim("│")
            result_str += d

        counter_str = ""
        for idx, d in enumerate(counter_digits):
            if idx > 0 and (8 - idx) % 3 == 0:
                counter_str += dim("│")
            counter_str += d

        lines.append(colored(" │ ", "bright_cyan") + result_str.ljust(50) + colored("│", "bright_cyan") +
                     colored(" │ ", "green") + counter_str.ljust(40) + colored("│", "green"))
        
        # Numeric values
        lines.append(colored(" │ ", "bright_cyan") + colored(f"= {calc.read_result():>15}", "white").ljust(50) + colored("│", "bright_cyan") +
                     colored(" │ ", "green") + colored(f"= {calc.read_counter():>8}", "white").ljust(40) + colored("│", "green"))

        lines.append(colored(" └────────────────────────────────────────────────────┘", "bright_cyan") + 
                     colored(" └──────────────────────────────────────────┘", "green"))
        return "\n".join(lines)

    def render_gears(self) -> str:
        """Render animated gear mechanisms."""
        calc = self.calc
        angle = calc.crank_angle
        
        gear_lines = ["", "", "", ""]
        for i in range(5):
            a = (angle + i) % len(GEAR_FRAMES)
            frame = GEAR_FRAMES[a % len(GEAR_FRAMES)]
            for j, line in enumerate(frame):
                if i < 2 or (i >= 2 and calc.carriage_pos > 0):
                    if calc.setting[i if i < 2 else i - 2 + calc.carriage_pos] > 0:
                        gear_lines[j] += colored(line, "bright_yellow")
                    else:
                        gear_lines[j] += dim(line)
                else:
                    gear_lines[j] += dim(line)
                gear_lines[j] += " "

        lines = []
        lines.append(colored(" ┌─ GEAR MECHANISM ─────────────────────────────────┐", "yellow"))
        for gl in gear_lines:
            lines.append(colored(" │ ", "yellow") + gl.ljust(50) + colored("│", "yellow"))
        
        # Crank handle
        crank_chars = ["⬆", "⬈", "⬅", "⬋", "⬇", "⬊"]
        crank = crank_chars[angle % len(crank_chars)]
        lines.append(colored(" │ ", "yellow") + f"Crank: {colored(crank, 'bright_white')}   Turns: {calc.read_counter()}".ljust(50) + colored("│", "yellow"))
        lines.append(colored(" └────────────────────────────────────────────────────┘", "yellow"))
        return "\n".join(lines)

    def render_log(self, max_lines: int = 5) -> str:
        """Render the operation log."""
        calc = self.calc
        recent = calc.operation_log[-max_lines:]
        lines = []
        lines.append(colored(" ┌─ OPERATION LOG ───────────────────────────────────┐", "white"))
        for entry in recent:
            lines.append(colored(" │ ", "white") + entry.ljust(50) + colored("│", "white"))
        # Pad remaining lines
        for _ in range(max_lines - len(recent)):
            lines.append(colored(" │ ", "white") + "".ljust(50) + colored("│", "white"))
        lines.append(colored(" └────────────────────────────────────────────────────┘", "white"))
        return "\n".join(lines)

    def render_full(self) -> str:
        """Render the complete calculator display."""
        output = []
        output.append(self.render_header())
        output.append("")
        output.append(self.render_setting_sliders())
        output.append("")
        output.append(self.render_carriage())
        output.append("")
        output.append(self.render_dials())
        output.append("")
        output.append(self.render_gears())
        output.append("")
        output.append(self.render_log())
        return "\n".join(output)

    def render_compact(self) -> str:
        """Render a compact view for animation frames."""
        calc = self.calc
        setting_val = calc.read_setting()
        counter_val = calc.read_counter()
        result_val = calc.read_result()

        lines = []
        # Header
        lines.append(colored("╔═══ CURTA TYPE II ═══╗", "bright_cyan"))
        lines.append(colored("║ ", "bright_cyan") + f"Set:  {setting_val:>11}".ljust(18) + colored("║", "bright_cyan"))
        lines.append(colored("║ ", "bright_cyan") + f"×10^{calc.carriage_pos}" if calc.carriage_pos > 0 else colored("║ ", "bright_cyan") + f"× 1 ".ljust(18) + colored("║", "bright_cyan"))
        lines.append(colored("║ ", "bright_cyan") + f"Cnt:  {counter_val:>11}".ljust(18) + colored("║", "bright_cyan"))
        lines.append(colored("║ ", "bright_cyan") + colored(f"Res:  {result_val:>11}", "bright_white").ljust(38) + colored("║", "bright_cyan"))
        lines.append(colored("╚═════════════════════╝", "bright_cyan"))
        return "\n".join(lines)


# ─── Interactive Mode ──────────────────────────────────────────────────────────

def interactive_mode(calc: MechanicalCalculator, display: CalculatorDisplay, speed: float):
    """Run the calculator in interactive terminal mode."""
    print(clear_screen())
    print(esc("?25l"))  # Hide cursor
    
    try:
        while True:
            # Render
            print(esc("H") + display.render_full())
            print()
            print(colored(" Commands: ", "bright_white") + colored("[s]et  [c]rank  [r]everse  [p]osition  [C]lear  [q]uit", "white"))
            print(colored("           ", "bright_white") + colored("[m]ultiply  [d]ivide  [a]dd  [b]subtract  [+]  [-]", "white"))
            
            try:
                cmd = input(colored(" > ", "bright_cyan")).strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            
            if not cmd:
                continue
            
            parts = cmd.split()
            action = parts[0]
            
            if action == 'q':
                break
            elif action == 's':
                # Set a number
                if len(parts) >= 2:
                    try:
                        num = int(parts[1])
                        calc.set_number(num)
                    except ValueError:
                        calc.operation_log.append("Error: invalid number")
                else:
                    calc.operation_log.append("Usage: s <number>")
            elif action == 'c':
                # Crank forward
                times = int(parts[1]) if len(parts) >= 2 else 1
                animate_crank(calc, display, times, reverse=False, speed=speed)
            elif action == 'r':
                # Crank reverse
                times = int(parts[1]) if len(parts) >= 2 else 1
                animate_crank(calc, display, times, reverse=True, speed=speed)
            elif action == 'p':
                # Set carriage position
                if len(parts) >= 2:
                    try:
                        pos = int(parts[1])
                        calc.set_carriage(pos)
                    except ValueError:
                        calc.operation_log.append("Error: invalid position")
                else:
                    calc.operation_log.append("Usage: p <position 0-8>")
            elif action == 'C':
                # Clear
                if len(parts) >= 2 and parts[1] == 'all':
                    calc.clear_all()
                elif len(parts) >= 2 and parts[1] == 'counter':
                    calc.clear_counter()
                else:
                    calc.clear_result()
                    calc.clear_counter()
            elif action == '+':
                # Quick add
                if len(parts) >= 2:
                    try:
                        num = int(parts[1])
                        calc.set_number(num)
                        animate_crank(calc, display, 1, reverse=False, speed=speed)
                    except ValueError:
                        calc.operation_log.append("Error: invalid number")
            elif action == '-':
                # Quick subtract
                if len(parts) >= 2:
                    try:
                        num = int(parts[1])
                        calc.set_number(num)
                        animate_crank(calc, display, 1, reverse=True, speed=speed)
                    except ValueError:
                        calc.operation_log.append("Error: invalid number")
            elif action == 'm':
                # Multiply: set number, then crank at different positions
                if len(parts) >= 2:
                    try:
                        num = int(parts[1])
                        calc.set_number(num)
                        # Simple: just crank 1 time at position 0
                        calc.clear_counter()
                        animate_crank(calc, display, 1, reverse=False, speed=speed)
                    except ValueError:
                        calc.operation_log.append("Error: invalid number")
                else:
                    calc.operation_log.append("Usage: m <number>")
            elif action == 'a':
                # Add number to result
                if len(parts) >= 2:
                    try:
                        num = int(parts[1])
                        calc.set_number(num)
                        animate_crank(calc, display, 1, reverse=False, speed=speed)
                    except ValueError:
                        calc.operation_log.append("Error: invalid number")
            elif action == 'b':
                # Subtract number from result
                if len(parts) >= 2:
                    try:
                        num = int(parts[1])
                        calc.set_number(num)
                        animate_crank(calc, display, 1, reverse=True, speed=speed)
                    except ValueError:
                        calc.operation_log.append("Error: invalid number")
            elif action == 'd':
                # Demo division
                calc.operation_log.append("Division: use reverse cranks at positions")
            elif action == 'h':
                calc.operation_log.append("s=N c=N r=N p=N C m d +/- help")
    finally:
        print(esc("?25h"))  # Show cursor
        print(clear_screen())
        print("Goodbye! The Curta rests.")


def animate_crank(calc: MechanicalCalculator, display: CalculatorDisplay, times: int, reverse: bool, speed: float):
    """Animate a crank operation with visible gear rotation."""
    for step in range(times):
        # Animate the crank rotation
        for frame in range(6):
            calc.crank_angle = (calc.crank_angle + 1) % 6
            print(esc("H") + display.render_full())
            print(colored(f"  Cranking... {'◀ reverse' if reverse else '▶ forward'} {step+1}/{times}", "bright_yellow"))
            time.sleep(speed * 0.05)
        
        # Perform the actual operation
        if reverse:
            calc.crank_reverse(1)
        else:
            calc.crank(1)
        
        print(esc("H") + display.render_full())
        time.sleep(speed * 0.1)


# ─── Demo Mode ─────────────────────────────────────────────────────────────────

def run_demo(calc: MechanicalCalculator, display: CalculatorDisplay, speed: float):
    """Run a self-playing demonstration of the calculator."""
    print(clear_screen())
    print(esc("?25l"))
    
    try:
        # Demo 1: Addition
        print(esc("H") + display.render_full())
        print(colored("\n  🎬 Demo 1: Addition — 4287 + 3156", "bright_yellow"))
        time.sleep(speed * 0.5)
        
        calc.set_number(4287)
        print(esc("H") + display.render_full())
        print(colored(f"\n  Set 4287 on the sliders...", "bright_yellow"))
        time.sleep(speed * 0.8)
        
        animate_crank(calc, display, 1, reverse=False, speed=speed)
        print(colored(f"\n  Crank forward → Result = {calc.read_result()}", "bright_green"))
        time.sleep(speed * 0.5)
        
        calc.set_number(3156)
        print(esc("H") + display.render_full())
        print(colored(f"\n  Set 3156 on the sliders...", "bright_yellow"))
        time.sleep(speed * 0.8)
        
        animate_crank(calc, display, 1, reverse=False, speed=speed)
        print(colored(f"\n  Crank forward → Result = {calc.read_result()}", "bright_green"))
        time.sleep(speed * 1.0)
        
        # Demo 2: Multiplication
        calc.clear_all()
        print(colored("\n  🎬 Demo 2: Multiplication — 123 × 456", "bright_yellow"))
        time.sleep(speed * 0.5)
        
        calc.set_number(123)
        print(esc("H") + display.render_full())
        print(colored(f"\n  Set 123 on the sliders...", "bright_yellow"))
        time.sleep(speed * 0.8)
        
        # Multiply by 456: crank 6 times at pos 0, 5 at pos 1, 4 at pos 2
        calc.set_carriage(0)
        print(esc("H") + display.render_full())
        print(colored(f"\n  Carriage at position 0 — cranking 6 times for 6×1", "bright_yellow"))
        time.sleep(speed * 0.5)
        animate_crank(calc, display, 6, reverse=False, speed=speed)
        print(colored(f"\n  Counter = {calc.read_counter()}, Result = {calc.read_result()}", "bright_green"))
        time.sleep(speed * 0.5)
        
        calc.set_carriage(1)
        calc.clear_counter()
        print(esc("H") + display.render_full())
        print(colored(f"\n  Carriage at position 1 — cranking 5 times for 5×10", "bright_yellow"))
        time.sleep(speed * 0.5)
        animate_crank(calc, display, 5, reverse=False, speed=speed)
        print(colored(f"\n  Result so far = {calc.read_result()}", "bright_green"))
        time.sleep(speed * 0.5)
        
        calc.set_carriage(2)
        calc.clear_counter()
        print(esc("H") + display.render_full())
        print(colored(f"\n  Carriage at position 2 — cranking 4 times for 4×100", "bright_yellow"))
        time.sleep(speed * 0.5)
        animate_crank(calc, display, 4, reverse=False, speed=speed)
        print(colored(f"\n  123 × 456 = {calc.read_result()}", "bright_green"))
        time.sleep(speed * 1.0)
        
        # Demo 3: Subtraction
        calc.clear_all()
        print(colored("\n  🎬 Demo 3: Subtraction — 9000 - 3456", "bright_yellow"))
        time.sleep(speed * 0.5)
        
        calc.set_number(9000)
        print(esc("H") + display.render_full())
        print(colored(f"\n  Set 9000 and crank forward...", "bright_yellow"))
        time.sleep(speed * 0.5)
        animate_crank(calc, display, 1, reverse=False, speed=speed)
        print(colored(f"\n  Result = {calc.read_result()}", "bright_green"))
        time.sleep(speed * 0.5)
        
        calc.set_number(3456)
        print(esc("H") + display.render_full())
        print(colored(f"\n  Set 3456 and crank in reverse...", "bright_yellow"))
        time.sleep(speed * 0.5)
        animate_crank(calc, display, 1, reverse=True, speed=speed)
        print(colored(f"\n  9000 - 3456 = {calc.read_result()}", "bright_green"))
        time.sleep(speed * 1.5)
        
    finally:
        print(esc("?25h"))
        print(clear_screen())
        print(bold("  ⚙ Curta Type II Mechanical Calculator Demo Complete! ⚙"))
        print()
        print(colored("  Run with --interactive to use the calculator yourself.", "bright_cyan"))
        print()


# ─── Batch Mode ────────────────────────────────────────────────────────────────

def run_batch(calc: MechanicalCalculator, display: CalculatorDisplay, operations: List[str]):
    """Execute a sequence of operations in batch mode."""
    for op in operations:
        parts = op.split(":")
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "set":
            calc.set_number(int(args[0]))
        elif cmd == "crank":
            times = int(args[0]) if args else 1
            calc.crank(times)
        elif cmd == "reverse":
            times = int(args[0]) if args else 1
            calc.crank_reverse(times)
        elif cmd == "position":
            calc.set_carriage(int(args[0]))
        elif cmd == "clear":
            if args and args[0] == "all":
                calc.clear_all()
            elif args and args[0] == "counter":
                calc.clear_counter()
            else:
                calc.clear_result()
                calc.clear_counter()
        elif cmd == "add":
            calc.set_number(int(args[0]))
            calc.crank(1)
        elif cmd == "sub":
            calc.set_number(int(args[0]))
            calc.crank_reverse(1)
        elif cmd == "multiply":
            # multiply:a:b — compute a*b
            a = int(args[0])
            b = int(args[1])
            calc.set_number(a)
            calc.crank(b)
        elif cmd == "wait":
            time.sleep(float(args[0]) if args else 1.0)


# ─── Non-Interactive Display ───────────────────────────────────────────────────

def print_result(calc: MechanicalCalculator, display: CalculatorDisplay):
    """Print the calculator state in a nice format for non-interactive mode."""
    print(display.render_full())
    print()
    print(colored("  Setting:  ", "bright_cyan") + f"{calc.read_setting()}")
    print(colored("  Carriage: ", "bright_cyan") + f"position {calc.carriage_pos} (×10^{calc.carriage_pos})")
    print(colored("  Counter:  ", "bright_cyan") + f"{calc.read_counter()}")
    print(colored("  Result:   ", "bright_white") + bold(f"{calc.read_result()}"))
    print()


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Curta Type II Mechanical Calculator Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --demo                    Watch an automated demonstration
  %(prog)s --interactive              Use the calculator interactively
  %(prog)s --add 4287 3156           Compute 4287 + 3156
  %(prog)s --multiply 123 456        Compute 123 × 456
  %(prog)s --subtract 9000 3456      Compute 9000 - 3456
  %(prog)s --batch set:4287,add:4287,add:3156

Interactive commands:
  s <number>   Set number on sliders
  c [times]    Crank forward (default 1)
  r [times]    Crank in reverse
  p <pos>      Set carriage position (0-8)
  C             Clear result & counter
  C all         Clear everything
  + <number>   Quick add
  - <number>   Quick subtract
  q             Quit
        """,
    )
    parser.add_argument("--demo", action="store_true", help="Run automated demo")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--add", nargs=2, type=int, metavar=("A", "B"), help="Add A + B")
    parser.add_argument("--multiply", nargs=2, type=int, metavar=("A", "B"), help="Multiply A × B")
    parser.add_argument("--subtract", nargs=2, type=int, metavar=("A", "B"), help="Subtract A - B")
    parser.add_argument("--divide", nargs=2, type=int, metavar=("A", "B"), help="Divide A ÷ B (integer)")
    parser.add_argument("--batch", nargs="+", help="Batch operations (set:N,add:N,crank:N,etc)")
    parser.add_argument("--speed", type=float, default=1.0, help="Animation speed multiplier (default 1.0)")
    parser.add_argument("--no-animate", action="store_true", help="Skip animations")
    
    args = parser.parse_args()
    
    calc = MechanicalCalculator()
    display = CalculatorDisplay(calc)
    speed = args.speed if args.speed > 0 else 1.0
    
    if args.demo:
        run_demo(calc, display, speed)
    elif args.interactive:
        interactive_mode(calc, display, speed)
    elif args.add:
        a, b = args.add
        calc.set_number(a)
        calc.crank(1)
        calc.set_number(b)
        calc.crank(1)
        print_result(calc, display)
    elif args.multiply:
        a, b = args.multiply
        calc.set_number(a)
        # Simple multiplication via repeated addition at shifted positions
        calc.clear_counter()
        b_str = str(abs(b))
        for idx, digit in enumerate(reversed(b_str)):
            d = int(digit)
            if d > 0:
                calc.set_carriage(idx)
                calc.clear_counter()
                calc.crank(d)
        if b < 0:
            result = calc.read_result()
            calc.clear_all()
            calc.set_number(-result)
            calc.crank(1)
        print_result(calc, display)
    elif args.subtract:
        a, b = args.subtract
        calc.set_number(a)
        calc.crank(1)
        calc.set_number(b)
        calc.crank_reverse(1)
        print_result(calc, display)
    elif args.divide:
        a, b = args.divide
        if b == 0:
            print(colored("Error: Division by zero!", "bright_red"))
            return
        # Integer division using repeated subtraction (how a Curta does it)
        # Load dividend into result
        calc.set_number(a)
        calc.crank(1)
        # Now subtract divisor repeatedly
        divisor = abs(b)
        calc.set_number(divisor)
        quotient = 0
        while calc.read_result() >= divisor:
            # Directly subtract to avoid counter tracking issues
            result = calc.read_result() - divisor
            # Write result back
            s = str(result).zfill(15)[-15:]
            for i in range(15):
                calc.result[i] = int(s[14 - i])
            quotient += 1
        calc.operation_log.append(f"Divided {a} ÷ {b} = {quotient} r {calc.read_result()}")
        print_result(calc, display)
        print(colored(f"  Quotient:  {quotient}", "bright_white"))
        print(colored(f"  Remainder: {calc.read_result()}", "bright_white"))
    elif args.batch:
        run_batch(calc, display, args.batch)
        print_result(calc, display)
    else:
        # Default: show a quick demo then help
        parser.print_help()


if __name__ == "__main__":
    main()