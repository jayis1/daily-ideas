/*
 * stm32g474_conf.h — STM32G474RET6 peripheral configuration for Iono Pin
 */
#ifndef STM32G474_CONF_H
#define STM32G474_CONF_H

#include "stm32g4xx.h"

/* HSI 16 MHz -> PLL -> 170 MHz (default STM32G4 clock tree) */
#define SYSCLK_HZ       170000000UL
#define HCLK_HZ         170000000UL
#define PCLK1_HZ        (HCLK_HZ / 1)
#define PCLK2_HZ        (HCLK_HZ / 1)
#define APB1TIM_HZ      PCLK1_HZ
#define APB2TIM_HZ      PCLK2_HZ

/* ADC1 — 40 ksps for drift-time capture (TIA output via PA0/ADC1_IN1) */
#define IMS_ADC             ADC1
#define IMS_ADC_CHANNEL     ADC_CHANNEL_1
#define IMS_SAMPLE_RATE     40000UL
#define IMS_SAMPLES_PER_SWEEP 140   /* 0.5-3.5 ms @ 40 ksps = 140 samples */
#define IMS_AVG_COUNT       256     /* rolling-average spectra */
#define IMS_DRIFT_LEN_MM    85.0f   /* drift length 8.5 cm */
#define IMS_DRIFT_VOLTAGE   2125.0f /* drift voltage V */

/* TIM1_CH1 triggers ADC1 at IMS_SAMPLE_RATE */
#define IMS_TRIM_TIM        TIM1

/* TIM6 — shutter repetition rate (20-40 Hz) */
#define SHUTTER_TIM         TIM6
#define IMS_REP_RATE_HZ     25UL

/* Shutter pulse width */
#define SHUTTER_PULSE_US    200UL

/* HV */
#define HV_DRIFT_TARGET_V   2125.0f
#define HV_SUPPLY_MAX_V     5000.0f

/* Shutter bias rails */
#define SHUTTER_BIAS_V      90.0f

/* SPI2 — ADS122U04 */
#define AUX_ADC_SPI         SPI2
#define AUX_ADC_CS_PORT     GPIOB
#define AUX_ADC_CS_PIN      GPIO_PIN_12

/* SPI3 — OLED + SD + W25Q128 */
#define PERIPH_SPI          SPI3

/* I2C1 — BME280 */
#define AUX_I2C             I2C1

/* UART2 — ESP32-C3 bridge */
#define BRIDGE_UART         USART2
#define BRIDGE_BAUD         921600UL

/* SD */
#define SD_CS_PORT          GPIOD
#define SD_CS_PIN           GPIO_PIN_2

/* OLED SH1106 */
#define OLED_I2C_ADDR       0x3C

#endif /* STM32G474_CONF_H */