#!/usr/bin/env python3
"""dump_log.py — pull a session log from Frost Point over BLE or USB-CDC.

Usage:
    python3 dump_log.py --port /dev/ttyUSB0 --out session.csv
    python3 dump_log.py --ble --addr AA:BB:CC:DD:EE:FF --out session.csv

Reads the CSV log stream emitted by the device and writes it to a file.
"""
import argparse
import serial
import sys
import time


def dump_uart(port: str, baud: int, out_path: str, duration_s: int):
    with serial.Serial(port, baud, timeout=1) as ser, open(out_path, "w") as f:
        print(f"Logging from {port} for {duration_s}s → {out_path}")
        f.write("ts_ms,dew_c,rh_pct,ah_gm3,w_gkg,pressure_pa,co2_ppm,"
                "mirror_c,tec_i,tec_v,phase,state\n")
        t0 = time.time()
        while time.time() - t0 < duration_s:
            line = ser.readline().decode("ascii", errors="replace").strip()
            if line.startswith("DEW "):
                # Parse the notify-format line into CSV
                parts = line.split()
                # DEW <dew> RH <rh> AH <ah> W <w> M <mirror> S <state> TEC <pct> P <phase>
                try:
                    dew = float(parts[1])
                    rh  = float(parts[3])
                    ah  = float(parts[5])
                    w   = float(parts[7])
                    mir = float(parts[9])
                    state = int(parts[11])
                    pct = int(parts[13])
                    phase = int(parts[15])
                    ts = int(time.time() * 1000)
                    f.write(f"{ts},{dew:.2f},{rh:.2f},{ah:.2f},{w:.2f},"
                            f"0,0,{mir:.2f},{pct/25:.2f},0,{phase},{state}\n")
                    f.flush()
                except (IndexError, ValueError):
                    pass


def dump_ble(addr: str, out_path: str, duration_s: int):
    try:
        from bleak import BleakClient
    except ImportError:
        print("Install bleak: pip install bleak", file=sys.stderr)
        sys.exit(1)

    NOTIFY_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"

    async def run():
        async with BleakClient(addr) as client:
            with open(out_path, "w") as f:
                f.write("ts_ms,dew_c,rh_pct,ah_gm3,w_gkg,pressure_pa,co2_ppm,"
                        "mirror_c,tec_i,tec_v,phase,state\n")

                def handler(sender, data: bytearray):
                    line = data.decode("ascii", errors="replace").strip()
                    if line.startswith("DEW "):
                        parts = line.split()
                        try:
                            dew = float(parts[1]); rh = float(parts[3])
                            ah = float(parts[5]); w = float(parts[7])
                            mir = float(parts[9]); state = int(parts[11])
                            pct = int(parts[13]); phase = int(parts[15])
                            ts = int(time.time() * 1000)
                            f.write(f"{ts},{dew:.2f},{rh:.2f},{ah:.2f},{w:.2f},"
                                    f"0,0,{mir:.2f},{pct/25:.2f},0,{phase},{state}\n")
                            f.flush()
                        except (IndexError, ValueError):
                            pass

                await client.start_notify(NOTIFY_UUID, handler)
                print(f"BLE notify started on {addr}, logging for {duration_s}s")
                await asyncio.sleep(duration_s)
                await client.stop_notify(NOTIFY_UUID)

    import asyncio
    asyncio.run(run())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", help="serial port (e.g. /dev/ttyUSB0)")
    p.add_argument("--ble", action="store_true", help="use BLE instead of UART")
    p.add_argument("--addr", help="BLE device address")
    p.add_argument("--out", required=True, help="output CSV path")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--duration", type=int, default=60, help="seconds to log")
    args = p.parse_args()

    if args.ble:
        if not args.addr:
            print("--addr required for BLE", file=sys.stderr)
            sys.exit(1)
        dump_ble(args.addr, args.out, args.duration)
    else:
        if not args.port:
            print("--port required for UART", file=sys.stderr)
            sys.exit(1)
        dump_uart(args.port, args.baud, args.out, args.duration)


if __name__ == "__main__":
    main()