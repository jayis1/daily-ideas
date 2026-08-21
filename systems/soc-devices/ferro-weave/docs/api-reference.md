# API Reference — Ferro Weave firmware

## STM32G474 firmware (`firmware/main/`)

### `sweep.h`

```c
void  sweep_defaults(sweep_params_t *p);
int   sweep_start(const sweep_params_t *p);
sweep_state_t sweep_get_status(void);
void  sweep_stop(void);
void  sweep_gen_cycle(const sweep_params_t *p, float amp, float *out, int n);
void  sweep_gen_degauss(float *amps, int n_cycles);
```

`sweep_params_t`:
| Field | Type | Range | Notes |
|-------|------|-------|-------|
| `waveform` | `sweep_waveform_t` | SIN/TRI/DC | drive waveform |
| `i_peak` | float | 0.05–2.0 A | peak magnetizing current |
| `freq` | float | 0.1–1000 Hz | sweep frequency |
| `ramp_cycles` | uint16 | 1–100 | amplitude ramp-up cycles |
| `hold_cycles` | uint16 | 1–100 | cycles at peak before capture |
| `degauss` | bool | — | degauss before sweep |

`sweep_state_t`: `IDLE → DEGAUSS → ARM → RAMP → HOLD → CAPTURE →
COMPUTE → LOG → DISARM → DONE` (or `→ FAULT`).

### `adc.h`

```c
void  adc_init(void);
void  adc_arm_capture(void);
bool  adc_wait_capture(uint32_t timeout_ms);
void  adc_to_engineering(const uint16_t *raw_i, const uint16_t *raw_b,
                         int n, float *I, float *B);
void  adc_ocp_handler(void);
```

Raw buffers: `adc_raw_i[ADC_BUF_LEN]`, `adc_raw_b[ADC_BUF_LEN]`
(ADC_BUF_LEN = 4096).

### `bh.h`

```c
int   bh_compute(const float *H, const float *B, int n,
                 const geom_t *g, bh_result_t *out);
void  bh_air_flux_correct(float *B, const float *H, int n, const geom_t *g);
float bh_loop_area(const float *H, const float *B, int n);
float bh_find_hc(const float *H, const float *B, int n);
float bh_find_br(const float *H, const float *B, int n);
```

`geom_t`: `n1, n2, l_e (m), a2 (m²), a_core (m²), rho (kg/m³), freq (Hz)`.

`bh_result_t`: `b_sat (T), h_c (A/m), b_r (T), mu_dc, mu_inc_peak,
p_v (W/kg), squareness, loop_area (T·A/m), n_points`.

### `integrator.h`
```c
void integrator_reset(void);
void integrator_hold_reset(bool hold);
```

### `power.h`
```c
void    power_init(void);
void    power_amp_enable(bool en);
float   power_get_temp_c(void);
uint8_t power_get_soc(void);
float   power_get_vbat(void);
bool    power_fault_latched(void);
void    power_clear_fault(void);
```

### `display.h`
```c
void display_init(void);
void display_plot_loop(const float *H, const float *B, int n,
                       const bh_result_t *r);
void display_status(const char *line1, const char *line2);
```

### `sdlog.h`
```c
int sdlog_mount(void);
int sdlog_write(const sweep_params_t *sp, const geom_t *g,
                const float *H, const float *B, int n,
                const bh_result_t *r);
```

### `esp_link.h`
```c
void esp_link_init(void);
int  esp_link_send_sweep(const sweep_params_t *sp, const geom_t *g,
                         const float *H, const float *B, int n,
                         const bh_result_t *r);
int  esp_link_send_status(const char *s);
int  esp_link_poll_cmd(char *cmd, size_t maxlen);
```

## Text command protocol (ESP32-C3 → STM32)

Commands are ASCII, newline-terminated, sent as `ESP_FRAME_CMD`:

| Command | Effect |
|---------|--------|
| `SWEEP` | start a measurement cycle |
| `WAVE SIN\|TRI\|DC` | select waveform |
| `IPEAK <A>` | set peak current (0.05–2.0) |
| `FREQ <Hz>` | set sweep frequency |
| `GEOM <N1> <N2> <l_e> <A2> <Acore> <rho>` | set specimen geometry |
| `ICAL <gain>` | set current-sense gain calibration |
| `BCAL <kint>` | set integrator scale calibration |
| `STOP` | abort current sweep |

## ESP32-C3 firmware (`firmware/esp32/main/`)

### `proto.h`
```c
uint8_t proto_crc8(const uint8_t *p, int n);
int     proto_decode(const uint8_t *in, int in_len, proto_frame_t *out,
                     int *consumed);
```

### `ble.h`
```c
void ble_init(void);
void ble_notify_sweep(const uint8_t *payload, uint16_t len);
void ble_notify_status(const char *s);
void ble_set_cmd_callback(ble_cmd_cb_t cb);
```

### `wifi.h`
```c
void wifi_init(void);
void wifi_set_last_sweep(const uint8_t *json, int len);
void wifi_start_stream(void);
```

## BLE GATT

| UUID | Type | Purpose |
|------|------|---------|
| `8a7b3c2d-…-2c3d` | service | FerroWeave |
| `8a7b3c2d-…-2c3e` | write | client → device commands (ASCII) |
| `8a7b3c2d-…-2c3f` | notify | device → client sweep/status frames (chunked 180 B) |

## HTTP endpoints (Wi-Fi)

| Method | Path | Returns |
|--------|------|---------|
| GET | `/sweep.json` | last sweep result + arrays |
| GET | `/` | captive config portal (geometry entry) |
| POST | `/cmd` | forward a command to the STM32 |
| TCP | port 7788 | raw frame stream (live plotting) |