# 🔐 Terminal Enigma Machine

A complete simulation of the WWII Enigma cipher machine with 8 historical rotors, 3 reflectors, configurable plugboard, visual encryption path tracing, random configuration generation, config save/load, and multiple output formats — all in your terminal.

## Description

The Enigma machine was a cryptographic device used by Nazi Germany during World War II. Its complex system of rotors, reflectors, and plugboard created a polyalphabetic substitution cipher that was considered unbreakable — until Alan Turing and the Bletchley Park team cracked it.

This project faithfully simulates the Enigma's encryption mechanics including:

- **Rotor stepping** with the famous double-stepping anomaly
- **Plugboard (Steckerbrett)** letter-pair swapping
- **Ring settings (Ringstellung)** that shift the internal wiring offset
- **Reflector (Umkehrwalze)** that sends the signal back through the rotors
- **Encryption path tracing** showing exactly how each letter transforms at every stage
- **Signal path visualization** with ASCII bar charts
- **Correct signal path** through the rotors (right → middle → left → reflector → left → middle → right)

The Enigma is **reciprocal**: encrypting the ciphertext with the same settings recovers the plaintext. No separate "encrypt" and "decrypt" modes needed — just use the same configuration.

## Features

### Core Encryption
- **8 historical rotors** (I–VIII) with authentic Wehrmacht/Kriegsmarine wirings
- **3 reflectors** (A, B, C) — Reflector B was the most commonly used
- **Plugboard** with up to 13 letter pairs (validated for duplicates and self-swaps)
- **Configurable ring settings** for each rotor (1–26, validated)
- **Double-stepping mechanism** — the real Enigma's mechanical quirk that makes the middle rotor step twice at turnover
- **No self-encryption** — faithfully reproduces the Enigma's property that no letter ever encrypts to itself (with reflectors B and C)
- **Known test vector verified** — encrypting `AAAAA` with rotors I-II-III, positions AAA, ring 01-01-01, reflector B produces `BDZGO`, matching the standard Enigma I reference

### New in v2.0
- **Random configuration** (`--random`) — generate a random machine setup for quick one-time-pad style encryption
- **Config save/load** (`--save-config`/`--load-config`) — persist and share machine configurations as JSON files
- **Output formatting** (`--format plain|grouped|verbose`) — display output in traditional 5-letter groups, verbose per-character mode, or plain text
- **Signal path visualization** (`--signal`) — see an ASCII bar chart showing how each letter's index transforms through the machine
- **Full message tracing** — `get_all_traces()` API to trace every character's path through the machine
- **File input** (`--file`) — encrypt text from a file
- **Stdin input** (`--stdin`) — pipe text in from standard input
- **Config display** in interactive mode — view and save current configuration from within the REPL
- **`reset_positions()` method** — programmatically reset rotor positions
- **`get_config()` method** — export machine configuration as a serializable dict
- **`__version__` constant** — programmatic version checking
- **Interactive `signal` command** — visualize the signal path for a single letter inside interactive mode
- **Interactive `save` command** — save configuration to JSON from within interactive mode

### Interface
- **Encryption path tracing** (`--trace`) — see exactly how each letter transforms through every component
- **ASCII rotor visualization** (`--visualize`) — see the current machine state
- **Interactive mode** (`--interactive`) — type messages in real-time, toggle tracing, reset rotors, view config, save config
- **Component listing** (`--list`) — browse all available rotors, reflectors, and their wirings
- **`--version` flag** — display version number
- **Input validation** — plugboard pairs, ring settings, and rotor names are all validated with clear error messages
- **85 unit tests** covering reciprocal property, known test vectors, no-self-encryption, double-stepping, plugboard validation, config round-trips, random config generation, and more

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

# Show signal path visualization with ASCII bar chart
python3 enigma.py --trace --signal "HELLO"

# Show rotor visualization
python3 enigma.py --visualize "HELLO"

# Output in traditional 5-letter groups
python3 enigma.py --format grouped "HELLO WORLD"
# Output: Input:     HELLO WORLD
#         Encrypted: ILBDA AMTAZ

# Verbose per-character output
python3 enigma.py --format verbose "ABC"

# Generate a random configuration
python3 enigma.py --random "HELLO"

# Save configuration to a file
python3 enigma.py --save-config my_config.json "HELLO"

# Load configuration from a file (reuses saved rotor/plugboard settings)
python3 enigma.py --load-config my_config.json "HELLO"

# Encrypt from a file
python3 enigma.py --file message.txt

# Pipe from stdin
echo "HELLO" | python3 enigma.py --stdin

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
| `-v`, `--visualize` | off | Show rotor state visualization before output |
| `--random` | off | Generate a random machine configuration |
| `--format` | `plain` | Output format: `plain`, `grouped`, or `verbose` |
| `--group-size` | `5` | Group size for `grouped` format |
| `--file` | (none) | Read plaintext from a file |
| `--stdin` | off | Read plaintext from stdin |
| `--save-config` | (none) | Save configuration to a JSON file |
| `--load-config` | (none) | Load configuration from a JSON file |
| `--signal` | off | Show signal path visualization |
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
╔══════════════════════════════════════════════╗
║     ENIGMA MACHINE — Interactive Mode       ║
╚══════════════════════════════════════════════╝

  Rotors:   I II III
  Reflector: B
  Start positions: A A A
  Ring settings:   1 1 1
  Plugboard: (none)

  Commands:
    <text>       Encrypt the text
    trace         Toggle trace mode
    state         Show current machine state
    signal        Show signal path visualization
    config        Show current configuration
    save <file>   Save configuration to JSON file
    reset         Reset rotor positions to starting positions
    help          Show this help
    quit          Exit

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

enigma [AAC]> signal
  Enter a single letter to visualize its signal path:
  Letter> E
  E → M

┌──────────────────────────────────────────────────────────┐
│                 SIGNAL PATH VISUALIZATION                │
├──────────────────────────────────────────────────────────┤
│  Input              E ( 4)  █████                        │
│  Plugboard→         E ( 4)  █████                        │
│  Rotor III→         K (10)  ███████████                 │
│  Rotor II→          S (18)  ███████████████████         │
│  Rotor I→           U (20)  ██████████████████████      │
│  Reflector B        S (18)  ███████████████████         │
│  ←Rotor I           Z (25)  █████████████████████████   │
│  ←Rotor II          G ( 6)  ███████                      │
│  ←Rotor III         M (12)  █████████████               │
│  Output             M (12)  █████████████               │
├──────────────────────────────────────────────────────────┤
│                          E ──→ M                         │
└──────────────────────────────────────────────────────────┘

enigma [AAD]> config
  Current configuration:
    Rotors:   I II III
    Positions: A A D
    Ring settings: 1 1 1
    Reflector: B
    Plugboard: (none)

enigma [AAD]> save my_settings.json
  Configuration saved to my_settings.json

enigma [AAD]> reset
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

# Get all per-character traces
traces = machine.get_all_traces()

# Export configuration
config = machine.get_config()
# config = {
#     "rotor_names": ["IV", "II", "I"],
#     "rotor_positions": ["A", "B", "C"],
#     "ring_settings": [5, 3, 7],
#     "reflector_name": "B",
#     "plugboard_pairs": ["AB", "SZ", "UJ", "MY"],
#     "version": "2.0.0"
# }

# Reset positions
machine.reset_positions()

# Generate a random configuration
from enigma import random_config
cfg = random_config()
random_machine = EnigmaMachine(
    rotor_names=cfg["rotor_names"],
    rotor_positions=cfg["rotor_positions"],
    ring_settings=cfg["ring_settings"],
    reflector_name=cfg["reflector_name"],
    plugboard_pairs=cfg["plugboard_pairs"],
)

# Format output in 5-letter groups (traditional Enigma style)
from enigma import format_output
formatted = format_output(ciphertext, style="grouped", group_size=5)

# Known test vector verification
m = EnigmaMachine(
    rotor_names=["I", "II", "III"],
    rotor_positions=["A", "A", "A"],
    ring_settings=[1, 1, 1],
    reflector_name="B"
)
assert m.encrypt("AAAAA") == "BDZGO"  # Standard Enigma I test vector
```

## Output Formats

### Plain (default)
```
Input:     HELLO WORLD
Encrypted: ILBDA AMTAZ
```

### Grouped (traditional Enigma style)
```
Input:     HELLO WORLD
Encrypted: ILBDA AMTAZ
```
Groups letters into blocks (default 5, customizable with `--group-size`), stripping non-alpha characters.

### Verbose
Shows each character's position and mapping individually. Useful for detailed analysis.

## Config Files

Save and load machine configurations as JSON for reproducible encryption:

```bash
# Save your current settings
python3 enigma.py --save-config enigma_settings.json "HELLO"

# Load and use those same settings for decryption
python3 enigma.py --load-config enigma_settings.json "ILBDA"
```

The config file format:
```json
{
  "rotor_names": ["IV", "II", "I"],
  "rotor_positions": ["A", "B", "C"],
  "ring_settings": [5, 3, 7],
  "reflector_name": "B",
  "plugboard_pairs": ["AB", "SZ"],
  "version": "2.0.0"
}
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

## Testing

```bash
python3 -m pytest test_enigma.py -v
```

85 tests covering reciprocal property, known test vectors, no-self-encryption, double-stepping, plugboard validation, ring setting validation, lowercase handling, position wrapping, random config generation, format output, signal path visualization, config save/load round trips, and more.

## License

MIT