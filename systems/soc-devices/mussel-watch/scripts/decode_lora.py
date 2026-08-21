#!/usr/bin/env python3
"""
Mussel Watch — LoRa Packet Decoder

Decodes the 34-byte Mussel Watch LoRa packet (as received by a gateway)
and prints the contents in human-readable form. Optionally handles the
AES-128 decryption if the key is provided.

Usage:
    python3 decode_lora.py <hex_packet> [--key <aes_key_hex>]

Example:
    python3 decode_lora.py 01123A0000000068010100010A000000FFFFFFFF... --key 2B7E151628AED2A6ABF7158809CF4F3C
"""

import sys
import argparse
import struct

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None  # pycryptodome is optional; only needed for --key


ALERT_NAMES = {
    0: "Normal",
    1: "Closure event",
    2: "Sustained closure (>10min)",
    3: "Rhythm deviation",
    4: "Multi-mussel closure",
    5: "Temperature anomaly",
    6: "Low dissolved oxygen",
    7: "Low battery",
}


def decrypt_packet(pkt_bytes, key_hex):
    """Decrypt the packet payload (bytes 2–33) using AES-128 ECB."""
    if AES is None:
        print("Error: pycryptodome is required for decryption. Install with: pip install pycryptodome")
        sys.exit(1)

    key = bytes.fromhex(key_hex)
    if len(key) != 16:
        print("Error: AES key must be 16 bytes (32 hex chars)")
        sys.exit(1)

    cipher = AES.new(key, AES.MODE_ECB)
    # Decrypt two 16-byte blocks (bytes 2-17 and 18-33)
    block1 = cipher.decrypt(pkt_bytes[2:18])
    block2 = cipher.decrypt(pkt_bytes[18:34])

    return pkt_bytes[:2] + block1 + block2


def decode_packet(pkt_bytes):
    """Decode the 34-byte Mussel Watch packet into a dictionary."""
    if len(pkt_bytes) != 34:
        print(f"Error: packet must be 34 bytes, got {len(pkt_bytes)}")
        sys.exit(1)

    device_class = pkt_bytes[0]
    deployment_id = pkt_bytes[1]

    # Timestamp: bytes 2-9, big-endian uint64 (we use uint32 padded)
    timestamp = struct.unpack(">Q", pkt_bytes[2:10])[0]

    flags = pkt_bytes[10]
    alert_flag = bool(flags & 0x01)
    low_battery_flag = bool(flags & 0x02)
    cal_mode_flag = bool(flags & 0x04)
    multi_head_flag = bool(flags & 0x08)

    # Gape angles: 4 × float32 LE
    gape = []
    for i in range(4):
        raw = pkt_bytes[11 + i * 4: 11 + i * 4 + 4]
        val = struct.unpack("<f", raw)[0]
        if raw == b"\xff\xff\xff\xff":
            gape.append(None)
        else:
            gape.append(val)

    # Water temp: int8, °C × 2
    temp_x2 = struct.unpack("b", pkt_bytes[27:28])[0]
    temp_c = temp_x2 / 2.0

    # Dissolved O₂: uint16 LE, mg/L × 100
    do_x100 = struct.unpack("<H", pkt_bytes[28:30])[0]
    do_mgl = do_x100 / 100.0

    # Depth: int16 LE, cm
    depth_cm = struct.unpack("<h", pkt_bytes[30:32])[0]
    depth_m = depth_cm / 100.0

    # Battery %
    battery_pct = pkt_bytes[32]

    # Alert code
    alert_code = pkt_bytes[33]

    return {
        "device_class": device_class,
        "deployment_id": deployment_id,
        "timestamp": timestamp,
        "flags": flags,
        "alert_flag": alert_flag,
        "low_battery_flag": low_battery_flag,
        "cal_mode_flag": cal_mode_flag,
        "multi_head_flag": multi_head_flag,
        "gape": gape,
        "temp_c": temp_c,
        "do_mgl": do_mgl,
        "depth_m": depth_m,
        "battery_pct": battery_pct,
        "alert_code": alert_code,
    }


def print_decoded(d):
    """Pretty-print the decoded packet."""
    print("=" * 50)
    print("  MUSSEL WATCH — LoRa PACKET DECODE")
    print("=" * 50)
    print(f"  Device class    : 0x{d['device_class']:02X} ({'Mussel Watch' if d['device_class'] == 1 else 'Unknown'})")
    print(f"  Deployment ID   : 0x{d['deployment_id']:02X}")
    print(f"  Timestamp       : {d['timestamp']} (Unix epoch)")

    # Convert timestamp to datetime
    from datetime import datetime
    dt = datetime.fromtimestamp(d["timestamp"])
    print(f"                   ({dt.isoformat()})")

    print(f"  Flags           : 0x{d['flags']:02X}")
    print(f"    Alert active       : {'YES' if d['alert_flag'] else 'no'}")
    print(f"    Low battery        : {'YES' if d['low_battery_flag'] else 'no'}")
    print(f"    Calibration mode   : {'YES' if d['cal_mode_flag'] else 'no'}")
    print(f"    Multi-head config  : {'YES' if d['multi_head_flag'] else 'no'}")

    print(f"  Gape angles      :")
    for i, g in enumerate(d["gape"]):
        if g is None:
            print(f"    Mussel {chr(65+i)}     : (unused)")
        else:
            status = "OPEN" if g > 2.0 else ("CLOSED" if g < 2.0 else "PARTIAL")
            print(f"    Mussel {chr(65+i)}     : {g:5.2f}°  [{status}]")

    print(f"  Water temp      : {d['temp_c']:.1f} °C")
    print(f"  Dissolved O₂    : {d['do_mgl']:.2f} mg/L")
    print(f"  Depth           : {d['depth_m']:.2f} m")
    print(f"  Battery         : {d['battery_pct']}%")
    print(f"  Alert           : {d['alert_code']} ({ALERT_NAMES.get(d['alert_code'], 'Unknown')})")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Decode a Mussel Watch LoRa packet")
    parser.add_argument("packet", help="Hex-encoded 34-byte packet")
    parser.add_argument("--key", default=None,
                       help="AES-128 key in hex (32 chars) for decryption")
    args = parser.parse_args()

    pkt_hex = args.packet.replace(" ", "").replace("\n", "")
    try:
        pkt_bytes = bytes.fromhex(pkt_hex)
    except ValueError:
        print("Error: invalid hex string")
        sys.exit(1)

    if args.key:
        pkt_bytes = decrypt_packet(pkt_bytes, args.key)

    decoded = decode_packet(pkt_bytes)
    print_decoded(decoded)


if __name__ == "__main__":
    main()