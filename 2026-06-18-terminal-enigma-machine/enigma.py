#!/usr/bin/env python3
"""
Terminal Enigma Machine — A full simulation of the WWII Enigma cipher machine.

Supports configurable rotors, reflector, plugboard, and visual encryption path tracing.
Encrypts and decrypts text from the command line or interactively.

Features:
  - 8 historical rotors (I–VIII) with authentic wirings and notch positions
  - 3 reflectors (A, B, C)
  - Configurable plugboard with validation
  - Ring settings (Ringstellung)
  - Double-stepping mechanism
  - Encryption path tracing
  - Interactive mode with on-the-fly configuration
  - File/stdin encryption
  - Random configuration generation
  - Config save/load (JSON)
  - Output formatting (grouped, plain, verbose)
"""

import argparse
import json
import os
import random
import sys
import string

__version__ = "2.0.0"

# ─── Historical Enigma Components ────────────────────────────────────────────

# Rotor wirings (input letter index → output letter index)
# Each rotor has a specific wiring, a notch position where it triggers the next rotor,
# and can be set to a starting position.
ROTOR_WIRINGS = {
    "I":   "EKMFLGDQVZNTOWYHXUSPAIBRCJ",
    "II":  "AJDKSIRUXBLHWTMCQGZNPYFVOE",
    "III": "BDFHJLCPRTXVZNYEIWGAKMUSQO",
    "IV":  "ESOVPZJAYQUIRHXLNFTGKDCMWB",
    "V":   "VZBRGITYUPSDNHLXAWMJQOFECK",
    "VI":  "JPGVOUMFYQBENHZRDKASXLICTW",
    "VII": "NZJHGRCXMYSWBOUFAIVLPEKQDT",
    "VIII": "FKQHTLXOCBJSPDZRAMEWNIUYGV",
}

# Notch positions: when the rotor's visible letter hits this, it steps the next rotor
ROTOR_NOTCHES = {
    "I":   "Q",
    "II":  "E",
    "III": "V",
    "IV":  "J",
    "V":   "Z",
    "VI":  "ZM",   # dual notch
    "VII": "ZM",
    "VIII": "ZM",
}

# Reflector wirings
REFLECTOR_WIRINGS = {
    "A": "EJMZALYXVBWFCRQUONTSPIKHGD",
    "B": "YRUHQSLDPXNGOKMIEBFZCWVJAT",
    "C": "FVPJIAOYEDRZXWGCTKUQSBNMHL",
}

ALPHABET = string.ascii_uppercase


def char_to_index(c):
    """Convert a character to its 0-based alphabet index."""
    return ord(c.upper()) - ord('A')


def index_to_char(i):
    """Convert a 0-based alphabet index to its character, wrapping at 26."""
    return chr(i % 26 + ord('A'))


def random_config():
    """
    Generate a random Enigma machine configuration.

    Returns:
        dict with keys: rotor_names, rotor_positions, ring_settings,
                        reflector_name, plugboard_pairs
    """
    rotor_choices = list(ROTOR_WIRINGS.keys())
    # Pick 3 distinct rotors (Enigma used 3 of the available rotors)
    chosen = random.sample(rotor_choices, 3)
    positions = [random.choice(ALPHABET) for _ in range(3)]
    rings = [random.randint(1, 26) for _ in range(3)]
    reflector = random.choice(list(REFLECTOR_WIRINGS.keys()))

    # Pick 0–10 random plugboard pairs
    num_pairs = random.randint(0, 10)
    letters = list(ALPHABET)
    random.shuffle(letters)
    pairs = [letters[2*i] + letters[2*i+1] for i in range(num_pairs)]

    return {
        "rotor_names": chosen,
        "rotor_positions": positions,
        "ring_settings": rings,
        "reflector_name": reflector,
        "plugboard_pairs": pairs,
    }


def format_output(text, style="plain", group_size=5):
    """
    Format encrypted/decrypted text for display.

    Args:
        text: The text to format.
        style: 'plain' (as-is), 'grouped' (groups of letters separated by spaces),
               or 'verbose' (each letter on its own line with index).
        group_size: Number of letters per group when style='grouped'.

    Returns:
        Formatted string.
    """
    alpha_only = "".join(c for c in text if c.isalpha())

    if style == "grouped":
        groups = [alpha_only[i:i+group_size] for i in range(0, len(alpha_only), group_size)]
        return " ".join(groups)
    elif style == "verbose":
        lines = []
        for i, (orig, enc) in enumerate(zip(text, text)):
            if orig.isalpha():
                lines.append(f"  {i+1:>4}: {orig} → {enc}")
        return "\n".join(lines)
    else:  # plain
        return text


class Plugboard:
    """Enigma plugboard (Steckerbrett) — swaps pairs of letters before and after rotor encryption."""

    def __init__(self, pairs=None):
        """
        Args:
            pairs: List of 2-letter strings like ["AB", "CD"] meaning A↔B, C↔D.
                   Each letter can appear at most once.
        Raises:
            ValueError: If a pair is invalid, has duplicate letters, or a letter
                        appears in multiple pairs.
        """
        self.mapping = list(range(26))  # identity mapping
        self.pairs = []  # store the pairs for display
        if pairs:
            used = set()
            for pair in pairs:
                pair = pair.upper()
                if len(pair) != 2:
                    raise ValueError(f"Invalid plugboard pair '{pair}': must be exactly 2 letters")
                if not pair.isalpha():
                    raise ValueError(f"Invalid plugboard pair '{pair}': must contain only letters")
                if pair[0] == pair[1]:
                    raise ValueError(f"Invalid plugboard pair '{pair}': cannot swap a letter with itself")
                a, b = char_to_index(pair[0]), char_to_index(pair[1])
                if a in used or b in used:
                    raise ValueError(f"Letter '{pair[0]}' or '{pair[1]}' appears in multiple plugboard pairs")
                used.add(a)
                used.add(b)
                self.mapping[a] = b
                self.mapping[b] = a
                self.pairs.append(pair)

    def encode(self, index):
        """Apply plugboard substitution."""
        return self.mapping[index]

    def is_identity(self):
        """Return True if no plugboard pairs are set (identity mapping)."""
        return self.mapping == list(range(26))

    def __repr__(self):
        if self.is_identity():
            return "Plugboard(identity)"
        return f"Plugboard(pairs={self.pairs})"


class Rotor:
    """A single Enigma rotor with wiring, ring setting, and position."""

    def __init__(self, name, position="A", ring_setting=1):
        """
        Args:
            name: Rotor name (I-VIII).
            position: Initial visible letter position ("A"-"Z").
            ring_setting: Ring setting (1-26, also known as Ringstellung).
        """
        if name not in ROTOR_WIRINGS:
            raise ValueError(f"Unknown rotor: {name}. Choose from {list(ROTOR_WIRINGS.keys())}")
        self.name = name
        self.wiring = ROTOR_WIRINGS[name]
        self.notch_positions = ROTOR_NOTCHES[name]
        self.position = char_to_index(position)
        self.ring_setting = ring_setting - 1  # convert to 0-indexed

        # Build forward and reverse wiring maps
        self.forward = [char_to_index(c) for c in self.wiring]
        self.reverse = [0] * 26
        for i, o in enumerate(self.forward):
            self.reverse[o] = i

    def encode_right_to_left(self, index):
        """Encode a signal passing through the rotor (right to left)."""
        # Adjust for position and ring setting
        shifted = (index - self.ring_setting + self.position) % 26
        output = self.forward[shifted]
        output = (output - self.position + self.ring_setting) % 26
        return output

    def encode_left_to_right(self, index):
        """Encode a signal passing back through the rotor (left to right)."""
        shifted = (index - self.ring_setting + self.position) % 26
        output = self.reverse[shifted]
        output = (output - self.position + self.ring_setting) % 26
        return output

    def step(self):
        """Advance the rotor by one position. Returns True if at notch (should trigger next rotor)."""
        at_notch = index_to_char(self.position) in self.notch_positions
        self.position = (self.position + 1) % 26
        return at_notch

    def get_position_char(self):
        """Return the current visible position as a letter."""
        return index_to_char(self.position)

    def set_position(self, pos):
        """Set rotor position from a letter (A-Z)."""
        self.position = char_to_index(pos)

    def __repr__(self):
        return f"Rotor({self.name}, pos={self.get_position_char()}, ring={self.ring_setting + 1})"


class Reflector:
    """Enigma reflector (Umkehrwalze) — maps each letter to another and back."""

    def __init__(self, name="B"):
        if name not in REFLECTOR_WIRINGS:
            raise ValueError(f"Unknown reflector: {name}. Choose from {list(REFLECTOR_WIRINGS.keys())}")
        self.name = name
        self.wiring = REFLECTOR_WIRINGS[name]
        self.mapping = [char_to_index(c) for c in self.wiring]

    def encode(self, index):
        """Apply reflector mapping."""
        return self.mapping[index]

    def __repr__(self):
        return f"Reflector({self.name})"


class EnigmaMachine:
    """Complete Enigma machine with plugboard, rotors, and reflector."""

    def __init__(self, rotor_names=None, rotor_positions=None, ring_settings=None,
                 reflector_name="B", plugboard_pairs=None):
        """
        Args:
            rotor_names: List of 3 rotor names (left to right), e.g. ["IV", "II", "I"]
            rotor_positions: List of 3 starting positions, e.g. ["A", "B", "C"]
            ring_settings: List of 3 ring settings (1-26), e.g. [1, 1, 1]
            reflector_name: Reflector name ("A", "B", or "C")
            plugboard_pairs: List of plugboard pairs, e.g. ["AB", "CD"]
        """
        if rotor_names is None:
            rotor_names = ["I", "II", "III"]
        if rotor_positions is None:
            rotor_positions = ["A", "A", "A"]
        if ring_settings is None:
            ring_settings = [1, 1, 1]

        if len(rotor_names) != 3:
            raise ValueError("Must specify exactly 3 rotors")
        if len(rotor_positions) != 3:
            raise ValueError("Must specify exactly 3 rotor positions")
        if len(ring_settings) != 3:
            raise ValueError("Must specify exactly 3 ring settings")
        for rs in ring_settings:
            if not isinstance(rs, int) or rs < 1 or rs > 26:
                raise ValueError(f"Ring setting must be 1-26, got {rs}")

        # Rightmost rotor is index 2 (closest to input), leftmost is index 0
        self.rotors = [
            Rotor(rotor_names[i], rotor_positions[i], ring_settings[i])
            for i in range(3)
        ]
        self.reflector = Reflector(reflector_name)
        self.plugboard = Plugboard(plugboard_pairs or [])
        self.trace = None  # will hold last encryption path trace
        self._all_traces = []  # holds per-character traces for full message tracing
        self._initial_positions = list(rotor_positions)
        self._initial_ring_settings = list(ring_settings)

    def _step_rotors(self):
        """
        Step the rotors according to Enigma's double-stepping mechanism.
        The rightmost rotor always steps. The middle rotor steps when the
        right rotor is at its notch (or the middle rotor is at its notch,
        causing the left rotor to also step — the "double-stepping" anomaly).
        """
        right_at_notch = index_to_char(self.rotors[2].position) in self.rotors[2].notch_positions
        middle_at_notch = index_to_char(self.rotors[1].position) in self.rotors[1].notch_positions

        # If middle rotor is at notch, both middle and left step (double stepping)
        if middle_at_notch:
            self.rotors[0].step()
            self.rotors[1].step()
        # If right rotor is at notch, middle steps
        elif right_at_notch:
            self.rotors[1].step()

        # Right rotor always steps
        self.rotors[2].step()

    def encrypt_char(self, char, trace=False):
        """
        Encrypt a single character through the Enigma machine.

        Args:
            char: A single uppercase letter.
            trace: If True, record the encryption path for visualization.

        Returns:
            The encrypted letter.
        """
        if char not in string.ascii_uppercase:
            return char  # pass through non-alpha characters

        self._step_rotors()
        index = char_to_index(char)

        path = []
        if trace:
            path.append(("Input", char, index))

        # Plugboard in
        index = self.plugboard.encode(index)
        if trace:
            path.append(("Plugboard→", index_to_char(index), index))

        # Through rotors right to left (signal enters right/fast rotor first)
        for rotor in reversed(self.rotors):
            index = rotor.encode_right_to_left(index)
            if trace:
                path.append((f"Rotor {rotor.name}→", index_to_char(index), index))

        # Reflector
        index = self.reflector.encode(index)
        if trace:
            path.append((f"Reflector {self.reflector.name}", index_to_char(index), index))

        # Through rotors left to right (signal returns through left/slow rotor first)
        for rotor in self.rotors:
            index = rotor.encode_left_to_right(index)
            if trace:
                path.append((f"←Rotor {rotor.name}", index_to_char(index), index))

        # Plugboard out
        index = self.plugboard.encode(index)
        result = index_to_char(index)
        if trace:
            path.append(("Output", result, index))
            self.trace = path

        return result

    def encrypt(self, text, trace=False):
        """
        Encrypt a string of text.

        Args:
            text: The text to encrypt. Non-alpha characters are passed through.
            trace: If True, record the encryption path for each character.

        Returns:
            The encrypted text.
        """
        text = text.upper()
        result = []
        self._all_traces = []
        for char in text:
            encrypted = self.encrypt_char(char, trace=trace)
            result.append(encrypted)
            if trace and char.isalpha():
                self._all_traces.append(self.trace)
        return "".join(result)

    def get_rotor_positions(self):
        """Return current rotor position letters."""
        return [r.get_position_char() for r in self.rotors]

    def get_state_string(self):
        """Return a string showing the current machine state."""
        positions = self.get_rotor_positions()
        return f"{positions[0]} {positions[1]} {positions[2]}"

    def get_config(self):
        """
        Return the current machine configuration as a dictionary.
        Useful for saving and recreating a machine.
        """
        return {
            "rotor_names": [r.name for r in self.rotors],
            "rotor_positions": self.get_rotor_positions(),
            "ring_settings": [r.ring_setting + 1 for r in self.rotors],
            "reflector_name": self.reflector.name,
            "plugboard_pairs": self.plugboard.pairs,
            "version": __version__,
        }

    def reset_positions(self, positions=None):
        """
        Reset rotor positions to the initial positions or specified positions.

        Args:
            positions: List of 3 position letters, or None to use initial positions.
        """
        if positions is None:
            positions = self._initial_positions
        if len(positions) != 3:
            raise ValueError("Must specify exactly 3 rotor positions")
        for i, pos in enumerate(positions):
            self.rotors[i].set_position(pos)

    def get_all_traces(self):
        """Return all per-character traces from the last encrypt() call with trace=True."""
        return self._all_traces


def format_trace(trace, char, output_char):
    """Format a single character's encryption trace as a readable string."""
    lines = []
    lines.append(f"  Encrypting '{char}' → '{output_char}'")
    lines.append(f"  {'Step':<20} {'Letter':<8} {'Index':<6}")
    lines.append(f"  {'─' * 34}")
    for step_name, letter, index in trace:
        lines.append(f"  {step_name:<20} {letter:<8} {index:<6}")
    return "\n".join(lines)


def format_full_trace(all_traces, plaintext, ciphertext):
    """
    Format a full message's encryption traces showing every character's path.

    Args:
        all_traces: List of per-character traces from get_all_traces().
        plaintext: Original plaintext (uppercase, alpha only).
        ciphertext: Resulting ciphertext (uppercase, alpha only).

    Returns:
        Formatted string with all traces.
    """
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║           ENIGMA MACHINE — Full Encryption Trace        ║")
    lines.append("╚══════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append(f"  Plaintext:  {plaintext}")
    lines.append(f"  Ciphertext: {ciphertext}")
    lines.append("")

    for i, (trace, p_char, c_char) in enumerate(zip(all_traces, plaintext, ciphertext)):
        lines.append(f"  ── Character {i+1}: '{p_char}' → '{c_char}' ──")
        for step_name, letter, index in trace:
            lines.append(f"    {step_name:<20} {letter:<8} {index:<6}")
        lines.append("")

    return "\n".join(lines)


def visualize_rotors(machine, width=60):
    """Create an ASCII visualization of the current rotor state."""
    lines = []
    lines.append("┌" + "─" * (width - 2) + "┐")

    # Header
    header = "  ENIGMA MACHINE — Current State"
    lines.append("│" + header.center(width - 2) + "│")

    lines.append("├" + "─" * (width - 2) + "┤")

    # Rotor positions
    positions = machine.get_rotor_positions()
    pos_line = f"  Rotor positions: {positions[0]}  {positions[1]}  {positions[2]}"
    lines.append("│" + pos_line.ljust(width - 2) + "│")

    rotor_names = [r.name for r in machine.rotors]
    name_line = f"  Rotors: {rotor_names[0]:>4}  {rotor_names[1]:>4}  {rotor_names[2]:>4}"
    lines.append("│" + name_line.ljust(width - 2) + "│")

    ring_settings = [r.ring_setting + 1 for r in machine.rotors]
    ring_line = f"  Ring settings:  {ring_settings[0]:>2}   {ring_settings[1]:>2}   {ring_settings[2]:>2}"
    lines.append("│" + ring_line.ljust(width - 2) + "│")

    lines.append("├" + "─" * (width - 2) + "┤")

    # Rotor visual — show the window letters prominently
    for i in range(3):
        rotor = machine.rotors[i]
        pos = rotor.position
        # Show 5 letters around the visible position
        letters = []
        for j in range(-2, 3):
            letters.append(index_to_char((pos + j) % 26))
        vis = "  ".join(letters)

        if i == 0:
            line = f"  {rotor.name:>4}  │ {vis} │"
        else:
            line = f"       │ {vis} │"
        lines.append("│" + line.ljust(width - 2) + "│")

    lines.append("└" + "─" * (width - 2) + "┘")
    return "\n".join(lines)


def visualize_signal_path(trace, width=60):
    """
    Create an ASCII visualization of the signal path through the Enigma machine
    for a single character encryption.

    Args:
        trace: A trace list from encrypt_char(trace=True).
        width: Display width.

    Returns:
        Formatted string showing the signal path.
    """
    if not trace:
        return "(No trace data)"

    lines = []
    lines.append("┌" + "─" * (width - 2) + "┐")
    header = "  SIGNAL PATH VISUALIZATION"
    lines.append("│" + header.center(width - 2) + "│")
    lines.append("├" + "─" * (width - 2) + "┤")

    input_char = trace[0][1]
    output_char = trace[-1][1]

    for step_name, letter, index in trace:
        bar = "█" * min(index + 1, 30)
        line = f"  {step_name:<18} {letter} ({index:>2})  {bar}"
        lines.append("│" + line.ljust(width - 2) + "│")

    lines.append("├" + "─" * (width - 2) + "┤")
    summary = f"  {input_char} ──→ {output_char}"
    lines.append("│" + summary.center(width - 2) + "│")
    lines.append("└" + "─" * (width - 2) + "┘")
    return "\n".join(lines)


def interactive_mode(machine, show_trace=False):
    """Run an interactive Enigma machine session."""
    print("\n╔══════════════════════════════════════════════╗")
    print("║     ENIGMA MACHINE — Interactive Mode       ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    print(f"  Rotors:   {machine.rotors[0].name} {machine.rotors[1].name} {machine.rotors[2].name}")
    print(f"  Reflector: {machine.reflector.name}")
    positions = machine.get_rotor_positions()
    print(f"  Start positions: {positions[0]} {positions[1]} {positions[2]}")
    print(f"  Ring settings:   {machine.rotors[0].ring_setting+1} {machine.rotors[1].ring_setting+1} {machine.rotors[2].ring_setting+1}")
    if not machine.plugboard.is_identity():
        pairs_str = " ".join(machine.plugboard.pairs)
        print(f"  Plugboard: {pairs_str}")
    else:
        print("  Plugboard: (none)")
    print()
    print("  Commands:")
    print("    <text>       Encrypt the text")
    print("    trace         Toggle trace mode")
    print("    state         Show current machine state")
    print("    signal        Show signal path visualization")
    print("    config        Show current configuration")
    print("    save <file>   Save configuration to JSON file")
    print("    reset         Reset rotor positions to starting positions")
    print("    help          Show this help")
    print("    quit          Exit")
    print()

    initial_positions = [r.position for r in machine.rotors]
    local_trace = show_trace

    while True:
        try:
            positions = machine.get_rotor_positions()
            prompt = f"enigma [{positions[0]}{positions[1]}{positions[2]}]> "
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd == "quit" or cmd == "exit":
            print("  Goodbye!")
            break
        elif cmd == "help":
            print("  Commands:")
            print("    <text>       Encrypt the text")
            print("    trace         Toggle trace mode")
            print("    state         Show current machine state")
            print("    signal        Show signal path visualization")
            print("    config        Show current configuration")
            print("    save <file>   Save configuration to JSON file")
            print("    reset         Reset rotor positions")
            print("    help          Show this help")
            print("    quit          Exit")
        elif cmd == "trace":
            local_trace = not local_trace
            print(f"  Trace mode: {'ON' if local_trace else 'OFF'}")
        elif cmd == "state":
            print(visualize_rotors(machine))
        elif cmd == "signal":
            # Encrypt a single character to show the signal path
            print("  Enter a single letter to visualize its signal path:")
            try:
                letter = input("  Letter> ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                continue
            if letter and letter.isalpha() and len(letter) == 1:
                result = machine.encrypt_char(letter, trace=True)
                print(f"  {letter} → {result}")
                if machine.trace:
                    print(visualize_signal_path(machine.trace))
            else:
                print("  Please enter a single letter (A-Z).")
        elif cmd == "config":
            config = machine.get_config()
            print("  Current configuration:")
            print(f"    Rotors:   {' '.join(config['rotor_names'])}")
            print(f"    Positions: {' '.join(config['rotor_positions'])}")
            print(f"    Ring settings: {' '.join(str(r) for r in config['ring_settings'])}")
            print(f"    Reflector: {config['reflector_name']}")
            if config['plugboard_pairs']:
                print(f"    Plugboard: {' '.join(config['plugboard_pairs'])}")
            else:
                print("    Plugboard: (none)")
        elif cmd.startswith("save "):
            filepath = user_input[5:].strip()
            if not filepath:
                print("  Usage: save <filename>")
                continue
            try:
                config = machine.get_config()
                with open(filepath, 'w') as f:
                    json.dump(config, f, indent=2)
                print(f"  Configuration saved to {filepath}")
            except OSError as e:
                print(f"  Error saving configuration: {e}")
        elif cmd == "reset":
            for i, rotor in enumerate(machine.rotors):
                rotor.position = initial_positions[i]
            print(f"  Rotors reset to: {' '.join(machine.get_rotor_positions())}")
        else:
            # Encrypt the text
            encrypted = machine.encrypt(user_input.upper(), trace=local_trace)
            print(f"  Input:     {user_input.upper()}")
            print(f"  Encrypted: {encrypted}")
            if local_trace and machine.trace:
                print(format_trace(machine.trace, user_input.upper()[-1], encrypted[-1]))


def list_components():
    """Print available rotors, reflectors, and their details."""
    print("\n╔══════════════════════════════════════════════╗")
    print("║        Enigma Machine Components            ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    print("  ROTORS:")
    print(f"  {'Name':<6} {'Notch':<8} Wiring")
    print(f"  {'─'*6} {'─'*8} {'─'*26}")
    for name, wiring in ROTOR_WIRINGS.items():
        notch = ROTOR_NOTCHES[name]
        print(f"  {name:<6} {notch:<8} {wiring}")
    print()
    print("  REFLECTORS:")
    print(f"  {'Name':<6} Wiring")
    print(f"  {'─'*6} {'─'*26}")
    for name, wiring in REFLECTOR_WIRINGS.items():
        print(f"  {name:<6} {wiring}")
    print()
    print("  NOTES:")
    print("  • Rotors are placed left-to-right; rightmost rotor steps first")
    print("  • Dual-notch rotors (VI, VII, VIII) turn over more frequently")
    print("  • Reflector A was used in early models; B and C were more common")
    print("  • The Enigma is reciprocal: encrypting twice with the same settings")
    print("    yields the original plaintext")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Terminal Enigma Machine — Simulate the WWII Enigma cipher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick encrypt with default settings (rotors I II III, positions AAA)
  python enigma.py "HELLO WORLD"

  # Specify rotors and starting positions
  python enigma.py "SECRET MESSAGE" -r IV II I -p A A B

  # Use plugboard pairs
  python enigma.py "ATTACK AT DAWN" -P AB CD EF

  # Interactive mode with trace
  python enigma.py --interactive --trace

  # List available components
  python enigma.py --list

  # Show encryption path for a single letter
  python enigma.py --trace "HELLO"

  # Generate a random configuration
  python enigma.py --random "HELLO"

  # Group output in 5-letter blocks (traditional Enigma style)
  python enigma.py --format grouped "HELLO WORLD"

  # Encrypt from a file
  python enigma.py --file message.txt

  # Read from stdin
  echo "HELLO" | python enigma.py --stdin

  # Save current configuration to a file
  python enigma.py --save-config my_config.json "HELLO"

  # Load configuration from a file
  python enigma.py --load-config my_config.json "HELLO"
"""
    )

    parser.add_argument("text", nargs="?", help="Text to encrypt/decrypt")
    parser.add_argument("-r", "--rotors", nargs=3, default=["I", "II", "III"],
                        metavar=("LEFT", "MIDDLE", "RIGHT"),
                        help="Rotor names left-to-right (default: I II III)")
    parser.add_argument("-p", "--positions", nargs=3, default=["A", "A", "A"],
                        metavar=("L", "M", "R"),
                        help="Starting rotor positions (default: A A A)")
    parser.add_argument("--ring", nargs=3, type=int, default=[1, 1, 1],
                        metavar=("L", "M", "R"),
                        help="Ring settings 1-26 (default: 1 1 1)")
    parser.add_argument("-f", "--reflector", default="B",
                        choices=["A", "B", "C"],
                        help="Reflector (default: B)")
    parser.add_argument("--plugboard", "-P", nargs="+", default=None,
                        metavar="PAIR",
                        help="Plugboard pairs like AB CD EF (must come before text)")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Start interactive mode")
    parser.add_argument("-t", "--trace", action="store_true",
                        help="Show encryption path trace")
    parser.add_argument("-l", "--list", action="store_true",
                        help="List available rotors and reflectors")
    parser.add_argument("-v", "--visualize", action="store_true",
                        help="Show rotor state visualization before output")
    parser.add_argument("--random", action="store_true",
                        help="Generate a random machine configuration")
    parser.add_argument("--format", choices=["plain", "grouped", "verbose"],
                        default="plain", dest="output_format",
                        help="Output format: plain, grouped (5-letter blocks), or verbose")
    parser.add_argument("--group-size", type=int, default=5,
                        help="Group size for 'grouped' format (default: 5)")
    parser.add_argument("--file", metavar="FILEPATH",
                        help="Read plaintext from a file")
    parser.add_argument("--stdin", action="store_true",
                        help="Read plaintext from stdin")
    parser.add_argument("--save-config", metavar="FILEPATH",
                        help="Save the current configuration to a JSON file")
    parser.add_argument("--load-config", metavar="FILEPATH",
                        help="Load machine configuration from a JSON file")
    parser.add_argument("--signal", action="store_true",
                        help="Show signal path visualization for the first character")
    parser.add_argument("--version", action="version", version=f"Enigma Machine {__version__}")

    args = parser.parse_args()

    if args.list:
        list_components()
        return

    # Handle config loading
    config_from_file = None
    if args.load_config:
        try:
            with open(args.load_config, 'r') as f:
                config_from_file = json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file '{args.load_config}' not found.", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file '{args.load_config}': {e}", file=sys.stderr)
            sys.exit(1)

    # Apply config from file (overrides command-line defaults)
    if config_from_file:
        if "rotor_names" in config_from_file:
            args.rotors = config_from_file["rotor_names"]
        if "rotor_positions" in config_from_file:
            args.positions = config_from_file["rotor_positions"]
        if "ring_settings" in config_from_file:
            args.ring = config_from_file["ring_settings"]
        if "reflector_name" in config_from_file:
            args.reflector = config_from_file["reflector_name"]
        if "plugboard_pairs" in config_from_file:
            args.plugboard = config_from_file["plugboard_pairs"]

    # Handle random config
    if args.random:
        cfg = random_config()
        args.rotors = cfg["rotor_names"]
        args.positions = cfg["rotor_positions"]
        args.ring = cfg["ring_settings"]
        args.reflector = cfg["reflector_name"]
        args.plugboard = cfg["plugboard_pairs"]

    # Validate plugboard pairs
    pairs = [p.upper() for p in (args.plugboard or [])]
    for pair in pairs:
        if len(pair) != 2 or not pair.isalpha():
            print(f"Error: Invalid plugboard pair '{pair}'. Use 2-letter pairs like AB CD.", file=sys.stderr)
            sys.exit(1)
        if pair[0] == pair[1]:
            print(f"Error: Invalid plugboard pair '{pair}': cannot swap a letter with itself.", file=sys.stderr)
            sys.exit(1)

    # Check for duplicate letters in plugboard
    used = set()
    for pair in pairs:
        for c in pair:
            if c in used:
                print(f"Error: Letter '{c}' appears in multiple plugboard pairs.", file=sys.stderr)
                sys.exit(1)
            used.add(c)

    # Create the machine
    try:
        machine = EnigmaMachine(
            rotor_names=args.rotors,
            rotor_positions=args.positions,
            ring_settings=args.ring,
            reflector_name=args.reflector,
            plugboard_pairs=pairs,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Save config if requested
    if args.save_config:
        config = machine.get_config()
        try:
            with open(args.save_config, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Configuration saved to {args.save_config}")
        except OSError as e:
            print(f"Error saving configuration: {e}", file=sys.stderr)
            sys.exit(1)

    if args.interactive:
        interactive_mode(machine, show_trace=args.trace)
        return

    # Determine input text
    input_text = None
    if args.text:
        input_text = args.text
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                input_text = f.read().strip()
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error reading file '{args.file}': {e}", file=sys.stderr)
            sys.exit(1)
    elif args.stdin:
        if not sys.stdin.isatty():
            input_text = sys.stdin.read().strip()
        else:
            print("Error: No input on stdin.", file=sys.stderr)
            sys.exit(1)

    if input_text is None:
        parser.print_help()
        return

    if args.visualize:
        print(visualize_rotors(machine))
        print()

    # Encrypt the text
    encrypted = machine.encrypt(input_text, trace=args.trace)
    formatted = format_output(encrypted, style=args.output_format,
                              group_size=args.group_size)

    print(f"Input:     {input_text.upper()}")
    print(f"Encrypted: {formatted}")

    if args.trace and machine._all_traces:
        # Show trace for the last character by default
        upper_text = input_text.upper()
        alpha_chars = [c for c in upper_text if c.isalpha()]
        if alpha_chars:
            last_char = alpha_chars[-1]
            last_encrypted = [c for c in encrypted if c.isalpha()][-1]
            print()
            print(format_trace(machine.trace, last_char, last_encrypted))

    if args.signal and machine.trace:
        print()
        print(visualize_signal_path(machine.trace))

    # Show random config info if --random was used
    if args.random:
        print()
        print("  Random configuration used:")
        print(f"    Rotors:   {' '.join(args.rotors)}")
        print(f"    Positions: {' '.join(args.positions)}")
        print(f"    Rings:     {' '.join(str(r) for r in args.ring)}")
        print(f"    Reflector: {args.reflector}")
        if pairs:
            print(f"    Plugboard: {' '.join(pairs)}")


if __name__ == "__main__":
    main()