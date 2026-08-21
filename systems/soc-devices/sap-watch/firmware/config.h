/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * config.h — System-wide constants and configuration
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SAP_WATCH_CONFIG_H
#define SAP_WATCH_CONFIG_H

#include <stdint.h>
#include <stddef.h>

/* ---- System clock (STM32WL55, M4 core) ---- */
#define CPU_FREQ_HZ           48000000U

/* ---- Measurement cycle ---- */
#define MEASUREMENT_INTERVAL_S  300U     /* 5 min between heat-pulse cycles */
#define BASELINE_SAMPLES        100      /* 10 s pre-pulse baseline @ 10 Hz */
#define PULSE_DURATION_MS        2000U    /* 2 s heat pulse */
#define POST_PULSE_SAMPLES      240      /* 60 s post-pulse @ 4 Hz */
#define POST_PULSE_SAMPLE_HZ    4U
#define BASELINE_SAMPLE_HZ      10U

/* ---- Heater ---- */
#define HEATER_RESISTANCE_OHM   40.0f
#define HEATER_VOLTAGE_V        6.0f
#define HEATER_CURRENT_LIMIT_MA 500U     /* hardware overcurrent trip */
#define HEATER_PULSE_ENERGY_J    1.8f   /* 6V × 0.15A × 2s */

/* ---- Probe geometry ---- */
#define PROBE_SPACING_UP_MM      5.0f    /* upstream thermistor to heater */
#define PROBE_SPACING_DN_MM      10.0f  /* downstream thermistor to heater */
#define PROBE_DEPTH_MM           20.0f  /* insertion depth into sapwood */

/* ---- Thermistor (NCP18XH103F03RB, 10k @ 25C) ---- */
#define THERM_R_REF              10000.0f   /* 10k at 25 C */
#define THERM_R_DIVIDER          10000.0f   /* 10k 0.1% reference resistor */
#define THERM_B2585              3380.0f
#define THERM_A                  0.790389e-3f  /* Steinhart-Hart A */
#define THERM_B                  2.273577e-4f  /* Steinhart-Hart B */
#define THERM_C                  1.6089e-7f    /* Steinhart-Hart C */

/* ---- ADS122U04 ADC ---- */
#define ADC_UART_BAUD            9600U
#define ADC_GAIN                 4       /* PGA gain ×4 (±0.8125 V) */
#define ADC_DATA_RATE            20      /* 20 SPS for 24-bit resolution */

/* ---- Thermal properties of sapwood ---- */
#define K_XYLEM_DEFAULT          0.0025f /* cm²/s thermal diffusivity */
#define RHO_WATER                998.0f  /* kg/m³ */
#define C_WATER                  4186.0f /* J/(kg·K) */
#define RHO_SAPWOOD_DEFAULT      800.0f  /* kg/m³ */
#define C_SAPWOOD_DEFAULT        2500.0f /* J/(kg·K) */
#define WOUND_FACTOR_DEFAULT     1.35f   /* wound correction (species-dependent) */

/* ---- Zero-flow calibration ---- */
#define ZERO_CAL_MIN_SAMPLES     60      /* min predawn readings to validate */
#define ZERO_CAL_PREDAWN_HOUR    4       /* hour (0-23) for predawn zero calibration */
#define ZERO_CAL_RECHECK_DAYS    7       /* re-run zero-cal weekly */

/* ---- Drought-stress detection ---- */
#define STRESS_RATIO_THRESHOLD   0.40f   /* midday/predawn < 40% → stress */
#define STRESS_MIN_FLUX_CMH      1.0f     /* min predawn flux for valid comparison */
#define STRESS_HISTORY_DAYS      7       /* rolling baseline window */
#define STRESS_BASELINE_DROP_PCT 30      /* 30% drop from 7-day mean = anomaly */

/* ---- Sapwood area (set per tree via LoRaWAN downlink) ---- */
#define SAPWOOD_AREA_DEFAULT_CM2 180.0f  /* default for 30cm DBH oak */

/* ---- LoRaWAN ---- */
#define LORA_REGION_868          1       /* 1=EU 868, 0=US 915 */
#define LORA_TX_POWER_DBM        14
#define LORA_SPREADING_FACTOR    7
#define LORA_BANDWIDTH_HZ        125000U
#define LORA_CODING_RATE          5      /* 4/5 */
#define LORA_PREAMBLE_LEN        8
#define LORA_UPLINK_INTERVAL_S   900U   /* 15 min default */
#define LORA_JOIN_TIMEOUT_MS     30000U

/* ---- Sensors ---- */
#define SHT45_ADDR               0x44U
#define TSL2591_ADDR             0x29U
#define MAX17048_ADDR            0x36U
#define SENSOR_POLL_MS           60000U  /* 60 s */

/* ---- Power ---- */
#define BATTERY_LOW_PCT         15
#define BATTERY_CRIT_PCT         8
#define DEEP_SLEEP_LOW_SOC       10      /* enter deep sleep below 10% */
#define ADC_BATTERY_DIVIDER      3.0f
#define ADC_SOLAR_DIVIDER        4.0f

/* ---- External flash (W25Q16, optional log buffer) ---- */
#define FLASH_SECTOR_SIZE        4096U
#define FLASH_LOG_PAGES          512U    /* 512 pages × 8 bytes = 4KB log ring */
#define FLASH_LOG_ENTRY_BYTES    8

/* ---- Pin assignments (mirror README pinout) ---- */
/* ADC / analog */
#define PIN_ADC_READY            0    /* PA0 — ADS122U04 DRDY (EXTI) */
#define PIN_ADC_BAT              1    /* PA1 — ADC1_IN2 battery divider */
#define PIN_ADC_SOLAR            24   /* PB0 — ADC1_IN15 solar divider */

/* UART — ADS122U04 */
#define PIN_ADC_UART_TX          2    /* PA2 — USART2_TX */
#define PIN_ADC_UART_RX          3    /* PA3 — USART2_RX */

/* Heater */
#define PIN_HEATER_MOSFET        4    /* PA4 — heater low-side MOSFET gate (TIM2 PWM) */
#define PIN_HEATER_ENABLE        21   /* PB6 — heater high-side enable (safety) */
#define PIN_HEATER_FAULT         22   /* PB7 — overcurrent comparator fault input */
#define PIN_HEATER_CURRENT       31   /* PC1 — ADC heater current monitor */

/* SPI1 — external flash */
#define PIN_SPI_SCK              5    /* PA5 */
#define PIN_SPI_MISO            6    /* PA6 */
#define PIN_SPI_MOSI            7    /* PA7 */
#define PIN_FLASH_CS            8    /* PA8 */
#define PIN_FLASH_CS_PORT        GPIOA

/* I2C1 — SHT45 + TSL2591 + MAX17048 */
#define PIN_I2C_SCL              9    /* PA9 */
#define PIN_I2C_SDA              10   /* PA10 */

/* Status LEDs (TIM4 PWM) */
#define PIN_LED_GREEN            11   /* PA11 — TIM4_CH1 */
#define PIN_LED_RED              12   /* PA12 — TIM4_CH2 */
#define PIN_LED_AMBER            13   /* PA13 — TIM4_CH3 */

/* Buttons */
#define PIN_BTN_PROG             14   /* PA14 — program/provision */
#define PIN_BTN_MODE             15   /* PA15 — trigger measurement */

/* 1-Wire — DS18B20 */
#define PIN_1WIRE_POWER           17   /* PB1 — strong pull-up power */
#define PIN_1WIRE_DATA            19   /* PB3 — 1-Wire data line */

/* ADC chip select (UART ADC, CS for config commands) */
#define PIN_ADC_CS               20   /* PB4 */

/* Analog front-end power gate */
#define PIN_AFE_POWER             25   /* PB9 — P-MOSFET gate for ADC power */
#define PIN_AFE_RESET             32   /* PC0 — analog front-end reset */

/* LDO / radio control */
#define PIN_TCXO_ENABLE           23   /* PB12 — LoRa TCXO enable */
#define PIN_TSL_INT               23   /* PB8 — TSL2591 INT (alt func) */
#define PIN_TSL_INT_PORT          GPIOB

/* Fuel gauge */
#define PIN_FG_ALRT               33   /* PC13 — MAX17048 alert */

/* Debug UART */
#define PIN_DEBUG_TX              26   /* PB10 — USART3_TX */
#define PIN_DEBUG_RX              27   /* PB11 — USART3_RX */

/* ---- Scheduler task config ---- */
#define MEASURE_STACK_BYTES       2048
#define SENSOR_STACK_BYTES        1024
#define LORAWAN_STACK_BYTES       2048
#define POWER_STACK_BYTES         1024

/* ---- Log ring buffer ---- */
#define LOG_BUFFER_ENTRIES       288   /* 5 min × 288 = 24h of measurements */
#define LOG_ENTRY_STRUCT_BYTES   16

/* ---- Uplink packet sizes ---- */
#define UPLINK_PORT1_BYTES        19
#define UPLINK_PORT2_BYTES         8
#define DOWNLINK_MAX_BYTES       12

#endif /* SAP_WATCH_CONFIG_H */