/*
 * visco-shear / firmware / main.h
 * Global definitions for Visco Shear — Pocket Rotational Rheometer
 *
 * MIT License.
 */
#ifndef VISCO_SHEAR_MAIN_H
#define VISCO_SHEAR_MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

/* ── Pin definitions (RP2040) ──────────────────────────────────── */
#define PIN_STEP          0   /* TMC2209 step (PIO-driven) */
#define PIN_DIR           1   /* TMC2209 direction */
#define PIN_TMC_EN        2   /* TMC2209 enable (active low) */
#define PIN_TMC_UART      3   /* TMC2209 UART config */
#define PIN_I2C_SCL       4   /* I2C clock (ADS1115 + OLED) */
#define PIN_I2C_SDA       5   /* I2C data  (ADS1115 + OLED) */
#define PIN_PELTIER_PWM   7   /* DRV8833 AIN1 (Peltier) */
#define PIN_PELTIER_DIR   8   /* DRV8833 AIN2 (Peltier polarity) */
#define PIN_PELTIER_EN    9   /* DRV8833 EN   (Peltier on/off) */
#define PIN_SD_CS        10   /* MicroSD SPI CS */
#define PIN_SPI_SCK      11   /* SPI clock (SD) */
#define PIN_SPI_MISO     12   /* SPI MISO (SD) */
#define PIN_SPI_MOSI     13   /* SPI MOSI (SD) */
#define PIN_BTN_START    14   /* Start button (active low) */
#define PIN_BTN_MODE     15   /* Mode button (active low) */
#define PIN_BTN_MENU     16   /* Menu button (active low) */
#define PIN_BUZZER       17   /* Piezo buzzer (PWM) */
#define PIN_UART_TX      18   /* RP2040 → ESP32-C3 UART TX */
#define PIN_UART_RX      19   /* ESP32-C3 → RP2040 UART RX */
#define PIN_STATUS_LED   20   /* White status LED */
#define PIN_SPINDLE_ID   21   /* Spindle ID (ADC3) — shared w/ ENC_A */
#define PIN_FAULT_TMC    22   /* TMC2209 diagnostic */
#define PIN_LED_B        23   /* Onboard LED B */
#define PIN_LED_G        24   /* Onboard LED G */
#define PIN_LED_R        25   /* Onboard LED R */
#define PIN_ADC_HALL     26   /* ADC0: DRV5053 torque (primary, backup) */
#define PIN_ADC_NTC      27   /* ADC1: Peltier NTC thermistor */
#define PIN_ADC_VBAT     28   /* ADC2: Battery voltage monitor */
#define PIN_ADC_TEMP     29   /* ADC3: RP2040 internal temp diode */

/* ── Constants ─────────────────────────────────────────────────── */
#define I2C_FREQ_HZ      400000   /* I2C bus frequency */
#define UART_BAUD        1000000  /* RP2040 ↔ ESP32-C3 UART baud */
#define SAMPLE_RATE_HZ   2000     /* Torque sample rate (Hz) */
#define TORQUE_AVG       64       /* Torque averaging samples */

/* TMC2209 microstepping */
#define MICROSTEPS       256      /* 1/256 microstep */
#define STEPS_PER_REV    200      /* NEMA8: 200 full steps/rev */
#define STEP_PER_REV     (STEPS_PER_REV * MICROSTEPS)  /* 51200 */

/* ── Spindle geometries ────────────────────────────────────────── */
typedef enum {
    SPINDLE_CC_13 = 0,   /* Coaxial cylinder Ø13mm */
    SPINDLE_CP_25,       /* Cone-plate Ø25mm 1° */
    SPINDLE_VN_16,       /* Vane Ø16mm 4-blade */
    SPINDLE_TB_3,        /* T-bar Ø3mm */
    SPINDLE_COUNT
} spindle_type_t;

typedef struct {
    const char *name;
    float R_i;           /* Inner radius (bob) [m] */
    float R_o;           /* Outer radius (cup) [m] */
    float L;             /* Immersed length [m] */
    float cone_angle;    /* Cone angle [rad] (0 if not CP) */
    float spring_k;      /* Torsion spring constant [mN·m/rad] */
    float vol_mL;        /* Sample volume [mL] */
} spindle_geo_t;

extern const spindle_geo_t spindle_table[SPINDLE_COUNT];

/* ── Measurement modes ─────────────────────────────────────────── */
typedef enum {
    MODE_FLOW_CURVE = 0,   /* Controlled-rate sweep */
    MODE_YIELD_STRESS,     /* Controlled-stress ramp */
    MODE_OSCILLATORY,      /* G′/G″ frequency sweep */
    MODE_THIXOTROPY,       /* Hysteresis + recovery */
    MODE_SINGLE_SPEED,     /* Single-point viscosity */
    MODE_COUNT
} measure_mode_t;

/* ── Rheological models ────────────────────────────────────────── */
typedef enum {
    MODEL_NEWTONIAN = 0,
    MODEL_POWER_LAW,
    MODEL_BINGHAM,
    MODEL_HERSCHEL_BULKLEY,
    MODEL_CASSON,
    MODEL_CROSS,
    MODEL_CARREAU,
    MODEL_COUNT
} rheo_model_t;

typedef struct {
    rheo_model_t model;
    float param[4];      /* Model parameters (model-dependent) */
    float r_squared;     /* Goodness of fit */
    float aic;           /* Akaike Information Criterion */
} model_fit_t;

extern const char *model_names[MODEL_COUNT];

/* ── Measurement result ────────────────────────────────────────── */
#define MAX_FLOW_POINTS 64

typedef struct {
    int n_points;
    float omega[MAX_FLOW_POINTS];     /* rpm */
    float shear_rate[MAX_FLOW_POINTS]; /* 1/s */
    float torque[MAX_FLOW_POINTS];     /* µN·m */
    float viscosity[MAX_FLOW_POINTS];  /* mPa·s */
    float temperature;                 /* °C */
    spindle_type_t spindle;
    measure_mode_t mode;
    model_fit_t best_fit;

    /* Oscillatory results */
    int n_freq;
    float freq[8];       /* Hz */
    float G_prime[8];    /* Pa (storage modulus) */
    float G_double[8];   /* Pa (loss modulus) */
    float tan_delta[8];  /* G″/G′ */
    float eta_complex[8];/* Pa·s */

    /* Thixotropy */
    float hysteresis_area; /* Pa·s⁻¹ (loop area) */
    float recovery_time;   /* s (τ_r) */
} measure_result_t;

/* ── Command codes (BLE/UART) ──────────────────────────────────── */
typedef enum {
    CMD_START       = 0x01,
    CMD_STOP        = 0x02,
    CMD_SET_MODE    = 0x03,
    CMD_SET_SPINDLE = 0x04,
    CMD_SET_TEMP    = 0x05,
    CMD_CALIBRATE   = 0x06,
    CMD_GET_INFO    = 0x07,
    CMD_STREAM_DATA = 0x08,
} cmd_code_t;

/* ── Global state ──────────────────────────────────────────────── */
typedef enum {
    STATE_IDLE = 0,
    STATE_EQUIL,
    STATE_FLOW,
    STATE_OSCILL,
    STATE_THIXO,
    STATE_RESULT,
} sys_state_t;

extern volatile sys_state_t g_state;
extern volatile bool g_measure_request;
extern volatile bool g_cancel_request;

/* ── Function prototypes ───────────────────────────────────────── */
void buzzer_beep(int ms, int freq_hz);

#endif /* VISCO_SHEAR_MAIN_H */