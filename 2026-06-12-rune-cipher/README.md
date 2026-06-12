# Rune Cipher 🗝️ᚱᚢᚾᛖ

A terminal cryptography playground that encodes messages with historical ciphers, renders output in **Elder Futhark runic Unicode**, and cracks ciphertext using frequency analysis and hill-climbing attacks.

## Features

- **5 Ciphers**: Caesar, Vigenère, Atbash, ROT13, and simple Substitution
- **Runic Rendering**: All output can be displayed in Elder Futhark runes (ᚨᛒᚲᛞᛖᚠ...)
- **Frequency-Analysis Cracker**: Breaks Caesar, Vigenère (Kasiski), and substitution ciphers
- **Interactive Mode**: REPL-style playground for experimenting with ciphers
- **Demo Mode**: One-command showcase of all ciphers and cracking
- **CLI Mode**: Script-friendly argparse interface for pipelining

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

# Encrypt with Caesar cipher
python3 rune_cipher.py encrypt --cipher caesar --key 3 --text "hello world"

# Encrypt with runic output
python3 rune_cipher.py encrypt --cipher caesar --key 7 --text "attack at dawn" --runic

# Encrypt with Vigenère cipher
python3 rune_cipher.py encrypt --cipher vigenere --key secret --text "meet me at the bridge"

# Decrypt
python3 rune_cipher.py decrypt --cipher caesar --key 3 --text "khoor zruog"

# Crack a Caesar cipher (tries all 25 shifts, ranks by English-likeness)
python3 rune_cipher.py crack --cipher caesar --text "khoor zruog"

# Crack a Vigenère cipher (Kasiski analysis)
python3 rune_cipher.py crack --cipher vigenere --text "kbr ulcpo slbae"

# Convert text to runes
python3 rune_cipher.py runes --text "hello world"
```

## Usage Examples

### Interactive Mode

```
rune ⟩ encrypt caesar 5 secret message
  ╔══════════════════════════════════════╗
  ║  Caesar (key=5) — Encrypted          ║
  ║  ᛪᛃᚺᚱᛦ᛬ᛗᛗᛋᛋᚨᚷᛖ                  ║
  ╚══════════════════════════════════════╝

rune ⟩ crack caesar xhjhyw njwij
  [1] Key  5: secret message ← BEST MATCH

rune ⟩ runes attack at dawn
  ᛬ ᚨᛏᛏᚨᚲᚴ᛬ᚨᛏ᛬ᛞᚨᚹᚾ᛬

rune ⟩ random caesar
  📜 Random fact encrypted with Caesar (key=14):
  ...
```

### Cracking

The cracker uses:
- **Caesar**: Brute-force all 25 shifts, scored by English letter frequency + bigram frequency
- **Vigenère**: Index-of-coincidence to guess key length, then frequency analysis per column
- **Substitution**: Hill-climbing with random restarts, optimizing bigram score

Longer ciphertexts produce more accurate results. Short texts (<20 letters) may not crack cleanly.

### Substitution Cipher with Keywords

```bash
# Use a keyword to generate the substitution alphabet
python3 rune_cipher.py encrypt --cipher substitution --key rune --text "hello"
# Internally generates: runekey -> runeahijlmopqstuvwxfz (keyword-based alphabet)
```

## Runic Alphabet

The tool maps A–Z to Elder Futhark runes:

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q | R | S | T | U | V | W | X | Y | Z |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ᚨ | ᛒ | ᚲ | ᛞ | ᛖ | ᚠ | ᚷ | ᚺ | ᛁ | ᛃ | ᚴ | ᛚ | ᛗ | ᚾ | ᛟ | ᛈ | ᛩ | ᚱ | ᛋ | ᛏ | ᚢ | ᚡ | ᚹ | ᛪ | ᛦ | ᛉ |

Spaces render as `᛬`

## What It Does

Rune Cipher is an educational cryptography tool that lets you:

1. **Encrypt** plaintext using historical ciphers (Caesar, Vigenère, Atbash, ROT13, Substitution)
2. **Decrypt** ciphertext when you know the key
3. **Crack** ciphertext without knowing the key using statistical analysis
4. **Visualize** encrypted output in ancient Norse runes — making your ciphertext look like an archaeologist's puzzle

The interactive mode provides a REPL for quick experimentation, while the CLI interface supports scripting and piping.