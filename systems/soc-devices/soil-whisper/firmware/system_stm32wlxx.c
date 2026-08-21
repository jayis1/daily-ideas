/**
  ******************************************************************************
  * Soil Whisper — System Clock Configuration
  * STM32WL55xx System Init
  ******************************************************************************
  */

#include "stm32wlxx.h"

/**
  * @brief  System Clock Configuration
  *         MSI 4 MHz default, configurable to PLL 48 MHz
  * @param  None
  * @retval None
  */
void SystemInit(void)
{
  /* Enable power clock */
  RCC->APB1ENR1 |= RCC_APB1ENR1_PWREN;

  /* Set voltage range 1 for 48 MHz operation */
  PWR->CR1 = (PWR->CR1 & ~PWR_CR1_VOS) | PWR_CR1_VOS_0;

  /* Wait for voltage regulator to be ready */
  while ((PWR->SR2 & PWR_SR2_VOSF) != 0);

  /* Configure Flash: 3 wait states for 48 MHz */
  FLASH->ACR = FLASH_ACR_LATENCY_3WS;

  /* Enable MSI (4 MHz) as system clock source */
  RCC->CR |= RCC_CR_MSION;
  while ((RCC->CR & RCC_CR_MSIRDY) == 0);

  /* Configure MSI range to 4 MHz */
  RCC->CR = (RCC->CR & ~RCC_CR_MSIRANGE) | RCC_CR_MSIRANGE_6;

  /* MSI as system clock */
  RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_MSI;
  while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_MSI);

  /* Disable PLL to reconfigure */
  RCC->CR &= ~RCC_CR_PLLON;
  while ((RCC->CR & RCC_CR_PLLRDY) != 0);

  /* Configure PLL: MSI 4 MHz → 48 MHz
   * PLLM = 1, PLLN = 12, PLLR = 1
   * 4 MHz / 1 * 12 / 1 = 48 MHz
   */
  RCC->PLLCFGR = RCC_PLLCFGR_PLLSRC_MSI
                | (1 << RCC_PLLCFGR_PLLM_Pos)   /* PLLM = 1 */
                | (12 << RCC_PLLCFGR_PLLN_Pos)    /* PLLN = 12 */
                | (0 << RCC_PLLCFGR_PLLR_Pos)     /* PLLR = 1 (encoded as 0) */
                | RCC_PLLCFGR_PLLREN;              /* Enable PLLR */

  /* Enable PLL */
  RCC->CR |= RCC_CR_PLLON;
  while ((RCC->CR & RCC_CR_PLLRDY) == 0);

  /* Switch system clock to PLL */
  RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
  while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL);

  /* System clock is now 48 MHz */
  SystemCoreClock = 48000000;
}

uint32_t SystemCoreClock = 48000000;