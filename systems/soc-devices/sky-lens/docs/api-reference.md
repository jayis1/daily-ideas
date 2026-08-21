# Sky Lens — API Reference

## Acquisition

### `void acquisition_start(void)`
Arm the detector: enable the SiPM bias boost, initialise the ADS7946,
reset the coincidence logic, and begin event collection. If the bias
boost fails to start, sets status to `ACQ_FAULT`.

### `void acquisition_stop(void)`
Disarm the detector: disable the SiPM bias, deinitialise the ADC,
and set status to `ACQ_IDLE`.

### `acquisition_status_t acquisition_get_status(void)`
Returns the current acquisition status:
- `ACQ_IDLE` — not running
- `ACQ_ARMING` — in the process of arming
- `ACQ_RUN` — actively acquiring coincidence events
- `ACQ_FAULT` — a hardware fault has occurred (bias OCP, thermal)
- `ACQ_SLEEP` — in deep-sleep duty-cycle mode
- `ACQ_LIFETIME` — running in muon-lifetime (prompt-delayed) mode

## Coincidence

### `void coincidence_init(void)`
Reset the coincidence logic: clear stamps, reset the event ring, reset
the event counter.

### `void coincidence_set_window_ns(int32_t ns)`
Set the coincidence window in nanoseconds (5–5000 ns). Default: 60 ns.
A wider window catches more real muons but also more accidental
coincidences.

### `int32_t coincidence_get_window_ns(void)`
Returns the current coincidence window in ns.

### `bool coincidence_pop(event_t *out)`
Pop the next coincidence event from the ring. Returns `true` if an
event was available, `false` if the ring is empty. The event struct is
fully populated (heights, Δt, zenith, azimuth, quaternion, pressure,
temperature).

### `uint64_t coincidence_count(void)`
Total number of coincidences detected since the last init.

## Skymap

### `void skymap_init(void)` / `void skymap_clear(void)`
Initialise / clear the 64×32 (az × zen) skymap histogram.

### `void skymap_add_event(float zenith_deg, float az_deg)`
Add a single event to the skymap. Zenith is clipped to [0, 90°),
azimuth is wrapped to [0, 360°).

### `void skymap_get(skymap_t *out)`
Copy the current skymap into `out`. The `skymap_t` struct contains
`cells[64*32]` (uint32) and `total` (uint32).

### `uint32_t skymap_total(void)`
Total number of events in the skymap.

## Zenith

### `void zenith_init(void)` / `void zenith_clear(void)`
Initialise / clear the 18-bin (5° each, 0–90°) zenith histogram.

### `void zenith_add(float zenith_deg)`
Add a zenith angle to the histogram.

### `void zenith_get_bins(uint32_t *bins, int n)`
Copy the zenith histogram bins into `bins` (up to `n` bins).

### `zenith_fit_t zenith_fit(void)`
Fit `I(θ) = I(0)·cos²θ` to the histogram and return:
- `.i0` — fitted I(0) (counts per minute at zenith)
- `.chi2` — reduced chi-squared of the fit
- `.residual` — mean residual

## Lifetime

### `void lifetime_init(void)` / `void lifetime_clear(void)`
Initialise / clear the 200-bin (100 ns each, 0–20 µs) delay histogram.

### `void lifetime_add_delay(float dt_us)`
Add a prompt-delayed inter-event delay (in µs) to the histogram.

### `void lifetime_get_delays(uint32_t *out, int n)`
Copy the delay histogram into `out` (up to `n` bins).

### `lifetime_result_t lifetime_fit(void)`
Fit `N(t) = N0·exp(−t/τ) + bg` to the delay histogram and return:
- `.tau_us` — fitted lifetime τ_µ (µs), expected ≈ 2.197
- `.tau_err_us` — 1-σ error on τ_µ
- `.bg_per_bin` — fitted flat background
- `.chi2` — reduced chi-squared
- `.n_pairs` — total number of prompt-delayed pairs

## Pressure

### `float pressure_read_hpa(void)`
Read the current barometric pressure in hPa from the BMP390.

### `float pressure_read_temp_c(void)`
Read the current temperature in °C from the BMP390.

### `float pressure_correct_rate(float rate_cpm, float p_hpa, float t_c)`
Apply the barometric correction to a muon rate (cpm). Returns the
corrected rate:
```
R_corr = R_meas · exp[ β · (P_ref − P) ]
```
where `P_ref = 1013.25 hPa` and `β = 0.012 hPa⁻¹`.

## Event Protocol

### `void proto_pack_event(const event_t *ev, uint8_t *buf, int *len)`
Pack an event into a 56-byte binary frame for BLE/Wi-Fi transmission.
Frame format:
| Offset | Field | Size |
|--------|-------|------|
| 0–1 | magic 0x534C | 2 |
| 2–5 | seq | 4 |
| 6–13 | ts_us | 8 |
| 14–15 | h0_mv | 2 |
| 16–17 | h1_mv | 2 |
| 18–21 | dt_ps | 4 |
| 22–25 | zenith_deg | 4 |
| 26–29 | az_deg | 4 |
| 30–45 | quaternion (w,x,y,z) | 16 |
| 46–49 | p_hpa | 4 |
| 50–53 | t_c | 4 |
| 54 | flags | 1 |
| 55 | checksum (XOR) | 1 |

### `bool proto_unpack_event(const uint8_t *buf, int len, event_t *ev)`
Unpack a 56-byte frame. Returns `true` if the magic and checksum are
valid.

## SD Logging

### `void sdlog_write_event(const event_t *ev)`
Append an event to `/sdcard/EVENTS/ev_YYYYMMDD.csv`. Each line:
```
ts_us,seq,h0_mv,h1_mv,dt_ps,zenith_deg,az_deg,qw,qx,qy,qz,p_hpa,t_c,flags
```

### `void sdlog_write_daily(const skymap_t *m, const zenith_fit_t *z, const daily_t *d, const lifetime_result_t *lf)`
Write a daily rollup JSON to `/sdcard/EVENTS/daily_YYYYMMDD.json`.

## BLE

### `void ble_send_event(const event_t *ev)`
Send an event frame over the BLE event characteristic (notify).

### `void ble_send_skymap(const skymap_t *m)`
Send the skymap over the BLE skymap characteristic.

### `void ble_send_lifetime(const lifetime_result_t *lf)`
Send the lifetime fit over the BLE lifetime characteristic.

## Power

### `float power_battery_pct(void)`
Battery state-of-charge (0–100%) from the MAX17048.

### `float power_battery_mv(void)`
Battery voltage in mV.

### `void power_deep_sleep(uint64_t us)`
Enter ESP32 light-sleep for `us` microseconds, waking on the SiPM
discriminator edges (RTC GPIO) or the timer. Used for duty-cycled
long runs.