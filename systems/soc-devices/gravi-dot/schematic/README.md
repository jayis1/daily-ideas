# Gravi Dot — Schematic

KiCad 7+ project files for the Gravi Dot portable relative gravimeter.

## Files

| File | Description |
|------|-------------|
| `gravi_dot.kicad_pro` | KiCad project file |
| `gravi_dot.kicad_sch` | Schematic (symbolic netlist) |
| `gravi_dot.kicad_pcb` | PCB layout (placement + layer stackup) |
| `gravi_dot.kicad_prl` | Project local settings |

## Design rules

- 4-layer PCB: signal / GND / 3V3 / signal
- 50×50 mm board size
- Minimum trace: 0.15 mm (6 mil)
- Minimum via: 0.4 mm diameter, 0.2 mm drill
- ENIG finish for fine-pitch components (LCC-14 ADXL355)

## Key design notes

1. **ADXL355 on daughterboard** — the gravity sensor is on a separate 15×15 mm PCB inside a copper thermal mass, connected via FFC. This isolates it from main-board thermal gradients and vibration.
2. **SPI1 bus sharing** — ADXL355 and SCL3300 share SPI1 with separate CS lines. The ADXL355 has priority (higher sample rate). The SCL3300 is read once per station (30 s).
3. **Peltier drive** — DRV8833 H-bridge driven by HRTIM PWM at 20 kHz (above audible range). The PID loop runs at 10 Hz.
4. **GPS isolation** — NEO-M9N is on the opposite side of the board from the ADXL355 to minimize RF interference.
5. **Decoupling** — each IC has 100 nF + 10 nF ceramic decoupling close to the VDD pin. The ADXL355 has additional 1 µF bulk.