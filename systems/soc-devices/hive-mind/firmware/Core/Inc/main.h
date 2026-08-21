/*
 * Hive Mind — Main Header
 * Pin definitions, peripheral handles, and shared types
 * STM32WL55JC beehive health monitor
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef MAIN_H
#define MAIN_H

#include "stm32wlxx_hal.h"

/* ---- Pin Definitions ---- */

/* HX711 Load Cell ADC */
#define HX711_DOUT_PORT    GPIOA
#define HX711_DOUT_PIN     GPIO_PIN_1
#define HX711_SCK_PORT     GPIOA
#define HX711_SCK_PIN      GPIO_PIN_2
#define HX711_PWR_PORT     GPIOB
#define HX711_PWR_PIN      GPIO_PIN_7

/* DS18B20 1-Wire */
#define ONEWIRE_PORT        GPIOB
#define ONEWIRE_PIN         GPIO_PIN_3

/* I2S MEMS Microphone (ICS-43434) */
/* Uses SPI2 in I2S mode:
 *   PB4 = I2S_CK  (SPI2_SCK)
 *   PB5 = I2S_WS  (SPI2_NSS remapped as WS)
 *   PB6 = I2S_SD  (SPI2_MISO remapped as SD)
 */

/* BME280 + SSD1306 OLED (I2C1) */
/*   PA9 = I2C1_SCL
 *   PA10 = I2C1_SDA
 */

/* IR Break-Beam Sensors */
#define IR_LED_OUT_PORT     GPIOB
#define IR_LED_OUT_PIN      GPIO_PIN_8
#define IR_PHOTO_OUT_PORT   GPIOB
#define IR_PHOTO_OUT_PIN    GPIO_PIN_9
#define IR_LED_IN_PORT      GPIOB
#define IR_LED_IN_PIN       GPIO_PIN_10
#define IR_PHOTO_IN_PORT    GPIOB
#define IR_PHOTO_IN_PIN     GPIO_PIN_11

/* Status LEDs */
#define LED_GREEN_PORT      GPIOC
#define LED_GREEN_PIN       GPIO_PIN_6
#define LED_RED_PORT        GPIOC
#define LED_RED_PIN         GPIO_PIN_7

/* User Button */
#define USER_BTN_PORT       GPIOC
#define USER_BTN_PIN        GPIO_PIN_13

/* Battery ADC (PA0, ADC Channel 5) */
#define VBAT_ADC_CHANNEL   ADC_CHANNEL_5

/* Solar ADC (PA7, ADC Channel 7) */
#define VSOLAR_ADC_CHANNEL ADC_CHANNEL_7

/* ---- Peripheral Handles ---- */

extern I2C_HandleTypeDef hi2c1;
extern I2S_HandleTypeDef hi2s2;
extern UART_HandleTypeDef hlpuart1;
extern ADC_HandleTypeDef hadc;
extern RTC_HandleTypeDef hrtc;
extern SPI_HandleTypeDef hspi2;

/* ---- Function Prototypes ---- */

void SystemClock_Config(void);
void MX_GPIO_Init(void);
void MX_I2C1_Init(void);
void MX_I2S2_Init(void);
void MX_LPUART1_UART_Init(void);
void MX_SPI2_Init(void);
void MX_ADC_Init(void);
void MX_RTC_Init(void);

#endif /* MAIN_H */