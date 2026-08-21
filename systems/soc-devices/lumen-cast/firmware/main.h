/**
 * lumen_cast/firmware/main.h — Lumen Cast Pocket Goniophotometer
 *
 * STM32G491RET6 (Cortex-M4F @ 170 MHz, 512 KB flash, 112 KB SRAM, LQFP64)
 * main firmware header.
 *
 * Cooperative super-loop with timer ISRs:
 *   motor_task   — TIM2 PWM step generation for TMC2209 / NEMA8 azimuth
 *   servo_task   — TIM3_CH1 PWM for SG90 elevation servo
 *   photometer   — OPT3001 illuminance sampling
 *   color_task   — TCS34725 RGBC → CCT/Duv
 *   goniometry   — spherical integration, beam angle, flux
 *   display_task — SH1106 OLED polar/isocandela plots
 *   ble_task     — UART protocol to ESP32-C3 BLE/WiFi bridge
 *   flash_task   — W25Q128 scan logging
 *   button_task  — debounced button polling
 *
 * Build: see firmware/Makefile (arm-none-eabi-gcc + STM32G4 HAL)
 */

#ifndef LUMEN_CAST_MAIN_H
#define LUMEN_CAST_MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <math.h>

/* ── Pin assignments (STM32G491RET6 LQFP64) ────────────────────────── */

/* TIM2_CH1 — stepper step pulses → TMC2209 STEP */
#define PIN_STEPPER_STEP       0    /* PA0  TIM2_CH1 */
#define PIN_STEPPER_DIR        1    /* PA1  GPIO → TMC2209 DIR */
#define PIN_STEPPER_EN         2    /* PA2  GPIO → TMC2209 EN (active low) */

/* TIM3_CH1 — servo PWM for elevation */
#define PIN_SERVO              6    /* PA6  TIM3_CH1 → SG90 */

/* ADC1 — battery monitoring */
#define PIN_BATT_ADC           3    /* PA3  ADC1_IN4 (battery divider) */

/* Buttons */
#define PIN_BTN_SCAN           4    /* PA4  SCAN / start sweep */
#define PIN_BTN_MODE           5    /* PA5  MODE / navigate / hold for cal */

/* Status LED */
#define PIN_LED_STATUS         8    /* PA8  status LED */

/* USART1 — to ESP32-C3 BLE/WiFi bridge */
#define PIN_USART1_TX          9    /* PA9  USART1 TX → ESP32-C3 RX */
#define PIN_USART1_RX          10   /* PA10 USART1 RX ← ESP32-C3 TX */

/* USB (native) */
#define PIN_USB_DM             11   /* PA11 USB D- */
#define PIN_USB_DP             12   /* PA12 USB D+ */

/* WS2812B */
#define PIN_WS2812             0    /* PB0  WS2812B data */

/* Charger status */
#define PIN_CHG_STAT           1    /* PB1  MCP73831 STAT */

/* ESP32-C3 control */
#define PIN_ESP_EN             3    /* PB3  ESP32-C3 EN */
#define PIN_ESP_BOOT           4    /* PB4  ESP32-C3 BOOT (pull-up) */

/* I2C1 — shared bus: OPT3001, TCS34725, SH1106, DS3231 */
#define PIN_I2C1_SCL           6    /* PB6  I2C1 SCL */
#define PIN_I2C1_SDA           7    /* PB7  I2C1 SDA */

/* SPI2 — W25Q128 flash */
#define PIN_SPI2_SCK           13   /* PB13 SPI2 SCK */
#define PIN_SPI2_MISO          14   /* PB14 SPI2 MISO */
#define PIN_SPI2_MOSI          15   /* PB15 SPI2 MOSI */
#define PIN_FLASH_CS           12   /* PB12 W25Q128 CS */

/* ── I2C addresses ────────────────────────────────────────────────── */

#define OPT3001_I2C_ADDR       0x44   /* TI OPT3001 illuminance sensor */
#define TCS34725_I2C_ADDR      0x29   /* AMS TCS34725 RGB+C color sensor */
#define SH1106_I2C_ADDR        0x3C   /* SH1106 OLED 1.3" */
#define DS3231_I2C_ADDR        0x68   /* Maxim DS3231 RTC */

/* ── Stepper / TMC2209 configuration ──────────────────────────────── */

#define STEPPER_STEPS_PER_REV  3200   /* 200 full × 16 microsteps */
#define STEPPER_MAX_RPM        30
#define STEPPER_SCAN_RPM       15     /* scan speed (4°/s) */
#define STEPPER_STEP_DEG       (360.0f / STEPPER_STEPS_PER_REV) /* 0.1125° */

/* ── Servo (SG90) configuration ───────────────────────────────────── */

#define SERVO_PWM_HZ           50     /* 50 Hz / 20ms period */
#define SERVO_MIN_US           500    /* 0°   → -90° elevation */
#define SERVO_MAX_US           2400   /* 180° → +90° elevation */
#define SERVO_RANGE_DEG        180    /* total servo travel */

/* ── Photometric geometry ─────────────────────────────────────────── */

#define SENSOR_RADIUS_M        0.150f /* sensor-to-source distance (m) */
#define SENSOR_RADIUS_SQ       (SENSOR_RADIUS_M * SENSOR_RADIUS_M) /* 0.0225 */

/* ── Scan configuration ───────────────────────────────────────────── */

#define SCAN_MAX_AZ_STEPS      360    /* max azimuth samples */
#define SCAN_MAX_EL_STEPS      180    /* max elevation samples */

typedef enum {
    SCAN_TYPE_A = 0,     /* azimuth only, 0–360° @ 1° (360 samples) */
    SCAN_TYPE_C,         /* 2-axis: 24 az × 12 el (5°/15° grid) */
    SCAN_MERIDIAN,       /* elevation sweep at fixed azimuth */
    SCAN_NEARFIELD,      /* dense ±60° grid at 5° resolution */
} scan_type_t;

typedef struct {
    scan_type_t type;
    uint16_t    az_steps;     /* number of azimuth samples */
    uint16_t    el_steps;     /* number of elevation samples */
    float       az_start;     /* degrees */
    float       az_end;       /* degrees */
    float       el_start;     /* degrees */
    float       el_end;       /* degrees */
    float       step_deg;     /* angular step size */
} scan_config_t;

/* ── Operating modes ──────────────────────────────────────────────── */

typedef enum {
    MODE_IDLE = 0,
    MODE_HOMING,         /* stepper homing to 0° */
    MODE_SCANNING,       /* active sweep */
    MODE_RESULTS,        /* showing photometric report */
    MODE_REVIEW,         /* reviewing past scans */
    MODE_CALIBRATION,    /* reference lamp calibration */
    MODE_SETTINGS,       /* scan config settings */
} lumen_mode_t;

/* ── Photometric sample ───────────────────────────────────────────── */

typedef struct {
    float    azimuth_deg;    /* 0–360° */
    float    elevation_deg;  /* -90 to +90° */
    float    lux;            /* illuminance (lux) from OPT3001 */
    float    candela;        /* I = lux × r² */
    uint16_t r, g, b, c;     /* TCS34725 raw RGBC */
    float    cct_k;          /* correlated color temperature (K) */
    float    duv;            /* distance from Planckian locus */
    float    x, y;           /* CIE 1931 chromaticity */
} photo_sample_t;

/* ── Scan buffer ──────────────────────────────────────────────────── */

#define MAX_SAMPLES_TOTAL   4320   /* 360×12 max for Type C near-field */

typedef struct {
    photo_sample_t samples[MAX_SAMPLES_TOTAL];
    int            n_samples;
    scan_config_t  config;
    uint32_t       timestamp;     /* from DS3231 */
    float          ambient_lux;   /* pre-scan ambient reading */
    float          cal_factor;    /* calibration factor applied */
} scan_buffer_t;

/* ── Photometric result ───────────────────────────────────────────── */

typedef struct {
    float    luminous_flux_lm;      /* Φ (lm) — spherical integration */
    float    peak_candela;          /* I_max (cd) */
    float    peak_az_deg;           /* azimuth of peak */
    float    peak_el_deg;           /* elevation of peak */
    float    beam_angle_fwhm;       /* FWHM beam angle (°) */
    float    field_angle_10pct;     /* angle to 10% of peak (°) */
    float    cbcp_candela;          /* center beam candlepower (cd) */
    float    beam_uniformity;       /* min/max within beam cone */
    float    throw_m;               /* distance to 0.25 lux (m) */

    float    cct_onaxis_k;          /* CCT at beam center */
    float    duv_onaxis;            /* Duv at beam center */
    float    cct_edge_k;            /* CCT at beam edge */
    float    duv_edge;              /* Duv at beam edge */
    float    delta_cct_k;           /* CCT variation across beam */
    float    macadam_steps_edge;    /* color shift at edge (MacAdam) */

    uint32_t timestamp;
    uint16_t scan_id;
    bool     valid;
} photo_result_t;

/* ── Global handles ────────────────────────────────────────────────── */

extern volatile lumen_mode_t g_mode;
extern volatile bool g_scan_trigger;
extern scan_buffer_t g_scan;
extern photo_result_t g_result;
extern float g_cal_factor;

/* ── Function prototypes ──────────────────────────────────────────── */

/* sensor drivers */
int opt3001_init(void);
int opt3001_read_lux(float *lux);
int tcs34725_init(void);
int tcs34725_read_rgbc(uint16_t *r, uint16_t *g, uint16_t *b, uint16_t *c);

/* color computation */
void color_compute_cct_duv(uint16_t r, uint16_t g, uint16_t b, uint16_t c,
                            float *cct_k, float *duv, float *x, float *y);

/* motor control */
void motor_init(void);
void motor_enable(bool en);
void motor_set_dir(bool clockwise);
void motor_move_to_deg(float target_deg, float rpm);
void motor_step(int steps);
bool motor_at_target(void);
float motor_get_position_deg(void);
void motor_home(void);

/* servo */
void servo_init(void);
void servo_set_elevation(float elev_deg);

/* goniometry computation */
void goniometry_compute(scan_buffer_t *s, photo_result_t *r);
float goniometry_integrate_flux(const scan_buffer_t *s);
float goniometry_beam_angle(const scan_buffer_t *s, float fraction);
void goniometry_find_peak(const scan_buffer_t *s, float *peak_cd,
                           float *az, float *el);

/* display */
int sh1106_init(void);
void sh1106_draw_idle(void);
void sh1106_draw_scanning(const scan_buffer_t *s, float az, float el, uint8_t batt);
void sh1106_draw_results(const photo_result_t *r, uint8_t batt);
void sh1106_draw_polar(const scan_buffer_t *s);
void sh1106_draw_settings(const scan_config_t *c, int field);

/* flash logging */
int flashlog_init(void);
int flashlog_write_scan(const photo_result_t *r, const scan_buffer_t *s);
int flashlog_read_scan(uint16_t id, photo_result_t *r);
uint16_t flashlog_get_count(void);

/* RTC */
int ds3231_init(void);
int ds3231_get_time(uint32_t *epoch);

/* BLE bridge (UART to ESP32-C3) */
int ble_bridge_init(void);
void ble_bridge_send_result(const photo_result_t *r);
void ble_bridge_send_scan_data(const scan_buffer_t *s);
void ble_bridge_send_ies_file(const scan_buffer_t *s);
void ble_bridge_poll(void);

/* WS2812B */
void ws2812_init(void);
void ws2812_set(uint8_t r, uint8_t g, uint8_t b);

/* battery */
uint8_t battery_read_pct(void);

/* utility */
uint32_t millis(void);
void delay_ms(uint32_t ms);

#endif /* LUMEN_CAST_MAIN_H */