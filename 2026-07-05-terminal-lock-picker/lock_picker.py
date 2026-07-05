#!/usr/bin/env python3
"""
Terminal Lock Picking Simulator
An interactive simulation of picking pin tumbler locks in the terminal.
Feel the tension, set the pins, and hear the click!

Usage:
    python3 lock_picker.py              # Interactive curses mode
    python3 lock_picker.py --help        # Show usage info
    python3 lock_picker.py --version     # Show version
    python3 lock_picker.py --pins 5 --difficulty 3  # Start with specific settings
    python3 lock_picker.py --demo        # Auto-pick demo mode
"""

import argparse
import curses
import json
import os
import random
import sys
import time
import math

# ─── Constants ────────────────────────────────────────────────────────────

VERSION = "1.2.0"

DIFFICULTY_NAMES = ['Novice', 'Easy', 'Medium', 'Hard', 'Master']

MIN_PINS = 2
MAX_PINS = 8

SAVE_FILE = os.path.join(os.path.expanduser("~"), ".lock_picker_stats.json")

# Sound: terminal bell on pin set
ENABLE_BELL = True


# ─── Persistence ──────────────────────────────────────────────────────────

def load_stats():
    """Load persistent stats from disk. Returns dict with best times and totals."""
    try:
        with open(SAVE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "locks_picked": 0,
            "total_time": 0.0,
            "best_times": {},  # key: "pins-difficulty", value: seconds
        }


def save_stats(stats):
    """Save persistent stats to disk."""
    try:
        with open(SAVE_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except OSError:
        pass  # Silently fail if we can't write


# ─── Lock Mechanics ───────────────────────────────────────────────────────

class Pin:
    """A single pin in a pin tumbler lock.

    Attributes:
        key_height: The correct height for this pin (0.0-1.0).
        current_height: Current height of the pin.
        spring_tension: How strongly the spring pushes the pin down (damping).
        is_set: Whether this pin is at the shear line.
        is_bound: Whether this pin is binding against the plug.
        binding_order: Order in which pins bind (lower = binds first).
        wobble: Random wobble factor from manufacturing imperfections.
    """
    def __init__(self, key_height, spring_tension):
        self.key_height = key_height
        self.current_height = 0.0
        self.spring_tension = spring_tension
        self.is_set = False
        self.is_bound = False
        self.binding_order = 0
        self.wobble = 0.0


class Lock:
    """A pin tumbler lock with multiple pins.

    Models realistic pin tumbler lock mechanics including binding order,
    spring tension, wobble, and shear line tolerance.

    Args:
        num_pins: Number of pins (2-8).
        difficulty: Difficulty level 1-5 (Novice to Master).
    """
    PIN_NAMES = ['│', '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']

    def __init__(self, num_pins=5, difficulty=1):
        num_pins = max(MIN_PINS, min(MAX_PINS, num_pins))
        difficulty = max(1, min(5, difficulty))

        self.num_pins = num_pins
        self.difficulty = difficulty
        self.pins = []
        self.tension = 0.0
        self.is_open = False
        self.core_rotation = 0.0
        self.raking_mode = False
        self.pick_health = 1.0  # Pick durability (1.0 = full, 0.0 = broken)

        self._generate_pins()

    @property
    def pins_set_count(self):
        """Number of pins currently set (computed from pin states)."""
        return sum(1 for p in self.pins if p.is_set)

    def _generate_pins(self):
        """Generate random pin heights and binding orders.

        Spring tension is a damping factor that reduces effective lift.
        Higher difficulty means stronger springs, more wobble, and tighter tolerance.
        """
        base_tension = 0.10 + self.difficulty * 0.04
        for i in range(self.num_pins):
            key_height = random.uniform(0.25, 0.85)
            spring_tension = base_tension + random.uniform(-0.03, 0.03)
            pin = Pin(key_height, spring_tension)
            self.pins.append(pin)

        # Assign binding order — randomised manufacturing imperfections
        order = list(range(self.num_pins))
        random.shuffle(order)
        for i, pin in enumerate(self.pins):
            pin.binding_order = order.index(i)

        # Add wobble based on difficulty
        for pin in self.pins:
            pin.wobble = random.uniform(0.001, 0.005) * self.difficulty

    def apply_tension(self, amount):
        """Apply or release tension on the plug.

        Args:
            amount: Tension level (0.0-1.0).
        """
        self.tension = max(0.0, min(1.0, amount))
        self._update_binding()

    def _update_binding(self):
        """Determine which pins are currently binding.

        When tension is applied, manufacturing tolerances cause specific pins
        to bind against the chamber wall. More tension causes more pins to
        bind simultaneously, making them harder to distinguish.
        """
        if self.tension < 0.05:
            for pin in self.pins:
                pin.is_bound = False
            return

        # How many pins bind at once — more tension means more simultaneous binding
        bound_count = max(1, int(self.tension * self.num_pins / 2))

        for pin in self.pins:
            pin.is_bound = False

        # Sort unset pins by binding order — lower order binds first
        unset_pins = [p for p in self.pins if not p.is_set]
        unset_pins.sort(key=lambda p: p.binding_order)

        for pin in unset_pins[:bound_count]:
            pin.is_bound = True

    def lift_pin(self, pin_index, amount):
        """Lift a pin by the given amount.

        Spring tension acts as damping — it reduces effective lift.
        Wobble adds random noise. If a non-bound pin is lifted too high,
        it oversets and snaps back down.

        Args:
            pin_index: Index of the pin to lift.
            amount: How much to lift (positive float).

        Returns:
            True if the pin clicked into place (set), False otherwise.
        """
        if pin_index < 0 or pin_index >= self.num_pins:
            return False

        pin = self.pins[pin_index]

        # Check if pick is broken
        if self.pick_health <= 0:
            return False

        # Spring tension acts as damping
        if pin.is_bound:
            damping = pin.spring_tension * (1.0 - self.tension * 0.2)
        else:
            damping = pin.spring_tension * 0.5

        effective_lift = amount * (1.0 - damping)

        # Add wobble based on difficulty
        wobble = random.gauss(0, pin.wobble) * 3
        effective_lift += wobble

        # Pick wear — each lift slightly damages the pick on Hard/Master
        if self.difficulty >= 4:
            self.pick_health = max(0.0, self.pick_health - 0.0005 * amount)

        new_height = pin.current_height + effective_lift
        new_height = max(0.0, new_height)

        # If pin is not bound, it might overset (go too high and snap back)
        if not pin.is_bound and not pin.is_set and new_height > 0.95:
            new_height = max(0.0, new_height * 0.3)

        pin.current_height = min(1.0, new_height)

        # Check if pin is set (at the shear line = key height)
        tolerance = 0.06 - (self.difficulty * 0.006)
        if pin.is_bound and not pin.is_set and abs(pin.current_height - pin.key_height) < tolerance:
            pin.is_set = True
            pin.current_height = pin.key_height  # Snap to set position
            return True  # Click!

        # If pin was set but we moved it, it might unset
        if pin.is_set and abs(pin.current_height - pin.key_height) > tolerance * 2.5:
            pin.is_set = False

        return False

    def release_pin(self, pin_index):
        """Release a pin — let the spring push it back down.

        Args:
            pin_index: Index of the pin to release.
        """
        if 0 <= pin_index < self.num_pins:
            pin = self.pins[pin_index]
            if pin.is_set:
                return  # Set pins stay
            pin.current_height = max(0.0, pin.current_height - 0.15)

    def check_open(self):
        """Check if all pins are set and the lock can open.

        Returns:
            True if the lock is successfully opened.
        """
        if all(pin.is_set for pin in self.pins) and self.tension >= 0.2:
            self.is_open = True
            return True
        return False

    def rack(self):
        """Attempt to rake the lock — rapidly scrub all pins.

        This has a lower success rate than careful picking, but it's
        faster. Works better on easier locks with fewer pins.

        Returns:
            Number of pins that clicked during the rake.
        """
        clicks = 0
        for pin in self.pins:
            if not pin.is_set:
                # Random lift with raking
                pin.current_height = random.uniform(0.1, 0.9)
                tolerance = 0.06 - (self.difficulty * 0.008)
                if pin.is_bound and abs(pin.current_height - pin.key_height) < tolerance:
                    pin.is_set = True
                    pin.current_height = pin.key_height
                    clicks += 1
        # Raking can unset previously set pins on hard locks
        if self.difficulty >= 3:
            for pin in self.pins:
                if pin.is_set and random.random() < 0.15 * (self.difficulty - 2):
                    pin.is_set = False
        # Raking is hard on the pick
        if self.difficulty >= 3:
            self.pick_health = max(0.0, self.pick_health - 0.03)
        return clicks

    def get_next_hint(self):
        """Get a hint about which pin to work on next.

        Returns:
            Tuple of (pin_index, hint_text) or (None, "No hint available").
        """
        unset_bound = [(i, p) for i, p in enumerate(self.pins)
                       if p.is_bound and not p.is_set]
        if unset_bound:
            # Return the first bound unset pin
            idx, pin = unset_bound[0]
            dist = abs(pin.current_height - pin.key_height)
            if dist < 0.1:
                return idx, f"Pin {idx+1} is bound and almost at shear line!"
            elif dist < 0.25:
                return idx, f"Pin {idx+1} is bound — keep lifting."
            else:
                return idx, f"Pin {idx+1} is bound — needs more lift."
        elif self.tension < 0.05:
            return None, "Apply tension first (A key)."
        else:
            return None, "All bound pins are set. Adjust tension to bind more."


# ─── Visual Helpers ────────────────────────────────────────────────────────

def height_to_bar(height, width=8):
    """Convert a 0-1 height value to a bar string."""
    filled = int(height * width)
    filled = max(0, min(width, filled))
    return '█' * filled + '░' * (width - filled)


def get_pin_visual(pin, width=10):
    """Get a visual representation of a pin."""
    if pin.is_set:
        return '✦ SET ✦'

    h = pin.current_height
    filled = int(h * width)
    filled = max(0, min(width, filled))

    bar = '▓' * filled + '░' * (width - filled)
    status = ''
    if pin.is_bound:
        status = ' ←BOUND'

    return bar + status


def get_tension_bar(tension, width=30):
    """Visualize tension on the plug."""
    filled = int(tension * width)
    filled = max(0, min(width, filled))
    bar = '▓' * filled + '░' * (width - filled)
    return f"Tension: [{bar}] {tension:.0%}"


def get_pick_health_bar(health, width=20):
    """Visualize pick health/durability."""
    filled = int(health * width)
    filled = max(0, min(width, filled))
    if health > 0.5:
        bar = '▓' * filled + '░' * (width - filled)
    elif health > 0.2:
        bar = '▒' * filled + '░' * (width - filled)
    else:
        # Critical health: show remaining as warning dots
        bar = '·' * filled + '·' * (width - filled)
    return f"Pick: [{bar}] {health:.0%}"


# ─── Main Game ─────────────────────────────────────────────────────────────

class LockPickerGame:
    """Interactive terminal lock picking game using curses."""

    def __init__(self, stdscr, start_pins=None, start_difficulty=None):
        self.stdscr = stdscr
        self.lock = None
        self.selected_pin = 0
        self.lift_amount = 0.02
        self.tension_amount = 0.3
        self.message = ""
        self.message_timer = 0
        self.attempts = 0
        self.locks_picked = 0
        self.total_time = 0
        self.start_time = 0
        self.state = 'menu'
        self.num_pins = start_pins if start_pins is not None else 5
        self.difficulty = start_difficulty if start_difficulty is not None else 1
        self.scroll_offset = 0
        self.hint_cooldown = 0  # Frames until next hint available
        self.last_hint = ""
        self.persistent_stats = load_stats()

        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_GREEN)

        curses.curs_set(0)
        self.stdscr.nodelay(1)
        self.stdscr.timeout(50)  # 50ms refresh

    def show_message(self, msg, duration=30):
        """Display a temporary message on screen."""
        self.message = msg
        self.message_timer = duration

    def new_lock(self):
        """Create a new lock and start picking."""
        self.lock = Lock(self.num_pins, self.difficulty)
        self.selected_pin = 0
        self.start_time = time.time()
        self.attempts += 1
        self.state = 'picking'
        self.hint_cooldown = 0
        self.last_hint = ""
        self.show_message(
            f"Lock #{self.attempts} — {self.num_pins} pins, "
            f"{DIFFICULTY_NAMES[self.difficulty-1]} difficulty"
        )

    def run(self):
        """Main game loop."""
        while True:
            if self.state == 'menu':
                if not self._menu_loop():
                    break
            elif self.state == 'picking':
                self._picking_loop()
            elif self.state == 'victory':
                self._victory_loop()

        # Save stats on exit
        self.persistent_stats["locks_picked"] = (
            self.persistent_stats.get("locks_picked", 0) + self.locks_picked
        )
        self.persistent_stats["total_time"] = (
            self.persistent_stats.get("total_time", 0.0) + self.total_time
        )
        save_stats(self.persistent_stats)
        return self.locks_picked

    def _draw_centered(self, y, text, attr=curses.A_NORMAL):
        """Draw text centered on the screen."""
        h, w = self.stdscr.getmaxyx()
        x = max(0, (w - len(text)) // 2)
        try:
            self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _menu_loop(self):
        """Draw and handle the main menu."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        if h < 20 or w < 40:
            self._draw_centered(h // 2, "Terminal too small! Resize to at least 40x20.")
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                return False
            return True

        # Title
        title_lines = [
            "╔══════════════════════════════════════╗",
            "║   🔐 TERMINAL LOCK PICKER 🔐        ║",
            "║   Pin Tumbler Lock Simulator        ║",
            "╚══════════════════════════════════════╝",
        ]

        start_y = max(1, h // 2 - 14)
        for i, line in enumerate(title_lines):
            self._draw_centered(start_y + i, line, curses.color_pair(4) | curses.A_BOLD)

        # Instructions
        y = start_y + 6
        info_lines = [
            f"Number of pins:  {self.num_pins}  (← → to change)",
            f"Difficulty:      {DIFFICULTY_NAMES[self.difficulty-1]}  (↑ ↓ to change)",
            "",
            "Press ENTER to start picking",
            "Press Q to quit",
            "",
            f"Locks picked this session: {self.locks_picked}",
            f"All-time locks picked:     {self.persistent_stats.get('locks_picked', 0)}",
        ]

        # Show best time for current settings
        key = f"{self.num_pins}-{self.difficulty}"
        best = self.persistent_stats.get("best_times", {}).get(key)
        if best is not None:
            info_lines.append(f"Best time ({self.num_pins}p/{DIFFICULTY_NAMES[self.difficulty-1]}):  {best:.1f}s")

        for i, line in enumerate(info_lines):
            self._draw_centered(y + i, line)

        # Draw a decorative lock
        lock_y = y + len(info_lines) + 1
        lock_art = [
            "    ╔═══╗    ",
            "    ║ 🔒 ║    ",
            "╔═══╩═══╩═══╗",
            "║  ┌─┬─┬─┐  ║",
            "║  │ │ │ │  ║",
            "║  ├─┼─┼─┤  ║",
            "║  │ │ │ │  ║",
            "║  └─┴─┴─┘  ║",
            "╚════════════╝",
        ]
        for i, line in enumerate(lock_art):
            self._draw_centered(lock_y + i, line, curses.color_pair(2))

        self.stdscr.refresh()

        key = self.stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            return False
        elif key == curses.KEY_LEFT:
            self.num_pins = max(MIN_PINS, self.num_pins - 1)
        elif key == curses.KEY_RIGHT:
            self.num_pins = min(MAX_PINS, self.num_pins + 1)
        elif key == curses.KEY_UP:
            self.difficulty = min(5, self.difficulty + 1)
        elif key == curses.KEY_DOWN:
            self.difficulty = max(1, self.difficulty - 1)
        elif key in (ord('\n'), curses.KEY_ENTER):
            self.new_lock()

        return True

    def _picking_loop(self):
        """Draw and handle the picking screen."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        if h < 20 or w < 40:
            self._draw_centered(h // 2, "Terminal too small! Resize to at least 40x20.")
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                self.state = 'menu'
            return

        # ── Physics update ──────────────────────────────────────────
        if self.lock:
            for pin in self.lock.pins:
                if not pin.is_set and pin.current_height > 0:
                    # Spring slowly pushes pin down
                    decay = pin.spring_tension * 0.5
                    pin.current_height = max(0.0, pin.current_height - decay)

            # Check for open
            if self.lock.check_open():
                elapsed = time.time() - self.start_time
                self.state = 'victory'
                self.locks_picked += 1
                self.total_time += elapsed

                # Update best time
                stat_key = f"{self.lock.num_pins}-{self.difficulty}"
                best_times = self.persistent_stats.get("best_times", {})
                if stat_key not in best_times or elapsed < best_times[stat_key]:
                    best_times[stat_key] = elapsed
                    self.persistent_stats["best_times"] = best_times
                    self.show_message("🏆 NEW BEST TIME! 🏆", 60)
                else:
                    self.show_message("🔓 LOCK OPENED! 🔓", 60)
                return

        # ── Hint cooldown ──────────────────────────────────────────
        if self.hint_cooldown > 0:
            self.hint_cooldown -= 1

        # ── Draw Lock Cross-Section ──────────────────────────────────
        y = 0

        # Header
        diff_name = DIFFICULTY_NAMES[self.difficulty - 1]
        header = f"Lock #{self.attempts} — {self.lock.num_pins} pins — {diff_name}"
        self._draw_centered(y, header, curses.color_pair(4) | curses.A_BOLD)
        y += 1

        # Tension bar
        y += 1
        tension_str = get_tension_bar(self.lock.tension, max(10, w - 20))
        try:
            self.stdscr.addstr(y, 2, tension_str, curses.color_pair(2))
        except curses.error:
            pass
        y += 1

        # Pick health (only on Hard/Master)
        if self.difficulty >= 4:
            try:
                health_str = get_pick_health_bar(self.lock.pick_health, max(10, w - 30))
                color = curses.color_pair(1) if self.lock.pick_health > 0.5 else (
                    curses.color_pair(3) if self.lock.pick_health <= 0.2 else curses.color_pair(2))
                self.stdscr.addstr(y, 2, health_str, color)
            except curses.error:
                pass
            y += 1

        # Time + session stats
        elapsed = time.time() - self.start_time
        try:
            self.stdscr.addstr(y, 2, f"Time: {elapsed:.1f}s    Locks picked: {self.locks_picked}",
                               curses.A_DIM)
        except curses.error:
            pass
        y += 2

        # ── Draw Pin Chamber ─────────────────────────────────────────
        try:
            self.stdscr.addstr(y, 1, "Pin Chamber:", curses.A_BOLD)
            y += 1

            # Shear line position
            shear_y = y + 3  # The shear line row

            chamber_height = 10
            for row in range(chamber_height):
                row_str = "  ┃"
                height_frac = 1.0 - (row / chamber_height)  # Top=1.0, bottom=0.0

                for pi, pin in enumerate(self.lock.pins):
                    cell = "  "
                    if pin.is_set:
                        if abs(height_frac - pin.key_height) < 0.08:
                            cell = "✦✦"
                        elif height_frac > pin.key_height:
                            cell = "██"
                        elif height_frac < 0.05:
                            cell = "▀▀"
                    else:
                        if abs(height_frac - pin.current_height) < 0.08:
                            cell = "▓▓"
                        elif height_frac < pin.current_height and height_frac > pin.current_height - 0.15:
                            cell = "▒▒"
                        elif height_frac < 0.05:
                            cell = "▀▀"

                    # Selected pin highlight
                    if pi == self.selected_pin:
                        row_str += f"[{cell}]"
                    else:
                        row_str += f" {cell} "

                row_str += "┃"

                # Shear line annotation
                attr = curses.A_NORMAL
                if row == 3:
                    row_str += " ← SHEAR LINE"
                    attr = curses.color_pair(2) | curses.A_BOLD

                self.stdscr.addstr(y, 1, row_str, attr)
                y += 1

            # Bottom of chamber
            bottom = "  ┃"
            for pi, pin in enumerate(self.lock.pins):
                if pi == self.selected_pin:
                    bottom += f"[  ]"
                else:
                    bottom += f"    "
            bottom += "┃"
            self.stdscr.addstr(y, 1, bottom)
            y += 1

            # Spring indicators
            springs = "  ┃"
            for pi, pin in enumerate(self.lock.pins):
                spring_str = "⌇⌇" if not pin.is_set else "  "
                if pi == self.selected_pin:
                    springs += f"[{spring_str}]"
                else:
                    springs += f" {spring_str} "
            springs += "┃"
            self.stdscr.addstr(y, 1, springs)
            y += 1

            # Pin number labels
            labels = "   "
            for pi, pin in enumerate(self.lock.pins):
                if pi == self.selected_pin:
                    labels += f"[{pi+1}]"
                else:
                    labels += f" {pi+1} "
            self.stdscr.addstr(y, 1, labels, curses.color_pair(4))
            y += 1

        except curses.error:
            pass

        y += 1

        # ── Pin Details ───────────────────────────────────────────────
        pin = self.lock.pins[self.selected_pin]

        try:
            self.stdscr.addstr(y, 2, f"── Pin {self.selected_pin + 1} ──",
                               curses.color_pair(4) | curses.A_BOLD)
            y += 1

            # Pin height bar
            bar_width = min(40, w - 30)
            bar = height_to_bar(pin.current_height, bar_width)
            status_color = (curses.color_pair(1) if pin.is_set
                           else curses.color_pair(3) if pin.is_bound
                           else curses.A_NORMAL)
            self.stdscr.addstr(y, 2, f"Height:  [{bar}] {pin.current_height:.2f}", status_color)
            y += 1

            # Shear line indicator
            filled = int(pin.key_height * bar_width)
            shear_bar = '░' * filled + '▼' + '░' * max(0, bar_width - filled - 1)
            self.stdscr.addstr(y, 2, f"Shear:   [{shear_bar}] {pin.key_height:.2f}",
                               curses.color_pair(2))
            y += 1

            # Status
            if pin.is_set:
                status = "✦ SET ✦ — Pin is at shear line!"
                self.stdscr.addstr(y, 2, status, curses.color_pair(1) | curses.A_BOLD)
            elif pin.is_bound:
                dist = abs(pin.current_height - pin.key_height)
                if dist < 0.1:
                    status = f"BOUND — Almost there! Distance: {dist:.3f}"
                elif dist < 0.25:
                    status = f"BOUND — Getting close. Distance: {dist:.3f}"
                else:
                    status = f"BOUND — Need to lift more. Distance: {dist:.3f}"
                self.stdscr.addstr(y, 2, status, curses.color_pair(3) | curses.A_BOLD)
            else:
                status = "Free — Not binding. Apply more tension or find the binding pin."
                self.stdscr.addstr(y, 2, status, curses.A_DIM)
            y += 1

            # Spring info
            spring_str = f"Spring tension: {pin.spring_tension:.3f}"
            self.stdscr.addstr(y, 2, spring_str, curses.A_DIM)
            y += 1

        except curses.error:
            pass

        y += 1

        # ── Progress ──────────────────────────────────────────────────
        set_count = sum(1 for p in self.lock.pins if p.is_set)
        progress_bar_width = min(30, w - 20)
        filled = int((set_count / self.lock.num_pins) * progress_bar_width)
        progress_bar = '█' * filled + '░' * (progress_bar_width - filled)
        try:
            self.stdscr.addstr(y, 2,
                f"Progress: [{progress_bar}] {set_count}/{self.lock.num_pins} pins set",
                curses.color_pair(1) if set_count == self.lock.num_pins else curses.A_NORMAL)
            y += 1
        except curses.error:
            pass

        # ── Hint display ──────────────────────────────────────────────
        if self.last_hint and self.hint_cooldown > 0:
            try:
                self.stdscr.addstr(y, 2, f"💡 {self.last_hint}", curses.color_pair(5))
                y += 1
            except curses.error:
                pass

        # ── Message ───────────────────────────────────────────────────
        if self.message_timer > 0:
            try:
                self.stdscr.addstr(y, 2, self.message, curses.color_pair(5) | curses.A_BOLD)
                self.message_timer -= 1
            except curses.error:
                pass
            y += 1

        # ── Pick broken warning ───────────────────────────────────────
        if self.lock.pick_health <= 0:
            try:
                self.stdscr.addstr(y, 2, "⚠ PICK BROKEN! Press N for a new lock.",
                                   curses.color_pair(3) | curses.A_BOLD)
                y += 1
            except curses.error:
                pass
        elif self.lock.pick_health < 0.3 and self.difficulty >= 4:
            try:
                self.stdscr.addstr(y, 2, "⚠ Pick is wearing thin... be careful!",
                                   curses.color_pair(2) | curses.A_BOLD)
                y += 1
            except curses.error:
                pass

        # ── Controls ──────────────────────────────────────────────────
        y += 1
        controls = [
            "Controls:",
            " ←/→  Select pin        ↑/↓  Lift/release pin",
            " A/Z  Increase/decrease tension    R  Rake (scrub)",
            " S/X  Adjust lift amount    H  Hint    N  New lock    Q  Quit",
        ]
        for line in controls:
            try:
                self.stdscr.addstr(y, 2, line, curses.A_DIM)
                y += 1
            except curses.error:
                pass

        self.stdscr.refresh()

        # ── Input ─────────────────────────────────────────────────────
        key = self.stdscr.getch()

        if key == ord('q') or key == ord('Q'):
            self.state = 'menu'
        elif key == curses.KEY_LEFT:
            self.selected_pin = max(0, self.selected_pin - 1)
        elif key == curses.KEY_RIGHT:
            self.selected_pin = min(self.lock.num_pins - 1, self.selected_pin + 1)
        elif key == curses.KEY_UP:
            # Lift pin
            if self.lock.pick_health > 0:
                clicked = self.lock.lift_pin(self.selected_pin, self.lift_amount)
                if clicked:
                    self.show_message(f"✦ CLICK! Pin {self.selected_pin + 1} set! ✦")
                    if ENABLE_BELL:
                        curses.beep()
            else:
                self.show_message("⚠ Pick is broken! Press N for a new lock.")
        elif key == curses.KEY_DOWN:
            # Release pin
            self.lock.release_pin(self.selected_pin)
        elif key == ord('a') or key == ord('A'):
            # Increase tension
            new_tension = min(1.0, self.lock.tension + 0.05)
            self.lock.apply_tension(new_tension)
        elif key == ord('z') or key == ord('Z'):
            # Decrease tension
            new_tension = max(0.0, self.lock.tension - 0.05)
            self.lock.apply_tension(new_tension)
        elif key == ord('r') or key == ord('R'):
            # Rake
            if self.lock.pick_health > 0:
                self.lock.raking_mode = True
                clicks = self.lock.rack()
                if clicks > 0:
                    self.show_message(f"Raked! {clicks} pin(s) clicked!")
                    if ENABLE_BELL:
                        curses.beep()
                else:
                    self.show_message("Raked... no pins set this time.")
                self.lock.raking_mode = False
            else:
                self.show_message("⚠ Pick is broken! Press N for a new lock.")
        elif key == ord('s') or key == ord('S'):
            self.lift_amount = min(0.15, self.lift_amount + 0.005)
            self.show_message(f"Lift amount: {self.lift_amount:.3f}")
        elif key == ord('x') or key == ord('X'):
            self.lift_amount = max(0.005, self.lift_amount - 0.005)
            self.show_message(f"Lift amount: {self.lift_amount:.3f}")
        elif key == ord('h') or key == ord('H'):
            # Hint system
            idx, hint = self.lock.get_next_hint()
            self.last_hint = hint
            self.hint_cooldown = 40  # Show hint for ~2 seconds
            if idx is not None:
                self.selected_pin = idx
        elif key == ord('n') or key == ord('N'):
            self.new_lock()

    def _victory_loop(self):
        """Draw and handle the victory screen."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        elapsed = time.time() - self.start_time

        victory_art = [
            "",
            "╔══════════════════════════════════════╗",
            "║                                      ║",
            "║     🔓 LOCK SUCCESSFULLY PICKED! 🔓  ║",
            "║                                      ║",
            "╚══════════════════════════════════════╝",
            "",
        ]

        y = max(1, h // 2 - 10)
        for i, line in enumerate(victory_art):
            self._draw_centered(y + i, line, curses.color_pair(1) | curses.A_BOLD)

        y += len(victory_art)

        # Check if this is a best time
        stat_key = f"{self.lock.num_pins}-{self.difficulty}"
        best_time = self.persistent_stats.get("best_times", {}).get(stat_key)
        is_best = best_time is not None and abs(elapsed - best_time) < 0.05

        stats = [
            f"Time: {elapsed:.1f} seconds",
            f"Pins: {self.lock.num_pins}",
            f"Difficulty: {DIFFICULTY_NAMES[self.difficulty-1]}",
            f"Total locks picked: {self.locks_picked}",
            f"Total time: {self.total_time + elapsed:.1f}s",
        ]

        if is_best:
            stats.append("🏆 NEW BEST TIME! 🏆")

        if self.lock.pick_health > 0:
            stats.append(f"Pick health remaining: {self.lock.pick_health:.0%}")

        stats.append("")
        stats.append("ENTER — New lock    M — Menu    Q — Quit")

        for i, line in enumerate(stats):
            attr = curses.color_pair(5) | curses.A_BOLD if "🏆" in line else curses.A_NORMAL
            self._draw_centered(y + i, line, attr)

        # Celebration animation — random sparkles
        for _ in range(5):
            sx = random.randint(0, max(0, w - 1))
            sy = random.randint(0, max(0, h - 1))
            sparkle = random.choice(['✦', '✧', '★', '☆', '·', '*'])
            try:
                self.stdscr.addstr(sy, sx, sparkle,
                                   curses.color_pair(random.choice([1, 2, 4, 5])) | curses.A_BOLD)
            except curses.error:
                pass

        self.stdscr.refresh()

        key = self.stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            self.state = 'menu'
        elif key in (ord('\n'), curses.KEY_ENTER):
            self.new_lock()
        elif key == ord('m') or key == ord('M'):
            self.state = 'menu'


# ─── Demo Mode ─────────────────────────────────────────────────────────────

def run_demo(num_pins=5, difficulty=2, speed=0.05):
    """Auto-pick a lock in demo mode, printing output to terminal.

    The demo uses a smarter picking strategy: for each bound pin, it lifts
    multiple times per "round" to counteract spring decay. If no bound pin
    is found, it gradually increases tension to bind more pins.

    Args:
        num_pins: Number of pins for the demo lock.
        difficulty: Difficulty level (1-5).
        speed: Delay between rounds in seconds.
    """
    print(f"\n🔐 Terminal Lock Picker — Demo Mode")
    print(f"   {num_pins} pins, {DIFFICULTY_NAMES[difficulty-1]} difficulty\n")

    lock = Lock(num_pins, difficulty)
    lock.apply_tension(0.3)
    print(f"Applied initial tension: {lock.tension:.0%}\n")

    round_num = 0
    max_rounds = 800
    lift_per_round = 8  # Multiple lifts per round to counteract spring decay
    no_progress_count = 0

    while not lock.is_open and round_num < max_rounds:
        # Apply spring decay (simulates one game frame)
        for p in lock.pins:
            if not p.is_set and p.current_height > 0:
                p.current_height = max(0.0, p.current_height - p.spring_tension * 0.5)

        # Re-apply tension to update binding (pins that were set now free up binding spots)
        lock.apply_tension(lock.tension)

        # Find the first bound, unset pin
        found_bound = False
        for i, pin in enumerate(lock.pins):
            if pin.is_bound and not pin.is_set:
                clicked_pin = False
                for _ in range(lift_per_round):
                    clicked = lock.lift_pin(i, 0.02)
                    if clicked:
                        print(f"  Round {round_num+1}: ✦ CLICK! Pin {i+1} set! ✦")
                        no_progress_count = 0
                        clicked_pin = True
                        break
                if not clicked_pin:
                    no_progress_count += 1
                found_bound = True
                break

        if not found_bound:
            # Increase tension to bind more pins
            old_tension = lock.tension
            lock.apply_tension(min(1.0, lock.tension + 0.05))
            if lock.tension > old_tension:
                print(f"  Round {round_num+1}: Increasing tension to {lock.tension:.0%}")
            no_progress_count += 1

        # If we've been stuck for a while, try raking or adjust tension
        if no_progress_count > 30:
            # Try raking
            clicks = lock.rack()
            if clicks > 0:
                print(f"  Round {round_num+1}: Raked — {clicks} pin(s) set!")
                no_progress_count = 0
            else:
                # Reset tension and try again
                lock.apply_tension(0.3)
                no_progress_count = 0

        lock.check_open()
        round_num += 1
        time.sleep(speed)

    if lock.is_open:
        print(f"\n🔓 Lock opened in {round_num} rounds!")
        print(f"   All {num_pins} pins set successfully.\n")
    else:
        print(f"\n❌ Failed to pick lock in {max_rounds} rounds.\n")

    return lock.is_open


# ─── CLI Entry Point ──────────────────────────────────────────────────────

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Terminal Lock Picker — An interactive pin tumbler lock picking simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python3 lock_picker.py                     Interactive mode (default)
  python3 lock_picker.py --pins 4            Start with 4 pins
  python3 lock_picker.py --difficulty 3       Start on Medium difficulty
  python3 lock_picker.py --demo              Watch the AI pick a lock
  python3 lock_picker.py --demo --pins 3     Demo with 3-pin lock
  python3 lock_picker.py --version            Show version
"""
    )
    parser.add_argument('--version', action='version', version=f'Terminal Lock Picker v{VERSION}')
    parser.add_argument('--pins', type=int, choices=range(MIN_PINS, MAX_PINS + 1),
                        metavar=f'{MIN_PINS}-{MAX_PINS}',
                        help=f'Number of pins ({MIN_PINS}-{MAX_PINS}), default: 5')
    parser.add_argument('--difficulty', type=int, choices=range(1, 6),
                        metavar='1-5',
                        help='Difficulty level (1=Novice, 5=Master), default: 1')
    parser.add_argument('--demo', action='store_true',
                        help='Run in demo mode (auto-pick, no curses)')
    parser.add_argument('--speed', type=float, default=0.05,
                        help='Demo speed in seconds between steps (default: 0.05)')
    return parser.parse_args()


def main():
    """Main entry point — parse args and launch appropriate mode."""
    args = parse_args()

    pins = args.pins if args.pins is not None else 5
    difficulty = args.difficulty if args.difficulty is not None else 1

    if args.demo:
        # Non-interactive demo mode
        success = run_demo(num_pins=pins, difficulty=difficulty, speed=args.speed)
        sys.exit(0 if success else 1)
    else:
        # Interactive curses mode
        result = None
        try:
            def curses_main(stdscr):
                game = LockPickerGame(stdscr, start_pins=args.pins, start_difficulty=args.difficulty)
                return game.run()

            result = curses.wrapper(curses_main)
        except KeyboardInterrupt:
            print("\nThanks for playing Terminal Lock Picker!")
        print(f"\nLocks picked this session: {result if result is not None else 'interrupted'}")


if __name__ == '__main__':
    main()