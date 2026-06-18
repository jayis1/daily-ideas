#!/usr/bin/env python3
"""
Turing Machine Simulator — A visual, interactive simulator for Turing machines
with built-in example programs, custom machine creation, validation, and
multiple execution modes (visual, text, batch, trace).

Version: 2.0.0
"""

import os
import sys
import time
import curses
import json
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List

__version__ = "2.0.0"

__all__ = [
    "Transition", "Tape", "TuringMachine", "ExecutionStats", "ExecutionStep",
    "BUILTIN_PROGRAMS", "run_batch", "run_text", "run_visual", "run_trace",
    "save_machine", "load_machine", "create_custom_machine",
    "export_dot", "compare_tapes", "machine_info",
]

# ─── Data structures ────────────────────────────────────────────────

@dataclass
class Transition:
    """A single transition rule: (state, read_symbol) -> (next_state, write_symbol, direction)."""
    next_state: str
    write_symbol: str
    direction: str  # 'L', 'R', 'S' (stay)

    def __repr__(self):
        return f"→ ({self.next_state}, {self.write_symbol}, {self.direction})"


@dataclass
class ExecutionStats:
    """Statistics collected during machine execution."""
    total_steps: int = 0
    cells_written: int = 0
    leftmost_visited: int = 0
    rightmost_visited: int = 0
    unique_cells_visited: int = 0

    def summary(self) -> str:
        """Return a human-readable summary of the execution statistics."""
        return (
            f"Steps: {self.total_steps}  "
            f"Cells written: {self.cells_written}  "
            f"Tape span: [{self.leftmost_visited}, {self.rightmost_visited}]  "
            f"Unique cells: {self.unique_cells_visited}"
        )


@dataclass
class ExecutionStep:
    """A single recorded step in an execution trace."""
    step_number: int
    state: str
    head_position: int
    symbol_read: str
    symbol_written: str
    direction: str
    next_state: str
    tape_snapshot: str


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
        """Look up the transition for (state, symbol), or None if undefined."""
        return self.transitions.get((state, symbol))

    def validate(self) -> List[str]:
        """Validate the machine definition and return a list of warnings (empty if valid)."""
        warnings = []

        # Check initial state is in states list
        if self.initial_state not in self.states:
            warnings.append(f"Initial state '{self.initial_state}' not in states list")

        # Check accept/reject states are in states list
        for s in self.accept_states:
            if s not in self.states:
                warnings.append(f"Accept state '{s}' not in states list")
        for s in self.reject_states:
            if s not in self.states:
                warnings.append(f"Reject state '{s}' not in states list")

        # Check that all transition states are known
        for (state, symbol), trans in self.transitions.items():
            if state not in self.states:
                warnings.append(f"Transition references unknown state '{state}'")
            if symbol not in self.alphabet and symbol != self.blank_symbol:
                warnings.append(f"Transition references unknown symbol '{symbol}'")
            if trans.next_state not in self.states:
                warnings.append(f"Transition targets unknown state '{trans.next_state}'")
            if trans.write_symbol not in self.alphabet and trans.write_symbol != self.blank_symbol:
                warnings.append(f"Transition writes unknown symbol '{trans.write_symbol}'")
            if trans.direction not in ("L", "R", "S"):
                warnings.append(f"Transition has invalid direction '{trans.direction}'")

        # Check for unreachable states (states never appearing as a transition target)
        reachable = {self.initial_state}
        for (s, _), trans in self.transitions.items():
            reachable.add(trans.next_state)
        unreachable = set(self.states) - reachable
        # Accept/reject states may be unreachable by design (they're targets)
        unreachable -= set(self.accept_states)
        unreachable -= set(self.reject_states)
        if unreachable:
            warnings.append(f"Potentially unreachable states: {', '.join(sorted(unreachable))}")

        # Check initial tape symbols are in alphabet
        for ch in self.initial_tape:
            if ch not in self.alphabet:
                warnings.append(f"Initial tape contains symbol '{ch}' not in alphabet")

        return warnings


class Tape:
    """An infinite tape implemented with a dict (sparse representation)."""

    def __init__(self, blank: str = "_"):
        self.cells: Dict[int, str] = {}
        self.blank = blank

    def read(self, pos: int) -> str:
        """Read the symbol at the given position."""
        return self.cells.get(pos, self.blank)

    def write(self, pos: int, symbol: str):
        """Write a symbol at the given position. Blank symbols are erased."""
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

    def get_contents(self) -> str:
        """Return the full non-blank tape contents as a string."""
        if not self.cells:
            return ""
        lo, hi = self.non_blank_segment()
        return "".join(self.read(i) for i in range(lo, hi + 1))


# ─── Built-in programs ──────────────────────────────────────────────

BUILTIN_PROGRAMS = {}

def _register(name, desc, states, alphabet, blank, initial, accept, reject, transitions, tape):
    """Register a built-in Turing machine program."""
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
            "q_back", "q_accept", "q_reject"],
    alphabet=["0", "1", "_", "X"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=["q_reject"],
    transitions={
        # Empty tape is palindrome
        ("q0", "_"): ("q_accept", "_", "S"),
        # Read leftmost symbol, mark it, go right
        ("q0", "0"): ("q_right0", "X", "R"),
        ("q0", "1"): ("q_right1", "X", "R"),
        # All characters marked — it's a palindrome
        ("q0", "X"): ("q_accept", "X", "S"),
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
        ("q_left0", "X"): ("q_accept", "X", "S"),  # single char or all marked
        ("q_left1", "1"): ("q_back", "X", "L"),
        ("q_left1", "0"): ("q_reject", "0", "S"),
        ("q_left1", "X"): ("q_accept", "X", "S"),  # single char or all marked
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
    states=["q0", "q1", "q2", "q3", "q5", "q_cleanup", "q_accept"],
    alphabet=["0", "1", "_", "=", "|", "Y"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=[],
    transitions={
        # Mark a 1 by changing it to Y, then go right to end and add a |
        ("q0", "0"): ("q0", "0", "R"),
        ("q0", "1"): ("q1", "Y", "R"),
        ("q0", "Y"): ("q0", "Y", "R"),     # skip already-counted 1s
        ("q0", "="): ("q_cleanup", "=", "L"),  # all 1s counted, clean up Ys
        # Scan right to end past 0s, 1s, =, and existing |s
        ("q1", "0"): ("q1", "0", "R"),
        ("q1", "1"): ("q1", "1", "R"),
        ("q1", "="): ("q1", "=", "R"),
        ("q1", "|"): ("q1", "|", "R"),
        ("q1", "Y"): ("q1", "Y", "R"),
        ("q1", "_"): ("q2", "|", "L"),
        # Go back left to find next unmarked 1
        ("q2", "|"): ("q2", "|", "L"),
        ("q2", "="): ("q2", "=", "L"),
        ("q2", "0"): ("q2", "0", "L"),
        ("q2", "1"): ("q2", "1", "L"),
        ("q2", "Y"): ("q0", "Y", "R"),
        ("q2", "_"): ("q3", "_", "R"),
        # No more Ys left of =, we're done scanning left — clean up Ys
        ("q3", "Y"): ("q3", "1", "R"),     # convert Y back to 1
        ("q3", "0"): ("q3", "0", "R"),
        ("q3", "1"): ("q3", "1", "R"),
        ("q3", "="): ("q3", "=", "R"),
        ("q3", "|"): ("q_accept", "|", "S"),

        # Cleanup state: go left converting Y→1 (reached via q0 on =)
        ("q_cleanup", "Y"): ("q_cleanup", "1", "L"),
        ("q_cleanup", "0"): ("q_cleanup", "0", "L"),
        ("q_cleanup", "1"): ("q_cleanup", "1", "L"),
        ("q_cleanup", "="): ("q_cleanup", "=", "L"),
        ("q_cleanup", "_"): ("q_accept", "_", "R"),  # reached start, done

        # No 1s found at all — just skip past = to accept
        ("q5", "|"): ("q5", "|", "R"),
        ("q5", "Y"): ("q5", "1", "R"),     # clean up Y markers
        ("q5", "="): ("q5", "=", "R"),
        ("q5", "_"): ("q_accept", "_", "S"),
    },
    tape="10110=",  # 3 ones → |||
)

# 7. Binary decrement — decrements a binary number by 1 (new!)
# Strategy: scan right to end, then borrow left, then strip leading zeros.
_register(
    "binary_decrement",
    "Decrement a binary number by 1 (e.g., 1100 → 1011, 1000 → 111)",
    states=["q0", "q_carry", "q_done", "q_strip", "q_accept", "q_reject"],
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
        # Borrow: turn 1→0 with borrow, 0→1 continue borrowing
        ("q_carry", "1"): ("q_done", "0", "L"),
        ("q_carry", "0"): ("q_carry", "1", "L"),
        ("q_carry", "_"): ("q_reject", "_", "S"),  # underflow (was 0)
        # Move back to start, then strip leading zeros
        ("q_done", "0"): ("q_done", "0", "L"),
        ("q_done", "1"): ("q_accept", "1", "S"),
        ("q_done", "_"): ("q_strip", "_", "R"),
        # Strip leading zeros (erase them by writing blank, skip past)
        ("q_strip", "0"): ("q_strip", "_", "R"),
        ("q_strip", "1"): ("q_accept", "1", "S"),
        ("q_strip", "_"): ("q_reject", "_", "S"),  # was 1 → now 0, edge case
    },
    tape="1100",  # 12 → 1011 (11)
)

# 8. Unary doubler — doubles a unary number (e.g., 111 → 111111)
# Strategy: Mark original 1s as X, use = as separator between originals and copies.
# After all originals are Xs, convert X→1, then shift copies left over the = position.
# The shift: erase =, then for each cell after it, move it one position left.
# This creates a "bubble" of blank that travels right until it reaches the end.
_register(
    "unary_doubler",
    "Double a unary number (e.g., 111 → 111111)",
    states=["q0", "q1", "q2", "q_back", "q_cleanup", "q_find_eq", "q_shift", "q_shift_back", "q_shift_next", "q_accept"],
    alphabet=["1", "_", "X", "="],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=[],
    transitions={
        # q0: find leftmost unmarked 1 among originals (before =)
        ("q0", "1"): ("q1", "X", "R"),
        ("q0", "X"): ("q0", "X", "R"),
        ("q0", "="): ("q_cleanup", "=", "L"),  # all originals marked, start cleanup
        ("q0", "_"): ("q_accept", "_", "S"),     # empty input

        # q1: scan to find end, placing = on first pass
        ("q1", "1"): ("q1", "1", "R"),
        ("q1", "X"): ("q1", "X", "R"),
        ("q1", "="): ("q2", "=", "R"),
        ("q1", "_"): ("q2", "=", "R"),     # first time: place = separator, go right past it

        # q2: go past copies (and Xs) to find end and append a 1
        ("q2", "1"): ("q2", "1", "R"),
        ("q2", "="): ("q2", "=", "R"),
        ("q2", "X"): ("q2", "X", "R"),       # skip marked originals (e.g., single 1 input)
        ("q2", "_"): ("q_back", "1", "L"),

        # q_back: go all the way back to start
        ("q_back", "1"): ("q_back", "1", "L"),
        ("q_back", "="): ("q_back", "=", "L"),
        ("q_back", "X"): ("q_back", "X", "L"),
        ("q_back", "_"): ("q0", "_", "R"),

        # q_cleanup: convert Xs to 1s (going left from = position)
        ("q_cleanup", "X"): ("q_cleanup", "1", "L"),
        ("q_cleanup", "_"): ("q_find_eq", "_", "R"),

        # q_find_eq: scan right to find = separator
        ("q_find_eq", "1"): ("q_find_eq", "1", "R"),
        ("q_find_eq", "="): ("q_shift", "_", "R"),  # erase =, begin shifting

        # q_shift: move each 1 one position left to fill the gap.
        # We just erased = (wrote _). We're at the cell right of it.
        # The "gap" (blank) travels right as we swap each 1 left.
        ("q_shift", "1"): ("q_shift_back", "_", "L"),   # swap this 1 into the gap
        ("q_shift", "_"): ("q_shift_next", "_", "R"),    # skip gap, look for next 1

        # q_shift_next: we're past the gap, find next 1 to shift
        ("q_shift_next", "1"): ("q_shift_back", "_", "L"),  # found 1, swap it into gap
        ("q_shift_next", "_"): ("q_accept", "_", "S"),      # no more 1s, done

        # q_shift_back: write 1 at the gap position, then go right to the next cell
        ("q_shift_back", "_"): ("q_shift", "1", "R"),    # filled gap, continue
    },
    tape="111",  # 3 → 6 ones
)

# 9. Binary AND — bitwise AND of two equal-length binary strings separated by '&'
# Strategy: Process bit by bit from left to right. For each position:
#   1. Read leftmost unprocessed left bit, mark it (X=was0, Y=was1)
#   2. Go right past &, skip already-processed markers on right
#   3. Process the right bit: if left was 0, write X (result=0); if left was 1, keep right bit as-is (mark X for 0, Y for 1)
#   4. Go back left and repeat
#   5. When all done, convert X→0 and Y→1
_register(
    "binary_and",
    "Bitwise AND of two equal-length binary strings separated by '&' (e.g., 1100&1010=1000)",
    states=["q0", "q_left0", "q_left1", "q_right0", "q_right1", "q_back", "q_left_cleanup", "q_done", "q_accept"],
    alphabet=["0", "1", "&", "_", "X", "Y"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=[],
    transitions={
        # q0: find leftmost unprocessed bit on left side
        ("q0", "0"): ("q_left0", "X", "R"),     # left bit is 0, mark it
        ("q0", "1"): ("q_left1", "Y", "R"),     # left bit is 1, mark it
        ("q0", "X"): ("q0", "X", "R"),           # skip processed 0 on left
        ("q0", "Y"): ("q0", "Y", "R"),           # skip processed 1 on left
        ("q0", "&"): ("q_left_cleanup", "&", "L"),      # all left bits processed, clean left markers

        # q_left0: left bit was 0 — go right to find & then the right operand
        ("q_left0", "0"): ("q_left0", "0", "R"),
        ("q_left0", "1"): ("q_left0", "1", "R"),
        ("q_left0", "X"): ("q_left0", "X", "R"),
        ("q_left0", "Y"): ("q_left0", "Y", "R"),
        ("q_left0", "&"): ("q_right0", "&", "R"),

        # q_right0: in right operand, skip processed markers, result is always 0
        ("q_right0", "X"): ("q_right0", "X", "R"),   # skip processed 0 on right
        ("q_right0", "Y"): ("q_right0", "Y", "R"),   # skip processed 1 on right
        ("q_right0", "0"): ("q_back", "X", "L"),     # 0 AND 0 = 0, write X
        ("q_right0", "1"): ("q_back", "X", "L"),     # 0 AND 1 = 0, write X
        ("q_right0", "_"): ("q_accept", "_", "S"),    # right side shorter — done

        # q_left1: left bit was 1 — go right to find & then the right operand
        ("q_left1", "0"): ("q_left1", "0", "R"),
        ("q_left1", "1"): ("q_left1", "1", "R"),
        ("q_left1", "X"): ("q_left1", "X", "R"),
        ("q_left1", "Y"): ("q_left1", "Y", "R"),
        ("q_left1", "&"): ("q_right1", "&", "R"),

        # q_right1: in right operand, skip processed markers, result = right bit
        ("q_right1", "X"): ("q_right1", "X", "R"),   # skip processed 0 on right
        ("q_right1", "Y"): ("q_right1", "Y", "R"),   # skip processed 1 on right
        ("q_right1", "0"): ("q_back", "X", "L"),     # 1 AND 0 = 0, write X
        ("q_right1", "1"): ("q_back", "Y", "L"),     # 1 AND 1 = 1, write Y
        ("q_right1", "_"): ("q_accept", "_", "S"),    # right side shorter — done

        # q_back: go all the way back to start
        ("q_back", "0"): ("q_back", "0", "L"),
        ("q_back", "1"): ("q_back", "1", "L"),
        ("q_back", "&"): ("q_back", "&", "L"),
        ("q_back", "X"): ("q_back", "X", "L"),
        ("q_back", "Y"): ("q_back", "Y", "L"),
        ("q_back", "_"): ("q0", "_", "R"),

        # q_left_cleanup: convert X→0 and Y→1 on left side, then go right to clean right side
        ("q_left_cleanup", "X"): ("q_left_cleanup", "0", "L"),
        ("q_left_cleanup", "Y"): ("q_left_cleanup", "1", "L"),
        ("q_left_cleanup", "_"): ("q_done", "_", "R"),

        # q_done: convert X→0 and Y→1 on right side
        ("q_done", "X"): ("q_done", "0", "R"),
        ("q_done", "Y"): ("q_done", "1", "R"),
        ("q_done", "&"): ("q_done", "&", "R"),
        ("q_done", "0"): ("q_done", "0", "R"),
        ("q_done", "1"): ("q_done", "1", "R"),
        ("q_done", "_"): ("q_accept", "_", "S"),
    },
    tape="1100&1010",  # 12 AND 10 = 8 → after &: 1000
)

# 10. String reverser — reverses a binary string
# Strategy: Use = as a separator between input and output areas.
# 1. First, place = at the end of the input string.
# 2. Repeatedly: find the rightmost unprocessed char (just left of = or markers),
#    erase it (write X), remember it, go right past = to the end, write the char.
# 3. When all input chars are processed, clean up X markers and =.
_register(
    "string_reverser",
    "Reverse a binary string (e.g., 110 → 011)",
    states=[
        "q_init",       # initial state: scan right, place = at end
        "q0",           # scan right to find = separator
        "q_left",       # go left from = to find rightmost input char
        "q_found0",     # found a 0 on input side, go right past =
        "q_found1",     # found a 1 on input side, go right past =
        "q_seek_end0",  # scan right past = and output to write 0
        "q_seek_end1",  # scan right past = and output to write 1
        "q_back",       # go back left to start next iteration
        "q_cleanup",    # erase X markers and =
        "q_accept",
    ],
    alphabet=["0", "1", "_", "X", "="],
    blank="_",
    initial="q_init",
    accept=["q_accept"],
    reject=[],
    transitions={
        # q_init: scan right to end of input, place = separator
        ("q_init", "0"): ("q_init", "0", "R"),
        ("q_init", "1"): ("q_init", "1", "R"),
        ("q_init", "_"): ("q0", "=", "L"),   # place = at end, go back left

        # q0: scan right to find = separator, then go left to find input char
        ("q0", "0"): ("q0", "0", "R"),
        ("q0", "1"): ("q0", "1", "R"),
        ("q0", "X"): ("q0", "X", "R"),
        ("q0", "="): ("q_left", "=", "L"),     # found separator, go left
        ("q0", "_"): ("q_cleanup", "_", "R"),   # no input chars, go to cleanup

        # q_left: find the rightmost unprocessed input char (left of =)
        ("q_left", "0"): ("q_found0", "X", "L"),  # erase it, remember 0
        ("q_left", "1"): ("q_found1", "X", "L"),  # erase it, remember 1
        ("q_left", "X"): ("q_left", "X", "L"),     # skip erased positions
        ("q_left", "_"): ("q_cleanup", "_", "R"),  # no more input, go to cleanup

        # q_found0: we erased a 0, go right to find = and then the output area
        ("q_found0", "0"): ("q_found0", "0", "R"),
        ("q_found0", "1"): ("q_found0", "1", "R"),
        ("q_found0", "X"): ("q_found0", "X", "R"),
        ("q_found0", "="): ("q_seek_end0", "=", "R"),  # past separator
        ("q_found0", "_"): ("q_found0", "_", "R"),     # past left edge, go right

        # q_found1: we erased a 1, go right to find = and then the output area
        ("q_found1", "0"): ("q_found1", "0", "R"),
        ("q_found1", "1"): ("q_found1", "1", "R"),
        ("q_found1", "X"): ("q_found1", "X", "R"),
        ("q_found1", "="): ("q_seek_end1", "=", "R"),  # past separator
        ("q_found1", "_"): ("q_found1", "_", "R"),     # past left edge, go right

        # q_seek_end0: scan past existing output to write 0
        ("q_seek_end0", "0"): ("q_seek_end0", "0", "R"),
        ("q_seek_end0", "1"): ("q_seek_end0", "1", "R"),
        ("q_seek_end0", "_"): ("q_back", "0", "L"),    # write 0 at end

        # q_seek_end1: scan past existing output to write 1
        ("q_seek_end1", "0"): ("q_seek_end1", "0", "R"),
        ("q_seek_end1", "1"): ("q_seek_end1", "1", "R"),
        ("q_seek_end1", "_"): ("q_back", "1", "L"),    # write 1 at end

        # q_back: go back left to find = and restart
        ("q_back", "0"): ("q_back", "0", "L"),
        ("q_back", "1"): ("q_back", "1", "L"),
        ("q_back", "="): ("q0", "=", "L"),    # restart: go left from =

        # q_cleanup: erase X markers and = separator
        ("q_cleanup", "X"): ("q_cleanup", "_", "R"),
        ("q_cleanup", "="): ("q_cleanup", "_", "R"),
        ("q_cleanup", "0"): ("q_cleanup", "0", "R"),
        ("q_cleanup", "1"): ("q_cleanup", "1", "R"),
        ("q_cleanup", "_"): ("q_accept", "_", "S"),
    },
    tape="110",  # 110 reversed = 011
)

# 11. Unary subtractor — subtracts second unary number from first (separated by '-')
# Strategy: Erase one 1 from the first number for each 1 in the second number.
# Find a 1 in the second number, mark it M, then go left to find - and erase
# the rightmost 1 from the first number. Repeat until all second-number 1s are M.
# Then clean up: erase - and all Ms.
_register(
    "unary_subtract",
    "Subtract two unary numbers separated by '-' (e.g., 11111-11=111)",
    states=[
        "q0",            # scan right to find - separator
        "q_find_one",    # in second operand, find next unmarked 1
        "q_mark",        # found a 1, mark it M, go left to find -
        "q_erase_one",   # go left past - to find rightmost 1 in first number
        "q_go_right",    # go right past - to get back to second operand
        "q_cleanup",     # erase Ms going left
        "q_cleanup2",    # skip past first-number 1s going right, accept
        "q_accept",
        "q_reject",
    ],
    alphabet=["1", "-", "M", "_"],
    blank="_",
    initial="q0",
    accept=["q_accept"],
    reject=["q_reject"],
    transitions={
        # q0: scan right to find - separator
        ("q0", "1"): ("q0", "1", "R"),
        ("q0", "-"): ("q_find_one", "-", "R"),

        # q_find_one: find next unmarked 1 in second number
        ("q_find_one", "1"): ("q_mark", "M", "L"),    # mark it, go left
        ("q_find_one", "M"): ("q_find_one", "M", "R"), # skip marked
        ("q_find_one", "_"): ("q_cleanup", "_", "L"),  # no more 1s, done

        # q_mark: go left to find - separator
        ("q_mark", "M"): ("q_mark", "M", "L"),
        ("q_mark", "1"): ("q_mark", "1", "L"),
        ("q_mark", "-"): ("q_erase_one", "-", "L"),

        # q_erase_one: scan left through first number to find rightmost 1 and erase it
        ("q_erase_one", "1"): ("q_go_right", "_", "R"),  # found and erased a 1
        ("q_erase_one", "_"): ("q_erase_one", "_", "L"), # skip blanks (already erased)
        ("q_erase_one", "-"): ("q_reject", "-", "S"),   # shouldn't reach here

        # q_go_right: go right through first number to find - and get back to second operand
        ("q_go_right", "1"): ("q_go_right", "1", "R"),
        ("q_go_right", "_"): ("q_go_right", "_", "R"),
        ("q_go_right", "-"): ("q_find_one", "-", "R"),

        # q_cleanup: erase all Ms going left
        ("q_cleanup", "M"): ("q_cleanup", "_", "L"),
        ("q_cleanup", "-"): ("q_cleanup2", "_", "R"),

        # q_cleanup2: skip past remaining first-number 1s, we're done
        ("q_cleanup2", "_"): ("q_accept", "_", "S"),
        ("q_cleanup2", "1"): ("q_cleanup2", "1", "R"),
    },
    tape="11111-11",  # 5 - 2 = 3 ones: 111
)

# 12. Unary multiplier — multiplies two unary numbers separated by 'x'
# Strategy: Place = at end as result separator. For each 1 in first number (mark as A),
# for each 1 in second number (mark as B), append 1 after =. Restore B→1 after each
# inner loop, restore A→1 after all outer loops. Final tape: 11x111=111111
_register(
    "unary_multiplier",
    "Multiply two unary numbers separated by 'x' (e.g., 11x111 → 11x111=111111)",
    states=[
        "q_init",        # scan right to end, place = separator
        "q_left",        # go left to start of first number
        "q0",            # find leftmost unmarked 1 in first number, mark it A
        "q_scan_x",      # scan right to find x
        "q_find_B",      # find leftmost unmarked 1 in second number, mark it B
        "q_goto_eq",     # scan right past remaining second number to find =
        "q_find_end",    # go right past result 1s, write 1 at end
        "q_back2x",      # go left back to x to restart inner loop
        "q_restore_B",   # all B's become 1s again (inner loop done)
        "q_back2first",  # go left to find next 1 in first number
        "q_cleanup",     # convert A→1 in first number, then accept
        "q_accept",
    ],
    alphabet=["1", "x", "=", "A", "B", "_"],
    blank="_",
    initial="q_init",
    accept=["q_accept"],
    reject=[],
    transitions={
        # q_init: scan right to end of tape, place = separator
        ("q_init", "1"): ("q_init", "1", "R"),
        ("q_init", "x"): ("q_init", "x", "R"),
        ("q_init", "_"): ("q_left", "=", "L"),

        # q_left: go all the way left to start of first number
        ("q_left", "1"): ("q_left", "1", "L"),
        ("q_left", "x"): ("q_left", "x", "L"),
        ("q_left", "="): ("q_left", "=", "L"),
        ("q_left", "A"): ("q_left", "A", "L"),
        ("q_left", "B"): ("q_left", "B", "L"),
        ("q_left", "_"): ("q0", "_", "R"),    # at left edge, go right

        # q0: find leftmost 1 in first number, mark it A
        ("q0", "1"): ("q_scan_x", "A", "R"),    # mark it, start scanning
        ("q0", "A"): ("q0", "A", "R"),          # skip already marked
        ("q0", "x"): ("q_cleanup", "x", "L"),  # all first-number 1s processed

        # q_scan_x: scan right to find x separator
        ("q_scan_x", "1"): ("q_scan_x", "1", "R"),
        ("q_scan_x", "A"): ("q_scan_x", "A", "R"),
        ("q_scan_x", "x"): ("q_find_B", "x", "R"),

        # q_find_B: find leftmost unmarked 1 in second number, mark it B
        ("q_find_B", "1"): ("q_goto_eq", "B", "R"),   # mark as B
        ("q_find_B", "B"): ("q_find_B", "B", "R"),     # skip already marked
        ("q_find_B", "="): ("q_restore_B", "=", "L"),  # all 1s marked for this iteration

        # q_goto_eq: scan right past remaining chars to find = separator
        ("q_goto_eq", "1"): ("q_goto_eq", "1", "R"),
        ("q_goto_eq", "B"): ("q_goto_eq", "B", "R"),
        ("q_goto_eq", "="): ("q_find_end", "=", "R"),

        # q_find_end: go right past result 1s, append 1 at end
        ("q_find_end", "1"): ("q_find_end", "1", "R"),
        ("q_find_end", "_"): ("q_back2x", "1", "L"),

        # q_back2x: go left back to x to restart inner loop
        ("q_back2x", "1"): ("q_back2x", "1", "L"),
        ("q_back2x", "="): ("q_back2x", "=", "L"),
        ("q_back2x", "B"): ("q_back2x", "B", "L"),
        ("q_back2x", "x"): ("q_find_B", "x", "R"),

        # q_restore_B: convert B markers back to 1 in second number (inner loop done)
        ("q_restore_B", "B"): ("q_restore_B", "1", "L"),
        ("q_restore_B", "x"): ("q_back2first", "x", "L"),

        # q_back2first: go left to start, find next unmarked 1 in first number
        ("q_back2first", "1"): ("q_back2first", "1", "L"),
        ("q_back2first", "A"): ("q_back2first", "A", "L"),
        ("q_back2first", "x"): ("q_back2first", "x", "L"),
        ("q_back2first", "_"): ("q0", "_", "R"),

        # q_cleanup: convert A markers back to 1 (going left), then accept
        ("q_cleanup", "A"): ("q_cleanup", "1", "L"),
        ("q_cleanup", "_"): ("q_accept", "_", "S"),
    },
    tape="11x111",  # 2 * 3 = 6 ones, output: 11x111=111111
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
    stats = ExecutionStats()

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

        # Tape indices (head marker)
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

        # Position numbers
        pos_line = "  "
        for i, pos in enumerate(range(start, start + len(cells))):
            if pos == 0:
                pos_line += " 0 "
            elif abs(pos) % 5 == 0:
                pos_line += f"{pos:+d}"[-3:]
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
        current_symbol = tape.read(head_pos)
        for (s, r), t in sorted(machine.transitions.items()):
            if y >= h - 6:
                remaining = len(machine.transitions) - displayed
                stdscr.addstr(y, 4, f"  ... and {remaining} more rules", curses.color_pair(4))
                break
            # Highlight active state; extra highlight for the currently applicable transition
            if s == state and r == current_symbol:
                marker = "▶"
                color = curses.color_pair(2) | curses.A_BOLD
            elif s == state:
                marker = "►"
                color = curses.color_pair(6)
            else:
                marker = " "
                color = curses.color_pair(4)
            rule = f"{marker} ({s}, {r}) → ({t.next_state}, {t.write_symbol}, {t.direction})"
            try:
                stdscr.addstr(y, 4, rule, color)
            except curses.error:
                pass
            y += 1
            displayed += 1

        # Status bar with stats
        stdscr.addstr(h - 3, 0, "─" * w, curses.color_pair(4))
        status = "PAUSED" if paused else ("STEP MODE" if step_mode else "RUNNING")
        status_color = curses.color_pair(5) if paused else (curses.color_pair(3) if step_mode else curses.color_pair(2))
        stdscr.addstr(h - 2, 2, f"Status: {status}  |  {stats.summary()}", status_color)

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

            # Update stats
            stats.total_steps = steps + 1
            stats.cells_written += 1
            stats.leftmost_visited = min(stats.leftmost_visited, head_pos)
            stats.rightmost_visited = max(stats.rightmost_visited, head_pos)
            stats.unique_cells_visited = len(tape.cells) if tape.cells else 0

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
                        stats.total_steps = steps + 1
                        stats.cells_written += 1
                        stats.leftmost_visited = min(stats.leftmost_visited, head_pos)
                        stats.rightmost_visited = max(stats.rightmost_visited, head_pos)
                        stats.unique_cells_visited = len(tape.cells) if tape.cells else 0
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
                stats = ExecutionStats()
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
    stats = ExecutionStats()

    while steps < max_steps:
        current_symbol = tape.read(head_pos)
        transition = machine.step(state, current_symbol)

        if transition is None:
            break

        tape.write(head_pos, transition.write_symbol)
        state = transition.next_state

        # Update stats
        stats.cells_written += 1
        stats.leftmost_visited = min(stats.leftmost_visited, head_pos)
        stats.rightmost_visited = max(stats.rightmost_visited, head_pos)
        stats.unique_cells_visited = len(tape.cells) if tape.cells else 0

        if transition.direction == "R":
            head_pos += 1
        elif transition.direction == "L":
            head_pos -= 1

        steps += 1

        if state in machine.accept_states or state in machine.reject_states:
            break

    # Collect tape contents
    tape_str = tape.get_contents()

    stats.total_steps = steps

    return {
        "machine": machine.name,
        "input": machine.initial_tape or "(blank)",
        "output": tape_str,
        "final_state": state,
        "steps": steps,
        "accepted": state in machine.accept_states,
        "stats": stats,
    }


# ─── Execution trace (detailed step log) ──────────────────────────────

def run_trace(machine: TuringMachine, max_steps: int = 10000) -> List[ExecutionStep]:
    """Run machine and return a detailed trace of every step.

    Each step records the state, head position, symbol read/written,
    direction, next state, and a tape snapshot. Useful for debugging,
    analysis, and educational purposes.
    """
    tape = Tape(blank=machine.blank_symbol)
    if machine.initial_tape:
        for i, ch in enumerate(machine.initial_tape):
            tape.write(i, ch)

    state = machine.initial_state
    head_pos = 0
    steps = 0
    trace: List[ExecutionStep] = []

    while steps < max_steps:
        current_symbol = tape.read(head_pos)
        transition = machine.step(state, current_symbol)

        if transition is None:
            break

        tape.write(head_pos, transition.write_symbol)

        trace.append(ExecutionStep(
            step_number=steps,
            state=state,
            head_position=head_pos,
            symbol_read=current_symbol,
            symbol_written=transition.write_symbol,
            direction=transition.direction,
            next_state=transition.next_state,
            tape_snapshot=tape.get_contents(),
        ))

        state = transition.next_state

        if transition.direction == "R":
            head_pos += 1
        elif transition.direction == "L":
            head_pos -= 1

        steps += 1

        if state in machine.accept_states or state in machine.reject_states:
            break

    return trace


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
    stats = ExecutionStats()

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

        # Update stats
        stats.cells_written += 1
        stats.leftmost_visited = min(stats.leftmost_visited, head_pos)
        stats.rightmost_visited = max(stats.rightmost_visited, head_pos)
        stats.unique_cells_visited = len(tape.cells) if tape.cells else 0

        if transition.direction == "R":
            head_pos += 1
        elif transition.direction == "L":
            head_pos -= 1

        steps += 1
        time.sleep(delay)

    final_tape = tape.get_contents()
    stats.total_steps = steps
    print(f"\n  Final tape: {final_tape}")
    print(f"  {stats.summary()}")
    return {"steps": steps, "final_state": state, "output": final_tape, "stats": stats}


# ─── Program editor (simple JSON-based) ──────────────────────────────

def create_custom_machine():
    """Interactively create a custom Turing machine."""
    print("\n╔══════════════════════════════════════════╗")
    print("║     Custom Turing Machine Creator       ║")
    print("╚══════════════════════════════════════════╝\n")

    name = input("Machine name (snake_case): ").strip() or "custom_machine"
    # Sanitize name for use as filename
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
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
            if d not in ("L", "R", "S"):
                print(f"  ⚠ Invalid direction '{d}'. Use L, R, or S.")
                continue
            transitions[(s, r)] = Transition(next_state=ns, write_symbol=w, direction=d)
        except (ValueError, IndexError):
            print("  Invalid format. Use: state,read -> next_state,write,direction")
            continue

    machine = TuringMachine(
        name=safe_name, description=description, states=states, alphabet=alphabet,
        blank_symbol=blank, initial_state=initial_state, accept_states=accept_states,
        reject_states=reject_states, transitions=transitions, initial_tape=initial_tape
    )

    # Validate the machine
    warnings = machine.validate()
    if warnings:
        print(f"\n  ⚠ Validation warnings:")
        for w in warnings:
            print(f"    - {w}")
    else:
        print(f"\n  ✓ Machine definition looks valid!")

    # Save to file
    filepath = os.path.expanduser(f"~/daily-ideas/2026-06-18-turing-machine-simulator/machines/{safe_name}.json")
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
    """Load a TuringMachine from JSON.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required fields are missing from the JSON data.
        ValueError: If transition keys have unexpected format.
    """
    with open(filepath) as f:
        data = json.load(f)

    # Validate required top-level fields
    required_fields = ["name", "description", "states", "alphabet", "blank_symbol",
                       "initial_state", "accept_states", "reject_states", "transitions"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise KeyError(f"Missing required fields in machine JSON: {', '.join(missing)}")

    transitions = {}
    for key, val in data["transitions"].items():
        parts = key.split(",")
        if len(parts) != 2:
            raise ValueError(f"Invalid transition key '{key}': expected 'state,symbol' format")
        s, r = parts
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


# ─── Additional utility functions ──────────────────────────────────

def export_dot(machine: TuringMachine, filepath: str = None) -> str:
    """Export a Turing machine's state diagram as Graphviz DOT format.

    Generates a directed graph showing all states and transitions.
    Accept states are rendered with double borders. Transitions are
    labeled with 'read -> write, dir'.

    Args:
        machine: The TuringMachine to export.
        filepath: Optional file path to write the DOT source to.
                  If None, the DOT source is only returned as a string.

    Returns:
        The DOT source code as a string.
    """
    lines = [
        "digraph TuringMachine {",
        f'  label="{machine.name}: {machine.description}";',
        "  rankdir=LR;",
        "  node [shape=circle];",
        '  __blank [label="" shape=point];',
        f'  __blank -> {machine.initial_state} [label="start"];',
        "",
    ]

    # Mark accept states
    for state in machine.accept_states:
        lines.append(f"  {state} [shape=doublecircle];")

    # Mark reject states
    for state in machine.reject_states:
        lines.append(f"  {state} [shape=triangle];")

    lines.append("")

    # Group transitions by (from_state, to_state) for edge consolidation
    edge_labels = {}
    for (state, symbol), trans in machine.transitions.items():
        key = (state, trans.next_state)
        label = f"{symbol} -> {trans.write_symbol}, {trans.direction}"
        if key in edge_labels:
            edge_labels[key] += "\\n" + label
        else:
            edge_labels[key] = label

    for (from_state, to_state), label in edge_labels.items():
        lines.append(f'  {from_state} -> {to_state} [label="{label}"];')

    lines.append("}")

    dot_source = "\n".join(lines)

    if filepath:
        with open(filepath, "w") as f:
            f.write(dot_source)

    return dot_source


def compare_tapes(tape1: Tape, tape2: Tape) -> dict:
    """Compare two tapes and return a detailed comparison.

    Useful for verifying machine outputs against expected results.

    Args:
        tape1: First tape to compare.
        tape2: Second tape to compare.

    Returns:
        A dict with keys:
            'match': bool - whether the tape contents match exactly
            'contents1': str - non-blank contents of tape1
            'contents2': str - non-blank contents of tape2
            'diff_positions': list of (pos, val1, val2) tuples where they differ
    """
    contents1 = tape1.get_contents()
    contents2 = tape2.get_contents()
    match = contents1 == contents2

    all_positions = set(tape1.cells.keys()) | set(tape2.cells.keys())
    diff_positions = []
    for pos in sorted(all_positions):
        v1 = tape1.read(pos)
        v2 = tape2.read(pos)
        if v1 != v2:
            diff_positions.append((pos, v1, v2))

    return {
        "match": match,
        "contents1": contents1,
        "contents2": contents2,
        "diff_positions": diff_positions,
    }


def machine_info(machine: TuringMachine) -> dict:
    """Return a summary dict of machine properties for display or inspection.

    Args:
        machine: The TuringMachine to inspect.

    Returns:
        A dict with keys: name, description, num_states, num_transitions,
        alphabet, accept_states, reject_states, initial_state, initial_tape.
    """
    return {
        "name": machine.name,
        "description": machine.description,
        "num_states": len(machine.states),
        "num_transitions": len(machine.transitions),
        "alphabet": sorted(machine.alphabet),
        "accept_states": list(machine.accept_states),
        "reject_states": list(machine.reject_states),
        "initial_state": machine.initial_state,
        "initial_tape": machine.initial_tape,
    }


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
  python3 turing.py --trace --run binary_increment  # Detailed step-by-step trace
  python3 turing.py --load machine.json # Load and run custom machine
  python3 turing.py --tape 1010 --run binary_increment  # Override tape input
  python3 turing.py --validate --run binary_increment    # Validate before running
        """
    )
    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--visual", "-v", action="store_true", help="Launch visual (curses) mode")
    parser.add_argument("--list", "-l", action="store_true", help="List built-in programs")
    parser.add_argument("--run", "-r", metavar="NAME", help="Run a specific built-in program")
    parser.add_argument("--text", "-t", action="store_true", help="Text-mode step display")
    parser.add_argument("--speed", type=float, default=0.3, help="Step delay in seconds (default: 0.3)")
    parser.add_argument("--max-steps", type=int, default=10000, help="Max steps for batch mode")
    parser.add_argument("--load", metavar="FILE", help="Load a machine from JSON file")
    parser.add_argument("--create", action="store_true", help="Interactively create a custom machine")
    parser.add_argument("--tape", metavar="TAPE", help="Override initial tape contents for built-in programs")
    parser.add_argument("--validate", action="store_true", help="Validate machine definition before running")
    parser.add_argument("--trace", action="store_true", help="Print a detailed execution trace (each step)")
    parser.add_argument("--export", metavar="NAME", help="Export a built-in machine to JSON (e.g., 'busy_beaver_3')")
    parser.add_argument("--info", "-i", metavar="NAME", help="Show detailed info about a built-in machine")
    parser.add_argument("--dot", metavar="NAME", help="Export a built-in machine's state diagram as Graphviz DOT format")

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

    if args.export:
        name = args.export
        if name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {name}")
            print(f"Available: {', '.join(BUILTIN_PROGRAMS.keys())}")
            sys.exit(1)
        machine = BUILTIN_PROGRAMS[name]
        out_dir = os.path.expanduser("~/daily-ideas/2026-06-18-turing-machine-simulator/machines")
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, f"{name}.json")
        save_machine(machine, filepath)
        print(f"Exported '{name}' to {filepath}")
        return

    if args.info:
        name = args.info
        if name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {name}")
            print(f"Available: {', '.join(BUILTIN_PROGRAMS.keys())}")
            sys.exit(1)
        machine = BUILTIN_PROGRAMS[name]
        info = machine_info(machine)
        print(f"\n{'='*60}")
        print(f"  Machine: {info['name']}")
        print(f"  Description: {info['description']}")
        print(f"  States ({info['num_states']}): {', '.join(machine.states)}")
        print(f"  Transitions: {info['num_transitions']}")
        print(f"  Alphabet: {', '.join(info['alphabet'])}")
        print(f"  Blank symbol: {machine.blank_symbol}")
        print(f"  Initial state: {info['initial_state']}")
        print(f"  Accept states: {', '.join(info['accept_states'])}")
        print(f"  Reject states: {', '.join(info['reject_states'])}")
        print(f"  Initial tape: {info['initial_tape'] or '(blank)'}")
        warnings = machine.validate()
        if warnings:
            print(f"\n  Validation warnings:")
            for w in warnings:
                print(f"    - {w}")
        else:
            print(f"\n  Validation: OK")
        print(f"{'='*60}\n")
        return

    if args.dot:
        name = args.dot
        if name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {name}")
            print(f"Available: {', '.join(BUILTIN_PROGRAMS.keys())}")
            sys.exit(1)
        machine = BUILTIN_PROGRAMS[name]
        dot_source = export_dot(machine)
        print(dot_source)
        return

    if args.create:
        machine = create_custom_machine()
        print(f"\nCreated machine: {machine.name}")
        # Ask if they want to run it
        try:
            run_choice = input("Run it now? (v=visual, t=text, n=no) [n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if run_choice == "v":
            try:
                curses.wrapper(lambda stdscr: run_visual(stdscr, machine, args.speed))
            except (KeyboardInterrupt, curses.error):
                pass
        elif run_choice == "t":
            run_text(machine, delay=args.speed)
        return

    if args.load:
        try:
            machine = load_machine(args.load)
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading machine from '{args.load}': {e}")
            sys.exit(1)

        print(f"Loaded: {machine.name} — {machine.description}")

        if args.validate:
            warnings = machine.validate()
            if warnings:
                print("Validation warnings:")
                for w in warnings:
                    print(f"  ⚠ {w}")
            else:
                print("✓ Machine definition is valid.")

        if args.visual:
            try:
                curses.wrapper(lambda stdscr: run_visual(stdscr, machine, args.speed))
            except (KeyboardInterrupt, curses.error):
                pass
        elif args.text:
            run_text(machine, delay=args.speed)
        elif args.trace:
            trace = run_trace(machine, max_steps=args.max_steps)
            print(f"\n{'='*70}")
            print(f"  Execution Trace: {machine.name}")
            print(f"  {machine.description}")
            print(f"  Input: {machine.initial_tape or '(blank)'}")
            print(f"  Steps: {len(trace)}")
            print(f"{'='*70}\n")
            for step in trace:
                print(f"  Step {step.step_number:4d} | "
                      f"State: {step.state:12s} | "
                      f"Read: {step.symbol_read} → Write: {step.symbol_written} {step.direction} → {step.next_state} | "
                      f"Head: {step.head_position} | "
                      f"Tape: {step.tape_snapshot}")
            final_state = trace[-1].next_state if trace else machine.initial_state
            accepted = final_state in machine.accept_states
            print(f"\n  {'✓ ACCEPTED' if accepted else '✗ REJECTED'} after {len(trace)} steps")
            print(f"  Final tape: {trace[-1].tape_snapshot if trace else '(blank)'}")
        else:
            result = run_batch(machine, args.max_steps)
            status = "✓ ACCEPTED" if result["accepted"] else "✗ REJECTED"
            print(f"\nResult: {result['machine']} | Steps: {result['steps']} | {status}")
            print(f"Output: {result['output']}")
            print(result["stats"].summary())
        return

    # Select a machine
    machine_name = args.run

    # Override tape if specified
    if args.tape and machine_name and machine_name in BUILTIN_PROGRAMS:
        # Create a copy with the new tape
        orig = BUILTIN_PROGRAMS[machine_name]
        machine = TuringMachine(
            name=orig.name, description=orig.description, states=orig.states,
            alphabet=orig.alphabet, blank_symbol=orig.blank_symbol,
            initial_state=orig.initial_state, accept_states=orig.accept_states,
            reject_states=orig.reject_states, transitions=orig.transitions,
            initial_tape=args.tape
        )
    elif machine_name and machine_name in BUILTIN_PROGRAMS:
        machine = BUILTIN_PROGRAMS[machine_name]
    else:
        machine = None

    if args.validate and machine:
        warnings = machine.validate()
        if warnings:
            print("Validation warnings:")
            for w in warnings:
                print(f"  ⚠ {w}")
        else:
            print("✓ Machine definition is valid.")

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

            try:
                choice = input("Enter number (or name): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(keys):
                    machine_name = keys[idx]
                elif idx == len(keys):
                    # Launch interactive creator
                    machine = create_custom_machine()
                    print(f"\nLaunching visual mode with {machine.name}...")
                    try:
                        curses.wrapper(lambda stdscr: run_visual(stdscr, machine, args.speed))
                    except (KeyboardInterrupt, curses.error):
                        pass
                    return
                else:
                    print("Invalid choice.")
                    return
            except ValueError:
                machine_name = choice

        if machine_name and machine_name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {machine_name}")
            print(f"Available: {', '.join(BUILTIN_PROGRAMS.keys())}")
            return

        machine = BUILTIN_PROGRAMS[machine_name]
        if args.tape:
            machine = TuringMachine(
                name=machine.name, description=machine.description, states=machine.states,
                alphabet=machine.alphabet, blank_symbol=machine.blank_symbol,
                initial_state=machine.initial_state, accept_states=machine.accept_states,
                reject_states=machine.reject_states, transitions=machine.transitions,
                initial_tape=args.tape
            )

        try:
            curses.wrapper(lambda stdscr: run_visual(stdscr, machine, args.speed))
        except (KeyboardInterrupt, curses.error):
            pass

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
            print(f"  {'':25s}  {result['stats'].summary()}")
        print()

    elif args.text:
        if not machine_name:
            machine_name = "binary_increment"
        if machine_name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {machine_name}")
            print(f"Available: {', '.join(BUILTIN_PROGRAMS.keys())}")
            return
        machine = BUILTIN_PROGRAMS[machine_name]
        if args.tape:
            machine = TuringMachine(
                name=machine.name, description=machine.description, states=machine.states,
                alphabet=machine.alphabet, blank_symbol=machine.blank_symbol,
                initial_state=machine.initial_state, accept_states=machine.accept_states,
                reject_states=machine.reject_states, transitions=machine.transitions,
                initial_tape=args.tape
            )
        run_text(machine, delay=args.speed)

    elif args.trace:
        if not machine_name:
            machine_name = "binary_increment"
        if machine_name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {machine_name}")
            print(f"Available: {', '.join(BUILTIN_PROGRAMS.keys())}")
            return
        machine = BUILTIN_PROGRAMS[machine_name]
        if args.tape:
            machine = TuringMachine(
                name=machine.name, description=machine.description, states=machine.states,
                alphabet=machine.alphabet, blank_symbol=machine.blank_symbol,
                initial_state=machine.initial_state, accept_states=machine.accept_states,
                reject_states=machine.reject_states, transitions=machine.transitions,
                initial_tape=args.tape
            )
        trace = run_trace(machine, max_steps=args.max_steps)
        print(f"\n{'='*70}")
        print(f"  Execution Trace: {machine.name}")
        print(f"  {machine.description}")
        print(f"  Input: {machine.initial_tape or '(blank)'}")
        print(f"  Steps: {len(trace)}")
        print(f"{'='*70}\n")
        for step in trace:
            print(f"  Step {step.step_number:4d} | "
                  f"State: {step.state:12s} | "
                  f"Read: {step.symbol_read} → Write: {step.symbol_written} {step.direction} → {step.next_state} | "
                  f"Head: {step.head_position} | "
                  f"Tape: {step.tape_snapshot}")
        final_state = trace[-1].next_state if trace else machine.initial_state
        accepted = final_state in machine.accept_states
        print(f"\n  {'✓ ACCEPTED' if accepted else '✗ REJECTED'} after {len(trace)} steps")
        print(f"  Final tape: {trace[-1].tape_snapshot if trace else '(blank)'}")

    elif args.run:
        if machine_name not in BUILTIN_PROGRAMS:
            print(f"Unknown program: {machine_name}")
            print(f"Available: {', '.join(BUILTIN_PROGRAMS.keys())}")
            return
        machine = BUILTIN_PROGRAMS[machine_name]
        if args.tape:
            machine = TuringMachine(
                name=machine.name, description=machine.description, states=machine.states,
                alphabet=machine.alphabet, blank_symbol=machine.blank_symbol,
                initial_state=machine.initial_state, accept_states=machine.accept_states,
                reject_states=machine.reject_states, transitions=machine.transitions,
                initial_tape=args.tape
            )
        result = run_batch(machine, args.max_steps)
        status = "✓ ACCEPTED" if result["accepted"] else "✗ REJECTED"
        print(f"\nResult: {result['machine']} | Steps: {result['steps']} | {status}")
        print(f"Output: {result['output']}")
        print(result["stats"].summary())


if __name__ == "__main__":
    main()