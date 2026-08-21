# Tremor Tile

**A credit-card-sized structural health monitor with ultra-low-noise accelerometer, on-device FFT analysis, LoRa uplink, and battery-free solar operation.**

---

## What It Does

The Tremor Tile is a thin, mountable PCB that you bolt, glue, or magnet-attach to bridges, buildings, wind turbines, pipelines, industrial machinery, or any structure where you need to **continuously monitor vibration and detect anomalies** — without ever changing a battery.

- **Ultra-low-noise 3-axis vibration** — ADXL355 (7µg/√Hz) captures micro-tremors from 0.1 Hz to 1500 Hz
- **On-device FFT analysis** — RP2040 dual-core ARM computes 1024-point FFT in real-time, extracts spectral peaks, bandwidth, and energy in configurable frequency bands
- **Anomaly detection** — Learns the normal vibration signature during a calibration period, then alerts on deviations (cracks, loosening bolts, bearing wear, resonance shifts)
- **LoRa uplink** — Semtech SX1262 transmits anomaly alerts and periodic spectral summaries up to 15 km line-of-sight
- **Solar-powered** — Indoor amorphous solar cell (PowerFilm MPT3.6-75) keeps the 1000mAh LiFePO4 battery topped up indefinitely; 30+ days on battery alone
- **Magnetic mount** — Neodymium magnets embedded in the case snap onto steel structures in seconds
- **IP67 rated** — Conformal-coated PCB, potting compound on exposed components, sealed enclosure

### Use Cases

| Application | How Tremor Tile Helps |
|-------------|----------------------|
| Bridge monitoring | Detect traffic-induced vibration changes, cable tension loss, bearing degradation |
| Wind turbine | Monitor tower oscillation, blade imbalance, gearbox vibration signatures |
| Building seismic | Record micro-tremors, detect soil-structure interaction changes, earthquake early warning |
| Industrial machinery | Predictive maintenance — detect bearing wear, misalignment, imbalance before failure |
| Pipeline integrity | Detect transient pressure waves, third-party damage (digging, drilling) |
| Heritage structures | Non-intrusive monitoring of ancient buildings, towers, monuments |
| Elevator monitoring | Track car vibration, door mechanism wear, cable tension |
| Mining/tunneling | Detect micro-seismic events, ground displacement, rock-burst precursors |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        TREMOR TILE                                │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────┐ │
│  │ ADXL355       │  │ BME280        │  │ DS3231SN#           │ │
│  │ 3-Axis Accel │  │ T/H/Pressure  │  │ RTC + TCXO          │ │
│  │ SPI @ 4MHz   │  │ I²C 0x77      │  │ I²C 0x68            │ │
│  │ 7µg/√Hz noise│  │ (env context) │  │ (precise timestamp) │ │
│  └───────┬───────┘  └───────┬───────┘  └──────────┬──────────┘ │
│          │                  │                      │             │
│          │ SPI              └──────────┬───────────┘             │
│          │                            │ I²C bus (400kHz)        │
│  ┌───────▼────────────────────────────▼──────────────────────┐ │
│  │                    RP2040                                  │ │
│  │  ┌───────────┐  ┌───────────┐  ┌──────────────────────┐ │ │
│  │  │ ARM M0+   │  │ ARM M0+   │  │ 264KB SRAM            │ │ │
│  │  │ Core 0    │  │ Core 1    │  │ (FFT buffer 8KB)      │ │ │
│  │  │ Sensor    │  │ Analysis  │  │                       │ │ │
│  │  │ + Comms   │  │ + FFT     │  │                       │ │ │
│  │  └───────────┘  └───────────┘  └──────────────────────┘ │ │
│  │  ┌───────────────────────────────────────────────────────┐ │ │
│  │  │ 16MB QSPI Flash (W25Q128) — firmware + spectral log  │ │ │
│  │  └───────────────────────────────────────────────────────┘ │ │
│  └──────┬──────────────────────────┬──────────────────────────┘ │
│         │ SPI                      │ SPI                         │
│  ┌──────▼──────────┐  ┌────────────▼───────────┐              │
│  │ ADXL355          │  │ SX1262                 │              │
│  │ (see above)      │  │ LoRa 868/915MHz        │              │
│  └─────────────────┘  │ 22dBm, +127dBm sens     │              │
│                        └────────────┬───────────┘              │
│                                     │                           │
│                        ┌────────────▼───────────┐              │
│                        │ LoRa Antenna            │              │
│                        │ (PCB trace, 868MHz)     │              │
│                        └────────────────────────┘              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Power: SPV1040 MPPT solar → TP4056 charger                │   │
│  │ LiFePO4 1000mAh (3.2V) → RT9013-3.3V LDO → VDD          │   │
│  │ Solar: PowerFilm MPT3.6-75 (indoor amorphous, 75mA)       │   │
│  │ USB-C for charging + flash (field service)                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ SK6812MINI  │  │ Buzzer       │  │ Reed Switch         │    │
│  │ Status LED  │  │ Alert tone   │  │ Tamper detect       │    │
│  │ GPIO         │  │ GPIO (PWM)   │  │ GPIO (interrupt)   │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (RP2040)

| Pin | Function | Connected To |
|-----|----------|-------------|
| GPIO0 | SPI0 RX (MISO) | ADXL355 DOUT |
| GPIO1 | SPI0 CSn | ADXL355 CS (active low) |
| GPIO2 | SPI0 SCK | ADXL355 SCLK |
| GPIO3 | SPI0 TX (MOSI) | ADXL355 DIN (unused, pulled high) |
| GPIO4 | SPI1 RX (MISO) | SX1262 MISO |
| GPIO5 | SPI1 CSn | SX1262 NSS (active low) |
| GPIO6 | SPI1 SCK | SX1262 SCK |
| GPIO7 | SPI1 TX (MOSI) | SX1262 MOSI |
| GPIO8 | GPIO input | ADXL355 DRDY (data-ready interrupt) |
| GPIO9 | GPIO input | ADXL355 INT1 (overrun / watermark) |
| GPIO10 | GPIO input | SX1262 DIO1 (LoRa interrupt) |
| GPIO11 | GPIO output | SX1262 RESET (active low) |
| GPIO12 | GPIO output | SX1262 BUSY (read busy status) |
| GPIO13 | GPIO output | SX1262 TXCO_EN (TCXO enable) |
| GPIO14 | GPIO output | SX1262 RF_SWITCH (antenna path — TX/RX) |
| GPIO15 | I²C0 SDA | BME280 + DS3231 SDA (4.7k pull-up) |
| GPIO16 | I²C0 SCL | BME280 + DS3231 SCL (4.7k pull-up) |
| GPIO17 | GPIO output | SK6812MINI data (status LED) |
| GPIO18 | GPIO output | Buzzer PWM |
| GPIO19 | GPIO input | Reed switch (tamper interrupt) |
| GPIO20 | GPIO input | Boot button (hold at reset = USB boot) |
| GPIO21 | GPIO output | Power gate — sensor rail (ADXL355 VDD enable) |
| GPIO22 | ADC input | Battery voltage divider (1:2, 100k/100k) |
| GPIO23 | ADC input | Solar panel voltage (MPPT feedback) |
| GPIO24 | GPIO output | W25Q128 SPI CS (external flash — shares SPI0) |
| GPIO25 | GPIO output | LED on (active low, board LED) |
| GPIO26 | ADC input | ADXL355 analog temp out (diagnostic) |
| GPIO27 | GPIO output | ADXL355 RANGE select (0 = ±2g, 1 = ±4g, float = ±8g) |
| GPIO28 | GPIO input | DS3231 INT/SQW (RTC alarm interrupt) |
| GPIO29 | GPIO output | Flash CS (internal — do not reassign) |

---

## Power Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Solar Panel    │     │  SPV1040     │     │  TP4056      │
│  MPT3.6-75      │────►│  MPPT Boost │────►│  LiFePO4    │
│  3.6V 75mA      │     │  5V @ 150mA │     │  Charger     │
│  (indoor film)  │     └──────────────┘     │  3.2V 1A     │
└─────────────────┘                           └──────┬───────┘
                                                      │
                    ┌─────────────────────────────────┘
                    │ LiFePO4 1000mAh (3.2V nominal)
                    ▼
              ┌──────────────┐
              │ RT9013-3.3V  │────► VDD (3.3V rail)
              │ LDO 500mA    │        RP2040 + all peripherals
              └──────────────┘        ADXL355 @ 200µA
                                      SX1262 RX @ 10mA
                                      BME280 @ 0.1µA (standby)
                                      DS3231 @ 200µA (always on)
```

**Power budget:**

| Mode | Current | Duration | Avg Current | Battery Life |
|------|---------|----------|-------------|-------------|
| Deep sleep (RTC only) | 25µA | Continuous | 25µA | 4+ years |
| Low-power monitor | 200µA | 10s/sample | ~50µA avg | 2+ years |
| Active acquisition | 12mA | 5s every 10min | ~100µA avg | 370 days |
| FFT analysis burst | 25mA | 500ms | — | — |
| LoRa TX (alert) | 120mA | 200ms | — | — |
| Solar charge (typical indoor) | +50mA avg | Continuous | — | Net positive |

**Key insight:** With indoor solar at ~50mA average and total system draw averaging ~100µA in monitor mode, the battery stays at 80–100% indefinitely. Even in total darkness, the 1000mAh LiFePO4 lasts 370+ days.

---

## Vibration Analysis Pipeline

### Core 0: Sensor Acquisition + Communications

```
Main loop:
  1. Sleep until RTC alarm or DRDY interrupt
  2. Read ADXL355 FIFO (up to 32 samples × 3 axes × 4 bytes = 384 bytes)
  3. Push samples to inter-core FIFO (8KB ring buffer)
  4. Read BME280 (temperature, humidity, pressure — for environmental context)
  5. Read DS3231 (precise timestamp for each sample batch)
  6. If LoRa TX pending: transmit alert/summary packet
  7. If BLE connected: stream raw or FFT data
  8. Check tamper switch
  9. Update status LED
  10. Return to sleep
```

### Core 1: Signal Processing + Anomaly Detection

```
Main loop:
  1. Wait for samples in inter-core FIFO
  2. Accumulate 1024-sample window (at configured sample rate)
  3. Apply Hann window
  4. Compute 1024-point FFT (arm_cfft_f32 from CMSIS-DSP)
  5. Compute magnitude spectrum
  6. Extract spectral features:
     - Peak frequencies (top 5)
     - Band energy (0–10Hz, 10–50Hz, 50–200Hz, 200–500Hz, 500–1500Hz)
     - RMS vibration (overall, per-axis)
     - Crest factor
     - Kurtosis
  7. Compare features against learned baseline
  8. If anomaly detected: set LoRa TX flag + buzzer alert
  9. Store spectral summary to flash
  10. Repeat
```

### Anomaly Detection

The device learns a **baseline vibration signature** during a calibration period (default: 24 hours). It stores:

- Mean and standard deviation of each spectral feature
- Peak frequency locations and their acceptable drift range
- Band energy ratios (shape of the spectrum)

Anomaly is flagged when **any** of these conditions are met:

| Condition | Threshold |
|-----------|-----------|
| New spectral peak appears | >6σ above baseline noise floor |
| Existing peak shifts | >20% frequency change |
| Band energy exceeds baseline | >5σ above mean |
| RMS increases | >4σ above baseline RMS |
| Kurtosis increases | >3σ (indicates impulsive events) |

Alerts include: **timestamp, anomaly type, severity (1–10), affected frequency bands, and current spectral snapshot**.

---

## LoRa Protocol

The Tremor Tile uses LoRa to transmit to a gateway (e.g., RAK7258 or Dragino LPS8) on a configurable frequency (868 MHz EU / 915 MHz US).

### Packet Types

| Type | Size | Interval | Content |
|------|------|----------|---------|
| Heartbeat | 12 bytes | 1 hour | Device ID, battery %, uptime, status flags |
| Spectral Summary | 48 bytes | 15 min | Top 5 peaks (freq + amplitude), 5 band energies, RMS, kurtosis |
| Anomaly Alert | 32 bytes | Immediate | Anomaly type, severity, affected bands, timestamp |
| Raw Data Burst | 256 bytes | On demand | 64 samples × 3 axes × 10-bit (compressed) |

### LoRa Settings

| Parameter | Value |
|-----------|-------|
| Frequency | 868.0 MHz (EU) / 915.0 MHz (US) |
| Bandwidth | 125 kHz |
| Spreading Factor | SF7 (normal) / SF12 (alerts — max range) |
| Coding Rate | 4/5 |
| TX Power | +22 dBm |
| Preamble | 8 symbols |
| CRC | Enabled |

At SF7: ~5ms airtime for heartbeat, ~40ms for spectral summary
At SF12: ~2s airtime for anomaly alert (maximum range)

---

## Mechanical

- PCB: 85mm × 54mm × 1.6mm (credit card size), 4-layer FR4, ENIG finish
- Enclosure: 90mm × 58mm × 15mm, ABS/IP67 rated, UV-stabilized
- Solar cell on top face: PowerFilm MPT3.6-75 (75mm × 38mm, amorphous silicon, indoor-rated)
- Mounting: 4× M3 bolt holes + 2× embedded N35 neodymium magnets (for steel surfaces)
- Antenna: 868/915 MHz PCB trace antenna on bottom edge (meandered F-antenna)
- Buzzer: CMB-6542-100-SMT, 4kHz resonant
- Status LED: SK6812MINI (RGB, under diffuser lens)
- Tamper: Reed switch detects case opening
- Weight: ~35g with battery, ~45g in enclosure

---

## Firmware Architecture

```
firmware/
├── main/
│   ├── app_main.c            # Entry point, core launch, NVS init
│   ├── sensor_acq.c           # ADXL355 SPI driver, FIFO read, sample buffering
│   ├── sensor_acq.h
│   ├── env_sensor.c           # BME280 driver (temp/humidity/pressure)
│   ├── env_sensor.h
│   ├── rtc_manager.c          # DS3231 driver, alarm scheduling, timestamps
│   ├── rtc_manager.h
│   ├── fft_engine.c           # 1024-point FFT, spectral feature extraction
│   ├── fft_engine.h
│   ├── anomaly_detect.c       # Baseline learning, deviation detection
│   ├── anomaly_detect.h
│   ├── lora_radio.c           # SX1262 driver, TX/RX, LoRaWAN-like protocol
│   ├── lora_radio.h
│   ├── data_logger.c          # QSPI flash logging, circular buffer
│   ├── data_logger.h
│   ├── power_manager.c        # Sleep modes, solar charge tracking, battery monitor
│   ├── power_manager.h
│   ├── status_led.c           # SK6812MINI driver, patterns
│   ├── status_led.h
│   ├── buzzer.c               # PWM buzzer, alert patterns
│   ├── buzzer.h
│   ├── tamper_detect.c        # Reed switch interrupt handler
│   ├── tamper_detect.h
│   ├── intercore_fifo.c       # RP2040 dual-core FIFO, ring buffer
│   ├── intercore_fifo.h
│   └── config.h               # Sample rates, thresholds, LoRa settings
├── lib/
│   ├── cmsis_dsp/             # ARM CMSIS-DSP (FFT, statistics)
│   ├── adxl355_regs.h         # Register definitions
│   ├── sx1262_regs.h          # Register definitions
│   └── ds3231_regs.h          # Register definitions
├── CMakeLists.txt
└── sdkconfig.defaults
```

### Key Firmware Flow

```c
// Core 0: Sensor acquisition and communications
void core0_main(void) {
    power_manager_init();
    rtc_manager_init();
    sensor_acq_init();        // ADXL355: 400Hz ODR, ±2g range, FIFO watermark=32
    env_sensor_init();        // BME280: forced mode, 1Hz oversample
    lora_radio_init();        // SX1262: SF7, 125kHz BW, +22dBm
    status_led_init();
    buzzer_init();
    tamper_detect_init();
    intercore_fifo_init();

    // Set RTC alarm for periodic acquisition
    rtc_manager_set_periodic(ALARM_EVERY_10_SEC);

    while (true) {
        if (sensor_acq_fifo_ready()) {
            // Read ADXL355 FIFO (up to 32 samples)
            sample_batch_t batch = sensor_acq_read_fifo();

            // Push to Core 1 for processing
            intercore_fifo_push(&batch);

            // Timestamp with RTC
            batch.timestamp = rtc_manager_get_time();
        }

        // Handle LoRa TX queue
        if (lora_radio_tx_pending()) {
            lora_radio_send_next();
        }

        // Check for anomalies flagged by Core 1
        if (anomaly_detect_alert_pending()) {
            alert_t alert = anomaly_detect_get_alert();
            lora_radio_enqueue_alert(&alert);
            buzzer_play(ALERT_PATTERN);
            status_led_set(LED_RED_BLINK);
        }

        // Environmental context (every 60 seconds)
        if (rtc_manager_seconds_elapsed() % 60 == 0) {
            env_data_t env = env_sensor_read();
            data_logger_log_env(&env);
        }

        // Power management
        power_manager_sleep_until_next_event();
    }
}

// Core 1: Signal processing
void core1_main(void) {
    fft_engine_init();         // 1024-point FFT, Hann window
    anomaly_detect_init();     // Load baseline from flash or start learning

    sample_buffer_t buf;
    buf.count = 0;

    while (true) {
        // Wait for samples from Core 0
        sample_batch_t batch;
        if (intercore_fifo_pop(&batch)) {
            // Append to rolling buffer
            fft_engine_append(&buf, &batch);

            // When we have 1024 samples, run FFT
            if (buf.count >= FFT_SIZE) {
                spectral_features_t features;
                fft_engine_compute(&buf, &features);

                // Run anomaly detection
                anomaly_result_t result = anomaly_detect_evaluate(&features);

                if (result.is_anomaly) {
                    anomaly_detect_flag_alert(&result);
                }

                // Log spectral summary
                data_logger_log_spectrum(&features);

                // Reset buffer (overlapped windows — 50% overlap)
                fft_engine_overlap_reset(&buf);
            }
        }
    }
}
```

---

## BLE Service (Optional — USB-C Connected)

When USB-C is connected for field service, the device also exposes a BLE interface for live configuration and data streaming:

```
Service UUID: 0xFFC0 (TremorTile)
  ├── Char 0xFFC1: Vibration RMS X (read/notify) — float32 (g)
  ├── Char 0xFFC2: Vibration RMS Y (read/notify) — float32 (g)
  ├── Char 0xFFC3: Vibration RMS Z (read/notify) — float32 (g)
  ├── Char 0xFFC4: Peak Frequency (read/notify) — float32 (Hz)
  ├── Char 0xFFC5: Anomaly Status (read/notify) — uint8 (0=normal, 1=alert)
  ├── Char 0xFFC6: Battery Level (read) — uint8 (0–100%)
  ├── Char 0xFFC7: Temperature (read) — float32 (°C)
  ├── Char 0xFFC8: Sample Rate (read/write) — uint8 (0=100Hz, 1=200Hz, 2=400Hz)
  ├── Char 0xFFC9: FFT Size (read/write) — uint8 (0=256, 1=512, 2=1024)
  ├── Char 0xFFCA: Anomaly Threshold (read/write) — float32 (sigma multiplier)
  ├── Char 0xFFCB: Baseline Reset (write) — uint8 (1=reset, starts new learning)
  └── Char 0xFFCC: Device Info (read) — string
```

---

## Bill of Materials

| # | Part | Package | Qty | Unit $ | Note |
|---|------|---------|-----|--------|------|
| 1 | RP2040 | QFN-56 7x7 | 1 | $0.90 | Dual M0+, 264KB SRAM |
| 2 | W25Q128JVSIQ | SOIC-8 | 1 | $0.65 | 16MB QSPI flash |
| 3 | ADXL355 | LGA-14 6x6 | 1 | $9.50 | Ultra-low-noise 3-axis accel |
| 4 | SX1262IMLTRT | QFN-24 4x4 | 1 | $3.20 | LoRa transceiver |
| 5 | BME280 | LGA-8 2.5x2.5 | 1 | $2.80 | T/H/Pressure |
| 6 | DS3231SN# | SOIC-16 | 1 | $2.10 | RTC + TCXO (±2ppm) |
| 7 | SPV1040TR | TSSOP-8 | 1 | $1.80 | Solar MPPT boost charger |
| 8 | TP4056 | SOP-8 | 1 | $0.30 | LiFePO4 charger |
| 9 | RT9013-33GB | SOT-223 | 1 | $0.25 | 3.3V LDO, 500mA |
| 10 | CR1220 holder | SMD | 1 | $0.20 | DS3231 backup battery |
| 11 | PowerFilm MPT3.6-75 | Custom | 1 | $4.50 | Indoor solar, 3.6V 75mA |
| 12 | LiFePO4 1000mAh | 602030 pouch | 1 | $5.50 | 3.2V nominal |
| 13 | SK6812MINI | 3535 | 1 | $0.10 | RGB status LED |
| 14 | CMB-6542-100-SMT | SMD buzzer | 1 | $0.40 | 4kHz piezo |
| 15 | Reed switch | SMD | 1 | $0.15 | Tamper detect |
| 16 | USB-C receptacle | 16-pin SMD | 1 | $0.35 | Field service + flash |
| 17 | Antenna: PCB trace | On PCB | 1 | $0.00 | Meandered F-antenna 868MHz |
| 18 | N35 neodymium magnets | 6x3mm disc | 2 | $0.20 | Steel surface mount |
| 19 | Passives (R/C/L/inductor) | 0402 | ~45 | $0.75 | Decoupling, dividers, filters |
| 20 | PCB 4-layer 85x54mm | Rect | 1 | $2.00 | JLCPCB |

**Total estimated BOM: ~$36.45** (qty 1)

---

## Directory Structure

```
tremor-tile/
├── README.md                  # This file
├── schematic/
│   ├── tremor_tile.kicad_sch
│   ├── tremor_tile.kicad_pcb
│   └── tremor_tile.kicad_pro
├── firmware/
│   ├── main/
│   │   ├── app_main.c
│   │   ├── sensor_acq.c
│   │   ├── sensor_acq.h
│   │   ├── env_sensor.c
│   │   ├── env_sensor.h
│   │   ├── rtc_manager.c
│   │   ├── rtc_manager.h
│   │   ├── fft_engine.c
│   │   ├── fft_engine.h
│   │   ├── anomaly_detect.c
│   │   ├── anomaly_detect.h
│   │   ├── lora_radio.c
│   │   ├── lora_radio.h
│   │   ├── data_logger.c
│   │   ├── data_logger.h
│   │   ├── power_manager.c
│   │   ├── power_manager.h
│   │   ├── status_led.c
│   │   ├── status_led.h
│   │   ├── buzzer.c
│   │   ├── buzzer.h
│   │   ├── tamper_detect.c
│   │   ├── tamper_detect.h
│   │   ├── intercore_fifo.c
│   │   ├── intercore_fifo.h
│   │   └── config.h
│   ├── lib/
│   │   ├── cmsis_dsp/
│   │   │   └── arm_math.h
│   │   ├── adxl355_regs.h
│   │   ├── sx1262_regs.h
│   │   └── ds3231_regs.h
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── hardware/
│   └── BOM.csv
├── scripts/
│   ├── read_tremor.py          # LoRa gateway data reader
│   ├── calibrate_baseline.py   # Baseline learning tool
│   ├── spectral_viewer.py       # Real-time FFT visualization
│   └── deploy_config.py         # Configure device over BLE/USB
└── docs/
    ├── assembly_guide.md
    ├── api_reference.md
    ├── mounting_guide.md
    └── anomaly_detection.md
```

---

## Getting Started

### Flash Firmware

```bash
# Install Pico SDK
git clone https://github.com/jayis1/SoC-Device-Inventions.git
cd SoC-Device-Inventions/tremor-tile/firmware
mkdir build && cd build
cmake ..
make -j4

# Flash via USB (hold BOOT button, press RESET, release both)
# The RP2040 appears as a USB mass storage device
cp tremor_tile.uf2 /media/$USER/RPI-RP2/
```

### Mount the Device

1. Clean the mounting surface (steel, concrete, wood)
2. For steel: snap the magnetic mount on — done
3. For concrete/wood: use the M3 bolt holes or industrial double-sided tape
4. Ensure the solar cell faces ambient light (even indoor lighting works)
5. Device auto-starts and begins learning the baseline

### Monitor from a Gateway

```bash
# Using a LoRa gateway (RAK7258, Dragino LPS8, etc.)
# Data appears as MQTT messages on the gateway
pip install paho-mqtt
python3 scripts/read_tremor.py --gateway 192.168.1.100 --topic "tremor/#"
```

### Live Spectral Viewer (via USB-C)

```bash
# Connect USB-C for field service mode
pip install pyserial numpy matplotlib
python3 scripts/spectral_viewer.py --port /dev/ttyACM0
```

---

## Calibration and Learning

### Baseline Learning (Automatic)

On first boot, the Tremor Tile enters a **24-hour baseline learning period**:

1. Collects vibration data at 400 Hz continuously
2. Computes 1024-point FFTs every ~2.5 seconds (50% overlap)
3. Builds a statistical model of each spectral feature:
   - Mean, standard deviation, min, max for each feature
   - Peak frequency locations and their typical variation
   - Band energy ratios and their normal ranges
4. After 24 hours, transitions to **monitoring mode**

### Manual Baseline Reset

Send a LoRa downlink command or use the BLE characteristic `0xFFCB` (write 1) to reset the baseline and start learning again. Useful after:
- Moving the device to a new location
- Major structural changes
- Seasonal recalibration

### Sensitivity Adjustment

The anomaly threshold (σ multiplier) defaults to 5σ but can be adjusted:

| Threshold | Sensitivity | False Alarm Rate |
|-----------|-------------|-----------------|
| 3σ | High | ~1 per day |
| 5σ | Medium (default) | ~1 per month |
| 7σ | Low | ~1 per year |
| 10σ | Very Low | ~1 per decade |

---

## Safety and Deployment Notes

- **The Tremor Tile is NOT a safety-critical device** — it provides supplementary monitoring and early warning, but should not be the sole safety system for any structure
- **LoRa frequency regulations vary by country** — configure the device for your region's ISM band (868 MHz EU, 915 MHz US, 923 MHz AS/NZ)
- **LiFePO4 chemistry is inherently safe** — no thermal runaway risk, stable at -20°C to +60°C
- **The ADXL355 is sensitive to shock** — do not drop the device; handle with care during installation
- **Solar panel performance depends on light** — in very dim locations (<100 lux), expect slower charging and reduced battery margin

---

## Comparison with Existing Solutions

| Feature | Tremor Tile | MEMS Accelerometer Logger | Commercial SHM System | Seismograph |
|---------|-------------|--------------------------|----------------------|-------------|
| Price | ~$36 | $50–150 | $500–5000 | $2000+ |
| Noise floor | 7 µg/√Hz | 50–100 µg/√Hz | 1–10 µg/√Hz | 0.1–1 µg/√Hz |
| On-device FFT | ✅ Real-time | ❌ Store only | ✅ (some) | ❌ |
| Wireless uplink | ✅ LoRa 15km | ❌ or Wi-Fi | ✅ Cellular | ❌ |
| Solar powered | ✅ Indefinite | ❌ Battery only | ✅ (some) | ❌ |
| Anomaly detection | ✅ On-device | ❌ Post-process | ✅ Cloud | ❌ |
| Size | Credit card | Data logger | 19" rack | Lab equipment |
| Install time | 30 seconds | 30 min | Hours | Days |

---

*Invented 2026-06-15 by jayis1*