# Schematic — Bone Echo

This folder contains the KiCad project files for the Bone Echo pocket
quantitative ultrasound bone densitometer.

## Files

- `bone_echo.kicad_pro` — KiCad project file
- `bone_echo.kicad_sch` — schematic (top sheet)
- `bone_echo.kicad_pcb` — PCB layout (placeholder, 4-layer, 90×70 mm)

## Schematic Overview

The schematic is organized into these sections:

1. **Power** — USB-C 5 V → TP4056 charger → 18650 cell → MCP1640B
   boost (3.7→5 V) → AP2112-3.3 (digital) + LP5907-3.3 (analog) +
   REF3030 (3.0 V reference). A MAX668 boost generates the 200 V HV
   rail for the transmitter pulser (gated by PB4/PB5).

2. **SoC** — STM32G474RET6 (LQFP64). HRTIM drives the TX pulse
   trigger; ADC1 digitizes the RX signal at 3.6 Msps (ToF) or
   oversampled 16-bit @ 28 ksps (BUA spectral). CORDIC accelerates
   the FFT; DAC1 generates the TGC ramp for the AD8331 VGA.

3. **TX path** — HRTIM trigger → TC6320 HV MOSFET pulser → 200 V
   5-cycle 1 MHz burst → 10 nF 250 V coupling cap → 1 MHz PZT
   transducer. A 100:1 voltage divider (R1/R2) feeds PA3 for HV
   verification. A 100 kΩ 2 W bleeder (R10) discharges the HV rail
   within 10 ms when PB5 goes low.

4. **RX path** — 1 MHz PZT transducer → 1 nF C0G coupling cap →
   4th-order Bessel BPF (0.5–2 MHz) → AD8331 VGA (0–48 dB, TGC ramp
   from DAC1) → STM32 ADC1 (PA0).

5. **Transducers** — matched pair of 1 MHz longitudinal PZT
   transducers (13 mm active aperture) mounted in the heel coupling
   fixture. Optional SMA connectors (J3/J4) allow external
   transducers for non-heel applications.

6. **Heel caliper** — 10 kΩ linear potentiometer (RV1) on the
   spring-loaded caliper; PA5 reads the wiper → heel width d (mm).

7. **Phantom** — 25 mm acrylic block (PH1) with a reed switch
   (PB12) for auto-detection. Used for SOS calibration (2700 m/s)
   and BUA reference FFT.

8. **Sensors** — DS18B20 (phantom temp, 1-Wire on PC15) + BME280
   (ambient temp/humidity/pressure, optional, on I2C1).

9. **Memory / logging** — microSD (SPI1) for CSV + raw waveform
   binary; W25Q128 (SPI) for waveform buffering.

10. **Display** — SH1106 1.3" 128×64 OLED (I2C1, 0x3D).

11. **BLE bridge** — ESP32-C3-MINI-1 (USART1, 921600 baud) for BLE
    5 + Wi-Fi 4 streaming of waveforms + results.

12. **UI** — EC11 rotary encoder + 6 tactile buttons (Mode, Scan,
    ID, Age, Sex, Eth) + WS2812B RGB status LED.

## HV Safety

The 200 V TX rail is the highest-voltage node in the device. Safety
measures:

- **Gated arming** — PB4 (HV_ENABLE) must be high to arm the TC6320.
  The firmware only sets this during an active scan.
- **Active discharge** — PB5 (HV_DISCHARGE) controls the MAX668
  charge pump. When low, the 100 kΩ 2 W bleeder (R10) discharges
  the 1 µF 250 V reservoir cap (C10) to GND: τ = 100k × 1µ = 100 ms
  → 200 V → 0 V in <500 ms (5τ). The firmware drives PB5 low at
  scan completion.
- **Mechanical interlock** — the heel fixture spring-cover
  physically prevents touching the transducer faces with the HV
  armed.
- **Pulse duration** — the TX burst is 5 cycles × 1 µs = 5 µs, not
  a sustained voltage. The duty cycle is <0.1% (5 µs burst, >5 s
  between scans).

## Grounding

- **AGND / DGND split** — analog ground (AD8331, BPF, RX transducer
  return, REF3030) ties to AGND; digital ground (STM32, ESP32-C3,
  OLED, SD) ties to DGND. They meet at a single star point under
  the STM32.
- **HV return** — the TC6320 pulser return is a separate net that
  ties to AGND at the star point only, to keep HV switching currents
  out of the RX signal ground.

## Build Notes

- The 200 V HV section requires a 2-layer minimum with a solid
  ground plane on layer 2; keep the HV trace short and wide (≥0.5 mm,
  2 kV/mm breakdown for FR-4 → 0.5 mm gives 1 kV margin).
- The AD8331 is the noise-critical part; keep its input traces
  short, shielded, and away from the HV switching node.
- The transducer cables (TX/RX) should be low-loss coax (RG-174,
  50 Ω, <30 cm) to minimize capacitive loading.
- The caliper potentiometer (RV1) is a panel-mount part; wire with
  a twisted pair to PA5 to reject noise.

## Opening in KiCad

```
kicad bone_echo.kicad_pro
```

Requires KiCad 7.0+ (uses the 20231120 file format).