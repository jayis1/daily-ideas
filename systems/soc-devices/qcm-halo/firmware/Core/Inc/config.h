/*
 * config.h — QCM Halo global configuration
 * STM32G474RET6
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>
#include <stdbool.h>

/* ── Physical constants ──────────────────────────────────── */
#define QUARTZ_DENSITY      2650.0f       /* ρq kg/m³  */
#define QUARTZ_SHEAR_MOD    2.947e10f     /* μq Pa     */
#define PI                  3.14159265358979f

/* ── QCM Parameters ──────────────────────────────────────── */
#define QCM_FUNDAMENTAL_HZ  5000000       /* 5 MHz crystal   */
#define QCM_OVERtones       6             /* 1,3,5,7,9,11    */
extern const uint8_t overtone_multipliers[QCM_OVERtones];

#define QCM_GATE_TIME_MS    1000          /* reciprocal counting gate */
#define QCM_FREQ_RES        0.01f         /* Hz resolution           */
#define QCM_CHANNELS        2

/* Dissipation ring-down */
#define RINGDOWN_SAMPLES    2048
#define RINGDOWN_RATE_HZ    20000000ULL   /* 20 Msps ADC            */
#define RINGDOWN_MAX_US     500           /* max capture window      */

/* ── Si5351A ─────────────────────────────────────────────── */
#define SI5351_I2C_ADDR     0x60
#define SI5351_XTAL_HZ      25000000
#define SI5351_LOAD_CAP     10            /* pF */

/* ── Temperature / TEC ───────────────────────────────────── */
#define TEC_KP              2.5f
#define TEC_KI              0.8f
#define TEC_KD              0.1f
#define TEC_TEMP_MIN        15.0f
#define TEC_TEMP_MAX        50.0f
#define TEC_TEMP_DEFAULT    25.0f
#define TEC_PWM_HZ          20000
#define TEC_I_MAX           4.0f          /* amps */

#define RTD_R_REF           1000.0f       /* ohms at 0°C */
#define RTD_ALPHA           0.003851f     /* PT1000 */

/* ── Liquid Handling ─────────────────────────────────────── */
#define PUMP_PWM_HZ         1000
#define PUMP_MAX_RATE       5.0f          /* mL/min */
#define VALVE_STEPS_PER_REV 4096

/* ── Storage ─────────────────────────────────────────────── */
#define SD_LOG_RATE_HZ      10
#define W25Q128_SIZE        (16*1024*1024)
#define PARAMS_FLASH_ADDR   0x000000

/* ── BLE / UART ──────────────────────────────────────────── */
#define BLE_BAUD            921600
#define BLE_MAX_PAYLOAD     200

/* ── Display ─────────────────────────────────────────────── */
#define OLED_I2C_ADDR       0x3C
#define OLED_WIDTH          128
#define OLED_HEIGHT         64

/* ── Power ───────────────────────────────────────────────── */
#define VBAT_DIVIDER        2.0f
#define VBAT_LOW_MV         3400
#define VBAT_CRIT_MV        3200

/* ── Sauerbrey sensitivity ───────────────────────────────── */
/* S = 2 * f0^2 / (A * sqrt(ρq*μq))  →  Δm = -Δf / S         */
/* For 5 MHz, 1 cm²: S ≈ 56.6 Hz·cm²/µg                     */
#define SAUERBREY_AREA_CM2  0.196f        /* 5mm Ø active area */
#define SAUERBREY_SENS      (2.0f * QCM_FUNDAMENTAL_HZ * QCM_FUNDAMENTAL_HZ / \
                             (SAUERBREY_AREA_CM2 * 1e-7f * \
                              sqrtf(QUARTZ_DENSITY * QUARTZ_SHEAR_MOD)))

/* ── Device state machine ────────────────────────────────── */
typedef enum {
    STATE_BOOT,
    STATE_IDLE,
    STATE_MENU,
    STATE_CALIBRATE,
    STATE_MEASURE,
    STATE_RINGDOWN,
    STATE_PROCESS,
    STATE_DISPLAY_RESULT,
    STATE_LOG_STREAM,
    STATE_EXPERIMENT,
    STATE_ERROR
} device_state_t;

/* ── Acquisition parameters ──────────────────────────────── */
typedef struct {
    uint8_t  channel;           /* 0 or 1                */
    uint8_t  overtone;           /* index into multipliers */
    uint8_t  run_overtone_sweep; /* measure all overtones? */
    float    target_temp;        /* °C, 0 = no control     */
    float    pump_rate;          /* mL/min, 0 = no flow    */
    uint8_t  valve_pos;          /* 0-5                    */
    uint16_t measure_interval_ms;/* auto-measure period    */
    uint16_t duration_s;         /* experiment duration    */
    uint8_t  voigt_fit;          /* run Voigt model?       */
} acq_params_t;

/* ── QCM measurement result ──────────────────────────────── */
typedef struct {
    uint8_t  channel;
    uint8_t  overtone_idx;
    uint8_t  overtone_n;
    float    frequency;          /* Hz            */
    float    f_baseline;         /* Hz (air/ref)  */
    float    delta_f;            /* Hz            */
    float    dissipation;        /* dimensionless */
    float    d_baseline;         /* dimensionless */
    float    delta_d;            /* dimensionless */
    float    temperature;        /* °C            */
    float    sauerbrey_mass;     /* ng/cm²        */
    float    sauerbrey_thick;    /* nm (if rho_f known) */
    float    voigt_thick;        /* nm            */
    float    voigt_viscosity;    /* Pa·s          */
    float    voigt_shear_mod;    /* Pa            */
    uint32_t timestamp_ms;
    uint8_t  valid;
} qcm_result_t;

/* ── Experiment result ───────────────────────────────────── */
typedef struct {
    float    kd;                 /* dissociation constant M  */
    float    kon;                /* association rate 1/(M·s) */
    float    koff;               /* off rate 1/s              */
    float    rmax;               /* max response Hz           */
} kinetic_result_t;

#endif /* CONFIG_H */