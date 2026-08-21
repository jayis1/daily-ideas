# Therma Weave

**A multi-zone heated textile controller with distributed temperature sensing, adaptive PID control, BLE smartphone app, and safety watchdog — built on the ESP32-C3.**

---

## What It Does

Therma Weave is a smart heated-garment controller that clips to any jacket, blanket, glove, or seat cushion and turns dumb resistive heating elements into an intelligent, zone-controlled warmth system. It drives up to 4 independent heating zones, reads temperature from up to 8 thermistors distributed across the fabric, and runs PID control loops per zone to maintain target temperatures — all while continuously monitoring for overcurrent, over-temperature, and open-circuit faults.

Core capabilities:

- **4-zone MOSFET-driven heating output** — PWM-controlled N-channel MOSFETs drive resistive heating elements at up to 3A per zone (12V supply)
- **8-channel thermistor input** — multiplexed NTC 10kΩ thermistor reads across the garment for per-zone temperature feedback
- **Adaptive PID control** — each zone runs an independent PID loop targeting a user-set temperature (30–55°C), with anti-windup and output limiting
- **Continuous current monitoring** — high-side current sense amplifier (INA199) on each zone detects shorts, opens, and power consumption
- **BLE 5.0 smartphone control** — set target temps, monitor real-time zone temps/power, receive fault alerts, and update firmware OTA
- **OLED status display** — 128×64 SSD1306 shows current zone temps, duty cycles, battery voltage, and fault status at a glance
- **Safety watchdog** — hardware over-temperature cutout at 65°C, per-zone over-current shutdown at 4A, auto-retry with backoff
- **Battery or 12V powered** — runs from 3S LiPo (11.1V) or external 12V DC; onboard buck regulator provides 3.3V logic supply
- **Ambient sensing** — BME280 provides ambient temperature, humidity, and barometric pressure for context-aware adjustments
- **Activity-adaptive heating** — LSM6DS3 IMU detects activity level (still/walking/running); active zones reduce power to prevent overheating during exertion

Typical use cases:
- Heated motorcycle jacket with independent chest, back, sleeve, and collar zones
- Medical warming blanket with multi-zone PID control and safety logging
- Heated gloves with finger-level temperature monitoring
- Smart seat cushion with occupant-presence detection and zone heating
- Outdoor gear (hunting stands, sleeping bag liner) with battery-optimized heating

Battery life: **3–8 hours** depending on zone count and ambient temperature (3S 2200mAh LiPo).

---

## Block Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         THERMA WEAVE                                 │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │  BME280      │  │  LSM6DS3     │  │  8× NTC 10kΩ Thermistors   │ │
│  │  Ambient     │  │  6-axis IMU  │  │  (distributed in garment)   │ │
│  │  T/H/Press  │  │  Activity     │  │  Z1_T1 Z1_T2 Z2_T1 Z2_T2  │ │
│  │  I²C 0x76   │  │  I²C 0x6A    │  │  Z3_T1 Z3_T2 Z4_T1 Z4_T2  │ │
│  └──────┬───────┘  └──────┬───────┘  │  (via 74HC4051 mux)       │ │
│         │                  │          └─────────┬──────────────────┘ │
│         │ I²C              │ I²C               │ Analog muxed       │
│  ┌──────┴──────────────────┴────────────────────┤                   │
│  │              ESP32-C3-MINI-1                  │                   │
│  │                                               │                   │
│  │  ┌──────────────────────────────────┐        │                   │
│  │  │  Zone Controller (4× PID loops)  │        │                   │
│  │  │  Zone 0-3: target → duty cycle   │        │                   │
│  │  │  Anti-windup + output clamping   │        │                   │
│  │  └──────────────────────────────────┘        │                   │
│  │                                               │                   │
│  │  GPIO0  → I²C SDA                             │                   │
│  │  GPIO1  → I²C SCL                             │                   │
│  │  GPIO2  → Zone0 PWM (LEDC ch0)               │                   │
│  │  GPIO3  → Zone1 PWM (LEDC ch1)               │                   │
│  │  GPIO4  → Zone2 PWM (LEDC ch2)               │                   │
│  │  GPIO5  → Zone3 PWM (LEDC ch3)               │                   │
│  │  GPIO6  → MUX_A (74HC4051 select)            │                   │
│  │  GPIO7  → MUX_B                              │                   │
│  │  GPIO8  → MUX_C                              │                   │
│  │  GPIO9  → MUX_EN (active low)                │                   │
│  │  GPIO10 → ADC (thermistor mux output)         │                   │
│  │  GPIO11 → INA199 alert (overcurrent)         │                   │
│  │  GPIO12 → USB D+                              │                   │
│  │  GPIO13 → USB D-                              │                   │
│  │  GPIO14 → OLED RST                            │                   │
│  │  GPIO15 → OLED DC                             │                   │
│  │  GPIO18 → UART TX (debug)                     │                   │
│  │  GPIO19 → UART RX (debug)                     │                   │
│  │  GPIO20 → Safety shutdown (OR gate to MOSFET) │                   │
│  └────────────────────────────────────────────────┤                   │
│                                                     │                   │
│  ┌──────────────────┐  ┌───────────────────────────┤                   │
│  │  SSD1306 OLED    │  │  INA199 Current Sense     │                   │
│  │  128×64 I²C      │  │  4 channels (shared shunt)│                   │
│  │  0x3C            │  │  I²C 0x40 (4× shunt, mux)│                   │
│  └──────────────────┘  └───────────────────────────┘                   │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      POWER STAGE                                │  │
│  │                                                                  │  │
│  │  12V IN ──► LM2596 Buck (12V→5V 3A) ──► AP2112 LDO (5V→3.3V) │  │
│  │                                                                  │  │
│  │  Zone0: GPIO2 → TC4427 driver → IRF3205 MOSFET → Heater Z0     │  │
│  │  Zone1: GPIO3 → TC4427 driver → IRF3205 MOSFET → Heater Z1     │  │
│  │  Zone2: GPIO4 → TC4427 driver → IRF3205 MOSFET → Heater Z2     │  │
│  │  Zone3: GPIO5 → TC4427 driver → IRF3205 MOSFET → Heater Z3     │  │
│  │                                                                  │  │
│  │  Each zone: INA199A current sense → shared I²C via 74HC4051      │  │
│  │  Safety: GPIO20 (HW shutdown) → OR gate → all MOSFET gates     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Power Input: 12V DC barrel OR 3S LiPo (11.1V 2200mAh)        │  │
│  │  Charging: TP4056 for 3S (balance charger)                      │  │
│  │  Battery monitor: Voltage divider → ADC on ESP32-C3             │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (ESP32-C3-MINI-1)

| Pin | Function | Connected To | Notes |
|-----|----------|-------------|-------|
| GPIO0 | I²C SDA | BME280, LSM6DS3, INA199, SSD1306 | 4.7kΩ pull-up to 3.3V |
| GPIO1 | I²C SCL | BME280, LSM6DS3, INA199, SSD1306 | 4.7kΩ pull-up to 3.3V |
| GPIO2 | LEDC PWM ch0 | Zone 0 gate driver (TC4427 input) | 1kHz PWM, duty 0–100% |
| GPIO3 | LEDC PWM ch1 | Zone 1 gate driver | 1kHz PWM |
| GPIO4 | LEDC PWM ch2 | Zone 2 gate driver | 1kHz PWM |
| GPIO5 | LEDC PWM ch3 | Zone 3 gate driver | 1kHz PWM |
| GPIO6 | MUX_A | 74HC4051 select line A | Thermistor mux select |
| GPIO7 | MUX_B | 74HC4051 select line B | Thermistor mux select |
| GPIO8 | MUX_C | 74HC4051 select line C | Thermistor mux select |
| GPIO9 | MUX_EN | 74HC4051 enable (active low) | Enable thermistor mux |
| GPIO10 | ADC2_CH0 | 74HC4051 common output | Thermistor voltage divider |
| GPIO11 | GPIO_INPUT | INA199 ALERT (shared) | Overcurrent fault interrupt |
| GPIO12 | USB D+ | USB-C connector | CDC + OTA |
| GPIO13 | USB D- | USB-C connector | CDC + OTA |
| GPIO14 | GPIO_OUTPUT | SSD1306 RST | OLED reset (active low) |
| GPIO15 | GPIO_OUTPUT | SSD1306 DC | OLED data/command |
| GPIO18 | UART TX | Debug header | 115200 baud |
| GPIO19 | UART RX | Debug header | 115200 baud |
| GPIO20 | GPIO_OUTPUT | Safety shutdown OR gate | Active HIGH = kill all heaters |
| GPIO21 | ADC2_CH1 | Battery voltage divider | 12V × 100k/10k divider → ADC |

---

## Power Architecture

```
Power Input (12V DC barrel jack OR 3S LiPo 11.1V)
         │
         ├──► LM2596-5.0 (Buck, 12V→5V, 3A max)
         │       │
         │       ├──► AP2112-3.3 (LDO, 5V→3.3V, 600mA) ──► 3.3V Rail
         │       │       (ESP32-C3, BME280, LSM6DS3, OLED, mux)
         │       │
         │       └──► 5V Rail (INA199, TC4427 driver Vcc)
         │
         └──► 12V Heater Bus (direct to MOSFET drains)
              (Heating elements connected drain→GND with 12V supply)

Current monitoring:
  Each zone heater → 0.01Ω shunt → INA199A (gain 100V/V) → I²C
  Current = (V_shunt × 100) / R_shunt → full-scale 3.3A @ 3.3V ADC

Battery monitoring:
  VBAT × (100k / (100k + 10k)) → ADC2_CH1
  Full-scale: 12V × 100k/110k = 10.9V (within 3.3V ADC range with 3.3× headroom)

Safety chain:
  GPIO20 (SW_DISABLE) ──► 74HC32 OR gate ──► All MOSFET gate enables
  Over-temperature comparator (hardware) ──► Same OR gate
  → Either software OR hardware can force all heaters OFF independently
```

- **Quiescent current**: ~15mA (ESP32-C3 active, all heaters off)
- **Per-zone heating**: 0.5–3A at 12V = 6–36W per zone
- **Max total heating power**: 12A × 12V = 144W (with appropriate supply)
- **Battery life**: 3S 2200mAh ≈ 2–8 hours depending on duty cycle and zones active
- **Deep sleep**: <50µA (all MOSFETs off, BLE advertising only)

---

## Thermistor Multiplexing

The 8 thermistor channels are read through a single ADC using a 74HC4051 8:1 analog multiplexer:

```
NTC 10kΩ @ 25°C, β=3950
Voltage divider: 3.3V ──[10kΩ fixed]──┬──[NTC]── GND
                                      │
                              74HC4051 input ──→ common out ──→ GPIO10 (ADC)

Select lines: MUX_A (GPIO6), MUX_B (GPIO7), MUX_C (GPIO8)
Enable: MUX_EN (GPIO9, active low)

Channel mapping:
  CH0 → Zone 0, Thermistor 1 (e.g., chest left)
  CH1 → Zone 0, Thermistor 2 (e.g., chest right)
  CH2 → Zone 1, Thermistor 1 (e.g., upper back)
  CH3 → Zone 1, Thermistor 2 (e.g., lower back)
  CH4 → Zone 2, Thermistor 1 (e.g., left sleeve)
  CH5 → Zone 2, Thermistor 2 (e.g., right sleeve)
  CH6 → Zone 3, Thermistor 1 (e.g., collar)
  CH7 → Zone 3, Thermistor 2 (e.g., pocket)

Temperature calculation (Steinhart-Hart simplified):
  T = 1 / (1/T₀ + (1/β) × ln(R/R₀))
  Where T₀ = 298.15K, β = 3950, R₀ = 10000Ω
```

Each thermistor is scanned every 500ms, providing 250ms effective update rate per zone (2 thermistors per zone, averaged).

---

## PID Control

Each zone runs an independent PID controller:

```
                    ┌─────────────┐
  Target Temp ─────►│    Σ        │
          +         │  Error      │───► Kp ──────┐
          │         └─────────────┘               │
          │                    │                    │
          │               ┌────▼────┐             │
  Current Temp ──────────►│  Ki     │             │
          -               │(integral)│             │
                          └────┬────┘             │
                               │                    │
                          ┌────▼────┐             │
                          │  Kd     │             │
                          │(deriv)  │             │
                          └────┬────┘             │
                               │                    │
                          ┌────▼────────────────────▼────┐
                          │      Output = Kp*e + Ki*∫e  │
                          │              + Kd*de/dt      │
                          │                              │
                          │  Clamped to [0, 100]% duty   │
                          │  Anti-windup: clamp integral │
                          └──────────┬───────────────────┘
                                     │
                                     ▼
                              PWM duty cycle
                              → MOSFET gate
```

**Default PID parameters** (tuned for typical heated garment):

| Zone | Kp | Ki | Kd | Notes |
|------|----|----|----|-------|
| All | 2.5 | 0.08 | 0.4 | Starting values for ~50g fabric |
| | | | | Auto-tune via BLE app |

**Safety limits**:
- Maximum duty cycle: 95% (prevents 100% on stuck fault)
- Maximum temperature: 55°C (user setting), 65°C hard cutoff (hardware)
- Maximum current per zone: 3.5A (software shutdown at 4A)
- Over-temperature shutdown: all zones off, requires manual reset via BLE

---

## BLE GATT Service

```
Service UUID: 0x181A (Environmental Sensing, extended)
  ├── Char 0x2A6E (Temperature) — Zone 0 temp (read/notify) — float32 °C
  ├── Char 0x2A6E+1 — Zone 1 temp — float32 °C
  ├── Char 0x2A6E+2 — Zone 2 temp — float32 °C
  ├── Char 0x2A6E+3 — Zone 3 temp — float32 °C
  ├── Char 0x2A1C — Ambient temp (BME280) — float32 °C
  ├── Char 0x2A6F — Humidity (BME280) — uint16 ‰
  └── Char 0x2A1C — Battery voltage — uint16 mV

Custom Service UUID: 0xFFB0 (ThermaWeave Control)
  ├── Char 0xFFB1 — Zone 0 target temp (read/write) — uint8 °C (30–55)
  ├── Char 0xFFB2 — Zone 1 target temp (read/write) — uint8 °C
  ├── Char 0xFFB3 — Zone 2 target temp (read/write) — uint8 °C
  ├── Char 0xFFB4 — Zone 3 target temp (read/write) — uint8 °C
  ├── Char 0xFFB5 — Zone 0 duty cycle (read/notify) — uint8 %
  ├── Char 0xFFB6 — Zone 1 duty cycle (read/notify) — uint8 %
  ├── Char 0xFFB7 — Zone 2 duty cycle (read/notify) — uint8 %
  ├── Char 0xFFB8 — Zone 3 duty cycle (read/notify) — uint8 %
  ├── Char 0xFFB9 — Zone 0 current (read/notify) — uint16 mA
  ├── Char 0xFFBA — Zone 1 current (read/notify) — uint16 mA
  ├── Char 0xFFBB — Zone 2 current (read/notify) — uint16 mA
  ├── Char 0xFFBC — Zone 3 current (read/notify) — uint16 mA
  ├── Char 0xFFBD — Activity level (read/notify) — uint8 (0=still,1=walk,2=run)
  ├── Char 0xFFBE — All zones enable (write) — uint8 bitmask
  ├── Char 0xFFBF — Safety shutdown (write) — uint8 (0x01=shutdown, 0x02=reset)
  ├── Char 0xFFC0 — Fault status (read/notify) — uint8 bitmask
  ├── Char 0xFFC1 — Zone 0 PID Kp (read/write) — float32
  ├── Char 0xFFC2 — Zone 0 PID Ki (read/write) — float32
  ├── Char 0xFFC3 — Zone 0 PID Kd (read/write) — float32
  └── Char 0xFFFF — Device info (read) — string
```

BLE advertising packet (31 bytes):
```
[Flags] [Complete 16-bit UUID: FFB0] [Mfr-specific: zone0_temp(2), zone0_duty(1), battery(2), fault(1)]
```

---

## Activity-Adaptive Heating

The LSM6DS3 IMU provides activity classification that modulates zone temperatures:

| Activity | IMU Signal | Behavior |
|----------|-----------|----------|
| Still (sitting/standing) | Low accel variance | Full target temperature |
| Walking | Moderate accel variance, periodic | Target temp – 3°C |
| Running | High accel variance, high freq | Target temp – 6°C |
| Fall detected | Impact spike + orientation change | All zones OFF for 30s, then max heat |

This prevents the common problem of overheating during exertion and under-heating during rest.

---

## Mechanical

- **PCB**: 50mm × 70mm, 1.6mm FR4, 2-layer (power on bottom, signal on top)
- **Connectors**: JST-PH 4-pin for each heater zone (12V, GND, 2× thermistor)
- **Power connector**: XT30 for 12V input, JST-PH 3-pin for battery balance
- **Mounting**: 4× M3 mounting holes, clips into garment pocket
- **Heat sink**: MOSFETs on bottom copper pour, thermal vias to ground plane
- **Enclosure**: 3D-printed PETG case, IP54 rated (splash resistant), 56mm × 76mm × 22mm
- **Cable harness**: 4× braided 4-conductor cables (2× heater wire, 2× thermistor wire) with JST-PH terminals
- Weight: 45g (PCB + components), 65g (with enclosure)

```
┌─────────────────────────────────────────────────────────┐
│  Therma Weave PCB — 50mm × 70mm                         │
│                                                          │
│  ┌──────────┐                     ┌───────────────────┐ │
│  │ ESP32-C3 │                     │  OLED 128×64      │ │
│  │ MINI-1   │                     │  SSD1306          │ │
│  └──────────┘                     └───────────────────┘ │
│                                                          │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐    ┌────────────────┐ │
│  │Z0 │  │Z1 │  │Z2 │  │Z3 │    │  BME280         │ │
│  │PWM│  │PWM│  │PWM│  │PWM│    │  + LSM6DS3      │ │
│  └─┬──┘  └─┬──┘  └─┬──┘  └─┬──┘    └────────────────┘ │
│    │       │       │       │                             │
│  ┌─▼───────▼───────▼───────▼──┐  ┌────────────────┐   │
│  │  TC4427 ×4    IRF3205 ×4  │  │  74HC4051 MUX  │   │
│  │  MOSFET driver board       │  │  + INA199       │   │
│  └────────────────────────────┘  └────────────────┘   │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐   │
│  │ LM2596   │  │ AP2112   │  │ XT30 ── 12V IN     │   │
│  │ Buck     │  │ LDO 3.3V │  │ JST-PH ── Battery  │   │
│  └──────────┘  └──────────┘  └────────────────────┘   │
│                                                          │
│  ○ JST-PH Z0   ○ JST-PH Z1   ○ JST-PH Z2   ○ JST-PH Z3 │
└─────────────────────────────────────────────────────────┘
```

---

## Firmware Architecture

```
firmware/
├── main/
│   ├── app_main.c          # Entry point, NVS init, task launch
│   ├── zone_controller.c   # PID loops, PWM output, temperature target
│   ├── zone_controller.h
│   ├── temp_sensor.c       # 74HC4051 mux + ADC thermistor reading
│   ├── temp_sensor.h
│   ├── current_monitor.c   # INA199 current sense + fault detection
│   ├── current_monitor.h
│   ├── ble_service.c       # GATT server, advertising, control chars
│   ├── ble_service.h
│   ├── oled_display.c      # SSD1306 status display
│   ├── oled_display.h
│   ├── activity_detect.c   # LSM6DS3 IMU, step count, fall detect
│   ├── activity_detect.h
│   ├── ambient_sensor.c    # BME280 ambient T/H/P
│   ├── ambient_sensor.h
│   ├── power_manager.c     # Battery monitor, deep sleep, duty cycling
│   ├── power_manager.h
│   ├── safety_watchdog.c   # Over-temp, over-current, open-circuit detection
│   ├── safety_watchdog.h
│   └── nvs_storage.c      # Save/load settings to flash
│   └── nvs_storage.h
├── CMakeLists.txt
└── sdkconfig.defaults
```

### Key Firmware Flow

```c
void app_main(void) {
    nvs_init();
    i2c_bus_init();
    adc_init();
    pwm_init();

    temp_sensor_init();     // 74HC4051 + ADC
    current_monitor_init(); // INA199
    ambient_sensor_init();  // BME280
    activity_detect_init(); // LSM6DS3
    oled_display_init();    // SSD1306
    ble_service_init();     // BLE GATT
    safety_watchdog_init(); // Hardware safety

    zone_controller_init(); // PID loops, load targets from NVS

    // Create FreeRTOS tasks
    xTaskCreate(temp_sensor_task,    "temp",   4096, NULL, 5, NULL);  // 2Hz per channel
    xTaskCreate(pid_control_task,    "pid",    4096, NULL, 7, NULL);  // 4Hz per zone
    xTaskCreate(current_monitor_task,"current",2048, NULL, 6, NULL);  // 10Hz per zone
    xTaskCreate(ble_task,           "ble",    4096, NULL, 3, NULL);
    xTaskCreate(oled_task,          "oled",   3072, NULL, 2, NULL);  // 1Hz update
    xTaskCreate(activity_task,      "imu",    2048, NULL, 4, NULL);  // 50Hz sample
    xTaskCreate(safety_task,        "safety",  2048, NULL, 8, NULL);  // 10Hz check
    xTaskCreate(power_task,         "power",  2048, NULL, 1, NULL);  // 0.1Hz check
}
```

### Task Priorities

| Task | Priority | Rate | Stack | Description |
|------|----------|------|-------|-------------|
| safety | 8 (highest) | 10Hz | 2048 | Over-temp/over-current watchdog |
| pid_control | 7 | 4Hz | 4096 | PID loop computation + PWM update |
| current_monitor | 6 | 10Hz | 2048 | Current sense read + fault detect |
| temp_sensor | 5 | 2Hz (per ch) | 4096 | Thermistor mux scan + conversion |
| activity | 4 | 50Hz | 2048 | IMU sampling + activity classification |
| ble | 3 | Event-driven | 4096 | BLE GATT server |
| oled | 2 | 1Hz | 3072 | Display update |
| power | 1 (lowest) | 0.1Hz | 2048 | Battery monitor + sleep management |

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | ESP32-C3-MINI-1 | Module | 1 | $2.10 | WiFi/BLE5 SoC |
| 2 | BME280 | LGA-8 2.5×2.5 | 1 | $2.50 | Ambient T/H/P |
| 3 | LSM6DS3TR-C | LGA-14 2.5×3 | 1 | $2.20 | 6-axis IMU |
| 4 | INA199A2DBVR | SOT-23-5 | 1 | $0.65 | Current sense amp (100V/V) |
| 5 | 74HC4051PW | TSSOP-16 | 1 | $0.30 | 8:1 analog mux |
| 6 | TC4427COA | SOIC-8 | 2 | $0.80 | MOSFET driver (2 per IC, 2 ICs = 4 channels) |
| 7 | IRF3205SPbF | D2PAK-3 | 4 | $0.70 | N-channel MOSFET (55V, 110A, 8mΩ) |
| 8 | SSD1306 | Module 128×64 | 1 | $1.20 | I²C OLED display |
| 9 | LM2596-5.0 | TO-263-5 | 1 | $0.90 | Buck converter 12V→5V 3A |
| 10 | AP2112-3.3 | SOT-223 | 1 | $0.30 | LDO 5V→3.3V 600mA |
| 11 | NTC 10kΩ 3950 | 0805 | 8 | $0.05 | Thermistors (distributed) |
| 12 | 0.01Ω 1% shunt | 2512 | 1 | $0.20 | Current sense shunt |
| 13 | 74HC32 | SOIC-14 | 1 | $0.20 | Quad OR gate (safety) |
| 14 | LM393 | SOIC-8 | 1 | $0.25 | Comparator (HW over-temp cutoff) |
| 15 | Passives (R/C/L) | 0402/0603 | ~40 | $0.60 | Pull-ups, dividers, decoupling |
| 16 | XT30 connector | Panel mount | 1 | $0.40 | 12V power input |
| 17 | JST-PH 4-pin | SMD | 4 | $0.10 | Heater zone connectors |
| 18 | JST-PH 3-pin | SMD | 1 | $0.10 | Battery connector |
| 19 | USB-C receptacle | 16-pin SMD | 1 | $0.35 | USB power + data |
| 20 | Inductor 68µH | SMD | 1 | $0.40 | LM2596 inductor |
| 21 | Schottky diode | SOD-123 | 1 | $0.10 | Reverse polarity protection |
| 22 | PCB 2-layer 50×70mm | Rect | 1 | $1.50 | JLCPCB |

**Total estimated BOM: ~$18.50** (qty 1)

---

## Safety Design

Therma Weave has multiple independent safety layers:

### Layer 1: Software Watchdog (fastest response)
- Each zone: if current > 4A → immediately set PWM to 0%, flag fault
- Each zone: if thermistor reads > 65°C → immediately set PWM to 0%, flag fault
- All faults logged to NVS with timestamp

### Layer 2: Hardware Comparator (analog, independent of MCU)
- LM393 comparator monitors a voltage divider from the thermistor bus
- If any thermistor exceeds the hardware threshold (~70°C), LM393 output goes LOW
- LM393 output feeds 74HC32 OR gate → forces all MOSFET gate drivers LOW
- This path is independent of ESP32-C3 — works even if MCU crashes

### Layer 3: Thermal Fuse (one-time, fail-safe)
- Each heater zone has a 75°C thermal fuse in series (non-resettable)
- If all other safety layers fail, the fuse blows permanently
- Must be replaced by opening the garment

### Layer 4: BLE Alert
- On any fault, BLE characteristic 0xFFC0 is notified
- Smartphone app shows alert with zone ID, fault type, and timestamp
- Manual reset required via BLE (char 0xFFBF write 0x02)

---

## Directory Structure

```
therma-weave/
├── README.md                  # This file
├── schematic/
│   ├── therma-weave.kicad_sch
│   ├── therma-weave.kicad_pcb
│   └── therma-weave.kicad_pro
├── firmware/
│   ├── main/
│   │   ├── app_main.c
│   │   ├── zone_controller.c
│   │   ├── zone_controller.h
│   │   ├── temp_sensor.c
│   │   ├── temp_sensor.h
│   │   ├── current_monitor.c
│   │   ├── current_monitor.h
│   │   ├── ble_service.c
│   │   ├── ble_service.h
│   │   ├── oled_display.c
│   │   ├── oled_display.h
│   │   ├── activity_detect.c
│   │   ├── activity_detect.h
│   │   ├── ambient_sensor.c
│   │   ├── ambient_sensor.h
│   │   ├── power_manager.c
│   │   ├── power_manager.h
│   │   ├── safety_watchdog.c
│   │   ├── safety_watchdog.h
│   │   ├── nvs_storage.c
│   │   └── nvs_storage.h
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── hardware/
│   ├── BOM.csv
│   ├── gerbers/
│   └── enclosure/
│       └── therma_weave_case.step
├── docs/
│   ├── assembly_guide.md
│   ├── api_reference.md
│   ├── safety_manual.md
│   └── pid_tuning_guide.md
└── scripts/
    ├── therma_weave_ble.py      # BLE control script
    ├── pid_autotune.py           # PID auto-tune tool
    └── data_logger.py            # CSV data logger
```

---

## Getting Started

### Flash Firmware

```bash
# Install ESP-IDF v5.3+
git clone https://github.com/jayis1/SoC-Device-Inventions.git
cd SoC-Device-Inventions/therma-weave/firmware
idf.py set-target esp32c3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

### Control via BLE (Python)

```bash
pip install bleak
python3 scripts/therma_weave_ble.py --mac AA:BB:CC:DD:EE:FF --zone 0 --target 40
```

### Monitor Data

```python
from therma_weave_ble import ThermaWeaveClient

tw = ThermaWeaveClient("AA:BB:CC:DD:EE:FF")
tw.connect()

# Read all zone temperatures
temps = tw.read_zone_temps()
print(f"Z0: {temps[0]:.1f}°C  Z1: {temps[1]:.1f}°C  Z2: {temps[2]:.1f}°C  Z3: {temps[3]:.1f}°C")

# Set target temperature for zone 0
tw.set_target_temp(0, 42)  # 42°C

# Read current draw per zone
currents = tw.read_zone_currents()
print(f"Z0: {currents[0]:.0f}mA  Z1: {currents[1]:.0f}mA  Z2: {currents[2]:.0f}mA  Z3: {currents[3]:.0f}mA")

# Emergency shutdown
tw.emergency_shutdown()
```

### Auto-Tune PID

```bash
# Connect to device and run Ziegler-Nichols auto-tune
python3 scripts/pid_autotune.py --mac AA:BB:CC:DD:EE:FF --zone 0
```

---

## Safety Notes

- **Burn risk**: Heating elements can reach 55°C+. Always test temperature before prolonged skin contact.
- **Fire risk**: Never operate without thermistor feedback. If thermistors read disconnected, all zones shut down.
- **Battery safety**: Use only protected 3S LiPo packs with balance charging. Never short or puncture.
- **Water resistance**: The enclosure is IP54 (splash resistant). Do not submerge.
- **Maximum load**: Do not exceed 3A per zone or 12A total. Use appropriate wire gauge (≥18 AWG for heater leads).
- **Medical caution**: Not FDA approved. Not for therapeutic use on insensate skin or open wounds.

---

## License

MIT — build it, wear it, improve it.

---

*Device #12 in the [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions) collection.*