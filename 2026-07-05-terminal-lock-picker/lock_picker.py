#!/usr/bin/env python3
"""
Terminal Lock Picking Simulator
An interactive simulation of picking pin tumbler locks in the terminal.
Feel the tension, set the pins, and hear the click!
"""

import curses
import random
import time
import math
import sys

# ─── Lock Mechanics ───────────────────────────────────────────────────────

class Pin:
    """A single pin in a pin tumbler lock."""
    def __init__(self, key_height, spring_tension):
        self.key_height = key_height        # The correct height for this pin (0.0-1.0)
        self.current_height = 0.0           # Current height of the pin
        self.spring_tension = spring_tension # How strongly the spring pushes the pin down
        self.is_set = False                 # Whether this pin is at the shear line
        self.is_bound = False               # Whether this pin is binding against the plug
        self.binding_order = 0              # Order in which pins bind (lower = binds first)
        self.wobble = 0.0                   # Random wobble factor


class Lock:
    """A pin tumbler lock with multiple pins."""
    PIN_NAMES = ['│','▏','▎','▍','▌','▋','▊','▉','█']
    
    def __init__(self, num_pins=5, difficulty=1):
        self.num_pins = num_pins
        self.difficulty = difficulty  # 1-5, affects tolerance and spring tension
        self.pins = []
        self.tension = 0.0           # How much torque is applied to the plug (0.0-1.0)
        self.is_open = False
        self.core_rotation = 0.0     # How much the plug has rotated (0.0-1.0)
        self.raking_mode = False
        
        self._generate_pins()
    
    def _generate_pins(self):
        """Generate random pin heights and binding orders."""
        # Spring tension is a *damping* factor, not a force that cancels lift.
        # It reduces how much of your lift actually moves the pin.
        base_tension = 0.10 + self.difficulty * 0.04
        for i in range(self.num_pins):
            key_height = random.uniform(0.25, 0.85)
            spring_tension = base_tension + random.uniform(-0.03, 0.03)
            pin = Pin(key_height, spring_tension)
            self.pins.append(pin)
        
        # Assign binding order — pins with lower key_heights and further from plug tend to bind first
        order = list(range(self.num_pins))
        random.shuffle(order)
        for i, pin in enumerate(self.pins):
            pin.binding_order = order.index(i)
        
        # Add some wobble based on difficulty
        for pin in self.pins:
            pin.wobble = random.uniform(0.001, 0.005) * self.difficulty
    
    def apply_tension(self, amount):
        """Apply or release tension on the plug."""
        self.tension = max(0.0, min(1.0, amount))
        self._update_binding()
    
    def _update_binding(self):
        """Determine which pins are currently binding."""
        if self.tension < 0.05:
            for pin in self.pins:
                pin.is_bound = False
            return
        
        # How many pins bind at once — more tension means more pins bind simultaneously
        # At minimum, 1 pin always binds when tension is applied
        bound_count = max(1, int(self.tension * self.num_pins / 2))
        
        # Clear all binding first
        for pin in self.pins:
            pin.is_bound = False
        
        # Sort unset pins by binding order — the ones that bind first get set first
        unset_pins = [p for p in self.pins if not p.is_set]
        unset_pins.sort(key=lambda p: p.binding_order)
        
        # The first `bound_count` unset pins are currently binding
        for pin in unset_pins[:bound_count]:
            pin.is_bound = True
    
    def lift_pin(self, pin_index, amount):
        """Lift a pin by the given amount."""
        if pin_index < 0 or pin_index >= self.num_pins:
            return False
        
        pin = self.pins[pin_index]
        
        # Spring tension acts as damping — it reduces the effective lift
        # More tension on the plug means more friction on bound pins (easier to feel)
        # but non-bound pins resist less
        if pin.is_bound:
            damping = pin.spring_tension * (1.0 - self.tension * 0.2)
        else:
            damping = pin.spring_tension * 0.5
        
        effective_lift = amount * (1.0 - damping)
        
        # Add wobble based on difficulty
        wobble = random.gauss(0, pin.wobble) * 3
        effective_lift += wobble
        
        new_height = pin.current_height + effective_lift
        
        # Can't push below 0
        new_height = max(0.0, new_height)
        
        # If pin is not bound, it might overset (go too high and spring back)
        if not pin.is_bound and not pin.is_set and new_height > 0.95:
            # Pin drops back down — overset
            new_height = max(0.0, new_height * 0.3)
        
        pin.current_height = min(1.0, new_height)
        
        # Check if pin is set (at the shear line = key height)
        tolerance = 0.06 - (self.difficulty * 0.006)  # Harder locks have tighter tolerance
        if pin.is_bound and abs(pin.current_height - pin.key_height) < tolerance:
            pin.is_set = True
            pin.current_height = pin.key_height  # Snap to set position
            return True  # Click!
        
        # If pin was set but we moved it, it might unset
        if pin.is_set and abs(pin.current_height - pin.key_height) > tolerance * 2.5:
            pin.is_set = False
        
        return False
    
    def release_pin(self, pin_index):
        """Release a pin — let the spring push it back down."""
        if 0 <= pin_index < self.num_pins:
            pin = self.pins[pin_index]
            if pin.is_set:
                return  # Set pins stay
            pin.current_height = max(0.0, pin.current_height - 0.15)
    
    def check_open(self):
        """Check if all pins are set and the lock can open."""
        if all(pin.is_set for pin in self.pins) and self.tension > 0.2:
            self.is_open = True
            return True
        return False
    
    def rack(self):
        """Attempt to rake the lock — rapidly scrub all pins."""
        clicks = 0
        for pin in self.pins:
            if not pin.is_set:
                # Random lift with raking
                lift = random.uniform(0.05, 0.25)
                pin.current_height = random.uniform(0.1, 0.9)
                tolerance = 0.06 - (self.difficulty * 0.008)
                if pin.is_bound and abs(pin.current_height - pin.key_height) < tolerance:
                    pin.is_set = True
                    pin.current_height = pin.key_height
                    clicks += 1
        return clicks


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
    
    # Show the shear line position
    shear_pos = int(pin.key_height * width)
    
    status = ''
    if pin.is_bound:
        status = ' ←BOUND'
    elif pin.is_set:
        status = ' ←SET'
    
    return bar + status


def get_tension_bar(tension, width=30):
    """Visualize tension on the plug."""
    filled = int(tension * width)
    filled = max(0, min(width, filled))
    bar = '▓' * filled + '░' * (width - filled)
    return f"Tension: [{bar}] {tension:.0%}"


# ─── Main Game ─────────────────────────────────────────────────────────────

class LockPickerGame:
    DIFFICULTY_NAMES = ['Novice', 'Easy', 'Medium', 'Hard', 'Master']
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.lock = None
        self.selected_pin = 0
        self.lift_amount = 0.02
        self.tension_amount = 0.3
        self.message = ""
        self.message_timer = 0
        self.clicks = []  # History of "click" feedback
        self.attempts = 0
        self.locks_picked = 0
        self.total_time = 0
        self.start_time = 0
        self.state = 'menu'  # menu, picking, victory
        self.num_pins = 5
        self.difficulty = 1
        self.scroll_offset = 0
        self.haptic_feedback = []  # Simulated haptic queue
        
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
        self.message = msg
        self.message_timer = duration
    
    def new_lock(self):
        self.lock = Lock(self.num_pins, self.difficulty)
        self.selected_pin = 0
        self.start_time = time.time()
        self.attempts += 1
        self.state = 'picking'
        self.show_message(f"Lock #{self.attempts} — {self.num_pins} pins, {self.DIFFICULTY_NAMES[self.difficulty-1]} difficulty")
    
    def run(self):
        while True:
            if self.state == 'menu':
                if not self._menu_loop():
                    break
            elif self.state == 'picking':
                self._picking_loop()
            elif self.state == 'victory':
                self._victory_loop()
        
        return self.locks_picked
    
    def _draw_centered(self, y, text, attr=curses.A_NORMAL):
        h, w = self.stdscr.getmaxyx()
        x = max(0, (w - len(text)) // 2)
        try:
            self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass
    
    def _menu_loop(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Title
        title_lines = [
            "╔══════════════════════════════════════╗",
            "║   🔐 TERMINAL LOCK PICKER 🔐        ║",
            "║   Pin Tumbler Lock Simulator        ║",
            "╚══════════════════════════════════════╝",
        ]
        
        start_y = max(1, h // 2 - 12)
        for i, line in enumerate(title_lines):
            self._draw_centered(start_y + i, line, curses.color_pair(4) | curses.A_BOLD)
        
        # Instructions
        y = start_y + 6
        info_lines = [
            f"Number of pins:  {self.num_pins}  (← → to change)",
            f"Difficulty:      {self.DIFFICULTY_NAMES[self.difficulty-1]}  (↑ ↓ to change)",
            "",
            "Press ENTER to start picking",
            "Press Q to quit",
            "",
            "Locks picked this session: {}".format(self.locks_picked),
        ]
        
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
            self.num_pins = max(2, self.num_pins - 1)
        elif key == curses.KEY_RIGHT:
            self.num_pins = min(8, self.num_pins + 1)
        elif key == curses.KEY_UP:
            self.difficulty = min(5, self.difficulty + 1)
        elif key == curses.KEY_DOWN:
            self.difficulty = max(1, self.difficulty - 1)
        elif key in (ord('\n'), curses.KEY_ENTER):
            self.new_lock()
        
        return True
    
    def _picking_loop(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Physics update — springs slowly push unset pins down
        if self.lock:
            for i, pin in enumerate(self.lock.pins):
                if not pin.is_set and pin.current_height > 0:
                    # Spring slowly pushes pin down
                    decay = pin.spring_tension * 0.5
                    pin.current_height = max(0.0, pin.current_height - decay)
            
            # Check for open
            if self.lock.check_open():
                self.state = 'victory'
                self.locks_picked += 1
                self.total_time += time.time() - self.start_time
                self.show_message("🔓 LOCK OPENED! 🔓", 60)
                return
        
        # ─── Draw Lock Cross-Section ──────────────────────────────────
        y = 0
        
        # Header
        diff_name = self.DIFFICULTY_NAMES[self.difficulty - 1]
        header = f"Lock #{self.attempts} — {self.lock.num_pins} pins — {diff_name}"
        self._draw_centered(y, header, curses.color_pair(4) | curses.A_BOLD)
        y += 1
        
        # Tension bar
        y += 1
        tension_str = get_tension_bar(self.lock.tension, w - 20)
        try:
            self.stdscr.addstr(y, 2, tension_str, curses.color_pair(2))
        except curses.error:
            pass
        y += 1
        
        # Time
        elapsed = time.time() - self.start_time
        try:
            self.stdscr.addstr(y, 2, f"Time: {elapsed:.1f}s    Locks picked: {self.locks_picked}", curses.A_DIM)
        except curses.error:
            pass
        y += 2
        
        # ─── Draw Pin Chamber ─────────────────────────────────────────
        chamber_top = y
        chamber_height = 10
        
        # Draw chamber walls and pins
        try:
            self.stdscr.addstr(y, 1, "Pin Chamber:", curses.A_BOLD)
            y += 1
            
            # Shear line label
            shear_y = y + 3  # The shear line position
            
            for row in range(chamber_height):
                row_str = "  ┃"
                height_frac = 1.0 - (row / chamber_height)  # Top = 1.0, bottom = 0.0
                
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
                
                # Shear line
                attr = curses.A_NORMAL
                if row == 3:  # Shear line row
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
                marker = f" {pi+1} "
                if pi == self.selected_pin:
                    labels += f"[{pi+1}]"
                else:
                    labels += marker
            self.stdscr.addstr(y, 1, labels, curses.color_pair(4))
            y += 1
            
        except curses.error:
            pass
        
        y += 1
        
        # ─── Pin Details ───────────────────────────────────────────────
        pin = self.lock.pins[self.selected_pin]
        
        try:
            self.stdscr.addstr(y, 2, f"── Pin {self.selected_pin + 1} ──", curses.color_pair(4) | curses.A_BOLD)
            y += 1
            
            # Pin height bar
            bar_width = min(40, w - 30)
            bar = height_to_bar(pin.current_height, bar_width)
            status_color = curses.color_pair(1) if pin.is_set else (curses.color_pair(3) if pin.is_bound else curses.A_NORMAL)
            self.stdscr.addstr(y, 2, f"Height:  [{bar}] {pin.current_height:.2f}", status_color)
            y += 1
            
            # Shear line indicator
            shear_bar_width = bar_width
            filled = int(pin.key_height * shear_bar_width)
            shear_bar = '░' * filled + '▼' + '░' * (shear_bar_width - filled - 1)
            self.stdscr.addstr(y, 2, f"Shear:   [{shear_bar}] {pin.key_height:.2f}", curses.color_pair(2))
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
        
        # ─── Progress ──────────────────────────────────────────────────
        set_count = sum(1 for p in self.lock.pins if p.is_set)
        progress_bar_width = min(30, w - 20)
        filled = int((set_count / self.lock.num_pins) * progress_bar_width)
        progress_bar = '█' * filled + '░' * (progress_bar_width - filled)
        try:
            self.stdscr.addstr(y, 2, f"Progress: [{progress_bar}] {set_count}/{self.lock.num_pins} pins set", 
                             curses.color_pair(1) if set_count == self.lock.num_pins else curses.A_NORMAL)
            y += 1
        except curses.error:
            pass
        
        # ─── Message ───────────────────────────────────────────────────
        if self.message_timer > 0:
            try:
                self.stdscr.addstr(y, 2, self.message, curses.color_pair(5) | curses.A_BOLD)
                self.message_timer -= 1
            except curses.error:
                pass
            y += 1
        
        # ─── Controls ──────────────────────────────────────────────────
        y += 1
        controls = [
            "Controls:",
            " ←/→  Select pin        ↑/↓  Lift/release pin",
            " A/Z  Increase/decrease tension    R  Rack (scrub)",
            " S/X  Adjust lift amount    N  New lock    Q  Quit",
        ]
        for line in controls:
            try:
                self.stdscr.addstr(y, 2, line, curses.A_DIM)
                y += 1
            except curses.error:
                pass
        
        self.stdscr.refresh()
        
        # ─── Input ─────────────────────────────────────────────────────
        key = self.stdscr.getch()
        
        if key == ord('q') or key == ord('Q'):
            self.state = 'menu'
        elif key == curses.KEY_LEFT:
            self.selected_pin = max(0, self.selected_pin - 1)
        elif key == curses.KEY_RIGHT:
            self.selected_pin = min(self.lock.num_pins - 1, self.selected_pin + 1)
        elif key == curses.KEY_UP:
            # Lift pin
            clicked = self.lock.lift_pin(self.selected_pin, self.lift_amount)
            if clicked:
                self.show_message(f"✦ CLICK! Pin {self.selected_pin + 1} set! ✦")
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
            self.lock.raking_mode = True
            clicks = self.lock.rack()
            if clicks > 0:
                self.show_message(f"Raked! {clicks} pin(s) clicked!")
            else:
                self.show_message("Raked... no pins set this time.")
            self.lock.raking_mode = False
        elif key == ord('s') or key == ord('S'):
            self.lift_amount = min(0.15, self.lift_amount + 0.005)
            self.show_message(f"Lift amount: {self.lift_amount:.3f}")
        elif key == ord('x') or key == ord('X'):
            self.lift_amount = max(0.005, self.lift_amount - 0.005)
            self.show_message(f"Lift amount: {self.lift_amount:.3f}")
        elif key == ord('n') or key == ord('N'):
            self.new_lock()
    
    def _victory_loop(self):
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
        
        stats = [
            f"Time: {elapsed:.1f} seconds",
            f"Pins: {self.lock.num_pins}",
            f"Difficulty: {self.DIFFICULTY_NAMES[self.difficulty-1]}",
            f"Total locks picked: {self.locks_picked}",
            f"Total time: {self.total_time + elapsed:.1f}s",
            "",
            "ENTER — New lock    M — Menu    Q — Quit",
        ]
        
        for i, line in enumerate(stats):
            self._draw_centered(y + i, line)
        
        # Celebration animation — random sparkles
        for _ in range(5):
            sx = random.randint(0, w - 1)
            sy = random.randint(0, h - 1)
            sparkle = random.choice(['✦', '✧', '★', '☆', '·', '*'])
            try:
                self.stdscr.addstr(sy, sx, sparkle, curses.color_pair(random.choice([1, 2, 4, 5])) | curses.A_BOLD)
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


def main(stdscr):
    game = LockPickerGame(stdscr)
    game.run()


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nThanks for playing Terminal Lock Picker!")
    print(f"\nLocks picked this session: session interrupted")