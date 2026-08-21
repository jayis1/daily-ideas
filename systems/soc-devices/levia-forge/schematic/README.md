# Levia Forge — Schematic Notes

## Overview

The Levia Forge schematic captures the full electrical design of the
72-channel acoustic levitation controller. Due to the repetitive nature
of the transducer driver circuit (72 identical channels), the schematic
is organized into hierarchical sheets.

## Sheet Organization

### Sheet 1: RP2040 + Flash
- RP2040 (QFN-56) with 12 MHz crystal, W25Q128JVSIQ (16 MB SPI flash)
- USB-C connector with 27Ω series resistors and 1MΩ pulldown on CC
- Decoupling: 100nF on each VCC pin, 10µF bulk
- Boot button on RUN (reset) and BOOTSEL

### Sheet 2: Power Supply
- Input: 2× 18650 LiPo (7.4V nominal, 6.0–8.4V range)
- TP4056: USB-C charging (1A charge current, 4.2V/cell)
- DW01 + FS8205A: Battery protection (overcharge/overdischarge/short)
- MCP1603T-3.3: Buck converter 7.4V → 3.3V / 500 mA
  - Inductor: 4.7µH, 1A
  - Input cap: 10µF, Output cap: 10µF
- TPS61023: Boost converter 7.4V → 10V / 1.5A
  - Inductor: 10µH, 2A
  - Input cap: 10µF, Output cap: 22µF
  - Feedback divider: 1MΩ (top) + 118kΩ (bottom) → Vout = 1.256V × (1 + 1M/118k) ≈ 10.05V
- AP2112K-5.0: LDO 5V / 300 mA (for VL53L0X and SD card level shifter)

### Sheet 3: Phase Shift Register Chain
- 9× 74HC595 (SOIC-16), daisy-chained
  - SER (pin 14) of chip 1 ← RP2040 GP0 (DATA)
  - Q7' (pin 9) of chip N → SER of chip N+1
  - SRCLK (pin 11) all tied to RP2040 GP1 (CLOCK, 10.24 MHz)
  - RCLK (pin 12) all tied to RP2040 GP2 (LATCH, 40 kHz via PWM)
  - OE (pin 13) all tied to RP2040 GP3 (BLANK, active low)
  - SRCLR (pin 10) tied to 3.3V
  - 100nF decoupling on each VCC pin
  - 10kΩ pull-up on OE (default blanked on power-up)

### Sheet 4: Transducer Driver Array (72 channels)
Each channel:
```
74HC595 Q[i] ── 1kΩ ──┬── MMBT3904 base (NPN)
                      │
                      └── MMBT3906 base (PNP)

Collector of MMBT3904 → +10V
Emitter of MMBT3904 ────┐
                        ├──→ Transducer (+)
Emitter of MMBT3906 ────┘
Collector of MMBT3906 → GND

Transducer (−) → GND
```

When 74HC595 output = HIGH: NPN on, transducer sees +10V
When 74HC595 output = LOW: PNP on, transducer sees 0V
Result: 10 Vpp square wave at 40 kHz, phase-controlled

### Sheet 5: ESP32-C3 BLE Bridge
- ESP32-C3-WROOM-02 module
- UART: GPIO2 (RX ← RP2040 GP4), GPIO3 (TX → RP2040 GP5)
- EN pin ← RP2040 GP21 (enable control)
- BOOT0 ← RP2040 GP20 (for OTA)
- LED on GPIO8 (BLE connection status)
- 100nF on VCC, 10µF bulk, 32kHz crystal (internal RTC)
- Antenna: PCB trace (module-integrated)

### Sheet 6: Peripherals
- SSD1306 OLED (128×64, I2C): I2C1 (GP6/GP7), 0x3C
  - 4.7kΩ pull-ups on SDA/SCL
- VL53L0X ToF sensor: I2C0 (GP12/GP13), 0x29
  - 4.7kΩ pull-ups on SDA/SCL
  - XSHUT pin to RP2040 GPIO (for reset)
  - 2.8V regulator (optional, can run on 3.3V with VDDA)
- microSD socket: SPI0 (GP8-GP11)
  - Card detect on GP18
  - 10kΩ pull-up on CS
- Analog joystick: GP26 (ADC0, X), GP27 (ADC1, Y)
  - 10kΩ potentiometers, 3.3V supply
- Rotary encoder: GP14 (A), GP15 (B), GP16 (button)
  - 10kΩ pull-ups, 0.1µF hardware debounce caps
- Buttons: GP15 (MODE), GP16 (RELEASE)
  - 10kΩ pull-ups, 0.1µF debounce caps
- Reed switch: GP19, 10kΩ pull-up (magnet on lid)
- LSM6DSO IMU: I2C (shared with VL53L0X or separate)
  - INT1 → GP22 (tilt interrupt)

## Power Budget

| Rail | Voltage | Current | Components |
|------|---------|---------|------------|
| 3.3V | 3.3V | ~200 mA | RP2040 (40mA), 74HC595×9 (20mA), ESP32-C3 (80mA), OLED (20mA), SD (40mA) |
| 10V  | 10V  | ~400 mA peak | 72 transducers × 5 mA = 360 mA |
| 5V   | 5V   | ~50 mA | VL53L0X (15mA), SD level shifter, misc |
| Total from battery | 7.4V | ~700 mA peak | ~5.2W peak, ~2.5W average |

Battery life: 2500 mAh / 700 mA ≈ 3.6 hours (full power)
            : 2500 mAh / 350 mA ≈ 7.1 hours (eco mode, 50% power)

## PCB Layout Notes

- 4-layer board: Top (signals), GND, 3.3V, Bottom (signals + power)
- 10V rail: wide traces (≥0.5mm) to handle 400 mA with minimal drop
- 72 driver channels: place BJT pairs close to 74HC595 outputs
- Transducer wires: 30 AWG, equal length (±5mm per array)
- Array connector: 2× 36-pin headers (0.1" pitch) on top edge for
  top and bottom arrays
- VL53L0X: mounted on a small breakout board above the top array,
  connected via 4-wire ribbon cable (I2C + power)
- Keep PIO clock trace (GP1) short and away from analog signals