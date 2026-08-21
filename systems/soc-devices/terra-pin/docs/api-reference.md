# Terra Pin — API Reference

## Firmware Architecture

The Terra Pin firmware runs on the ESP32-S3-WROOM-1 using ESP-IDF v5.2 with FreeRTOS. Eleven tasks handle sensor acquisition, data fusion, display, logging, and wireless communication.

### Task Summary

| Task | Priority | Stack (bytes) | Rate | Purpose |
|------|----------|---------------|------|---------|
| `flux_task` | 5 | 4096 | 5 s × 12 (60 s) | SCD41 chamber CO₂ rise rate |
| `ambient_task` | 3 | 3072 | 10 s | SCD41 ambient CO₂ baseline |
| `orp_task` | 4 | 3072 | 5 s | EZO-ORP redox potential |
| `ec_task` | 4 | 3072 | 5 s | EZO-EC conductivity |
| `moisture_task` | 3 | 2048 | 1 s | Capacitive VWC via PCNT |
| `temp_task` | 3 | 2048 | 2 s | DS18B20 soil temperature |
| `shi_task` | 6 | 4096 | 5 s | Soil Health Index fusion |
| `display_task` | 2 | 3072 | 10 Hz | SH1106 OLED UI |
| `button_task` | 3 | 2048 | 100 Hz | Button + encoder debounce |
| SD logging | — | event-driven | per-reading | FAT32 CSV |
| BLE notify | — | event-driven | per-reading | GATT notifications |

## Sensor Driver APIs

### SCD41 (scd41.h / scd41.c)

```c
// Initialize I2C bus and both SCD41 sensors via TCA9548A mux
esp_err_t scd41_init(void);

// Select TCA9548A channel (0=chamber, 1=ambient, 2=OLED passthrough)
esp_err_t scd41_select_channel(uint8_t ch);

// Single-shot read from chamber sensor
// Returns CO2 ppm, temperature °C, relative humidity %
esp_err_t scd41_measure_chamber(uint16_t *co2, float *temp, float *rh);

// Single-shot read from ambient sensor
esp_err_t scd41_measure_ambient(uint16_t *co2, float *temp, float *rh);

// Start/stop periodic measurement (5 s interval) on chamber sensor
esp_err_t scd41_start_periodic_chamber(void);
esp_err_t scd41_stop_periodic_chamber(void);
```

### EZO-ORP (ezo_orp.h / ezo_orp.c)

```c
// Initialize UART for Atlas Scientific EZO-ORP
esp_err_t ezo_orp_init(void);

// Read redox potential in mV (int16, range ±2000)
esp_err_t ezo_orp_read(int16_t *orp_mv);
```

### EZO-EC (ezo_ec.h / ezo_ec.c)

```c
// Initialize UART for Atlas Scientific EZO-EC
esp_err_t ezo_ec_init(void);

// Read conductivity in µS/cm (uint16)
// Temperature compensation applied via "T,<temp>" command
esp_err_t ezo_ec_read(uint16_t *ec_us, float *temp_comp);
```

### DS18B20 (ds18b20.h / ds18b20.c)

```c
// Initialize 1-Wire bus and detect DS18B20
esp_err_t ds18b20_init(void);

// Read temperature in °C (12-bit resolution, 750 ms conversion)
esp_err_t ds18b20_read(float *temp_c);
```

### Moisture (moisture.h / moisture.c)

```c
// Initialize PCNT for capacitive probe frequency measurement
esp_err_t moisture_init(void);

// Read VWC % (0-100, linearly interpolated from calibration endpoints)
esp_err_t moisture_read(float *vwc);

// Save calibration endpoints to NVS
esp_err_t moisture_calibrate(float freq_dry, float freq_wet);
```

## Soil Health Index (shi.c)

```c
// Compute SHI from a terra_reading_t struct
// Modifies: shi_resp, shi_redox, shi_ec, shi_moist, shi_temp, shi
void shi_compute(terra_reading_t *r);
```

### SHI Formula

```
SHI = 100 × (0.30·S_resp + 0.25·S_redox + 0.20·S_ec + 0.15·S_moist + 0.10·S_temp)
```

Each sub-score is 0.0–1.0:

| Sub-score | Parameter | Model |
|-----------|-----------|-------|
| S_resp | CO₂ flux (mg C m⁻² h⁻¹) | Bell curve, peak at 30, range 15–60 |
| S_redox | ORP (mV) | Linear ramp 100→300, plateau 300–550, penalty >550 |
| S_ec | EC (µS/cm) | Bell curve, peak at 600, range 100–1500 |
| S_moist | VWC (%) | Bell curve, peak at 35, range 25–45 |
| S_temp | Temp (°C) | Bell curve, peak at 20, range 15–25 |

### Q₁₀ Temperature Correction

Respiration is temperature-corrected to 20 °C reference:

```
flux_corrected = flux_measured × Q10^((20 - T_soil) / 10)
```

With Q₁₀ = 2.0 (standard microbial respiration Q₁₀).

## BLE GATT Protocol

### Service

| UUID | Name |
|------|------|
| 0x0001 (128-bit custom) | Terra Pin Service |

### Characteristics

| UUID | Name | Type | Format | Description |
|------|------|------|--------|-------------|
| 0x0002 | SHI | read/notify | uint8 | 0–100 |
| 0x0003 | Flux | read | float32 LE | mg C m⁻² h⁻¹ |
| 0x0004 | ORP | read | int16 LE | mV |
| 0x0005 | EC | read | uint16 LE | µS/cm |
| 0x0006 | Moisture | read | float32 LE | VWC % |
| 0x0007 | Temperature | read | float32 LE | °C |
| 0x0008 | Raw CO₂ | read | 2× uint16 LE | chamber, ambient ppm |
| 0x0009 | Mode | read/write | uint8 | 0=point, 1=continuous, 2=calibrate |

### Notification

When a new reading completes, the SHI characteristic sends a notification with the updated 0–100 value. Subscribe to 0x0002 to receive push updates.

## SD Card Log Format

```csv
# Terra Pin soil health log
session,timestamp,co2_chamber,co2_ambient,flux_ppm_min,flux_mgC,
orp_mv,ec_us,moisture_vwc,temp_c,shi,
shi_resp,shi_redox,shi_ec,shi_moist,shi_temp
```

Files are named `TERRA_NNNN.CSV` (incrementing session number).

## Python Helper Script

### terra_pin_plot.py

```bash
# Basic SHI time-series plot
python3 scripts/terra_pin_plot.py TERRA_0001.csv --output shi.png

# Full report with trends and correlation
python3 scripts/terra_pin_plot.py TERRA_0001.csv --trends --correlation

# Custom output paths
python3 scripts/terra_pin_plot.py TERRA_0001.csv \
    --output shi.png \
    --trends --trend-output trends.png \
    --correlation --corr-output corr.png
```

Outputs:
- `soil_shi.png` — SHI time-series with health zones
- `soil_trends.png` — 6-panel parameter trend plot
- `soil_corr.png` — Pearson correlation heatmap
- Console summary with mean/min/max/std for all parameters

## Operating Modes

| Mode | Value | Behavior |
|------|-------|----------|
| Point | 0 | Single measurement on MEASURE button press; sensors sleep between readings |
| Continuous | 1 | All sensors active; SHI updates every 60 s; continuous SD logging |
| Calibrate | 2 | Moisture dry/wet calibration; ORP/EC calibration prompts |

## Power Management

- **Light sleep** between readings in point mode (ESP32-S3 deep sleep at 5 mA)
- SCD41 sensors enter idle mode between measurements (5 mA each)
- OLED can be dimmed after 30 s of inactivity
- Estimated battery life: 32 h continuous, >5 days point mode

## Calibration Commands

### ORP (via UART to EZO-ORP)
```
Cal,228\r        → calibrate to ZoBell's solution (228 mV at 25°C)
Cal,?\r          → read calibration state
Cal,clear\r      → clear calibration
```

### EC (via UART to EZO-EC)
```
Cal,dry\r        → calibrate dry probe (0 µS/cm)
Cal,low,1413\r   → calibrate with 1413 µS/cm KCl standard
Cal,?\r          → read calibration state
T,19.5\r         → set temperature compensation
```

### Moisture (via firmware calibration mode)
1. Place probe in oven-dry soil → press MEASURE → stores `freq_dry`
2. Place probe in saturated soil → press MEASURE → stores `freq_wet`
3. Values saved to NVS (`moist_dry`, `moist_wet` keys)

### SCD41 (via I2C)
```
perform_forced_recalibration(420)  → recalibrate to 420 ppm ambient CO₂
```