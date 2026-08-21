/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * system_stm32g474.c — System clock + SystemCoreClock + SCB/CPPWR setup
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"

uint32_t SystemCoreClock = SYSCLK_HZ;

void SystemInit(void)
{
    /* FPU + NVIC setup happens in startup.c and main.c clock_init().
     * This stub exists for HAL-style init calls. */
}

void SystemCoreClockUpdate(void)
{
    SystemCoreClock = SYSCLK_HZ;
}