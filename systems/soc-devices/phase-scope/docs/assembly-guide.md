# Phase Scope — Assembly Guide

## Overview

This guide walks you through assembling the Phase Scope 3-phase power quality analyzer, from bare PCB to a working instrument.

⚠️ **SAFETY WARNING**: This device connects directly to mains voltage (up to 690V L-L, 400V L-N). Incorrect assembly can result in electrocution, fire, or equipment damage. Only qualified personnel should assemble and use this device. Always verify isolation integrity before first use.

## Tools Required

- Soldering iron (temperature-controlled, 320–350°C)
- Solder (0.5mm Sn96/Ag3.5 lead-free recommended)
- Flux pen (no-clean type)
- Tweezers (ESD-safe, fine tip)
- Multimeter (for continuity and voltage testing)
- Magnifying loupe or microscope (for SMD inspection)
- Hot air rework station (for QFN/VSSOP packages)
- SWD programmer (ST-Link V2 or compatible)
- USB-C cable for charging

## Assembly Order (Bottom-Up)

### Step 1: SMD Components — Power Supply

1. **U11 (TPS63020)** — Buck-boost regulator (VSON-10). Apply flux, align, and reflow with hot air. This is the most challenging package — take your time.
2. **L1 (2.2µH inductor)** — Place near U11 output.
3. **C10, C11 (10µF, 22µF capacitors)** — Input and output filter caps for U11.
4. **U10 (MCP73831)** — Battery charger (SOT-23-5). Easy to hand-solder.
5. **C30-C32 (4.7µF caps)** — VDD bulk decoupling.
6. **J1 (USB-C connector)** — Align carefully, flux, and reflow.

**Test**: Connect USB-C power. Verify 3.3V at TPS63020 output (3.3V ± 50mV). Verify battery charging current (~500mA into discharged cell).

### Step 2: SMD Components — MCU and Digital

1. **U1 (STM32G491RET6)** — Main MCU (LQFP-64). Apply solder paste with stencil, place, and reflow.
2. **C20-C29 (100nF decoupling caps)** — Place near each VDD pin.
3. **C33-C34 (1µF VDDA caps)** — Place near analog supply pins.
4. **U7 (REF3030)** — Voltage reference (SOT-23). Place near ADC inputs.
5. **Y1 (8 MHz crystal)** — HSE oscillator. Place close to OSC_IN/OSC_OUT pins.
6. **C38-C39 (12pF load caps)** — For crystal.

**Test**: Power on. Measure 3.3V at all VDD pins. Check that MCU doesn't draw excessive current (<50mA expected).

### Step 3: SMD Components — Analog Front-End

1. **U2, U3, U4 (AMC1301)** — Isolation amplifiers (SOIC-8). These straddle the isolation boundary — ensure correct placement on the isolated side of the board.
2. **R1-R3 (470kΩ 1W resistors)** — Voltage divider upper legs. These dissipate heat — ensure good solder joints.
3. **R4-R6 (1kΩ 0.1% resistors)** — Voltage divider lower legs.
4. **C1-C3 (10nF filter caps)** — Input filter capacitors.
5. **D1-D3 (SMBJ1000A TVS)** — Input protection. Observe polarity!
6. **U5, U6 (OPA2376)** — Current signal conditioning (VSSOP-8). Use hot air.
7. **R10-R15 (CT burden resistors)** — 100Ω and 1Ω, 0.1% tolerance.

⚠️ **CRITICAL**: The isolation gap between the primary (mains) side and secondary (MCU) side of each AMC1301 must have at least 8mm creepage/clearance. Verify this before proceeding.

**Test**: With no mains connected, apply a known DC voltage (e.g., 5V from bench supply) to each voltage input through a current-limiting resistor (10kΩ). Verify the output of each AMC1301 on the MCU side with a multimeter.

### Step 4: SMD Components — BLE and Display

1. **U9 (nRF52810)** — BLE module (QFN-32). Requires hot air or reflow oven.
2. **Antenna matching network** — Place per Nordic reference design (balun + DC block).
3. **U8 (SH1106 OLED)** — Display module. Solder the flex cable or module headers.
4. **J3 (MicroSD slot)** — Hirose DM3AT push-push socket. Careful with the thin pins.

### Step 5: Through-Hole Components

1. **F1, F2, F3 (500mA fuses)** — Insert into fuse holders.
2. **K1, K2, K3 (OUAZ-SL relays)** — Range selection relays. Ensure correct orientation.
3. **J4 (CT input header)** — 2x3 pin header.
4. **J5 (Voltage input terminals)** — 5mm screw terminal block.
5. **J6 (SWD debug header)** — 1x4 pin header.
6. **J7 (Battery connector)** — JST-PH 2-pin.
7. **SW1, SW2, SW3 (Tactile buttons)** — Mode, Select, Hold.
8. **D5-D8 (LEDs)** — Green (L1), Yellow (L2), Red (L3), Blue (BLE).

### Step 6: Connectors and Hardware

1. **Battery (BT1)** — Connect Li-Po cell to J7.
2. **OLED display** — Connect to mainboard via FPC cable or headers.
3. **Enclosure** — Insert assembled PCB into ABS case, secure with 4× M2 screws.

## Programming

### Initial Flash

1. Connect ST-Link to SWD header (J6): SWDIO, SWCLK, GND, 3V3
2. Flash the firmware:
   ```bash
   openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
     -c "program phase-scope.bin verify reset exit 0x08000000"
   ```

### BLE Module Programming (nRF52810)

1. The nRF52810 comes pre-programmed with Nordic UART Service (NUS) firmware
2. If reprogramming is needed, use SWD on the nRF test pads

## Calibration

### Voltage Calibration

1. Apply a known AC voltage (e.g., 230V from a calibrated variac)
2. Connect Phase Scope voltage inputs
3. Send BLE command `0x40` (calibration mode)
4. Device will compute gain/offset and store to flash

### Current Calibration

1. Apply a known AC current through CT clamp (e.g., 10A from a load bank)
2. Same calibration procedure

### Phase Calibration

1. Apply a resistive load (PF ≈ 1.0)
2. Phase Scope adjusts internal timing to achieve PF > 0.999

## Safety Verification

Before first use with mains voltage, verify:

1. ✅ **Isolation resistance**: >10MΩ between primary and secondary sides (500V DC megger test)
2. ✅ **No continuity** between mains input terminals and any digital-side component
3. ✅ **All fuses** installed and correct rating (500mA)
4. ✅ **TVS diodes** correctly oriented
5. ✅ **Enclosure** fully assembled with no exposed conductors
6. ✅ **Creepage/clearance**: Minimum 8mm between isolated and non-isolated circuits

## First Power-Up

1. Charge the battery fully via USB-C (green LED on charger IC)
2. Disconnect USB-C
3. Press and hold the Mode button
4. Phase Scope should show the splash screen on OLED
5. Verify the BLE advertising name "PhaseScope-XXXX" appears in nRF Connect
6. Connect voltage probes and CT clamps to a known source
7. Verify readings match expected values

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No display | OLED wiring or power | Check 3.3V, SPI connections |
| Wrong voltage readings | Calibration needed | Run calibration procedure |
| BLE not visible | nRF52810 not programmed | Flash NUS firmware via SWD |
| Overheating | Short circuit on isolated side | Check for solder bridges |
| Battery drains fast | TPS63020 misconfigured | Verify EN pin, check output voltage |
| SD card not recognized | SPI wiring or card format | Format as FAT32, check CS/SCK/MOSI |

## Maintenance

- Replace fuses if blown (500mA, 5×20mm, 250V rated)
- Calibrate annually against a reference standard
- Clean OLED with soft cloth (no solvents)
- Store in dry environment when not in use
- Battery life: ~500 charge cycles, replace when capacity drops below 80%