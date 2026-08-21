/*
 * stm32g491_conf.h — minimal HAL configuration for Phase Lock
 * Selects the STM32G491RET6, enables HSI PLL for 170 MHz, HRTIM, CORDIC,
 * FMAC, ADC, DAC, I2C, SPI, USART, DMA, CRC, and the GPIO clocks.
 */
#ifndef STM32G491_CONF_H
#define STM32G491_CONF_H

#include "stm32g4xx.h"

/* HSI 16 MHz → PLL → 170 MHz SYSCLK (VOS Range 0) */
#define PLLM_VALUE   4
#define PLLN_VALUE   85
#define PLLP_VALUE   7
#define PLLQ_VALUE   8
#define PLLR_VALUE   2
#define HSI_VALUE    16000000UL
#define SYSCLK_FREQ  170000000UL
#define APB1_FREQ    170000000UL
#define APB2_FREQ    170000000UL

/* HRTIM clock = 170 MHz × 32 (HSI ratio) = 5.44 GHz tick (τ ≈ 184 ps) */
#define HRTIM_FREQ_HZ 5440000000ULL

/* ADC clock = 170 MHz / 2 = 85 MHz; 16-bit oversampled @ 28 ksps */
#define ADC_FREQ_HZ   85000000UL
#define ADC_OVS_RATIO 256
#define ADC_SPS        28000UL

/* Reference oscillator DDS */
#define DAC_RATE_HZ   1000000UL
#define DAC_AMPLITUDE 2047  /* 12-bit signed */

/* I2C for OLED + ADS1115 */
#define I2C1_FREQ_HZ  400000UL

/* USART1 to ESP32-C3 BLE bridge */
#define USART1_BAUD   921600UL

/* SPI1 for microSD */
#define SPI1_FREQ_HZ  25000000UL

/* SysTick 1 kHz */
#define SYSTICK_HZ    1000UL

/* CORDIC cosine/sine: q1.31 scale */
#define CORDIC_Q31_SCALE  2147483648.0

#endif /* STM32G491_CONF_H */