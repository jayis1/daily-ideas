# Flux Ring

**A finger-worn magnetic field explorer with haptic + LED field feedback, real-time BLE streaming, and spatial mapping via phone app.**

---

## What It Does

The Flux Ring is a ring-sized PCB you wear on your index finger. As you move your hand through space, it continuously measures the 3-axis magnetic field vector and gives you **immediate, eyes-free feedback** about the invisible magnetic landscape around you:

- **RGB LED** — shifts from blue (ambient Earth field) through green, yellow, to red (strong field near magnets, speakers, current-carrying wires)
- **Vibration motor** — pulses faster as field strength increases; different patterns for N vs S pole dominance
- **OLED display** — shows field magnitude in Gauss/Tesla, vector components, and compass heading
- **BLE 5.0 streaming** — live 3-axis field data + orientation sent to a companion phone app that builds a **spatial magnetic field map** as you walk around your space

### Use Cases

| Application | How Flux Ring Helps |
|-------------|---------------------|
| EMC troubleshooting | Trace magnetic noise sources on PCBs, near power supplies, or in enclosures |
| Speaker design | Map fringing fields, check polarity of magnets, find null points |
| Current sensing | Detect and trace AC current flow in walls, cables, and bus bars (non-contact) |
| Magnet quality | Verify permanent magnet strength, find weak/depolarized magnets |
| Education | Let students *feel* magnetic fields — make the invisible tangible |
| Hidden magnet detection | Find concealed magnets in furniture, cases, or security tags |
| Compass navigation | Acts as a precision digital compass with tilt compensation |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                       FLUX RING                              │
│                                                              │
│  ┌───────────────┐   ┌───────────────┐   ┌──────────────┐   │
│  │ MMC5983MA     │   │ LIS2DH12      │   │ MS5837-02BA  │   │
│  │ 3-Axis Mag   │   │ 3-Axis Accel  │   │ Barometer     │   │
│  │ I²C 0x30     │   │ I²C 0x19      │   │ I²C 0x76      │   │
│  └───────┬───────┘   └───────┬───────┘   └──────┬───────┘   │
│          │                   │                   │            │
│          └───────────────────┼───────────────────┘            │
│                              │ I²C bus (400kHz)              │
│                                                              │
│  ┌───────────────────────────▼──────────────────────────┐   │
│  │                   nRF52840-QIAA                      │   │
│  │  ┌──────────┐  ┌─────────────┐  ┌────────────────┐  │   │
│  │  │ ARM M4F  │  │ BLE 5.0    │  │ 64MHz FPU      │  │   │
│  │  │ 64MHz    │  │ Long Range │  │ Vector Math     │  │   │
│  │  └──────────┘  └─────────────┘  └────────────────┘  │   │
│  │  ┌──────────────────────────────────────────────────┐│   │
│  │  │ Field Mapping Engine: tilt-comp, spatial stream   ││   │
│  │  └──────────────────────────────────────────────────┘│   │
│  └──────────────────────┬────────────────────────────────┘   │
│                          │                                    │
│  ┌───────────┐  ┌────────▼────────┐  ┌──────────────────┐   │
│  │ SSD1306   │  │ WS2812B-2020   │  │ Vibration Motor  │   │
│  │ OLED 32x64│  │ RGB LED        │  │ DRV2603L driver  │   │
│  │ I²C 0x3C  │  │ GPIO           │  │ I²C 0x5A         │   │
│  └───────────┘  └────────────────┘  └──────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Power: MCP73831 charger + TLV73333 LDO + 200mAh Lipo│   │
│  │ USB-C for charging + UART flash                     │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (nRF52840-QIAA)

| Pin | Function | Connected To |
|-----|----------|-------------|
| P0.02 | I²C SDA | All I²C devices (4.7k pull-up) |
| P0.03 | I²C SCL | All I²C devices (4.7k pull-up) |
| P0.04 | ADC input | Battery voltage divider (1:2) |
| P0.05 | GPIO output | WS2812B data line |
| P0.06 | GPIO output | DRV2603L EN (haptic enable) |
| P0.07 | UART TX | Debug/flash (via USB-C) |
| P0.08 | UART RX | Debug/flash (via USB-C) |
| P0.09 | GPIO input | Capacitive touch pad (tap to cycle mode) |
| P0.11 | GPIO output | MMC5983MA SET/RESET (magnetic set pulse) |
| P0.12 | GPIO output | OLED RESET |
| P0.13 | GPIO output | LIS2DH12 INT1 (data-ready) |
| P0.14 | GPIO input | LIS2DH12 INT2 (wake-on-motion) |
| P0.15 | USB D+ | USB-C connector |
| P0.16 | USB D- | USB-C connector |
| P0.17 | GPIO output | CHARGE_STAT LED (red) |
| P0.18 | GPIO output | Mode LED (green) |
| P0.19 | SPI CLK | W25Q16 flash (logging) |
| P0.20 | SPI MISO | W25Q16 flash |
| P0.21 | SPI MOSI | W25Q16 flash |
| P0.22 | SPI CS | W25Q16 flash |
| P0.24 | GPIO output | Motor MOSFET gate (direct drive fallback) |
| P0.25 | ADC input | Motor current sense (optional) |
| P0.26 | GPIO input | Boot button (hold at power-on for DFU) |
| P0.27 | GPIO output | LDO EN (power gate for sensors) |
| P0.28 | GPIO input | MMC5983MA INT (data-ready) |
| P0.29 | GPIO output | MS5837 CSB (chip select, active low) |
| P0.30 | GPIO output | DRV2603L I²C address select |
| P0.31 | GPIO output | Power-on LED (white) |

---

## Power Architecture

```
USB-C (5V) ──► MCP73831 ──► Lipo (3.7V 200mAh) ──► TLV73333 (3.3V) ──► VDD

Quiescent: ~8µA (system off, RTC on)
BLE advertising only: ~15µA avg
Active streaming (100Hz mag + BLE): ~4.5mA avg → ~44h theoretical, ~30h typical
Active + OLED + haptic: ~12mA peak, ~18h typical
Deep sleep (wake on motion): ~25µA
```

**Power modes:**

| Mode | Sample Rate | BLE | OLED | Haptic | Current | Battery Life |
|------|-------------|-----|------|--------|----------|-------------|
| Sleep | Off | Off | Off | Off | 8µA | 2.5 years |
| Monitor | 10Hz | Adv | Off | Off | 0.8mA | ~10 days |
| Explore | 100Hz | Connected | On | On | 6mA | ~30h |
| Mapping | 200Hz | Connected+Stream | On | On | 12mA | ~16h |
| Compass | 25Hz | Adv | On | Off | 2mA | ~4 days |

---

## Mechanical

- PCB: 22mm x 18mm x 1.2mm, 4-layer FR4, ENIG finish
- Overall ring size: 22mm x 18mm x 10mm (with battery on top deck)
- Battery sits on a flex PCB tongue that wraps around finger
- Adjustable ring band: 3D-printed TPU, sizes S/M/L
- Sensor openings: MMC5983MA on top face (closest to field), LIS2DH12 adjacent
- OLED on inner face (visible when you tilt your hand up)
- WS2812B on outer face (visible to others, great for demos)
- Capacitive touch pad on bottom (between fingers, tap to cycle mode)
- USB-C on the "hinge" end
- IP54 splash resistant (conformal coating, no gaskets)
- Weight: ~12g with battery

---

## Firmware Architecture

```
firmware/
├── main/
│   ├── app_main.c            # Entry point, power init, task launch
│   ├── mag_sensor.c          # MMC5983MA driver, set/reset, read 3-axis
│   ├── accel_sensor.c        # LIS2DH12 driver, read 3-axis
│   ├── baro_sensor.c         # MS5837 driver, read pressure/altitude
│   ├── field_engine.c        # Tilt compensation, vector math, magnitude
│   ├── haptic_feedback.c     # DRV2603L driver, pattern generation
│   ├── led_feedback.c        # WS2812B color mapping from field strength
│   ├── oled_display.c        # SSD1306 driver, compass, magnitude, graph
│   ├── ble_service.c         # GATT server + advertising + stream mode
│   ├── data_logger.c         # W25Q16 SPI flash logging
│   ├── power_manager.c       # Sleep modes, wake-on-motion, charge monitor
│   ├── touch_input.c         # Capacitive touch debounce, mode cycling
│   └── compass.c             # Tilt-compensated compass algorithm
├── CMakeLists.txt
└── sdkconfig.defaults
```

### Key Firmware Flow

```c
void app_main(void) {
    power_manager_init();
    i2c_bus_init();
    mag_sensor_init();       // MMC5983MA: set/reset cycle for offset cancel
    accel_sensor_init();     // LIS2DH12: configure wake-on-motion
    baro_sensor_init();     // MS5837: oversample x4
    oled_display_init();    // SSD1306: 32x64 monochrome
    haptic_feedback_init(); // DRV2603L: load waveform library
    led_feedback_init();    // WS2812B: off
    ble_service_init();     // Start advertising
    data_logger_init();     // Mount SPI flash
    
    mode_t current_mode = MODE_EXPLORE;
    
    while (true) {
        // Read sensors
        mag_data_t mag = mag_sensor_read();    // 3-axis Gauss
        accel_data_t acc = accel_sensor_read(); // 3-axis g
        baro_data_t baro = baro_sensor_read();
        
        // Tilt-compensate magnetic vector
        field_vector_t field = field_engine_compensate(&mag, &acc);
        
        // Compute derived values
        float magnitude_gauss = field_engine_magnitude(&field);
        compass_heading_t heading = compass_compute(&field, &acc);
        
        // Feedback
        led_feedback_set_field(magnitude_gauss, field.dominant_pole);
        haptic_feedback_set_intensity(magnitude_gauss, field.dominant_pole);
        oled_display_update(field, magnitude_gauss, heading, current_mode);
        
        // BLE streaming (mapping mode)
        if (current_mode == MODE_MAPPING && ble_is_connected()) {
            ble_stream_sample(&field, &acc, &baro, heading);
        }
        
        // Log to flash
        data_logger_append(&field, &acc, heading);
        
        // Power management
        power_manager_wait_next_tick(mode_sample_rate(current_mode));
    }
}
```

---

## Magnetic Field Processing

The MMC5983MA provides ±8 Gauss full-scale range with 0.4 mG resolution (24-bit). The on-chip SET/RESET function cancels sensor offset every 10 seconds for drift-free measurements.

### Tilt Compensation Algorithm

Raw magnetic vector **M** = (Mx, My, Mz) is measured in sensor frame. Accelerometer **A** = (Ax, Ay, Az) gives the gravity direction. Tilt compensation projects **M** onto the horizontal plane:

```
1. Normalize gravity: g = A / |A|
2. Roll angle: φ = atan2(Ay, Az)
3. Pitch angle: θ = atan2(-Ax, Ay*sin(φ) + Az*cos(φ))
4. Compensated horizontal:
   Mx_h = Mx*cos(θ) + My*sin(φ)*sin(θ) + Mz*cos(φ)*sin(θ)
   My_h = My*cos(φ) - Mz*sin(φ)
5. Heading: α = atan2(My_h, Mx_h)
```

### Field Strength Color Map

| Magnitude (Gauss) | LED Color | Haptic Pulse |
|-------------------|-----------|-------------|
| 0.0 – 0.5 (Earth field) | Soft blue | None |
| 0.5 – 1.0 | Cyan | Every 2s |
| 1.0 – 3.0 | Green | Every 1s |
| 3.0 – 10.0 | Yellow | Every 0.5s |
| 10.0 – 50.0 | Orange | Every 0.25s |
| 50.0 – 800.0 (near magnet) | Red | Continuous |

N-pole dominant → warm pulse rhythm
S-pole dominant → cool pulse rhythm

---

## BLE GATT Service

```
Service UUID: 0xFFB0 (FluxRing)
  ├── Char 0xFFB1: Field Vector X (read/notify) — float32 (Gauss)
  ├── Char 0xFFB2: Field Vector Y (read/notify) — float32
  ├── Char 0xFFB3: Field Vector Z (read/notify) — float32
  ├── Char 0xFFB4: Field Magnitude (read/notify) — float32
  ├── Char 0xFFB5: Compass Heading (read/notify) — uint16 (0–359 deg)
  ├── Char 0xFFB6: Dominant Pole (read) — uint8 (0=none, 1=N, 2=S)
  ├── Char 0xFFB7: Sample Rate (read/write) — uint8 (0=10Hz, 1=100Hz, 2=200Hz)
  ├── Char 0xFFB8: Mode (read/write) — uint8 (0=monitor, 1=explore, 2=mapping, 3=compass)
  ├── Char 0xFFB9: Battery Level (read) — uint8 (0–100%)
  └── Char 0xFFBA: Device Info (read) — string
```

**Stream mode** (mapping): When BLE notification is enabled on 0xFFB1–0xFFB5, the device sends a packed binary packet at the configured sample rate:

```
[timestamp(4)] [Mx(4)] [My(4)] [Mz(4)] [Ax(2)] [Ay(2)] [Az(2)] [heading(2)] = 22 bytes/sample
```

At 200Hz, this is 4.4KB/s — well within BLE 5.0 throughput.

---

## Phone App — Spatial Mapper

The companion phone app receives the BLE stream and uses the phone's IMU (or the ring's accelerometer data) to track the user's hand position in space. Each magnetic field sample is tagged with a 3D position estimate, building a **magnetic field point cloud** that can be visualized as:

- 2D heat map (top-down slice)
- 3D volumetric rendering (color = field strength)
- Vector field (arrows showing direction + magnitude)
- Time-lapse animation (for AC fields)

Export formats: CSV (point cloud), VTK (3D visualization), PNG (heat map).

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | nRF52840-QIAA | QFN-48 6x6 | 1 | $3.80 | BLE 5.0, ARM M4F |
| 2 | MMC5983MA | LGA-16 3x3 | 1 | $2.50 | 3-axis AMR, ±8Gauss |
| 3 | LIS2DH12 | LGA-12 2x2 | 1 | $0.70 | 3-axis accel |
| 4 | MS5837-02BA | QFN-8 3.3x3.3 | 1 | $3.20 | Barometric pressure |
| 5 | SSD1306 OLED | Custom 32x64 | 1 | $1.80 | Monochrome display |
| 6 | WS2812B-2020 | 2x2 | 1 | $0.15 | RGB LED |
| 7 | DRV2603L | WSON-8 2x2 | 1 | $0.90 | Haptic driver |
| 8 | W25Q16JVSIQ | SOIC-8 | 1 | $0.45 | 16Mbit SPI flash |
| 9 | MCP73831 | SOT-23-5 | 1 | $0.40 | Lipo charger |
| 10 | TLV73333 | SOT-23-5 | 1 | $0.30 | 3.3V LDO, 300mA |
| 11 | Lipo 200mAh | 302020 pouch | 1 | $2.80 | 3.7V |
| 12 | USB-C receptacle | 16-pin SMD | 1 | $0.35 | Power + data |
| 13 | Vibration motor | 6x2.7mm coin | 1 | $0.60 | ERM |
| 14 | Capacitive touch pad | PCB trace | 1 | $0.00 | On-board electrode |
| 15 | Passives (R/C/L) | 0402 | ~35 | $0.55 | Pullups, decoupling, dividers |
| 16 | PCB 4-layer 22x18mm | Rect | 1 | $1.20 | JLCPCB |

**Total estimated BOM: ~$19.70** (qty 1)

---

## Calibration

### Hard Iron Calibration

The MMC5983MA SET/RESET function cancels most sensor offset, but nearby ferrous parts on the PCB (USB-C shell, motor core) create a hard-iron offset. The firmware performs a **figure-8 calibration** on first boot:

1. User rotates the ring in a figure-8 pattern for 10 seconds
2. Firmware records min/max of each axis
3. Offset = (max + min) / 2, scale = (max - min) / 2
4. Stores calibration in flash (retained across resets)

### Soft Iron Calibration

If the ring is worn near a steel watch band or other soft-iron objects, the distortion matrix is computed from the figure-8 data using an ellipsoid fitting algorithm (see `docs/calibration_guide.md`).

---

## Operating Modes

### Mode: Monitor (10Hz, BLE adv only)

Low-power continuous monitoring. OLED off. Haptic off. LED slow-pulse. Logs to flash. Good for all-day wear, detecting unusual fields.

### Mode: Explore (100Hz, BLE connected)

Full interactivity. OLED shows compass + magnitude. LED and haptic respond to field changes. Best for walking around and investigating.

### Mode: Mapping (200Hz, BLE streaming)

Maximum data rate. Streams every sample to phone app for spatial map building. OLED shows stream status. Haptic brief pulse on start/stop.

### Mode: Compass (25Hz, BLE adv)

Tilt-compensated digital compass. OLED shows heading + cardinal direction. LED shows N (red) vs S (blue) as you rotate. Low power for hiking/navigation.

**Mode switching:** Tap the capacitive touch pad (between fingers) to cycle modes. Double-tap to enter/exit mapping mode.

---

## Data Logging

The W25Q16 SPI flash stores up to 2MB of field data. At 100Hz (explore mode), each 22-byte sample gives ~90,000 samples = 15 minutes of continuous logging. At 10Hz (monitor mode), ~2.5 hours.

Log format:
```
Header (32 bytes): magic, version, sample_rate, start_time, calibration_params
Samples (22 bytes each): timestamp, Mx, My, Mz, Ax, Ay, Az, heading
```

Data is retrieved via BLE or USB-C (appears as mass storage or CDC console).

---

## Directory Structure

```
flux-ring/
├── README.md                  # This file
├── schematic/
│   ├── flux_ring.kicad_sch
│   ├── flux_ring.kicad_pcb
│   └── flux_ring.kicad_pro
├── firmware/
│   ├── main/
│   │   ├── app_main.c
│   │   ├── mag_sensor.c
│   │   ├── mag_sensor.h
│   │   ├── accel_sensor.c
│   │   ├── accel_sensor.h
│   │   ├── baro_sensor.c
│   │   ├── baro_sensor.h
│   │   ├── field_engine.c
│   │   ├── field_engine.h
│   │   ├── haptic_feedback.c
│   │   ├── haptic_feedback.h
│   │   ├── led_feedback.c
│   │   ├── led_feedback.h
│   │   ├── oled_display.c
│   │   ├── oled_display.h
│   │   ├── ble_service.c
│   │   ├── ble_service.h
│   │   ├── data_logger.c
│   │   ├── data_logger.h
│   │   ├── power_manager.c
│   │   ├── power_manager.h
│   │   ├── touch_input.c
│   │   ├── touch_input.h
│   │   ├── compass.c
│   │   └── compass.h
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── hardware/
│   └── BOM.csv
├── scripts/
│   ├── read_flux.py            # BLE reader + live plot
│   ├── calibrate.py            # Figure-8 calibration helper
│   ├── export_log.py           # Export flash log to CSV/VTK
│   └── spatial_map.py         # Generate 2D/3D field maps
└── docs/
    ├── calibration_guide.md
    ├── assembly_guide.md
    └── api_reference.md
```

---

## Getting Started

### Flash Firmware

```bash
# Install nRF Connect SDK (nRF5 SDK v2.6+)
git clone https://github.com/jayis1/SoC-Device-Inventions.git
cd SoC-Device-Inventions/flux-ring/firmware
west build -b nrf52840dk_nrf52840
west flash
```

### Calibrate

1. Power on the ring (it auto-enters calibration on first boot)
2. Rotate your hand in a figure-8 pattern for 10 seconds
3. The OLED shows "CAL OK" when done
4. You're ready to explore!

### Read BLE Data

```bash
# Using the provided Python script
pip install bleak numpy matplotlib
python3 scripts/read_flux.py --mac AA:BB:CC:DD:EE:FF
```

### Build a Spatial Map

```bash
# Start streaming mode (double-tap the ring)
python3 scripts/spatial_map.py --mac AA:BB:CC:DD:EE:FF --output field_map.vtk
```

---

## Safety Notes

- The MMC5983MA is an AMR (Anisotropic Magnetoresistance) sensor — it is **not** affected by static magnetic fields below 80 Gauss and will not be permanently damaged by strong magnets
- Do not expose to fields > 1000 Gauss (rare earth magnets at <1cm) — sensor reading will saturate but recover after SET/RESET cycle
- The device is **not** a medical device — do not use for clinical electromagnetic exposure assessments
- USB-C is for charging and data only — do not connect to non-standard USB-C sources

---

## Comparison with Existing Tools

| Feature | Flux Ring | Handheld Gauss Meter | Phone Compass | Hall Probe |
|---------|-----------|---------------------|-------------|------------|
| Wearable | ✅ Ring | ❌ Handheld | ✅ Pocket | ❌ Probe |
| Eyes-free feedback | ✅ LED + haptic | ❌ Screen only | ❌ Screen | ❌ Screen |
| 3-axis measurement | ✅ | ✅ (some) | ❌ 1-axis | ✅ |
| Spatial mapping | ✅ BLE stream + app | ❌ | ❌ | ❌ |
| Tilt compensation | ✅ Auto | ❌ Manual | ✅ | ❌ |
| Price range | ~$20 | $30–200 | $0 (built-in) | $100–500 |
| Battery life | 30h | 8–20h | 4–8h | 6–12h |
| Resolution | 0.4 mG | 0.1–1 mG | ~50 mG | 0.01 mG |

---

*Invented 2026-06-14 by jayis1*