# Spiro Flow — Assembly Guide

## Overview

The Spiro Flow is a portable electronic spirometer built around the CH32V203RBT6 RISC-V microcontroller. This guide covers component sourcing, PCB assembly, pneumotachograph construction, and firmware flashing.

## Tools Required

- Soldering iron (fine tip, 0.4mm) with temperature control
- Hot-air rework station (for QFN/DFN packages)
- Solder paste and stencil (recommended for QFN parts)
- Digital multimeter
- WCH-LinkE SWD programmer (for CH32V203 flashing)
- USB-C cable
- 3D printer (for case and pneumotach housing)
- Silicone tubing (2mm ID)

## PCB Assembly

### 1. Main PCB (4-layer, 80×40mm)

**Soldering order (lowest profile first):**

1. **Passives** — resistors, capacitors (0402/0603)
   - I2C pull-ups: 4.7kΩ ×2 on PB6/PB7
   - Battery divider: 100kΩ ×2 on PA1
   - Decoupling: 100nF on each IC VDD
   - 10µF on +3V3 rail, 10µF on VBUS, 10µF on VBAT

2. **Small ICs** (SOT-23 packages)
   - U9: TLV70033 LDO (SOT-23-5)
   - U10: DW01A battery protection (SOT-23-6)
   - U11: FS8205A dual MOSFET (SOT-23-6)
   - Q1: 2N3904 buzzer driver (SOT-23)

3. **Medium ICs** (SOIC/TSSOP)
   - U6: W25Q128 flash (SOIC-8)

4. **Large ICs** (QFN/LQFP — use hot air or stencil)
   - U1: CH32V203RBT6 (LQFP-64) — align pin 1 dot, apply flux
   - U2: ESP32-C3-MINI-1 (module, castellated pads)
   - U3: SDP810-500Pa (DFN-8) — careful alignment
   - U4: BME280 (LGA-8) — very small, use stencil
   - U7: MCP73831 (DFN-8)
   - U8: TPS63020 (SON-14)

5. **Connectors and mechanical**
   - J1: USB-C receptacle (through-hole tabs + SMD pins)
   - J2: JST-PH battery connector
   - J3: Silicone tubing connector for pressure ports
   - SW1, SW2: Tactile buttons
   - BZ1: Piezo buzzer
   - LED1: WS2812B
   - LED2: Status LED

6. **Inductor**
   - L1: 2.2µH 3A (4×4mm) for TPS63020

### 2. Pneumotachograph Assembly

The pneumotachograph is the critical mechanical component that converts airflow into a measurable pressure differential.

**Materials:**
- Stainless steel mesh screen (400 mesh / 38µm pore)
- 3D-printed housing (PLA or PETG)
- Disposable cardboard mouthpieces (30mm OD)
- Bacterial/viral filter (optional but recommended)

**Construction:**

1. **3D print the housing** using the included STL files (see `hardware/`):
   - `pneumotach_body.stl` — main barrel with screen seat
   - `pneumotach_cap.stl` — end cap with mouthpiece holder
   - `pressure_port.stl` — two pressure tap ports

2. **Install the mesh screen:**
   - Cut a 25mm disc of 400-mesh stainless screen
   - Seat it in the screen groove of the housing
   - Secure with a thin O-ring or press-fit ring

3. **Attach pressure ports:**
   - Connect two silicone tubes (2mm ID, 30mm long) to the upstream and downstream pressure taps
   - The upstream tap is before the screen; downstream is after
   - Connect the other ends to J3 on the PCB, which routes to SDP810 P1+ and P2-

4. **Calibrate the pneumotach:**
   - Use a calibrated syringe (3L calibration syringe, ~$30)
   - Inject air at various flow rates
   - Verify the SDP810 reading matches expected ΔP
   - Adjust `PNEUMO_RESISTANCE` in `main.h` if needed (default: 0.0115 Pa·s/L)

### 3. Case Assembly

1. **3D print the case** (two halves):
   - `case_top.stl` — with OLED window and button holes
   - `case_bottom.stl` — with battery compartment

2. **Assembly:**
   - Insert PCB into case bottom
   - Connect battery to J2
   - Route pneumotach tubing through case opening
   - Place OLED in case top window
   - Snap case halves together (4× M2 screws)

### 4. Firmware Flashing

**CH32V203 (main MCU):**

```bash
# Install riscv-none-embed-gcc toolchain
# https://github.com/WCH-RV/gcc-riscv-none-embed

# Build
cd firmware
make

# Flash via WCH-LinkE SWD programmer
# Connect: SWDIO → CH32V203 SWD pin, SWCLK → SWCLK, 3V3, GND
make flash
# or: wchisp flash spiro_flow.bin
```

**ESP32-C3 (BLE/WiFi bridge):**

```bash
# Install ESP-IDF v5.2
# https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32c3/get-started/

cd firmware/esp32_c3_bridge
idf.py set-target esp32c3
idf.py build

# Flash via USB-C (the USB-C connector is wired to CH32V203,
# so flash ESP32-C3 via its UART pins: GPIO4/GPIO5 accessible
# through test pads on the PCB)
idf.py -p /dev/ttyUSB0 flash
```

### 5. Testing

1. **Power on** — LED should turn blue (idle mode)
2. **Check OLED** — should display "SPIRO FLOW / PRESS MEASURE"
3. **Press MEASURE** — buzzer warbles (ready), LED turns cyan
4. **Blow into mouthpiece** — buzzer blasts, flow-volume curve draws on OLED
5. **Complete maneuver** — results display, LED turns green/yellow/red based on grade
6. **BLE pairing** — search "SpiroFlow" on phone, connect via companion app

### 6. Calibration

Before clinical use, calibrate with a 3L calibration syringe:

1. Enter calibration mode (hold MODE for 5 seconds)
2. Inject 3L of air at moderate flow (~5 L/s)
3. Device measures the volume and computes a correction factor
4. Repeat 3 times; device averages and stores in flash

The syringe volume should read 3.0L ± 150mL (±5%). Adjust `PNEUMO_RESISTANCE` if outside this range.

## Safety Notes

- The Spiro Flow is a screening device, not a diagnostic instrument
- Always use disposable mouthpieces — never share between patients
- Install a bacterial/viral filter for clinical use
- The device is not FDA-approved; for research and educational use
- Do not use on patients without proper medical oversight
- Clean the pneumotach screen monthly with 70% isopropyl alcohol