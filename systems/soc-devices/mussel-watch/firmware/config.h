/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * config.h — Pin assignments, I²C addresses, constants
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>
#include <stddef.h>

/* ---- nRF52840 GPIO pin assignments ---- */
#define PIN_I2C_SDA         3       /* P0.03 — I²C data (TCA9548A, ADS1115×4, MS5837, Atlas, BME280) */
#define PIN_I2C_SCL         4       /* P0.04 — I²C clock */
#define PIN_SPI_MISO         28      /* P0.28 — SPI MISO (SX1262 + SD card shared) */
#define PIN_SPI_MOSI         29      /* P0.29 — SPI MOSI */
#define PIN_SPI_SCK          30      /* P0.30 — SPI SCK */
#define PIN_SX1262_CS        31      /* P0.31 — LoRa CS */
#define PIN_SD_CS            26      /* P0.26 — SD card CS */
#define PIN_SX1262_DIO1      24      /* P0.24 — LoRa IRQ */
#define PIN_SX1262_NRST      25      /* P0.25 — LoRa reset */
#define PIN_SX1262_TCXO      7       /* P0.07 — SX1262 TCXO enable (3.3V) */
#define PIN_ONEWIRE          2       /* P0.02 — DS18B20 1-Wire data */
#define PIN_BATTERY_V        5       /* P0.05 — SAADC battery voltage (÷2) */
#define PIN_SOLAR_V          6       /* P0.06 — SAADC solar panel voltage (÷2) */
#define PIN_SENSOR_PWR       8       /* P0.08 — Sensor head power enable (load switch) */
#define PIN_MODE_BTN         9       /* P0.09 — Mode / calibrate button */
#define PIN_LED_BLUE         10      /* P0.10 — Status LED (blue) */
#define PIN_LED_RED          11      /* P0.11 — Alert LED (red) */
#define PIN_MUX_RESET        12      /* P0.12 — TCA9548A reset (active low) */
#define PIN_SD_PWR           15      /* P0.15 — SD card power (load switch) */
#define PIN_DO_PWR           16      /* P0.16 — Atlas DO probe power */

/* ---- I²C addresses (7-bit) ---- */
#define I2C_ADDR_ADS1115_0   0x48    /* Mussel A: ADDR→GND */
#define I2C_ADDR_ADS1115_1   0x49    /* Mussel B: ADDR→VDD */
#define I2C_ADDR_ADS1115_2   0x4A    /* Mussel C: ADDR→SDA */
#define I2C_ADDR_ADS1115_3   0x4B    /* Mussel D: ADDR→SCL */
#define I2C_ADDR_TCA9548A    0x70    /* I²C multiplexer */
#define I2C_ADDR_MS5837      0x76    /* Pressure/depth sensor */
#define I2C_ADDR_BME280      0x77    /* Barometric pressure (air pod) */
#define I2C_ADDR_ATLAS_DO    0x61    /* Atlas Scientific DO EZO */

/* ---- ADS1115 config ---- */
#define ADS1115_REG_CONVERSION   0x00
#define ADS1115_REG_CONFIG       0x01
#define ADS1115_REG_LO_THRESH    0x02
#define ADS1115_REG_HI_THRESH    0x03
#define ADS1115_PGA_2048         0x0400  /* PGA gain ±2.048V */
#define ADS1115_DR_128SPS        0x0080  /* 128 SPS data rate */
#define ADS1115_MUX_AIN0_GND     0x4000  /* Single-ended AIN0 vs GND */
#define ADS1115_OS_SINGLE        0x8000  /* Single-shot */
#define ADS1115_ACTIVE           0x0000  /* Begin conversion (not OS bit set) */

/* ---- DRV5053 Hall sensor ---- */
#define DRV5053_SENSITIVITY_MV_PER_MT   18.0f  /* mV/mT at Vcc=3.3V */
#define DRV5053_VREF_MV                 1650.0f /* Zero-field output ≈ Vcc/2 */

/* ---- Gape sensing ---- */
#define MAX_MUSSELS              4
#define GAPE_SAMPLE_RATE_HZ      4
#define GAPE_MAX_ANGLE_DEG       15.0f
#define GAPE_CLOSED_THRESHOLD    2.0f   /* degrees — below this = closed */
#define GAPE_CAL_FLASH_KEY       0xDEADBEEF

/* ---- Anomaly detection ---- */
#define CLOSURE_EVENT_MIN_DURATION_S    30      /* closure >30s = event */
#define SUSTAINED_CLOSURE_ALERT_S       600     /* closure >10min = sustained alert */
#define CLOSURE_EVENTS_PER_HOUR_ALERT   3       /* ≥3 events/hour = stress */
#define RHYTHM_WINDOW_HOURS             24
#define RHYTHM_BINS                     24      /* hourly bins */
#define TEMP_ANOMALY_DELTA_C            5.0f    /* sudden temp change = anomaly */
#define DO_ANOMALY_LOW_MGL              4.0f    /* DO <4 mg/L = hypoxia alert */

/* ---- LoRa (SX1262) ---- */
#define LORA_FREQ_HZ            868100000ULL  /* EU 868.1 MHz (use 915000000 for US) */
#define LORA_SF                 7             /* Spreading factor 7 (default, ADR) */
#define LORA_BW                 125000        /* 125 kHz bandwidth */
#define LORA_CR                 4             /* Coding rate 4/5 */
#define LORA_TX_POWER_DBM       14            /* +14 dBm */
#define LORA_PREAMBLE_LEN        8
#define LORA_PKT_LEN            34            /* payload bytes */
#define LORA_AES_KEY_LEN        16

/* ---- Power / timing ---- */
#define DEFAULT_SAMPLE_INTERVAL_S      15      /* gape sample every 15s */
#define DEFAULT_UPLINK_INTERVAL_S      900     /* LoRa uplink every 15 min */
#define DEFAULT_LOG_INTERVAL_S         60      /* SD log every 60s */
#define BATTERY_LOW_PCT                20
#define SOLAR_CHARGE_THRESHOLD_MV      4000   /* panel voltage to consider charging */

/* ---- Battery monitoring (SAADC) ---- */
#define BATTERY_DIVIDER_RATIO          2.0f
#define BATTERY_FULL_MV                4200
#define BATTERY_EMPTY_MV               3200
#define SAADC_RESOLUTION_BITS          12
#define SAADC_REF_MV                    3600  /* nRF internal Vref (0.6×6=3.6V) */

/* ---- MS5837 pressure sensor ---- */
#define MS5837_CMD_RESET       0x1E
#define MS5837_CMD_CONV_D1_256  0x40
#define MS5837_CMD_CONV_D2_256  0x50
#define MS5837_CMD_ADC_READ    0x00
#define MS5837_CMD_PROM_READ   0xA0  /* + offset 0..7 */

/* ---- Atlas Scientific DO EZO commands ---- */
#define ATLAS_CMD_READ         "R"
#define ATLAS_CMD_CAL          "Cal"
#define ATLAS_CMD_INFO         "I"
#define ATLAS_CMD_LED          "L"
#define ATLAS_CMD_STATUS       "Status"

/* ---- Alert codes ---- */
typedef enum {
    ALERT_NONE                = 0,
    ALERT_CLOSURE_EVENT       = 1,
    ALERT_SUSTAINED_CLOSURE   = 2,
    ALERT_RHYTHM_DEVIATION    = 3,
    ALERT_MULTI_MUSSEL_EVENT  = 4,
    ALERT_TEMP_ANOMALY        = 5,
    ALERT_DO_ANOMALY          = 6,
    ALERT_LOW_BATTERY         = 7,
} alert_code_t;

/* ---- Operation modes ---- */
typedef enum {
    MODE_NORMAL = 0,     /* default: sample + uplink + log */
    MODE_CALIBRATE,      /* calibration mode (BLE-driven) */
    MODE_TEST,           /* test mode: continuous BLE streaming */
} mussel_watch_mode_t;

/* ---- Global state struct ---- */
typedef struct {
    /* Gape angles (degrees) for each mussel head */
    float gape_angle[MAX_MUSSELS];
    /* Calibration values (Hall voltage at closed / open) */
    float cal_closed_mv[MAX_MUSSELS];
    float cal_open_mv[MAX_MUSSELS];
    int   cal_valid[MAX_MUSSELS];
    int   n_mussels;  /* active heads (1–4) */

    /* Water quality */
    float water_temp_c;
    float dissolved_o2_mgl;
    float water_depth_m;
    float baro_hpa;
    float prev_temp_c;  /* for anomaly detection */

    /* Power */
    float battery_v;
    float solar_v;
    int   battery_pct;
    int   charging;

    /* Anomaly */
    uint32_t closure_start_ms[MAX_MUSSELS];
    int      closure_active[MAX_MUSSELS];
    uint32_t closure_events_hour[MAX_MUSSELS];
    uint32_t last_hour_reset_ms;
    alert_code_t current_alert;
    uint32_t alert_time_ms;

    /* Rhythm tracking */
    float rhythm_profile[RHYTHM_BINS][MAX_MUSSELS];
    int   rhythm_count;

    /* Config */
    uint16_t sample_interval_s;
    uint16_t uplink_interval_s;
    uint16_t log_interval_s;
    float    gape_threshold_deg;
    uint16_t closure_duration_s;
    uint8_t  deployment_id;

    /* Timing */
    uint32_t last_sample_ms;
    uint32_t last_uplink_ms;
    uint32_t last_log_ms;
    uint32_t boot_time_ms;
    mussel_watch_mode_t mode;
} mussel_watch_state_t;

#endif /* CONFIG_H */