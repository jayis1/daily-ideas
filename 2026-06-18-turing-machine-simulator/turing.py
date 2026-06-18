#!/usr/bin/env python3
"""
Turing Machine Simulator — A visual, interactive simulator for Turing machines
with built-in example programs and a custom program mode.
"""

import os
import sys
import time
import curses
import json
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List

# ─── Data structures ────────────────────────────────────────────────

@dataclass
class Transition:
    """A single transition rule: (state, read_symbol) -> (next_state, write_symbol, direction)"""
    next_state: str
    write_symbol: str
    direction: str  # 'L', 'R', 'S' (stay)

    def __repr__(self):
        return f"→ ({self.next_state}, {self.write_symbol}, {self.direction})"


@dataclass
class TuringMachine:
    """A complete Turing machine definition."""
    name: str
    description: str
    states: List[str]
    alphabet: List[str]
    blank_symbol: str = "_"
    initial_state: str = "q0"
    accept_states: List[str] = field(default_factory=lambda: ["q_accept"])
    reject_states: List[str] = field(default_factory=lambda: ["q_reject"])
    transitions: Dict[Tuple[str, str], Transition] = field(default_factory=dict)
    initial_tape: str = ""

    def step(self, state: str, symbol: str) -> Optional[Transition]:
        return self.transitions.get((state, symbol))


class Tape:
    """An infinite tape implemented with a dict (sparse)."""

    def __init__(self, blank: str = "_"):
        self.cells: Dict[int, str] = {}
        self.blank = blank

    def read(self, pos: int) -> str:
        return self.cells.get(pos, self.blank)

    def write(self, pos: int, symbol: str):
        if symbol == self.blank:
            self.cells.pop(pos, None)
        else:
            self.cells[pos] = symbol

    def to_string(self, head_pos: int, window: int = 30) -> list:
        """Return a list of symbols centered around head_pos."""
        start = head_pos - window // 2
        end = head_pos + window // 2
        result = []
        for i in range(start, end + 1):
            result.append(self.cells.get(i, self.blank))
        return result

    def non_blank_segment(self) -> Tuple[int, int]:
        """Return (min, max) positions with non-blank cells."""
        if not self.cells:
            return (0, 0)
        return (min(self.cells.keys()), max(self.cells.keys()))


# ─── Built-in programs ──────────────────────────────────────────────

BUILTIN_PROGRAMS = {}

def _register(name, desc, states, alphabet, blank, initial, accept, reject, transitions, tape):
    BUILTIN_PROGRAMS[name] = TuringMachine(
        name=name, description=desc, states=states, alphabet=alphabet,
        blank_symbol=blank, initial_state=initial, accept_states=accept,
        reject_states=reject, transitions={
            (s, r): Transition(ns, w, d)
            for (s, r), (ns, w, d) in transitions.items()
        },
        initial_tape=tape
    )

# 1. Binary increment — increments a binary number by 1
_register(
    "binary_increment",
    "Increment a binary number by 1",
    states=["q0", "q_carry", "q_done", "q_accept", "q_reject"],
    alphabet=["0", "1", "_"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=["q_reject"],
    transitions={
        # Move right to find the end
        ("q0", "0"): ("q0", "0", "R"),
        ("q0", "1"): ("q0", "1", "R"),
        ("q0", "_"): ("q_carry", "_", "L"),
        # Carry: add 1
        ("q_carry", "1"): ("q_carry", "0", "L"),
        ("q_carry", "0"): ("q_done", "1", "L"),
        ("q_carry", "_"): ("q_done", "1", "S"),
        # Done
        ("q_done", "0"): ("q_accept", "0", "S"),
        ("q_done", "1"): ("q_accept", "1", "S"),
        ("q_done", "_"): ("q_accept", "_", "S"),
    },
    tape="1011",  # 11 in binary, should become 1100 (12)
)

# 2. Unary addition — adds two unary numbers separated by '+'
# Strategy: replace '+' with '1', then erase the last '1' to compensate
_register(
    "unary_addition",
    "Add two unary numbers separated by '+' (e.g., 111+11=11111)",
    states=["q0", "q1", "q2", "q_accept"],
    alphabet=["1", "+", "_"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=[],
    transitions={
        # Skip 1s, find the +
        ("q0", "1"): ("q0", "1", "R"),
        # Replace + with 1
        ("q0", "+"): ("q1", "1", "R"),
        # Skip remaining 1s to find end
        ("q1", "1"): ("q1", "1", "R"),
        # Found end, go back to erase last 1
        ("q1", "_"): ("q2", "_", "L"),
        # Erase the last 1
        ("q2", "1"): ("q_accept", "_", "S"),
    },
    tape="111+11",  # 3+2=5 ones
)

# 3. Palindrome checker for binary strings
_register(
    "palindrome_checker",
    "Check if a binary string is a palindrome",
    states=["q0", "q_left0", "q_left1", "q_right0", "q_right1",
            "q_back", "q_done0", "q_done1", "q_accept", "q_reject"],
    alphabet=["0", "1", "_", "X"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=["q_reject"],
    transitions={
        # Empty tape or single char is palindrome
        ("q0", "_"): ("q_accept", "_", "S"),
        # Read leftmost symbol, mark it, go right
        ("q0", "0"): ("q_right0", "X", "R"),
        ("q0", "1"): ("q_right1", "X", "R"),
        # q_right0: skip to rightmost, check it's 0
        ("q_right0", "0"): ("q_right0", "0", "R"),
        ("q_right0", "1"): ("q_right0", "1", "R"),
        ("q_right0", "_"): ("q_left0", "_", "L"),
        ("q_right0", "X"): ("q_accept", "X", "S"),  # only one symbol left
        # q_right1: skip to rightmost, check it's 1
        ("q_right1", "0"): ("q_right1", "0", "R"),
        ("q_right1", "1"): ("q_right1", "1", "R"),
        ("q_right1", "_"): ("q_left1", "_", "L"),
        ("q_right1", "X"): ("q_accept", "X", "S"),
        # Found rightmost: verify it matches, mark it, go back left
        ("q_left0", "0"): ("q_back", "X", "L"),
        ("q_left0", "1"): ("q_reject", "1", "S"),
        ("q_left1", "1"): ("q_back", "X", "L"),
        ("q_left1", "0"): ("q_reject", "0", "S"),
        # Go back to leftmost
        ("q_back", "0"): ("q_back", "0", "L"),
        ("q_back", "1"): ("q_back", "1", "L"),
        ("q_back", "X"): ("q0", "X", "R"),
        ("q_back", "_"): ("q0", "_", "R"),
    },
    tape="10101",  # palindrome
)

# 4. Busy Beaver (3-state) — champion: writes 6 ones in 13 steps
_register(
    "busy_beaver_3",
    "Busy Beaver 3-state champion — writes 6 ones then halts (13 steps)",
    states=["A", "B", "C", "HALT"],
    alphabet=["0", "1"],
    blank="0",
    initial="A",
    accept=["HALT"],
    reject=[],
    transitions={
        ("A", "0"): ("B", "1", "R"),
        ("A", "1"): ("C", "1", "R"),
        ("B", "0"): ("C", "1", "L"),
        ("B", "1"): ("HALT", "1", "S"),
        ("C", "0"): ("A", "1", "R"),
        ("C", "1"): ("B", "0", "L"),
    },
    tape="",  # starts blank
)

# 5. Binary NOT — flip all bits of a binary string
_register(
    "binary_not",
    "Flip all bits in a binary string (NOT operation)",
    states=["q0", "q_accept"],
    alphabet=["0", "1", "_"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=[],
    transitions={
        ("q0", "0"): ("q0", "1", "R"),
        ("q0", "1"): ("q0", "0", "R"),
        ("q0", "_"): ("q_accept", "_", "S"),
    },
    tape="10110011",
)

# 6. Count 1s in binary — counts the number of 1s and writes result in unary after '='
_register(
    "count_ones",
    "Count the 1s in a binary string and write unary result after '='",
    states=["q0", "q1", "q2", "q3", "q4", "q_accept"],
    alphabet=["0", "1", "_", "=", "|"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=[],
    transitions={
        # Find a 1
        ("q0", "0"): ("q0", "0", "R"),
        ("q0", "1"): ("q1", "1", "R"),
        ("q0", "="): ("q4", "=", "R"),
        # Remember we saw a 1, go to the end
        ("q1", "0"): ("q1", "0", "R"),
        ("q1", "1"): ("q1", "1", "R"),
        ("q1", "="): ("q1", "=", "R"),
        ("q1", "|"): ("q1", "|", "R"),
        ("q1", "_"): ("q2", "|", "L"),
        # Go back to find next 1
        ("q2", "|"): ("q2", "|", "L"),
        ("q2", "="): ("q2", "=", "L"),
        ("q2", "0"): ("q2", "0", "L"),
        ("q2", "1"): ("q0", "1", "R"),
        ("q2", "_"): ("q3", "_", "R"),
        # If we reached = without finding 1, we're done
        ("q0", "_"): ("q4", "=", "R"),
        # Move right to end and accept
        ("q4", "|"): ("q4", "|", "R"),
        ("q4", "_"): ("q_accept", "_", "S"),
        # Handle start of second pass
        ("q3", "0"): ("q0", "0", "R"),
        ("q3", "1"): ("q0", "1", "R"),
        ("q3", "="): ("q_accept", "=", "S"),
    },
    tape="10110=",  # 3 ones → |||
)


# ─── Visual simulator using curses ──────────────────────────────────

def run_visual(stdscr: curses.window, machine: TuringMachine, speed: float = 0.3):
    """Run the Turing machine with a curses-based visualization."""

    curses.curs_set(0)
    stdscr.nodelay(False)

    # Initialize tape
    tape = Tape(blank=machine.blank_symbol)
    if machine.initial_tape:
        for i, ch in enumerate(machine.initial_tape):
            tape.write(i, ch)

    state = machine.initial_state
    head_pos = 0
    steps = 0
    running = True
    paused = False
    step_mode = False
    history = []  # List of (state, head_pos, tape_snapshot) for rewind

    TAPE_WINDOW = 40
    MAX_DISPLAY_STEPS = 5000

    def draw():
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Title
        title = f"  ⟨ {machine.name.replace('_', ' ').title()} ⟩"
        stdscr.addstr(0, 2, title, curses.A_BOLD | curses.color_pair(3))

        desc_line = f"  {machine.description}"
        stdscr.addstr(1, 2, desc_line, curses.color_pair(2))

        # Divider
        stdscr.addstr(2, 0, "─" * w, curses.color_pair(4))

        # State info
        state_color = curses.color_pair(1)
        if state in machine.accept_states:
            state_color = curses.color_pair(2) | curses.A_BOLD
        elif state in machine.reject_states:
            state_color = curses.color_pair(5) | curses.A_BOLD

        info_line = f"  State: {state}    Step: {steps}    Head: {head_pos}"
        stdscr.addstr(3, 2, info_line, state_color)

        # Tape display
        cells = tape.to_string(head_pos, TAPE_WINDOW)
        start = head_pos - TAPE_WINDOW // 2

        # Tape indices
        idx_line = "  "
        for i, pos in enumerate(range(start, start + len(cells))):
            if pos == head_pos:
                idx_line += " ▼ "
            else:
                idx_line += "   "
        try:
            stdscr.addstr(5, 0, idx_line[:w])
        except curses.error:
            pass

        # Tape cells
        tape_line = "  "
        for i, (pos, sym) in enumerate(zip(range(start, start + len(cells)), cells)):
            if pos == head_pos:
                tape_line += f"[{sym}]"
            else:
                tape_line += f" {sym} "
        try:
            stdscr.addstr(6, 0, tape_line[:w], curses.color_pair(6))
        except curses.error:
            pass

        # Head indicator
        head_marker = "  " + " " * 0
        for i, pos in enumerate(range(start, start + len(cells))):
            if pos == head_pos:
                break
            if pos == head_pos:
                head_marker += "   "
            else:
                head_marker += "   "

        # Position numbers
        pos_line = "  "
        for i, pos in enumerate(zip(range(start, start + len(cells)))):
            p = pos[0]
            mod = abs(p) % 5
            if p == 0:
                pos_line += " 0 "
            elif mod == 0:
                pos_line += f"{p:+d}"[-3:]
            else:
                pos_line += " · "
        try:
            stdscr.addstr(7, 0, pos_line[:w], curses.color_pair(4))
        except curses.error:
            pass

        # Divider
        stdscr.addstr(9, 0, "─" * w, curses.color_pair(4))

        # Transition rules display
        stdscr.addstr(10, 2, "Transition Rules:", curses.A_BOLD | curses.color_pair(3))
        y = 11
        displayed = 0
        for (s, r), t in sorted(machine.transitions.items()):
            if y >= h - 6:
                stdscr.addstr(y, 4, f"  ... and {len(machine.transitions) - displayed} more rules", curses.color_pair(4))
                break
            marker = "►" if s == state else " "
            color = curses.color_pair(6) if s == state else curses.color_pair(4)
            rule = f"{marker} ({s}, {r}) → ({t.next_state}, {t.write_symbol}, {t.direction})"
            try:
                stdscr.addstr(y, 4, rule, color)
            except curses.error:
                pass
            y += 1
            displayed += 1

        # Status bar
        stdscr.addstr(h - 3, 0, "─" * w, curses.color_pair(4))
        status = "PAUSED" if paused else ("STEP MODE" if step_mode else "RUNNING")
        status_color = curses.color_pair(5) if paused else (curses.color_pair(3) if step_mode else curses.color_pair(2))
        stdscr.addstr(h - 2, 2, f"Status: {status}", status_color)

        controls = "SPACE=Pause  S=Step  R=Reset  Q=Quit  +/-=Speed"
        stdscr.addstr(h - 1, 2, controls, curses.color_pair(4))

        stdscr.refresh()

    def init_colors():
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)

    init_colors()
    draw()

    while running:
        if not paused and not step_mode:
            # Execute a step
            current_symbol = tape.read(head_pos)
            transition = machine.step(state, current_symbol)

            if transition is None:
                # No transition — check if in accept/reject
                if state in machine.accept_states:
                    paused = True
                elif state in machine.reject_states:
                    paused = True
                else:
                    paused = True  # stuck
                draw()
                continue

            # Save history for potential rewind
            if steps < MAX_DISPLAY_STEPS:
                history.append((state, head_pos, dict(tape.cells)))

            # Execute transition
            tape.write(head_pos, transition.write_symbol)
            state = transition.next_state

            if transition.direction == "R":
                head_pos += 1
            elif transition.direction == "L":
                head_pos -= 1
            # 'S' = stay

            steps += 1

            # Check halt
            if state in machine.accept_states or state in machine.reject_states:
                paused = True

            draw()
            time.sleep(speed)

            if steps > MAX_DISPLAY_STEPS:
                paused = True

        else:
            # Wait for input
            draw()
            key = stdscr.getch()

            if key == ord('q') or key == ord('Q'):
                running = False
            elif key == ord(' '):
                if step_mode:
                    step_mode = False
                paused = not paused
            elif key == ord('s') or key == ord('S'):
                # Execute one step
                if not (state in machine.accept_states or state in machine.reject_states):
                    current_symbol = tape.read(head_pos)
                    transition = machine.step(state, current_symbol)
                    if transition:
                        if steps < MAX_DISPLAY_STEPS:
                            history.append((state, head_pos, dict(tape.cells)))
                        tape.write(head_pos, transition.write_symbol)
                        state = transition.next_state
                        if transition.direction == "R":
                            head_pos += 1
                        elif transition.direction == "L":
                            head_pos -= 1
                        steps += 1
            elif key == ord('r') or key == ord('R'):
                # Reset
                tape = Tape(blank=machine.blank_symbol)
                if machine.initial_tape:
                    for i, ch in enumerate(machine.initial_tape):
                        tape.write(i, ch)
                state = machine.initial_state
                head_pos = 0
                steps = 0
                history.clear()
                paused = False
                step_mode = False
            elif key == ord('+') or key == ord('='):
                speed = max(0.01, speed - 0.05)
            elif key == ord('-'):
                speed = min(2.0, speed + 0.05)


# ─── Non-interactive batch runner ────────────────────────────────────

def run_batch(machine: TuringMachine, max_steps: int = 10000) -> dict:
    """Run machine without visualization, return result dict."""
    tape = Tape(blank=machine.blank_symbol)
    if machine.initial_tape:
        for i, ch in enumerate(machine.initial_tape):
            tape.write(i, ch)

    state = machine.initial_state
    head_pos = 0
    steps = 0

    while steps < max_steps:
        current_symbol = tape.read(head_pos)
        transition = machine.step(state, current_symbol)

        if transition is None:
            break

        tape.write(head_pos, transition.write_symbol)
        state = transition.next_state

        if transition.direction == "R":
            head_pos += 1
        elif transition.direction == "L":
            head_pos -= 1

        steps += 1

        if state in machine.accept_states or state in machine.reject_states:
            break

    # Collect tape contents
    lo, hi = tape.non_blank_segment()
    tape_str = "".join(tape.read(i) for i in range(lo, hi + 1))

    return {
        "machine": machine.name,
        "input": machine.initial_tape or "(blank)",
        "output": tape_str,
        "final_state": state,
        "steps": steps,
        "accepted": state in machine.accept_states,
    }


# ─── Text-mode step display (no curses) ──────────────────────────────

def run_text(machine: TuringMachine, max_steps: int = 200, delay: float = 0.15):
    """Run with simple text output (fallback for non-terminal environments)."""
    tape = Tape(blank=machine.blank_symbol)
    if machine.initial_tape:
        for i, ch in enumerate(machine.initial_tape):
            tape.write(i, ch)

    state = machine.initial_state
    head_pos = 0
    steps = 0

    WINDOW = 30

    print(f"\n{'='*60}")
    print(f"  Machine: {machine.name.replace('_', ' ').title()}")
    print(f"  {machine.description}")
    print(f"  Input: {machine.initial_tape or '(blank)'}")
    print(f"{'='*60}\n")

    while steps < max_steps:
        cells = tape.to_string(head_pos, WINDOW)
        start = head_pos - WINDOW // 2

        # Build display
        tape_str = "".join(cells)
        head_idx = head_pos - start

        # Highlight head position
        left = tape_str[:head_idx]
        sym = tape_str[head_idx] if head_idx < len(tape_str) else machine.blank_symbol
        right = tape_str[head_idx + 1:]

        print(f"  Step {steps:4d}  State: {state}")
        print(f"  ...{left}[{sym}]{right}...")
        print()

        if state in machine.accept_states:
            print(f"  ✓ ACCEPTED after {steps} steps")
            break
        if state in machine.reject_states:
            print(f"  ✗ REJECTED after {steps} steps")
            break

        current_symbol = tape.read(head_pos)
        transition = machine.step(state, current_symbol)

        if transition is None:
            print(f"  ⚠ No transition for ({state}, {current_symbol}) — STUCK after {steps} steps")
            break

        tape.write(head_pos, transition.write_symbol)
        state = transition.next_state

        if transition.direction == "R":
            head_pos += 1
        elif transition.direction == "L":
            head_pos -= 1

        steps += 1
        time.sleep(delay)

    lo, hi = tape.non_blank_segment()
    final_tape = "".join(tape.read(i) for i in range(lo, hi + 1))
    print(f"\n  Final tape: {final_tape}")
    return {"steps": steps, "final_state": state, "output": final_tape}


# ─── Program editor (simple JSON-based) ──────────────────────────────

def create_custom_machine():
    """Interactively create a custom Turing machine."""
    print("\n╔══════════════════════════════════════════╗")
    print("║     Custom Turing Machine Creator       ║")
    print("╚══════════════════════════════════════════╝\n")

    name = input("Machine name (snake_case): ").strip() or "custom_machine"
    description = input("Description: ").strip() or "A custom Turing machine"
    initial_tape = input("Initial tape contents: ").strip()

    states_str = input("States (comma-separated, e.g. q0,q1,q_accept): ").strip()
    states = [s.strip() for s in states_str.split(",")] if states_str else ["q0", "q_accept"]

    alphabet_str = input("Alphabet (comma-separated, e.g. 0,1,_): ").strip()
    alphabet = [s.strip() for s in alphabet_str.split(",")] if alphabet_str else ["0", "1", "_"]

    blank = input("Blank symbol [default='_']: ").strip() or "_"
    initial_state = input(f"Initial state [default='{states[0]}']: ").strip() or states[0]

    accept_str = input("Accept states (comma-separated): ").strip()
    accept_states = [s.strip() for s in accept_str.split(",")] if accept_str else ["q_accept"]

    reject_str = input("Reject states (comma-separated): ").strip()
    reject_states = [s.strip() for s in reject_str.split(",")] if reject_str else ["q_reject"]

    transitions = {}
    print("\nNow enter transitions. Format: state,read -> next_state,write,direction")
    print("Enter empty line to finish.\n")

    while True:
        rule = input("  Rule: ").strip()
        if not rule:
            break
        try:
            lhs, rhs = rule.split("->")
            s, r = [x.strip() for x in lhs.split(",")]
            ns, w, d = [x.strip() for x in rhs.split(",")]
            transitions[(s, r)] = Transition(next_state=ns, write_symbol=w, direction=d)
        except (ValueError, IndexError):
            print("  Invalid format. Use: state,read -> next_state,write,direction")
            continue

    machine = TuringMachine(
        name=name, description=description, states=states, alphabet=alphabet,
        blank_symbol=blank, initial_state=initial_state, accept_states=accept_states,
        reject_states=reject_states, transitions=transitions, initial_tape=initial_tape
    )

    # Save to file
    filepath = os.path.expanduser(f"~/daily-ideas/2026-06-18-turing-machine-simulator/machines/{name}.json")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    save_machine(machine, filepath)
    print(f"\n  Saved to {filepath}")

    return machine


def save_machine(machine: TuringMachine, filepath: str):
    """Save a TuringMachine to JSON."""
    data = {
        "name": machine.name,
        "description": machine.description,
        "states": machine.states,
        "alphabet": machine.alphabet,
        "blank_symbol": machine.blank_symbol,
        "initial_state": machine.initial_state,
        "accept_states": machine.accept_states,
        "reject_states": machine.reject_states,
        "transitions": {
            f"{s},{r}": {"next_state": t.next_state, "write_symbol": t.write_symbol, "direction": t.direction}
            for (s, r), t in machine.transitions.items()
        },
        "initial_tape": machine.initial_tape,
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def load_machine(filepath: str) -> TuringMachine:
    """Load a TuringMachine from JSON."""
    with open(filepath) as f:
        data = json.load(f)

    transitions = {}
    for key, val in data["transitions"].items():
        s, r = key.split(",")
        transitions[(s, r)] = Transition(
            next_state=val["next_state"], write_symbol=val["write_symbol"], direction=val["direction"]
        )

    return TuringMachine(
        name=data["name"], description=data["description"], states=data["states"],
        alphabet=data["alphabet"], blank_symbol=data["blank_symbol"],
        initial_state=data["initial_state"], accept_states=data["accept_states"],
        reject_states=data["reject_states"], transitions=transitions,
        initial_tape=data.get("initial_tape", ""),
    )


# ─── Main entry point ───────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Turing Machine Simulator — Visual & batch modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 turing.py --visual          # Interactive visual mode (curses)
  python3 turing.py --list             # List built-in programs
  python3 turing.py --run busy_beaver_3   # Run specific program
  python3 turing.py --run all          # Run all programs in batch
  python3 turing.py --text             # Text-mode step display
  python3 turing.py --load machine.json # Load and run custom machine
        """
    )
    parser.add_argument("--visual", "-v", action="store_true", help="Launch visual (curses) mode")
    parser.add_argument("--list", "-l", action="store_true", help="List built-in programs")
    parser.add_argument("--run", "-r", metavar="NAME", help="Run a specific built-in program")
    parser.add_argument("--text", "-t", action="store_true", help="Text-mode step display")
    parser.add_argument("--speed", type=float, default=0.3, help="Step delay in seconds (default: 0.3)")
    parser.add_argument("--max-steps", type=int, default=10000, help="Max steps for batch mode")
    parser.add_argument("--load", metavar="FILE", help="Load a machine from JSON file")
    parser.add_argument("--create", action="store_true", help="Interactively create a custom machine")

    args = parser.parse_args()

    if args.list:
        print("\n╔══════════════════════════════════════════╗")
        print("║     Built-in Turing Machine Programs    ║")
        print("╚══════════════════════════════════════════╝\n")
        for key, machine in BUILTIN_PROGRAMS.items():
            print(f"  {key:25s} — {machine.description}")
            print(f"  {'':25s}   Input: {machine.initial_tape or '(blank)'}")
            print(f"  {'':25s}   States: {', '.join(machine.states)}")
            print(f"  {'':25s}   Transitions: {len(machine.transitions)}")
            print()
        return

    if args.create:
        machine = create_custom_machine()
        print(f"\nCreated machine: {machine.name}")
        # Ask if they want to run it
        run_choice = input("Run it now? (v=visual, t=text, n=no) [n]: ").strip().lower()
        if run_choice == "v":
            curses.wrapper(lambda stdscr: run_visual(stdscr, machine, args.speed))
        elif run_choice == "t":
            run_text(machine, delay=args.speed)
        return

    if args.load:
        machine = load_machine(args.load)
        print(f"Loaded: {machine.name} — {machine.description}")
        if args.visual:
            curses.wrapper(lambda stdscr: run_visual(stdscr, machine, args.speed))
        elif args.text:
            run_text(machine, delay=args.speed)
        else:
            result = run_batch(machine, args.max_steps)
            print(f"\nResult: {result}")
        return

    # Select a machine
    machine_name = args.run

    if args.visual or (not args.run and not args.text):
        # Default: show menu then run visual
        if not machine_name:
            print("\n╔══════════════════════════════════════════╗")
            print("║     Turing Machine Simulator            ║")
            print("╚══════════════════════════════════════════╝\n")
            print("Select a program to run:\n")
            keys = list(BUILTIN_PROGRAMS.keys())
            for i, key in enumerate(keys, 1):
                m = BUILTIN_PROGRAMS[key]
                print(f"  {i}. {key:25s} — {m.description}")
            print(f"  {len(keys)+1}. {'custom':25s} — Create your own machine")
            print()

            choice = input("Enter number (or name): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(keys):
                    machine_name = keys[idx]
                elif idx == len(keys):
                    # Launch interactive creator
                    machine = create_custom_machine()
                    print(f"\nLaunching visual mode with {machine.name}...")
                    curses.wrapper(lambda stdscr: run_visual(stdscr, machine, args.speed))
                    return
                else:
                    print("Invalid choice.")
                    return
            except ValueError:
                machine_name = choice

        if machine_name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {machine_name}")
            print(f"Available: {', '.join(BUILTIN_PROGRAMS.keys())}")
            return

        machine = BUILTIN_PROGRAMS[machine_name]
        curses.wrapper(lambda stdscr: run_visual(stdscr, machine, args.speed))

    elif args.run == "all":
        print("\n╔══════════════════════════════════════════╗")
        print("║     Batch Run — All Programs            ║")
        print("╚══════════════════════════════════════════╝\n")
        results = []
        for key, machine in BUILTIN_PROGRAMS.items():
            result = run_batch(machine, args.max_steps)
            results.append(result)
            status = "✓ ACCEPTED" if result["accepted"] else "✗ REJECTED"
            print(f"  {result['machine']:25s}  Input: {result['input']:15s}  "
                  f"Output: {result['output']:15s}  Steps: {result['steps']:5d}  {status}")
        print()

    elif args.text:
        if not machine_name:
            machine_name = "binary_increment"
        if machine_name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {machine_name}")
            return
        machine = BUILTIN_PROGRAMS[machine_name]
        run_text(machine, delay=args.speed)

    elif args.run:
        if machine_name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {machine_name}")
            return
        machine = BUILTIN_PROGRAMS[machine_name]
        result = run_batch(machine, args.max_steps)
        print(f"\nResult: {result}")


if __name__ == "__main__":
    main()