/**
  * Soil Whisper — STM32WL55xx Startup Code
  * Vector table and startup routine
  */

  .syntax unified
  .cpu cortex-m4
  .fpu fpv4-sp-d16
  .thumb

.global  Reset_Handler
.global  SystemInit

/* Vector table */
.section  .isr_vector, "a", %progbits
.type  g_pfnVectors, %object
g_pfnVectors:
  .word  _estack
  .word  Reset_Handler
  .word  NMI_Handler
  .word  HardFault_Handler
  .word  MemManage_Handler
  .word  BusFault_Handler
  .word  UsageFault_Handler
  .word  0
  .word  0
  .word  0
  .word  0
  .word  SVC_Handler
  .word  DebugMon_Handler
  .word  0
  .word  PendSV_Handler
  .word  SysTick_Handler

/* External interrupts (STM32WL55xx specific) */
  .word  WWDG_IRQHandler
  .word  PVD_PVM_IRQHandler
  .word  TAMP_STAMP_LSECSS_SSRU_IRQHandler
  .word  RTC_WKUP_IRQHandler
  .word  FLASH_IRQHandler
  .word  RCC_IRQHandler
  .word  EXTI0_IRQHandler
  .word  EXTI1_IRQHandler
  .word  EXTI2_IRQHandler
  .word  EXTI3_IRQHandler
  .word  EXTI4_IRQHandler
  .word  DMA1_Channel1_IRQHandler
  .word  DMA1_Channel2_IRQHandler
  .word  DMA1_Channel3_IRQHandler
  .word  DMA1_Channel4_IRQHandler
  .word  DMA1_Channel5_IRQHandler
  .word  DMA1_Channel6_IRQHandler
  .word  DMA1_Channel7_IRQHandler
  .word  ADC_IRQHandler
  .word  DAC_IRQHandler
  .word  C2SEV_PWR_IRQHandler
  .word  COMP_IRQHandler
  .word  EXTI9_5_IRQHandler
  .word  TIM1_BRK_IRQHandler
  .word  TIM1_UP_IRQHandler
  .word  TIM1_TRG_COM_IRQHandler
  .word  TIM1_CC_IRQHandler
  .word  TIM2_IRQHandler
  .word  TIM16_IRQHandler
  .word  TIM17_IRQHandler
  .word  I2C1_EV_IRQHandler
  .word  I2C1_ER_IRQHandler
  .word  I2C2_EV_IRQHandler
  .word  I2C2_ER_IRQHandler
  .word  SPI1_IRQHandler
  .word  SPI2_IRQHandler
  .word  USART1_IRQHandler
  .word  USART2_IRQHandler
  .word  LPUART1_IRQHandler
  .word  EXTI15_10_IRQHandler
  .word  RTC_Alarm_IRQHandler
  .word  SUBGHZ_Radio_IRQHandler
  .word  0
  .word  0
  .word  0
  .word  TIM3_IRQHandler
  .word  0
  .word  0
  .word  0
  .word  0
  .word  0

.size  g_pfnVectors, . - g_pfnVectors

/* Reset handler */
.section  .text.Reset_Handler
.weak  Reset_Handler
.type  Reset_Handler, %function
Reset_Handler:
  ldr   r0, =_estack
  mov   sp, r0

  /* Copy .data from Flash to RAM */
  ldr   r0, =_sdata
  ldr   r1, =_edata
  ldr   r2, =_sidata
copy_data:
  cmp   r0, r1
  ittt  lo
  ldrlo r3, [r2], #4
  strlo r3, [r0], #4
  blo   copy_data

  /* Zero .bss */
  ldr   r0, =_sbss
  ldr   r1, =_ebss
  mov   r2, #0
zero_bss:
  cmp   r0, r1
  ittt  lo
  strlo r2, [r0], #4
  blo   zero_bss

  /* Call SystemInit then main */
  bl    SystemInit
  bl    main

  /* If main returns, loop forever */
  b     .

/* Default interrupt handlers */
.weak NMI_Handler
.thumb_set NMI_Handler, Infinite_Loop

.weak HardFault_Handler
.thumb_set HardFault_Handler, Infinite_Loop

.weak MemManage_Handler
.thumb_set MemManage_Handler, Infinite_Loop

.weak BusFault_Handler
.thumb_set BusFault_Handler, Infinite_Loop

.weak UsageFault_Handler
.thumb_set UsageFault_Handler, Infinite_Loop

.weak SVC_Handler
.thumb_set SVC_Handler, Infinite_Loop

.weak DebugMon_Handler
.thumb_set DebugMon_Handler, Infinite_Loop

.weak PendSV_Handler
.thumb_set PendSV_Handler, Infinite_Loop

.section  .text.Infinite_Loop
Infinite_Loop:
  b     .

/* TIM3 IRQ handler — used for moisture frequency capture */
.weak TIM3_IRQHandler
.thumb_set TIM3_IRQHandler, Infinite_Loop

/* USART2 IRQ handler */
.weak USART2_IRQHandler
.thumb_set USART2_IRQHandler, Infinite_Loop