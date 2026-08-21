/*
 * lode-sweep / firmware / main.h
 * Global types, constants, and declarations for the STM32G474 core.
 */
#ifndef LODE_SWEEP_MAIN_H
#define LODE_SWEEP_MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* ---- System constants ---- */
#define SYS_CLK_HZ        170000000
#define ADC_SAMPLE_RATE   1000000       /* 1 Msps internal ADC */

/* ---- TX pulse parameters ---- */
#define TX_PULSE_US       100           /* 100 µs on-time */
#define TX_PERIOD_US      1000          /* 1 kHz repetition rate */
#define TX_OFF_US         (TX_PERIOD_US - TX_PULSE_US)  /* 900 µs off */
#define TX_VOLTAGE        12.0f         /* boosted rail */
#define COIL_INDUCTANCE   0.5e-3        /* 0.5 mH */
#define COIL_RESISTANCE   2.0f          /* 2 Ω */

/* ---- 16 time gates (log-spaced 10–284 µs after TX off) ---- */
#define NUM_GATES         16
static const float GATE_DELAY_US[NUM_GATES] = {
    10.0f, 12.5f, 15.6f, 19.5f, 24.4f, 30.5f, 38.1f, 47.7f,
    59.6f, 74.5f, 93.1f, 116.4f, 145.5f, 181.9f, 227.4f, 284.2f
};
#define GATE_OVERSAMPLE   16            /* 16 samples averaged per gate */
#define GATE_WINDOW_US    16            /* 16 µs window per gate */

/* ---- ADC ---- */
#define ADC_BITS          12
#define ADC_MAX           4095
#define ADC_SAMPLES_PER_PULSE  (NUM_GATES * GATE_OVERSAMPLE) /* 256 */

/* ---- Target classification ---- */
#define NUM_CLASSES       8
#define NUM_TEMPLATES     32
#define KNN_K             5

/* Class indices */
#define CL_IRON           0
#define CL_FOIL           1
#define CL_NICKEL         2
#define CL_PULLTAB        3
#define CL_ZINC           4
#define CL_GOLD           5
#define CL_COPPER         6
#define CL_SILVER         7

extern const char *const CLASS_NAMES[NUM_CLASSES];

/* ---- States ---- */
typedef enum {
    ST_IDLE = 0,    /* powered, no sweeping */
    ST_ACTIVE,      /* full detection + GPS + BLE */
    ST_DRIFT,       /* detection only, no BLE/Wi-Fi, GPS on */
    ST_SLEEP,       /* everything off, ESP32 deep-sleep wake */
} sweep_state_t;

/* ---- Detection result ---- */
typedef struct {
    uint8_t  target_class;      /* 0–7 (NUM_CLASSES) */
    float    confidence;        /* 0..1 (fraction of k nearest neighbors) */
    float    depth_cm;          /* estimated depth */
    float    signal_strength;   /* sum of all 16 gates (normalized) */
    float    decay[NUM_GATES];  /* normalized 16-gate decay curve */
    float    tilt_deg;          /* coil tilt from horizontal */
    float    lat, lon;          /* GPS (from ESP32 via UART) */
    float    hdop;              /* GPS HDOP */
    uint32_t unix_ts;           /* GPS time */
    uint8_t  iron_discrim;      /* 1 if iron/foil silenced in audio */
} sweep_result_t;

/* ---- Global context ---- */
typedef struct {
    sweep_state_t    state;
    sweep_result_t   last;
    uint32_t         pulse_count;
    uint16_t         battery_mv;
    bool             charging;
    bool             sd_present;
    bool             gps_fix;
    bool             headphones;
    uint8_t          sensitivity;     /* 1–10 */
    bool             discrim_mode;    /* iron/foil audio blanking */
    float            ground_amp;      /* adaptive ground amplitude */
    float            ground_tau;      /* adaptive ground time constant */
} sweep_ctx_t;

extern sweep_ctx_t g_ctx;

/* ---- millis ---- */
uint32_t millis(void);

/* ---- module init functions ---- */
void pi_driver_init(void);
void decay_init(void);
void ground_init(void);
void target_id_init(void);
void depth_init(void);
void audio_init(void);
void imuw_init(void);
void sd_log_init(void);
void oled_init(void);
void uart_link_init(void);
void model_init(void);

/* ---- module task/process functions ---- */
void pi_fire_and_sample(int16_t *samples_out);     /* one TX pulse + ADC capture */
void decay_extract(const int16_t *raw, float *gates); /* 16-gate averaging */
void decay_normalize(float *gates);                   /* normalize to 0..1 */
void ground_balance(float *gates);                    /* subtract ground model */
void ground_calibrate(const float *gates);            /* update ground model */
void target_id_classify(const float *gates, sweep_result_t *r);
void depth_estimate(sweep_result_t *r);
void audio_update(const sweep_result_t *r);
void imuw_read_tilt(float *tilt_deg);
void sd_log_write(const sweep_result_t *r);
void oled_update(const sweep_ctx_t *ctx);
void uart_link_send_result(const sweep_result_t *r);
void uart_link_poll(void);

/* ---- helpers ---- */
float clampf(float v, float lo, float hi);

#endif /* LODE_SWEEP_MAIN_H */