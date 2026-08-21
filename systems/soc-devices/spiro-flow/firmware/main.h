/**
 * spiro_flow/main.h — Spiro Flow Portable Electronic Spirometer
 *
 * CH32V203RBT6 (RISC-V RV32IMAC, 144 MHz, 128 KB flash, 64 KB SRAM)
 * main firmware header.
 *
 * FreeRTOS-like cooperative task loop (super-loop with timer ISRs):
 *   sensor_task   — SDP810 differential pressure sampling @ 250 Hz
 *   flow_task     — flow integration, volume computation, maneuver detection
 *   spirometry_task — FVC/FEV1/PEF/FEF25-75 computation + quality grading
 *   display_task  — SH1106 OLED flow-volume loop + results
 *   ble_task      — UART protocol to ESP32-C3 BLE/WiFi bridge
 *   flash_task    — W25Q128 session logging
 *   button_task   — button polling + coaching buzzer
 *
 * Build: see firmware/Makefile (riscv-none-embed-gcc + WCH CH32V20x HAL)
 */

#ifndef SPIRO_FLOW_MAIN_H
#define SPIRO_FLOW_MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <math.h>

/* ── Pin assignments (CH32V203RBT6 LQFP64) ────────────────────────── */

/* I2C1 — shared bus: SDP810 (0x21), BME280 (0x76), SH1106 (0x3C) */
#define PIN_I2C1_SCL          6    /* PB6  I2C1 SCL */
#define PIN_I2C1_SDA          7    /* PB7  I2C1 SDA */

/* USART1 — to ESP32-C3 BLE/WiFi bridge */
#define PIN_USART1_TX         9    /* PA9  USART1 TX → ESP32-C3 RX */
#define PIN_USART1_RX         10   /* PA10 USART1 RX ← ESP32-C3 TX */

/* USART2 — debug / USB-CDC */
#define PIN_USART2_TX         2    /* PA2  USART2 TX (debug) */
#define PIN_USART2_RX         3    /* PA3  USART2 RX (debug) */

/* SPI2 — W25Q128 flash */
#define PIN_SPI2_SCK          13   /* PB13 SPI2 SCK */
#define PIN_SPI2_MISO         14   /* PB14 SPI2 MISO */
#define PIN_SPI2_MOSI         15   /* PB15 SPI2 MOSI */
#define PIN_FLASH_CS          12   /* PB12 W25Q128 CS */

/* TIM3 CH1 — buzzer PWM */
#define PIN_BUZZER            6    /* PA6  TIM3 CH1 → buzzer (via transistor) */

/* WS2812B — bit-bang on GPIO */
#define PIN_WS2812            0    /* PA0  WS2812B data */

/* ADC1 — battery monitoring */
#define PIN_BATT_ADC          1    /* PA1  ADC1 CH1 (battery divider) */

/* Buttons */
#define PIN_BTN_MEASURE       4    /* PA4  MEASURE / start maneuver */
#define PIN_BTN_MODE          5    /* PA5  MODE / navigate */

/* Status LED */
#define PIN_LED_STATUS        8    /* PA8  status LED */

/* ESP32-C3 control */
#define PIN_ESP_EN            3    /* PB3  ESP32-C3 EN */
#define PIN_ESP_BOOT          4    /* PB4  ESP32-C3 BOOT (pull-up) */

/* Charger status */
#define PIN_CHG_STAT          0    /* PB0  MCP73831 STAT */

/* USB (native) */
#define PIN_USB_DM            11   /* PA11 USB D- */
#define PIN_USB_DP            12   /* PA12 USB D+ */

/* ── I2C addresses ────────────────────────────────────────────────── */

#define SDP810_I2C_ADDR       0x21   /* Sensirion SDP810-500Pa */
#define BME280_I2C_ADDR       0x76   /* Bosch BME280 (SDO=GND) */
#define SH1106_I2C_ADDR       0x3C   /* SH1106 OLED 1.3" */

/* ── SDP810 configuration ─────────────────────────────────────────── */

#define SDP810_SAMPLE_HZ      250    /* continuous measurement rate */
#define SDP810_SCALE_FACTOR   120.0f /* scale factor for 500Pa variant */
/* SDP810 differential pressure range: ±500 Pa, 9-bit cmd for continuous */

/* ── Pneumotachograph parameters ──────────────────────────────────── */

/* Fleisch-style pneumotach: pressure drop = R * flow
 * R_screen = 0.0115 Pa·s/L (calibrated for our mesh + housing)
 * flow (L/s) = ΔP (Pa) / R_screen
 */
#define PNEUMO_RESISTANCE     0.0115f   /* Pa·s/L */
#define FLOW_MAX_LPS          14.0f     /* max measurable flow L/s */
#define FLOW_MIN_LPS          -14.0f    /* min (inspiratory) flow L/s */
#define DEAD_SPACE_ML         50.0f     /* mouthpiece dead space mL */

/* ── Sampling parameters ──────────────────────────────────────────── */

#define SAMPLE_RATE_HZ        250      /* pressure sampling rate */
#define SAMPLE_PERIOD_MS      4        /* 1000/250 = 4ms */
#define MANEUVER_TIMEOUT_SEC  15       /* max maneuver duration */
#define MANEUVER_MIN_VOL_ML   100      /* minimum volume for valid maneuver */
#define MANEUVER_WINDOW_SEC   8        /* rolling 8-second capture window */

/* ── Spirometry parameters ────────────────────────────────────────── */

/* BTPS correction:
 * V_btps = V_ambient × (310.15 / (T_amb + 273.15)) × (P_amb - P_H2O) / (P_amb - 47)
 * where 47 mmHg = water vapor pressure at 37°C
 */
#define BTPS_BODY_TEMP_K      310.15f  /* 37°C in Kelvin */
#define BTPS_WATER_VAPOR_MMHG 47.0f    /* saturated water vapor at 37°C */

/* maneuver detection thresholds */
#define BLAST_FLOW_THRESH_LPS 0.5f     /* flow above which exhalation starts */
#define BACK_EXTRAP_MAX_ML    150      /* max back-extrapolation volume for grade A */
#define FET_MIN_SEC           3.0f     /* minimum forced expiratory time */
#define PEF_TIME_WINDOW_MS    80       /* PEF averaging window */

/* quality grading thresholds */
#define GRADE_A_BEV_ML        50       /* back-extrapolation volume */
#define GRADE_B_BEV_ML        100
#define GRADE_C_BEV_ML        150
#define GRADE_A_FET_SEC       6.0f
#define GRADE_B_FET_SEC       3.0f

/* predicted value coefficients (ECSC/ERS 1993 reference equations) */
/* For males: FEV1 = 4.30×H - 0.029×A - 2.89  (H in m, A in years) */
/* For females: FEV1 = 3.95×H - 0.022×A - 2.60 */
/* FVC male: 5.76×H - 0.026×A - 4.34 */
/* FVC female: 4.43×H - 0.026×A - 2.89 */

/* ── Operating modes ──────────────────────────────────────────────── */

typedef enum {
    MODE_IDLE = 0,        /* waiting for maneuver */
    MODE_READY,           /* armed, waiting for blast */
    MODE_CAPTURE,         /* actively capturing flow/volume */
    MODE_RESULTS,         /* showing results */
    MODE_REVIEW,          /* reviewing past sessions */
    MODE_SETTINGS,        /* patient settings entry */
} spiro_mode_t;

/* ── Quality grade ────────────────────────────────────────────────── */

typedef enum {
    GRADE_F = 0,   /* unacceptable */
    GRADE_D,       /* poor */
    GRADE_C,       /* acceptable */
    GRADE_B,       /* good */
    GRADE_A,       /* excellent (ATS/ERS 2019 acceptability) */
} quality_grade_t;

/* ── Patient profile ──────────────────────────────────────────────── */

typedef struct {
    uint8_t  age_years;
    uint8_t  height_cm;
    uint8_t  sex;           /* 0 = male, 1 = female */
    uint8_t  ethnicity;     /* 0 = caucasian, 1 = african, 2 = asian */
    char     name[16];      /* patient identifier */
} patient_t;

/* ── Spirometry results ───────────────────────────────────────────── */

typedef struct {
    /* measured parameters */
    float    fvc_liters;        /* Forced Vital Capacity (L) */
    float    fev1_liters;       /* FEV1 (L) */
    float    fev1_fvc_ratio;    /* FEV1/FVC (%) */
    float    pef_lps;           /* Peak Expiratory Flow (L/s) */
    float    fef2575_lps;      /* FEF25-75% (L/s) */
    float    fet_sec;           /* Forced Expiratory Time (s) */
    float    pif_lps;           /* Peak Inspiratory Flow (L/s) */
    float    fivc_liters;      /* Forced Inspiratory Vital Capacity (L) */
    float    back_extrap_ml;   /* back-extrapolation volume (mL) */
    float    peft_ms;           /* time to PEF (ms) */

    /* predicted values */
    float    fev1_pred;
    float    fvc_pred;
    float    fev1_fvc_pred;

    /* percent predicted */
    float    fev1_pct_pred;
    float    fvc_pct_pred;

    /* diagnostic classification */
    uint8_t  pattern;           /* 0=normal, 1=obstructive, 2=restrictive, 3=mixed */
    float    lln_fev1_fvc;     /* lower limit of normal for FEV1/FVC */

    /* quality */
    quality_grade_t grade;
    uint8_t  acceptability_flags; /* bit0=BEV ok, bit1=FET ok, bit2=smooth */

    /* BTPS correction factor applied */
    float    btps_factor;

    /* ambient conditions at time of maneuver */
    float    ambient_temp_c;
    float    ambient_pressure_mmhg;
    float    ambient_humidity_pct;

    /* metadata */
    uint32_t timestamp;         /* session epoch (from ESP32-C3 NTP) */
    uint16_t session_id;
    uint8_t  maneuver_count;    /* which attempt (1-3) */
    bool     valid;
} spiro_result_t;

/* ── Flow/volume sample buffer ────────────────────────────────────── */

#define MAX_SAMPLES    2000   /* 8 sec × 250 Hz = 2000 samples */

typedef struct {
    float    flow_lps[MAX_SAMPLES];   /* flow in L/s */
    float    volume_ml[MAX_SAMPLES];  /* integrated volume in mL */
    int      n_samples;
    float    sample_rate;
    uint32_t start_tick;
} maneuver_buffer_t;

/* ── Global handles ────────────────────────────────────────────────── */

extern volatile spiro_mode_t g_mode;
extern volatile bool g_measure_trigger;
extern patient_t g_patient;
extern maneuver_buffer_t g_maneuver;
extern spiro_result_t g_result;

/* ── Function prototypes ──────────────────────────────────────────── */

/* sensor drivers */
esp_err_t sdp810_init(void);
esp_err_t sdp810_read_pressure(float *diff_pa, float *temp_c);
esp_err_t sdp810_start_continuous(void);
esp_err_t sdp810_stop_continuous(void);

esp_err_t bme280_init(void);
esp_err_t bme280_read(float *temp_c, float *pressure_mmhg, float *humidity_pct);

esp_err_t sh1106_init(void);
void sh1106_draw_idle(void);
void sh1106_draw_ready(uint8_t battery_pct);
void sh1106_draw_capture(const maneuver_buffer_t *m, float current_flow, float current_vol);
void sh1106_draw_results(const spiro_result_t *r, uint8_t battery_pct);
void sh1106_draw_settings(const patient_t *p, int field);

/* spirometry computation */
void spirometry_compute(maneuver_buffer_t *m, const patient_t *p,
                         const float *ambient, spiro_result_t *r);
float compute_btps(float temp_c, float pressure_mmhg, float humidity_pct);
void compute_predicted(const patient_t *p, float *fev1_pred, float *fvc_pred,
                        float *fev1_fvc_pred, float *lln_ratio);
quality_grade_t grade_maneuver(const maneuver_buffer_t *m, const spiro_result_t *r);

/* flash logging */
esp_err_t flashlog_init(void);
esp_err_t flashlog_write_session(const spiro_result_t *r, const maneuver_buffer_t *m);
esp_err_t flashlog_read_session(uint16_t id, spiro_result_t *r);

/* BLE bridge (UART to ESP32-C3) */
esp_err_t ble_bridge_init(void);
void ble_bridge_send_result(const spiro_result_t *r);
void ble_bridge_send_flow_data(const maneuver_buffer_t *m);
void ble_bridge_poll(void);

/* buzzer */
void buzzer_init(void);
void buzzer_coach_start(void);
void buzzer_coach_blast(void);
void buzzer_coach_done(void);
void buzzer_beep(uint16_t freq_hz, uint16_t duration_ms);

/* WS2812B */
void ws2812_init(void);
void ws2812_set(uint8_t r, uint8_t g, uint8_t b);

/* battery */
uint8_t battery_read_pct(void);

/* utility */
uint32_t millis(void);
void delay_ms(uint32_t ms);

#endif /* SPIRO_FLOW_MAIN_H */