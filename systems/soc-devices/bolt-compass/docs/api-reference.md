# Bolt Compass — API Reference

Firmware API for the Bolt Compass lightning direction-finder. All
functions are in `firmware/main/`. See `types.h` for the shared structs.

## Core types (`types.h`)

```c
typedef struct {
    int16_t ch[4];           // [0]=NS, [1]=EW, [2]=slow-E, [3]=fast-E
} sample_t;

typedef struct {
    sample_t  *buf;          // RING_LEN entries (PSRAM)
    volatile int wr;         // ISR write index
    volatile uint64_t ts_us;
} ring_t;

typedef struct {
    float peak_ns, peak_ew, peak_slow_e, peak_fast_e;
    float rise_us, zero_cross_us, slow_tail_ratio;
    float loop_coherence, spectral_centroid_khz;
    int   e_sign;
    float feat[16];
    int16_t wave_ns[400], wave_ew[400], wave_e[400];
    uint64_t ts_us;
} sferic_t;

typedef struct { int label; float conf; float prob[3]; } classify_t;
typedef struct { float azimuth_deg, distance_km, peak_field_uv; } geo_t;
typedef struct { uint64_t ts_us; sferic_t sf; classify_t cls; geo_t geo; } stroke_t;
typedef struct { float bearing_deg, distance_km; int stroke_count, cg_count;
                 float flash_rate_per_min; uint64_t first_seen_us, last_seen_us;
                 float approach_kmph; bool active; } storm_cell_t;
```

## ADC (`adc.h`)

```c
int      adc_init(void);          // configure ADS131M04, arm DRDY ISR
void     adc_isr(void);           // DRDY edge handler body
ring_t  *adc_ring(void);          // direct ring access for the detector
uint64_t adc_snapshot(sample_t *out, int n);  // copy latest n samples
void     adc_sleep(void);
void     adc_wake(void);
```

`adc_init()` configures the ADS131M04 for 8 ksps, PGA ×8, continuous
conversion, and installs the DRDY falling-edge GPIO interrupt. The ISR
reads 4×24-bit samples over SPI and pushes into the PSRAM ring buffer.

## Detection (`detect.h`)

```c
void   detect_init(void);
int    detect_sferic(ring_t *r, sferic_t *out);
float  detect_noise_floor(void);
```

`detect_sferic()` runs the CFAR detector over the latest 10 ms of the
ring. If a sferic is found, it fills `out` with the 16-feature vector,
the 50 ms waveform window, and timing. Returns 1 on detection, 0
otherwise. Called at ~100 Hz from the sferic core task.

## Classification (`classify.h`)

```c
void classify_init(void);
void classify_sferic(const sferic_t *s, classify_t *out);
```

Runs the int8 logistic-regression classifier (3 classes: CG=0, IC=1,
CC=2). Fills `out->label`, `out->conf` (softmax max), `out->prob[]`.

## Bearing (`bearing.h`)

```c
float bearing_compute(const sferic_t *s);
```

Returns azimuth 0–360° (0=N, clockwise) from the crossed-loop
goniometer, with 180° ambiguity resolved by the E-field sign.

## Ranging (`range.h`)

```c
typedef enum { GROUND_OCEAN, GROUND_WET, GROUND_AVG, GROUND_DRY, GROUND_ICE } ground_t;
typedef struct { ground_t ground; int daytime; float ref_field_uv; } range_model_t;

float range_estimate(const sferic_t *s, const range_model_t *m);
void  range_defaults(range_model_t *m);
```

Estimates distance (km) from the sferic peak amplitude + the
Earth-ionosphere waveguide propagation model. Newton iteration on the
inverse of `E(d) = E_ref · exp(−α·d) · sqrt(d_ref/d)`.

## Storm tracker (`storm.h`)

```c
void storm_init(void);
void storm_add(const stroke_t *st);
void storm_snapshot(storm_t *out);
int  storm_alerts(alert_t *out, int n);
```

Online DBSCAN clustering of strokes into storm cells. `storm_alerts()`
returns pending alerts (STORM_APPROACHING, STORM_IMMINENT, FIRST_CG).

## GPS (`gps.h`)

```c
void     gps_init(void);
uint64_t gps_pps_last(void);       // µs timestamp of last PPS edge
uint64_t gps_sample_count(void);   // ADC samples since last PPS
int      gps_fix_valid(void);
void     gps_position(int32_t *lat_e7, int32_t *lon_e7, int32_t *alt_cm);
void     gps_tick_sample(void);    // called by ADC ISR per sample
```

## Display (`display.h`)

```c
void display_init(void);
void display_radar(const storm_t *storm, const stroke_t *last);
void display_status(const char *l1, const char *l2);
```

## SD logging (`sdlog.h`)

```c
int  sdlog_mount(void);
void sdlog_sferic(const stroke_t *st);
void sdlog_flush(void);
```

## BLE (`ble.h`)

```c
void ble_init(void);
void ble_notify_sferic(const stroke_t *st);
void ble_notify_alert(alert_t a);
```

GATT service `0xB07C` with:
- `0xB071` SfericEvent (notify, 12 bytes packed)
- `0xB073` StormAlert (notify, 1 byte)
- `0xB074` Command (write)

## Wi-Fi (`wifi.h`)

```c
void wifi_init(void);
void wifi_stream_sferic(const stroke_t *st);
```

AP+STA, HTTP endpoints:
- `GET /` — captive config page
- `GET /events.json` — last 100 strokes
- `GET /stream` — Server-Sent Events feed
- `TCP 7777` — raw 12-byte packed events

## Power (`power.h`)

```c
void   power_init(void);
float  power_soc(void);            // battery state-of-charge 0..100
int    power_solar_present(void);
void   power_light_sleep(void);    // sleep until next ADC DRDY
```

## FFT (`fft.h`)

```c
void fft256(float *re, float *im);  // in-place 256-pt Radix-2
```