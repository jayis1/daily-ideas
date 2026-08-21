# Assembly Guide — Thermo Trace Pocket DSC

This guide walks you through assembling the Thermo Trace pocket DSC from
components to a finished, working device.

## Prerequisites

### Tools

- Soldering iron (fine tip, 0.4mm recommended)
- Solder (0.5mm 63/37 or lead-free)
- Flux pen
- Tweezers (fine, anti-magnetic)
- Magnifier or microscope (for SMD work)
- Multimeter
- Heat gun (for SMD reflow, optional)
- Kapton tape
- Thermal conductive epoxy (e.g., Arctic Silver or MG Chemicals)
- 3D-printed cell holder (STL provided in `hardware/`)

### Skills

- SMD soldering (down to 0805 / 0603)
- Basic through-hole soldering
- Mechanical assembly

## Step 1: PCB Fabrication

1. Order the PCB from JLCPCB, PCBWay, or similar:
   - 2-layer FR4, 1.6mm
   - Size: 110 × 70 mm
   - Surface finish: HASL (lead-free) or ENIG
   - Download the gerbers from `schematic/thermo_trace.kicad_pcb`
2. Inspect the PCB for shorts/opens with a multimeter continuity check.

## Step 2: SMD Components (Bottom Side)

1. Apply solder paste to the bottom-side stencil
2. Place components:
   - U1 (STM32G491RET6) — LQFP-64, align pin 1 marker
   - U5 (TP4056) — SOP-8
   - U7 (AP2112K-3.3) — SOT-23-5
   - U8 (TLV3201) — SOT-23-6
   - All resistors (0805) and capacitors (0805/0603)
   - D1, D2 (LEDs) — note orientation (cathode = line on silkscreen)
3. Reflow with hot air gun or reflow oven (peak ~245°C for Pb-free)
4. Inspect for solder bridges under magnification

## Step 3: SMD Components (Top Side)

1. Apply solder paste to top-side stencil
2. Place components:
   - U2 (ADS122U04) — TSSOP-16
   - U3 (ESP32-C3-MINI-1) — module, hand-solder pads
   - J1 (USB-C) — SMD, hand-solder or reflow
   - J2 (microSD socket) — SMD
3. Reflow or hand-solder

## Step 4: Through-Hole Components

1. Solder:
   - Q1, Q2 (IRLZ44N MOSFETs) — TO-220, bent to lay flat
   - BT1 (18650 holder) — through-hole
   - SW1 ×3 (tactile buttons) — through-hole
   - DS1 (DS18B20) — TO-92, bend leads to lay flat
2. Clean flux residue with isopropyl alcohol

## Step 5: DSC Cell Assembly

This is the most critical step — the DSC cell must be thermally isolated
from the PCB.

### 5.1 Prepare the Ceramic Spacer

1. Cut a 10 × 20mm piece of 1mm alumina (Al₂O₃) ceramic
2. Clean with isopropyl alcohol

### 5.2 Mount Heaters

1. Apply a thin layer of thermal conductive epoxy to the ceramic spacer
2. Place both Kapton thin-film heaters (H1, H2) on the ceramic, 5mm apart
3. Allow epoxy to cure (follow manufacturer instructions, typically 24h
   at room temperature or 2h at 80°C)

### 5.3 Mount RTDs

1. Apply thermal conductive epoxy to the underside of each heater
2. Place PT1000 RTD (RTD1 under H1, RTD2 under H2) with the sensing
   element centered
3. Cure the epoxy

### 5.4 Wire the Cell

1. Solder 4-wire connections to each RTD:
   - 2 wires for IDAC excitation (AIN0/AIN1 for sample, AIN2/AIN3 for ref)
   - 2 wires for voltage sensing (same pins, Kelvin connection)
2. Solder heater leads to the MOSFET drain connections
3. Use fine-gauge wire (30 AWG) and keep leads short

### 5.5 Mount Cell on PCB

1. Apply Kapton tape to the PCB under the cell area
2. Place the ceramic spacer (with heaters + RTDs) on the Kapton tape
3. The air gap between ceramic and PCB provides thermal isolation
4. Secure with a small 3D-printed bracket

### 5.6 Install Thermal Fuse

1. Solder the 250°C one-shot thermal fuse (F1) in series with the 5V
   heater rail, physically touching the ceramic spacer
2. This is the last-resort safety device — it must be in good thermal
   contact with the cell

## Step 6: OLED Display

1. Solder the SH1106 OLED module to the I2C1 pads (PB6 SCL, PB7 SDA)
2. Mount the OLED in the enclosure cutout
3. Secure with double-sided tape or screws

## Step 7: Safety Comparator Setup

1. The TLV3201 comparator monitors a dedicated thermistor on the cell
2. Set the threshold to 320°C by adjusting the reference voltage divider
3. The comparator output drives PB8 (EXTI8) and directly controls the
   heater enable line (PB9)
4. Test: heat the cell to 320°C and verify the comparator triggers
   (do this carefully with a heat gun and thermal camera)

## Step 8: Firmware Flashing

1. Connect an ST-Link V2 programmer to the SWD header:
   - SWDIO → PA13
   - SWCLK → PA14
   - GND → GND
   - 3V3 → 3V3
2. Build the firmware:
   ```bash
   cd firmware
   mkdir build && cd build
   cmake ..
   make -j$(nproc)
   ```
3. Flash:
   ```bash
   openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
     -c "program thermo_trace.elf verify reset exit"
   ```
4. The OLED should show "THERMO TRACE / POCKET DSC / READY"

## Step 9: ESP32-C3 Firmware

1. The ESP32-C3-MINI-1 runs a BLE GATT server that relays UART data
2. Flash the ESP32-C3 bridge firmware:
   ```bash
   # Via USB or via STM32 UART passthrough
   esptool.py --port /dev/ttyUSB0 write_flash 0x0 esp_bridge.bin
   ```
3. The ESP32-C3 advertises as "Thermo Trace" with a Nordic UART
   Service (NUS) compatible UUID

## Step 10: Mechanical Assembly

1. 3D-print the enclosure (or use the aluminum enclosure)
2. Mount the PCB in the enclosure
3. Mount the OLED in the enclosure cutout
4. Mount the 18650 battery in its holder
5. Mount the DSC cell assembly with the sample loading lid accessible
6. Secure all connectors and close the enclosure

## Step 11: Calibration

1. Load an indium standard (5 mg) into the sample pan
2. Run a scan from RT to 200°C at 5°C/min
3. The indium melting peak should appear at 156.6°C with ΔH = 28.71 J/g
4. Use the calibration script to compute correction coefficients:
   ```bash
   python scripts/calibrate.py --indium
   ```
5. Send the correction coefficients to the device via BLE
6. Repeat with tin (Tm = 231.9°C) for two-point calibration

## Step 12: Final Test

1. Load a known sample (e.g., paraffin wax, Tm = 58°C)
2. Run a scan and verify the melting peak appears at the correct
   temperature
3. Test BLE streaming with the companion app:
   ```bash
   python scripts/thermo_trace_app.py
   ```
4. Test the safety cutoff by heating to 320°C (with a heat gun, not
   the internal heaters!) and verifying the comparator trips

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| OLED blank | I2C wiring wrong | Check PB6/PB7 connections, OLED address 0x3C |
| No temperature reading | ADS122U04 SPI issue | Check SPI wiring, CS pin (PA10), DRDY (PA12) |
| Heaters not working | MOSFET wiring | Check Q1/Q2 gate connections (PA8/PA9), heater enable (PB9) |
| Temperature overshoots | PID tuning | Reduce kI, increase kD in `heater.c` |
| BLE not connecting | ESP32-C3 not flashed | Flash the bridge firmware, check UART (PA2/PA3) |
| Safety trip immediately | Comparator threshold | Check TLV3201 reference voltage divider |
| SD card not mounting | SPI2 wiring | Check PB2/PB3/PB4/PB5 connections |