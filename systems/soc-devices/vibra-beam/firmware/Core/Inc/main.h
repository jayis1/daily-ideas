/*
 * main.h — Vibra Beam application header
 * STM32G474RET6
 */

#ifndef MAIN_H
#define MAIN_H

#include "stm32g4xx_hal.h"
#include "config.h"

/* ── Device state machine ────────────────────────────────── */
typedef enum {
    STATE_BOOT = 0,
    STATE_IDLE,
    STATE_MENU,
    STATE_CALIBRATE,
    STATE_MEASURE,
    STATE_PROCESS,
    STATE_DISPLAY_RESULT,
    STATE_LOG_STREAM,
    STATE_AUDIO_LISTEN,
    STATE_FAULT
} device_state_t;

/* ── Acquisition parameters ──────────────────────────────── */
typedef struct {
    float    laser_mw;             /* laser power, mW */
    float    vel_lp_fc_hz;         /* velocity low-pass cutoff */
    uint16_t fft_size_log2;        /* FFT size = 2^N */
    uint8_t  imu_compensate;       /* enable self-motion compensation */
    uint8_t  audio_enable;         /* heterodyne-to-audio */
    float    audio_gain;           /* audio gain */
    float    audio_shift;          /* audio frequency shift × */
    uint8_t  log_csv;              /* SD CSV logging */
    uint8_t  log_bin;              /* SD raw I/Q binary logging */
    uint8_t  ble_stream;           /* BLE live streaming */
    uint8_t  run_fft;              /* run FFT after measure */
    uint8_t  run_modal;            /* run modal fit after measure */
    float    target_freq_hz;       /* expected target freq (modal fit) */
} acq_params_t;

/* ── Result ──────────────────────────────────────────────── */
typedef struct {
    float    displacement_nm;      /* peak-to-peak displacement */
    float    velocity_mms;         /* peak velocity, mm/s */
    float    dc_velocity_mms;      /* DC (mean) velocity */
    float    rms_velocity_mms;     /* RMS velocity */
    float    freq_peak_hz;         /* dominant vibration frequency */
    float    thd_pct;              /* total harmonic distortion */
    float    fringe_count;        /* number of 2π fringes crossed */
    float    snr_db;               /* signal-to-noise ratio */
} measure_result_t;

/* ── Externs ─────────────────────────────────────────────── */
extern ADC_HandleTypeDef hadc1, hadc2;
extern I2C_HandleTypeDef hi2c1;
extern SPI_HandleTypeDef hspi2;
extern TIM_HandleTypeDef htim3, htim8;
extern UART_HandleTypeDef huart2;
extern I2S_HandleTypeDef hi2s2;

extern volatile device_state_t g_state;
extern acq_params_t g_params;
extern measure_result_t g_result;

#endif /* MAIN_H */