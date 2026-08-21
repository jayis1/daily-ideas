# Flux Ring — Assembly Guide

## Overview

This guide walks you through assembling the Flux Ring — a finger-worn magnetic field explorer. The assembly involves soldering SMD components onto a 4-layer PCB, attaching a flexible OLED display, mounting the vibration motor, and connecting the lithium-polymer battery.

## Tools Required

| Tool | Purpose |
|------|---------|
| Soldering iron (fine tip, temperature-controlled) | SMD soldering |
| Solder paste + stencil (optional but recommended) | Reflow soldering |
| Hot air rework station | QFN/LGA packages |
| Tweezers (ESD-safe, fine tip) | Component placement |
| Multimeter | Continuity/voltage checks |
| USB-C cable | Power + programming |
| Magnifying loupe or microscope | Inspection |
| 3D printer (optional) | TPU ring band |

## PCB Specification

- **Size:** 22mm × 18mm × 1.2mm
- **Layers:** 4 (signal, ground, power, signal)
- **Material:** FR4, ENIG finish
- **Minimum feature:** 0.1mm trace/space
- **Impedance control:** Not required (no high-speed signals)

Order from JLCPCB or similar with the KiCad gerber files in `schematic/`.

## Assembly Order (Bottom-Up)

### Step 1: Passives (0402 R/C)

Place all 0402 passive components first:
- I2C pull-up resistors (6× 4.7kΩ) on SDA, SCL lines for each I2C device group
- Decoupling capacitors (8× 100nF) — one per power pin of each IC
- Bulk capacitors (3× 10µF) — near VDD input
- Voltage divider resistors (2× 100kΩ) — battery monitoring
- USB series resistor (1× 22Ω)
- LED series resistor (1× 1kΩ)

**Tip:** Use solder paste + stencil for the 0402 components. A microscope is essential.

### Step 2: nRF52840-QIAA (QFN-48)

This is the most challenging component:
1. Apply solder paste to all 48 pads + center thermal pad
2. Align the IC using the pin-1 marker (dot in corner)
3. Place with tweezers, then reflow
4. Inspect all sides for solder bridges
5. Verify with continuity test: VDD to GND should NOT be shorted

**Important:** The thermal pad must be connected to GND. Use vias to the ground plane.

### Step 3: MMC5983MA (LGA-16)

The magnetometer is the most critical sensor:
1. Place on the **top face** of the PCB (closest to the magnetic field)
2. Apply minimal solder paste — the LGA pads are small
3. Align carefully — there's a dot marking pin 1
4. Reflow with low temperature (avoid overheating the AMR elements)
5. Keep ferrous materials away during soldering (no steel tweezers near this chip!)

**Note:** The MMC5983MA is sensitive to thermal stress. Do not exceed 260°C for more than 10 seconds.

### Step 4: LIS2DH12 (LGA-12)

1. Apply solder paste
2. Place adjacent to the MMC5983MA on the top face
3. Reflow
4. The accelerometer should be as close as possible to the magnetometer for accurate tilt compensation

### Step 5: MS5837-02BA (QFN-8)

1. Apply solder paste to the 8 pads + center pad
2. Place on top face near the other sensors
3. The barometer port should face outward (exposed to ambient air)

### Step 6: DRV2603L (WSON-8)

1. Apply solder paste
2. Place on the bottom face of the PCB
3. The exposed pad must be soldered to GND

### Step 7: W25Q16JVSIQ (SOIC-8)

1. This is the easiest package — standard SOIC
2. Place on the bottom face
3. Solder all 8 pins

### Step 8: MCP73831 + TLV73333 (SOT-23-5)

1. Place both on the bottom face near the USB-C connector
2. The MCP73831 handles battery charging
3. The TLV73333 provides 3.3V regulation
4. Check the pin-1 markers before soldering

### Step 9: USB-C Receptacle

1. Place the 16-pin SMD USB-C receptacle at the PCB edge
2. This is a fine-pitch component — use solder paste
3. After reflow, verify all 16 pins are soldered
4. Check for shorts between adjacent pins with a multimeter

### Step 10: WS2812B-2020

1. Place on the outer face (visible to others)
2. The data input pad faces toward the nRF52840
3. Solder carefully — these are tiny (2mm × 2mm)

### Step 11: SSD1306 OLED Display

The 32×64 monochrome OLED is mounted on a flexible PCB:
1. The flex PCB attaches to the inner face of the ring (visible when you tilt your hand)
2. Solder the I2C + power connections (4 wires: VDD, GND, SDA, SCL)
3. Use a thin flexible cable or direct FPC connection
4. Secure the display with double-sided tape or epoxy

### Step 12: Vibration Motor

1. The 6×2.7mm coin ERM motor sits in a pocket on the top face
2. Solder the two motor leads to the DRV2603L output pads
3. Secure with a small amount of epoxy (don't glue the motor body — it needs to vibrate!)

### Step 13: Battery

1. The 302020 LiPo pouch battery (200mAh) sits on a flex PCB tongue
2. Solder the + and - leads to the MCP73831 BAT and GND pads
3. **CRITICAL:** Observe polarity! Reverse polarity will destroy the MCP73831
4. The battery should be insulated with Kapton tape
5. Route the flex PCB tongue to wrap around the finger

### Step 14: Capacitive Touch Pad

1. The touch pad is a copper trace on the bottom of the PCB
2. No component to solder — it's part of the PCB layout
3. Cover with a thin layer of solder mask (not too thick, or touch sensitivity drops)

## Post-Assembly Checklist

- [ ] All ICs oriented correctly (pin-1 markers aligned)
- [ ] No solder bridges between fine-pitch pads
- [ ] VDD to GND continuity: should be >100Ω (not shorted)
- [ ] USB-C port: no shorts between D+/D-, VBUS/GND
- [ ] Battery polarity correct
- [ ] All I2C pull-ups present (4.7kΩ)
- [ ] Decoupling caps on all IC VDD pins
- [ ] Motor leads not shorted together
- [ ] OLED flex cable securely attached
- [ ] No visible flux residue near sensors

## First Power-On

1. **Do not** connect the battery yet
2. Connect USB-C to a 5V source
3. Measure VDD (3.3V) with a multimeter
4. If VDD is correct, disconnect USB and attach the battery
5. Connect USB again — the MCP73831 should begin charging
6. Check the CHARGE_STAT LED (red while charging)
7. Flash the firmware via USB-C UART

## Firmware Flashing

```bash
# Install nRF Connect SDK
# Build and flash
cd firmware
west build -b nrf52840dk_nrf52840
west flash

# Or via USB-C DFU
nrfutil dfu serial -pkg build/zephyr/app_update.bin -p /dev/ttyACM0
```

## 3D-Printed Ring Band (Optional)

The TPU ring band provides comfort and adjustable sizing:

1. Print `hardware/ring_band_S.stl`, `_M.stl`, or `_L.stl` in TPU (95A shore)
2. The band clips onto the PCB edges
3. The battery flex tongue threads through the band
4. Select size based on your finger circumference:
   - S: 50-55mm
   - M: 55-60mm
   - L: 60-65mm

## Troubleshooting

| Symptom | Possible Cause | Fix |
|---------|---------------|-----|
| No power (no LED) | USB not connected, battery dead, LDO failed | Check VBUS, measure VDD |
| OLED blank | I2C not connected, OLED DOFF | Check I2C pull-ups, send display-on command |
| Magnetometer reads zero | MMC5983MA not responding | Check I2C address (0x30), verify WHO_AM_I |
| Compass always points wrong | Not calibrated | Run figure-8 calibration |
| Motor doesn't vibrate | DRV2603L not initialized | Check I2C (0x5A), check motor leads |
| BLE not discoverable | Firmware not flashed, antenna issue | Check firmware, verify 32MHz crystal |
| Battery drains fast | High current draw | Check sleep modes, reduce sample rate |
| LED color wrong | WS2812B timing issue | Check GPIO5, verify bit-bang timing |

---

*See also: [Calibration Guide](calibration_guide.md) | [API Reference](api_reference.md)*