/*
 * stm32g491_conf.h — STM32G491RET6 register definitions and pin map
 * for Thermo Trace pocket DSC.
 */
#ifndef STM32G491_CONF_H
#define STM32G491_CONF_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* ---- Base addresses ---- */
#define PERIPH_BASE       0x40000000U
#define AHB1_BASE         (PERIPH_BASE + 0x08000U)
#define AHB2_BASE         (PERIPH_BASE + 0x18000U)
#define APB1_BASE         (PERIPH_BASE + 0x00000U)
#define APB2_BASE         (PERIPH_BASE + 0x10000U)

/* ---- RCC ---- */
#define RCC_BASE          (AHB1_BASE + 0x5800U)
#define RCC_CR            (*(volatile uint32_t *)(RCC_BASE + 0x00U))
#define RCC_CFGR          (*(volatile uint32_t *)(RCC_BASE + 0x08U))
#define RCC_PLLCFGR       (*(volatile uint32_t *)(RCC_BASE + 0x0CU))
#define RCC_AHB1ENR       (*(volatile uint32_t *)(RCC_BASE + 0x48U))
#define RCC_AHB2ENR       (*(volatile uint32_t *)(RCC_BASE + 0x4CU))
#define RCC_APB1ENR1      (*(volatile uint32_t *)(RCC_BASE + 0x58U))
#define RCC_APB1ENR2      (*(volatile uint32_t *)(RCC_BASE + 0x5CU))
#define RCC_APB2ENR       (*(volatile uint32_t *)(RCC_BASE + 0x60U))

/* ---- GPIO ---- */
#define GPIOA_BASE        (AHB2_BASE + 0x0000U)
#define GPIOB_BASE        (AHB2_BASE + 0x0400U)
#define GPIOC_BASE        (AHB2_BASE + 0x0800U)

#define GPIO_MODER(b)     (*(volatile uint32_t *)((b) + 0x00U))
#define GPIO_OTYPER(b)    (*(volatile uint16_t *)((b) + 0x04U))
#define GPIO_OSPEEDR(b)   (*(volatile uint32_t *)((b) + 0x08U))
#define GPIO_PUPDR(b)     (*(volatile uint32_t *)((b) + 0x0CU))
#define GPIO_IDR(b)       (*(volatile uint16_t *)((b) + 0x10U))
#define GPIO_ODR(b)       (*(volatile uint16_t *)((b) + 0x14U))
#define GPIO_BSRR(b)      (*(volatile uint32_t *)((b) + 0x18U))
#define GPIO_AFRL(b)      (*(volatile uint32_t *)((b) + 0x20U))
#define GPIO_AFRH(b)      (*(volatile uint32_t *)((b) + 0x24U))

/* GPIO pin helpers */
#define GPIO_MODE_INPUT    0x00U
#define GPIO_MODE_OUTPUT   0x01U
#define GPIO_MODE_AF       0x02U
#define GPIO_MODE_ANALOG   0x03U

#define GPIO_SET(b, n)     GPIO_BSRR(b) = (1U << (n))
#define GPIO_CLR(b, n)     GPIO_BSRR(b) = (1U << ((n) + 16))

/* ---- USART2 (BLE bridge) ---- */
#define USART2_BASE       (APB1_BASE + 0x4400U)
#define USART2_CR1        (*(volatile uint32_t *)(USART2_BASE + 0x00U))
#define USART2_CR2        (*(volatile uint32_t *)(USART2_BASE + 0x04U))
#define USART2_BRR        (*(volatile uint32_t *)(USART2_BASE + 0x0CU))
#define USART2_ISR        (*(volatile uint32_t *)(USART2_BASE + 0x1CU))
#define USART2_TDR        (*(volatile uint32_t *)(USART2_BASE + 0x28U))
#define USART2_RDR        (*(volatile uint32_t *)(USART2_BASE + 0x24U))

/* ---- SPI1 (ADS122U04) ---- */
#define SPI1_BASE         (APB2_BASE + 0x3000U)
#define SPI1_CR1          (*(volatile uint32_t *)(SPI1_BASE + 0x00U))
#define SPI1_CR2          (*(volatile uint32_t *)(SPI1_BASE + 0x04U))
#define SPI1_SR           (*(volatile uint32_t *)(SPI1_BASE + 0x08U))
#define SPI1_DR           (*(volatile uint32_t *)(SPI1_BASE + 0x0CU))

/* ---- SPI2 (microSD) ---- */
#define SPI2_BASE         (APB1_BASE + 0x3800U)
#define SPI2_CR1          (*(volatile uint32_t *)(SPI2_BASE + 0x00U))
#define SPI2_CR2          (*(volatile uint32_t *)(SPI2_BASE + 0x04U))
#define SPI2_SR           (*(volatile uint32_t *)(SPI2_BASE + 0x08U))
#define SPI2_DR           (*(volatile uint32_t *)(SPI2_BASE + 0x0CU))

/* ---- I2C1 (OLED) ---- */
#define I2C1_BASE         (APB1_BASE + 0x5400U)
#define I2C1_CR1          (*(volatile uint32_t *)(I2C1_BASE + 0x00U))
#define I2C1_CR2          (*(volatile uint32_t *)(I2C1_BASE + 0x04U))
#define I2C1_TIMINGR      (*(volatile uint32_t *)(I2C1_BASE + 0x10U))
#define I2C1_ISR          (*(volatile uint32_t *)(I2C1_BASE + 0x18U))
#define I2C1_TXDR         (*(volatile uint32_t *)(I2C1_BASE + 0x28U))
#define I2C1_RXDR         (*(volatile uint32_t *)(I2C1_BASE + 0x24U))

/* ---- TIM1 (heater PWM channel 1+2) ---- */
#define TIM1_BASE         (APB2_BASE + 0x2C00U)
#define TIM1_CR1          (*(volatile uint32_t *)(TIM1_BASE + 0x00U))
#define TIM1_CR2          (*(volatile uint32_t *)(TIM1_BASE + 0x04U))
#define TIM1_SMFR         (*(volatile uint32_t *)(TIM1_BASE + 0x08U))
#define TIM1_DIER         (*(volatile uint32_t *)(TIM1_BASE + 0x0CU))
#define TIM1_SR           (*(volatile uint32_t *)(TIM1_BASE + 0x10U))
#define TIM1_CCMR1        (*(volatile uint32_t *)(TIM1_BASE + 0x18U))
#define TIM1_CCMR2        (*(volatile uint32_t *)(TIM1_BASE + 0x1CU))
#define TIM1_CCER         (*(volatile uint32_t *)(TIM1_BASE + 0x20U))
#define TIM1_CNT          (*(volatile uint32_t *)(TIM1_BASE + 0x24U))
#define TIM1_PSC          (*(volatile uint32_t *)(TIM1_BASE + 0x28U))
#define TIM1_ARR          (*(volatile uint32_t *)(TIM1_BASE + 0x2CU))
#define TIM1_CCR1         (*(volatile uint32_t *)(TIM1_BASE + 0x34U))
#define TIM1_CCR2         (*(volatile uint32_t *)(TIM1_BASE + 0x38U))
#define TIM1_BDTR         (*(volatile uint32_t *)(TIM1_BASE + 0x44U))

/* ---- IWDG (independent watchdog) ---- */
#define IWDG_BASE         (APB1_BASE + 0x3000U)
#define IWDG_KR           (*(volatile uint32_t *)(IWDG_BASE + 0x00U))
#define IWDG_PR           (*(volatile uint32_t *)(IWDG_BASE + 0x04U))
#define IWDG_RLR          (*(volatile uint32_t *)(IWDG_BASE + 0x08U))
#define IWDG_SR           (*(volatile uint32_t *)(IWDG_BASE + 0x0CU))

/* ---- NVIC ---- */
#define NVIC_BASE         (0xE000E100U)
#define NVIC_ISER0        (*(volatile uint32_t *)(NVIC_BASE + 0x000U))
#define NVIC_ICER0        (*(volatile uint32_t *)(NVIC_BASE + 0x080U))
#define NVIC_IPR(n)       (*(volatile uint8_t *)(NVIC_BASE + 0x300U + (n)))

/* ---- SysTick ---- */
#define SYSTICK_BASE      0xE000E010U
#define SYSTICK_CSR       (*(volatile uint32_t *)(SYSTICK_BASE + 0x00U))
#define SYSTICK_RVR       (*(volatile uint32_t *)(SYSTICK_BASE + 0x04U))
#define SYSTICK_CVR       (*(volatile uint32_t *)(SYSTICK_BASE + 0x08U))

/* ---- EXTI (safety comparator) ---- */
#define EXTI_BASE         (APB2_BASE + 0x3C00U)
#define EXTI_IMR1         (*(volatile uint32_t *)(EXTI_BASE + 0x00U))
#define EXTI_RTSR1        (*(volatile uint32_t *)(EXTI_BASE + 0x08U))
#define EXTI_FTSR1        (*(volatile uint32_t *)(EXTI_BASE + 0x0CU))
#define EXTI_PR1          (*(volatile uint32_t *)(EXTI_BASE + 0x14U))

/* ---- System clock: 170 MHz from HSI16 + PLL ---- */
#define SYS_CLK_HZ        170000000U
#define APB1_CLK_HZ       (SYS_CLK_HZ / 1U)   /* no prescaler */
#define APB2_CLK_HZ       (SYS_CLK_HZ / 1U)

/* ---- Pin assignments ---- */
/* ADS122U04 SPI1 */
#define ADS_CS_PORT       GPIOA_BASE
#define ADS_CS_PIN        10
#define ADS_START_PORT    GPIOA_BASE
#define ADS_START_PIN     11
#define ADS_DRDY_PORT     GPIOA_BASE
#define ADS_DRDY_PIN      12

/* Heaters PWM */
#define HEATER1_PWM_PIN   8   /* PA8, TIM1_CH1 */
#define HEATER2_PWM_PIN   9   /* PA9, TIM1_CH2 */
#define HEATER_EN_PORT    GPIOB_BASE
#define HEATER_EN_PIN     9   /* PB9, active LOW = cutoff */

/* Safety comparator */
#define SAFETY_CMP_PORT   GPIOB_BASE
#define SAFETY_CMP_PIN    8   /* PB8, EXTI8 */

/* OLED */
#define OLED_DC_PORT      GPIOB_BASE
#define OLED_DC_PIN       0
#define OLED_RST_PORT     GPIOB_BASE
#define OLED_RST_PIN      1

/* microSD */
#define SD_CS_PORT        GPIOB_BASE
#define SD_CS_PIN         5

/* Buttons */
#define BTN_A_PORT        GPIOB_BASE
#define BTN_A_PIN         10
#define BTN_B_PORT        GPIOB_BASE
#define BTN_B_PIN         11
#define BTN_C_PORT        GPIOB_BASE
#define BTN_C_PIN         12

/* LEDs */
#define LED_RED_PORT      GPIOB_BASE
#define LED_RED_PIN       13
#define LED_GREEN_PORT    GPIOB_BASE
#define LED_GREEN_PIN     14

/* ESP32-C3 power control */
#define ESP_EN_PORT       GPIOB_BASE
#define ESP_EN_PIN        15

/* DS18B20 */
#define DS18B20_PORT      GPIOC_BASE
#define DS18B20_PIN       1

/* Battery voltage ADC */
#define BATT_ADC_PORT     GPIOC_BASE
#define BATT_ADC_PIN      0

/* Heater parameters */
#define HEATER_R_OHM      50.0f        /* heater resistance */
#define HEATER_MAX_DUTY   0.85f        /* max PWM duty (safety) */
#define PWM_FREQ_HZ       10000U       /* 10 kHz */
#define PWM_PERIOD        (SYS_CLK_HZ / PWM_FREQ_HZ)  /* ticks */

/* Temperature limits */
#define TEMP_MAX_C        300.0f
#define TEMP_SAFETY_C     320.0f
#define TEMP_COOLDOWN_C   50.0f
#define TEMP_AMBIENT_C    25.0f

/* ADS122U04 */
#define ADS_CHANNELS      4
#define ADS_SAMPLE_HZ     100

/* DSC parameters */
#define DSC_RAMP_DEFAULT  5.0f         /* °C/min */
#define DSC_MAX_TEMP      300.0f
#define DSC_SAMPLE_RATE   100          /* Hz */

#endif /* STM32G491_CONF_H */