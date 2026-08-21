# Phase Lock — API Reference

This document describes the BLE GATT interface, the SD card file
format, the UART bridge protocol, and the firmware build process.

## BLE GATT Characteristics

The ESP32-C3 BLE bridge exposes a GATT server with service UUID
`0000ffe0-0000-1000-8000-00805f9b34fb` and the following
characteristics:

| UUID Suffix | Name       | Direction    | Format | Notes |
|-------------|------------|--------------|--------|-------|
| `ffe1`      | Demod Data | Notify       | struct | R, Θ, X, Y, noise @ 100 Hz |
| `ffe2`      | Sweep Data | Notify       | struct | per-point during sweep |
| `ffe3`      | Status     | Notify       | string | status messages |
| `ffe4`      | Command    | Write        | string | host → device |
| `ffe5`      | Config     | Write        | struct | freq, TC, slope, gain |

### Demod Data (0xFFE1) — 25 bytes

```
struct __attribute__((packed)) {
    uint8_t  tag;       // 1 = demod
    float    freq;      // reference frequency (Hz)
    float    gain;      // current PGA gain (1..1024)
    float    R;         // magnitude (V)
    float    theta;     // phase (rad)
    float    X;         // in-phase (V)
    float    Y;         // quadrature (V)
    float    noise;     // noise floor (V/√Hz)
};
```

### Sweep Data (0xFFE2) — 33 bytes

```
struct __attribute__((packed)) {
    uint8_t  tag;       // 2 = sweep
    float    f;         // frequency (Hz)
    float    a;         // amplitude (V)
    float    R, theta, X, Y, noise;
    uint32_t ts_ms;     // timestamp (ms since boot)
};
```

### Status (0xFFE3) — 32 bytes

ASCII string, null-padded to 32 bytes.

### Command (0xFFE4) — Write

ASCII commands (newline-terminated or fixed-length):

| Command | Effect |
|---------|--------|
| `RUN`   | Start acquisition (time-trace mode) |
| `SWP`   | Start a frequency sweep (default 10 Hz–100 kHz, 100 pts, log) |
| `STOP`  | Stop any running acquisition/sweep |
| `F:<hz>` | Set reference frequency (e.g., `F:1234.5`) |
| `A:<v>`  | Set reference amplitude (e.g., `A:1.0`) |
| `TC:<n>` | Set time constant index 0..9 |
| `SL:<n>` | Set slope 0=6, 1=12, 2=24, 3=48 dB/oct |
| `G:<n>`  | Set PGA gain index 0..10 (0 = auto) |
| `DUAL:1` | Enable 2f dual-harmonic mode |
| `DUAL:0` | Disable 2f mode |

### Config (0xFFE5) — Write

```
struct __attribute__((packed)) {
    float    freq;       // Hz
    float    ampl;       // V
    uint8_t  tc;         // 0..9
    uint8_t  slope;      // 0..3
    uint8_t  gain;       // 0..10 (0 = auto)
    uint8_t  dual_mode;  // 0/1
};
```

## SD Card File Format

The microSD card is FAT32. Files are named `TRC_NNNN.csv` (time-trace)
and `SWP_NNNN.csv` (sweep), where NNNN is a 4-digit run counter.

### Time-Trace File (TRC_NNNN.csv)

```
# TRC_0001.csv — Phase Lock time-trace
# f=1000.000 Hz, TC=0.010 s
ts_ms,R,theta,X,Y,noise
0,0.123456,1.5708,0.000000,0.123456,4.500e-07
10,0.123460,1.5707,0.000001,0.123459,4.480e-07
...
```

### Sweep File (SWP_NNNN.csv)

```
# SWP_0001.csv — Phase Lock sweep log
f,a,R,theta,X,Y,noise,ts_ms
10.000,1.0000,0.000012,0.0123,0.000012,0.000000,3.200e-08,0
12.597,1.0000,0.000015,0.0145,0.000015,0.000001,3.180e-08,350
...
100000.000,1.0000,0.002345,1.2345,0.000891,0.002170,4.100e-07,35000
```

## UART Bridge Protocol (STM32 ↔ ESP32-C3)

USART1 at 921600 baud, 8N1. Framed packets:

```
[0xAA][len][payload...][crc]
```

- `0xAA` — frame sync byte
- `len` — payload length (1 byte, max 64)
- `payload` — tag byte + data
- `crc` — XOR of all payload bytes

### Tags

| Tag | Direction | Content |
|-----|-----------|---------|
| 1 | STM32→ESP32 | Demod data (25 bytes) |
| 2 | STM32→ESP32 | Sweep point (33 bytes) |
| 3 | STM32→ESP32 | Status string (32 bytes) |
| 4 | ESP32→STM32 | Command (variable) |
| 5 | ESP32→STM32 | Config (10 bytes) |

## Firmware Build

### Prerequisites

- `arm-none-eabi-gcc` (GCC 12+)
- STM32Cube HAL for STM32G4 (or use the bare-metal headers included)
- CMSIS-DSP library (link `libarm_cortexM4lf_math.a`)
- OpenOCD + ST-Link v2/v3 (for flashing)

### Build

```bash
cd firmware
make           # builds phase_lock.elf
make flash     # flashes via ST-Link + OpenOCD
```

Or with CMake:

```bash
mkdir build && cd build
cmake ..
make
```

### ESP32-C3 BLE Bridge Firmware

The ESP32-C3 runs a separate firmware (not included here in full;
the bridge protocol is defined above). A minimal Arduino/ESP-IDF
sketch would:
1. Initialize BLE with the GATT service/characteristics above.
2. Initialize UART1 at 921600 baud.
3. In a loop: read framed packets from UART, parse the tag, and
   push the payload to the corresponding BLE characteristic as a
   notification.
4. On BLE write to the Command characteristic, frame the payload and
   send over UART to the STM32.

### Calibration Procedure

1. **Gain calibration**: Connect Ref Out → Signal In (BNC loopback).
   Run `scripts/gain_cal.py` over BLE. The script sweeps amplitude
   10 mV–2 V at f₀ = 1 kHz and records R at each amplitude. The
   firmware stores the gain-vs-amplitude table in NVS.
2. **Phase calibration**: Same loopback; sweep frequency 1 Hz–100 kHz
   at 1 V. The firmware records Θ vs. frequency (the group delay of
   the analog chain) and stores the phase correction table.
3. **Noise calibration**: Short Signal In to GND. The firmware records
   the noise spectral density for each gain setting (1×–1024×) and
   stores it for the noise-floor readout.