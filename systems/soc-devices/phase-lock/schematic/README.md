# Phase Lock — KiCad Schematic

This folder contains the KiCad 7+ project files for the Phase Lock
pocket digital lock-in amplifier.

## Files

- `phase_lock.kicad_pro` — KiCad project file
- `phase_lock.kicad_sch` — schematic (top-level)
- `phase_lock.kicad_pcb` — PCB layout (4-layer, 1.6 mm)

## Schematic Overview

```
   USB-C ── TP4056 ── 18650 ── MCP1640B (5V) ─┬─ TPS65131 (±10V)
                                              ├─ AP2112-3.3 (digital)
                                              ├─ LP5907-3.3 (analog)
                                              └─ REF3030 (3.0V VREF)
   STM32G491RET6 (U1):
     CORDIC → DAC1 → reconstruction LPF → Ref Out BNC
                                      → OPA569 power amp → ±10 V excite
     ADC1 ← Bessel LPF ← PGA113 ← PGA204 ← Signal In BNC
     I2C1 → SH1106 OLED + ADS1115
     SPI1 → MicroSD
     USART1 → ESP32-C3 (BLE)
     GPIO → PGA gain selects, encoder, buttons, WS2812B, OPA569 enable
```

## PCB Stackup

4-layer, 1.6 mm:
- **Top** — analog + SoC + BNC connectors
- **L2** — solid GND pour (analog + digital split under PGA)
- **L3** — power (3.3 V, 5 V, ±10 V islands)
- **Bottom** — passives + routing

## Notes

- The analog front-end (PGA204 → PGA113 → Bessel LPF) is in a dedicated
  analog island on the top layer, surrounded by a GND guard ring.
- The ±10 V rail from the TPS65131 is on L3 with a moat; the OPA569
  power-amp section is isolated from the sensitive ADC input.
- The REF3030 (3.0 V VREF) is placed adjacent to the STM32G491 VREF+
  pin with a 100 nF + 1 µF decoupling pair.
- The ESP32-C3 BLE bridge module is on the bottom side, away from the
  analog section, with its own GND island tied to the main GND at one
  point under the USART1 connector.

## Build

Open the `.kicad_pro` in KiCad 7+. Run ERC then PCB layout. The BOM
is in `../hardware/BOM.csv`.