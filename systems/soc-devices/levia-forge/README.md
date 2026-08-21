# Levia Forge — Pocket Acoustic Levitation Manipulator

> A battery-powered, pocket-sized acoustic levitation platform that
> traps and manipulates small objects (styrofoam beads, liquid
> droplets, solder balls, insects) in mid-air using a phased array of
> 72 ultrasonic transducers with per-element phase control via
> RP2040 PIO + I2S DMA, real-time 3D trap positioning via analog
> joystick and BLE app, particle height feedback from a VL53L0X
> time-of-flight sensor, OLED status display, and safety interlock —
> bringing $2k–$15k lab acoustic levitators (UltraHaptics,
> SonicSurface, TinyLev) down to ~$61 and coffee-mug size.

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         LEVIA FORGE                                   │
 │          Pocket Acoustic Levitation Manipulator                       │
 │                                                                       │
 │  ┌──────────────────────────────────────────────────────────┐        │
 │  │  TOP ARRAY (36× MA40S4S, 40 kHz, hemispherical)         │        │
 │  │  ┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐                              │        │
 │  │  │T1││T2││T3││T4││T5││T6│   ← 6×6 = 36 top elements    │        │
 │  │  └──┘└──┘└──┘└──┘└──┘└──┘     arranged on a curve      │        │
 │  │  ...                                                   │        │
 │  └────────────────────┬───────────────────────────────────┘        │
 │                       │ ◄── standing wave trap zone                 │
 │                  ┌────┴────┐                                        │
 │                  │  ◉ ◉   │  ← levitated particle (bead/droplet)   │
 │                  └────┬────┘                                        │
 │                       │                                              │
 │  ┌────────────────────┴───────────────────────────────────┐        │
 │  │  BOTTOM ARRAY (36× MA40S4S, 40 kHz, hemispherical)    │        │
 │  │  ┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐                              │        │
 │  │  │B1││B2││B3││B4││B5││B6│   ← 6×6 = 36 bottom elements│        │
 │  │  └──┘└──┘└──┘└──┘└──┘└──┘                             │        │
 │  │  ...                                                   │        │
 │  └───────────────────────────────────────────────────────┘        │
 │                                                                       │
 │  Phase engine:  RP2040 PIO @ 10.24 MHz serial                        │
 │                 9× 74HC595 (72-bit frame, 256 phase steps)           │
 │                 72× TC4427 half-bridges → 10 Vpp to transducers      │
 │                                                                       │
 │  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐           │
 │  │ Joystick     │───▶│  RP2040      │───▶│ 72× phase      │           │
 │  │ 2-axis + ENC │    │  Dual-core   │    │ computation    │           │
 │  │ + buttons    │    │  133 MHz     │    │ (Helmholtz)    │           │
 │  └─────────────┘    │              │    └───────┬────────┘           │
 │                     │  ┌────────┐  │            │                     │
 │                     │  │ PIO    │  │     ┌──────┴──────┐              │
 │                     │  │ 10.24  │  │     │ 9× 74HC595  │              │
 │                     │  │ MHz    │──┼────▶│ → 72-bit    │              │
 │                     │  │ serial │  │     │ parallel    │              │
 │                     │  └────────┘  │     └──────┬──────┘              │
 │                     │              │            │                     │
 │                     │  ┌────────┐  │     ┌──────┴──────┐              │
 │                     │  │ VL53L0X│  │     │ 72× TC4427  │              │
 │                     │  │ ToF    │  │     │ half-bridge │              │
 │                     │  │ height │  │     │ → 10 Vpp    │              │
 │                     │  └────────┘  │     └─────────────┘              │
 │                     └──┬────┬────┬─┘                                  │
 │                        │    │    │                                     │
 │                   ┌────┘    │    └──────┐                              │
 │                   ▼         ▼           ▼                              │
 │              ┌────────┐ ┌──────┐  ┌──────────┐                         │
 │              │OLED    │ │SD    │  │ESP32-C3  │                         │
 │              │128×64  │ │log   │  │BLE app   │                         │
 │              │status  │ │CSV   │  │control   │                         │
 │              └────────┘ └──────┘  └──────────┘                         │
 │                                                                       │
 │  Power: 2× 18650 LiPo (7.4V) → 5V/3.3V buck + 10V boost for drivers  │
 │  Safety: reed switch interlock + tilt sensor + IWDG                   │
 └──────────────────────────────────────────────────────────────────────┘
```

## What It Does

Levia Forge is a complete acoustic levitation platform that fits on a
desktop (or in a large pocket). On power-up, the device:

1. **Initializes the phased array** — the RP2040 configures a PIO state
   machine to generate a 10.24 MHz serial bitstream (256× oversampling
   of the 40 kHz carrier). Two DMA channels feed a 2304-byte circular
   buffer (72 bits × 256 phase steps) through the PIO FIFO
   continuously. Nine daisy-chained 74HC595 shift registers convert
   the serial stream to 72 parallel outputs, latched at 40 kHz. Each
   output drives a TC4427 MOSFET half-bridge that delivers 10 Vpp to
   one ultrasonic transducer.

2. **Computes the trap focus** — for a desired focal point **p** = (x,
   y, z) in the levitation cavity, Core 0 computes the phase for each
   of the 72 transducers:

   ```
   φᵢ = (2π · f / c) · |tᵢ − p|
   ```

   where **tᵢ** is the 3D position of transducer *i*, *f* = 40 kHz, *c*
   = 343 m/s. The phase is quantized to one of 256 steps and packed
   into the DMA buffer as a bit pattern (first half of the 256-step
   window = HIGH, second half = LOW for a square wave at phase φᵢ).

3. **Creates a standing wave trap** — all 72 transducers fire
   simultaneously with phases chosen to constructively interfere at
   the focal point and destructively interfere elsewhere, creating a
   pressure node (trap) where an object can be suspended against
   gravity. The trap is typically 2–4 mm in diameter, holding objects
   up to ~3 mm in size and ~10 mg in weight.

4. **Moves the trap in 3D** — an analog joystick (2-axis) moves the
   focal point in X/Y; a rotary encoder moves it in Z (height). The
   phase buffer is recomputed at 50 Hz (20 ms latency) for smooth
   motion. The focal point can traverse a ±15 mm × ±15 mm × 20 mm
   working volume.

5. **Senses the levitated object** — a VL53L0X time-of-flight laser
   distance sensor (mounted on the top array, pointing down) measures
   the distance to the levitated particle at 20 Hz. If the particle
   drifts, the firmware can auto-correct the Z focus. If no object is
   detected within the expected range, the device enters "search" mode
   (small oscillating focus to capture a fallen particle).

6. **Displays status** — a 128×64 SSD1306 OLED shows the current trap
   position (X, Y, Z in mm), particle detected (yes/no + height), array
   power (mW), phase pattern mode (point/line/vortex/transport), and
   battery voltage.

7. **Streams over BLE** — an ESP32-C3 companion module provides BLE
   connectivity. A phone app can:
   - Set the trap position (X, Y, Z sliders)
   - Select phase patterns (single trap, twin trap, vortex, bending,
     transport conveyor)
   - Monitor particle status
   - Log session data to the phone

8. **Logs to SD card** — a microSD slot on the RP2040 SPI bus records
   trap position, phase pattern, particle height, power, and timestamps
   at 10 Hz for experiment reproducibility.

## Phase Pattern Modes

Levia Forge supports several advanced acoustic manipulation patterns
beyond a simple single-point trap:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Point** | Single focused trap at (x, y, z) | Basic levitation |
| **Twin** | Two traps separated by Δx | Holding two particles |
| **Vortex** | Azimuthal phase gradient (topological charge ℓ=1) | Particle rotation / spin |
| **Bottle** | Hollow trap (surrounding pressure) | Confined trapping |
| **Bending** | Linear phase gradient along one axis | Particle transport |
| **Transport** | Moving line trap (conveyor) | Move particles across stage |

## Applications

- **Contactless sample handling** — move liquid droplets, powder
  samples, or biological specimens without contamination
- **Micro-assembly** — position solder balls, SMD components, or
  micro-mechanical parts without tweezers
- **Pharmaceutical research** — containerless crystal growth, study
  of amorphous solid formation without wall nucleation
- **Biology** — levitate and study insects, cells in droplets, or
  small organisms without substrate contact
- **Education** — demonstrate acoustic radiation force, standing
  waves, and wave physics interactively
- **Materials science** — containerless melting/solidification of
  low-melting-point alloys (with heated gas environment)
- **Food science** — droplet mixing, coalescence studies

## Block Diagram

```
                    ┌─────────────────────────────────────┐
                    │         POWER ARCHITECTURE           │
                    │                                      │
   2× 18650 ──┬────▶│ 7.4V ──┬── MCP1603T-3.3 ──▶ 3.3V    │
   (7.4V)     │     │         │   (logic, MCU, OLED)       │
              │     │         │                             │
              │     │         ├── TPS61023 ──▶ 10V          │
              │     │         │   (boost, transducer drive) │
              │     │         │                             │
              │     │         └── AP2112K-5.0 ──▶ 5V       │
              │     │              (ToF, SD, ESP32-C3)     │
              │     └──────────────────────────────────────┘
              │
              ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                      RP2040 (Core 0)                             │
 │                                                                   │
 │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
 │  │ Joystick  │  │ Rotary   │  │ 2× Button│  │ VL53L0X  │        │
 │  │ ADC0/ADC1 │  │ Encoder  │  │ GPIO     │  │ I2C0     │        │
 │  │ (X/Y)     │  │ PIO1 SM0 │  │          │  │ (height) │        │
 │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
 │       │              │              │              │              │
 │       └──────────────┴──────┬───────┴──────────────┘              │
 │                              ▼                                    │
 │                    ┌──────────────────┐                          │
 │                    │  Trap Controller  │                          │
 │                    │  (50 Hz loop)     │                          │
 │                    │  • Phase compute  │                          │
 │                    │  • Pattern select │                          │
 │                    │  • Auto-track Z   │                          │
 │                    │  • Safety monitor │                          │
 │                    └────────┬─────────┘                          │
 │                             │                                     │
 │                    ┌────────▼─────────┐                          │
 │                    │  Phase Buffer     │                          │
 │                    │  72 × 256 bits    │                          │
 │                    │  = 2304 bytes     │                          │
 │                    │  (RAM, DMA src)   │                          │
 │                    └────────┬─────────┘                          │
 │                             │                                     │
 │  ┌──────────────────────────┼────────────────────────────┐      │
 │  │         RP2040 (Core 1 / PIO0)                         │      │
 │  │                        ▼                                │      │
 │  │  ┌──────────────────────────────┐                      │      │
 │  │  │ PIO0 SM0: Serial bitstream    │                      │      │
 │  │  │ 10.24 MHz clock               │                      │      │
 │  │  │ 72-bit frame × 256 = 2304 B   │                      │      │
 │  │  │ DMA CH0: buffer → PIO FIFO    │                      │      │
 │  │  │ DMA CH1: CH0 trigger (wrap)   │                      │      │
 │  │  └───────────┬──────────────────┘                      │      │
 │  │              │ DATA (GP0)                              │      │
 │  │              │ CLOCK (GP1) ──────────────────┐         │      │
 │  │              │ LATCH (GP2) ─────┐             │         │      │
 │  └──────────────┼──────────────────┼────────────┼─────────┘      │
 │                 │                  │             │                 │
 └─────────────────┼──────────────────┼─────────────┼────────────────┘
                   │                  │             │
          ┌────────▼────────┐  ┌──────┘      ┌──────┘
          │ 9× 74HC595      │  │             │
          │ (daisy chain)   │  │ Latch       │
          │ SER ← DATA      │  │ (40 kHz)    │
          │ SRCLK ← CLOCK   │  │             │
          │ RCLK ← LATCH    │  │             │
          │                 │  │             │
          │ 72 parallel     │  │             │
          │ outputs (Q0-Q7) │  │             │
          └────────┬────────┘  │             │
                   │            │             │
          ┌────────▼────────────▼─────────────┐
          │ 36× TC4427 (dual MOSFET driver)    │
          │ Each TC4427 drives 2 transducers   │
          │ Push-pull: 10V → GND → 10V         │
          │ Output: 10 Vpp square wave         │
          └────────┬───────────────────────────┘
                   │
          ┌────────▼───────────────────────────┐
          │ 72× MA40S4S 40 kHz ultrasonic      │
          │ transducers                         │
          │ 36 top + 36 bottom (opposing)      │
          │ Hemispherical curvature            │
          └────────────────────────────────────┘

  ┌──────────────────────────────────────────────────┐
  │ RP2040 peripherals (shared both cores):          │
  │  I2C0: VL53L0X (0x29)                            │
  │  I2C1: SSD1306 OLED (0x3C)                       │
  │  SPI0: microSD card (FAT32)                      │
  │  UART1: ESP32-C3 BLE bridge (921600 baud)        │
  │  ADC: joystick X (GP26), Y (GP27), VBAT (GP28)   │
  │  GPIO: rotary encoder (GP10/GP11), buttons       │
  └──────────────────────────────────────────────────┘
```

## Pin Assignments (RP2040)

| Pin | Function | Direction | Notes |
|-----|----------|-----------|-------|
| GP0 | PIO0 SM0 DATA | OUT | Serial data to 74HC595 chain |
| GP1 | PIO0 SM0 CLOCK | OUT | 10.24 MHz shift clock |
| GP2 | PIO0 SM0 LATCH | OUT | 40 kHz latch pulse (RCLK) |
| GP3 | PIO0 SM0 BLANK | OUT | Transducer enable (OE on 74HC595) |
| GP4 | UART1 TX | OUT | To ESP32-C3 RX |
| GP5 | UART1 RX | IN | From ESP32-C3 TX |
| GP6 | I2C1 SDA | BIDIR | SSD1306 OLED (0x3C) |
| GP7 | I2C1 SCL | OUT | SSD1306 OLED |
| GP8 | SPI0 SCK | OUT | microSD card |
| GP9 | SPI0 MOSI | OUT | microSD card |
| GP10 | SPI0 MISO | IN | microSD card ( rotary encoder moved) |
| GP11 | SPI0 CS | OUT | microSD card CS |
| GP12 | ENC A | IN | Rotary encoder quadrature A |
| GP13 | ENC B | IN | Rotary encoder quadrature B |
| GP14 | ENC BTN | IN | Rotary encoder push button |
| GP15 | BTN_MODE | IN | Mode select button (active low) |
| GP16 | BTN_RELEASE | IN | Emergency release (active low) |
| GP17 | LED_STATUS | OUT | Status LED (PWM breathing) |
| GP18 | SD_CD | IN | SD card detect (active low) |
| GP19 | SAFETY_REED | IN | Reed switch interlock (active low) |
| GP20 | ESP_BOOT | OUT | ESP32-C3 BOOT0 (pull low for OTA) |
| GP21 | ESP_EN | OUT | ESP32-C3 enable |
| GP22 | TILT_IRQ | IN | LSM6DSO tilt interrupt (safety) |
| GP26 | ADC0 (X) | IN | Joystick X axis (0–3.3V) |
| GP27 | ADC1 (Y) | IN | Joystick Y axis (0–3.3V) |
| GP28 | ADC2 (VBAT) | IN | Battery voltage divider (÷4) |

## Pin Assignments (ESP32-C3)

| Pin | Function | Notes |
|-----|----------|-------|
| GPIO2 | UART RX | From RP2040 GP4 (TX) |
| GPIO3 | UART TX | To RP2040 GP5 (RX) |
| GPIO8 | LED | BLE connection status |
| GPIO9 | BOOT | Boot button |

## Schematic Overview

### Phase Generation Chain

The heart of Levia Forge is the 72-channel phase-shifted square wave
generator:

```
RP2040 PIO0 SM0
     │
     ├── GP0 (DATA) ──────────────────────▶ 74HC595 #1 SER
     ├── GP1 (CLOCK, 10.24 MHz) ──┬──────▶ 74HC595 #1-9 SRCLK
     │                             │
     ├── GP2 (LATCH, 40 kHz)  ──┬──▶ 74HC595 #1-9 RCLK
     │                           │
     └── GP3 (BLANK/OE)     ──┬──▶ 74HC595 #1-9 OE (active low)
                               │
     74HC595 chain:  #1 → #2 → #3 → #4 → #5 → #6 → #7 → #8 → #9
     (SER of #N+1 connects to Q7' of #N, all share SRCLK + RCLK + OE)

     74HC595 #1:  Q0-Q7  → TC4427 #1A, #1B, #2A, #2B (4 transducers)
     74HC595 #2:  Q0-Q7  → TC4427 #3A, #3B, #4A, #4B
     ...
     74HC595 #9:  Q0-Q7  → TC4427 #17A, #17B, #18A, #18B (last 4)

     Total: 9 × 8 = 72 outputs → 36 × TC4427 → 72 × MA40S4S
```

### TC4427 Half-Bridge Driver

Each TC4427 is a dual non-inverting MOSFET driver. For push-pull
operation, each channel drives a complementary MOSFET pair:

```
                  10V
                   │
              ┌────┴────┐
         10V─┤P-ch Si2301├─┐
              └─────────┘  │
                           ├──▶ To transducer (+)
              ┌─────────┐  │
         GND ─┤N-ch Si2300├─┘
              └─────────┘
              TC4427 output drives both gates (complementary via
              internal dead-time)

     Actually simplified: TC4427 drives a single N-channel MOSFET
     in a high-side configuration with charge pump, OR we use a
     simplified push-pull:

     Better approach: Each 74HC595 output directly drives a
     2N3904 (NPN) + 2N3906 (PNP) complementary pair:

     74HC595 Q ──┬── 1kΩ ──┬── 2N3904 base (NPN, high-side to 10V)
                 │          │
                 │          └── 2N3906 base (PNP, low-side to GND)
                 │
     Transducer (+) connects to the junction of NPN emitter / PNP emitter
     Transducer (−) connects to GND

     When 74HC595 output = HIGH: NPN on, transducer sees +10V
     When 74HC595 output = LOW:  PNP on, transducer sees 0V
     Result: 10 Vpp square wave at 40 kHz, phase-controlled
```

### Transducer Array Geometry

```
Top array (36 elements) — viewed from below:

     Col:  0    1    2    3    4    5
     Row 0: T00 T01 T02 T03 T04 T05
     Row 1: T06 T07 T08 T09 T10 T11
     Row 2: T12 T13 T14 T15 T16 T17
     Row 3: T18 T19 T20 T21 T22 T23
     Row 4: T24 T25 T26 T27 T28 T29
     Row 5: T30 T31 T32 T33 T34 T35

     Each transducer on a curved mount (R = 40 mm curvature)
     Spacing: 10 mm center-to-center (one transducer diameter)
     Height above trap zone: 35 mm (top of cavity)

Bottom array (36 elements) — identical, mirrored:

     Col:  0    1    2    3    4    5
     Row 0: B00 B01 B02 B03 B04 B05
     ...
     Row 5: B30 B31 B32 B33 B34 B35

     Curved mount, pointing up
     Height below trap zone: 35 mm (bottom of cavity)

Total cavity: 70 mm height, 60 mm × 60 mm working area
Trap zone center: (0, 0, 0) = geometric center
Working volume: ±15 mm X, ±15 mm Y, 0 to +20 mm Z
```

### Power Architecture

```
2× 18650 LiPo (3.7V each, 2500 mAh)
     │
     ├── 7.4V nominal (6.0V – 8.4V range)
     │
     ├── MCP1603T-3.3 Buck → 3.3V / 500 mA
     │   (RP2040, 74HC595, ESP32-C3, OLED, VL53L0X, SD card)
     │
     ├── TPS61023 Boost → 10V / 1.5A (transducer drive)
     │   (72 transducers × ~5 mA = 360 mA peak, 10V)
     │
     └── AP2112K-5.0 LDO → 5V / 300 mA
         (VL53L0X, SD card level shifter, ESP32-C3 alt supply)

Battery monitoring: GP28 ADC via voltage divider (7.4V ÷ 4 = 1.85V)
Low battery cutoff: 6.0V (3.0V/cell) → auto-shutdown transducers
```

## Bill of Materials (BOM)

| # | Part | Qty | Unit ($) | Total ($) | Notes |
|---|------|-----|----------|-----------|-------|
| 1 | RP2040 (QFN-56) | 1 | 1.20 | 1.20 | Main MCU, dual-core 133 MHz |
| 2 | W25Q128JVSIQ (16MB Flash) | 1 | 0.85 | 0.85 | Firmware + phase tables |
| 3 | ESP32-C3-WROOM-02 | 1 | 2.50 | 2.50 | BLE/WiFi bridge |
| 4 | MA40S4S 40kHz ultrasonic transducer | 72 | 0.35 | 25.20 | Murata, 10mm, 10Vpp |
| 5 | 74HC595 (SOIC-16) | 9 | 0.15 | 1.35 | 8-bit shift register |
| 6 | TC4427 (SOIC-8) | 0 | — | — | (Using discrete BJT pairs instead) |
| 7 | 2N3904 (NPN, SOT-23: MMBT3904) | 72 | 0.03 | 2.16 | High-side driver |
| 8 | 2N3906 (PNP, SOT-23: MMBT3906) | 72 | 0.03 | 2.16 | Low-side driver |
| 9 | 1kΩ 0805 resistor | 72 | 0.01 | 0.72 | Base drive resistor |
| 10 | TPS61023 Boost (10V) | 1 | 1.10 | 1.10 | 3.7V→10V, 1.5A |
| 11 | MCP1603T-3.3 Buck | 1 | 0.90 | 0.90 | 7.4V→3.3V |
| 12 | AP2112K-5.0 LDO | 1 | 0.35 | 0.35 | 5V for peripherals |
| 13 | SSD1306 OLED 128×64 (I2C) | 1 | 3.50 | 3.50 | Display |
| 14 | VL53L0X ToF sensor | 1 | 3.00 | 3.00 | Particle height |
| 15 | microSD socket (push-push) | 1 | 0.80 | 0.80 | Logging |
| 16 | 2-axis analog joystick (KY-023) | 1 | 1.20 | 1.20 | X/Y positioning |
| 17 | Rotary encoder (EC11) | 1 | 1.00 | 1.00 | Z height |
| 18 | 2× tactile buttons (6mm) | 2 | 0.10 | 0.20 | Mode, Release |
| 19 | 18650 battery holder (2-cell) | 1 | 1.50 | 1.50 | 7.4V pack |
| 20 | 18650 LiPo 2500mAh | 2 | 3.00 | 6.00 | Power |
| 21 | Reed switch (glass, 10mm) | 1 | 0.30 | 0.30 | Safety interlock |
| 22 | LSM6DSO (IMU, QFN-14) | 1 | 2.50 | 2.50 | Tilt safety |
| 23 | USB-C connector (16-pin) | 1 | 0.50 | 0.50 | Programming + charging |
| 24 | TP4056 (LiPo charger) | 1 | 0.40 | 0.40 | USB charging |
| 25 | 10µH 2A inductor (SMD) | 1 | 0.40 | 0.40 | Boost converter |
| 26 | 4.7µH 1A inductor (SMD) | 1 | 0.30 | 0.30 | Buck converter |
| 27 | 10µF 16V X7R (0805) | 10 | 0.05 | 0.50 | Decoupling |
| 28 | 100nF 16V X7R (0805) | 30 | 0.01 | 0.30 | Decoupling |
| 29 | 10kΩ 0805 resistor | 10 | 0.01 | 0.10 | Pull-ups |
| 30 | PCB (4-layer, 80×60mm) | 1 | 4.00 | 4.00 | Custom |
| 31 | 3D-printed array mounts (2) | 1 | 2.00 | 2.00 | PETG curved holders |
| | | | **Total** | **~$61.39** | |

## Firmware Architecture

### Core 0 — Control Loop (50 Hz)

```
┌─────────────────────────────────────────┐
│            Core 0: Controller            │
│                                          │
│  1. Read joystick (ADC) → target X,Y   │
│  2. Read encoder → target Z             │
│  3. Read buttons → mode / release       │
│  4. Read VL53L0X → particle height      │
│  5. Auto-track Z (PID if particle set)  │
│  6. Compute 72 phases (Helmholtz)       │
│  7. Update phase buffer (DMA source)    │
│  8. Update OLED display (10 Hz)         │
│  9. Log to SD (10 Hz)                   │
│ 10. UART exchange with ESP32-C3         │
│ 11. Safety check (tilt, reed, battery)  │
└─────────────────────────────────────────┘
```

### Core 1 — Phase Engine (background)

```
┌─────────────────────────────────────────┐
│       Core 1: Phase DMA Engine           │
│                                          │
│  • Configures PIO0 SM0 at startup       │
│  • Sets up DMA CH0 (buffer → PIO FIFO)  │
│  • Sets up DMA CH1 (re-trigger CH0)     │
│  • Monitors DMA for underrun            │
│  • Adjusts PIO clock if needed          │
│  • Runs phase buffer integrity check    │
└─────────────────────────────────────────┘
```

### Phase Computation

```c
// For each transducer i at position t[i]:
//   distance = sqrt((t[i].x - px)^2 + (t[i].y - py)^2 + (t[i].z - pz)^2)
//   phase_rad = (2 * PI * FREQ / SPEED_OF_SOUND) * distance
//   phase_step = (int)(phase_rad / (2*PI) * PHASE_STEPS) % PHASE_STEPS
//
// Pack into buffer: for each of 256 phase steps,
//   bit[i] = (phase_step < PHASE_STEPS/2) ? 1 : 0
// This creates a 50% duty square wave at the transducer's phase.
```

## Safety Features

1. **Reed switch interlock** — a magnetic reed switch on the enclosure
   detects if the lid is open. If open, transducers are immediately
   disabled (OE pin high = blank all 74HC595 outputs).

2. **Tilt sensor** — an LSM6DSO IMU detects if the device is tilted
   more than 15° from horizontal. If tilted, transducer power is
   reduced to 50% (to prevent particle from launching).

3. **Hardware watchdog** — the RP2040 watchdog timer must be kicked
   every 100 ms. If Core 0 freezes, the watchdog resets the device,
   disabling the transducers (OE goes high on reset).

4. **Low battery cutoff** — if battery voltage drops below 6.0V
   (3.0V/cell), transducers are disabled and a low-battery icon
   appears on the OLED.

5. **Temperature monitor** — the RP2040 internal temperature sensor
   is monitored. If >70°C, transducer power is reduced.

6. **Emergency release button** — a dedicated hardware button (GP16)
   is polled at 1 kHz. When pressed, all transducers are immediately
   blanked (OE high).

## Performance Specifications

| Parameter | Value |
|-----------|-------|
| Carrier frequency | 40 kHz |
| Phase resolution | 256 steps (1.41°) |
| Number of transducers | 72 (36 top + 36 bottom) |
| Transducer drive voltage | 10 Vpp |
| Max acoustic pressure | ~2.5 kPa (at focus) |
| Max levitable mass | ~10 mg (styrofoam), ~3 mg (water droplet) |
| Max levitable diameter | ~3 mm |
| Working volume | ±15 mm × ±15 mm × 0–20 mm |
| Position resolution | 0.1 mm (phase-limited) |
| Update rate | 50 Hz (phase recomputation) |
| Serial bit clock | 10.24 MHz |
| DMA buffer size | 2304 bytes (72 bits × 256 steps ÷ 8) |
| Battery life | ~2.5 hours continuous (full power) |
| Battery life (eco) | ~6 hours (50% power, single trap) |
| Dimensions | 80 × 80 × 70 mm (array + base) |
| Weight | ~180 g (without batteries) |

## Build Guide

### PCB Assembly

1. **Solder the RP2040 section** — RP2040 (QFN-56), W25Q128 flash,
   12 MHz crystal, decoupling caps, pull-up resistors. Follow the
   [official RP2040 minimum hardware design](https://datasheets.raspberrypi.com/rp2040/hardware-design-with-rp2040.pdf).

2. **Solder the power section** — TPS61023 boost (10V), MCP1603T
   buck (3.3V), AP2112K LDO (5V), TP4056 charger, USB-C connector.

3. **Solder the 74HC595 chain** — 9× 74HC595 in a row, daisy-chained
   (Q7' → SER of next). Add 100nF decoupling on each VCC pin.

4. **Solder the BJT driver array** — 72× MMBT3904 + 72× MMBT3906
   pairs with 1kΩ base resistors. These are the most tedious part.
   Use a stencil + reflow for the SOT-23 packages.

5. **Solder the ESP32-C3 module** — place near the RP2040, connect
   UART (GP4/GP5) and control pins (EN, BOOT).

6. **Solder peripherals** — SSD1306 OLED (I2C1), VL53L0X (I2C0),
   microSD socket (SPI0), joystick (ADC), rotary encoder, buttons,
   reed switch, LSM6DSO.

### Mechanical Assembly

1. **3D print the transducer mounts** — two curved PETG brackets
   (top and bottom) with 36 holes each for MA40S4S transducers.
   Curvature radius: 40 mm. STL files in `hardware/`.

2. **Mount transducers** — press-fit each MA40S4S into the bracket
   holes. Solder 30 AWG wires from each transducer to the PCB driver
   pads. Keep wire lengths equal (±5 mm) within each array.

3. **Assemble the enclosure** — the PCB sits in the base, the bottom
   array bracket mounts above it (pointing up), and the top array
   bracket mounts above (pointing down). The VL53L0X mounts on the
   top bracket center, pointing down.

4. **Install batteries** — two 18650 cells in the rear holder.

### Firmware Flashing

1. **Flash RP2040** — hold BOOTSEL on power-up, drag the UF2 file
   to the RPI-RP2 mass storage drive:
   ```bash
   cd firmware/build
   cp levia_forge.uf2 /media/$USER/RPI-RP2/
   ```

2. **Flash ESP32-C3** — via USB or OTA:
   ```bash
   cd firmware/esp32c3
   idf.py flash
   ```

## Usage

1. **Power on** — the OLED displays "LEVIA FORGE" and battery voltage.
   The phase engine starts in standby (transducers off).

2. **Place a particle** — drop a small styrofoam bead (1–3 mm) into
   the cavity. It will fall to the bottom array.

3. **Activate** — press the MODE button. The transducers energize and
   the standing wave trap forms at the center. The bead is captured
   and levitated.

4. **Manipulate** — use the joystick to move the bead in X/Y. Use the
   rotary encoder to change height (Z). The VL53L0X auto-tracks the
   bead height.

5. **Change patterns** — press MODE again to cycle: Point → Twin →
   Vortex → Bending → Transport → back to Point.

6. **Release** — press the RELEASE button (or open the lid). The
   transducers deactivate and the bead drops.

7. **BLE control** — connect via the companion app (`scripts/levia_app.py`)
   for remote control and logging.

## Companion App

A Python/PyQt6 companion app is provided in `scripts/levia_app.py`:

```
python3 scripts/levia_app.py
```

Features:
- BLE scan and connect
- 3D position sliders (X, Y, Z)
- Pattern selection dropdown
- Live particle height readout
- Session logging to CSV
- Battery and temperature monitoring

## File Structure

```
levia-forge/
├── README.md                    # This file
├── schematic/
│   ├── levia-forge.kicad_sch    # KiCad schematic
│   ├── levia-forge.kicad_pcb    # KiCad PCB (4-layer)
│   └── README.md                # Schematic notes
├── firmware/
│   ├── CMakeLists.txt           # CMake build
│   ├── pico_sdk_import.cmake    # Pico SDK import
│   ├── sdkconfig.h              # Build config
│   ├── main.c                   # Core 0: control loop
│   ├── phase_engine.c           # Core 1: PIO + DMA
│   ├── phase_engine.h
│   ├── phase_compute.c          # Helmholtz phase math
│   ├── phase_compute.h
│   ├── transducer_layout.c      # 72 transducer 3D positions
│   ├── transducer_layout.h
│   ├── pio_phase.pio            # PIO program (serial bitstream)
│   ├── display.c                # OLED SSD1306 driver
│   ├── display.h
│   ├── tof.c                    # VL53L0X driver
│   ├── tof.h
│   ├── sd_log.c                 # SD card logging
│   ├── sd_log.h
│   ├── ble_bridge.c             # ESP32-C3 UART protocol
│   ├── ble_bridge.h
│   ├── safety.c                 # Safety monitors
│   ├── safety.h
│   ├── input.c                  # Joystick + encoder + buttons
│   ├── input.h
│   └── esp32c3/
│       ├── CMakeLists.txt
│       └── main.c               # ESP32-C3 BLE bridge firmware
├── hardware/
│   ├── BOM.csv                  # Bill of materials
│   ├── array_mount_top.stl      # 3D-printable top bracket
│   ├── array_mount_bottom.stl   # 3D-printable bottom bracket
│   └── enclosure_base.stl       # 3D-printable base
├── scripts/
│   ├── levia_app.py             # PyQt6 BLE companion app
│   ├── phase_visualizer.py      # 3D acoustic field visualizer
│   └── calibrate_array.py       # Array calibration helper
└── docs/
    ├── assembly_guide.md        # Step-by-step assembly
    ├── api_reference.md         # Firmware API docs
    └── acoustic_theory.md       # Radiation force theory
```

## License

MIT — build it, levitate stuff, improve it.

---

*Invented as device #42 in the SoC Device Inventions collection.*