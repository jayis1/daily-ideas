# Aero Cast — Schematic (KiCad)

This directory contains the KiCad schematic project for the Aero Cast pocket 3-axis ultrasonic anemometer.

## Files

| File | Description |
|------|-------------|
| `aero_cast.kicad_pro` | KiCad project file |
| `aero_cast.kicad_sch` | Main schematic |
| `aero_cast.kicad_pcb` | PCB layout (4-layer) |
| `aero_cast.net` | Netlist (exported) |
| `symbols/` | Custom symbols (if any) |
| `footprints/` | Custom footprints (if any) |

## Schematic Overview

The schematic is organized into these functional blocks:

### 1. Power Supply
- **TP4056** USB-C Li-ion charger with charge status output
- **AP2112-3.3** LDO regulating 3.7V battery → 3.3V system rail
- **18650 battery holder** with protection diode
- Battery voltage divider (2:1) → RP2040 ADC for monitoring

### 2. RP2040 Main MCU
- Dual-core ARM Cortex-M0+ at 125 MHz
- 2 MB external QSPI flash (W25Q16) for program storage
- 24 MHz crystal
- USB-C debug port (USB DP/DM on GP28/GP29... actually RP2040 fixed USB pins)
- All GPIO broken out per the pin assignment table

### 3. Ultrasonic Frontend
- **TC4427** dual MOSFET driver (×2) — boosts 3.3V PIO output to ~20Vpp
  - Driven by a charge pump: 3.3V → 10V via diode + capacitor ladder
  - Transducer TX side connected to HV driver output through DC blocking cap
- **CD4052B** 4:1 analog multiplexer — routes active transducer pair to TIA
- **OPA2350** dual rail-to-rail op-amp:
  - First half: Transimpedance amplifier (TIA) for received echo
    - Feedback: 100kΩ + 10pF → gain of ~100k at 40 kHz
  - Second half: Envelope detector (diode + RC)
- **TLV3201** fast comparator — converts envelope to clean digital edge
  - Threshold set by MCP4911 SPI DAC (adjustable)
  - Output → RP2040 PIO SM1 input (GP17)

### 4. Transducer Array
- 6× Manorshi MS-P4010 40 kHz ultrasonic transducers
- Arranged in tripod geometry: 3 bottom (120° apart, 40mm radius) + 3 top (center)
- Each transducer pair shares a path of ~100mm
- Transducers mounted on the PCB sensor head with M3 standoffs

### 5. ESP32-C3 Wireless Bridge
- ESP32-C3-MINI-1 module
- UART connection to RP2040 (1 Mbps, GP2/GP3)
- PCB antenna (built into module)
- Reset line from RP2040 (GP22)
- Separate 3.3V power rail (shared with RP2040)

### 6. BME280 Atmospheric Sensor
- I2C (GP0 SDA, GP1 SCL)
- Measures temperature, pressure, humidity for sonic temperature correction
- Mounted near sensor head for accurate air temperature

### 7. SSD1306 OLED Display
- 128×64 monochrome OLED, I2C address 0x3C
- Shares I2C bus with BME280

### 8. microSD Card Slot
- SPI interface (GP4 CS, GP5 SCK, GP6 MOSI, GP7 MISO)
- Card detect switch on separate GPIO

### 9. User Interface
- 3× tactile buttons (PWR, MODE, AVG) — active low with pull-ups
- 2× LEDs (status blue, data green)
- Passive buzzer (optional)

## PCB Layout Notes

- 4-layer board: Top (signal), Inner 1 (GND), Inner 2 (3.3V power), Bottom (signal)
- Sensor head is a separate PCB connected via 10-pin FFC
- Keep analog frontend (TIA, comparator) away from digital (RP2040, ESP32-C3)
- Place decoupling caps close to all ICs
- Route ultrasonic TX lines away from RX lines to prevent crosstalk
- Guard ring around TIA input for low noise
- Transducer mounting holes on sensor head PCB with precise 40mm radius spacing

## Mechanical

The device consists of two PCB assemblies:

1. **Main body PCB** (120 × 65 mm): RP2040, ESP32-C3, power, display, SD, buttons
2. **Sensor head PCB** (60 × 60 mm): 6 transducers, TIA, mux, BME280

Connected by a 10-pin 150mm FFC cable (power, 3× TX, 3× RX, mux select ×2, GND).

The sensor head PCB has M3 mounting holes for the transducer standoffs that create the 3D tripod geometry. Transducers are held in 3D-printed clips at precise angles.

## Schematic Net List (Key Nets)

| Net Name | Source | Destination |
|----------|--------|-------------|
| VBAT | 18650+ | TP4056 BAT, AP2112 IN, voltage divider |
| VCC_3V3 | AP2112 OUT | All ICs, RP2040, ESP32-C3, BME280, OLED |
| HV_DRIVE | TC4427 OUT | Transducers (via DC blocking caps) |
| ECHO_RX | Mux output | OPA2350 TIA input |
| ECHO_ENV | OPA2350 envelope | TLV3201 comparator input |
| ECHO_DIGI | TLV3201 output | RP2040 GP17 (PIO RX) |
| I2C_SDA | RP2040 GP0 | BME280, OLED |
| I2C_SCL | RP2040 GP1 | BME280, OLED |
| UART_TX | RP2040 GP2 | ESP32-C3 RX |
| UART_RX | RP2040 GP3 | ESP32-C3 TX |
| SPI_SCK | RP2040 GP5 | SD card, DAC |
| SPI_MOSI | RP2040 GP6 | SD card, DAC |
| SPI_MISO | RP2040 GP7 | SD card |
| SD_CS | RP2040 GP4 | SD card CS |
| DAC_CS | RP2040 GP19 | MCP4911 CS |
| MUX_A | RP2040 GP13 | CD4052B A |
| MUX_B | RP2040 GP14 | CD4052B B |
| HV_EN | RP2040 GP15 | TC4427 enable |
| PIO_TX | RP2040 GP16 | TC4427 input |