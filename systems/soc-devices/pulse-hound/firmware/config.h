/*
 * Pulse Hound — RF Signal Hunter
 * ESP32-S3 Firmware
 *
 * config.h — System-wide constants and configuration
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_CONFIG_H
#define PULSE_HOUND_CONFIG_H

#include <stdint.h>
#include <stddef.h>

/* ---- ESP32-S3 system ---- */
#define CPU_FREQ_HZ             240000000U
#define I2C_FREQ_HZ              400000U
#define I2C_PORT                 I2C_NUM_0
#define I2C_SDA_GPIO             1
#define I2C_SCL_GPIO             2

/* ---- RF detector (AD8318) ---- */
#define AD8318_PWDN_GPIO         21      /* power-down, active low */
#define AD8318_VRFLAG_GPIO       19      /* clip indicator (optional) */
#define AD8318_ANALOG_EN_GPIO    40      /* LDO enable for AFE */
#define AD8318_SLOPE_MV_PER_DB    (-19.0f)
#define AD8318_INTERCEPT_V        1.80f
#define AD8318_TEMP_COEFF_MV_PER_C (-2.2f)
#define AD8318_TEMP_AT_CALIBRATION_C 25.0f
#define AD8318_TEMP_NOMINAL_V     0.80f  /* TEMP pin at 25 C */
#define AD8318_TEMP_MV_PER_C      10.0f

/* ---- ADS1115 16-bit ADC ---- */
#define ADS1115_ADDR             0x48U
#define ADS1115_AIN_RSSI         0x4000U /* mux = AIN0 single-ended */
#define ADS1115_AIN_TEMP         0x5000U /* mux = AIN1 single-ended */
#define ADS1115_GAIN_6144       0x0000U /* PGA gain 1 (±6.144 V) */
#define ADS1115_DR_860SPS        0x00E0U
#define ADS1115_REG_CONFIG       0x01U
#define ADS1115_REG_CONVERSION   0x00U

/* ---- Sampling ---- */
#define SWEEP_SAMPLE_RATE_HZ     500U    /* ADC samples per second in sweep mode */
#define DF_SAMPLE_RATE_HZ        100U    /* ADC samples per second in DF mode */
#define WATERFALL_ROWS           64
#define WATERFALL_COLS           96
#define WATERFALL_ROW_MS         16U     /* 500 Hz / 8 samples per row ≈ 16 ms */

/* ---- OLED (SSD1306, 128x64, I2C) ---- */
#define SSD1306_ADDR             0x3CU
#define SSD1306_WIDTH            128
#define SSD1306_HEIGHT           64
#define DISPLAY_FPS              30
#define DISPLAY_WATERFALL_WIDTH  96
#define DISPLAY_INFO_WIDTH       32

/* ---- Stepper (28BYJ-48 via ULN2003) ---- */
#define STEPPER_IN1_GPIO         14
#define STEPPER_IN2_GPIO         15
#define STEPPER_IN3_GPIO         16
#define STEPPER_IN4_GPIO         17
#define STEPPER_POWER_GPIO       18      /* high-side MOSFET enable */
#define STEPPER_STEPS_PER_REV    2048U   /* 28BYJ-48 with 1:64 gear */
#define STEPPER_DF_STEPS         64U     /* 64 steps for 360 (5.625 deg each) */
#define STEPPER_SETTLE_MS         200U   /* settle time per DF step */
#define STEPPER_SAMPLE_MS         500U   /* sampling window per DF step */
#define STEPPER_HOME_GPIO        42      /* reed switch home sensor (active low) */

/* ---- Audio (LM386 via LEDC PWM) ---- */
#define AUDIO_PWM_GPIO           9
#define AUDIO_PWM_FREQ_HZ        10000U  /* 10 kHz carrier */
#define AUDIO_PWM_RES_BITS        10     /* 10-bit resolution (0–1023) */
#define AUDIO_AMP_SHUTDOWN_GPIO   8      /* LM386 shutdown (high = on) */
#define AUDIO_CLICK_MIN_RATE_HZ   1      /* noise floor */
#define AUDIO_CLICK_MAX_RATE_HZ   50     /* strong signal */

/* ---- SD card (SPI) ---- */
#define SD_MOSI_GPIO             10
#define SD_MISO_GPIO             11
#define SD_SCK_GPIO              12
#define SD_CS_GPIO               13
#define SD_LOG_INTERVAL_MS       200U    /* log every 200 ms */

/* ---- BLE ---- */
#define BLE_DEVICE_NAME          "Pulse Hound"
#define BLE_SERVICE_UUID        "8e7f1a01-b000-1000-8000-00805f9b34fb"
#define BLE_CHAR_RSSI           "8e7f1a02-b000-1000-8000-00805f9b34fb"
#define BLE_CHAR_SPECTRUM       "8e7f1a03-b000-1000-8000-00805f9b34fb"
#define BLE_CHAR_BEARING        "8e7f1a04-b000-1000-8000-00805f9b34fb"
#define BLE_CHAR_CLASS          "8e7f1a05-b000-1000-8000-00805f9b34fb"
#define BLE_CHAR_MODE           "8e7f1a06-b000-1000-8000-00805f9b34fb"
#define BLE_CHAR_BATTERY        "8e7f1a07-b000-1000-8000-00805f9b34fb"
#define BLE_CHAR_LOG_CTRL       "8e7f1a08-b000-1000-8000-00805f9b34fb"
#define BLE_NOTIFY_INTERVAL_MS   100U

/* ---- Fuel gauge (MAX17048) ---- */
#define MAX17048_ADDR            0x36U
#define MAX17048_REG_VCELL        0x02U
#define MAX17048_REG_SOC          0x04U
#define MAX17048_REG_VERSION      0x08U
#define MAX17048_REG_CHGRT        0x16U
#define MAX17048_ALRT_GPIO        38

/* ---- Buttons ---- */
#define BTN_MODE_GPIO            3
#define BTN_SCAN_GPIO            4
#define BTN_DF_GPIO              5
#define BTN_DEBOUNCE_MS          50

/* ---- LEDs ---- */
#define LED_GREEN_GPIO           6
#define LED_RED_GPIO             7

/* ---- TP4056 charge status ---- */
#define CHRG_STATUS_GPIO         39

/* ---- Modes ---- */
typedef enum {
    MODE_SWEEP = 0,     /* waterfall + audio */
    MODE_DF    = 1,     /* direction finding with rotating antenna */
    MODE_MONITOR = 2,   /* fixed-frequency monitoring with peak hold */
    MODE_POWER_SAVE = 3, /* low-power 1 Hz sampling */
} pulse_hound_mode_t;

/* ---- Signal classification ---- */
typedef enum {
    CLASS_CW        = 0,   /* continuous wave / analog bug */
    CLASS_WIFI_BLE  = 1,   /* bursty 10–100 ms on */
    CLASS_CELLULAR  = 2,   /* pulsed, 0.5–5 ms */
    CLASS_RADAR     = 3,    /* pulsed, 1–10 µs */
    CLASS_THERMAL   = 4,   /* slow drift, not a signal */
    CLASS_UNKNOWN   = 5,
    CLASS_COUNT
} signal_class_t;

/* ---- Power ---- */
#define BATTERY_LOW_PCT          15
#define BATTERY_CRIT_PCT         8
#define BATTERY_DIVIDER           2.0f  /* 1:2 voltage divider */

/* ---- RSSI thresholds ---- */
#define RSSI_NOISE_FLOOR_DBM    (-78.0f)
#define RSSI_ALARM_DBM          (-30.0f)
#define RSSI_MAX_DBM            (5.0f)
#define RSSI_MIN_DBM            (-80.0f)

/* ---- Classification windows ---- */
#define CLASS_WINDOW_S            5      /* 5 s analysis window */
#define CLASS_SAMPLE_HZ           100U   /* envelope sample rate for classifier */
#define CLASS_MIN_CONFIDENCE       0.5f  /* minimum autocorrelation confidence */

#endif /* PULSE_HOUND_CONFIG_H */