#!/usr/bin/env python3
"""
Terminal Enigma Machine — A full simulation of the WWII Enigma cipher machine.

Supports configurable rotors, reflector, plugboard, and visual encryption path tracing.
Encrypts and decrypts text from the command line or interactively.
"""

import argparse
import sys
import string

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
    return ord(c.upper()) - ord('A')


def index_to_char(i):
    return chr(i % 26 + ord('A'))


class Plugboard:
    """Enigma plugboard (Steckerbrett) — swaps pairs of letters before and after rotor encryption."""

    def __init__(self, pairs=None):
        """
        Args:
            pairs: List of 2-letter strings like ["AB", "CD"] meaning A↔B, C↔D.
                   Each letter can appear at most once.
        """
        self.mapping = list(range(26))  # identity mapping
        if pairs:
            for pair in pairs:
                a, b = char_to_index(pair[0]), char_to_index(pair[1])
                self.mapping[a] = b
                self.mapping[b] = a

    def encode(self, index):
        """Apply plugboard substitution."""
        return self.mapping[index]


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
        return index_to_char(self.position)


class Reflector:
    """Enigma reflector (Umkehrwalze) — maps each letter to another and back."""

    def __init__(self, name="B"):
        if name not in REFLECTOR_WIRINGS:
            raise ValueError(f"Unknown reflector: {name}. Choose from {list(REFLECTOR_WIRINGS.keys())}")
        self.name = name
        self.wiring = REFLECTOR_WIRINGS[name]
        self.mapping = [char_to_index(c) for c in self.wiring]

    def encode(self, index):
        return self.mapping[index]


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

        # Rightmost rotor is index 2 (closest to input), leftmost is index 0
        self.rotors = [
            Rotor(rotor_names[i], rotor_positions[i], ring_settings[i])
            for i in range(3)
        ]
        self.reflector = Reflector(reflector_name)
        self.plugboard = Plugboard(plugboard_pairs or [])
        self.trace = None  # will hold last encryption path trace

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

        # Through rotors right to left
        for i, rotor in enumerate(self.rotors):
            index = rotor.encode_right_to_left(index)
            if trace:
                path.append((f"Rotor {rotor.name}→", index_to_char(index), index))

        # Reflector
        index = self.reflector.encode(index)
        if trace:
            path.append((f"Reflector {self.reflector.name}", index_to_char(index), index))

        # Through rotors left to right
        for rotor in reversed(self.rotors):
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
        for char in text:
            result.append(self.encrypt_char(char, trace=trace))
        return "".join(result)

    def get_rotor_positions(self):
        """Return current rotor position letters."""
        return [r.get_position_char() for r in self.rotors]

    def get_state_string(self):
        """Return a string showing the current machine state."""
        positions = self.get_rotor_positions()
        return f"{positions[0]} {positions[1]} {positions[2]}"


def format_trace(trace, char, output_char):
    """Format a single character's encryption trace as a readable string."""
    lines = []
    lines.append(f"  Encrypting '{char}' → '{output_char}'")
    lines.append(f"  {'Step':<20} {'Letter':<8} {'Index':<6}")
    lines.append(f"  {'─' * 34}")
    for step_name, letter, index in trace:
        lines.append(f"  {step_name:<20} {letter:<8} {index:<6}")
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
        highlight_pos = 2  # center letter index in the vis string

        if i == 0:
            line = f"  {rotor.name:>4}  │ {vis} │"
        else:
            line = f"       │ {vis} │"
        lines.append("│" + line.ljust(width - 2) + "│")

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
    if machine.plugboard.mapping != list(range(26)):
        swaps = []
        used = set()
        for i in range(26):
            if machine.plugboard.mapping[i] != i and i not in used:
                swaps.append(f"{index_to_char(i)}{index_to_char(machine.plugboard.mapping[i])}")
                used.add(i)
                used.add(machine.plugboard.mapping[i])
        print(f"  Plugboard: {' '.join(swaps)}")
    else:
        print("  Plugboard: (none)")
    print()
    print("  Commands:")
    print("    <text>     Encrypt the text")
    print("    trace      Toggle trace mode")
    print("    state      Show current machine state")
    print("    reset      Reset rotor positions to starting positions")
    print("    help       Show this help")
    print("    quit       Exit")
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
            print("    <text>     Encrypt the text")
            print("    trace      Toggle trace mode")
            print("    state      Show current machine state")
            print("    reset      Reset rotor positions")
            print("    help       Show this help")
            print("    quit       Exit")
        elif cmd == "trace":
            local_trace = not local_trace
            print(f"  Trace mode: {'ON' if local_trace else 'OFF'}")
        elif cmd == "state":
            print(visualize_rotors(machine))
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
  python enigma.py "ATTACK AT DAWN" -p AB CD EF

  # Interactive mode with trace
  python enigma.py --interactive --trace

  # List available components
  python enigma.py --list

  # Show encryption path for a single letter
  python enigma.py --trace "HELLO"
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
                        help="Show rotor visualization before output")

    args = parser.parse_args()

    if args.list:
        list_components()
        return

    # Validate plugboard pairs
    pairs = [p.upper() for p in (args.plugboard or [])]
    for pair in pairs:
        if len(pair) != 2 or not pair.isalpha():
            print(f"Error: Invalid plugboard pair '{pair}'. Use 2-letter pairs like AB CD.", file=sys.stderr)
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

    if args.interactive:
        interactive_mode(machine, show_trace=args.trace)
        return

    if args.text is None:
        parser.print_help()
        return

    if args.visualize:
        print(visualize_rotors(machine))
        print()

    # Encrypt the text
    encrypted = machine.encrypt(args.text, trace=args.trace)
    print(f"Input:     {args.text.upper()}")
    print(f"Encrypted: {encrypted}")

    if args.trace and machine.trace:
        # Show trace for the last character
        last_char = args.text.upper()[-1] if args.text.upper()[-1].isalpha() else args.text.upper()[-1]
        print()
        print(format_trace(machine.trace, last_char, encrypted[-1] if encrypted else ""))


if __name__ == "__main__":
    main()