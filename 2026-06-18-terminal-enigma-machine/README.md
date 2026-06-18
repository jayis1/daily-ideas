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

The Enigma is **reciprocal**: encrypting the ciphertext with the same settings recovers the plaintext. No separate "encrypt" and "decrypt" modes needed — just use the same configuration.

## Features

- **8 historical rotors** (I–VIII) with authentic Wehrmacht/Kriegsmarine wirings
- **3 reflectors** (A, B, C) — Reflector B was the most commonly used
- **Plugboard** with up to 13 letter pairs
- **Configurable ring settings** for each rotor
- **Double-stepping mechanism** — the real Enigma's mechanical quirk that makes the middle rotor step twice at turnover
- **Encryption path tracing** (`--trace`) — see exactly how each letter transforms through every component
- **ASCII rotor visualization** (`--visualize`) — see the current machine state
- **Interactive mode** (`--interactive`) — type messages in real-time, toggle tracing, reset rotors
- **Component listing** (`--list`) — browse all available rotors, reflectors, and their wirings
- **No self-encryption** — faithfully reproduces the Enigma's property that no letter ever encrypts to itself
- **41 unit tests** covering reciprocal property, no-self-encryption, stepping, plugboard, and more

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

# Decrypt — just use the same settings!
python3 enigma.py "WSDUQ MNYIA"

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
  Encrypted: WSDUQ

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
  Rotor I→             B        1
  Rotor II→            K        10
  Rotor III→           S        18
  Reflector B          S        18
  ←Rotor III           Z        25
  ←Rotor II            P        15
  ←Rotor I             D        3
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
2. **Plugboard** → **Rotor III** (rightmost, steps first)
3. **Rotor III** → **Rotor II**
4. **Rotor II** → **Rotor I** (leftmost)
5. **Rotor I** → **Reflector** (maps letter to another)
6. **Reflector** → **Rotor I** (signal travels back!)
7. **Rotor I** → **Rotor II**
8. **Rotor II** → **Rotor III**
9. **Rotor III** → **Plugboard** (optional letter swap)
10. **Plugboard** → **Output letter**

The signal passes through the rotors *twice* (forward and back), and the rotors step *before* each keypress. This combination produces a polyalphabetic cipher where the substitution alphabet changes for every character.

### Key Properties

- **Reciprocal**: Same settings encrypt and decrypt
- **No self-encryption**: No letter ever encrypts to itself
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
```

## License

MIT