#!/usr/bin/env python3
"""
glyph_send.py — Glyph Press BLE Companion Script

Send text to the Glyph Press portable Braille embosser via Bluetooth
Classic SPP (HC-05) or a USB-CDC serial port.

Usage:
    python glyph_send.py --port /dev/tty.GlyphPress --text "Hello World"
    python glyph_send.py --port COM5 --file label.txt --mode G2
    python glyph_send.py --port /dev/ttyUSB0 --text "MEDS 8AM" --mode LABEL
    python glyph_send.py --port /dev/tty.GlyphPress --status
    python glyph_send.py --port /dev/tty.GlyphPress --test
    python glyph_send.py --scan

Requirements:
    pip install pyserial

On macOS, pair the HC-05 module first (PIN: 1234 or 0000),
then use the /dev/tty.GlyphPress-SPPDev port name.
On Linux, pair with bluetoothctl, then use rfcomm to bind a serial port.
On Windows, pair in Settings, then use the outgoing COM port.
"""

import argparse
import serial
import sys
import time
import os


def connect(port, baud=9600, timeout=2):
    """Open a serial connection to the Glyph Press."""
    try:
        ser = serial.Serial(port, baud, timeout=timeout)
        print(f"Connected to Glyph Press on {port}")
        return ser
    except serial.SerialException as e:
        print(f"Error opening {port}: {e}")
        sys.exit(1)


def send_command(ser, cmd):
    """Send a command line and read the response."""
    ser.write((cmd + "\n").encode("utf-8"))
    time.sleep(0.1)
    response = ""
    while ser.in_waiting > 0:
        response += ser.read(ser.in_waiting).decode("utf-8", errors="replace")
    return response.strip()


def send_text(ser, text):
    """Queue text for embossing."""
    resp = send_command(ser, f"TEXT {text}")
    print(f"  Queue: {resp}")
    return resp


def set_mode(ser, mode):
    """Set embossing mode: G1, G2, G8, LABEL, PAGE."""
    resp = send_command(ser, f"MODE {mode}")
    print(f"  Mode: {resp}")
    return resp


def set_lang(ser, lang):
    """Set language: en, fr, es, de, pt, ar, hi, zh."""
    resp = send_command(ser, f"LANG {lang}")
    print(f"  Lang: {resp}")
    return resp


def set_force(ser, force):
    """Set embossing force 0-9."""
    resp = send_command(ser, f"FORCE {force}")
    print(f"  Force: {resp}")
    return resp


def start_emboss(ser):
    """Start embossing queued text."""
    resp = send_command(ser, "START")
    print(f"  Start: {resp}")
    return resp


def get_status(ser):
    """Query device status."""
    resp = send_command(ser, "STATUS")
    print(f"  Status: {resp}")
    return resp


def run_test(ser):
    """Run self-test (emboss Braille alphabet)."""
    resp = send_command(ser, "TEST")
    print(f"  Test: {resp}")


def send_file(ser, filepath):
    """Send contents of a text file."""
    if not os.path.exists(filepath):
        print(f"  Error: file not found: {filepath}")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Strip newlines for single TEXT command (firmware handles line wrapping)
    content = content.replace("\n", " ").replace("\r", "")
    if len(content) > 4096:
        print(f"  Warning: file is {len(content)} chars, truncating to 4096")
        content = content[:4096]
    send_text(ser, content)


def scan_ports():
    """Scan for available serial ports."""
    import serial.tools.list_ports as list_ports
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    print("Available serial ports:")
    for p in ports:
        print(f"  {p.device}  {p.description}  {p.manufacturer or ''}")


def monitor_emboss(ser, total_cells=None):
    """Monitor embossing progress by polling STATUS."""
    print("Monitoring embossing progress... (Ctrl-C to stop)")
    prev_pct = -1
    try:
        while True:
            resp = send_command(ser, "STATUS")
            # Parse "OK <state> mode:<mode> cells:<done>/<total>"
            parts = resp.split()
            if "cells:" in resp:
                for part in parts:
                    if part.startswith("cells:"):
                        done, total = part.split(":")[1].split("/")
                        done, total = int(done), int(total)
                        if total > 0:
                            pct = (done * 100) // total
                            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                            if pct != prev_pct:
                                print(f"\r  {bar} {pct:3d}% ({done}/{total})", end="", flush=True)
                                prev_pct = pct
                            if done >= total and total > 0:
                                print("\n  Done!")
                                return
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n  Monitoring stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Glyph Press BLE Companion — send text to the portable Braille embosser"
    )
    parser.add_argument("--port", "-p", help="Serial port (e.g. /dev/tty.GlyphPress, COM5)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default 9600)")
    parser.add_argument("--text", "-t", help="Text string to emboss")
    parser.add_argument("--file", "-f", help="Text file to emboss")
    parser.add_argument("--mode", "-m", default="G2",
                        choices=["G1", "G2", "G8", "LABEL", "PAGE"],
                        help="Braille mode (default G2)")
    parser.add_argument("--lang", "-l", default="en",
                        choices=["en", "fr", "es", "de", "pt", "ar", "hi", "zh"],
                        help="Language (default en)")
    parser.add_argument("--force", type=int, default=5, help="Embossing force 0-9 (default 5)")
    parser.add_argument("--status", action="store_true", help="Query status only")
    parser.add_argument("--test", action="store_true", help="Run self-test (Braille alphabet)")
    parser.add_argument("--scan", action="store_true", help="Scan for available serial ports")
    parser.add_argument("--monitor", action="store_true", help="Monitor embossing progress")

    args = parser.parse_args()

    if args.scan:
        scan_ports()
        return

    if not args.port:
        print("Error: --port is required (or use --scan to list ports)")
        parser.print_help()
        sys.exit(1)

    ser = connect(args.port, args.baud)

    if args.status:
        get_status(ser)
        ser.close()
        return

    if args.test:
        run_test(ser)
        if args.monitor:
            monitor_emboss(ser)
        ser.close()
        return

    # Configure device
    set_mode(ser, args.mode)
    set_lang(ser, args.lang)
    set_force(ser, args.force)

    # Send text
    if args.file:
        print(f"Sending file: {args.file}")
        send_file(ser, args.file)
    elif args.text:
        print(f"Sending: \"{args.text}\"")
        send_text(ser, args.text)
    else:
        print("Error: provide --text or --file")
        ser.close()
        sys.exit(1)

    # Start embossing
    start_emboss(ser)

    if args.monitor:
        monitor_emboss(ser)
    else:
        print("Embossing started. Use --monitor to track progress.")

    ser.close()
    print("Disconnected.")


if __name__ == "__main__":
    main()