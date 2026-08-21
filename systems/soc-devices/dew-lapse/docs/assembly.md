# Assembly Guide — Frost Point Chilled-Mirror Hygrometer

This guide walks through assembling a Frost Point unit from the BOM.

## 1. PCB fabrication

Order the 4-layer PCB (60 × 60 mm) from your preferred fab (JLCPCB, PCBWay). The stack-up:

| Layer | Purpose |
|-------|---------|
| Top   | Components, signal routing |
| Inner 1 | GND plane (solid) |
| Inner 2 | 3.3 V plane + 5 V plane (split) |
| Bottom | Components, signal routing, heatsink pad for TEC hot side |

Finish: ENIG (for the gold mirror contact pad on the flex cable).

## 2. Mirror assembly (the hard part)

The mirror is the most delicate subassembly. Steps:

1. **Cut** a 10 × 10 × 1 mm borosilicate glass disc (Edmund Optics 43-960 cut down, or purchase pre-cut).
2. **Coat**: have a thin-film house sputter 200 Å Cr (adhesion), then 1 µm Au, then 50 Å Au final polish. The final 50 Å layer should be done with low-energy sputtering for a mirror finish. If you lack access to a sputter tool, an alternative is to use a pre-coated first-surface mirror (Edmund #84-491) and cut it to size with a diamond scribe.
3. **Bond thermistors**: use a tiny drop of Arctic Silver thermal epoxy to bond two Murata NCP18XH103F03RB 0805 NTC thermistors to the *back* of the glass disc (the uncoated side). Place one at the geometric center (this is T_m), one at the corner (this is T_r). Cover T_r with a 2 × 2 mm PTFE tape mask so that condensation cannot form on the gold above it.
4. **Bond to TEC**: bond the glass disc (back side, with thermistors) to the cold ceramic face of the TEC1-12706 with a thin layer of Arctic Silver thermal epoxy. Cure for 4 hours at 25 °C.
5. **Wire** the thermistors to the ADC bridge: each thermistor forms a half-bridge with a precision 100 kΩ 0.1% resistor on the PCB. Use 36 AWG PTFE wire.

## 3. TEC + heatsink

1. Clamp the TEC1-12706 between the mirror assembly (cold side) and a 40 × 40 × 11 mm aluminum heatsink (hot side). Use a thin layer of non-silicone thermal paste.
2. The heatsink exits through a cutout in the housing rear wall.
3. Mount the 30 mm Sunon blower so it blows across the heatsink fins and the mirror chamber simultaneously.

## 4. PCB population

Solder in this order (lowest to highest profile):

1. Resistors, capacitors, inductors
2. SOIC / SOT-23 (DRV8871, AD8418, MCP73831, TPS7A4700, CH224K)
3. QFN (STM32L476RG, ADS122U04) — use a hot-air station and solder paste stencil
4. W25Q128 (SOIC-8)
5. OLED, BLE module, USB-C connector
6. Sensor modules: BME280, SCD41, SHT45, MS5837 (all on I2C3)
7. IR LED and phototransistor on the mirror chamber side

## 5. Housing

The housing is a 60 × 60 × 32 mm CNC-machined 6061-T6 aluminum enclosure with:
- Air inlet: 4 mm PTFE tube fitting on the side
- Air outlet: louvered slots on the opposite side
- Heatsink cutout on the back
- USB-C port on the bottom
- OLED window on the front
- User button on the top

## 6. Wiring

Connect the TEC to J4 (2-pin JST-PH) with 22 AWG wire. Connect the blower to J5. Connect the mirror thermistor pair to the 4-pin header on the PCB (T_m, T_r, GND, V_ref).

## 7. First power-up

1. Connect USB-C (5 V, ≥2 A).
2. The OLED should show "FROST POINT v1.0" for 2 s, then the IDLE dashboard.
3. The status LED should be off (IDLE state).
4. Open a serial terminal on the BLE module's UART at 115200 baud to see the boot banner.
5. Press the user button — the device should enter RAMP_DOWN, LED red, then TRACK, LED green when stable.

## 8. Calibration

1. **Mirror thermistor offset**: with the TEC off, immerse the mirror in a stirred 0 °C ice-water bath (in a PTFE bag). Record raw ADC codes for T_m and T_r. Program the offsets into `config.h` (NTC_R_REF is the bridge reference; adjust for any observed offset).
2. **Coarse reference**: compare against a known RH sensor at 25 °C, 50 %RH. The dew point should read ~9.3 °C ±0.2 °C.
3. **Optical baseline**: run `optics_calibrate_baseline()` in IDLE state (TEC off, clean mirror) — the firmware does this automatically on boot.

## 9. Field use

For compressed-air dew-point measurement, plumb the air line to the inlet tube. For ambient measurement, simply expose the inlet to the air. Press the button to start; the dew point is valid within ~30 s.