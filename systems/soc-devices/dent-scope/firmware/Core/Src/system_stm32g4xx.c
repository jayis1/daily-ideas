# dent-scope / firmware/Core/Src/system_stm32g4xx.c
# Dent Scope — System init (vendor file placeholder)
# MIT License
#include "stm32g4xx_hal.h"

uint32_t SystemCoreClock = 16000000;

void SystemInit(void)
{
    /* FPU settings */
    SCB->CPACR |= ((3UL << 20) | (3UL << 22));
    __DSB();
    __ISB();
}