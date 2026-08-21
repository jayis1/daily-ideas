/*
 * main.h — QCM Halo main header
 */

#ifndef MAIN_H
#define MAIN_H

#include "stm32g4xx_hal.h"
#include "config.h"

/* ── Pin assignments (mapped to STM32G474RET6 LQFP-64) ──── */

/* ADC */
#define ADC_RINGDOWN_PIN    GPIO_PIN_0
#define ADC_RINGDOWN_PORT   GPIOA
#define ADC_DISSIP_PIN      GPIO_PIN_1
#define ADC_DISSIP_PORT     GPIOA
#define ADC_VBAT_PIN        GPIO_PIN_0
#define ADC_VBAT_PORT       GPIOB
#define ADC_TEC_ISENSE_PIN  GPIO_PIN_0
#define ADC_TEC_ISENSE_PORT GPIOC

/* USART2 → ESP32-C3 */
#define UART_TX_PIN     GPIO_PIN_2
#define UART_TX_PORT    GPIOA
#define UART_RX_PIN     GPIO_PIN_3
#define UART_RX_PORT    GPIOA

/* SPI1 → W25Q128 */
#define SPI_SCK_PIN     GPIO_PIN_5
#define SPI_SCK_PORT    GPIOA
#define SPI_MISO_PIN    GPIO_PIN_6
#define SPI_MISO_PORT   GPIOA
#define SPI_MOSI_PIN    GPIO_PIN_7
#define SPI_MOSI_PORT   GPIOA
#define FLASH_CS_PIN    GPIO_PIN_4
#define FLASH_CS_PORT   GPIOA

/* TIM1 — TX/RX gate */
#define TX_GATE_PIN     GPIO_PIN_8
#define TX_GATE_PORT    GPIOA
#define RX_GATE_PIN     GPIO_PIN_9
#define RX_GATE_PORT    GPIOA

/* GPIO control */
#define TXRX_SW_PIN     GPIO_PIN_10
#define TXRX_SW_PORT    GPIOA
#define CH1_SEL_PIN     GPIO_PIN_11
#define CH1_SEL_PORT    GPIOA
#define CH2_SEL_PIN     GPIO_PIN_12
#define CH2_SEL_PORT    GPIOA

/* TIM2_CH1 — reciprocal counting */
#define FREQ_COUNT_PIN  GPIO_PIN_15
#define FREQ_COUNT_PORT GPIOA

/* I2C1 */
#define I2C_SCL_PIN     GPIO_PIN_6
#define I2C_SCL_PORT    GPIOB
#define I2C_SDA_PIN     GPIO_PIN_7
#define I2C_SDA_PORT    GPIOB

/* TIM4_CH3 — Peltier PWM */
#define TEC_PWM_PIN     GPIO_PIN_8
#define TEC_PWM_PORT    GPIOB
#define TEC_EN_PIN      GPIO_PIN_9
#define TEC_EN_PORT     GPIOB

/* TIM2_CH3 — Pump PWM */
#define PUMP_PWM_PIN    GPIO_PIN_10
#define PUMP_PWM_PORT   GPIOB

/* Status LED */
#define LED_R_PIN       GPIO_PIN_11
#define LED_R_PORT      GPIOB
#define LED_G_PIN       GPIO_PIN_12
#define LED_G_PORT      GPIOB
#define LED_B_PIN       GPIO_PIN_13
#define LED_B_PORT      GPIOB

/* Buttons */
#define BTN_A_PIN       GPIO_PIN_14
#define BTN_A_PORT      GPIOB
#define BTN_B_PIN       GPIO_PIN_15
#define BTN_B_PORT      GPIOB

/* SD card SPI3 */
#define SD_CS_PIN       GPIO_PIN_10
#define SD_CS_PORT      GPIOC
#define SD_SCK_PIN      GPIO_PIN_10
#define SD_SCK_PORT     GPIOB
#define SD_MISO_PIN     GPIO_PIN_11
#define SD_MISO_PORT    GPIOC
#define SD_MOSI_PIN     GPIO_PIN_12
#define SD_MOSI_PORT    GPIOC
#define SD_DETECT_PIN   GPIO_PIN_4
#define SD_DETECT_PORT  GPIOC

/* 1-Wire (DS18B20) */
#define ONEWIRE_PIN     GPIO_PIN_13
#define ONEWIRE_PORT    GPIOC

/* Ring-down trigger */
#define RINGDOWN_TRIG_PIN   GPIO_PIN_2
#define RINGDOWN_TRIG_PORT  GPIOD

/* Valve control */
#define VALVE_A_PIN     GPIO_PIN_2
#define VALVE_A_PORT    GPIOB
#define VALVE_B_PIN     GPIO_PIN_4
#define VALVE_B_PORT    GPIOB
#define VALVE_C_PIN     GPIO_PIN_5
#define VALVE_C_PORT    GPIOB

/* Reed interlock */
#define REED_PIN        GPIO_PIN_3
#define REED_PORT       GPIOC

/* ── Function prototypes ─────────────────────────────────── */
void Error_Handler(void);

#endif /* MAIN_H */