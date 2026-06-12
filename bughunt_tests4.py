#!/usr/bin/env python3
"""Additional edge case tests for rune cipher."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-rune-cipher'))
from rune_cipher import *

# Bug: crack_vigenere with short text returns ("<short>", original_ciphertext)
# The second element should be a decryption attempt, not the original ciphertext
print("=== BUG: crack_vigenere short text returns original ciphertext ===")
result = crack_vigenere("ab")
print(f"crack_vigenere('ab') = {result}")
print(f"  Second element is original ciphertext: {result[0][1] == 'ab'}")
print(f"  This is misleading - user expects decrypted text, not ciphertext")

# Bug: analyze_frequency IoC with single letter has 0*(0-1)/(1*0) = 0/0 = ZeroDivisionError potential
print("\n=== BUG: analyze_frequency IoC with 1 letter ===")
# n=1: ic = c*(c-1) / (n*(n-1)) = 1*0 / (1*0) = 0/0
result = analyze_frequency("a")
print(f"analyze_frequency('a') = IoC = {result.get('index_of_coincidence')}")
# Should handle n=1 case (division by zero)

# Bug: analyze_frequency with exactly 2 letters
result2 = analyze_frequency("ab")
print(f"analyze_frequency('ab') = IoC = {result2.get('index_of_coincidence')}")

# Bug: crack_vigenere uses frequency_score instead of combined_score for per-column analysis
# This could make it less accurate
print("\n=== crack_vigenere uses frequency_score vs combined_score ===")
print("In crack_vigenere, per-column analysis uses frequency_score, not combined_score")
print("This reduces accuracy because bigrams and common words are not considered")

# Bug: xor_encrypt doesn't handle text with characters > 127 properly for display
# But it stores them as hex, so the round-trip should work
print("\n=== XOR round-trip with high unicode ===")
text = "hello"
key = "k"
enc = xor_encrypt(text, key)
dec = xor_decrypt(enc, key)
print(f"XOR round-trip: '{text}' -> '{enc}' -> '{dec}' = {text == dec}")

# Test: text_to_runes with newline characters
text_newline = "hello\nworld"
runes = text_to_runes(text_newline)
back = runes_to_text(runes)
print(f"\n=== Rune round-trip with newline ===")
print(f"Original: {repr(text_newline)}")
print(f"Runes: {repr(runes)}")
print(f"Back: {repr(back)}")
print(f"Match: {text_newline == back}")

# Bug: In the interactive mode, when encrypting with atbash/rot13, 
# the action title says "Encrypt" or "Decrypt" based on user input,
# but the title formatting uses f"{action.title()}ed" which becomes
# "Encrypt" -> "Encrypted" or "Decrypt" -> "Decrypted"
# This is correct behavior, not a bug.

# Check: What about generate_keyword_key with empty keyword?
print("\n=== generate_keyword_key edge cases ===")
try:
    key = generate_keyword_key("")
    print(f"generate_keyword_key(''): {key}")
    print(f"  Length: {len(key)}, unique: {len(set(key))}")
except Exception as e:
    print(f"generate_keyword_key('') raises: {e}")

# Check: generate_keyword_key with keyword containing all unique letters
key2 = generate_keyword_key("abcdefghijklmnopqrstuvwxyz")
print(f"generate_keyword_key('abcdefghijklmnopqrstuvwxyz'): {key2}")

# Bug: crack_affine returns top 10 candidates, but test expects to find the correct one
print("\n=== crack_affine accuracy ===")
text = "the quick brown fox jumps over the lazy dog"
a, b = 5, 8
ct = affine_encrypt(text, a, b)
candidates = crack_affine(ct)
found = False
for ca, cb, plain in candidates:
    if ca == a and cb == b:
        found = True
        print(f"Found correct key (a={a}, b={b}): {plain[:30]}...")
        break
if not found:
    print(f"WARNING: Correct key not found in top 10 candidates")
    print(f"Top candidate: a={candidates[0][0]}, b={candidates[0][1]} -> {candidates[0][2][:30]}")

# Bug: In crack_vigenere, find_key_length_candidates uses len(text)//3+1
# which can make the range very small for short texts
# The minimum key length tried is 2, but max is limited by text length

# Bug: combined_score uses word matching but only strips and splits on spaces
# Punctuation attached to words would prevent matching
print("\n=== combined_score word matching ===")
score1 = combined_score("the cat sat on the mat")
score2 = combined_score("the, cat. sat! on? the! mat.")
print(f"combined_score('the cat sat on the mat') = {score1:.2f}")
print(f"combined_score('the, cat. sat! on? the! mat.') = {score2:.2f}")
print(f"Punctuation hurts scoring: {score2 > score1}")

# Bug: In rune_cipher, the XOR encrypt function uses ord() on individual characters
# which works fine for ASCII but multi-byte chars produce values > 255
# These are stored as hex which can be > 2 digits, but xor_decrypt uses int(h, 16)
# which handles this correctly. However, the README example shows hex like "05 1c 07 09 16"
# which are all 2-digit hex, suggesting single-byte. Let's verify round-trip with unicode.
print("\n=== XOR with multi-byte unicode ===")
text_utf8 = "café"
enc = xor_encrypt(text_utf8, "key")
dec = xor_decrypt(enc, "key")
print(f"XOR round-trip 'café': {dec == text_utf8}")

# This works because Python's ord() returns the full Unicode code point
# and int(h, 16) correctly parses multi-digit hex values.
# So the hex output might have variable-width entries like "1b 0 3e9" instead of "1b 00 0f"
# Wait, let me check the format more carefully
enc_hello = xor_encrypt("hello", "key")
enc_cafe = xor_encrypt("café", "key")
print(f"XOR 'hello' with 'key': {enc_hello}")
print(f"XOR 'café' with 'key': {enc_cafe}")
# Note: 'é' has ord 233, so hex would be "e9" which is fine (2 digits)
# But what about higher unicode chars?
enc_emoji = xor_encrypt("a", "k")
print(f"XOR 'a' with 'k': {enc_emoji}")  # Should be hex of ord('a') ^ ord('k')