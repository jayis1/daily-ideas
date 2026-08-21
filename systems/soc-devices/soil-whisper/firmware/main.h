/*
 * Soil Whisper — Type Definitions
 * STM32WL55JC — Soil Intelligence Probe
 */

#ifndef MAIN_H
#define MAIN_H

#include "stm32wlxx_hal.h"
#include <stdint.h>
#include <stdarg.h>

/* ── Data structures ───────────────────────────────────────────────── */

typedef struct {
    float freq_dry;                /* Hz at 0% VWC */
    float freq_wet;                /* Hz at 100% VWC */
    float slope_mv_per_decade;     /* ISE Nernst slope */
    float offset_mv;               /* ISE offset (E0) */
} cal_channel_t;

typedef struct {
    cal_channel_t moist[3];        /* Moisture at 10/20/40 cm */
    cal_channel_t npk[3];          /* NPK: NO3, PO4, K */
    float ph_slope;                /* mV per pH unit (negative) */
    float ph_offset;               /* mV at pH 7 */
} cal_data_t;

typedef struct {
    float vwc[3];                  /* % VWC at each depth */
    float freq_hz[3];              /* Raw frequency Hz */
} moisture_data_t;

typedef struct {
    float celsius[3];             /* °C at each depth */
} temp_data_t;

typedef struct {
    float no3_ppm;                /* Nitrate ppm */
    float po4_ppm;                /* Phosphate ppm */
    float k_ppm;                  /* Potassium ppm */
} npk_data_t;

typedef struct {
    uint8_t flags;
    moisture_data_t moist;
    temp_data_t temp;
    npk_data_t npk;
    float ph;
    float humidity;
    float ambient_temp;
    float vbat;
} sensor_data_t;

typedef struct {
    uint32_t dev_addr;
    uint8_t nwk_skey[16];
    uint8_t app_skey[16];
    uint32_t fcnt_up;
    uint32_t fcnt_down;
} lora_state_t;

/* ── Power domain enumeration ──────────────────────────────────────── */

typedef enum {
    PWR_MOISTURE = 0,
    PWR_NPK_PH,
    PWR_ONEWIRE,
} sensor_power_domain_t;

/* ── Flags for payload validity ────────────────────────────────────── */

#define FLAG_MOIST_VALID  (1 << 7)
#define FLAG_TEMP_VALID   (1 << 6)
#define FLAG_NPK_VALID    (1 << 5)
#define FLAG_PH_VALID     (1 << 4)
#define FLAG_HUMID_VALID  (1 << 3)

#endif /* MAIN_H */