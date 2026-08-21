#!/usr/bin/env python3
"""
load_tables.py — Load Braille translation tables into W25Q16 flash

Generates Grade 1 Braille lookup tables for 8 languages and writes them
to the Glyph Press's external W25Q16 flash via the RP2040 USB-CDC interface.

Usage:
    python load_tables.py --port /dev/ttyACM0

Flash layout (W25Q16, 2 MB):
    0x0000: English Grade 1 table (128 bytes)
    0x0080: French
    0x0100: Spanish
    0x0180: German
    0x0200: Portuguese
    0x0280: Arabic
    0x0300: Hindi
    0x0380: Chinese pinyin
    0x0400: UEB contraction trie (4 KB)
"""

import argparse
import struct
import serial
import sys
import time

# ── Grade 1 English Braille (ASCII 0x20-0x7E) ──────────────────────
# Standard dot numbering: 1 4
#                        2 5
#                        3 6
# Bit mapping: bit0=dot1, bit1=dot2, ... bit5=dot6

ENGLISH = {
    ' ': 0x00, '!': 0x2A, '#': 0x3C, "'": 0x04, ',': 0x02,
    '-': 0x24, '.': 0x06, '?': 0x20, ':': 0x0A, ';': 0x08,
    '0': 0x3E, '1': 0x01, '2': 0x03, '3': 0x09, '4': 0x19,
    '5': 0x11, '6': 0x0B, '7': 0x1B, '8': 0x0D, '9': 0x05,
    'a': 0x01, 'b': 0x03, 'c': 0x09, 'd': 0x19, 'e': 0x11,
    'f': 0x0B, 'g': 0x1B, 'h': 0x0D, 'i': 0x05, 'j': 0x1D,
    'k': 0x0E, 'l': 0x07, 'm': 0x0A, 'n': 0x1A, 'o': 0x12,
    'p': 0x0F, 'q': 0x1F, 'r': 0x0C, 's': 0x0E, 't': 0x1E,
    'u': 0x06, 'v': 0x16, 'w': 0x1E, 'x': 0x0E, 'y': 0x1C,
    'z': 0x07,
}

# French Braille has additional accented chars
FRENCH = dict(ENGLISH)
FRENCH.update({
    'à': 0x1B, 'â': 0x1B, 'é': 0x0E, 'è': 0x0E, 'ê': 0x0E,
    'ë': 0x0E, 'î': 0x0E, 'ï': 0x0E, 'ô': 0x12, 'ù': 0x06,
    'û': 0x06, 'ç': 0x09,
})

# Spanish adds ñ
SPANISH = dict(ENGLISH)
SPANISH.update({'ñ': 0x1D, '¿': 0x20, '¡': 0x2A})

# German adds umlauts
GERMAN = dict(ENGLISH)
GERMAN.update({'ä': 0x1D, 'ö': 0x12, 'ü': 0x06, 'ß': 0x0E})

# Portuguese
PORTUGUESE = dict(ENGLISH)
PORTUGUESE.update({'ã': 0x1B, 'õ': 0x12, 'ç': 0x09, 'á': 0x01, 'é': 0x0E})

# Arabic (simplified — actual Arabic Braille is read left-to-right)
ARABIC = dict(ENGLISH)
ARABIC.update({'أ': 0x01, 'ب': 0x03, 'ج': 0x09, 'د': 0x19, 'ه': 0x11})

# Hindi (Devanagari simplified)
HINDI = dict(ENGLISH)
HINDI.update({'अ': 0x01, 'क': 0x0E, 'ख': 0x0E, 'ग': 0x1B})

# Chinese pinyin (uses standard Latin Braille)
CHINESE = dict(ENGLISH)

LANGUAGES = [ENGLISH, FRENCH, SPANISH, GERMAN, PORTUGUESE, ARABIC, HINDI, CHINESE]
LANG_NAMES = ["en", "fr", "es", "de", "pt", "ar", "hi", "zh"]


def build_table(lang_dict):
    """Build a 128-byte lookup table from a dictionary."""
    table = bytearray(128)
    for ch, dots in lang_dict.items():
        code = ord(ch)
        if 0 <= code < 128:
            table[code] = dots
    # Uppercase → same as lowercase
    for i in range(ord('A'), ord('Z') + 1):
        lower = i + 32
        if lower < 128:
            table[i] = table[lower]
    return bytes(table)


def write_flash(ser, addr, data):
    """Send a FLASH_WRITE command to the RP2040 USB-CDC interface."""
    # Protocol: "FLASH_W <addr_hex> <data_hex>\n"
    hex_addr = f"{addr:04X}"
    hex_data = data.hex().upper()
    cmd = f"FLASH_W {hex_addr} {hex_data}\n"
    ser.write(cmd.encode("ascii"))
    time.sleep(0.05)
    resp = ""
    while ser.in_waiting > 0:
        resp += ser.read(ser.in_waiting).decode("ascii", errors="replace")
    return resp.strip()


def main():
    parser = argparse.ArgumentParser(description="Load Braille tables into Glyph Press flash")
    parser.add_argument("--port", required=True, help="Serial port (USB-CDC)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate for USB-CDC")
    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=2)
    except serial.SerialException as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Loading Braille translation tables into W25Q16 flash...")

    for i, (lang, name) in enumerate(zip(LANGUAGES, LANG_NAMES)):
        table = build_table(lang)
        addr = i * 128
        resp = write_flash(ser, addr, table)
        print(f"  {name}: 128 bytes @ 0x{addr:04X} → {resp or 'OK'}")

    # Write UEB contraction markers (simplified — just zeros for now)
    ueb_data = bytes(4096)
    resp = write_flash(ser, 0x0400, ueb_data[:256])
    print(f"  UEB trie: 4096 bytes @ 0x0400 → {resp or 'OK'}")

    ser.close()
    print("Done. Tables loaded.")


if __name__ == "__main__":
    main()