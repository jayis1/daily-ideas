# Sky Lens — Assembly Guide

## Overview

Sky Lens is a pocket cosmic-ray muon telescope built around an
ESP32-S3-WROOM-1, two plastic scintillator tiles read out by silicon
photomultipliers (SiPMs), and an ADS7946 dual-channel 14-bit ADC for
pulse-height capture. This guide walks through the assembly in order
of dependency.

## Tools required

- Soldering iron (fine tip, 0.4 mm) + solder (0.5 mm SnAgCu)
- Hot-air rework station (for the QFN/MSOP packages)
- Tweezers, magnifier / microscope
- Multimeter
- USB-C cable for flashing + charging
- 3D printer (for the scintillator tile cage)
- Optical grease (Eljen EJ-550 or equivalent)
- PTFE thread-seal tape (diffuse reflector)
- Black electrical tape / aluminium foil (light-tight wrap)

## Step 1 — PCB population

### 1a. SoC + power (solder in this order)

1. **U1 — ESP32-S3-WROOM-1**: Place on the PCB footprint, align the
   castellated edges. Solder one corner pad, reflow with hot air at
   320 °C. The module has an internal antenna; keep the keep-out area
   clear of copper on all layers (see the datasheet).
2. **U12 — TP4056**: USB-C LiPo charger. Place near the USB-C connector.
3. **U11 — AMS1117-3.3**: 3.3 V LDO for the logic rail.
4. **U13 — MAX17048**: LiPo fuel gauge (I²C, address 0x36).
5. **BAT — LiPo connector**: JST-PH 2-pin for the 1500 mAh pack.

### 1b. SiPM bias (+30 V)

6. **U10 — TPS61158**: Boost converter to +30 V. Populate the inductor
   (22 µH), feedback resistors (set to 29.5 V), and the output cap
   (4.7 µF, 50 V rating — *important*: the 30 V rail needs 50 V caps).
7. **Q1 — DMN2041L**: N-FET high-side switch for BIAS_EN.
8. **Bias divider**: 10 MΩ + 330 kΩ (÷30) → GPIO16 (BIAS_MON).
9. **Bleeder**: 10 MΩ across the +30 V rail to discharge it on power-off.
10. **Fault pull-up**: 10 kΩ from GPIO38 (BIAS_FAULT) to +3V3.

### 1c. Analog front end

11. **U5 — OPA2356**: Dual transimpedance amp. Each SiPM anode connects
    to the inverting input through a 10 kΩ feedback resistor + 1 pF
    cap (sets the TIA gain and bandwidth). Place the SiPM input pads
    as close as possible to the op-amp inputs to minimise stray
    capacitance.
12. **D1, D2 — 1N4148**: Clamp diodes from each TIA input to +3V3 and
    GND, to protect the op-amp from SiPM transients.
13. **U6a, U6b — TLV3501**: Two ultra-fast comparators (4.5 ns
    propagation delay). Each TIA output feeds a comparator with a
    threshold set by a 10 kΩ potentiometer (calibrate so the
    threshold is ~1/3 of the single-photo-electron peak).
14. **Peak-hold**: A diode (BAV99) + 1 nF cap on each TIA output holds
    the pulse peak for the ADS7946 to sample. A reset FET (2N7002)
    discharges the cap after each read.

### 1d. ADC

15. **U2 — ADS7946**: Dual 14-bit SAR ADC. SPI interface to the ESP32-S3
    (GPIO4-8). Place close to the peak-hold outputs.
16. **REF — REF5045**: 4.5 V voltage reference for the ADS7946 full-scale.
17. **CONVST**: GPIO8 drives the ADS7946 CONVST pin, asserted by the
    coincidence logic.

### 1e. I²C peripherals

18. **U7 — SSD1306 OLED**: 128×64 I²C display. Solder the 4-pin header
    (VCC, GND, SCL, SDA) and mount the OLED on the front panel.
19. **U8 — BMP390**: Pressure + temperature sensor (I²C, 0x77). Place
    away from heat-generating components (the boost, the ESP32).
20. **U9 — ICM-42688-P**: 6-axis IMU (I²C, 0x69). Mount flat on the PCB,
    aligned with the detector axis (the z-axis should point up when
    the device is face-up).
21. Pull-ups: 4.7 kΩ on SDA and SCL (shared by all I²C devices).

### 1f. SD card + user I/O

22. **µSD — Molex 502570-0893**: microSD socket on SPI2 (GPIO11-14).
23. **Buttons**: START (GPIO21), MODE (GPIO20), each with a 100 nF
    debounce cap.
24. **LEDs**: RUN (green, GPIO19), FAULT (red, GPIO18), 1 kΩ resistor
    each.
25. **J1 — USB-C**: 2.0 receptacle for charging + ESP32 console.

## Step 2 — Scintillator stack assembly

1. **Print the tile cage** (`docs/tile_cage.stl`): a two-piece
   light-tight enclosure that holds the two EJ-200 tiles with a 30 mm
   gap. The cage has cutouts for the SiPMs on the back of each tile.
2. **Polish the tile edges**: sand the cut edges of the EJ-200 tiles
   with 2000-grit paper and polish with a soft cloth. Smooth edges
   improve light collection.
3. **Couple the SiPMs**: Apply a small dab of optical grease (EJ-550)
   to each SiPM active area and press it onto the centre of the tile's
   back face. Hold for 30 s until the grease spreads evenly.
4. **Wrap the tiles**: Wrap each tile in 2–3 layers of PTFE thread-seal
   tape (a diffuse reflector that bounces scintillation light back
   toward the SiPM). Leave only the SiPM area exposed.
5. **Assemble the stack**: Place the top tile, then the 30 mm spacer,
   then the bottom tile into the cage. Close the cage.
6. **Light-tight wrap**: Wrap the entire cage in black aluminium foil
   (or black tape) so no ambient light leaks in. Even a small light
   leak will swamp the SiPM signal.

## Step 3 — Flashing

1. Connect USB-C to a computer.
2. Flash the ESP32-S3:
   ```bash
   cd firmware/esp32
   idf.py set-target esp32s3
   idf.py build
   idf.py -p /dev/ttyACM0 flash monitor
   ```
3. The OLED should light up with the dashboard view. The RUN LED
   should be green. If the FAULT LED is red, the SiPM bias boost
   failed to start — check the TPS61158 and Q1.

## Step 4 — Calibration

See [`calibration-guide.md`](calibration-guide.md) for the threshold
scan, coincidence-window scan, pressure-barometric-coefficient fit, and
IMU attitude alignment.

## Step 5 — Field deployment

- **Indoor**: Place face-up on a stable surface. Muons will be detected
  at ~25 cpm. Watch the OLED dashboard.
- **Outdoor**: Place in a sheltered spot (rain will damage the
  non-conformal-coated PCB). For long runs, enable deep-sleep duty-cycle
  mode via the BLE app.
- **Muon-lifetime mode**: Place a stopping absorber (e.g. a 20 mm
  aluminium plate) above the bottom tile. Select "Lifetime" mode in the
  app. After a few hours, the lifetime histogram will populate and the
  fit will converge to τ_µ ≈ 2.2 µs.