/*
 * hall-puck / firmware / Core / Inc / main.h
 * Main header — pin definitions and global constants
 *
 * MIT License.
 */
#ifndef MAIN_H
#define MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

/* ===== STM32G474RET6 Pin Assignments ===== */

/* SPI1 — ADS122U04 + ADG714 switch matrix */
#define SPI1_SCK_PIN        5   /* PA5 */
#define SPI1_MISO_PIN       6   /* PA6 */
#define SPI1_MOSI_PIN       7   /* PA7 */
#define ADC_CS_PIN          8   /* PA8 */
#define SW1_CS_PIN          15  /* PA15 — ADG714 #1 (current) */
#define SW2_CS_PIN          0   /* PB0  — ADG714 #2 (voltage) */
#define ADC_DRDY_PIN        1   /* PB1 */

/* SPI2 — OLED + SD card */
#define SPI2_SCK_PIN        13  /* PB13 */
#define SPI2_MISO_PIN       14  /* PB14 */
#define SPI2_MOSI_PIN       15  /* PB15 */
#define OLED_CS_PIN         12  /* PB12 */
#define OLED_DC_PIN         10  /* PB10 */
#define SD_CS_PIN           11  /* PB11 */

/* Current source */
#define DAC1_OUT_PIN        4   /* PA4 — internal DAC1 channel 1 */
#define I_ENABLE_PIN        3   /* PA3 */
#define I_RANGE_SEL_PIN     2   /* PA2 */
#define I_SENSE_MON_PIN     0   /* PA0 — ADC channel */
#define INA_GAIN_SEL_PIN    11  /* PA11 */
#define INA_GAIN_CLK_PIN    12  /* PA12 */

/* Magnet stepper (28BYJ-48 via ULN2003) */
#define STEP_IN1_PIN        0   /* PC0 */
#define STEP_IN2_PIN        1   /* PC1 */
#define STEP_IN3_PIN        2   /* PC2 */
#define STEP_IN4_PIN        3   /* PC3 */
#define MAGNET_POS_PIN      5   /* PC5 — DRV5053 ADC */

/* Temperature + heater */
#define DS18B20_DQ_PIN      4   /* PC4 — 1-wire */
#define HEATER_PWM_PIN      1   /* PA1 — TIM2_CH1 */
#define HEATER_TEMP_PIN     13  /* PC13 — ADC (NTC) */

/* UART to ESP32-C3 */
#define UART_TX_PIN         9   /* PA9 — USART1_TX */
#define UART_RX_PIN         10  /* PA10 — USART1_RX */

/* Buttons + status */
#define BTN_MEASURE_PIN     8   /* PC8 */
#define BTN_MODE_PIN        9   /* PC9 */
#define BTN_MENU_PIN        10  /* PC10 */
#define STATUS_LED_PIN      11  /* PC11 */
#define BUZZER_PIN          12  /* PC12 — TIM3_CH1 */

/* ===== Constants ===== */
#define ELECTRON_CHARGE     1.602176634e-19f   /* C */
#define MAGNETIC_FIELD_T    0.482f              /* T (calibrated N52) */
#define STEPS_PER_REV       2048                /* 28BYJ-48 full steps */
#define HALF_REV_STEPS      1024                /* 180° rotation */

/* ===== Globals ===== */
extern volatile uint32_t sys_tick_ms;

#endif /* MAIN_H */