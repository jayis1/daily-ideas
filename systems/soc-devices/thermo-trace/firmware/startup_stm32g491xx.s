/*
 * startup_stm32g491xx.s — Cortex-M4 startup code for STM32G491
 * Minimal: copies .data, zeros .bss, calls main, loops on exit.
 */
    .syntax unified
    .cpu cortex-m4
    .thumb

.section .isr_vector, "a", %progbits
    .word _estack
    .word Reset_Handler
    .word NMI_Handler
    .word HardFault_Handler
    .word MemManage_Handler
    .word BusFault_Handler
    .word UsageFault_Handler
    .word 0
    .word 0
    .word 0
    .word 0
    .word SVC_Handler
    .word DebugMon_Handler
    .word 0
    .word PendSV_Handler
    .word SysTick_Handler

    /* External interrupts (simplified — only ones we use) */
    .word 0  /* WWDG */
    .word 0  /* PVD */
    .word 0  /* TAMPER */
    .word 0  /* RTC */
    .word 0  /* FLASH */
    .word 0  /* RCC */
    .word 0  /* EXTI0 */
    .word 0  /* EXTI1 */
    .word 0  /* EXTI2 */
    .word 0  /* EXTI3 */
    .word 0  /* EXTI4 */
    .word 0  /* DMA1_CH1 */
    .word 0  /* DMA1_CH2 */
    .word 0  /* DMA1_CH3 */
    .word 0  /* DMA1_CH4 */
    .word 0  /* DMA1_CH5 */
    .word 0  /* DMA1_CH6 */
    .word 0  /* DMA1_CH7 */
    .word 0  /* ADC1_2 */
    .word 0  /* USB */
    .word 0  /* CAN1 */
    .word 0  /* CAN2 */
    .word 0  /* EXTI9_5 */  /* slot 23 — safety comparator on PB8 */
    .word 0  /* TIM1_BRK */
    .word 0  /* TIM1_UP */
    .word 0  /* TIM1_TRG_COM */
    .word TIM1_CC_IRQHandler  /* TIM1_CC */
    .word 0  /* TIM2 */
    .word 0  /* TIM3 */
    .word 0  /* TIM4 */
    .word 0  /* I2C1_EV */
    .word 0  /* I2C1_ER */
    .word 0  /* I2C2_EV */
    .word 0  /* I2C2_ER */
    .word 0  /* SPI1 */
    .word 0  /* SPI2 */
    .word 0  /* USART1 */
    .word 0  /* USART2 */
    .word 0  /* USART3 */
    .word 0  /* EXTI15_10 */
    .word 0  /* RTC_ALARM */
    .word 0  /* USB wakeup */
    .word 0  /* TIM8_BRK */
    .word 0  /* TIM8_UP */
    .word 0  /* TIM8_TRG_COM */
    .word 0  /* TIM8_CC */
    .word 0  /* ADC3 */
    .word 0  /* FMC */
    .word 0  /* LPTIM1 */
    .word 0  /* TIM5 */
    .word 0  /* SPI3 */
    .word 0  /* UART4 */
    .word 0  /* UART5 */
    .word 0  /* TIM6 */
    .word 0  /* TIM7 */
    .word 0  /* DMA2_CH1 */
    .word 0  /* DMA2_CH2 */
    .word 0  /* DMA2_CH3 */
    .word 0  /* DMA2_CH4 */
    .word 0  /* DMA2_CH5 */
    .word 0  /* UCPD1 */
    .word 0  /* COMP1_2_3 */
    .word 0  /* COMP4 */
    .word 0  /* CRS */
    .word 0  /* SAI1 */
    .word 0  /* TIM20_BRK */
    .word 0  /* TIM20_UP */
    .word 0  /* TIM20_TRG_COM */
    .word 0  /* TIM20_CC */
    .word 0  /* FPU */
    .word 0  /* I2C4_EV */
    .word 0  /* I2C4_ER */
    .word 0  /* SPI4 */
    .word 0  /* LPUART1 */
    .word 0  /* AWD1/2/3 */

.section .text
.thumb_func
.global Reset_Handler
Reset_Handler:
    ldr r0, =_sdata
    ldr r1, =_edata
    ldr r2, =_etext
1:
    cmp r0, r1
    bcs 2f
    ldr r3, [r2], #4
    str r3, [r0], #4
    b 1b
2:
    ldr r0, =_sbss
    ldr r1, =_ebss
    movs r2, #0
3:
    cmp r0, r1
    bcs 4f
    str r2, [r0], #4
    b 3b
4:
    bl SystemInit
    bl main
5:
    b 5b

.thumb_func
.weak NMI_Handler
NMI_Handler:
    b .

.thumb_func
.weak HardFault_Handler
HardFault_Handler:
    b .

.thumb_func
.weak MemManage_Handler
MemManage_Handler:
    b .

.thumb_func
.weak BusFault_Handler
BusFault_Handler:
    b .

.thumb_func
.weak UsageFault_Handler
UsageFault_Handler:
    b .

.thumb_func
.weak SVC_Handler
SVC_Handler:
    bx lr

.thumb_func
.weak DebugMon_Handler
DebugMon_Handler:
    bx lr

.thumb_func
.weak PendSV_Handler
PendSV_Handler:
    bx lr

.thumb_func
.weak SysTick_Handler
SysTick_Handler:
    bx lr

.thumb_func
.weak TIM1_CC_IRQHandler
TIM1_CC_IRQHandler:
    bx lr

.weak SystemInit
.thumb_func
SystemInit:
    bx lr