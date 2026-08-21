# Aero Reed — Assembly Guide

This guide walks through building the Aero Reed electronic wind instrument
from a bare PCB to a playable instrument.

## Prerequisites

- Soldering iron (fine tip) or hot-air reflow station
- Solder paste (for reflow) or 0.5 mm solder wire
- Tweezers, flux, isopropyl alcohol
- Multimeter
- 3D printer (for mouthpiece and case)
- ESP-IDF v5.2+ installed on your computer

## Step 1: PCB Fabrication

Order the 4-layer PCB (50 × 180 mm, 1.6 mm FR4) from JLCPCB, PCBWay, or
your preferred fab. The KiCad files are in `schematic/`.

Recommended stackup:
- Layer 1 (Top): signal + touch pad electrodes
- Layer 2: GND plane (solid copper, keep clear of touch pads)
- Layer 3: 3V3 power plane
- Layer 4 (Bottom): signal + component placement

## Step 2: Solder the Power Section

1. Place **U8 (TP4056)** — USB-C LiPo charger.
2. Place **U9 (ME6211 LDO)** — 3.3 V regulator.
3. Place **U7 (MAX17048)** — fuel gauge (SOT-23-8).
4. Solder **R2/R3** (battery voltage divider: 100 kΩ / 220 kΩ).
5. Place **J2 (USB-C receptacle)**.
6. Place charge LEDs (**LED1** red, **LED2** green).

**Test:** Connect USB-C. Measure 3.3 V at the LDO output. Red LED should
light (charging, no battery). Check VBAT rail ~4.0 V when battery connected.

## Step 3: Solder the SoC

1. Apply solder paste to the ESP32-S3-WROOM-1 footprint.
2. Place **U1 (ESP32-S3-WROOM-1-N8)** with tweezers.
3. Reflow at 245 °C peak (lead-free profile).
4. Inspect under magnification for bridges on the castellated edges.

**Test:** Connect USB-C. The ESP32-S3 should enumerate as a USB device.
Flash the firmware:
```bash
cd firmware
idf.py set-target esp32s3
idf.py -p /dev/ttyACM0 flash monitor
```
You should see boot messages on the serial monitor.

## Step 4: Audio Section

1. Place **U4 (PCM5102A)** — I2S DAC (TSSOP-20).
2. Place **U5 (MAX98357A)** — class-D amp (QFN-16).
3. Place **J1 (3.5 mm headphone jack)**.
4. Solder the speaker wires to the SPK+/SPK- pads.

**Test:** Flash firmware. You should hear a faint click when the I2S bus
initializes. The synth simulation output should be audible when you blow
into the mouthpiece (once sensors are connected).

## Step 5: Sensors

### Breath Pressure (MP3V5004G)
1. Place **U2 (MP3V5004G)** on the PCB.
2. Connect the pressure port to the mouthpiece tube via silicone tubing
   (2 mm ID). The sensor measures the pressure difference between the
   mouthpiece chamber and ambient.

### Lip Force (FSR-402)
1. Mount the **FSR-402** in the mouthpiece assembly (see 3D print).
2. Wire: one leg to 3V3, other leg to GPIO16 (ADC) with 10 kΩ pull-down
   (R1) to GND. More bite → lower resistance → higher voltage at the ADC.

### IMU (ICM-42688-P)
1. Place **U3 (ICM-42688-P)** on the PCB (SPI bus, GPIO18-21).
2. Place 0.1 µF decoupling cap (C4) close to the VDD pin.

**Test:** The firmware logs IMU readings at boot. Tilt the board and verify
the pitch angle changes in the serial monitor.

## Step 6: Display

1. Solder the **SSD1306 OLED** module (I2C, 0x3C) to the top face.
2. Wire: VCC→3V3, GND→GND, SCL→GPIO9, SDA→GPIO8.

**Test:** On boot, the OLED should show "P0:Soprano Sax" and status info.

## Step 7: Touch Pads

The 14 touch pads are large copper areas on the front PCB face (top layer).
They can be used bare or covered with a thin (≤0.5 mm) acrylic/PCB overlay.
Thicker overlays reduce sensitivity — the firmware auto-calibrates the
baseline at boot, but very thick overlays will prevent detection.

The pad layout (saxophone-style) is:
```
       OCT↑    OCT↓          ← thumb pads (back of instrument)
  ┌─────────────────────┐
  │ L1  L2  L3  L4  L5   │   ← left hand (index-middle-ring-pinky)
  │ R1  R2  R3  R4  R5   │   ← right hand
  │    BEND     ALT       │   ← aux pads
  └─────────────────────┘
```

## Step 8: Mouthpiece Assembly

3D-print the mouthpiece (`docs/mouthpiece.stl`). It has two chambers:
1. **Breath chamber** — connects to the MP3V5004G pressure port via
   silicone tubing. The player blows here.
2. **Lip/bite platform** — the FSR-402 sits under a soft silicone pad.
   The player bites down on this to apply force.

Assemble:
1. Insert the FSR-402 into the bite platform slot.
2. Route the FSR wires through the mouthpiece body.
3. Connect the silicone tube from the breath chamber to the PCB pressure
   sensor port.
4. Snap the mouthpiece onto the top of the instrument body.

## Step 9: Battery

1. Connect the 3.7 V 800 mAh LiPo to the BAT+/BAT- pads.
2. Secure it in the battery compartment with double-sided tape.
3. Verify the fuel gauge reads ~100% in the OLED display.

## Step 10: Final Assembly

1. 3D-print the instrument body shell (`docs/body.stl`).
2. Insert the PCB assembly into the body.
3. Mount the OLED on the front face (cutout).
4. Mount the speaker (front or bottom face).
5. Screw the body halves together with M2 screws.

## Step 11: Play!

1. Power on (press BOOT button for 1 second).
2. Wait for OLED to show patch name.
3. Tap BOOT to cycle patches.
4. Blow into the mouthpiece and press touch pads to play notes.
5. Bite for pitch bend; tilt for modulation.
6. Connect USB-C to a DAW → "Aero Reed MIDI" appears as a MIDI input.
7. Pair via Bluetooth → "Aero Reed BLE MIDI" appears.

### Playing Tips
- **Breath** controls volume/dynamics (like a real wind instrument).
- **Lip/bite** controls pitch bend (bite harder = higher pitch, like a
  saxophone reed).
- **Tilt** the instrument forward for modulation/vibrato depth (CC1).
- **Octave pads** (thumb, back) shift ±1 octave. Hold both for ±2.
- **ALT pad** (right pinky) adds a semitone (for trills and alternate
  fingerings).

Enjoy your Aero Reed!