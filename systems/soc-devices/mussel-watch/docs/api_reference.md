# Mussel Watch — API Reference

## Firmware Architecture

The firmware is structured as a cooperative super-loop scheduler with the following modules:

| Module | File | Responsibility |
|--------|------|---------------|
| Config | `config.h` | Pin assignments, I²C addresses, constants, state struct |
 | Main | `main.c` | Scheduler loop, state machine, button handling |
| Gape Sensor | `gape_sensor.c/.h` | ADS1115 + DRV5053 driver, angle conversion, calibration |
| Water Quality | `water_quality.c/.h` | DS18B20, MS5837, Atlas DO, BME280 drivers |
| Anomaly | `anomaly.c/.h` | Closure detection, rhythm analysis, stress scoring |
| LoRa Uplink | `lora_uplink.c/.h` | SX1262 driver, packet formatting, AES-128 |
| BLE Config | `ble_config.c/.h` | GATT service for phone configuration |
| Logger | `logger.c/.h` | SD card FAT32 CSV logging |
| Power | `power.c/.h` | Battery/solar monitoring, sleep management |

## State Structure

The central `mussel_watch_state_t` structure (defined in `config.h`) carries all runtime state:

```c
typedef struct {
    float gape_angle[MAX_MUSSELS];       // Current gape angle per mussel (degrees)
    float cal_closed_mv[MAX_MUSSELS];    // Calibration: Hall voltage at 0°
    float cal_open_mv[MAX_MUSSELS];      // Calibration: Hall voltage at max open
    int   cal_valid[MAX_MUSSELS];        // Calibration validity flag per channel
    int   n_mussels;                     // Active mussel heads (1–4)

    float water_temp_c;                  // DS18B20 water temperature (°C)
    float dissolved_o2_mgl;              // Atlas DO (mg/L)
    float water_depth_m;                 // MS5837 depth (m)
    float baro_hpa;                      // BME280 barometric (hPa)
    float prev_temp_c;                   // Previous temp for anomaly detection

    float battery_v;                     // Battery voltage (V)
    float solar_v;                       // Solar panel voltage (V)
    int   battery_pct;                   // Battery percentage (0–100)
    int   charging;                      // Solar charging flag

    uint32_t closure_start_ms[MAX_MUSSELS]; // Closure event start timestamps
    int      closure_active[MAX_MUSSELS];   // Currently-in-closure flags
    uint32_t closure_events_hour[MAX_MUSSELS]; // Events this hour
    alert_code_t current_alert;          // Active alert code
    uint32_t alert_time_ms;              // Alert timestamp

    float rhythm_profile[24][MAX_MUSSELS]; // 24-hour hourly gape average
    int   rhythm_count;                   // Total rhythm updates

    uint16_t sample_interval_s;          // Gape sample interval
    uint16_t uplink_interval_s;          // LoRa uplink interval
    uint16_t log_interval_s;             // SD log interval
    float    gape_threshold_deg;          // Closure threshold (degrees)
    uint16_t closure_duration_s;         // Sustained-closure alert threshold
    uint8_t  deployment_id;               // Deployment identifier

    uint32_t last_sample_ms;
    uint32_t last_uplink_ms;
    uint32_t last_log_ms;
    uint32_t boot_time_ms;
    mussel_watch_mode_t mode;             // NORMAL, CALIBRATE, TEST
} mussel_watch_state_t;
```

## Gape Sensor API

### `gape_sensor_init()`
Initialize the TCA9548A multiplexer and all ADS1115 channels.
Returns: 0 on success, -1 on error.

### `gape_mux_select(channel)`
Select a channel (0–3) on the TCA9548A I²C multiplexer.
Returns: 0 on success, -1 on invalid channel or I²C error.

### `gape_read_hall_mv(channel)`
Read the Hall voltage from the ADS1115 for the given channel.
Returns: Hall voltage in millivolts, or -1.0 on error.

### `gape_hall_to_angle(channel, hall_mv)`
Convert Hall voltage to gape angle using stored calibration.
Returns: angle in degrees (0 = closed, 15 = open), or -1.0 if uncalibrated.

### `gape_calibrate_closed(channel)`
Record the current Hall voltage as the 0° (closed) reference.

### `gape_calibrate_open(channel)`
Record the current Hall voltage as the maximum-open reference.

### `gape_sample_all(state)`
Sample all active mussel heads and update `state->gape_angle[]`.

### `gape_cal_save(state)` / `gape_cal_load(state)`
Persist/load calibration to/from nRF flash (non-volatile).

## Water Quality API

### `water_quality_init()`
Initialize all water-quality sensors (BME280 reset).

### `water_temp_read_c()`
Read water temperature from DS18B20.
Returns: temperature in °C, or -999.0 on error.

### `water_do_read_mgl()`
Read dissolved oxygen from Atlas Scientific DO EZO.
Returns: DO in mg/L, or -1.0 on error.

### `water_depth_read_m(baro_hpa)`
Read water depth from MS5837, compensated for atmospheric pressure.
Returns: depth in meters, or -999.0 on error.

### `baro_read_hpa()`
Read barometric pressure from BME280.
Returns: pressure in hPa, or -1.0 on error.

### `water_quality_sample_all(state)`
Sample all water-quality parameters into the state struct.

## Anomaly Detection API

### `anomaly_init(state)`
Initialize anomaly detection state (zero counters, clear alerts).

### `anomaly_update(state, now_ms)`
Process a new gape sample for anomaly detection.
Returns: `alert_code_t` if a new alert is triggered, `ALERT_NONE` otherwise.

### `anomaly_check_water_quality(state)`
Check water-quality parameters for anomalies (temperature spike, hypoxia).
Returns: `alert_code_t` if anomaly detected.

### `anomaly_update_rhythm(state, now_ms)`
Update the 24-hour rhythm profile. Call once per uplink cycle.

### `anomaly_alert_name(code)`
Returns a human-readable string for the given alert code.

## LoRa Uplink API

### `lora_init()`
Initialize the SX1262 radio and configure LoRa modem parameters.

### `lora_build_packet(state, pkt)`
Build a 34-byte LoRa packet from the current state.
Returns: packet length (34 bytes).

### `lora_tx(pkt, len)`
Transmit a packet via SX1262.
Returns: 0 on success, -1 on error.

### `lora_uplink(state, immediate)`
Build + encrypt + transmit the current state.
If `immediate` is nonzero, this is an alert uplink.

### `crc32(data, len)`
Compute CRC32 (IEEE 802.3 polynomial) for packet integrity.

### `aes128_encrypt_block(key, block)`
AES-128 ECB encrypt a 16-byte block in-place.

## BLE Config API

### `ble_config_init(state)`
Initialize BLE SoftDevice and register the Mussel Watch GATT service.

### `ble_config_start_advertising()` / `ble_config_stop_advertising()`
Control BLE advertising.

### `ble_config_poll(state)`
Check for pending BLE commands (calibration, config changes).

### `ble_config_update_notify(state)`
Send BLE notifications with live gape, water-quality, and alert data.

### `ble_on_write(uuid, data, len, state)`
Write handler for GATT characteristics (called by SoftDevice).

### `ble_on_read(uuid, data, len, state)`
Read handler for GATT characteristics (called by SoftDevice).

## Logger API

### `logger_init()`
Initialize SD card and FAT32 filesystem.

### `logger_log(state, timestamp_s)`
Append a CSV log line with current state.

### `logger_log_calibration(state, channel, event)`
Log a calibration event.

### `logger_log_alert(state, code, timestamp_s)`
Log an alert event.

### `logger_get_filename(buf, len, timestamp_s)`
Generate the daily log filename (YYYY-MM-DD.csv).

## Power API

### `power_init()`
Initialize SAADC for battery and solar voltage monitoring.

### `power_read_battery_v()` / `power_read_solar_v()`
Read battery/solar voltage. Returns volts.

### `power_battery_pct(voltage)`
Compute battery percentage from voltage (0–100%).

### `power_is_charging(solar_v)`
Check if solar panel is actively charging. Returns 1/0.

### `power_enter_sleep(ms)`
Enter low-power sleep for `ms` milliseconds. Powers down peripherals.

### `power_manage(state)`
Full power management: read voltages, update state, handle low battery.

## Alert Codes

| Code | Constant | Description |
|------|----------|-------------|
| 0 | `ALERT_NONE` | Normal operation |
| 1 | `ALERT_CLOSURE_EVENT` | Mussel closed for >30s |
| 2 | `ALERT_SUSTAINED_CLOSURE` | Mussel closed for >10 minutes |
| 3 | `ALERT_RHYTHM_DEVIATION` | Gape pattern deviates from 24h baseline |
| 4 | `ALERT_MULTI_MUSSEL_EVENT` | ≥2 mussels closed simultaneously |
| 5 | `ALERT_TEMP_ANOMALY` | Sudden temperature change >5°C |
| 6 | `ALERT_DO_ANOMALY` | Dissolved O₂ < 4 mg/L |
| 7 | `ALERT_LOW_BATTERY` | Battery < 20% |

## LoRa Packet Format (34 bytes)

| Byte | Field | Type | Description |
|------|-------|------|-------------|
| 0 | device_class | uint8 | 0x01 = Mussel Watch |
| 1 | deployment_id | uint8 | Deployment hash |
| 2–9 | timestamp | uint64 BE | Unix epoch |
| 10 | flags | uint8 | bit0=alert, bit1=low_batt, bit2=cal_mode, bit3=multi-head |
| 11–14 | mussel_a_gape | float32 LE | Gape angle ° (0xFF=unused) |
| 15–18 | mussel_b_gape | float32 LE | (0xFF=unused) |
| 19–22 | mussel_c_gape | float32 LE | (0xFF=unused) |
| 23–26 | mussel_d_gape | float32 LE | (0xFF=unused) |
| 27 | water_temp | int8 | °C × 2 |
| 28–29 | dissolved_o2 | uint16 LE | mg/L × 100 |
| 30–31 | depth | int16 LE | cm (signed) |
| 32 | battery_pct | uint8 | 0–100 |
| 33 | alert_code | uint8 | See alert table |