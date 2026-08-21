# Halo Pin — Assembly Guide

## Overview

The Halo Pin is a pocket-sized optical particle counter that measures
airborne particle size distribution (0.3–40 µm) and computes PM1,
PM2.5, and PM10 mass concentration. This guide covers PCB assembly,
optical cell fabrication, and mechanical assembly.

## Tools Required

- Soldering iron (fine tip, 0.4 mm) + solder paste + hot-air reflow
  (or send the KiCad gerbers to JLCPCB for assembled PCB)
- Tweezers (ESD-safe)
- Multimeter
- 3D printer (for optical cell and enclosure)
- Scalpel / craft knife
- Compressed air (for cleaning)

## PCB Assembly

### Step 1: Order PCB

1. Open `schematic/halo_pin.kicad_pro` in KiCad 8.
2. Run **Plot Gerbers** (File → Fabrication Outputs → Gerbers).
3. Upload to JLCPCB / PCBWay: 4-layer, 1.6 mm, HASL, ENIG preferred.
4. Order the BOM components from the listed sources (see
   `hardware/BOM.csv`).

### Step 2: Solder Components (reflow order)

1. **Solder paste** — apply stencil paste to the PCB.
2. **Small components** — place passives (R, C, ferrite beads, L)
   using tweezers. Reference designators are silkscreened.
3. **SOIC / QFN ICs** — place U2 (TP4056), U4 (AP2112), U5 (LP5907),
   U6 (REF3030), U13 (NCP500), U7 (OPT101).
4. **LQFP-64** — place U1 (STM32G474RET6). Align pin 1 with the
   silkscreen dot. Use a fine tip and drag-solder the 0.5 mm pitch
   pins. Check for bridges with a magnifier.
5. **Modules** — hand-solder U11 (ESP32-C3-MINI-1), U12 (SH1106 OLED),
   J1 (USB-C), J2 (MicroSD). These are through-hole or castellated.
6. **Reflow** — hot-air reflow for SMD, iron for through-hole.

### Step 3: Power Rail Check

1. Connect USB-C (no battery). Measure:
   - +5V rail → ~5.0 V (MCP1640B pass-through when no battery)
   - +3V3D → 3.30 V ± 0.03
   - +3V3A → 3.30 V ± 0.03
   - VREF_3V0 → 3.00 V ± 0.01
2. If any rail is off, check for solder bridges / wrong-value parts.

### Step 4: Battery + Charger Check

1. Insert an 18650 cell (3.7V, ≥ 2500 mAh).
2. Connect USB-C. The charging LED should pulse.
3. After full charge, measure VBAT at the TP4056 BAT pin → ~4.15 V.
4. Disconnect USB. VBAT should stay at ~4.15 V.

## Optical Cell Fabrication

The optical cell is a 3D-printed black PLA chamber that houses:
- The laser diode (inlet side, horizontal beam)
- The OPT101 photodiode (top, 90° to beam)
- The airflow nozzle (vertical, crossing the beam at the focus)
- The exhaust port (bottom)

### Printing

1. Print `optical_cell.stl` in **black PLA** (infill 100%, 0.1 mm
   layer height). Black is critical to minimize internal reflections.
2. Print `inlet_nozzle.stl` — the nozzle tapers from 6 mm OD to
   1.5 mm ID, focusing the airflow into a 1.5 mm jet at the laser beam.
3. Sand the interior surfaces smooth and paint with matte black
   acrylic if any light leakage is visible.

### Assembly

1. Press-fit the laser diode (TO-18) into the horizontal bore. The
   beam should exit at the center of the chamber.
2. Press-fit the OPT101 (SO-8 on a small breakout) into the vertical
   bore, photodiode facing down toward the beam intersection.
3. Insert the inlet nozzle from the top; the 1.5 mm jet should be
   2 mm above the laser beam.
4. Connect the exhaust hose to the bottom port.
5. Add a light-absorbing baffle (black foam) between the photodiode
   and the laser diode to prevent direct beam pickup.

### Alignment Check

1. Power on. In a dark room, you should see a faint red dot where the
   laser beam hits the far wall of the cell.
2. The OPT101 output (PA0) should read ~0.5 V (baseline) in clean air.
3. If the baseline is > 1.0 V, the photodiode is picking up stray
   laser light — adjust the baffle or re-seat the diode.

## Mechanical Assembly

1. Mount the PCB in the 3D-printed enclosure (80 × 50 × 25 mm).
2. Mount the optical cell on top of the PCB.
3. Mount the blower on the side, connecting to the exhaust port.
4. Mount the HEPA prefilter on the inlet (optional, for zero tests).
5. Route the SDP810 pressure sensor tubing across the flow restrictor.
6. Mount the OLED, encoder, and buttons on the front panel.
7. Install the 18650 in the battery holder.

## Firmware Flash

1. Connect an ST-Link V2 to the SWD header (PD0/PD1 on the STM32).
2. Build: `cd firmware && make`
3. Flash: `make flash` (uses st-flash) or:
   ```
   openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
           -c "program halo_pin.elf verify reset exit"
   ```
4. The OLED should show "HALO PIN v1.0 ready".

## Calibration

See `docs/calibration-guide.md` for PSL sphere calibration and
`docs/zero-test.md` for the HEPA zero-air test.