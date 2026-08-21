# Tremor Tile — Assembly Guide

## Overview

The Tremor Tile is a credit-card-sized structural vibration monitor. This guide covers PCB assembly, component placement, and first-time setup.

## PCB Specifications

| Parameter | Value |
|-----------|-------|
| Dimensions | 85mm × 54mm |
| Layers | 4 |
| Thickness | 1.6mm |
| Material | FR4 |
| Finish | ENIG (Electroless Nickel Immersion Gold) |
| Min trace width | 0.15mm |
| Min via diameter | 0.3mm |
| Impedance control | Yes (50Ω for LoRa antenna) |

## Layer Stackup

```
L1 (Top): Signal + Components
L2: GND Plane
L3: 3V3 Power Plane
L4 (Bottom): Signal + LoRa Antenna
```

## Assembly Order

### Step 1: Solder Paste Application

1. Order a stainless steel stencil (0.1mm thickness) from JLCPCB or PCBWay
2. Apply solder paste using the stencil
3. Inspect paste deposits under magnification — especially the RP2040 QFN-56 and ADXL355 LGA-14

### Step 2: Component Placement (Top Side)

Place components in this order (largest to smallest):

| Order | Reference | Component | Package | Notes |
|-------|-----------|-----------|---------|-------|
| 1 | U1 | SPV1040TR | TSSOP-8 | Solar MPPT, orient pin 1 |
| 2 | U2 | TP4056 | SOP-8 | Battery charger |
| 3 | U3 | RT9013-33GB | SOT-223 | 3.3V LDO |
| 4 | U4 | RP2040 | QFN-56 7×7 | Align center pad, use stencil |
| 5 | U5 | ADXL355 | LGA-14 6×3 | **Critical: centered on PCB** |
| 6 | U6 | SX1262IMLTRT | QFN-24 4×4 | Near antenna edge |
| 7 | U7 | BME280 | LGA-8 2.5×2.5 | Corner placement |
| 8 | U8 | DS3231SN# | SOIC-16 | RTC module |
| 9 | U9 | W25Q128JVSIQ | SOIC-8 | QSPI flash |
| 10 | D1 | SK6812MINI | 3535 | Status LED |
| 11 | BZ1 | CMB-6542-100 | SMD buzzer | Piezo buzzer |
| 12 | J1 | USB-C 16-pin | SMD | Power + data |
| 13 | BT1 | CR1220 holder | SMD | RTC backup battery |
| 14 | SW1 | Reed switch | SMD | Tamper detection |
| 15 | All passives | R/C/L | 0402 | Decoupling, pullups |

### Step 3: Bottom Side Components

| Order | Reference | Component | Notes |
|-------|-----------|-----------|-------|
| 1 | ANT1 | PCB trace antenna | 868/915MHz meandered F-antenna |
| 2 | M1, M2 | N35 neodymium magnets | 6×3mm discs, press-fit |
| 3 | SOLAR1 | PowerFilm MPT3.6-75 | Solder tabs to pads |

### Step 4: Reflow Soldering

1. Use a reflow oven or hot plate
2. Profile: 150°C preheat → 180°C soak → 230°C peak → cool
3. Total cycle time: 4-6 minutes
4. **Critical:** Do NOT exceed 250°C (risk to BME280 and ADXL355)

### Step 5: Hand Soldering (Through-Hole)

- Solder the LiFePO4 battery leads to the PCB pads
- Solder the solar cell wires (if using external panel instead of on-board)

### Step 6: Inspection

1. Check all solder joints under 10× magnification
2. Pay special attention to:
   - RP2040 QFN-56 center pad (hidden under chip)
   - ADXL355 LGA-14 (no leads visible — use X-ray if available)
   - SX1262 QFN-24 ground pad
3. Verify no solder bridges on fine-pitch components
4. Check all 0402 passives for tombstoning

## First-Time Setup

### 1. Install CR1220 Battery

Insert a CR1220 coin cell into the DS3231 holder. This keeps the RTC running when main power is off.

### 2. Connect LiFePO4 Battery

Solder the LiFePO4 1000mAh pouch cell to the battery pads:
- **Red** → BAT+ pad
- **Black** → BAT- pad

### 3. Flash Firmware

1. Hold the BOOT button (GPIO20)
2. Connect USB-C to your computer
3. The RP2040 will appear as a USB mass storage device
4. Copy `tremor_tile.uf2` to the device
5. The device will automatically restart

### 4. Verify Operation

Connect via USB-C and open a serial terminal (115200 baud, 8N1):

```
=== Tremor Tile v1.0 ===
RP2040 dual-core structural vibration monitor
ADXL355: Detected (AD=0xAD, MST=0x1D, PART=0xED)
SX1262: Initialized — 868.0 MHz, SF7, BW=125kHz, +22dBm
BME280: Initialized at 0x77
DS3231: Initialized at 0x68
Anomaly: Initialized — learning mode active (24h baseline)
Core 0: Initialization complete, entering main loop
Core 1: Signal processing starting
```

### 5. Mounting

**Steel surfaces:** Place the device with the neodymium magnets facing the surface. The magnets will snap into place.

**Concrete/wood:** Use the M3 bolt holes or industrial double-sided tape (3M VHB recommended).

**Important:** Mount the device in the location where it will operate permanently BEFORE starting the baseline learning period. The baseline is position-specific.

### 6. Baseline Learning

The device automatically starts learning the baseline when first powered on. The SK6812 LED will show **cyan** during the learning period.

Wait at least 24 hours for the baseline to be established. The LED will turn **green** when monitoring mode begins.

### 7. Configure LoRa Gateway

Set up a LoRa gateway (e.g., RAK7258, Dragino LPS8) on the same frequency (868 MHz EU or 915 MHz US) and configure MQTT forwarding to your server.

## Conformal Coating

For outdoor or industrial deployment:

1. Apply conformal coating (MG Chemicals 422B silicone) to the entire PCB
2. **Exclude:** USB-C connector, antenna area, solar cell surface
3. **Exclude:** ADXL355 sensor opening (use masking tape)
4. Cure for 24 hours before deployment

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| No serial output | USB CDC not enumerated | Check USB-C cable (data + power), try different port |
| ADXL355 not detected | SPI bus issue | Check SPI0 wiring, verify CS pin, check 0x00/0x01 register reads |
| SX1262 BUSY timeout | Power or SPI issue | Verify 3.3V supply, check SPI1 wiring, check TCXO enable pin |
| No LoRa packets | Wrong frequency or SF | Verify gateway matches device config (868 MHz, SF7) |
| Battery draining fast | Solar panel disconnected | Check solar panel wiring, verify SPV1040 MPPT operation |
| Frequent false alerts | Baseline too short | Reset baseline and run 24h learning period in final location |
| LED not working | SK6812MINI timing | Verify 800kHz bit-bang timing, check 5V data level |

## Safety

- **LiFePO4 batteries are safe** but should still be protected from physical damage
- **Do not expose to water** unless conformal coated and enclosed
- **USB-C is for charging and programming only** — do not connect to non-standard power sources
- **The ADXL355 is shock-sensitive** — do not drop the device
- **LoRa frequency regulations vary** — ensure compliance with your country's ISM band rules