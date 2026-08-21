#!/usr/bin/env python3
"""
Tremor Tile — Configuration Deployment Tool
Configures device parameters over USB-C or BLE.

Usage:
    python3 deploy_config.py --port /dev/ttyACM0 --config production.json

Requires:
    pip install pyserial
"""

import argparse
import json
import struct
import sys
import time

try:
    import serial
except ImportError:
    print("Error: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

# Command codes
CMD_SET_SAMPLE_RATE = 0x10
CMD_SET_FFT_SIZE = 0x11
CMD_SET_THRESHOLD = 0x12
CMD_SET_LORA_FREQ = 0x13
CMD_SET_LORA_SF = 0x14
CMD_SET_HEARTBEAT = 0x15
CMD_RESET_BASELINE = 0x20
CMD_START_LEARNING = 0x21
CMD_GET_STATUS = 0x30
CMD_GET_BASELINE = 0x31
CMD_REBOOT = 0xFF


def send_command(ser, cmd, data=b""):
    """Send a command and read response."""
    packet = bytes([0xAA, 0x55, cmd, len(data)]) + data
    ser.write(packet)
    ser.flush()
    time.sleep(0.2)

    header = ser.read(4)
    if len(header) < 4:
        return None

    resp_cmd = header[2]
    resp_len = header[3]
    resp_data = ser.read(resp_len) if resp_len > 0 else b""
    return {"cmd": resp_cmd, "data": resp_data}


def load_config(path):
    """Load configuration from JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def deploy_config(ser, config):
    """Deploy configuration to the device."""
    print("Deploying configuration to Tremor Tile...")

    # Sample rate
    if "sample_rate_hz" in config:
        rate_code = {100: 0, 200: 1, 400: 2}.get(config["sample_rate_hz"], 2)
        print(f"  Setting sample rate: {config['sample_rate_hz']} Hz (code {rate_code})")
        send_command(ser, CMD_SET_SAMPLE_RATE, bytes([rate_code]))

    # FFT size
    if "fft_size" in config:
        fft_code = {256: 0, 512: 1, 1024: 2}.get(config["fft_size"], 2)
        print(f"  Setting FFT size: {config['fft_size']} points (code {fft_code})")
        send_command(ser, CMD_SET_FFT_SIZE, bytes([fft_code]))

    # Anomaly threshold
    if "anomaly_threshold_sigma" in config:
        sigma = struct.pack('<f', config["anomaly_threshold_sigma"])
        print(f"  Setting anomaly threshold: {config['anomaly_threshold_sigma']}σ")
        send_command(ser, CMD_SET_THRESHOLD, sigma)

    # LoRa frequency
    if "lora_freq_mhz" in config:
        freq = struct.pack('<f', config["lora_freq_mhz"])
        print(f"  Setting LoRa frequency: {config['lora_freq_mhz']} MHz")
        send_command(ser, CMD_SET_LORA_FREQ, freq)

    # LoRa spreading factor
    if "lora_sf" in config:
        print(f"  Setting LoRa SF: {config['lora_sf']}")
        send_command(ser, CMD_SET_LORA_SF, bytes([config["lora_sf"]]))

    # Heartbeat interval
    if "heartbeat_interval_s" in config:
        interval = struct.pack('<I', config["heartbeat_interval_s"])
        print(f"  Setting heartbeat interval: {config['heartbeat_interval_s']}s")
        send_command(ser, CMD_SET_HEARTBEAT, interval)

    print("Configuration deployed successfully!")


def main():
    parser = argparse.ArgumentParser(description="Tremor Tile Configuration Deployment")
    parser.add_argument("--port", default="/dev/ttyACM0",
                       help="Serial port (default: /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200,
                       help="Baud rate (default: 115200)")
    parser.add_argument("--config", default=None,
                       help="JSON configuration file")
    parser.add_argument("--get-status", action="store_true",
                       help="Get device status")
    parser.add_argument("--reset-baseline", action="store_true",
                       help="Reset baseline and restart learning")
    parser.add_argument("--reboot", action="store_true",
                       help="Reboot device")
    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=2.0)
        print(f"Connected to {args.port}")
        time.sleep(1)

        if args.config:
            config = load_config(args.config)
            deploy_config(ser, config)

        if args.get_status:
            resp = send_command(ser, CMD_GET_STATUS)
            if resp:
                print(f"Status: {resp['data'].hex()}")

        if args.reset_baseline:
            print("Resetting baseline...")
            send_command(ser, CMD_RESET_BASELINE)

        if args.reboot:
            print("Rebooting device...")
            send_command(ser, CMD_REBOOT)

        ser.close()
    except serial.SerialException as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()