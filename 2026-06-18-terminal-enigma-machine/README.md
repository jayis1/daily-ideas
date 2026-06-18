# 🔐 Terminal Enigma Machine

A complete simulation of the WWII Enigma cipher machine with 8 historical rotors, 3 reflectors, configurable plugboard, and visual encryption path tracing — all in your terminal.

## Description

The Enigma machine was a cryptographic device used by Nazi Germany during World War II. Its complex system of rotors, reflectors, and plugboard created a polyalphabetic substitution cipher that was considered unbreakable — until Alan Turing and the Bletchley Park team cracked it.

This project faithfully simulates the Enigma's encryption mechanics including:

- **Rotor stepping** with the famous double-stepping anomaly
- **Plugboard (Steckerbrett)** letter-pair swapping
- **Ring settings (Ringstellung)** that shift the internal wiring offset
- **Reflector (Umkehrwalze)** that sends the signal back through the rotors
- **Encryption path tracing** showing exactly how each letter transforms at every stage
- **Correct signal path** through the rotors (right → middle → left → reflector → left → middle → right)

The Enigma is **reciprocal**: encrypting the ciphertext with the same settings recovers the plaintext. No separate "encrypt" and "decrypt" modes needed — just use the same configuration.

## Features

- **8 historical rotors** (I–VIII) with authentic Wehrmacht/Kriegsmarine wirings
- **3 reflectors** (A, B, C) — Reflector B was the most commonly used
- **Plugboard** with up to 13 letter pairs (validated for duplicates and self-swaps)
- **Configurable ring settings** for each rotor (1–26, validated)
- **Double-stepping mechanism** — the real Enigma's mechanical quirk that makes the middle rotor step twice at turnover
- **Encryption path tracing** (`--trace`) — see exactly how each letter transforms through every component
- **ASCII rotor visualization** (`--visualize`) — see the current machine state
- **Interactive mode** (`--interactive`) — type messages in real-time, toggle tracing, reset rotors
- **Component listing** (`--list`) — browse all available rotors, reflectors, and their wirings
- **No self-encryption** — faithfully reproduces the Enigma's property that no letter ever encrypts to itself (with reflectors B and C)
- **Known test vector verified** — encrypting `AAAAA` with rotors I-II-III, positions AAA, ring 01-01-01, reflector B produces `BDZGO`, matching the standard Enigma I reference
- **Input validation** — plugboard pairs, ring settings, and rotor names are all validated with clear error messages
- **53 unit tests** covering reciprocal property, known test vectors, no-self-encryption, double-stepping, plugboard validation, and more

## Installation

No external dependencies — uses only the Python standard library.

```bash
# Clone or download, then run directly:
python3 enigma.py "HELLO WORLD"
```

## Quick Start

```bash
# Encrypt with default settings (rotors I II III, positions AAA, reflector B)
python3 enigma.py "HELLO WORLD"
# Output: Input:     HELLO WORLD
#         Encrypted: ILBDA AMTAZ

# Decrypt — just use the same settings!
python3 enigma.py "ILBDA AMTAZ"
# Output: Input:     ILBDA AMTAZ
#         Encrypted: HELLO WORLD

# Specify custom rotors and positions
python3 enigma.py "SECRET MESSAGE" -r IV II I -p A B C

# Use plugboard pairs
python3 enigma.py --plugboard AB SZ UJ MY "ATTACK AT DAWN"

# Set ring settings
python3 enigma.py --ring 5 3 7 "HELLO"

# Use Reflector C instead of B
python3 enigma.py -f C "TESTING"

# Show encryption path trace
python3 enigma.py --trace "HELLO"

# Show rotor visualization
python3 enigma.py --visualize "HELLO"

# Interactive mode
python3 enigma.py --interactive

# Interactive with trace
python3 enigma.py -i --trace

# List all components
python3 enigma.py --list

# Show version
python3 enigma.py --version
```

## Usage

```
python3 enigma.py [TEXT] [OPTIONS]
```

### Positional Arguments

| Argument | Description |
|----------|-------------|
| `TEXT` | Text to encrypt/decrypt (uppercase recommended) |

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-r`, `--rotors` | `I II III` | Three rotor names (left, middle, right) |
| `-p`, `--positions` | `A A A` | Starting rotor positions |
| `--ring` | `1 1 1` | Ring settings (1–26 for each rotor) |
| `-f`, `--reflector` | `B` | Reflector: A, B, or C |
| `--plugboard`, `-P` | (none) | Plugboard pairs like `AB CD EF` |
| `-i`, `--interactive` | off | Start interactive mode |
| `-t`, `--trace` | off | Show encryption path trace |
| `-v`, `--visualize` | off | Show rotor state visualization |
| `-l`, `--list` | off | List available rotors and reflectors |
| `--version` | | Show version and exit |

### Available Rotors

| Rotor | Notch | Use |
|-------|-------|-----|
| I | Q | Wehrmacht |
| II | E | Wehrmacht |
| III | V | Wehrmacht |
| IV | J | Kriegsmarine M4 |
| V | Z | Kriegsmarine M4 |
| VI | ZM | Kriegsmarine M4 (dual notch) |
| VII | ZM | Kriegsmarine M4 (dual notch) |
| VIII | ZM | Kriegsmarine M4 (dual notch) |

### Available Reflectors

| Reflector | Description |
|-----------|-------------|
| A | Early model (rarely used) |
| B | Standard (most common) |
| C | Alternative |

## Interactive Mode

```
enigma [AAA]> hello
  Input:     HELLO
  Encrypted: ILBDA

enigma [AAB]> trace
  Trace mode: ON

enigma [AAB]> a
  Input:     A
  Encrypted: D
  Encrypting 'A' → 'D'
  Step                 Letter   Index
  ──────────────────────────────────
  Input                A        0
  Plugboard→           A        0
  Rotor III→           B        1
  Rotor II→            K        10
  Rotor I→             S        18
  Reflector B          S        18
  ←Rotor I             P        15
  ←Rotor II            D        3
  ←Rotor III           D        3
  Output               D        3

enigma [AAC]> state
  (shows rotor visualization)

enigma [AAC]> reset
  Rotors reset to: A A A

enigma [AAA]> quit
  Goodbye!
```

## How It Works

The Enigma encryption path for a single letter:

1. **Input letter** → **Plugboard** (optional letter swap)
2. **Plugboard** → **Right rotor** (fast rotor, steps first)
3. **Right rotor** → **Middle rotor**
4. **Middle rotor** → **Left rotor** (slow rotor)
5. **Left rotor** → **Reflector** (maps letter to another)
6. **Reflector** → **Left rotor** (signal travels back!)
7. **Left rotor** → **Middle rotor**
8. **Middle rotor** → **Right rotor**
9. **Right rotor** → **Plugboard** (optional letter swap)
10. **Plugboard** → **Output letter**

The signal passes through the rotors *twice* (forward and back), and the rotors step *before* each keypress. This combination produces a polyalphabetic cipher where the substitution alphabet changes for every character.

### Important: Signal Path Direction

The signal enters the **right** (fast) rotor first on the forward pass, then travels through the middle and left rotors to the reflector. On the return path, it goes back through the left, middle, and right rotors. This is a critical detail — an incorrect signal path produces wrong ciphertext.

### Key Properties

- **Reciprocal**: Same settings encrypt and decrypt
- **No self-encryption**: No letter ever encrypts to itself (with reflectors B and C)
- **Double-stepping**: The middle rotor can step twice (the famous mechanical quirk)
- **Period**: The full cycle repeats every 16,900 (26×25×26) keystrokes for 3 rotors

## Programmatic Use

```python
from enigma import EnigmaMachine

# Create a machine with specific settings
machine = EnigmaMachine(
    rotor_names=["IV", "II", "I"],
    rotor_positions=["A", "B", "C"],
    ring_settings=[5, 3, 7],
    reflector_name="B",
    plugboard_pairs=["AB", "SZ", "UJ", "MY"]
)

# Encrypt
ciphertext = machine.encrypt("ATTACK AT DAWN")

# Decrypt (same settings, new machine)
machine2 = EnigmaMachine(
    rotor_names=["IV", "II", "I"],
    rotor_positions=["A", "B", "C"],
    ring_settings=[5, 3, 7],
    reflector_name="B",
    plugboard_pairs=["AB", "SZ", "UJ", "MY"]
)
plaintext = machine2.encrypt(ciphertext)

# Encrypt with tracing
result = machine.encrypt("HELLO", trace=True)
print(machine.trace)  # List of (step_name, letter, index) tuples

# Known test vector verification
m = EnigmaMachine(
    rotor_names=["I", "II", "III"],
    rotor_positions=["A", "A", "A"],
    ring_settings=[1, 1, 1],
    reflector_name="B"
)
assert m.encrypt("AAAAA") == "BDZGO"  # Standard Enigma I test vector
```

## Validation

The `Plugboard` and `EnigmaMachine` constructors validate their inputs and raise `ValueError` for:

- Unknown rotor names or reflector names
- Wrong number of rotors, positions, or ring settings
- Ring settings outside 1–26
- Plugboard pairs that are not exactly 2 letters
- Plugboard pairs with non-alphabetic characters
- A letter appearing in multiple plugboard pairs
- A plugboard pair swapping a letter with itself (e.g., "AA")

## Changelog

### v1.1.0 — Bug Fixes
- **Critical**: Fixed reversed rotor signal path — the forward pass now correctly goes through the right (fast) rotor first, matching the real Enigma. Previously the signal went through the left (slow) rotor first, producing incorrect ciphertext. Verified against the standard `AAAAA → BDZGO` test vector.
- **Critical**: Fixed plugboard validation — duplicate letters across pairs (e.g., `["AB", "AC"]`) are now rejected. Previously, this silently corrupted encryption by overwriting mappings.
- Added validation for plugboard self-swaps (e.g., `"AA"`) and non-alpha pairs (e.g., `"12"`).
- Added ring setting range validation (must be 1–26, previously accepted 0 or 27+).
- Added `--version` flag.
- Fixed potential `IndexError` when using `--trace` with empty text.
- Added CLI validation for self-swapping plugboard pairs.
- Added 12 new tests covering known test vector, signal path order, double-stepping detail, plugboard validation, ring setting validation, lowercase handling, position wrapping, and more.

## License

MIT