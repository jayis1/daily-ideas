/* system_stm32l4xx.c — system init stub (data/BSS already in startup).
 * Provided as a weak implementation that the startup can override.
 */
#include "stm32l4xx_hal.h"

void SystemInit(void)
{
    /* The HAL_Init() in main.c configures the clock tree; nothing
     * extra needed here. */
}

volatile uint32_t SystemCoreClock = 80000000UL;