# Terminal Semaphore Flag Signaler

A CLI tool that translates text into maritime flag semaphore positions and visualizes them as animated ASCII stick figures holding flags. Each letter of the alphabet is represented by holding two flags in specific compass directions — this tool brings that centuries-old signaling system to life in your terminal.

## What is Flag Semaphore?

Flag semaphore is a system of conveying information at a distance by means of visual signals with hand-held flags. It's still used today by the Navy and in scouting. The signaler holds two flags, each in one of 8 compass positions (like the spokes of a wheel), and the combination of the two positions encodes a letter, digit, or command.

```
       6    7    8
        \  |  /
     5-- O --1
        /  |  \
       4    3    2
```

Each letter is a unique pair of two positions (one per arm). For example:
- **A** = flags at positions 1 (down) and 8 (down-left)
- **B** = flags at positions 1 (down) and 7 (left)
- **S** = flags at positions 4 (up-right) and 8 (down-left)

## Features

- **Animated ASCII rendering** — a stick figure with head, torso, legs, and two arms holds flags at the correct angles for each character
- **Full alphabet support** — all 26 letters (A–Z) encoded per the ITU semaphore standard
- **Number mode** — digits 0–9 are encoded using the "numerals" preamble (J position) followed by letter-based codes
- **Compass diagram** — each frame shows a small diagram highlighting the active positions
- **Multiple modes**:
  - **Animated mode** — frame-by-frame animation of your text
  - **Encode mode** — text-only output of positions (no animation, great for piping)
  - **Chart mode** — print the complete semaphore alphabet reference
  - **Interactive mode** — REPL for encoding multiple messages
  - **File mode** — signal the contents of a file
- **Loop mode** — repeat the animation continuously
- **Configurable delay** — control the speed of animation
- **22 unit tests** — full test suite covering encoding, rendering, and edge cases

## Installation

No external dependencies required — pure Python standard library only.

```bash
# Just clone and run
cd ~/daily-ideas/2026-08-13-terminal-semaphore-signaler
python3 semaphore.py --help
```

Requires Python 3.6+ (uses `math`, `argparse`, `os`, `sys`, `time`, `string` — all standard library).

## How to Run

### Basic usage — animate text

```bash
python3 semaphore.py "SOS HELLO"
```

This clears the screen and shows an animated stick figure signaling each character, one frame at a time.

### Encode mode (text only, no animation)

```bash
python3 semaphore.py "SOS" --encode
```

Output:
```
Text: SOS
Frames: 3
----------------------------------------
     'S'  ->  L=4  R=8   (Letter 'S')
     'O'  ->  L=3  R=7   (Letter 'O')
     'S'  ->  L=4  R=8   (Letter 'S')
```

### Print the full semaphore chart

```bash
python3 semaphore.py --chart
```

### Interactive mode

```bash
python3 semaphore.py
```

Then type text and press Enter to signal it. Special commands:
- `:demo` — run a demo sequence ("SOS HELLO 42")
- `:chart` — show the full semaphore chart
- `:file path.txt` — signal the contents of a file
- `:quit` — exit

### File mode

```bash
python3 semaphore.py --file message.txt
```

### Loop the animation

```bash
python3 semaphore.py "HELLO WORLD" --loop
```

### Adjust animation speed

```bash
python3 semaphore.py "HELLO" --delay 0.5   # faster
python3 semaphore.py "HELLO" --delay 2.0   # slower
```

### Hide the compass diagram

```bash
python3 semaphore.py "HELLO" --no-diagram
```

## Usage Examples

```bash
# Signal a distress call
python3 semaphore.py "SOS"

# Signal a message with numbers
python3 semaphore.py "AGENT 007"

# Signal a longer message slowly
python3 semaphore.py "THE EAGLE HAS LANDED" --delay 2.0

# Get the encoding without animation
python3 semaphore.py "HELLO WORLD" --encode

# Print the reference chart
python3 semaphore.py --chart

# Interactive session
python3 semaphore.py
> SOS
> :demo
> :chart
> :quit
```

## How It Works

1. **Encoding**: The `encode_text()` function takes input text and converts each character to a `(left_position, right_position)` pair. Letters map directly via the semaphore table. Digits trigger a "numerals" preamble (the J position) followed by the corresponding letter code. Spaces produce the "rest" position (both arms down).

2. **Rendering**: For each frame, a 40×22 character canvas is created. A stick figure is drawn with a circular head (`@`), vertical torso (`|`), diagonal legs (`\` and `/`), and two arms drawn as lines (`-`) using Bresenham's line algorithm. Flag tips are marked with `#` characters. The arm angle is computed from the semaphore position number using trigonometry.

3. **Animation**: The `animate()` function clears the screen, renders each frame, displays it with the compass diagram and character info, then waits for the configured delay before advancing to the next frame.

## Semaphore Position Reference

```
Position 1 = straight down         (angle: -90°)
Position 2 = down-right            (angle: -45°)
Position 3 = right / horizontal    (angle:   0°)
Position 4 = up-right              (angle:  45°)
Position 5 = straight up           (angle:  90°)
Position 6 = up-left               (angle: 135°)
Position 7 = left / horizontal     (angle: 180°)
Position 8 = down-left             (angle: 225°)
```

## Testing

```bash
cd ~/daily-ideas/2026-08-13-terminal-semaphore-signaler
python3 test_semaphore.py
```

The test suite covers:
- All 26 letters have valid, non-conflicting semaphore mappings
- 8 flag positions with unique angles
- Letter encoding (uppercase and lowercase)
- Space → rest position
- Digit encoding with numeral preamble
- Multi-digit sequences sharing a single preamble
- Unknown character handling
- Figure rendering dimensions and content
- Different positions produce different renders
- Angle-to-delta conversion for all cardinal directions
- Canvas and line-drawing primitives
- Numeral map completeness
- SOS encoding
- Diagram rendering

## Files

| File | Description |
|------|-------------|
| `semaphore.py` | Main program — encoder, renderer, animator, CLI |
| `test_semaphore.py` | 22-test suite covering all functionality |
| `README.md` | This file |

## Educational Notes

Semaphore flag signaling dates back to the early 19th century and was widely used by naval forces before the advent of radio. It remains a practical skill in scouting and naval training. This tool serves as both a learning aid for the semaphore alphabet and a demonstration of how visual encoding systems work.

The ITU (International Telecommunication Union) standardized the flag semaphore system, and the encoding used here follows that standard. In practice, signalers also use special commands like "attention" (both flags raised), "error" (flags crossed), and "ready to receive" — these could be future additions to the tool.