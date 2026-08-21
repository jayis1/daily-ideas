/*
 * sonar-cast / firmware / main.h
 * Global types, constants, and declarations for the STM32G474 core.
 */
#ifndef SONAR_CAST_MAIN_H
#define SONAR_CAST_MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

/* CMSIS DSP Q15 type (from arm_math.h in real build) */
typedef int16_t q15_t;

/* ---- System constants ---- */
#define SYS_CLK_HZ        170000000
#define ADC_SAMPLE_RATE   1000000       /* 1 Msps ADS7945 */
#define ADC_BITS          12
#define ADC_MAX           4095

/* ---- CHIRP parameters ---- */
#define CHIRP_F0          150000        /* 150 kHz start */
#define CHIRP_F1          250000        /* 250 kHz end */
#define CHIRP_DURATION_US 500           /* 0.5 ms sweep */
#define CHIRP_SAMPLES     (ADC_SAMPLE_RATE / 1000000 * CHIRP_DURATION_US) /* 500 */
#define CHIRP_HAMMING     1

/* ---- Range / depth ---- */
#define SOUND_SPEED_DEFAULT 1500.0f     /* m/s fresh water 20C */
#define MIN_DEPTH_M       0.3f
#define MAX_DEPTH_M       80.0f
#define RANGE_RES_M       0.075f        /* 7.5 cm pulse-compressed */
#define BLANK_SAMPLES     ((uint32_t)(MIN_DEPTH_M * 2.0f * ADC_SAMPLE_RATE / SOUND_SPEED_DEFAULT))

/* ---- Echo capture window ---- */
/* After each ping we capture N samples covering the max range. */
#define ECHO_WINDOW_SAMPLES  16384      /* 16 ms → ~12 m; extend by decimation for 80 m */
#define ECHO_BIN_COUNT       128        /* water-column echogram bins for BLE */

/* ---- Detector ---- */
#define CFAR_GUARD   8
#define CFAR_TRAIN   16
#define CFAR_PFA     1e-4f
#define MAX_FISH_PER_PING 32

/* ---- States ---- */
typedef enum {
    ST_IDLE = 0,    /* not in water / powered on standby */
    ST_ACTIVE,      /* pinging + detecting + logging + streaming */
    ST_DRIFT,       /* low-power: 1 ping/s, no Wi-Fi, GPS on */
    ST_SLEEP,       /* everything off, ESP32 deep-sleep, GPS warm */
} sonar_state_t;

/* ---- Results ---- */
typedef struct {
    float    depth_m;          /* bottom depth (tilt-corrected) */
    float    depth_pres_m;     /* pressure-derived depth (cross-check) */
    uint8_t  bottom_type;      /* 0=hard 1=soft 2=weedy 3=unknown */
    float    bottom_conf;      /* 0..1 */
    uint8_t  fish_count;
    float    fish_depths[MAX_FISH_PER_PING];   /* m */
    float    fish_lengths[MAX_FISH_PER_PING];  /* cm (TS→length estimate) */
    float    fish_ts[MAX_FISH_PER_PING];       /* dB */
    float    temp_c;           /* DS18B20 water temp */
    float    sound_speed;      /* m/s, temp-corrected */
    float    tilt_deg;         /* transducer tilt from vertical */
    float    lat, lon;         /* GPS (from ESP32 via UART) */
    float    hdop;             /* GPS HDOP */
    uint32_t unix_ts;          /* GPS time */
    uint8_t  echogram[ECHO_BIN_COUNT]; /* 0..255 water-column intensity */
} sonar_result_t;

/* ---- Detector / bottom type ---- */
#define BT_HARD   0
#define BT_SOFT   1
#define BT_WEEDY  2
#define BT_UNKNOWN 3
extern const char *const BOTTOM_NAMES[4];

/* ---- Global context ---- */
typedef struct {
    sonar_state_t   state;
    sonar_result_t  last;
    uint32_t        ping_count;
    uint16_t        battery_mv;
    bool            charging;
    bool            water_detected;
    bool            sd_present;
    bool            gps_fix;
    uint8_t         ping_rate_hz;     /* 5..20 */
    float           user_salinity_ppm; /* 0 fresh, ~35000 marine */
} sonar_ctx_t;

extern sonar_ctx_t g_ctx;

/* ---- millis ---- */
uint32_t millis(void);

/* ---- module init functions ---- */
void chirp_init(void);
void hrtim_drv_init(void);
void adc_dsp_init(void);
void detector_init(void);
void imuw_init(void);
void depth_init(void);
void sd_log_init(void);
void oled_init(void);
void uart_link_init(void);
void model_init(void);

/* ---- module task/process functions ---- */
void chirp_fire(void);                       /* transmit one CHIRP ping */
void chirp_pulse_compress(const uint16_t *raw, uint32_t n_raw,
                          float *env_out, uint32_t n_env);  /* matched filter */
const uint16_t *chirp_get_freq_lut(void);
uint16_t *adc_capture(uint32_t n);           /* DMA capture n samples, return buffer */
void adc_pulse_compress(uint16_t *raw, float *env_bins, uint32_t n_bins);  /* matched filter → envelope */
void detector_run(const float *env, uint32_t n, sonar_result_t *r);
void bottom_class_run(const float *env, uint32_t n, uint32_t bottom_idx, sonar_result_t *r);
void imuw_read_tilt(float *tilt_deg);
void depth_read(float *temp_c, float *pressure_m, float *sound_speed);
void sd_log_write(const sonar_result_t *r);
void oled_update(const sonar_ctx_t *ctx);
void uart_link_send_result(const sonar_result_t *r);
void uart_link_poll(void);                   /* non-blocking: parse GPS from ESP32 */

/* ---- helpers ---- */
float clampf(float v, float lo, float hi);

#endif /* SONAR_CAST_MAIN_H */