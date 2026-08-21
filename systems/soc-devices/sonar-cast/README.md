# Sonar Cast — Pocket CHIRP Fish Finder & Bathymetry Logger

> A pocket-sized, battery-powered, CHIRP sonar fish finder and depth profiler that
> transmits a 150–250 kHz linear-frequency-modulated acoustic sweep, performs
> on-device **pulse compression** (matched filtering) for 7.5 cm range resolution,
> detects fish targets and bottom returns, classifies bottom type
> (hard / soft / weedy) from echo-envelope statistics, geo-tags every depth
> sounding with a NEO-M9N GPS, logs a bathymetry CSV to microSD, and streams a
> live water-column echogram to a phone over BLE / Wi-Fi — bringing
> $200–$1,500 castable fish finders (Deeper Smart Sonar, Garmin Striker Cast,
> Vexilar SP-200) down to **~$72** and a hockey-puck form factor, with an open
> pulse-compression DSP pipeline that commercial units keep proprietary.

---

## 1. What it is

**Sonar Cast** is a floating, castable CHIRP sonar probe. You cast it into the
water (or mount it on a float / transom mount), and it:

1. **Transmits** a 200 kHz-center, 150–250 kHz linear-FM (chirp) acoustic pulse
   of ~0.5 ms duration via a piezo-ceramic transducer, driven by an HV H-bridge
   at ±100 V.
2. **Receives** the backscattered echo with the same transducer (T/R switch),
   amplifies it with a time-gain-compensated VGA (AD8331, 0–48 dB ramping with
   range to compensate for 1/R² spreading + absorption), and digitizes at
   1 Msps / 12-bit via an ADS7945 ADC.
3. **Pulse-compresses** the raw echo with a pre-computed conjugate-chirp matched
   filter (FIR) in the time domain — collapsing the 0.5 ms sweep into a
   ~4 µs compressed pulse, giving **7.5 cm range resolution** instead of the
   75 cm a single-frequency 200 kHz pulse would yield.
4. **Detects** the bottom return (first strong peak past the blind zone),
   individual fish targets (thresholded peaks above the noise floor with
   echo-envelope shape analysis), estimates fish size from target strength and
   beam-pattern compensation, and classifies the **bottom type** (hard/soft/weedy)
   from the bottom-echo envelope statistics (rise time, decay tail, second
   bounce).
5. **Geo-tags** each ping with a NEO-M9N GPS fix (latitude, longitude, HDOP),
   **tilt-compensates** the depth reading with an ICM-42688-P IMU (transducer
   face must be ~vertical for the beam to point down), and **pressure-cross-
   checks** depth with an MS5837-30BA submersible pressure sensor.
6. **Logs** a bathymetry CSV (`lat,lon,depth_m,bottom_type,fish_count,fish_sz,
   temp,time`) and a binary raw-echo ring buffer to microSD, and **streams**
   a live 128-bin water-column echogram + depth/fish/bottom results to a phone
   over BLE (or Wi-Fi web dashboard).

All DSP runs on a **STM32G474RET6** (170 MHz CORDIC + DSP FPU + 5-timer HRTIM
for the HV drive), with an **ESP32-C3** handling BLE/Wi-Fi/GPS-NMEA relay.

| | |
|---|---|
| **SoC (DSP core)** | STM32G474RET6 (Cortex-M4F @ 170 MHz, CORDIC, HRTIM) |
| **SoC (radio/GPS)** | ESP32-C3-WROOM-02 (RISC-V, BLE 5.0 + Wi-Fi) |
| **Transducer** | 200 kHz piezo-ceramic, 8° beam, ±100 V drive |
| **CHIRP** | 150–250 kHz LFM, 0.5 ms, Hamming-weighted |
| **Range resolution** | 7.5 cm (pulse-compressed) vs 75 cm (CW) |
| **Max depth** | ~80 m (fresh water, TGC-limited) |
| **Min depth** | 0.3 m (blanking / T/R recovery) |
| **Ping rate** | 5–20 Hz (depth-adaptive: fast in shallow, slow in deep) |
| **ADC** | ADS7945, 1 Msps, 12-bit, SPI |
| **TGC** | AD8331 VGA, 0–48 dB, HRTIM-DAC ramp |
| **GPS** | u-blox NEO-M9N, 1 Hz, ≤1.5 m CEP |
| **IMU** | ICM-42688-P (6-axis, tilt compensation) |
| **Pressure** | MS5837-30BA, 0–30 bar, ±2 mbar |
| **Temp** | DS18B20 water temp (speed-of-sound correction) |
| **Display** | SSD1306 OLED 0.96″ 128×64 (local status) |
| **Logging** | microSD (FAT32, bathymetry CSV + raw echo bin) |
| **Radio** | BLE 5.0 (echogram stream) + Wi-Fi (web dashboard) |
| **Power** | 18650 Li-ion + TP4056 USB-C charging, ~8 h runtime |
| **Size** | Ø 62 mm × 38 mm hockey puck (IP68), 95 g |
| **BOM cost** | **~$72** |

---

## 2. Block Diagram

```
         ┌──────────────────────── STM32G474RET6 ────────────────────────┐
         │  HRTIM CHA/CHB ──► HV H-bridge (±100V) ──► T/R switch ──┐    │
         │  DAC1 ◄── TGC ramp ◄── HRTIM trigger                    │    │
         │  SPI1 ◄── ADS7945 (1Msps/12b) ◄── AD8331 VGA ◄──────────┘    │
         │        ▲                                                     │
         │  Cortex-M4F: CHIRP gen ► matched-filter FIR ► detector       │
         │  CORDIC: envelope, beam-pattern, range, speed-of-sound       │
         │  I2C1: ICM-42688-P (IMU), MS5837 (pressure), SSD1306 (OLED)  │
         │  SPI2: microSD (FAT32)                                       │
         │  USART1 ◄── DS18B20 (1-Wire via GPIO)                        │
         │  USART2 ──► ESP32-C3 (UART @ 1 Mbaud, binary echogram)       │
         │  GPIO: STATUS_LED, WATER_DETECT, BUTTON                      │
         └────────────────────────────┬──────────────────────────────────┘
                                      │ UART 1 Mbaud
         ┌────────────────────────────▼───────────────┐
         │             ESP32-C3-WROOM-02               │
         │  UART0 ◄── STM32 (echogram + results)       │
         │  UART1 ◄── NEO-M9N GPS (NMEA @ 38400)       │
         │  I2C: (free for expansion)                  │
         │  BLE 5.0 ──► phone echogram + depth stream  │
         │  Wi-Fi  ──► web dashboard (echogram viewer) │
         └─────────────────────────────────────────────┘
```

---

## 3. How it works

### 3.1 CHIRP transmit

The STM32G474's **HRTIM** (high-resolution timer, 184 ps) drives a full H-bridge
of 4× IRFH7440 MOSFETs, generating a bipolar ±100 V square-wave across the
piezo transducer. The drive frequency is swept linearly from **150 kHz to
250 kHz over 0.5 ms** (the chirp), synthesized by a 256-entry phase-accumulator
DDS table loaded into HRTIM compare registers via DMA. A **Hamming window** is
applied to the amplitude envelope (via the HRTIM deadtime + burst-mode gating)
to reduce range sidelobes to ~-43 dB.

### 3.2 Receive & TGC

After the chirp, the HRTIM switches the **T/R switch** (two antiparallel diode
clamps + a series resistor) to receive mode and starts a **TGC ramp**: the
STM32 DAC1 outputs a 0–1.6 V exponential ramp that controls the AD8331 VGA gain
from 0 dB (near range, strong echoes) to 48 dB (far range, weak echoes),
compensating 1/R² spreading + ~0.005 dB/m absorption at 200 kHz in fresh water.

The AD8331 output is AC-coupled, level-shifted to 0–3.3 V, and digitized by the
**ADS7945** (1 Msps, 12-bit, SPI with DMA) for ~16 ms after each ping (covering
~12 m of water at sound speed 1500 m/s — extended to 80 m by lowering the sample
rate / windowing the TGC).

### 3.3 Pulse compression (matched filter)

The received echo is convolved with the **conjugate-time-reversed chirp replica**
(pre-computed at boot, 500 samples at 1 Msps, Hamming-weighted) using the
Cortex-M4F's SIMD `__SMLALD` instructions in a 500-tap FIR. This compresses the
0.5 ms chirp echo into a ~4 µs peak (2 samples), yielding **range resolution =
c·Δt/2 = 1500×4µ/2 ≈ 3 mm theoretical, ~7.5 cm practical** with the Hamming
sidelobe floor.

### 3.4 Detection

The compressed envelope (computed via CORDIC magnitude of the analytic signal
— FIR + 90° Hilbert branch) is thresholded:

- **Bottom**: the strongest peak after the blanking zone (0.3 m). Depth =
  range×cos(tilt), tilt from IMU. A second-bounce detection (echo at 2×depth)
  confirms and refines the bottom pick.
- **Fish**: thresholded peaks above a CFAR (cell-averaged constant false-alarm
  rate) noise floor, with echo-envelope width < 2× the compressed pulse width
  (rejecting diffuse scatterers). Target strength → length estimate via the
  Love (1971) TS–length equation: `TS = 20·log₁₀(L) + 20·log₁₀(f) - 65.4`.
- **Bottom type**: the bottom-echo envelope's rise time (10→90%), decay tail
  (e-folding), and second-bounce ratio classify **hard** (fast rise, long tail,
  strong 2nd bounce), **soft** (slow rise, short tail), **weedy** (multi-peak,
  diffuse, weak 2nd bounce) via a 3-bin nearest-centroid classifier.

### 3.5 Speed-of-sound correction

Water temperature from the DS18B20 (mounted on the transducer face, wetted)
feeds the Mackenzie (1981) equation:

```
c = 1448.96 + 4.591·T − 0.05304·T² + 0.0002964·T³
```

(fresh-water simplification; salinity term omitted for the castable puck, can
be user-configured for marine use).

### 3.6 Geo-tagging & bathymetry

Each ping gets a GPS fix (NMEA `$GPGGA` parsed on the ESP32-C3) and is logged
to microSD as a row in `bathy_YYYYMMDD.csv`:

```csv
unix_ts,lat,lon,hdop,depth_m,bottom_type,fish_count,fish_avg_cm,temp_c
```

The Wi-Fi web dashboard (ESP32-C3) serves an interactive leaflet.js map with
depth-colored track points, and a scrolling water-column echogram (WebSocket
or Server-Sent Events).

---

## 4. Pin Assignments

### STM32G474RET6 (LQFP64)

| Pin   | Function         | Connected to                  |
|-------|------------------|-------------------------------|
| PA0   | DAC1_OUT1        | AD8331 GAIN (TGC ramp)        |
| PA1   | ADC1_IN1         | HV monitor (÷11) — safety     |
| PA2   | USART2_TX        | ESP32-C3 UART RX              |
| PA3   | USART2_RX        | ESP32-C3 UART TX              |
| PA4   | HRTIM_CHA1       | HV H-bridge high-side A       |
| PA5   | HRTM_CHA2        | HV H-bridge low-side A        |
| PA6   | HRTIM_CHB1       | HV H-bridge high-side B       |
| PA7   | HRTIM_CHB2       | HV H-bridge low-side B        |
| PA8   | GPIO (T/R SW)    | T/R switch control            |
| PA9   | SPI1_SCK         | ADS7945 SCK                   |
| PA10  | SPI1_MISO        | ADS7945 DOUT                  |
| PA11  | SPI1_NSS         | ADS7945 CS                    |
| PA12  | GPIO (WATER)     | Water-detect probes (float)   |
| PA13  | GPIO (BUTTON)    | Mode button                   |
| PA14  | GPIO (LED)       | Status LED (RGB, WS2812)      |
| PA15  | TIM2_CH1         | WS2812 data (µs-precise PWM)  |
| PB0   | I2C1_SCL         | IMU / OLED / MS5837 SCL       |
| PB1   | I2C1_SDA         | IMU / OLED / MS5837 SDA       |
| PB2   | SPI2_SCK         | microSD SCK                   |
| PB3   | SPI2_MISO        | microSD MISO                  |
| PB4   | SPI2_MOSI        | microSD MOSI                  |
| PB5   | SPI2_NSS         | microSD CS                    |
| PB6   | GPIO (1WIRE)     | DS18B20 DQ                    |
| PB7   | GPIO (CHG)       | TP4056 CHG status              |
| PC13  | GPIO (BOOT)      | Boot button                   |
| PC14  | GPIO (SD-DET)    | microSD card detect           |
| VBAT  | 3V3              | RTC battery (CR2032)          |
| VDD   | 3V3              | Core supply                   |
| VDDA  | 3V3 (ferrite)    | Analog supply (clean)         |

### ESP32-C3-WROOM-02

| Pin   | Function    | Connected to                |
|-------|-------------|-----------------------------|
| GPIO2 | UART0_RX    | STM32 USART2_TX (echogram)  |
| GPIO3 | UART0_TX    | STM32 USART2_RX (commands)  |
| GPIO4 | UART1_RX    | NEO-M9N GPS TX (NMEA)       |
| GPIO5 | UART1_TX    | NEO-M9N GPS RX (config)     |
| GPIO6 | GPIO (PPS)  | NEO-M9N PPS (time-tag)      |
| GPIO7 | GPIO (LED)  | Radio status LED            |
| GPIO8 | GPIO (WAKE) | STM32 wake (deep-sleep ctl) |
| GPIO9 | GPIO (BOOT) | Boot strap                  |
| GPIO10| I2C_SCL     | (expansion)                 |
| GPIO11| I2C_SDA     | (expansion)                 |

---

## 5. Power Architecture

```
  18650 (3.7V 3500mAh)
      │
      ├──► TP4056 (USB-C charging, 1A) ──► DW02 protection
      │
      └──► AP2112-3.3 LDO ──► 3V3 (STM32 + ESP32-C3 + sensors)
              │
              ├──► ferrite bead ──► 3V3A (clean analog: AD8331, ADS7945, DAC)
              └──► 3V3D (digital: STM32, ESP32, GPS, SD, OLED)

  HV rail: STM32 drives a MC34063 boost → 12V → H-bridge → ±100V across piezo
           (only energized during ping burst, ~0.5ms × 10Hz = 0.5% duty)
```

- **Average current**: ~120 mA (GPS + DSP + TGC), ~8 h on a 3500 mAh cell.
- **Ping burst current**: ~400 mA for 0.5 ms (HV rail), averaged out by 220 µF.
- **Power modes**: `ACTIVE` (pinging), `DRIFT` (GPS-only, 1 ping/s, no Wi-Fi,
  ~40 mA), `SLEEP` (everything off except ESP32-C3 deep-sleep + GPS warm-start
  wake, ~2 mA).

---

## 6. Firmware

Located in [`firmware/`](firmware/). Build with **STM32CubeIDE** or
`arm-none-eabi-gcc` + CMake (see `firmware/CMakeLists.txt`).

### Source files

| File | Purpose |
|------|---------|
| `main.c` | Boot, task scheduler, state machine |
| `chirp.c` / `chirp.h` | CHIRP waveform generation + matched-filter coefficient table |
| `hrtim_drv.c` | HRTIM + HV H-bridge drive, T/R switch timing |
| `adc_dsp.c` | ADS7945 SPI-DMA capture, pulse-compression FIR, envelope (CORDIC) |
| `detector.c` | CFAR, bottom detection, fish target detection, size estimate |
| `bottom_class.c` | Bottom-type classifier (hard/soft/weedy) |
| `imuw.c` | ICM-42688-P tilt compensation for depth |
| `depth.c` | MS5837 pressure depth, DS18B20 temp, speed-of-sound |
| `sd_log.c` | FatFs bathymetry CSV + binary echo logging |
| `oled.c` | SSD1306 local status display |
| `uart_link.c` | Binary framing to/from ESP32-C3 |
| `model.c` | Echo-envelope feature extraction (shared) |

### ESP32-C3 firmware

A small ESP-IDF app (`firmware/esp32c3/`) handles:
- UART receive from STM32 → ring buffer
- BLE GATT server (echogram + results characteristics)
- Wi-Fi AP + HTTP server (leaflet.js map + echogram WebSocket)
- NEO-M9N NMEA parsing → GPS fix struct, sent to STM32

---

## 7. Scripts

Located in [`scripts/`](scripts/):

| Script | Purpose |
|--------|---------|
| `live_echogram.py` | BLE-connected live echogram viewer (matplotlib waterfall) |
| `bathy_plot.py` | Plot a logged bathymetry CSV as a depth-colored track map |
| `flash_stm32.sh` | OpenOCD flash script (ST-Link) |
| `sim_chirp.py` | Simulate CHIRP pulse compression + verify range resolution |

---

## 8. Mechanical & Waterproofing

- **Housing**: 3D-printed PETG two-piece puck, Ø62×38 mm, IP68.
- **Transducer mount**: piezo cemented to the bottom face with epoxy, facing
  down; O-ring seal (AS568-018, 26 mm ID).
- **Buoyancy**: closed-cell foam ring so the puck floats with the transducer
  submerged and ~30 mm above water (keeps the beam vertical).
- **GPS antenna**: exposed on the top dome (above waterline).
- **Charging**: pogo-pin USB-C charging port with a magnetic cap.
- **Cast loop**: 3 mm hole for a fishing snap-swivel to cast from shore.

---

## 9. Comparison to commercial castable sonars

| Feature | Deeper Smart Sonar Pro+ | Garmin Striker Cast | Vexilar SP-200 | **Sonar Cast** |
|---------|------------------------|---------------------|----------------|----------------|
| CHIRP | yes (narrow) | yes | no | **yes (150–250 kHz)** |
| Pulse compression | proprietary | proprietary | n/a | **open matched-filter FIR** |
| Range resolution | ~2.5–5 cm | ~2.5 cm | ~75 cm | **7.5 cm** |
| Bottom classification | no | no | no | **hard/soft/weedy** |
| Fish size estimate | count only | count only | no | **yes (TS→length)** |
| GPS geo-tag | yes | yes | no | **yes (NEO-M9N)** |
| Bathymetry CSV export | subscription | no | no | **open SD CSV** |
| IMU tilt comp | no | no | no | **yes** |
| Price | ~$340 | ~$150 | ~$200 | **~$72** |
| Open source | no | no | no | **MIT** |

---

## 10. Applications

- **Recreational fishing**: cast from shore, kayak, or dock; see depth,
  fish, and bottom type on your phone.
- **Citizen-science bathymetry**: paddle a lake/kayak, log depth tracks,
  contribute to OpenStreetMap depth layers or inland bathymetry databases.
- **Aquaculture**: quick depth + bottom-type survey of ponds.
- **Search & rescue**: rapid underwater bottom profiling for drowned-object
  recovery planning.
- **Education**: a fully open CHIRP sonar DSP pipeline — great for teaching
  pulse compression, matched filtering, CFAR, and underwater acoustics.

---

## 11. License

MIT — build it, fish with it, improve it.