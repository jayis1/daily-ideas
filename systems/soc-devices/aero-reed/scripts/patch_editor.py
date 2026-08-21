#!/usr/bin/env python3
"""
Aero Reed — Patch Editor
=========================
Reads and edits the 8 patches stored on the Aero Reed via USB serial
(or BLE with an optional adapter).  Patches are 32 bytes; this script
sends/receives sysex messages to get/set individual patches.

Usage:
    python3 patch_editor.py --port /dev/ttyACM0 list
    python3 patch_editor.py --port /dev/ttyACM0 get 0
    python3 patch_editor.py --port /dev/ttyACM0 set 0 --name "My Patch" --wt 2 --transpose -3
    python3 patch_editor.py --port /dev/ttyACM0 save

Sysex protocol:
    GET  patch N: F0 7D 01 <patch_idx> F7           → reply: F0 7D 02 <idx> <32 bytes> F7
    SET  patch N: F0 7D 03 <idx> <32 bytes> F7
    SAVE:        F0 7D 04 F7
    LIST:        F0 7D 05 F7                        → 8× replies (type 02)
"""

import argparse
import struct
import sys
import time

try:
    import serial
except ImportError:
    print("This tool requires pyserial:  pip install pyserial")
    sys.exit(1)

# Manufacturer ID for Aero Reed sysex (7D = educational/experimental)
MFR_ID = 0x7D
SYSEX_START = 0xF0
SYSEX_END = 0xF7

# Patch field layout (32 bytes) — matches firmware/patch.c
PATCH_FIELDS = [
    ("wt_index",          "B",  0,   "Wavetable (0-7)"),
    ("transpose",         "b",  1,   "Transpose (semitones, -24..+24)"),
    ("breath_curve_exp",  "B",  2,   "Breath curve exponent x4 (1-8)"),
    ("breath_cc_exp",     "B",  3,   "Breath CC curve exponent x4"),
    ("bore_q_x10",        "B",  4,   "Bore resonator Q x10 (1-20)"),
    ("noise_mix",         "B",  5,   "Breath noise mix (0-127)"),
    ("bend_range_semi",   "B",  6,   "Lip bend range (semitones)"),
    ("growl_depth",       "B",  7,   "Growl depth (0-127)"),
    ("tilt_mod",          "B",  8,   "Tilt modulation depth (0-127)"),
    ("vibrato_rate_x2",   "B",  9,   "Vibrato rate Hz x2"),
    ("vibrato_depth",    "B",  10,  "Vibrato depth (cents)"),
    ("attack",           "B",  11,  "Attack (0-127)"),
    ("decay",            "B",  12,  "Decay (0-127)"),
    ("sustain",           "B",  13,  "Sustain (0-127)"),
    ("release",           "B",  14,  "Release (0-127)"),
    ("octave_base",       "b",  15,  "Octave base (-3..+3)"),
    # Bytes 16-31 = name (16 ASCII chars)
]

PATCH_SIZE = 32
NAME_OFFSET = 16
NAME_LEN = 16

WAVETABLES = ["Sine", "Triangle", "Saw", "Square",
              "Formant A", "Formant B", "Bright Pulse", "Breath Noise"]


def parse_patch(data: bytes) -> dict:
    """Parse 32 raw bytes into a patch dict."""
    if len(data) != PATCH_SIZE:
        raise ValueError(f"Patch data must be {PATCH_SIZE} bytes, got {len(data)}")
    patch = {}
    for name, fmt, offset, _desc in PATCH_FIELDS:
        patch[name] = struct.unpack_from(fmt, data, offset)[0]
    raw_name = data[NAME_OFFSET:NAME_OFFSET + NAME_LEN]
    patch["name"] = raw_name.split(b'\x00')[0].decode('ascii', errors='replace').strip()
    return patch


def serialize_patch(patch: dict) -> bytes:
    """Serialize a patch dict into 32 bytes."""
    data = bytearray(PATCH_SIZE)
    for name, fmt, offset, _desc in PATCH_FIELDS:
        if name in patch:
            struct.pack_into(fmt, data, offset, patch[name])
    name_bytes = patch.get("name", "").encode('ascii')[:NAME_LEN]
    data[NAME_OFFSET:NAME_OFFSET + len(name_bytes)] = name_bytes
    return bytes(data)


def patch_summary(idx: int, patch: dict) -> str:
    wt = WAVETABLES[patch["wt_index"] % len(WAVETABLES)]
    return (f"  [{idx}] {patch['name']:<16s}  wt={wt:<12s}  "
            f"transp={patch['transpose']:+d}  oct={patch['octave_base']:+d}  "
            f"atk={patch['attack']:3d} rel={patch['release']:3d}  "
            f"bend={patch['bend_range_semi']}st")


def send_sysex(ser, msg: list[int]):
    """Send a sysex message (list of bytes) over serial."""
    ser.write(bytes(msg))
    ser.flush()


def read_sysex(ser, timeout=2.0) -> list[int] | None:
    """Read a single sysex message (F0 ... F7)."""
    buf = []
    started = False
    end_time = time.time() + timeout
    while time.time() < end_time:
        if ser.in_waiting > 0:
            b = ser.read(1)
            if not b:
                continue
            val = b[0]
            if val == SYSEX_START:
                buf = [val]
                started = True
            elif started:
                buf.append(val)
                if val == SYSEX_END:
                    return buf
    return None


def cmd_list(ser):
    send_sysex(ser, [SYSEX_START, MFR_ID, 0x05, SYSEX_END])
    for i in range(8):
        msg = read_sysex(ser, timeout=3.0)
        if msg and len(msg) >= 5 and msg[2] == 0x02:
            idx = msg[3]
            data = bytes(msg[4:4 + PATCH_SIZE])
            patch = parse_patch(data)
            print(patch_summary(idx, patch))
        else:
            print(f"  [{i}] <no response>")


def cmd_get(ser, idx):
    send_sysex(ser, [SYSEX_START, MFR_ID, 0x01, idx, SYSEX_END])
    msg = read_sysex(ser, timeout=3.0)
    if msg and len(msg) >= 5 and msg[2] == 0x02:
        data = bytes(msg[4:4 + PATCH_SIZE])
        patch = parse_patch(data)
        print(f"\nPatch {idx}: {patch['name']}\n")
        for name, fmt, offset, desc in PATCH_FIELDS:
            print(f"  {name:<20s} = {patch[name]:<6d}  # {desc}")
        print(f"  {'name':<20s} = '{patch['name']}'")
    else:
        print(f"Error: no response for patch {idx}")
        sys.exit(1)


def cmd_set(ser, idx, args):
    # First get current patch, then modify
    send_sysex(ser, [SYSEX_START, MFR_ID, 0x01, idx, SYSEX_END])
    msg = read_sysex(ser, timeout=3.0)
    if not msg or len(msg) < 5:
        print(f"Error: could not read patch {idx}")
        sys.exit(1)
    data = bytes(msg[4:4 + PATCH_SIZE])
    patch = parse_patch(data)

    # Apply overrides from args
    if args.name:     patch["name"] = args.name[:NAME_LEN]
    if args.wt is not None:       patch["wt_index"] = args.wt
    if args.transpose is not None: patch["transpose"] = args.transpose
    if args.octave is not None:   patch["octave_base"] = args.octave
    if args.attack is not None:   patch["attack"] = args.attack
    if args.decay is not None:    patch["decay"] = args.decay
    if args.sustain is not None:  patch["sustain"] = args.sustain
    if args.release is not None:  patch["release"] = args.release
    if args.bend is not None:     patch["bend_range_semi"] = args.bend
    if args.noise is not None:    patch["noise_mix"] = args.noise
    if args.breath_curve is not None: patch["breath_curve_exp"] = args.breath_curve

    raw = serialize_patch(patch)
    msg = [SYSEX_START, MFR_ID, 0x03, idx] + list(raw) + [SYSEX_END]
    send_sysex(ser, msg)
    print(f"Patch {idx} updated: {patch['name']}")
    print(patch_summary(idx, patch))


def cmd_save(ser):
    send_sysex(ser, [SYSEX_START, MFR_ID, 0x04, SYSEX_END])
    print("Patches saved to NVS (flash).")


def main():
    p = argparse.ArgumentParser(description="Aero Reed Patch Editor")
    p.add_argument("--port", default="/dev/ttyACM0", help="Serial port")
    p.add_argument("--baud", type=int, default=115200, help="Baud rate")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all 8 patches")
    sub.add_parser("save", help="Save patches to flash (NVS)")

    g = sub.add_parser("get", help="Show a patch in detail")
    g.add_argument("index", type=int, help="Patch index 0-7")

    s = sub.add_parser("set", help="Modify a patch field")
    s.add_argument("index", type=int)
    s.add_argument("--name", help="Patch name (max 16 chars)")
    s.add_argument("--wt", type=int, choices=range(8), help="Wavetable index")
    s.add_argument("--transpose", type=int, help="Transpose semitones")
    s.add_argument("--octave", type=int, help="Octave base")
    s.add_argument("--attack", type=int, help="Attack (0-127)")
    s.add_argument("--decay", type=int, help="Decay (0-127)")
    s.add_argument("--sustain", type=int, help="Sustain (0-127)")
    s.add_argument("--release", type=int, help="Release (0-127)")
    s.add_argument("--bend", type=int, help="Bend range (semitones)")
    s.add_argument("--noise", type=int, help="Noise mix (0-127)")
    s.add_argument("--breath-curve", type=int, help="Breath curve exponent x4")

    args = p.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=1.0)
    time.sleep(0.5)  # wait for device to settle

    if args.command == "list":
        cmd_list(ser)
    elif args.command == "get":
        cmd_get(ser, args.index)
    elif args.command == "set":
        cmd_set(ser, args.index, args)
    elif args.command == "save":
        cmd_save(ser)

    ser.close()


if __name__ == "__main__":
    main()