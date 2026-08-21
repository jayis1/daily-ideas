# QCM Halo — Assembly Guide

## Overview

This guide walks through assembling a QCM Halo pocket QCM-D instrument from the KiCad schematics, BOM, and 3D-printed parts.

## Tools Required

- Soldering iron (fine tip, temperature-controlled)
- Solder (0.5mm rosin-core, lead-free or leaded)
- Tweezers (ESD-safe, fine tip)
- Magnifier or microscope (for SMD work)
- Multimeter
- ST-Link V2 programmer (for STM32)
- USB-C cable
- MicroSD card (4–32 GB)
- 3D printer (for enclosure and flow cell)
- Small Phillips screwdriver
- M2 screws and nuts
- PTFE tubing (3mm OD) and Luer fittings

## PCB Assembly

### Step 1: Order PCB
- Upload `schematic/qcm-halo.kicad_pcb` Gerbers to JLCPCB (or similar)
- Spec: 4-layer, 1.6mm, ENIG finish, 1oz copper
- Order minimum 5 boards (~$2 each)
- Note: 50Ω controlled impedance is recommended for the RF traces

### Step 2: Solder Components (in order of decreasing size)
1. **STM32G474RET6** (LQFP-64): Align pin 1, tack-solder corners, drag-solder or reflow
2. **ESP32-C3-MINI-1** module: Check orientation, solder castellated edges
3. **TPS63020** (QFN-14): Apply stencil solder paste, place with tweezers, reflow
4. **MCP73831** (SOT-23-5): Hand solder
5. **Si5351A-B-GT** (MSOP-10): Fine-pitch, use solder paste + reflow
6. **LTC1968** (MSOP-8): Solder paste + reflow
7. **ADS122U04** (TSSOP-16): Solder paste + reflow
8. **ADG918** (SC-70-6): Very small, use tweezers and solder paste
9. **OPA656** (SOT-23-6): Hand solder
10. **Passive components** (0603 resistors, capacitors): Use pick-and-place or tweezers
11. **DRV8833** (SOIC-16): Hand solder
12. **W25Q128** (SOIC-8): Hand solder
13. **Connectors**: USB-C, MicroSD socket, QCM crystal headers
14. **Through-hole**: DS18B20 (TO-92), ULN2003 (DIP-16), PT1000 leads

### Step 3: Clean and Inspect
- Clean flux residue with isopropyl alcohol
- Inspect all solder joints under magnification
- Check for bridges on fine-pitch ICs (especially Si5351A and ADG918)
- Verify continuity with multimeter (power rails: +3V3, GND, +12V)

### Step 4: Power Test
- Connect battery (3.7V LiPo) — **do NOT insert yet**
- Check for short circuits between +3V3 and GND
- Connect USB-C power (without battery)
- Verify: +3V3 rail reads 3.30V ± 0.05V
- Verify: +12V boost (TEC rail) reads ~12V

### Step 5: Program STM32
- Connect ST-Link V2 to SWD header (SWDIO, SWCLK, GND, 3V3)
- Flash firmware:
  ```bash
  openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
    -c "program qcm_halo.elf verify reset exit"
  ```
- Verify OLED display shows "QCM Halo v1.0" on boot

### Step 6: Program ESP32-C3
- Connect USB-C (which routes to ESP32-C3 UART)
- Or use external USB-to-UART adapter on ESP32-C3's GPIO2/GPIO3
- Flash with ESP-IDF:
  ```bash
  idf.py flash
  ```

### Step 7: Assemble Mechanical Parts

#### Flow Cell
1. 3D print the flow cell body (STL in `docs/flow_cell.stl`)
2. Insert QCM crystal holder with O-ring seal
3. Connect PTFE tubing (3mm OD) to inlet/outlet ports
4. Mount the PT1000 RTD on the aluminum thermal block behind the crystal holder

#### Peltier Assembly
1. Attach TEC1-12704 to the aluminum thermal block
2. Apply thermal paste on both TEC surfaces
3. Mount heatsink on the hot side
4. Connect TEC leads to DRV8833 output

#### Pump and Valve
1. Mount peristaltic pump head on motor shaft
2. Route PTFE tubing through pump head
3. Mount 28BYJ-48 stepper to 3D-printed valve body
4. Connect valve ports to: buffer, sample, wash, rinse, waste, air

### Step 8: Final Assembly
1. Mount PCB in 3D-printed enclosure
2. Route QCM crystal connector cables to flow cell
3. Insert LiPo battery (2000mAh)
4. Close enclosure with M2 screws
5. Apply magnetic reed switch interlock

## Calibration

### Crystal Calibration (Air + Water)
1. Mount a clean 5 MHz QCM crystal in the flow cell
2. Run calibration from the menu (Button A → Calibrate)
3. The device measures baselines at all 6 overtones in air
4. Introduce water via the pump
5. Verify Δf matches Kanazawa-Gordon prediction:
   - At 5 MHz: Δf ≈ -714 Hz (water at 20°C)
   - At 15 MHz (3rd overtone): Δf ≈ -3,713 Hz
6. Use `scripts/calibrate.py` for automated calibration via BLE

### Liquid Calibration
For viscosity measurements, use known standards:
- Water: η = 1.002 mPa·s at 20°C
- Glycerol 50%: η ≈ 6.0 mPa·s
- Glycerol 80%: η ≈ 60.1 mPa·s

## Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| No oscillation | Si5351A not configured | Check I2C address 0x60, verify 25 MHz crystal |
| Frequency unstable | Poor crystal contact | Clean crystal electrodes, check holder spring contacts |
| Dissipation too high | Liquid in holder gap | Check O-ring seal, reseat crystal |
| TEC not cooling | Polarity reversed | Swap TEC leads or check DRV8833 wiring |
| BLE not found | ESP32-C3 not flashed | Flash esp_bridge.c firmware |
| SD card error | Card not FAT32 | Format as FAT32, check socket soldering |

## Safety Notes

- **LiPo battery**: Do not short-circuit or puncture. Charge only with MCP73831.
- **TEC**: Can reach high temperatures if driven at 100% without heatsink. Always mount heatsink.
- **Chemical handling**: Use appropriate PPE when handling buffer solutions and analytes.