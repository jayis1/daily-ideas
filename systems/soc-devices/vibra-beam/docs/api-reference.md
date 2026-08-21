# Vibra Beam — API Reference

## BLE / UART Protocol

All frames: `0xAA <type> <len_hi> <len_lo> <payload...> <crc8>` where `crc8 = XOR of all preceding bytes`.

### Outgoing (device → host)

| Type | Name    | Payload                                  | Notes |
|------|---------|------------------------------------------|-------|
| 0x01 | RESULT  | `measure_result_t` (floats)              | After a measurement completes |
| 0x02 | FFT     | `{freq_peak, mag_peak, thd, snr, bin_hz, n_bins, bins[128]}` | Spectrum summary + 128 bins |
| 0x03 | STREAM  | `{t_ms, n, vel[64]}`                     | Live velocity excerpt during streaming |

### Incoming (host → device), type 0x10 CMD

Payload: `<param_id:u8> <value:f32>`

| param_id | Parameter         | Units   |
|----------|-------------------|---------|
| 0        | laser_mw          | mW      |
| 1        | vel_lp_fc_hz      | Hz      |
| 2        | audio_gain        | ×       |
| 3        | audio_shift       | ×       |
| 4        | imu_compensate    | 0/1     |
| 5        | ble_stream        | 0/1     |

## SD Card Files

- `vibra.csv` — `time_ms, disp_nm, vel_mms` per sample (up to 25 ksps)
- `vibra.iq` — binary: `<u32 t_ms><u32 n><int16 i><int16 q>...` blocks (up to 2.5 Msps)
- `vibra.cfg` — binary `acq_params_t` struct (persisted user settings)

## Firmware Modules

### interferometer.c
- `interferometer_init()` — set up CORDIC, baseline tracking
- `interferometer_process(iq, pb)` — I/Q → phase → displacement → velocity
- `cordic_atan2f(y, x)` — hardware-accelerated atan2

### dsp.c
- `dsp_fft(vel, n, res)` — Hann-windowed real FFT, peak/THD/SNR
- `dsp_modal_fit(fft, fmin, fmax, m)` — resonance + Q + damping

### imu.c
- `imu_read(s)` — read accel + gyro
- `imu_compensate_velocity(s, t_ms)` — sway velocity (mm/s) for subtraction

### laser.c
- `laser_set_power_mw(mw)` — set laser power (0–5 mW, clamped)
- `laser_safety_check()` — returns 1 if safe (reed + tilt + watchdog)

### audio.c
- `audio_push_velocity(v_mms)` — push a velocity sample to the I²S buffer

## Python Helpers (scripts/)

- `live_view.py` — BLE/Wi-Fi live waveform + spectrum plot (matplotlib)
- `export_csv.py` — read SD CSV → pandas DataFrame → export
- `fft_analyze.py` — offline FFT / spectrogram from CSV
- `modal_fit.py` — resonance + damping extraction (scipy curve_fit)
- `calibrate.py` — fringe / velocity scale calibration utility