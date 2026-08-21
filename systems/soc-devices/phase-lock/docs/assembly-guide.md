# Phase Lock — Assembly Guide

This guide walks through building the Phase Lock pocket digital
lock-in amplifier from the BOM and PCB.

## Tools Required

- Soldering iron (fine tip) or hot-air rework station
- Solder paste + stencil (recommended for the LQFP-64 SoC)
- Multimeter
- Tweezers (ESD-safe)
- KiCad (for viewing the schematic/PCB)
- Optional: oscilloscope (for verifying the reference output)

## Build Order

### 1. PCB Fabrication
Order the 4-layer PCB from JLCPCB / PCBWay / etc. using the
`phase_lock.kicad_pcb` file. Recommended stackup:
- Top: signal + SoC + analog
- L2: solid GND pour
- L3: power islands (3.3 V / 5 V / ±10 V)
- Bottom: passives + routing
- 1.6 mm, ENIG finish, 0.2 mm minimum trace / 0.4 mm minimum via.

### 2. Power Supply Section
Solder in this order (always power first, to enable testing):
1. USB-C receptacle (J1)
2. TP4056 charger (U2) + supporting passives (R_PROG = 1.2 kΩ → 1 A charge)
3. 18650 battery holder (BT1) — do NOT insert the battery yet
4. MCP1640B boost (U3) + inductor (4.7 µH)
5. TPS65131 dual-output ±10 V converter (U4) + inductors (2× 10 µH)
6. AP2112-3.3 digital LDO (U5)
7. LP5907-3.3 ultra-low-noise analog LDO (U6)
8. REF3030 3.0 V reference (U7) + decoupling (C9 = 1 µF, C6 = 100 nF)

**Test point:** With USB-C plugged in (no battery), verify:
- 5 V at the USB rail
- 3.3 V at AP2112 output (digital)
- 3.3 V at LP5907 output (analog)
- 3.0 V at REF3030 output
- ±10 V at TPS65131 outputs (check both)

### 3. SoC + Digital
1. STM32G491RET6 (U1) — LQFP-64. Use solder paste + stencil; align
   pin 1 with the silkscreen dot. Hot-air or reflow.
2. 32.768 kHz crystal (Y1, optional — for RTC timestamps) + 2× 12 pF
3. Decoupling: 100 nF on each VDD pin (6 caps), 10 µF bulk near SoC
4. WS2812B RGB LED (D1)
5. Mode + Run/Stop tactile buttons (SW2, SW3)
6. EC11 rotary encoder (SW1)

**Test point:** With battery inserted and powered on, the SoC should
boot. If you have the ST-Link, flash the firmware and verify the
OLED shows "PHASE LOCK v1.0 ready".

### 4. Analog Front End
1. PGA204 instrumentation amp (U8) — SOIC-16
2. PGA113 PGA (U9) — VSSOP-10
3. Bessel 2nd-order low-pass filter (U10) — SOIC-8 with 4× 1 nF C0G caps
4. Input protection: back-to-back Schottky clamps (BAT54S) at the
   Signal In BNC

**Critical:** Keep the analog section on its own GND island, tied to
the main GND at a single point under the PGA204. Use a guard ring
around the input traces. Keep the analog traces short and away from
the digital/switching sections.

### 5. Reference Path
1. OPA569 power op-amp (U11) — SO-20
2. DAC1 reconstruction filter: 5th-order Bessel using 4× 1 nF C0G
   caps and 1 kΩ series resistors
3. Ref Out BNC (J4)

**Test point:** With the firmware running, set f₀ = 1 kHz, amplitude
= 1 V. Connect an oscilloscope to Ref Out BNC; you should see a clean
1 kHz sine at ~1 V peak.

### 6. Front-Panel BNC Connectors
1. Signal In BNC (J3)
2. Ref Out BNC (J4)
3. Aux Out BNC (J5)
4. Aux In BNC (J6)

### 7. Peripherals
1. SH1106 OLED (U13) — I2C module, 4-pin header (VCC/GND/SDA/SCL)
2. MicroSD socket (J2)
3. ADS1115 aux ADC (U14) — MSOP-10
4. ESP32-C3-MINI-1 BLE bridge (U15) — module
5. W25Q128 flash (U12) — optional, for offline storage

### 8. Final Assembly
1. Insert the 18650 battery (check polarity!)
2. Close the 3D-printed enclosure
3. Power on via USB-C (the device runs from battery; USB-C is for
   charging + optional USB-CDC data)

## Enclosure

A 3D-printed PLA enclosure (~130 × 72 × 24 mm) holds the PCB, the
18650, and has cutouts for the four BNC connectors, the OLED, the
rotary encoder, the two buttons, and the USB-C port. The STL is in
`hardware/enclosure.stl` (placeholder — design your own in Fusion 360
or FreeCAD).

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No display | I2C wiring (PA11/PA12), OLED address (0x3C) |
| No Ref Out | DAC1 config, OPA569 enable (PB12), ±10 V rails |
| Signal always zero | PGA gain pins (PB2..PB7), input coupling |
| Noise too high | Analog GND island, ferrite beads, LP5907 |
| BLE not visible | ESP32-C3 firmware (separate), USART1 wiring |
| SD not mounting | SPI1 wiring (PA5/PA7/PA13), CS (PB8) |

## Safety Notes

- The OPA569 can source 200 mA at ±10 V — do not short the Ref Out BNC.
- The ±10 V rails can deliver ~2 W — the TPS65131 has thermal shutdown.
- The 18650 battery has no protection circuit on-board; use a
  protected cell (with built-in PCB) or add a DW01 + FS8202 protection
  IC. The TP4056 handles charging; discharge protection is the cell's
  responsibility.
- Always power down before connecting/disconnecting the BNC cables
  to a live experiment.