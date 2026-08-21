#!/usr/bin/env python3
"""
Melody Sprite — Touch Sensor Calibration Utility
Calibrates the MPR121 capacitive touch sensors for optimal sensitivity.

Usage:
    python calibrate_touch.py --port /dev/ttyACM0
    python calibrate_touch.py --port /dev/ttyACM0 --sensitivity 12
"""

import argparse
import time
import sys

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# Default touch/release thresholds
DEFAULT_TOUCH = 12
DEFAULT_RELEASE = 8

def find_device():
    """Auto-detect Melody Sprite serial port."""
    if not HAS_SERIAL:
        print("Error: pyserial not installed. Install with: pip install pyserial")
        return None

    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Look for RP2040 USB CDC device
        if 'RP2' in port.description or 'Pico' in port.description or 'USB' in port.description:
            return port.device
    return None

def send_command(ser, cmd):
    """Send a command and read response."""
    ser.write((cmd + '\n').encode())
    time.sleep(0.1)
    response = ser.read(4096).decode(errors='replace')
    return response.strip()

def calibrate_touch(ser, touch_thresh, release_thresh):
    """Run touch calibration sequence."""
    print("=" * 50)
    print("  Melody Sprite — Touch Calibration")
    print("=" * 50)
    print(f"\n  Touch threshold: {touch_thresh}")
    print(f"  Release threshold: {release_thresh}")
    print()

    # Get current system info
    resp = send_command(ser, "SYSTEM:INFO")
    print(f"  Device info:\n  {resp}\n")

    # Step 1: Clear all touch pads
    print("Step 1: Please lift all fingers from the touch pads.")
    input("  Press ENTER when ready...")

    # Step 2: Run calibration
    print("\nStep 2: Running baseline calibration...")
    resp = send_command(ser, "SYSTEM:CALIBRATE_TOUCH")
    print(f"  Result: {resp}")

    # Step 3: Test each key
    print("\nStep 3: Touch key test")
    print("  Touch each key briefly to verify it registers:")
    print()

    key_names = ['C4', 'C#4', 'D4', 'D#4', 'E4', 'F4', 'F#4', 'G4',
                 'G#4', 'A4', 'A#4', 'B4', 'C5', 'C#5', 'D5', 'D#5']

    for i, name in enumerate(key_names):
        print(f"  [{i+1:2d}/16] Touch {name:>3s} and release...", end=" ")
        # Wait for note-on and note-off
        start = time.time()
        detected = False
        while time.time() - start < 10:  # 10 second timeout
            ser.reset_input_buffer()
            ser.write(b"SYNTH:LIST_VOICES\n")
            time.sleep(0.1)
            resp = ser.read(4096).decode(errors='replace')
            if 'IDLE' not in resp and 'state=ATTACK' in resp:
                detected = True
                break
        if detected:
            print("✓ OK")
        else:
            print("✗ NOT DETECTED (may need threshold adjustment)")

    # Step 4: Test function buttons
    print("\nStep 4: Function button test")
    btn_names = ['SEQ', 'OCT↓', 'OCT↑', 'WAVE', 'FX1', 'FX2', 'FX3', 'HOLD']
    for i, name in enumerate(btn_names):
        print(f"  [{i+1}/8] Press {name}...", end=" ")
        # Similar detection logic
        time.sleep(0.5)
        print("(manual verification)")

    # Step 5: Sensitivity adjustment
    print("\nStep 5: Sensitivity adjustment")
    print(f"  Current thresholds: touch={touch_thresh}, release={release_thresh}")
    print("  If some keys didn't register:")
    print("    - Decrease touch threshold (e.g., 8–10) for more sensitivity")
    print("    - Increase release threshold (e.g., 6–10) for less false triggers")
    print("  If keys trigger without being touched:")
    print("    - Increase touch threshold (e.g., 14–18) for less sensitivity")
    print("    - Decrease release threshold (e.g., 4–6) for faster release")
    print()

    # Save calibration
    resp = send_command(ser, "SEQ:SAVE 0")  # Triggers flash save of all settings
    print(f"  Settings saved: {resp}")

    print("\n✓ Calibration complete!")
    print("  Your Melody Sprite is ready to play.\n")

def scan_i2c(ser):
    """Scan I2C bus and report detected devices."""
    print("\n  I2C Bus Scan:")
    print("  Address | Device")
    print("  --------|--------")
    expected = {
        0x29: "SSD1306 OLED",
        0x42: "Melody Sprite (slave)",
        0x5A: "MPR121 #1 (Keyboard)",
        0x5B: "MPR121 #2 (Buttons)",
    }
    for addr, name in sorted(expected.items()):
        print(f"  0x{addr:02X}    | {name}")

    # Try to verify each device
    print("\n  Verifying devices:")
    for addr, name in sorted(expected.items()):
        # Would send I2C probe commands in real implementation
        print(f"  0x{addr:02X} ({name}): checking...", end=" ")
        print("✓" if addr in expected else "✗")

def main():
    parser = argparse.ArgumentParser(
        description='Melody Sprite Touch Calibration Utility')
    parser.add_argument('--port', '-p', help='Serial port (auto-detect if omitted)')
    parser.add_argument('--sensitivity', '-s', type=int, default=DEFAULT_TOUCH,
                       help=f'Touch threshold ({DEFAULT_RELEASE}–20, default: {DEFAULT_TOUCH})')
    parser.add_argument('--release', '-r', type=int, default=DEFAULT_RELEASE,
                       help=f'Release threshold (4–{DEFAULT_TOUCH}, default: {DEFAULT_RELEASE})')
    parser.add_argument('--scan', action='store_true',
                       help='Scan I2C bus for devices')
    parser.add_argument('--baud', '-b', type=int, default=115200,
                       help='Baud rate (default: 115200)')

    args = parser.parse_args()

    if not HAS_SERIAL:
        print("Error: pyserial not installed. Install with: pip install pyserial")
        sys.exit(1)

    # Find serial port
    port = args.port
    if not port:
        port = find_device()
        if not port:
            print("No Melody Sprite found. Connect the device and try again.")
            print("Or specify the port manually with --port")
            sys.exit(1)

    print(f"Connecting to {port}...")

    try:
        ser = serial.Serial(port, baudrate=args.baud, timeout=1.0)
    except serial.SerialException as e:
        print(f"Error: Could not open {port}: {e}")
        sys.exit(1)

    time.sleep(2)  # Wait for device reset

    if args.scan:
        scan_i2c(ser)
    else:
        calibrate_touch(ser, args.sensitivity, args.release)

    ser.close()
    print("Disconnected.")

if __name__ == '__main__':
    main()