/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * config.h — System-wide constants and configuration
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PING_CALIPER_CONFIG_H
#define PING_CALIPER_CONFIG_H

#include <stdint.h>
#include <stddef.h>

/* ---- System clock (STM32G474, max 170 MHz) ---- */
#define SYSCLK_HZ           170000000U
#define HCLK_HZ              SYSCLK_HZ
#define APB1_HZ              (HCLK_HZ / 1)
#define APB2_HZ              (HCLK_HZ / 1)

/* ---- HRTIM (high-resolution timer, 184 ps) ---- */
#define HRTIM_CLK_HZ         170000000U   /* DLL = 170 MHz → 4× → 680 MHz tick (184 ps) */

/* ---- Ultrasonic acquisition ---- */
#define ADC_SAMPLE_RATE_HZ   5000000U     /* 5 Msps envelope digitization */
#define ADC_BITS             12
#define ADC_VREF_MV          3300
#define ADC_MAX              4095U
#define MAX_SAMPLES          2048         /* max samples per A-scan window */
#define MIN_SAMPLES          32

/* Capture window: 2 µs → 10 samples, 500 µs → 2500 samples (we cap at MAX_SAMPLES) */
#define CAPTURE_WINDOW_US_DEFAULT 100.0f   /* 100 µs → ~30 mm steel */

/* ---- Pulser ---- */
#define PULSE_WIDTH_NS_MIN   50
#define PULSE_WIDTH_NS_MAX   200
#define PULSE_WIDTH_NS_DEFAULT 100
#define HV_VOLTAGE_MIN_MV    30000        /* −30 V */
#define HV_VOLTAGE_MAX_MV    200000       /* −200 V */
#define HV_VOLTAGE_DEFAULT_MV 100000      /* −100 V */
#define PRF_HZ_MIN           10
#define PRF_HZ_MAX           1000
#define PRF_HZ_DEFAULT       100          /* 100 Hz live A-scan */

/* ---- TGC (time-gain compensation) ---- */
#define TGC_POINTS           256          /* DAC ramp points */
#define TGC_GAIN_MIN_DB      0.0f
#define TGC_GAIN_MAX_DB      48.0f

/* ---- Receiver ---- */
#define LNA_GAIN_LOW_DB      7.6f
#define LNA_GAIN_MID_DB      17.6f
#define LNA_GAIN_HIGH_DB    22.6f
#define VGA_GAIN_MIN_DB      0.0f
#define VGA_GAIN_MAX_DB      55.0f

/* ---- Measurement ---- */
#define MAX_MATERIALS        128
#define MATERIAL_NAME_MAX    24
#define VELOCITY_MIN_MPS     500U
#define VELOCITY_MAX_MPS     12000U
#define THICKNESS_MIN_MM     0.10f
#define THICKNESS_MAX_MM     250.0f

/* ---- Display (SSD1306 128×64) ---- */
#define OLED_WIDTH           128
#define OLED_HEIGHT          64
#define OLED_SPI_HZ          8000000U

/* ---- UART to ESP32-C3 ---- */
#define UART_BAUDRATE        921600
#define UART_BAUDRATE_ESPC3  921600
#define UART_DMA_BUF_SIZE    512

/* ---- FreeRTOS ---- */
#define TASK_STACK_ACQUIRE   512
#define TASK_STACK_PROCESS   768
#define TASK_STACK_UI        1024
#define TASK_STACK_COMM      512
#define TASK_PRIO_ACQUIRE    5
#define TASK_PRIO_PROCESS    4
#define TASK_PRIO_UI        3
#define TASK_PRIO_COMM      2
#define QUEUE_LEN            16

/* ---- Power / fuel gauge ---- */
#define BATTERY_LOW_PCT       15
#define BATTERY_CRIT_PCT      5

/* ---- Pin assignments (mirror README pinout) ---- */
/* ADC inputs */
#define PIN_ADC_ENVELOPE      0    /* PA2  ADC1_IN3 */
#define PIN_ADC_RF            1    /* PA3  ADC2_IN4 */
#define PIN_ADC_BAT           2    /* PA4  ADC1_IN17 */
#define PIN_ADC_HVMON         3    /* PC0  ADC1_IN6 */

/* DAC outputs */
#define PIN_DAC_TGC           0    /* PA0  DAC1_OUT1 */
#define PIN_DAC_HVSET         1    /* PA1  DAC1_OUT2 */

/* GPIO outputs */
#define PIN_HV_ENABLE         5    /* PA5 */
#define PIN_TR_SWITCH         6    /* PA6  MD0100 T/R */
#define PIN_PULSER_EN         7    /* PA7  LMG1210 enable */
#define PIN_OLED_DC           15   /* PA15 */
#define PIN_OLED_RESET        16   /* PB0 */
#define PIN_OLED_CS           17   /* PB1 */
#define PIN_SD_CS             5    /* PB5 (remapped) */
#define PIN_LED_WHITE         6    /* PB6 */
#define PIN_LED_RED           7    /* PB7 */
#define PIN_LED_GREEN         8    /* PB8 */
#define PIN_VDDA_GATE         9    /* PB9 */
#define PIN_BEEPER            1    /* PC1 remapped */
#define PIN_PROBE_DETECT      2    /* PC2 */
#define PIN_AFE_GATE          9    /* PB9 (alias) */
#define PIN_PULSER_INHIBIT    13   /* PC13 */
#define PIN_CAL_OUT           15   /* PC15 */

/* GPIO inputs */
#define PIN_TRIGGER           10   /* PA10 */
#define PIN_ENC_A             11   /* PA11 */
#define PIN_ENC_B             12   /* PA12 */
#define PIN_MENU_BTN          14   /* PB14 */
#define PIN_MODE_BTN          15   /* PB15 */
#define PIN_TAMPER            3    /* PC3 */
#define PIN_VBUS              9    /* PC9 */
#define PIN_CHRG_STAT          11   /* PC11 */
#define PIN_STDBY_STAT         12   /* PC12 */
#define PIN_PROBE_ID          14   /* PC14 */

/* ESP32-C3 control */
#define PIN_ESP_BOOT_EN       4    /* PC4 */
#define PIN_ESP_RESET         5    /* PC5 */
#define PIN_ESP_BOOT0         6    /* PC6 */

#endif /* PING_CALIPER_CONFIG_H */