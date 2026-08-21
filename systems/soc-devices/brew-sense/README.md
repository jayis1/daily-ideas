# Brew Sense

**A precision fermentation monitor that watches your brew so you don't have to — tracking gravity, temperature, CO₂ evolution, and pH in real time with BLE + Wi-Fi uplink.**

---

## What It Does

The Brew Sense is a compact, submersible-capable device that monitors home fermentation — beer, wine, mead, kimchi, sourdough, kombucha, or anything else alive and bubbling. Unlike hydrometer floaters or external temperature stickers, Brew Sense sits inside the fermentation vessel (or clips to the outside via a thermowell probe) and continuously measures:

- **Specific gravity** — via a vibrating tube densitometer (SMD piezo resonator), calibrated to ±0.002 SG
- **Temperature** — high-accuracy DS18B20 waterproof probe (±0.1°C)
- **CO₂ evolution** — Senseair S8 miniature NDIR CO₂ sensor on the headspace gas port
- **pH** — via analog pH probe interface (EZO-pH compatible) for active fermentation tracking
- **Pressure** — BMP388 barometric pressure sensor (for closed-vessel / spunding valve mode)
- **Activity index** — derived metric combining CO₂ rate, gravity change, and temperature trend to classify fermentation stage

All sensor data is processed on the **STM32L476RG** (ultra-low-power ARM Cortex-M4F) and transmitted over **BLE 5.2** to a companion phone app, or pushed over **Wi-Fi** (via AT-command ESP32-C3 co-processor) to a homebrew dashboard (Brewfather, Brewers Friend, or self-hosted MQTT).

### Fermentation Stage Classification

| Stage | Gravity Range | CO₂ Trend | Activity Index |
|-------|--------------|-----------|----------------|
| LAG | >1.060 (high) | Flat/rising slowly | 0–15 |
| ACTIVE | Dropping fast | Peaking | 40–100 |
| PEAK | Plateau (1.020–1.040) | Maximum | 90–100 |
| SLOWING | Slowly dropping | Declining | 20–50 |
| FINISHED | Stable <1.015 | Near zero | 0–10 |
| STUCK | No change >48h | Zero | 0 (alert) |

Battery life: **30 days** on 2× AAA (in low-power BLE mode), or **continuous** via USB-C wall power.

---

## Block Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         BREW SENSE                                  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐            │
│  │ DS18B20      │  │ BMP388       │  │ Senseair S8    │            │
│  │ Temp Probe   │  │ Baro Press   │  │ NDIR CO₂       │            │
│  │ 1-Wire GP8  │  │ I²C 0x77    │  │ UART1 (AT)     │            │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────┘            │
│         │                 │                    │                      │
│         └────────┬───────┴────────────────────┘                      │
│                  │                                                    │
│  ┌───────────────▼────────────────────────────────────────┐        │
│  │              STM32L476RG (LQFP-64)                      │        │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────────┐   │        │
│  │  │ Cortex-M4F  │ │ 1MB Flash  │ │ 128KB SRAM       │   │        │
│  │  │ 80MHz LP    │ │            │ │ + 32KB FIFO      │   │        │
│  │  │ 120MHz RUN  │ │            │ │ for DMA I2S      │   │        │
│  │  └────────────┘ └────────────┘ └──────────────────┘   │        │
│  │                                                          │        │
│  │  ┌─────────────────────────────────────────────┐        │        │
│  │  │  Fermentation Engine (gravity calc + stage)  │        │        │
│  │  │  • Densitometer frequency → SG               │        │        │
│  │  │  • CO₂ rate → activity index                  │        │        │
│  │  │  • Temp-compensated gravity correction        │        │        │
│  │  └─────────────────────────────────────────────┘        │        │
│  └────────┬────────────────┬──────────────────────────────┘        │
│           │                │                                         │
│  ┌────────▼──────┐  ┌─────▼──────────┐  ┌──────────────────┐       │
│  │ Piezo Dens.   │  │ ESP32-C3       │  │ EZO-pH           │       │
│  │ (vibrating    │  │ WiFi/BLE       │  │ pH Probe I/F     │       │
│  │  tube driver) │  │ AT-command     │  │ I²C 0x63         │       │
│  │ GP9/GP10 PWM  │  │ UART2          │  │                  │       │
│  └───────────────┘  └───────┬────────┘  └──────────────────┘       │
│                              │                                       │
│  ┌───────────────────────────▼──────────────────────────┐           │
│  │ Antenna: 2.4GHz chip antenna (on ESP32-C3 module)    │           │
│  └───────────────────────────────────────────────────────┘           │
│                                                                      │
│  ┌───────────────────────────────────────────────────────┐           │
│  │ Power: 2× AAA (3V) → TPS62740 buck (3.3V, 95% eff)   │           │
│  │        OR USB-C (5V) → MCP73871 charger + TPS62740    │           │
│  │        Battery: LIR2450 rechargeable coin (optional)   │           │
│  └───────────────────────────────────────────────────────┘           │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ SSD1306      │  │ Buzzer       │  │ LED RGB      │              │
│  │ OLED 128x32  │  │ (alarm)      │  │ (status)     │              │
│  │ I²C 0x3C    │  │ GP11 PWM     │  │ GP12/GP13    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└────────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (STM32L476RG)

| Pin | Function | Connected To |
|-----|----------|-------------|
| PA0 | ADC1_IN5 | pH probe analog (backup path) |
| PA2 | USART2_TX | Debug UART TX |
| PA3 | USART2_RX | Debug UART RX |
| PA4 | DAC1_OUT1 | Piezo drive signal A |
| PA5 | SPI1_SCK | Internal flash SPI |
| PA6 | SPI1_MISO | Internal flash SPI |
| PA7 | SPI1_MOSI | Internal flash SPI |
| PA8 | MCO (clock out) | System clock monitor |
| PA9 | I2C1_SCL | BMP388, SSD1306, EZO-pH (pull-up 4.7k) |
| PA10 | I2C1_SDA | BMP388, SSD1306, EZO-pH (pull-up 4.7k) |
| PB0 | ADC1_IN8 | Battery voltage divider (1/2 scale) |
| PB3 | GPIO_INPUT | DS18B20 1-Wire data (4.7k pull-up) |
| PB4 | TIM3_CH1 | Piezo drive signal B (complementary) |
| PB5 | GPIO_OUTPUT | Senseair S8 power enable |
| PB6 | I2C1_ALT_SCL | (reserved for future I²C expansion) |
| PB7 | I2C1_ALT_SDA | (reserved for future I²C expansion) |
| PB10 | USART3_TX | Senseair S8 UART TX |
| PB11 | USART3_RX | Senseair S8 UART RX |
| PB12 | SPI2_NSS | (reserved) |
| PB13 | SPI2_SCK | (reserved) |
| PB14 | TIM15_CH1 | Buzzer PWM |
| PB15 | GPIO_OUTPUT | RGB LED red (active low) |
| PC0 | ADC1_IN10 | Thermistor backup input |
| PC4 | USART1_TX | ESP32-C3 UART TX (AT commands) |
| PC5 | USART1_RX | ESP32-C3 UART RX (AT responses) |
| PC6 | GPIO_OUTPUT | ESP32-C3 power enable |
| PC7 | GPIO_OUTPUT | RGB LED green (active low) |
| PC8 | GPIO_OUTPUT | RGB LED blue (active low) |
| PC9 | GPIO_OUTPUT | USB-C VBUS detect |
| PC10 | GPIO_OUTPUT | Heater enable (for dew point / condensation prevention) |
| PC11 | GPIO_INPUT | BOOT button |
| PC12 | GPIO_OUTPUT | DS18B20 parasite power enable |
| PD2 | GPIO_OUTPUT | STATUS_LED (single) |
| NRST | RESET | Reset button |
| BOOT0 | BOOT | Boot configuration |

---

## Power Architecture

```
Power Path A (Battery):
  2× AAA (3V nominal, 2.0–3.2V) ──► TPS62740 buck ──► 3.3V VDD (95% eff)
  
Power Path B (USB-C):
  USB-C (5V) ──► MCP73871 ──► LIR2450 coin cell (3.7V, 110mAh, optional)
                  │                   │
                  └──► TPS62740 ◄─────┘ ──► 3.3V VDD

Quiescent: ~8µA (STOP mode, RTC on, sensors off)
Low-power mode: ~150µA (RTC + BLE advertising, 1Hz)
Active (all sensors + BLE): ~12mA avg
Active (Wi-Fi push burst): ~85mA for 300ms every 5min
Active (display on): +6mA for SSD1306

Battery life estimate (2× AAA alkaline, ~1000mAh):
  - Continuous monitoring + BLE: ~30 days
  - 1-minute sampling + BLE: ~60 days
  - Low-power (advertising only): ~120 days
```

Duty cycle in normal mode:
1. Wake on RTC alarm (60s interval)
2. Power on DS18B20 + BMP388 (10ms warmup)
3. Read temperature, pressure, gravity (~50ms)
4. Read CO₂ from S8 cache (~5ms, S8 reads continuously in background)
5. Read pH from EZO-pH (~50ms)
6. Compute activity index + fermentation stage (~2ms)
7. Update BLE GATT characteristics (~3ms)
8. Update OLED display (~10ms)
9. If Wi-Fi time: push to MQTT (300ms burst)
10. Enter STOP mode (~99.87s)

---

## Densitometer Principle

The Brew Sense measures specific gravity using a **vibrating tube densitometer** technique — the same principle used in laboratory-grade density meters (Anton Paar, Mettler Toledo), miniaturized for homebrew:

1. A small SMD piezo ceramic (Murata MA40S4S) is bonded to a stainless-steel vibrating tube
2. The STM32 drives the piezo at sweep frequencies (1–8 kHz) via DAC+PWM complementary outputs
3. A second piezo element picks up the resonant vibration
4. The resonant frequency shifts with fluid density: **f ∝ √(k / (m_tube + ρ × V_tube))**
5. Temperature compensation uses the DS18B20 reading
6. Calibration uses two reference points (air = 0 SG, distilled water = 1.000 SG)

This avoids the need for a traditional hydrometer and gives continuous, real-time gravity tracking throughout fermentation.

---

## Mechanical

- **PCB**: 72mm × 38mm, 1.6mm FR4, 4-layer
- **Vibrating tube assembly**: 316L stainless tube (4mm OD, 3mm ID, 50mm long) bonded to piezo elements
- **Thermowell option**: 6mm OD stainless probe with DS18B20 potted inside, 150mm length
- **Enclosure**: IP67-rated polycarbonate shell with O-ring seal (for external mount); food-safe silicone boot (for submersible)
- **CO₂ port**: Silicone tube (4mm ID) connects S8 sensor to headspace via fermenter airlock hole
- **Mounting**: Magnetic back + M4 bolt holes for fermenter bracket
- **Display window**: 30mm × 10mm clear aperture for OLED
- **Total height**: 25mm (external mount) or 15mm (submersible without display)

---

## Firmware Architecture

```
firmware/
├── Core/
│   ├── Src/
│   │   ├── main.c              # Entry point, clock config, task launch
│   │   ├── sensor_manager.c    # I2C/1-Wire/UART sensor reads
│   │   ├── densitometer.c      # Piezo drive, frequency sweep, SG calc
│   │   ├── fermentation.c      # Activity index, stage classification
│   │   ├── ble_service.c       # BLE GATT server, advertising
│   │   ├── wifi_uplink.c       # ESP32-C3 AT command interface
│   │   ├── power_manager.c     # STOP mode, duty cycling, battery monitor
│   │   ├── display.c           # SSD1306 UI (gravity graph, stage, temp)
│   │   ├── alarm.c             # Buzzer + LED alerts for stuck/finished
│   │   └── calibration.c       # Air/water calibration routine
│   ├── Inc/
│   │   ├── sensor_manager.h
│   │   ├── densitometer.h
│   │   ├── fermentation.h
│   │   ├── ble_service.h
│   │   ├── wifi_uplink.h
│   │   ├── power_manager.h
│   │   ├── display.h
│   │   ├── alarm.h
│   │   └── calibration.h
├── Drivers/
│   ├── STM32L4xx_HAL_Driver/  # ST HAL library
│   └── CMSIS/                  # Cortex-M4F core
├── Middlewares/
│   └── ST_BLE/                 # STM32 BLE stack
├── Makefile
└── STM32L476RGTX_FLASH.ld
```

### Key Firmware Flow

```c
int main(void) {
    HAL_Init();
    SystemClock_Config();
    
    power_manager_init();
    i2c_bus_init();
    uart_bus_init();
    onewire_init();
    
    sensor_manager_init();
    densitometer_init();
    fermentation_init();
    ble_service_init();
    display_init();
    alarm_init();
    
    // Load calibration from flash
    calibration_load();
    
    // Senseair S8 starts continuous background reads
    s8_start_continuous();
    
    while (1) {
        // Read all sensors
        float temperature = ds18b20_read_temp();
        float pressure   = bmp388_read_pressure();
        float co2_ppm    = s8_read_co2();
        float ph          = ezo_ph_read();
        float gravity     = densitometer_read_sg(temperature);
        
        // Compute fermentation state
        fermentation_update(temperature, gravity, co2_ppm, ph, pressure);
        ferment_stage_t stage = fermentation_get_stage();
        float activity       = fermentation_get_activity_index();
        
        // Update BLE
        ble_update_gravity(gravity);
        ble_update_temperature(temperature);
        ble_update_co2(co2_ppm);
        ble_update_ph(ph);
        ble_update_stage(stage);
        ble_update_activity(activity);
        
        // Update display
        display_render(gravity, temperature, stage, activity);
        
        // Check alarms
        alarm_check(stage, gravity, temperature);
        
        // Wi-Fi push (every 5 minutes)
        if (wifi_timer_expired()) {
            wifi_push_all(gravity, temperature, co2_ppm, ph, 
                          pressure, stage, activity);
        }
        
        // Sleep until next sample
        power_manager_sleep(SAMPLE_INTERVAL_SEC);
    }
}
```

---

## BLE GATT Service

```
Service UUID: 0xFFB0 (BrewSense)
  ├── Char 0xFFB1: Specific Gravity (read/notify) — float32 (e.g., 1.050)
  ├── Char 0xFFB2: Temperature °C (read/notify) — float32
  ├── Char 0xFFB3: CO₂ ppm (read/notify) — uint16
  ├── Char 0xFFB4: pH (read/notify) — float32
  ├── Char 0xFFB5: Pressure hPa (read) — float32
  ├── Char 0xFFB6: Fermentation Stage (read/notify) — uint8 (0-5)
  ├── Char 0xFFB7: Activity Index (read/notify) — uint8 (0-100)
  ├── Char 0xFFB8: Battery % (read) — uint8
  ├── Char 0xFFB9: Gravity Trend (read) — int8 (-2 to +2)
  └── Char 0xFFBA: Device Info (read) — string

BLE advertising packet (31 bytes):
[Flags] [Complete 16-bit UUID: FFB0] [Mfr-specific: gravity(4), temp(2), stage(1), activity(1)]
```

---

## MQTT Topics

For Wi-Fi uplink mode (via ESP32-C3):

```
brewsense/{device_id}/gravity       → float (SG)
brewsense/{device_id}/temperature   → float (°C)
brewsense/{device_id}/co2           → uint16 (ppm)
brewsense/{device_id}/ph            → float
brewsense/{device_id}/pressure      → float (hPa)
brewsense/{device_id}/stage         → string (LAG/ACTIVE/PEAK/SLOWING/FINISHED/STUCK)
brewsense/{device_id}/activity      → uint8 (0-100)
brewsense/{device_id}/trend         → int8 (-2 to +2)
brewsense/{device_id}/status        → JSON (all fields, every 5 min)
```

Compatible with: Home Assistant (auto-discovery), Brewfather (custom stream), Brewers Friend, Node-RED, Grafana.

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | STM32L476RG | LQFP-64 | 1 | $4.50 | Cortex-M4F, 1MB flash, ultra-low-power |
| 2 | ESP32-C3-MINI-1 | Module | 1 | $1.80 | Wi-Fi/BLE co-processor (AT mode) |
| 3 | DS18B20 | TO-92 (waterproof probe) | 1 | $1.50 | ±0.1°C temperature |
| 4 | BMP388 | LGA-10 2×2 | 1 | $1.20 | Barometric pressure |
| 5 | Senseair S8 | 33mm × 19mm module | 1 | $12.00 | NDIR CO₂ 0-10000ppm |
| 6 | EZO-pH (Atlas Scientific) | 18mm × 22mm module | 1 | $8.00 | pH probe interface (I²C) |
| 7 | Murata MA40S4S | SMD piezo | 2 | $0.50 | Densitometer driver/receiver |
| 8 | SSD1306 128×32 | OLED module | 1 | $1.50 | Display |
| 9 | TPS62740 | VSON-10 | 1 | $1.20 | Buck converter (95% eff) |
| 10 | MCP73871 | QFN-20 4×4 | 1 | $1.00 | USB-C battery charger |
| 11 | LIR2450 coin cell | CR2450 size | 1 | $2.00 | 3.7V 110mAh (optional) |
| 12 | USB-C receptacle | 16-pin SMD | 1 | $0.35 | Power + charging |
| 13 | AAA battery holder | Through-hole | 1 | $0.50 | 2× AAA side-by-side |
| 14 | Piezo buzzer | SMD 5mm | 1 | $0.25 | Alarm beeper |
| 15 | RGB LED | 0805 | 1 | $0.10 | Status indicator |
| 16 | 316L stainless tube | 4mm OD, 50mm | 1 | $0.80 | Densitometer vibrating element |
| 17 | Silicone tubing | 4mm ID, 200mm | 1 | $0.40 | CO₂ sampling port |
| 18 | Passives (R/C/L) | 0402 | ~40 | $0.80 | Pullups, decoupling, filters |
| 19 | O-ring | 18mm ID | 1 | $0.10 | Enclosure seal |
| 20 | PCB 4-layer 72×38mm | Rectangular | 1 | $1.50 | JLCPCB |

**Total estimated BOM: ~$38.55** (qty 1)

---

## Calibration Procedure

### Air/Water Two-Point Calibration

```python
# Run via scripts/calibrate.py
import serial

ser = serial.Serial('/dev/ttyUSB0', 115200)

# Step 1: Dry calibration (air)
input("Hold sensor in air. Press Enter...")
ser.write(b'CALS,air\n')
# Device measures resonant frequency in air (f_air)
# This maps to SG = 0.000 (by convention; actually SG_air ≈ 0.0012)

# Step 2: Water calibration
input("Submerge probe in distilled water at 20°C. Press Enter...")
ser.write(b'CALS,water\n')
# Device measures resonant frequency in water (f_water)
# This maps to SG = 1.000

# Step 3: Verify
ser.write(b'CALR\n')  # Read calibration constants
# Response: f_air=4250.3, f_water=3980.7, k=0.00123
```

### Temperature Compensation

Gravity readings are automatically temperature-corrected using the DS18B20 reading:
- Correction formula: **SG_corrected = SG_measured × [1 + 0.0000025 × (T_measured - T_calibration)²]**
- Calibration temperature defaults to 20°C
- Customizable via BLE characteristic or serial command

---

## Assembly Guide

### Soldering Order (by component height)

1. **Passives** (0402 resistors, capacitors) — all R/C first
2. **STM32L476RG** — align pin 1 dot, apply flux paste, hot-air reflow
3. **TPS62740** — VSON package, careful thermal pad soldering
4. **MCP73871** — QFN package with thermal pad
5. **BMP388** — LGA package, low solder paste
6. **SSD1306 OLED** — solder header, press-fit into clips
7. **USB-C receptacle** — SMD, through-hole tabs for strength
8. **AAA holder** — through-hole solder
9. **Piezo elements** — epoxy-bond to stainless vibrating tube
10. **DS18B20 probe** — connect to 3-pin header, silicone-seal the joint
11. **Senseair S8** — mount on PCB edge, connect silicone tube to CO₂ port
12. **EZO-pH** — stack on I²C header or connect via cable
13. **ESP32-C3 module** — solder last (Wi-Fi antenna orientation)

### Testing Checklist

- [ ] Verify 3.3V rail with USB-C connected (no batteries)
- [ ] Verify TPS62740 output with 2× AAA installed (no USB)
- [ ] Flash STM32 via SWD (ST-Link or Black Magic Probe)
- [ ] Verify DS18B20 reads ~25°C in air
- [ ] Verify BMP388 reads ~1013 hPa
- [ ] Verify S8 reads ~400-450 ppm in ambient air
- [ ] Run air/water calibration
- [ ] Verify BLE advertising visible on phone
- [ ] Verify Wi-Fi connection (configure via BLE)
- [ ] Submerge in water, verify gravity reads ~1.000

---

## Directory Structure

```
brew-sense/
├── README.md                  # This file
├── schematic/
│   ├── brew_sense.kicad_sch
│   ├── brew_sense.kicad_pcb
│   └── brew_sense.kicad_pro
├── firmware/
│   ├── Core/
│   │   ├── Src/
│   │   │   ├── main.c
│   │   │   ├── sensor_manager.c
│   │   │   ├── densitometer.c
│   │   │   ├── fermentation.c
│   │   │   ├── ble_service.c
│   │   │   ├── wifi_uplink.c
│   │   │   ├── power_manager.c
│   │   │   ├── display.c
│   │   │   ├── alarm.c
│   │   │   └── calibration.c
│   │   └── Inc/
│   │       ├── sensor_manager.h
│   │       ├── densitometer.h
│   │       ├── fermentation.h
│   │       ├── ble_service.h
│   │       ├── wifi_uplink.h
│   │       ├── power_manager.h
│   │       ├── display.h
│   │       ├── alarm.h
│   │       └── calibration.h
│   ├── Drivers/
│   │   └── STM32L4xx_HAL_Driver/
│   ├── Middlewares/
│   │   └── ST_BLE/
│   ├── Makefile
│   └── STM32L476RGTX_FLASH.ld
├── hardware/
│   ├── BOM.csv
│   └── enclosure/
│       └── brew_sense_shell.step
├── docs/
│   ├── api_reference.md
│   ├── assembly_guide.md
│   ├── densitometer_theory.md
│   └── fermentation_stages.md
└── scripts/
    ├── calibrate.py
    ├── read_brew.py
    ├── dashboard.py
    └── brewfather_sync.py
```

---

## Getting Started

### Flash Firmware

```bash
# Install STM32CubeIDE or arm-none-eabi-gcc toolchain
git clone https://github.com/jayis1/SoC-Device-Inventions.git
cd SoC-Device-Inventions/brew-sense/firmware

# Using Makefile + OpenOCD
make all
openocd -f interface/stlink.cfg -f target/stm32l4x.cfg -c "program build/brew_sense.elf verify reset exit"

# Or using STM32CubeProgrammer CLI
STM32_Programmer_CLI -c port=SWD -w build/brew_sense.elf -v -rst
```

### Read BLE Data

```bash
pip install bleak
python3 scripts/read_brew.py --mac AA:BB:CC:DD:EE:FF
```

### Calibrate

```bash
python3 scripts/calibrate.py --port /dev/ttyUSB0
```

### Monitor via MQTT

```bash
pip install paho-mqtt
python3 scripts/dashboard.py --mqtt mqtt://homeassistant.local:1883
```

### Sync to Brewfather

```bash
python3 scripts/brewfather_sync.py --device-id brewsense-001 --brewfather-key YOUR_KEY
```

---

## Use Cases

| Use Case | Configuration | Notes |
|----------|--------------|-------|
| Homebrew beer | Submersible in fermenter | Track FG, detect when to bottle |
| Wine fermentation | Thermowell mount + CO₂ port | Long-duration, 2-4 week monitoring |
| Kombucha | Submersible, pH critical | Alert when pH < 2.5 (over-fermented) |
| Sourdough starter | External mount, temp probe in jar | Track activity peaks for baking timing |
| Kimchi / sauerkraut | pH + CO₂ in mason jar lid | Food safety: alert if pH > 4.4 |
| Mead | Long-term (months), low-power mode | Detect stuck fermentation early |
| Distilling (legal) | Pressure mode for closed vessel | Track CO₂ + pressure for spunding |
| Science education | Classroom kit, OLED display | Real-time fermentation visualization |

---

## Safety Notes

- **Food safety**: All wetted parts (stainless tube, DS18B20 probe, pH probe) must be food-grade and properly sanitized
- **Pressure**: Never seal a fermenter unless using a pressure-rated vessel with relief valve
- **CO₂**: The S8 sensor samples headspace gas; ensure proper ventilation when working with active fermentations
- **Electrical**: The device is NOT waterproof in submersible mode without proper silicone potting of all seams
- **pH probe**: EZO-pH module must be calibrated with pH 4.0 and 7.0 buffers before first use

---

*Invented 2026-06-14 by jayis1*