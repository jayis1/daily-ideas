# Ping Caliper — Assembly Guide

This guide walks through the assembly, alignment, and first-power-up of a Ping Caliper. It assumes familiarity with surface-mount soldering and basic NDT practice.

---

## 1. PCB Fabrication

Order the 4-layer PCB (Gerbers in `schematic/gerbers/`) with:

- **4 layers, 2 oz copper on outer layers** (for the HV boost current paths)
- **ENIG finish** (flat pads for the QFN packages)
- **0.2 mm minimum trace / 0.2 mm minimum space**
- **Solder mask over the HV area** (the −200 V rail must be masked and kept ≥0.5 mm from any other net)
- **1.6 mm board thickness** for mechanical rigidity

Recommended fabricators: JLCPCB, PCBWay, Elecrow (all support 2 oz outer layers + ENIG).

---

## 2. Bill of Materials

The complete BOM is in `hardware/BOM.csv`. Key components:

| Ref | Part | Notes |
|-----|------|-------|
| U1 | STM32G474RET6 | LQFP-64, the MCU. Get genuine ST parts. |
| U2 | ESP32-C3-MINI-1 | Pre-certified Wi-Fi/BLE module |
| U3 | AD8331 | The TGC VGA. SOIC-16. The heart of the receiver. |
| U4 | LMG1210 | GaN half-bridge driver, WQFN-12 |
| U5 | LM5022 | HV boost controller, SOIC-8 |
| U6 | MD0100 | HV transmit/receive switch |
| Q1 | SCT2H12NZ | 650 V GaN HEMT (or IRF830 for ≤150 V operation) |
| U9 | TPS63020 | Buck-boost for the 3.3 V rail |

---

## 3. Soldering Order

### 3.1. Power supply first

1. Solder the **TPS63020** (U9) and its inductor L2, the input/output caps (C10, C11).
2. Solder the **TP4056** (U8) and USB-C connector (J2).
3. Apply power via USB-C and verify:
   - 5 V on the VBUS net (multimeter)
   - 3.3 V on the TPS63020 output
   - The TP4056 charges an 18650 (CHRG LED on while charging)

### 3.2. Digital core

1. Solder the **STM32G474RET6** (U1). Use a hot-air station for QFN-style packages; for the LQFP, use flux + solder paste + hot plate.
2. Solder the 8 MHz crystal (Y1), 32.768 kHz (Y2), and their load caps (C5-C8).
3. Solder the decoupling caps (C1 — one per VDD/VDDA pin).
4. **Do not power yet.** Verify shorts between VDD and GND with a multimeter (should be open).

### 3.3. Comms module

1. Solder the **ESP32-C3-MINI-1** (U2) module.
2. Solder the MAX17048 (U7) fuel gauge and its I²C pull-ups (R2).

### 3.4. Analog front-end (the critical section)

> ⚠️ The analog section is noise-sensitive. Keep the signal path short, use a solid ground plane under the AD8331, and keep the HV pulser traces away from the receiver input.

1. Solder the **AD8331** (U3). Place its 4.7 µF VCC bypass (C9) as close as possible to the VCC pin.
2. Solder the **MD0100** T/R switch (U6).
3. Solder the BAT54S limiter (D1) and the envelope detector diode (D3) + its RC (C14).
4. Solder the **LMG1210** (U4) driver, **SCT2H12NZ** (Q1) GaN FET, and the **LM5022** (U5) boost controller + inductor (L1).
5. Solder the HV reservoir cap (C3, 47 nF / 250 V) — keep its leads short.
6. Solder the probe connector (J1, LEMO/BNC).

### 3.5. Peripherals

1. Solder the SSD1306 OLED (U10), MicroSD slot (J3), rotary encoder (ENC1), buttons (SW1-SW3), LEDs (LED1-LED4), buzzer (SPK1).
2. Solder the SWD debug header (J4).

### 3.6. Battery holder

1. Solder the 18650 battery holder (BAT2) on the back side of the board.
2. Insert a protected 18650 cell.

---

## 4. Bring-up & Alignment

### 4.1. Flash the firmware

1. Connect a USB-UART/ST-Link to the SWD header (J4): SWDIO, SWCLK, 3V3, GND.
2. Build the STM32 firmware:
   ```sh
   cd firmware
   mkdir build && cd build
   cmake -DCMAKE_TOOLCHAIN_FILE=../toolchain-arm-none-eabi.cmake ..
   make -j4
   ```
3. Flash with OpenOCD:
   ```sh
   openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
           -c "program ping-caliper.bin reset exit 0x08000000"
   ```

### 4.2. Flash the ESP32-C3 firmware

1. Connect USB-C (the ESP32-C3's USB port for flashing, if available; otherwise use UART).
2. Build & flash with ESP-IDF:
   ```sh
   cd firmware/esp32c3
   idf.py set-target esp32c3
   idf.py build
   idf.py -p /dev/ttyACM0 flash monitor
   ```

### 4.3. HV alignment (⚠️ high voltage)

> The HV boost generates up to −200 V. This is not lethal but can cause a nasty shock and destroy components if mis-wired. **Do this with the battery disconnected and the probe unplugged.**

1. With an oscilloscope on the HV rail (1:100 probe), set the HV DAC to 50 V via the debug menu.
2. Verify the boost produces a clean −50 V, ripple < 100 mV.
3. Sweep up to −200 V and verify linearity.
4. Check the **HV inhibit** interlock (PC13) — the HV must turn off when the probe is uncoupled.

### 4.4. Receiver alignment

1. With a function generator injecting a 5 MHz, 100 mVpp sine into the probe connector (via a coupling cap), verify the AD8331 output on the scope. Sweep the VGA gain (DAC1) 0→1 V and verify 0→55 dB gain.
2. Verify the TGC ramp: trigger a shot and observe the DAC output — it should ramp from the start_db value to end_db over the window.
3. Verify the envelope detector output tracks the AD8331 RF amplitude.

### 4.5. Calibration

1. **Zero-probe calibration**: couple the probe to a **known-thickness reference block** (e.g., the 4 mm steel step block sold for UT calibrations). In the Calibration menu, enter the reference thickness (4.00 mm) and press trigger. The device measures the TOF, subtracts the expected travel time, and stores the probe delay (`zero_offset_ns`).
2. **Velocity calibration**: on the same block, run the velocity calibration. The device solves for the material velocity and stores it. (Useful for verifying an unknown material.)
3. **Gain calibration**: couple to a reference reflector (a 2 mm flat-bottom hole at 10 mm depth in a calibration block) and run gain calibration. The device sets `gain_offset_db` so the reflector reads ~80 % full-scale.

### 4.6. First measurement

1. Apply a drop of couplant gel to a steel plate of known thickness (e.g., 10 mm).
2. Press the probe down and pull the trigger.
3. The OLED should show an A-scan with a clear back-wall echo at the expected depth, and a thickness readout near 10.00 mm.
4. If the reading is off by a constant, re-do zero-probe calibration.

---

## 5. Safety

- **HV interlock**: the pulser is inhibited (PC13) when the probe is uncoupled. Never bypass this.
- **ESD**: the probe connector has a TVS diode (D2). Avoid touching the probe tip with charged hands.
- **Battery**: use only protected 18650 cells. The TP4056 has built-in over-charge protection, but a protected cell adds over-discharge + short-circuit protection.
- **HV service**: when aligning the HV boost, keep one hand behind your back and use a 100:1 scope probe.

---

## 6. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| No A-scan / "No signal" | Probe not coupled, HV off, or pulser not firing | Check coupling, verify HV rail, check HRTIM output on PA8 with scope |
| A-scan but no thickness reading | Zero-offset too large, or wrong material selected | Re-calibrate zero, check material selection |
| Thickness reading drifts | Probe temperature drift | Re-zero more frequently; use a delay-line probe for stable temp |
| Noisy A-scan | VDDA noise, or TGC too aggressive | Verify VDDA filtering; reduce TGC end_db |
| BLE not advertising | ESP32-C3 not flashed, or antenna issue | Re-flash ESP32-C3, verify antenna soldering |
| SD card not detected | Card not inserted, or SPI CS issue | Re-seat card, check PB5 |
| HV rail won't reach setpoint | LM5022 feedback loop unstable, or inductor saturation | Reduce target voltage; check inductor saturation current |
| Battery % wrong | MAX17048 not initialized | Power-cycle; verify I²C address 0x36 |

---

## 7. Maintenance

- **Clean the probe connector** with isopropyl alcohol after each session; couplant gel is corrosive over time.
- **Re-calibrate zero** at the start of each day or when changing probes.
- **Update the material database** via BLE (`material_db.py`) when working with unusual alloys.
- **Battery storage**: if storing for >1 month, charge to ~50 % and disconnect.

---

## 8. Enclosure

The reference enclosure is a 3D-printed ABS case (STLs in `docs/enclosure/`, when available) with:

- A cutout for the OLED (top)
- A panel-mount LEMO/BNC connector (side)
- A USB-C port (bottom) with a gasket for IP54
- A rotary encoder + 3 buttons (top)
- A battery compartment (back) with a door secured by 2 screws
- A wrist strap loop (corner)

The case should be conformal-coated on the inside (especially around the HV section) with silicone conformal coating for humidity resistance. The OLED window should have a gasket.

---

*Built and tested by SoC Device Inventions. MIT License.*