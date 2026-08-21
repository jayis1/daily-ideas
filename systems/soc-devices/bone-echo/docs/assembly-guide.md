# Assembly Guide — Bone Echo

This guide walks through the assembly of the Bone Echo pocket QUS
bone densitometer, from PCB population to the heel coupling fixture.

## Tools Required

- Soldering iron (fine tip, 0.4 mm) or hot-air reflow station
- Tweezers (ESD-safe, fine tip)
- Magnification (loupe or microscope, 5–10×)
- Multimeter
- Torx screwdriver set (for the heel fixture)
- 3D printer (for the heel fixture and enclosure, optional)

## PCB Assembly

### 1. Power Section

1. **U2 (TP4056)** — Li-ion charger. SOIC-8. Solder first; it powers
   everything else. Verify 5 V on the USB-C input and 3.7–4.2 V on
   the BT1 pad.
2. **U3 (MCP1640B)** — 3.7→5 V boost. SOT-23-5. Verify 5.0 V output.
3. **U5 (AP2112-3.3)** — Digital 3.3 V LDO. SOT-23-5. Verify 3.3 V.
4. **U6 (LP5907-3.3)** — Analog 3.3 V LDO (low-noise). SOT-23-5.
   Verify 3.3 V on VDDA.
5. **U7 (REF3030)** — 3.0 V reference. SOT-23-3. Verify 3.000 V on
   VREF+.
6. **U4 (MAX668)** — 5→200 V HV boost. SO-8. **Do not power yet** —
   solder R1 (100 MΩ), R2 (1 MΩ), R10 (100 kΩ 2 W bleeder), C10
   (1 µF 250 V), C11 (10 nF 250 V) first. Verify HV rail = 200 V
   when PB4 is high; verify it discharges to <5 V within 500 ms of
   PB4 going low.

### 2. SoC

1. **U1 (STM32G474RET6)** — LQFP-64. Use hot-air reflow or fine-pitch
   soldering. Apply flux, align pin 1, reflow at 260 °C for 30 s.
2. Verify 170 MHz clock via SWD (PA13/PA14): connect ST-Link, read
   the SystemInit clock registers.
3. Program the bootloader (optional) or use SWD for flashing.

### 3. Analog RX Front End

1. **U8 (AD8331)** — LQFP-32. This is the noise-critical part. Keep
   input traces short. Solder the input coupling cap (C12, 1 nF C0G)
   as close to pin 4 (VIN) as possible.
2. **U10 (BPF)** — 4th-order Bessel band-pass 0.5–2 MHz. SOIC-8.
3. Verify RX chain: inject a 1 mV 1 MHz sine at the RX transducer
   pads; observe a clean 1 MHz at PA0 (ADC input) with ~30 dB gain
   at VGA midpoint.

### 4. TX Pulser

1. **U9 (TC6320)** — HV MOSFET pulser. SO-16. This switches 200 V
   into the TX transducer. Keep the HV trace (pin 1) short and wide
   (≥0.5 mm, 2 kV/mm breakdown for FR-4).
2. **QTX (TX transducer)** — 1 MHz PZT, 13 mm. Wire with short
   coax (RG-174, <10 cm). The transducer face will contact the
   patient's heel; ensure the transducer is electrically isolated
   from the patient (the coupling gel and transducer face provide
   this).
3. Verify: HRTIM trigger → 5-cycle 1 MHz burst at the TX transducer
   pads (use an oscilloscope with a 100× probe).

### 5. RX Transducer

1. **QRX (RX transducer)** — 1 MHz PZT, 13 mm. Matched pair with TX.
   Wire with short coax (RG-174, <10 cm).
2. Verify: place TX and RX transducers face-to-face (direct
   contact through gel); fire TX burst; observe a clean received
   signal at PA0 with ~20 dB SNR.

### 6. Memory / Display / BLE

1. **J2 (MicroSD)** — SPI1. Solder the socket.
2. **U14 (W25Q128)** — SPI flash, SOIC-8. For waveform buffering.
3. **U11 (SH1106 OLED)** — I2C1, address 0x3D. Module with 4-pin
   header (VCC, GND, SCL, SDA).
4. **U13 (ESP32-C3-MINI-1)** — BLE bridge. USART1, 921600 baud.
   Solder the module; verify it advertises as "Bone Echo" after
   power-on.

### 7. Sensors / UI

1. **U15 (DS18B20)** — 1-Wire temperature. TO-92. For phantom temp.
2. **U16 (BME280)** — Ambient temp/humidity/pressure (optional).
3. **SW1 (EC11)** — Rotary encoder.
4. **SW2-SW7** — Tactile buttons (Mode, Scan, ID, Age, Sex, Eth).
5. **RV1 (10 kΩ pot)** — Caliper position sensor. Panel-mount on
   the heel fixture.
6. **D1 (WS2812B)** — RGB status LED.

## Heel Coupling Fixture

The heel fixture is 3D-printed (PLA or PETG) and holds the two
transducers in a spring-loaded caliper:

```
       ┌─────────────────────────┐
       │    Heel Fixture (top)    │
       │  ┌─────┐    ┌─────┐    │
       │  │ TX  │    │ RX  │    │
       │  │xdr  │    │xdr  │    │
       │  └──┬──┘    └──┬──┘    │
       │     │  spring  │       │
       │     │  ◀────▶  │       │
       │     │           │       │
       │  ┌──┴───────────┴──┐   │
       │  │   heel slot      │   │
       │  │  (calcaneus)     │   │
       │  └──────────────────┘   │
       └─────────────────────────┘
```

1. Print the two caliper jaws (left holds TX, right holds RX).
2. Mount the transducers in the jaws with the active face flush.
3. Install the compression spring (10 N, 20 mm travel).
4. Mount the 10 kΩ potentiometer (RV1) on the caliper pivot so the
   wiper tracks the jaw opening (0–80 mm).
5. Wire the transducers and potentiometer to the PCB via a short
   ribbon cable (<15 cm).
6. Install the reed switch (PB12) on the fixture so it detects the
   phantom's embedded magnet.

## HV Safety Verification

**Before first use**, verify the HV safety:

1. Arm HV (PB4 high), measure the HV rail with a high-voltage probe:
   must be 200 ± 20 V.
2. Disarm HV (PB4 low), measure the HV rail: must be <5 V within
   500 ms (100 kΩ bleeder, τ = 100 ms).
3. Verify the firmware disarms HV automatically if the device is
   idle for >2 s.
4. Verify the mechanical interlock: the transducer faces cannot be
   touched with the HV armed (spring-cover blocks access).

## First Scan

1. Insert the acrylic phantom between the transducers (reed switch
   detects it). Press SCAN. The device calibrates: measures SOS
   (should be ~2700 m/s) and captures the reference FFT.
2. Remove the phantom, apply gel to both transducer faces.
3. Place your heel in the fixture; the caliper reads the width.
4. Press SCAN. The OLED shows SOS, BUA, SI, T-score, Z-score, and
   the WHO classification.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No signal (SOS = 0) | Poor coupling / dry gel | Reapply ultrasonic gel |
| SOS out of range | Heel width wrong / caliper miscal | Recalibrate caliper (closed + 80 mm) |
| BUA R² < 0.75 | Poor coupling / air bubble | Reapply gel, ensure full contact |
| HV FAULT | HV not charging / bleeder stuck | Check MAX668, TC6320, R10 |
| Battery low | 18650 depleted | Charge via USB-C |
| OLED blank | I2C address wrong / wiring | Check 0x3D address, SDA/SCL |

## Calibration Schedule

- **Per session**: phantom reference (once per day or per session).
- **Per session**: caliper zero + full calibration (if moved).
- **Monthly**: HV pulse amplitude verification (200 ± 20 V).
- **Yearly**: full factory calibration (send to manufacturer or
  use the included `scripts/phantom_cal.py`).