# Rune Cipher 🗝️ᚱᚢᚾᛖ

A terminal cryptography playground that encodes messages with historical ciphers, renders output in **Elder Futhark runic Unicode**, cracks ciphertext using frequency analysis and hill-climbing attacks, and provides detailed text analytics.

## Features

### 7 Ciphers
- **Caesar** — Classic shift cipher with configurable key
- **Vigenère** — Polyalphabetic cipher with keyword
- **Atbash** — Mirror alphabet cipher (self-inverse)
- **ROT13** — Caesar with key 13 (self-inverse)
- **Substitution** — Simple substitution with keyword-based key generation
- **Affine** — Modular arithmetic cipher with two keys (a, b)
- **XOR** — Binary XOR cipher with hex output (symmetric)

### Runic Rendering
All output can be displayed in Elder Futhark runes (ᚨᛒᚲᛞᛖᚠ...). Spaces render as `᛬`. Supports full round-trip conversion (text → runes → text).

### Frequency Analysis
Built-in `analyze` command provides:
- Letter frequency chart with comparison to English
- Index of Coincidence (IoC) calculation
- Chi-squared distance from English
- Top bigrams and trigrams
- English likelihood assessment (High/Medium/Low)

### Cracking Engine
- **Caesar**: Brute-force all 25 shifts, scored by frequency + bigram analysis
- **Vigenère**: Kasiski analysis with Index of Coincidence for key length detection
- **Substitution**: Hill-climbing with random restarts, optimizing bigram score
- **Affine**: Brute-force all valid (a, b) pairs
- Atbash/ROT13: Direct decryption (self-inverse)

### Multiple Interfaces
- **CLI mode** — Script-friendly argparse interface for pipelining
- **Interactive mode** — REPL-style playground with history tracking
- **Demo mode** — One-command showcase of all features
- **File I/O** — `--infile` and `--outfile` flags for batch processing
- **Version flag** — `--version` support

## Installation

```bash
# No dependencies — pure Python 3.6+
# Just download and run:
curl -O https://raw.githubusercontent.com/USER/daily-ideas/main/2026-06-12-rune-cipher/rune_cipher.py
chmod +x rune_cipher.py
```

## How to Run

```bash
# Interactive mode (recommended for exploring)
python3 rune_cipher.py interactive

# Demo — see all ciphers in action
python3 rune_cipher.py demo

# Show version
python3 rune_cipher.py --version

# Encrypt with Caesar cipher
python3 rune_cipher.py encrypt --cipher caesar --key 3 --text "hello world"

# Encrypt with runic output
python3 rune_cipher.py encrypt --cipher caesar --key 7 --text "attack at dawn" --runic

# Encrypt with Vigenère cipher
python3 rune_cipher.py encrypt --cipher vigenere --key secret --text "meet me at the bridge"

# Encrypt with Affine cipher (a=5, b=8)
python3 rune_cipher.py encrypt --cipher affine --key 5,8 --text "hello"

# Encrypt with XOR cipher
python3 rune_cipher.py encrypt --cipher xor --key secret --text "hello"

# Decrypt
python3 rune_cipher.py decrypt --cipher caesar --key 3 --text "khoor zruog"
python3 rune_cipher.py decrypt --cipher affine --key 5,8 --text "rclla"
python3 rune_cipher.py decrypt --cipher xor --key secret --text "1b 00 0f 1e 0a"

# Crack a Caesar cipher (tries all 25 shifts, ranks by English-likeness)
python3 rune_cipher.py crack --cipher caesar --text "khoor zruog"

# Crack a Vigenère cipher (Kasiski analysis)
python3 rune_cipher.py crack --cipher vigenere --text "kbr ulcpo slbae"

# Crack an Affine cipher (brute-force valid keys)
python3 rune_cipher.py crack --cipher affine --text "zrc ivswcvz"

# Frequency analysis
python3 rune_cipher.py analyze --text "khoor zruog"

# Convert text to runes
python3 rune_cipher.py runes --text "hello world"

# Read from file / write to file
python3 rune_cipher.py encrypt --cipher caesar --key 3 --infile plaintext.txt --outfile ciphertext.txt
```

## Usage Examples

### Interactive Mode

```
rune ⟩ encrypt caesar 5 secret message
  ╔══════════════════════════════════════╗
  ║  Caesar (key=5) — Encrypted         ║
  ║  ᛪᛃᚺᚱᛦ᛬ᛗᛗᛋᛋᚨᚷᛖ                  ║
  ╚══════════════════════════════════════╝

rune ⟩ crack caesar khoor zruog
  [1] Key 3: hello world ← BEST MATCH

rune ⟩ runes attack at dawn
  ᛏᚨᛏᛏᚨᚲᚴ᛬ᚨᛏ᛬ᛞᚨᚹᚾ

rune ⟩ stats khoor zruog
  ────────────────────────────────────────────────────
  📊 FREQUENCY ANALYSIS
  ...

rune ⟩ encrypt affine 5,8 secret message
  ╔══════════════════════════════════════╗
  ║  Affine (a=5, b=8) — Encrypted      ║
  ║  ᛗᛖᚲᚱᛖᛏ᛬ᛗᛖᛋᛋᚨᚷᛖ                  ║
  ╚══════════════════════════════════════╝

rune ⟩ history
    1: encrypt caesar 5 secret message
    2: crack caesar khoor zruog
    3: runes attack at dawn
```

### Cracking

The cracker uses:
- **Caesar**: Brute-force all 25 shifts, scored by English letter frequency + bigram frequency
- **Vigenère**: Index-of-coincidence to guess key length, then frequency analysis per column
- **Substitution**: Hill-climbing with random restarts (8 restarts × 500 iterations), optimizing bigram score
- **Affine**: Brute-force all valid (a, b) pairs where gcd(a, 26) = 1

Longer ciphertexts produce more accurate results. Short texts (<20 letters) may not crack cleanly.

### Affine Cipher

The Affine cipher uses the formula E(x) = (ax + b) mod 26, where `a` must be coprime with 26. Valid `a` values: 1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25.

```bash
# Encrypt with Affine (a=5, b=8)
python3 rune_cipher.py encrypt --cipher affine --key 5,8 --text "hello"

# Decrypt
python3 rune_cipher.py decrypt --cipher affine --key 5,8 --text "rclla"

# Crack (tries all 312 valid key combinations)
python3 rune_cipher.py crack --cipher affine --text "rclla"
```

### XOR Cipher

XOR encryption is symmetric — encrypting twice with the same key decrypts. Output is hex-encoded for safe display.

```bash
# Encrypt
python3 rune_cipher.py encrypt --cipher xor --key mykey --text "hello"
# Output: 02 00 0c 0c 06

# Decrypt
python3 rune_cipher.py decrypt --cipher xor --key mykey --text "02 00 0c 0c 06"
# Output: hello
```

### Frequency Analysis

```bash
python3 rune_cipher.py analyze --text "khoor zruog"
```

Outputs: letter frequency chart with English comparison, Index of Coincidence, chi-squared distance, bigrams, trigrams, and English likelihood rating.

### Substitution Cipher with Keywords

```bash
# Use a keyword to generate the substitution alphabet
python3 rune_cipher.py encrypt --cipher substitution --key rune --text "hello"
# Internally generates: runeahijlmopqstuvwxfz (keyword-based alphabet)
```

## Runic Alphabet

The tool maps A–Z to Elder Futhark runes:

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q | R | S | T | U | V | W | X | Y | Z |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ᚨ | ᛒ | ᚲ | ᛞ | ᛖ | ᚠ | ᚷ | ᚺ | ᛁ | ᛃ | ᚴ | ᛚ | ᛗ | ᚾ | ᛟ | ᛈ | ᛩ | ᚱ | ᛋ | ᛏ | ᚢ | ᚡ | ᚹ | ᛪ | ᛦ | ᛉ |

Spaces render as `᛬`

## Testing

```bash
python3 test_rune_cipher.py
```

Runs 35 tests covering:
- Round-trip encryption/decryption for all 7 ciphers
- Runic text conversion (text → runes → text)
- Known-value tests for Caesar, Vigenère, Atbash, Affine
- Edge cases (empty strings, invalid keys, non-alpha characters)
- Cracking accuracy tests
- Frequency analysis validation
- Keyword key generation

## What It Does

Rune Cipher is an educational cryptography tool that lets you:

1. **Encrypt** plaintext using 7 historical and mathematical ciphers (Caesar, Vigenère, Atbash, ROT13, Substitution, Affine, XOR)
2. **Decrypt** ciphertext when you know the key
3. **Crack** ciphertext without knowing the key using statistical analysis (Caesar, Vigenère, Substitution, Affine)
4. **Analyze** any text's frequency profile with detailed statistics
5. **Visualize** encrypted output in ancient Norse runes — making your ciphertext look like an archaeologist's puzzle

The interactive mode provides a REPL with history tracking for quick experimentation, while the CLI interface supports scripting, file I/O, and pipelining.