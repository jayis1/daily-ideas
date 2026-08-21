# Iono Pin — Assembly Guide

This guide walks through assembling a complete Iono Pin pocket ion mobility spectrometer. It assumes basic SMD soldering skills and access to a 3D printer.

## Parts checklist

See [`../hardware/BOM.csv`](../hardware/BOM.csv) for the full BOM (~$65). Key subsystems:

1. **Main PCB** (4-layer, 80×40 mm, JLCPCB)
2. **SoCs**: STM32G474RET6 (U1), ESP32-C3-MINI-1 (U2)
3. **HV**: EMCO F50CT 5 kV module (U6) + 8× 10 MΩ 1 kV resistors (R1–R8)
4. **Ionizer**: Ni-63 37 kBq sealed source (SRC1) **or** corona-discharge needle (ALT1) + 2N7002 (Q2)
5. **Receiver**: ADA4530-1 TIA (U3) + REF3030 (U5) + ADS122U04 (U4)
6. **Drift tube**: PTFE tube 8.5 cm + stainless resistor rings + Bradbury-Nielsen shutter grid + Faraday plate (PCB)
7. **Sample path**: PDMS membrane (MEMB1), 6 V micro-pump (PUMP1), 2-way valve (VALVE1)
8. **Power**: 18650 holder + TP4056 + MCP1640B + AP2112K + LP5907
9. **UI**: SH1106 OLED + 3 buttons + EC11 encoder + buzzer + WS2812B
10. **Sensors**: BME280 + DS18B20 + W25Q128 flash + MicroSD socket

## Tools

- Soldering iron (fine tip) + solder paste + hot-air rework or reflow oven
- Multimeter
- ST-Link V2 (for STM32 flashing/debugging)
- USB-C cable
- 18650 cell (not in BOM cost)
- 3D-printed enclosure (STL in `docs/enclosure/` — optional)
- Ni-63 source handling: tweezers, gloves, designated storage box

## PCB assembly

1. **Order the PCB** from JLCPCB (4-layer, 80×40 mm, 1.6 mm, ENIG finish for the HV resistor pads).
2. **Stencil + paste**: apply solder paste with the stainless stencil.
3. **Place components** in order: passives (R/C/L first), then small ICs (LDOs, op-amp, ADC), then the STM32 (QFP-64), ESP32-C3 module, and finally the EMCO HV module (through-hole).
4. **Reflow**: standard lead-free profile (peak 245 °C). Hand-solder the EMCO module, USB-C, buttons, SD socket, and pin headers after reflow.
5. **HV resistor chain** (R1–R8, 10 MΩ 2512): these must be 1 kV-rated. Place along the drift tube ring positions. Verify with a multimeter after assembly (total 80 MΩ, R1 to R8).
6. **Clean** with isopropyl alcohol, especially around the ADA4530-1 input pad (any flux residue on the Faraday guard ring will cause leakage).

## Drift tube assembly

The drift tube is the heart of the IMS. It consists of:

```
Ionizer region -> Bradbury-Nielsen shutter -> 8 resistor rings (drift region) -> Faraday plate
```

1. **Cut the PTFE tube** to 8.5 cm length, ID 12 mm.
2. **Stainless rings**: 8 rings spaced 1 cm apart, each connected to a tap on the resistor chain. The top ring (R1) connects to +2125 V (HV), the bottom ring (R8) to GND. This creates a uniform 250 V/cm field.
3. **Bradbury-Nielsen shutter**: etch two interleaved wire sets (0.1 mm pitch) on a small PCB that slides into the tube just below the ionizer region. Wire the two sets to the SHUTTER_P and SHUTTER_N signals.
4. **Faraday plate**: a 8 mm diameter copper pad on the bottom PCB, connected to the ADA4530-1 inverting input via the shortest possible trace. Surround it with a guard ring driven at the same potential.
5. **Ionizer**: mount the Ni-63 foil (or corona needle) at the top of the ionization region, above the shutter. The sample inlet (PDMS membrane) should be adjacent.

## Wiring

| Connection | From | To |
|---|---|---|
| HV supply output | EMCO F50CT HV+ | R1 top (drift tube) |
| HV GND | EMCO F50CT GND | R8 bottom + system GND |
| Shutter P | PA3 (STM32) | Bradbury-Nielsen set A |
| Shutter N | PA4 (STM32) | Bradbury-Nielsen set B |
| Faraday plate | ADA4530-1 inverting input | — |
| Ionizer enable | PA2 (STM32) | Ni-63 bias / corona driver |
| Pump PWM | PA5 (STM32) | Pump MOSFET gate |
| Valve | PC12 (STM32) | 2-way valve |
| BME280 | I2C1 (PA15/PB4) | BME280 SDA/SCL |
| DS18B20 | PB6 (STM32) | DS18B20 DQ (1-Wire) |
| OLED | I2C1 (PA15/PB4) | SH1106 SDA/SCL |
| SD card | SPI3 (PC10-12, PD2) | MicroSD |
| ESP32-C3 | USART2 (PB10/PB11) | ESP32-C3 GPIO4/GPIO5 |

## Firmware flashing

### STM32G474
```bash
cd firmware
make
make flash   # via ST-Link + openocd
```

### ESP32-C3 bridge
```bash
cd firmware/bridge
idf.py set-target esp32c3
idf.py build flash monitor
```

## First power-up checklist

1. **No 18650, no HV**: power from USB-C only. Verify 3V3 and 5V rails with a multimeter. The OLED should show the splash screen.
2. **Check interlock**: with the lid open, the ionizer/HV should refuse to enable (display "LID OPEN").
3. **Calibration blank**: close the lid, press CAL. The pump runs on drift gas only. After ~10 s, the display should show the Reactant Ion Peak (RIP) at K₀ ≈ 2.7. If it does, the drift tube, HV, shutter, and electrometer all work.
4. **Sample test**: use a safe simulant (e.g., a cotton swab with trace acetone or DMMP) near the inlet. Press SCAN. The display should show a product-ion peak at the expected K₀ (acetone ≈ 1.95, DMMP ≈ 1.78).

## Calibration

- **RIP calibration**: run a blank (drift gas only) and note the RIP drift time. Adjust the drift-voltage servo until the RIP K₀ reads 2.70. This compensates for any drift-tube length tolerance.
- **K₀ library tuning**: if your instrument geometry differs slightly, collect simulants and adjust the library K₀ entries in [`firmware/main/library.c`](../firmware/main/library.c).

See [`measurement-theory.md`](measurement-theory.md) for the physics and [`safety-notes.md`](safety-notes.md) before operating.