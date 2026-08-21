#!/usr/bin/env python3
"""
Melody Sprite — BLE MIDI Bridge
Connects to the Melody Sprite via BLE MIDI and forwards
messages to/from a computer MIDI port.

Usage:
    python ble_midi_bridge.py                  # Auto-discover device
    python ble_midi_bridge.py --name "My Sprite"  # Connect by name
    python ble_midi_bridge.py --list                # List BLE devices

Requirements:
    pip install bleak python-rtmidi
"""

import argparse
import asyncio
import sys
import struct
import time

try:
    from bleak import BleakClient, BleakScanner
    HAS_BLEAK = True
except ImportError:
    HAS_BLEAK = False

try:
    import rtmidi
    HAS_RTMIDI = True
except ImportError:
    HAS_RTMIDI = False

# BLE MIDI Service UUID
BLE_MIDI_SERVICE_UUID = "03B80E5A-EDE8-4B33-A751-23CE4A040CBE"
BLE_MIDI_CHAR_UUID = "7772E5DB-3868-4112-A1C9-F2629926A7D3"

# MIDI message types
MIDI_NOTE_OFF = 0x80
MIDI_NOTE_ON = 0x90
MIDI_POLY_PRESSURE = 0xA0
MIDI_CC = 0xB0
MIDI_PROGRAM_CHANGE = 0xC0
MIDI_CHANNEL_PRESSURE = 0xD0
MIDI_PITCH_BEND = 0xE0
MIDI_SYS_EX = 0xF0


def midi_to_str(data):
    """Convert raw MIDI data to human-readable string."""
    if len(data) < 2:
        return f"Raw: {data.hex()}"

    status = data[0]
    msg_type = status & 0xF0
    channel = status & 0x0F

    if msg_type == MIDI_NOTE_ON:
        note = data[1] if len(data) > 1 else 0
        vel = data[2] if len(data) > 2 else 0
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        note_name = f"{notes[note % 12]}{note // 12 - 1}"
        return f"Note On  Ch{channel+1} {note_name} vel={vel}"

    elif msg_type == MIDI_NOTE_OFF:
        note = data[1] if len(data) > 1 else 0
        vel = data[2] if len(data) > 2 else 0
        return f"Note Off Ch{channel+1} note={note} vel={vel}"

    elif msg_type == MIDI_CC:
        cc = data[1] if len(data) > 1 else 0
        val = data[2] if len(data) > 2 else 0
        cc_names = {
            1: 'Mod Wheel', 7: 'Volume', 10: 'Pan',
            64: 'Sustain', 74: 'Brightness', 91: 'Reverb'
        }
        name = cc_names.get(cc, f'CC{cc}')
        return f"CC Ch{channel+1} {name}={val}"

    elif msg_type == MIDI_PROGRAM_CHANGE:
        pc = data[1] if len(data) > 1 else 0
        return f"PC Ch{channel+1} program={pc}"

    elif msg_type == MIDI_PITCH_BEND:
        lsb = data[1] if len(data) > 1 else 0
        msb = data[2] if len(data) > 2 else 0
        value = (msb << 7) | lsb
        return f"Pitch Bend Ch{channel+1} value={value}"

    else:
        return f"MIDI {data.hex()}"


def parse_ble_midi_packet(data):
    """Parse a BLE MIDI packet into individual MIDI messages.

    BLE MIDI packets have a timestamp byte before each MIDI message.
    Format: [timestamp, MIDI_data, ...] with timestamps on high bits.
    """
    messages = []
    i = 0
    while i < len(data):
        # Skip timestamp bytes (high bit set)
        if data[i] & 0x80:
            i += 1
            continue

        # Parse MIDI message
        status = data[i]
        msg_type = status & 0xF0

        if msg_type in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
            # 3-byte message
            if i + 2 < len(data):
                messages.append(bytes(data[i:i+3]))
                i += 3
            else:
                break
        elif msg_type in (0xC0, 0xD0):
            # 2-byte message
            if i + 1 < len(data):
                messages.append(bytes(data[i:i+2]))
                i += 2
            else:
                break
        else:
            i += 1

    return messages


async def discover_devices():
    """Scan for BLE devices and list those with MIDI service."""
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=10.0)

    midi_devices = []
    for device in devices:
        is_melody = "Melody" in (device.name or "") or "Sprite" in (device.name or "")
        is_midi = False
        if device.metadata and 'uuids' in device.metadata:
            for uuid in device.metadata['uuids']:
                if uuid.lower() == BLE_MIDI_SERVICE_UUID.lower():
                    is_midi = True
                    break
        if is_melody or is_midi:
            midi_devices.append(device)

    if not midi_devices:
        print("No Melody Sprite or BLE MIDI devices found.")
        print("\nAll discovered devices:")
        for dev in devices:
            print(f"  {dev.address} — {dev.name or 'Unknown'}")
    else:
        print(f"\nFound {len(midi_devices)} Melody Sprite device(s):")
        for dev in midi_devices:
            print(f"  {dev.address} — {dev.name or 'Unknown'}")

    return midi_devices


async def run_bridge(device_address, midi_port_name=None):
    """Connect to Melody Sprite via BLE and bridge MIDI to/from computer."""

    print(f"Connecting to {device_address}...")

    async with BleakClient(device_address) as client:
        print(f"Connected! Device: {client.mtu_size} MTU")

        # Set up computer MIDI port
        midi_out = None
        midi_in = None

        if HAS_RTMIDI:
            midi_out = rtmidi.MidiOut()
            midi_in = rtmidi.MidiIn()

            # Find Melody Sprite MIDI port
            out_ports = midi_out.get_ports()
            for i, name in enumerate(out_ports):
                if 'Melody' in name or 'Sprite' in name:
                    midi_out.open_port(i)
                    print(f"Opened MIDI output: {name}")
                    break
            else:
                # Create virtual port
                midi_out.open_virtual_port("Melody Sprite Bridge Out")
                print("Created virtual MIDI output port")

            in_ports = midi_in.get_ports()
            for i, name in enumerate(in_ports):
                if 'Melody' in name or 'Sprite' in name:
                    midi_in.open_port(i)
                    print(f"Opened MIDI input: {name}")
                    break
            else:
                midi_in.open_virtual_port("Melody Sprite Bridge In")
                print("Created virtual MIDI input port")

            midi_in.ignore_types(False, False, False)  # Don't ignore any messages

        # BLE MIDI notification handler
        def on_midi_notify(sender, data):
            messages = parse_ble_midi_packet(data)
            for msg in messages:
                print(f"  ← BLE: {midi_to_str(msg)}")
                # Forward to computer MIDI out
                if midi_out:
                    try:
                        midi_out.send_message(list(msg))
                    except Exception as e:
                        print(f"  MIDI out error: {e}")

        # Subscribe to BLE MIDI characteristic
        await client.start_notify(BLE_MIDI_CHAR_UUID, on_midi_notify)
        print("Subscribed to BLE MIDI notifications")
        print("\nBridge active! Press Ctrl+C to disconnect.")
        print("Play the Melody Sprite — MIDI data will be forwarded.")
        print()

        # Main loop: read from computer MIDI, send to BLE
        try:
            while True:
                if midi_in:
                    msg = midi_in.get_message()
                    if msg:
                        data, delta_time = msg
                        # Forward to BLE
                        ble_data = bytes([0x80]) + bytes(data)  # Add timestamp
                        try:
                            await client.write_gatt_char(
                                BLE_MIDI_CHAR_UUID, ble_data
                            )
                            print(f"  → BLE: {midi_to_str(bytes(data))}")
                        except Exception as e:
                            print(f"  BLE write error: {e}")

                await asyncio.sleep(0.001)  # Small delay to prevent busy loop

        except KeyboardInterrupt:
            print("\nDisconnecting...")

        # Clean up
        await client.stop_notify(BLE_MIDI_CHAR_UUID)
        if midi_out:
            midi_out.close_port()
        if midi_in:
            midi_in.close_port()

    print("Bridge disconnected.")


def main():
    parser = argparse.ArgumentParser(
        description='Melody Sprite BLE MIDI Bridge')
    parser.add_argument('--name', '-n', help='BLE device name to connect to')
    parser.add_argument('--address', '-a', help='BLE device address')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List BLE devices')
    parser.add_argument('--no-midi', action='store_true',
                       help='Disable computer MIDI forwarding')

    args = parser.parse_args()

    if not HAS_BLEAK:
        print("Error: bleak not installed. Install with: pip install bleak")
        sys.exit(1)

    if args.list:
        asyncio.run(discover_devices())
        return

    # Determine device address
    if args.address:
        device_address = args.address
    elif args.name:
        # Scan for device by name
        print(f"Searching for '{args.name}'...")
        async def find_by_name():
            devices = await BleakScanner.discover(timeout=10.0)
            for dev in devices:
                if dev.name and args.name.lower() in dev.name.lower():
                    return dev.address
            return None
        device_address = asyncio.run(find_by_name())
        if not device_address:
            print(f"Device '{args.name}' not found.")
            sys.exit(1)
    else:
        # Auto-discover
        print("Auto-discovering Melody Sprite...")
        async def auto_find():
            devices = await discover_devices()
            if devices:
                return devices[0].address
            return None
        device_address = asyncio.run(auto_find())
        if not device_address:
            print("No Melody Sprite found. Use --list to scan.")
            sys.exit(1)

    print(f"Connecting to {device_address}")

    # Run bridge
    try:
        asyncio.run(run_bridge(device_address))
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == '__main__':
    main()