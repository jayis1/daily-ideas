#!/usr/bin/env python3
"""
calibrate.py — QCM Halo crystal calibration utility

Performs air and water baseline calibration, writing the results
to the device's W25Q128 flash via BLE commands.

Calibration procedure:
1. Mount crystal in air (no liquid)
2. Measure f and D at all overtones → store as baseline
3. Introduce water/buffer
4. Measure f and D → verify Kanazawa-Gordon prediction
5. Send baselines to device

Usage:
    python3 calibrate.py [--device QCM-Halo]
"""

import asyncio
import struct
import sys

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install: pip install bleak")
    sys.exit(1)

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
TX_CHAR_UUID  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
RX_CHAR_UUID  = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

SYNC0, SYNC1 = 0xA5, 0x5A

def crc8(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) if (crc & 0x80) else (crc << 1)
            crc &= 0xFF
    return crc

def make_frame(cmd, payload=b''):
    frame = bytes([SYNC0, SYNC1, cmd, len(payload)]) + payload
    return frame + bytes([crc8(frame[2:])])

# Physical constants for verification
RHO_Q = 2650.0
MU_Q = 2.947e10
RHO_WATER = 1000.0
ETA_WATER = 0.001  # Pa·s at 20°C

OVERTONES = [1, 3, 5, 7, 9, 11]
F0 = 5e6

rx_buffer = bytearray()
calibration_data = {}

def notification_handler(sender, data):
    global rx_buffer
    rx_buffer.extend(data)
    # Parse results
    i = 0
    while i < len(rx_buffer) - 4:
        if rx_buffer[i] == SYNC0 and rx_buffer[i+1] == SYNC1:
            cmd = rx_buffer[i+2]
            plen = rx_buffer[i+3]
            if i + 5 + plen <= len(rx_buffer):
                payload = rx_buffer[i+4:i+4+plen]
                expected = crc8(rx_buffer[i+2:i+4+plen])
                if rx_buffer[i+4+plen] == expected:
                    if cmd == 0x01 and len(payload) >= 26:
                        ch = payload[0]
                        ov_n = payload[1]
                        df = struct.unpack_from('<f', payload, 2)[0]
                        diss = struct.unpack_from('<f', payload, 6)[0]
                        dd = struct.unpack_from('<f', payload, 10)[0]
                        calibration_data[ov_n] = {
                            'delta_f': df, 'dissipation': diss, 'delta_d': dd
                        }
                        print(f"  n={ov_n:2d}: Δf={df:+.2f} Hz, D={diss:.3e}, ΔD={dd:.3e}")
                    i += 5 + plen
                    continue
        i += 1
    rx_buffer[:] = rx_buffer[i:]

def kanazawa_predicted(f0, n, rho_l=1000, eta_l=0.001):
    """Kanazawa-Gordon predicted Δf for liquid loading."""
    fn = f0 * n
    factor = (rho_l * eta_l / (3.14159265 * RHO_Q * MU_Q)) ** 0.5
    return -(fn ** 1.5) * factor

async def calibrate():
    print("Scanning for QCM Halo...")
    devices = await BleakScanner.discover()
    target = None
    for d in devices:
        if "QCM" in (d.name or ""):
            target = d
            break

    if not target:
        print("QCM Halo not found!")
        return

    print(f"Found: {target.name}")

    async with BleakClient(target) as client:
        await client.start_notify(RX_CHAR_UUID, notification_handler)

        print("\n=== STEP 1: Air Baseline ===")
        print("Ensure crystal is mounted in AIR (no liquid).")
        print("Press Enter when ready, or Ctrl+C to abort.")
        input()

        print("Measuring air baseline at all overtones...")
        for n in OVERTONES:
            ov_idx = OVERTONES.index(n)
            await client.write_gatt_char(TX_CHAR_UUID,
                make_frame(0x81, bytes([0, ov_idx, 1])), response=True)
            await asyncio.sleep(3)  # wait for measurement

        air_data = dict(calibration_data)
        calibration_data.clear()

        print(f"\nAir baseline captured: {len(air_data)} overtones")

        print("\n=== STEP 2: Water Verification ===")
        print("Introduce water/buffer to the crystal surface.")
        print("Ensure flow cell is filled and no bubbles.")
        print("Press Enter when ready.")
        input()

        print("Measuring in water...")
        for n in OVERTONES:
            ov_idx = OVERTONES.index(n)
            await client.write_gatt_char(TX_CHAR_UUID,
                make_frame(0x81, bytes([0, ov_idx, 1])), response=True)
            await asyncio.sleep(3)

        water_data = dict(calibration_data)

        print("\n=== STEP 3: Verification ===")
        print(f"\n{'n':>4s}  {'Δf_air':>10s}  {'Δf_water':>10s}  {'Δf_Kanazawa':>12s}  {'Match':>6s}")
        print("-" * 55)
        for n in OVERTONES:
            if n in air_data and n in water_data:
                df_water = water_data[n]['delta_f'] - air_data[n]['delta_f']
                df_pred = kanazawa_predicted(F0, n)
                match = "✓" if abs(df_water - df_pred) < abs(df_pred) * 0.15 else "✗"
                print(f"{n:4d}  {air_data[n]['delta_f']:10.2f}  {water_data[n]['delta_f']:10.2f}  "
                      f"{df_pred:12.2f}  {match:>6s}")

        print("\n=== STEP 4: Send Baselines to Device ===")
        print("Sending calibration command...")
        await client.write_gatt_char(TX_CHAR_UUID,
            make_frame(0x88), response=True)  # CALIBRATE

        await asyncio.sleep(2)
        await client.stop_notify(RX_CHAR_UUID)
        print("\nCalibration complete!")

if __name__ == "__main__":
    asyncio.run(calibrate())