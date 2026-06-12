#!/usr/bin/env python3
"""
Rune Cipher — A terminal cryptography playground.

Encode messages with historical ciphers, render them in runic Unicode,
and crack them with frequency analysis. Supports Caesar, Vigenère,
Substitution, and Atbash ciphers.

Usage:
    python3 rune_cipher.py encrypt --cipher caesar --key 3 --text "hello world"
    python3 rune_cipher.py encrypt --cipher vigenere --key secret --text "attack at dawn"
    python3 rune_cipher.py encrypt --cipher atbash --text "abcxyz"
    python3 rune_cipher.py decrypt --cipher caesar --key 3 --text "khoor zruog"
    python3 rune_cipher.py crack --cipher caesar --text "khoor zruog"
    python3 rune_cipher.py crack --cipher substitution --ciphertext "xktlx wztlx"
    python3 rune_cipher.py interactive
"""

import argparse
import json
import os
import random
import sys
import string
import textwrap
from collections import Counter
from pathlib import Path

# ── Runic Unicode mapping ──────────────────────────────────────────────────────
# Elder Futhark runic alphabet (24 runes) + a few extensions for spacing
RUNE_MAP = {
    'a': 'ᚨ', 'b': 'ᛒ', 'c': 'ᚲ', 'd': 'ᛞ', 'e': 'ᛖ',
    'f': 'ᚠ', 'g': 'ᚷ', 'h': 'ᚺ', 'i': 'ᛁ', 'j': 'ᛃ',
    'k': 'ᚴ', 'l': 'ᛚ', 'm': 'ᛗ', 'n': 'ᚾ', 'o': 'ᛟ',
    'p': 'ᛈ', 'q': 'ᛩ', 'r': 'ᚱ', 's': 'ᛋ', 't': 'ᛏ',
    'u': 'ᚢ', 'v': 'ᚡ', 'w': 'ᚹ', 'x': 'ᛪ', 'y': 'ᛦ',
    'z': 'ᛉ',
}

RUNE_SPACE = '᛬'

# English letter frequency (approximate, from corpus analysis)
ENGLISH_FREQ = {
    'e': 12.7, 't': 9.1, 'a': 8.2, 'o': 7.5, 'i': 7.0,
    'n': 6.7, 's': 6.3, 'h': 6.1, 'r': 6.0, 'd': 4.3,
    'l': 4.0, 'c': 2.8, 'u': 2.8, 'm': 2.4, 'w': 2.4,
    'f': 2.2, 'g': 2.0, 'y': 2.0, 'p': 1.9, 'b': 1.5,
    'v': 1.0, 'k': 0.8, 'j': 0.2, 'x': 0.2, 'q': 0.1,
    'z': 0.1,
}

# Common English bigrams for scoring
COMMON_BIGRAMS = {'th', 'he', 'in', 'er', 'an', 'on', 'en', 'at',
                  'es', 'ed', 'or', 'te', 'of', 'nd', 'to', 'st',
                  'al', 'ar', 'ng', 'se', 'ha', 'as', 'ou', 'io',
                  'le', 've', 'co', 'me', 'de', 'hi', 'ri', 'ro',
                  'ic', 'ne', 'ea', 'ra', 'ce'}


def text_to_runes(text: str) -> str:
    """Convert ASCII text to runic characters."""
    result = []
    for ch in text.lower():
        if ch in RUNE_MAP:
            result.append(RUNE_MAP[ch])
        elif ch == ' ':
            result.append(RUNE_SPACE)
        elif ch == '\n':
            result.append('\n')
        else:
            result.append(ch)
    return ''.join(result)


def runes_to_text(runes: str) -> str:
    """Convert runic characters back to ASCII."""
    reverse_map = {v: k for k, v in RUNE_MAP.items()}
    reverse_map[RUNE_SPACE] = ' '
    result = []
    for ch in runes:
        if ch in reverse_map:
            result.append(reverse_map[ch])
        elif ch == '\n':
            result.append('\n')
        else:
            result.append(ch)
    return ''.join(result)


# ── Ciphers ─────────────────────────────────────────────────────────────────────

def caesar_encrypt(text: str, key: int) -> str:
    """Encrypt with Caesar cipher (shift cipher)."""
    result = []
    for ch in text.lower():
        if ch.isalpha():
            shifted = chr((ord(ch) - ord('a') + key) % 26 + ord('a'))
            result.append(shifted)
        else:
            result.append(ch)
    return ''.join(result)


def caesar_decrypt(text: str, key: int) -> str:
    """Decrypt Caesar cipher by shifting backwards."""
    return caesar_encrypt(text, -key)


def vigenere_encrypt(text: str, key: str) -> str:
    """Encrypt with Vigenère cipher."""
    key = key.lower()
    result = []
    ki = 0
    for ch in text.lower():
        if ch.isalpha():
            shift = ord(key[ki % len(key)]) - ord('a')
            result.append(chr((ord(ch) - ord('a') + shift) % 26 + ord('a')))
            ki += 1
        else:
            result.append(ch)
    return ''.join(result)


def vigenere_decrypt(text: str, key: str) -> str:
    """Decrypt Vigenère cipher."""
    key = key.lower()
    result = []
    ki = 0
    for ch in text.lower():
        if ch.isalpha():
            shift = ord(key[ki % len(key)]) - ord('a')
            result.append(chr((ord(ch) - ord('a') - shift) % 26 + ord('a')))
            ki += 1
        else:
            result.append(ch)
    return ''.join(result)


def atbash_encrypt(text: str) -> str:
    """Atbash cipher: A↔Z, B↔Y, etc. Encryption = decryption."""
    result = []
    for ch in text.lower():
        if ch.isalpha():
            result.append(chr(ord('z') - (ord(ch) - ord('a'))))
        else:
            result.append(ch)
    return ''.join(result)


def rot13_encrypt(text: str) -> str:
    """ROT13 cipher (Caesar with key 13)."""
    return caesar_encrypt(text, 13)


def substitution_encrypt(text: str, key: str) -> str:
    """Encrypt with simple substitution cipher using a 26-char key."""
    key = key.lower()
    if len(key) != 26 or len(set(key)) != 26:
        raise ValueError("Substitution key must be 26 unique letters.")
    result = []
    for ch in text.lower():
        if ch.isalpha():
            result.append(key[ord(ch) - ord('a')])
        else:
            result.append(ch)
    return ''.join(result)


def substitution_decrypt(text: str, key: str) -> str:
    """Decrypt simple substitution cipher."""
    key = key.lower()
    reverse = {key[i]: chr(ord('a') + i) for i in range(26)}
    result = []
    for ch in text.lower():
        if ch in reverse:
            result.append(reverse[ch])
        else:
            result.append(ch)
    return ''.join(result)


def random_substitution_key() -> str:
    """Generate a random substitution cipher key."""
    alpha = list(string.ascii_lowercase)
    random.shuffle(alpha)
    return ''.join(alpha)


def generate_keyword_key(keyword: str) -> str:
    """Generate a substitution key from a keyword (keyword cipher)."""
    keyword = keyword.lower()
    seen = set()
    key = []
    for ch in keyword:
        if ch.isalpha() and ch not in seen:
            key.append(ch)
            seen.add(ch)
    for ch in string.ascii_lowercase:
        if ch not in seen:
            key.append(ch)
    return ''.join(key)


# ── Cracking / Frequency Analysis ─────────────────────────────────────────────

def frequency_score(text: str) -> float:
    """Score text by how closely its letter frequency matches English.
    Lower score = better match."""
    text = text.lower()
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return float('inf')
    total = len(letters)
    counts = Counter(letters)
    score = 0.0
    for letter, expected_freq in ENGLISH_FREQ.items():
        actual_freq = (counts.get(letter, 0) / total) * 100
        score += (actual_freq - expected_freq) ** 2
    return score


def bigram_score(text: str) -> float:
    """Score text by how many common English bigrams it contains.
    Higher score = more English-like."""
    text = text.lower()
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) < 2:
        return 0
    bigrams = [''.join(letters[i:i+2]) for i in range(len(letters) - 1)]
    return sum(1 for b in bigrams if b in COMMON_BIGRAMS)


def crack_caesar(ciphertext: str) -> list:
    """Try all 25 shifts and return candidates sorted by English-likeness."""
    candidates = []
    for key in range(1, 26):
        decrypted = caesar_decrypt(ciphertext, key)
        freq = frequency_score(decrypted)
        bigr = bigram_score(decrypted)
        combined = freq - bigr * 2  # lower is better
        candidates.append((key, decrypted, combined))
    candidates.sort(key=lambda x: x[2])
    return [(k, d) for k, d, _ in candidates]


def crack_vigenere(ciphertext: str, max_key_len: int = 10) -> list:
    """Attempt to crack Vigenère cipher using Kasiski-like analysis.
    Returns list of (key, decrypted_text) candidates."""
    ciphertext_clean = ''.join(ch for ch in ciphertext.lower() if ch.isalpha())
    if len(ciphertext_clean) < 12:
        return [("?", ciphertext)]
    
    # Find repeating substrings to guess key length (simplified Kasiski)
    def find_key_length_candidates(text, max_len):
        scores = {}
        for kl in range(2, min(max_len + 1, len(text) // 3)):
            groups = ['' for _ in range(kl)]
            for i, ch in enumerate(text):
                groups[i % kl] += ch
            # Index of coincidence for each group
            total_ic = 0
            for g in groups:
                n = len(g)
                if n < 2:
                    continue
                counts = Counter(g)
                ic = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))
                total_ic += ic
            avg_ic = total_ic / kl
            scores[kl] = avg_ic
        # Sort by IC closest to English IC (~0.0667)
        return sorted(scores.keys(), key=lambda k: -scores[k])
    
    key_lengths = find_key_length_candidates(ciphertext_clean, max_key_len)
    candidates = []
    
    for kl in key_lengths[:4]:  # Try top 4 key length candidates
        # For each group, find best shift
        key_chars = []
        for pos in range(kl):
            group = ciphertext_clean[pos::kl]
            best_shift = 0
            best_score = float('inf')
            for shift in range(26):
                shifted = caesar_encrypt(group, -shift)
                s = frequency_score(shifted)
                if s < best_score:
                    best_score = s
                    best_shift = shift
            key_chars.append(chr(best_shift + ord('a')))
        key = ''.join(key_chars)
        decrypted = vigenere_decrypt(ciphertext, key)
        score = frequency_score(decrypted) - bigram_score(decrypted) * 2
        candidates.append((key, decrypted, score))
    
    candidates.sort(key=lambda x: x[2])
    return [(k, d) for k, d, _ in candidates]


def crack_substitution(ciphertext: str, iterations: int = 500) -> list:
    """Hill-climbing attack on simple substitution cipher.
    Returns top candidates."""
    ciphertext_clean = ''.join(ch for ch in ciphertext.lower() if ch.isalpha())
    if len(ciphertext_clean) < 10:
        return [("<too short>", ciphertext)]
    
    best_overall = []
    
    for _ in range(8):  # Multiple restarts
        key = list(string.ascii_lowercase)
        random.shuffle(key)
        current_key = ''.join(key)
        current_text = substitution_decrypt(ciphertext, current_key)
        current_score = frequency_score(current_text) - bigram_score(current_text) * 2
        
        improved = True
        iters = 0
        while improved and iters < iterations:
            improved = False
            for _ in range(200):
                # Swap two random positions
                a, b = random.sample(range(26), 2)
                new_key = list(current_key)
                new_key[a], new_key[b] = new_key[b], new_key[a]
                new_key = ''.join(new_key)
                new_text = substitution_decrypt(ciphertext, new_key)
                new_score = frequency_score(new_text) - bigram_score(new_text) * 2
                if new_score < current_score:
                    current_key = new_key
                    current_score = new_score
                    current_text = new_text
                    improved = True
            iters += 1
        
        best_overall.append((current_key, current_text, current_score))
    
    best_overall.sort(key=lambda x: x[2])
    return [(k, d) for k, d, _ in best_overall[:3]]


# ── Display helpers ─────────────────────────────────────────────────────────────

BANNER = r"""
╦╔═╔═╗╔╦╗╔═╗╦ ╦╦  
╠╩╗║ ║║║║║╣ ║║║║  
╩ ╩╚═╝╩ ╩╚═╝╚╩╝╩═╝
    C I P H E R
"""

DIVIDER = "─" * 52

def print_runic_box(text: str, title: str = ""):
    """Print text in a runic-styled box."""
    rune_text = text_to_runes(text)
    lines = rune_text.split('\n')
    max_len = max(len(line) for line in lines) if lines else 0
    width = max(max_len + 4, 40)
    
    print(f"  ╔{'═' * width}╗")
    if title:
        print(f"  ║  {title.center(width - 2)}  ║")
        print(f"  ╠{'═' * width}╣")
    for line in lines:
        print(f"  ║  {line.ljust(width - 2)}  ║")
    print(f"  ╚{'═' * width}╝")


def print_candidates(candidates: list, cipher_name: str, show_key: bool = True):
    """Print cracking candidates nicely."""
    print(f"\n🔍 Cracking {cipher_name} — Top candidates:\n")
    for i, item in enumerate(candidates):
        if show_key and len(item) == 2:
            key, plaintext = item
            print(f"  [{i+1}] Key: {key}")
        elif len(item) == 2:
            plaintext = item[1] if isinstance(item[1], str) else item[0]
            key = item[0]
            print(f"  [{i+1}] Key: {key}")
        else:
            key, plaintext = item[0], item[1]
            print(f"  [{i+1}] Key: {key}")
        print(f"      Plaintext: {plaintext}")
        print(f"      Runes:     {text_to_runes(plaintext)}")
        print()


# ── Interactive mode ────────────────────────────────────────────────────────────

def interactive():
    """Run an interactive cipher session."""
    print(BANNER)
    print("  Welcome to Rune Cipher — encode, decode, and crack ciphers!")
    print("  Type 'help' for commands, 'quit' to exit.\n")
    
    current_text = ""
    
    while True:
        try:
            prompt = "rune ⟩ "
            cmd = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  ✦ Farewell, cryptographer! ✦\n")
            break
        
        if not cmd:
            continue
        
        parts = cmd.split(None, 1)
        action = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        
        if action in ('quit', 'exit', 'q'):
            print("\n  ✦ Farewell, cryptographer! ✦\n")
            break
        
        elif action == 'help':
            print(textwrap.dedent("""
                Commands:
                  encrypt <cipher> <key> <text>  — Encrypt text
                  decrypt <cipher> <key> <text>  — Decrypt text  
                  crack <cipher> <text>          — Crack ciphertext
                  runes <text>                    — Convert to runes
                  fromrunes <text>                — Convert from runes
                  random <cipher>                 — Encrypt random fact
                  help                            — Show this help
                  quit                            — Exit
                
                Ciphers: caesar, vigenere, atbash, rot13, substitution
                
                Examples:
                  encrypt caesar 3 hello world
                  decrypt vigenere secret jiqtg vjwv
                  crack caesar khoor zruog
                  runes attack at dawn
            """))
        
        elif action == 'runes':
            print(f"  ᛬ {text_to_runes(rest)}")
        
        elif action == 'fromrunes':
            print(f"  → {runes_to_text(rest)}")
        
        elif action in ('encrypt', 'decrypt', 'crack'):
            sub = rest.split()
            if len(sub) < 1:
                print("  ⚠ Specify a cipher. Type 'help' for usage.")
                continue
            
            cipher = sub[0].lower()
            
            if action in ('encrypt', 'decrypt'):
                result = ""  # initialize to satisfy linter
                if cipher in ('atbash', 'rot13') and len(sub) >= 2:
                    # No key needed
                    text = ' '.join(sub[1:])
                    if cipher == 'atbash':
                        result = atbash_encrypt(text)
                    else:
                        result = rot13_encrypt(text)
                    if action == 'decrypt':
                        if cipher == 'atbash':
                            result = atbash_encrypt(text)
                        else:
                            result = rot13_encrypt(text)
                    current_text = result
                    print_runic_box(result, f"{cipher.title()} — {action.title()}ed")
                    print(f"\n  ASCII: {result}")
                
                elif cipher in ('caesar',) and len(sub) >= 3:
                    try:
                        key = int(sub[1])
                    except ValueError:
                        print("  ⚠ Caesar key must be a number.")
                        continue
                    text = ' '.join(sub[2:])
                    if action == 'encrypt':
                        result = caesar_encrypt(text, key)
                    else:
                        result = caesar_decrypt(text, key)
                    current_text = result
                    print_runic_box(result, f"Caesar (key={key}) — {action.title()}ed")
                    print(f"\n  ASCII: {result}")
                
                elif cipher == 'vigenere' and len(sub) >= 3:
                    key = sub[1]
                    text = ' '.join(sub[2:])
                    if action == 'encrypt':
                        result = vigenere_encrypt(text, key)
                    else:
                        result = vigenere_decrypt(text, key)
                    current_text = result
                    print_runic_box(result, f"Vigenère (key={key}) — {action.title()}ed")
                    print(f"\n  ASCII: {result}")
                
                elif cipher == 'substitution' and len(sub) >= 3:
                    key = sub[1]
                    text = ' '.join(sub[2:])
                    if len(key) != 26:
                        # Treat as keyword
                        key = generate_keyword_key(key)
                    try:
                        if action == 'encrypt':
                            result = substitution_encrypt(text, key)
                        else:
                            result = substitution_decrypt(text, key)
                        current_text = result
                        print_runic_box(result, f"Substitution — {action.title()}ed")
                        print(f"\n  ASCII: {result}")
                        print(f"  Key: {key}")
                    except ValueError as e:
                        print(f"  ⚠ {e}")
                
                else:
                    print(f"  ⚠ Invalid usage. Type 'help' for usage.")
            
            elif action == 'crack':
                if cipher == 'caesar':
                    text = ' '.join(sub[1:])
                    if not text.strip():
                        print("  ⚠ Provide ciphertext to crack.")
                        continue
                    candidates = crack_caesar(text)
                    print_candidates(candidates, "Caesar")
                    if candidates:
                        current_text = candidates[0][1]
                
                elif cipher == 'vigenere':
                    text = ' '.join(sub[1:])
                    if not text.strip():
                        print("  ⚠ Provide ciphertext to crack.")
                        continue
                    candidates = crack_vigenere(text)
                    print_candidates(candidates, "Vigenère")
                    if candidates:
                        current_text = candidates[0][1]
                
                elif cipher == 'substitution':
                    text = ' '.join(sub[1:])
                    if not text.strip():
                        print("  ⚠ Provide ciphertext to crack.")
                        continue
                    print("  ⏳ Hill-climbing attack in progress (this may take a moment)...")
                    candidates = crack_substitution(text)
                    print_candidates(candidates, "Substitution")
                    if candidates:
                        current_text = candidates[0][1]
                
                elif cipher in ('atbash', 'rot13'):
                    text = ' '.join(sub[1:])
                    if cipher == 'atbash':
                        result = atbash_encrypt(text)
                    else:
                        result = rot13_encrypt(text)
                    print(f"\n  {cipher.title()} is its own inverse!")
                    print_runic_box(result, f"{cipher.title()} — Decrypted")
                    print(f"\n  ASCII: {result}")
                    current_text = result
                
                else:
                    print(f"  ⚠ Unknown cipher: {cipher}")
        
        elif action == 'random':
            facts = [
                "the quick brown fox jumps over the lazy dog",
                "cryptography is the practice and study of techniques for secure communication",
                "the enigma machine was used by nazi germany to protect communications",
                "alan turing helped crack the enigma code during world war two",
                "julius caesar used a simple shift cipher for military messages",
                "the vigenere cipher was called the indecipherable cipher for three centuries",
                "frequency analysis was first described by al kindi in the ninth century",
                "ancient spartans used a scytale a cylinder wrapped with a strip of parchment",
            ]
            text = random.choice(facts)
            cipher = sub[0].lower() if sub else 'caesar'
            if cipher == 'caesar':
                key = random.randint(1, 25)
                result = caesar_encrypt(text, key)
                print(f"  📜 Random fact encrypted with Caesar (key={key}):")
            elif cipher == 'vigenere':
                key = random.choice(['secret', 'rune', 'cipher', 'magic', 'ancient'])
                result = vigenere_encrypt(text, key)
                print(f"  📜 Random fact encrypted with Vigenère (key={key}):")
            elif cipher == 'atbash':
                result = atbash_encrypt(text)
                print(f"  📜 Random fact encrypted with Atbash:")
            elif cipher == 'rot13':
                result = rot13_encrypt(text)
                print(f"  📜 Random fact encrypted with ROT13:")
            else:
                key = generate_keyword_key(random.choice(['rune', 'norse', 'viking']))
                result = substitution_encrypt(text, key)
                print(f"  📜 Random fact encrypted with Substitution (keyword key):")
            
            print_runic_box(result, "Ciphertext")
            print(f"\n  ASCII: {result}")
        
        else:
            print(f"  ⚠ Unknown command: {action}. Type 'help' for commands.")


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Rune Cipher — Terminal cryptography playground with runic rendering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              rune_cipher.py encrypt --cipher caesar --key 3 --text "hello world"
              rune_cipher.py encrypt --cipher vigenere --key secret --text "attack at dawn"
              rune_cipher.py decrypt --cipher caesar --key 3 --text "khoor zruog"
              rune_cipher.py crack --cipher caesar --text "khoor zruog"
              rune_cipher.py crack --cipher vigenere --text "lxfopv frhsr"
              rune_cipher.py interactive
        """)
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # encrypt
    enc = subparsers.add_parser('encrypt', help='Encrypt text')
    enc.add_argument('--cipher', required=True,
                     choices=['caesar', 'vigenere', 'atbash', 'rot13', 'substitution'],
                     help='Cipher to use')
    enc.add_argument('--key', default='', help='Cipher key (number for caesar, word for vigenere/substitution)')
    enc.add_argument('--text', required=True, help='Text to encrypt')
    enc.add_argument('--runic', action='store_true', help='Also display runic output')
    
    # decrypt
    dec = subparsers.add_parser('decrypt', help='Decrypt text')
    dec.add_argument('--cipher', required=True,
                    choices=['caesar', 'vigenere', 'atbash', 'rot13', 'substitution'],
                    help='Cipher to use')
    dec.add_argument('--key', default='', help='Cipher key')
    dec.add_argument('--text', required=True, help='Text to decrypt')
    dec.add_argument('--runic', action='store_true', help='Also display runic output')
    
    # crack
    crk = subparsers.add_parser('crack', help='Crack ciphertext using frequency analysis')
    crk.add_argument('--cipher', required=True,
                    choices=['caesar', 'vigenere', 'substitution', 'atbash', 'rot13'],
                    help='Cipher type to crack')
    crk.add_argument('--text', required=True, help='Ciphertext to crack')
    crk.add_argument('--top', type=int, default=5, help='Number of candidates to show (default: 5)')
    
    # runes
    run = subparsers.add_parser('runes', help='Convert text to runic characters')
    run.add_argument('--text', required=True, help='Text to convert')
    
    # interactive
    subparsers.add_parser('interactive', help='Start interactive mode')
    
    # demo
    subparsers.add_parser('demo', help='Run a demo showing all ciphers')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'interactive':
        interactive()
        return
    
    if args.command == 'demo':
        print(BANNER)
        demo_text = "the ancient runes conceal great power"
        print(f"\n  Original: {demo_text}")
        print(f"  Runes:   {text_to_runes(demo_text)}\n")
        
        print(DIVIDER)
        print("  CAESAR CIPHER (key=7)")
        enc = caesar_encrypt(demo_text, 7)
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {caesar_decrypt(enc, 7)}\n")
        
        print(DIVIDER)
        print("  VIGENÈRE CIPHER (key='rune')")
        enc = vigenere_encrypt(demo_text, 'rune')
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {vigenere_decrypt(enc, 'rune')}\n")
        
        print(DIVIDER)
        print("  ATBASH CIPHER")
        enc = atbash_encrypt(demo_text)
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {atbash_encrypt(enc)}\n")
        
        print(DIVIDER)
        print("  ROT13 CIPHER")
        enc = rot13_encrypt(demo_text)
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {rot13_encrypt(enc)}\n")
        
        print(DIVIDER)
        print("  CRACKING DEMO — Caesar-encrypted ciphertext")
        ct = caesar_encrypt("attack the fortress at dawn", 11)
        print(f"  Ciphertext: {ct}")
        print(f"  Cracking...")
        candidates = crack_caesar(ct)
        for i, (key, plain) in enumerate(candidates[:3]):
            marker = " ← BEST" if i == 0 else ""
            print(f"    Key {key:2d}: {plain}{marker}")
        print()
        
        return
    
    if args.command == 'runes':
        result = text_to_runes(args.text)
        print(result)
        return
    
    if args.command == 'encrypt':
        cipher = args.cipher
        text = args.text
        
        if cipher == 'caesar':
            key = int(args.key) if args.key else 3
            result = caesar_encrypt(text, key)
        elif cipher == 'vigenere':
            key = args.key or 'secret'
            result = vigenere_encrypt(text, key)
        elif cipher == 'atbash':
            result = atbash_encrypt(text)
        elif cipher == 'rot13':
            result = rot13_encrypt(text)
        elif cipher == 'substitution':
            key = args.key
            if len(key) != 26:
                key = generate_keyword_key(key)
            result = substitution_encrypt(text, key)
            print(f"Substitution key: {key}")
        
        print(f"Result: {result}")
        if args.runic:
            print(f"Runes:  {text_to_runes(result)}")
    
    elif args.command == 'decrypt':
        cipher = args.cipher
        text = args.text
        
        if cipher == 'caesar':
            key = int(args.key) if args.key else 3
            result = caesar_decrypt(text, key)
        elif cipher == 'vigenere':
            key = args.key or 'secret'
            result = vigenere_decrypt(text, key)
        elif cipher == 'atbash':
            result = atbash_encrypt(text)  # Atbash is its own inverse
        elif cipher == 'rot13':
            result = rot13_encrypt(text)  # ROT13 is its own inverse
        elif cipher == 'substitution':
            key = args.key
            if len(key) != 26:
                key = generate_keyword_key(key)
            result = substitution_decrypt(text, key)
            print(f"Substitution key: {key}")
        
        print(f"Result: {result}")
        if args.runic:
            print(f"Runes:  {text_to_runes(result)}")
    
    elif args.command == 'crack':
        cipher = args.cipher
        text = args.text
        
        if cipher == 'caesar':
            candidates = crack_caesar(text)
            print(f"Top {min(args.top, len(candidates))} Caesar cipher candidates:\n")
            for i, (key, plain) in enumerate(candidates[:args.top]):
                marker = " ← BEST MATCH" if i == 0 else ""
                print(f"  Key {key:2d}: {plain}{marker}")
                print(f"         {text_to_runes(plain)}\n")
        
        elif cipher == 'vigenere':
            print("Cracking Vigenère cipher (Kasiski analysis)...\n")
            candidates = crack_vigenere(text)
            for i, (key, plain) in enumerate(candidates[:args.top]):
                marker = " ← BEST MATCH" if i == 0 else ""
                print(f"  Key \"{key}\": {plain}{marker}")
                print(f"           {text_to_runes(plain)}\n")
        
        elif cipher == 'substitution':
            print("Cracking substitution cipher (hill-climbing attack)...\n")
            candidates = crack_substitution(text)
            for i, (key, plain) in enumerate(candidates[:args.top]):
                marker = " ← BEST MATCH" if i == 0 else ""
                print(f"  Key: {key}")
                print(f"  Text: {plain}{marker}\n")
        
        elif cipher in ('atbash', 'rot13'):
            if cipher == 'atbash':
                result = atbash_encrypt(text)
            else:
                result = rot13_encrypt(text)
            print(f"{cipher} is its own inverse!")
            print(f"Decrypted: {result}")
            print(f"Runes:     {text_to_runes(result)}")


if __name__ == '__main__':
    main()