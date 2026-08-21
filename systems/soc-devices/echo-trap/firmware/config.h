/*
 * Echo Trap — Acoustic Insect Trap
 * ESP32-S3 Firmware
 *
 * config.h — System-wide constants and configuration
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef ECHO_TRAP_CONFIG_H
#define ECHO_TRAP_CONFIG_H

#include <stdint.h>
#include <stddef.h>

/* ---- System clock (ESP32-S3, max 240 MHz) ---- */
#define CPU_FREQ_HZ           240000000U

/* ---- I2S capture ---- */
#define I2S_SAMPLE_RATE_HZ    16000U     /* 16 kHz — covers insect wingbeats 30-1500 Hz */
#define I2S_CHANNELS          2         /* dual MEMS mics */
#define I2S_BITS_PER_SAMPLE   16
#define I2S_DMA_BUF_COUNT     4
#define I2S_DMA_BUF_LEN       250       /* 250 samples × 2 ch = 500 frames/buf → 250 ms at 16 kHz */
#define WINDOW_MS             250       /* acoustic window length */
#define WINDOW_SAMPLES        (I2S_SAMPLE_RATE_HZ / 1000 * WINDOW_MS)   /* 4000 samples */

/* ---- Capture cadence ---- */
#define CAPTURE_INTERVAL_MS   1000U     /* capture a window every 1 s */
#define FRAMES_DOUBLE_BUF     2

/* ---- Pre-processing ---- */
#define HP_FILTER_CUTOFF_HZ   30.0f     /* high-pass (remove wind/traffic rumble) */
#define LP_FILTER_CUTOFF_HZ   2000.0f   /* low-pass (wingbeats are <1.5 kHz) */
#define ENERGY_THRESHOLD_DBFS -55.0f    /* RMS energy threshold (adaptive) */
#define AUTOCORR_MIN_HZ       20
#define AUTOCORR_MAX_HZ       1500

/* ---- FFT ---- */
#define FFT_SIZE              256       /* 256-point FFT of 250 ms window */
#define FFT_BINS              (FFT_SIZE / 2 + 1)  /* 129 bins */

/* ---- CNN classifier ---- */
#define NUM_CLASSES           12        /* 11 species + unknown */
#define CONFIDENCE_THRESHOLD  0.70f     /* top-1 prob required for capture trigger */
#define CNN_INPUT_SIZE        FFT_BINS  /* 129-point magnitude spectrum × 2 mics = 258 inputs */

/* ---- Species classes ---- */
enum {
    SPECIES_AEDES = 0,        /* target — mosquito disease vector */
    SPECIES_CULEX,            /* target — mosquito disease vector */
    SPECIES_ANOPHELES,        /* target — malaria vector */
    SPECIES_HONEYBEE,         /* beneficial — pollinator */
    SPECIES_DROSOPHILA,       /* target — fruit fly (SWD) */
    SPECIES_CODLING_MOTH,     /* target — orchard pest */
    SPECIES_ARMYWORM_MOTH,    /* target — row crop pest */
    SPECIES_HOUSEFLY,         /* neutral */
    SPECIES_WASP,             /* target — nuisance */
    SPECIES_LACEWING,         /* beneficial — predator */
    SPECIES_HOVERFLY,         /* beneficial — pollinator/predator */
    SPECIES_UNKNOWN,          /* unclassified */
    SPECIES_COUNT
};

#define NUM_TARGETS   7
#define NUM_BENEFICIAL 3

/* ---- UV LED lure ---- */
#define UV_PWM_FREQ_HZ        1000U     /* LEDC frequency */
#define UV_PWM_RESOLUTION     8         /* 8-bit → 0-255 duty */
#define UV_DUTY_DAY_OFF       0
#define UV_DUTY_NIGHT_LOW     77        /* 30% of 255 */
#define UV_DUTY_OVERRIDE      255       /* 100% */
#define UV_NIGHT_LUX_THRESH   10.0f     /* below this lux = "night" */

/* ---- Fan trap ---- */
#define FAN_PWM_FREQ_HZ       20000U    /* 20 kHz (above audible) */
#define FAN_PWM_RESOLUTION    10        /* 10-bit → 0-1023 */
#define FAN_SOFTSTART_MS      200       /* ramp-up time */
#define FAN_DURATION_MS       2000      /* capture duration */
#define FAN_DURATION_MOTH_MS  3000      /* longer for large moths */

/* ---- LoRaWAN ---- */
#define LORA_REGION_915       1          /* US/AU; 0 for EU 868 */
#define LORA_TX_POWER_DBM     20
#define LORA_SPREADING_FACTOR 7          /* SF7 default, ADR adjusts */
#define LORA_BANDWIDTH_HZ    125000U
#define LORA_CODING_RATE      5          /* 4/5 */
#define LORA_PREAMBLE_LEN    8
#define LORA_UPLINK_INTERVAL_S  900     /* 15 min default */
#define LORA_JOIN_TIMEOUT_MS    30000

/* ---- Sensors ---- */
#define SHT40_ADDR            0x44
#define TSL2591_ADDR          0x29
#define MAX17048_ADDR         0x36
#define SENSOR_POLL_MS        10000U     /* 10 s */

/* ---- Power ---- */
#define BATTERY_LOW_PCT       15
#define BATTERY_CRIT_PCT       5
#define LIGHT_SLEEP_ENABLED    1
#define ADC_BATTERY_DIVIDER    3.0f      /* 1:3 voltage divider */
#define ADC_SOLAR_DIVIDER      4.0f      /* 1:4 voltage divider */

/* ---- OLED (optional setup display) ---- */
#define OLED_WIDTH            128
#define OLED_HEIGHT           64
#define OLED_SPI_HZ           8000000U

/* ---- Pin assignments (mirror README pinout) ---- */
/* I2S */
#define PIN_I2S_SD1           0     /* GPIO0 — mic 1 data */
#define PIN_I2S_SD2           1     /* GPIO1 — mic 2 data */
#define PIN_I2S_WS            2     /* GPIO2 — word select */
#define PIN_I2S_SCK           3     /* GPIO3 — bit clock */

/* PWM outputs */
#define PIN_UV_LED            4     /* GPIO4 — UV LED enable (LEDC ch 0) */
#define PIN_FAN_PWM           5     /* GPIO5 — fan MOSFET gate (LEDC ch 1) */

/* SPI3 — SX1262 */
#define PIN_SX_NSS            6     /* GPIO6 */
#define PIN_SX_SCK            7     /* GPIO7 */
#define PIN_SX_MISO           8     /* GPIO8 */
#define PIN_SX_MOSI           9     /* GPIO9 */
#define PIN_SX_RST            10    /* GPIO10 */
#define PIN_SX_DIO1           11    /* GPIO11 (IRQ) */
#define PIN_SX_DIO2           12    /* GPIO12 (IRQ) */
#define PIN_SX_BUSY           13    /* GPIO13 (input) */

/* I2C */
#define PIN_I2C_SDA           14    /* GPIO14 */
#define PIN_I2C_SCL           15    /* GPIO15 */

/* SPI2 — OLED (optional) */
#define PIN_OLED_DC           16    /* GPIO16 */
#define PIN_OLED_RST          17    /* GPIO17 */
#define PIN_OLED_CS           18    /* GPIO18 */
#define PIN_SPI2_SCK           19    /* GPIO19 */
#define PIN_SPI2_MISO          20    /* GPIO20 (unused for write-only OLED) */
#define PIN_SPI2_MOSI          21    /* GPIO21 */

/* Status LEDs */
#define PIN_LED_GREEN         38    /* GPIO38 — LoRa/reporting OK */
#define PIN_LED_RED           39    /* GPIO39 — pest detected */
#define PIN_LED_AMBER         40    /* GPIO40 — charging */

/* Buttons */
#define PIN_BTN_PROG          41    /* GPIO41 — program/provision */
#define PIN_BTN_MODE          42    /* GPIO42 — mode */

/* ADC */
#define PIN_ADC_BAT           46    /* GPIO46 — ADC1_CH0 */
#define PIN_ADC_SOLAR          47    /* GPIO47 — ADC1_CH1 */

/* Fan tachometer (optional) */
#define PIN_FAN_TACH          48    /* GPIO48 */

/* ---- FreeRTOS task config ---- */
#define TASK_STACK_CAPTURE    4096
#define TASK_STACK_CLASSIFY    8192
#define TASK_STACK_TRAP        2048
#define TASK_STACK_LORAWAN     4096
#define TASK_STACK_POWER       2048
#define TASK_PRIO_CAPTURE     5
#define TASK_PRIO_CLASSIFY    4
#define TASK_PRIO_TRAP        3
#define TASK_PRIO_LORAWAN     3
#define TASK_PRIO_POWER       2

/* ---- Queue lengths ---- */
#define QUEUE_CAPTURE_LEN     4
#define QUEUE_DETECTION_LEN   8
#define QUEUE_UPLINK_LEN     8

#endif /* ECHO_TRAP_CONFIG_H */