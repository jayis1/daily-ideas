/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * system_stm32wl55.c — System initialization (clock tree, NVIC)
 *                      Simplified — full version uses STM32Cube HAL.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include <stdint.h>

/* ---- System core clock frequency (global for HAL) ---- */
uint32_t SystemCoreClock = CPU_FREQ_HZ;

/* ---- RCC base address (STM32WL55) ---- */
#define RCC_BASE        0x58000000U
#define RCC_CR          (*(volatile uint32_t *)(RCC_BASE + 0x00))
#define RCC_CFGR        (*(volatile uint32_t *)(RCC_BASE + 0x08))
#define RCC_PLLCFGR     (*(volatile uint32_t *)(RCC_BASE + 0x0C))
#define RCC_CIER        (*(volatile uint32_t *)(RCC_BASE + 0x18))

/* ---- PWR base ---- */
#define PWR_BASE        0x58000400U
#define PWR_CR1         (*(volatile uint32_t *)(PWR_BASE + 0x00))
#define PWR_CR5         (*(volatile uint32_t *)(PWR_BASE + 0x14))

/* ---- Flash latency (ACR) ---- */
#define FLASH_BASE       0x58004000U
#define FLASH_ACR        (*(volatile uint32_t *)(FLASH_BASE + 0x00))

/* ---- Clock config bits ---- */
#define RCC_CR_HSION     (1U << 8)
#define RCC_CR_HSERDY    (1U << 17)
#define RCC_CR_PLLRDY    (1U << 25)

#define RCC_CFGR_SW_HSI   0
#define RCC_CFGR_SW_PLL   3
#define RCC_CFGR_SWS_MSK  (3U << 2)

#define PLLCFGR_PLLSRC_HSI  (1U << 0)
#define PLLCFGR_PLLN_24     (24U << 8)
#define PLLCFGR_PLLM_3      (2U << 4)   /* /3 */
#define PLLCFGR_PLLP_7      (6U << 27)  /* /7 → 48 MHz */
#define PLLCFGR_PLLR_7      (6U << 24)  /* /7 → 48 MHz */
#define PLLCFGR_PLLREN     (1U << 18)

/*
 * System init — configure PLL for 48 MHz from HSI 16 MHz.
 * HSI(16) / PLLM(3) × PLLN(24) / PLLP(7) = 16/3×24/7 ≈ 48 MHz
 * (simplified — STM32Cube HAL does the full sequence)
 */
void SystemInit(void)
{
    /* Enable HSI */
    RCC_CR |= RCC_CR_HSION;
    while (!(RCC_CR & (1U << 10)));  /* wait HSIRDY */

    /* Configure PLL: HSI source, M=3, N=24, P=7, R=7 */
    RCC_PLLCFGR = PLLCFGR_PLLSRC_HSI | PLLCFGR_PLLM_3 |
                  PLLCFGR_PLLN_24 | PLLCFGR_PLLR_7 |
                  PLLCFGR_PLLREN;

    /* Enable PLL */
    RCC_CR |= (1U << 24);  /* PLLON */
    while (!(RCC_CR & RCC_CR_PLLRDY));

    /* Set flash latency to 1 wait state for 48 MHz */
    FLASH_ACR = 0x00000001U;

    /* Switch system clock to PLL */
    RCC_CFGR = (RCC_CFGR & ~0x3U) | RCC_CFGR_SW_PLL;
    while ((RCC_CFGR & RCC_CFGR_SWS_MSK) != (RCC_CFGR_SW_PLL << 2));

    SystemCoreClock = CPU_FREQ_HZ;
}

/*
 * Get tick in milliseconds (simplified — uses SysTick)
 */
static volatile uint32_t tick_ms = 0;

void SysTick_Handler(void) __attribute__((interrupt("IRQ")));
void SysTick_Handler(void)
{
    tick_ms++;
}

uint32_t hal_get_tick_ms(void)
{
    return tick_ms;
}

/*
 * Delay in milliseconds (polling — used when SysTick not yet set up)
 */
void hal_delay_ms(uint32_t ms)
{
    /* SysTick: 48 MHz / 1000 = 48000 ticks per ms */
    volatile uint32_t *SYSTICK_LOAD = (volatile uint32_t *)0xE000E014U;
    volatile uint32_t *SYSTICK_VAL = (volatile uint32_t *)0xE000E018U;
    volatile uint32_t *SYSTICK_CTRL = (volatile uint32_t *)0xE000E010U;

    for (uint32_t i = 0; i < ms; i++) {
        *SYSTICK_LOAD = 48000 - 1;
        *SYSTICK_VAL = 0;
        *SYSTICK_CTRL = 1;  /* enable, no interrupt */
        while (!(*SYSTICK_CTRL & (1U << 16)));  /* COUNTFLAG */
    }
}