#!/usr/bin/env python3
"""
Aero Reed — MIDI Monitor
========================
Connects to the Aero Reed via BLE MIDI (macOS/Linux) or USB MIDI and
prints all incoming MIDI messages in real time. Useful for verifying
breath (CC2), lip (pitch bend + CC74), tilt (CC1), and note on/off.

Usage:
    python3 midi_monitor.py --ble          # BLE MIDI (requires bleak)
    python3 midi_monitor.py --usb           # USB MIDI (requires mido + rtmidi)
"""

import argparse
import sys
import time

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
CC_NAMES = {
    1:  "Modulation",
    2:  "Breath",
    74: "Brightness",
    76: "Vibrato Rate",
    77: "Vibrato Depth",
}


def note_name(midi_note: int) -> str:
    octave = midi_note // 12 - 1
    return f"{NOTE_NAMES[midi_note % 12]}{octave}"


def decode_midi(msg: bytes):
    """Decode a raw MIDI message (status + data bytes)."""
    if len(msg) < 2:
        return None
    status = msg[0] & 0xF0
    ch = (msg[0] & 0x0F) + 1
    if status == 0x80 and len(msg) >= 3:  # Note Off
        return f"Note Off  ch{ch}  {note_name(msg[1]):<4s}  vel={msg[2]:3d}"
    elif status == 0x90 and len(msg) >= 3:  # Note On
        return f"Note On   ch{ch}  {note_name(msg[1]):<4s}  vel={msg[2]:3d}"
    elif status == 0xB0 and len(msg) >= 3:  # CC
        cc_name = CC_NAMES.get(msg[1], f"CC{msg[1]}")
        return f"CC        ch{ch}  {cc_name:<14s}  val={msg[2]:3d}"
    elif status == 0xE0 and len(msg) >= 3:  # Pitch Bend
        bend = ((msg[2] << 7) | msg[1]) - 8192
        return f"PitchBend ch{ch}  bend={bend:+6d}"
    elif status == 0xC0 and len(msg) >= 2:  # Program Change
        return f"ProgChg   ch{ch}  prog={msg[1]}"
    return f"Unknown   0x{msg[0]:02X} {' '.join(f'{b:02X}' for b in msg[1:])}"


def monitor_ble():
    """Monitor BLE MIDI messages using bleak."""
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        print("BLE mode requires bleak:  pip install bleak")
        sys.exit(1)

    MIDI_SERVICE_UUID = "03b80e5a-ede8-4b33-a075-8ce1a1e9d5a2"
    MIDI_CHAR_UUID = "7772e5db-3868-411e-a3eb-72c3ab20a7c0"

    print("Scanning for Aero Reed BLE MIDI…")
    devices = BleakScanner.discover(timeout=10.0)
    target = None
    for d in devices:
        if "Aero" in (d.name or ""):
            target = d
            break

    if not target:
        print("Aero Reed not found. Make sure it's powered on and advertising.")
        sys.exit(1)

    print(f"Found: {target.name} ({target.address})")
    print("Connecting…\n")

    async def run():
        async with BleakClient(target.address) as client:
            print("Connected! Listening for MIDI…\n")
            print(f"{'TIME':<12s}  MESSAGE")
            print("-" * 60)

            def notification_handler(sender, data: bytearray):
                # BLE MIDI: first 1-2 bytes are timestamp headers
                # Strip leading timestamp bytes (high bit set)
                i = 0
                while i < len(data) and (data[i] & 0x80):
                    i += 1
                midi_data = bytes(data[i:])
                if midi_data:
                    decoded = decode_midi(midi_data)
                    if decoded:
                        ts = time.strftime("%H:%M:%S")
                        print(f"{ts:<12s}  {decoded}")

            await client.start_notify(MIDI_CHAR_UUID, notification_handler)
            # Keep running
            while True:
                await asyncio.sleep(1)

    import asyncio
    asyncio.run(run())


def monitor_usb():
    """Monitor USB MIDI messages using rtmidi (via mido)."""
    try:
        import rtmidi
    except ImportError:
        print("USB mode requires python-rtmidi:  pip install python-rtmidi")
        sys.exit(1)

    midiin = rtmidi.MidiIn()
    ports = midiin.get_ports()
    aero_ports = [i for i, p in enumerate(ports) if "Aero" in p]

    if not aero_ports:
        print("No Aero Reed MIDI port found. Available ports:")
        for i, p in enumerate(ports):
            print(f"  [{i}] {p}")
        sys.exit(1)

    port = aero_ports[0]
    midiin.open_port(port)
    print(f"Listening on: {ports[port]}\n")
    print(f"{'TIME':<12s}  MESSAGE")
    print("-" * 60)

    try:
        while True:
            msg = midiin.get_message()
            if msg:
                data, _delta = msg
                decoded = decode_midi(bytes(data))
                if decoded:
                    ts = time.strftime("%H:%M:%S")
                    print(f"{ts:<12s}  {decoded}")
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        midiin.close_port()


def main():
    p = argparse.ArgumentParser(description="Aero Reed MIDI Monitor")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--ble", action="store_true", help="Monitor via BLE MIDI")
    group.add_argument("--usb", action="store_true", help="Monitor via USB MIDI")
    args = p.parse_args()

    if args.ble:
        monitor_ble()
    else:
        monitor_usb()


if __name__ == "__main__":
    main()