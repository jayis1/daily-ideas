/*
 * startup_stm32g474xx.s — startup code + vector table for STM32G474RET6
 * ARM Cortex-M4F, 170 MHz, 512 KB flash, 128 KB SRAM
 */

    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb

    .section .isr_vector, "a", %progbits
    .align 2
    .global g_pfnVectors
g_pfnVectors:
    .word _estack                /* Initial stack pointer */
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
    /* External interrupts (subset) */
    .word 0                       /* WWDG */
    .word 0                       /* PVD */
    .word 0                       /* TAMPER */
    .word 0                       /* RTC */
    .word 0                       /* FLASH */
    .word 0                       /* RCC */
    .word 0                       /* EXTI0 */
    .word 0                       /* EXTI1 */
    .word 0                       /* EXTI2 */
    .word 0                       /* EXTI3 */
    .word 0                       /* EXTI4 */
    .word 0                       /* DMA1_CH1 */
    .word 0                       /* DMA1_CH2 */
    .word ADC1_2_IRQHandler       /* ADC1/ADC2 */
    .word 0                       /* USB_HP */
    .word 0                       /* USB_LP */
    .word 0                       /* FDCAN1_IT0 */
    .word 0                       /* FDCAN1_IT1 */
    .word 0                       /* EXTI9_5 */
    .word 0                       /* TIM1_BRK */
    .word 0                       /* TIM1_UP */
    .word 0                       /* TIM1_TRG_COM */
    .word 0                       /* TIM1_CC */
    .word 0                       /* TIM2 */
    .word 0                       /* TIM3 */
    .word 0                       /* TIM4 */
    .word 0                       /* I2C1_EV */
    .word 0                       /* I2C1_ER */
    .word 0                       /* I2C2_EV */
    .word 0                       /* I2C2_ER */
    .word 0                       /* SPI1 */
    .word 0                       /* SPI2 */
    .word 0                       /* USART1 */
    .word 0                       /* USART2 */
    .word 0                       /* USART3 */
    .word 0                       /* EXTI15_10 */
    .word 0                       /* RTC_ALARM */
    .word 0                       /* USB_FS_WAKEUP */
    .word 0                       /* TIM8_BRK */
    .word 0                       /* TIM8_UP */
    .word 0                       /* TIM8_TRG_COM */
    .word 0                       /* TIM8_CC */
    .word 0                       /* ADC3 */
    .word 0                       /* FMC */
    .word 0                       /* LPTIM1 */
    .word 0                       /* TIM5 */
    .word 0                       /* SPI3 */
    .word 0                       /* UART4 */
    .word 0                       /* UART5 */
    .word 0                       /* TIM6_DAC */
    .word 0                       /* TIM7 */
    .word 0                       /* DMA2_CH1 */
    .word 0                       /* DMA2_CH2 */
    .word 0                       /* DMA2_CH3 */
    .word 0                       /* DMA2_CH4 */
    .word 0                       /* DMA2_CH5 */
    .word 0                       /* ADC4 */
    .word 0                       /* ADC5 */
    .word 0                       /* UCPD1 */
    .word 0                       /* COMP1_2_3 */
    .word 0                       /* COMP4_5_6 */
    .word 0                       /* COMP7 */
    .word 0                       /* HRTIM1_MASTER */
    .word 0                       /* HRTIM1_TIMA */
    .word 0                       /* HRTIM1_TIMB */
    .word 0                       /* HRTIM1_TIMC */
    .word 0                       /* HRTIM1_TIMD */
    .word 0                       /* HRTIM1_TIME */
    .word 0                       /* HRTIM1_TIMF */
    .word 0                       /* CRS */
    .word 0                       /* SAI1 */
    .word 0                       /* TIM20_BRK */
    .word 0                       /* TIM20_UP */
    .word 0                       /* TIM20_TRG_COM */
    .word 0                       /* TIM20_CC */
    .word 0                       /* FPU */
    .word 0                       /* I2C4_EV */
    .word 0                       /* I2C4_ER */
    .word 0                       /* SPI4 */
    .word 0                       /* FDCAN2_IT0 */
    .word 0                       /* FDCAN2_IT1 */
    .word 0                       /* FDCAN3_IT0 */
    .word 0                       /* FDCAN3_IT1 */
    .word 0                       /* RNG */
    .word 0                       /* LPUART1 */
    .word 0                       /* I2C3_EV */
    .word 0                       /* I2C3_ER */
    .word 0                       /* DMAMUX1_OVR */
    .word 0                       /* QUADSPI */
    .word 0                       /* DMA1_CH8 */
    .word 0                       /* DMA1_CH9 */
    .word 0                       /* DMA1_CH10 */
    .word 0                       /* DMA1_CH11 */
    .word 0                       /* DMA1_CH12 */
    .word 0                       /* DMA1_CH13 */
    .word 0                       /* DMA1_CH14 */
    .word 0                       /* DMA1_CH15 */
    .word 0                       /* DMA2_CH6 */
    .word 0                       /* DMA2_CH7 */
    .word 0                       /* DMA2_CH8 */
    .word 0                       /* DMA2_CH9 */
    .word 0                       /* DMA2_CH10 */
    .word 0                       /* DMA2_CH11 */
    .word 0                       /* DMA2_CH12 */
    .word 0                       /* DMA2_CH13 */
    .word 0                       /* DMA2_CH14 */
    .word 0                       /* DMA2_CH15 */
    .word 0                       /* DMAMUX2_OVR */
    .word 0                       /* CORDIC */
    .word 0                       /* FMAC */
    .word 0                       /* LPTIM2 */
    .word 0                       /* LPTIM3 */
    .word 0                       /* LPTIM4 */
    .word 0                       /* LPTIM5 */
    .word 0                       /* LPUART2 */
    .word 0                       /* WWDG1 */
    .word 0                       /* AES1 */
    .word 0                       /* AES2 */

    .section .text.Reset_Handler, "ax", %progbits
    .global Reset_Handler
Reset_Handler:
    ldr r0, =_sdata
    ldr r1, =_etext
    ldr r2, =_edata
1:  cmp r0, r2
    bcc 2f
    b 3f
2:  ldr r3, [r1], #4
    str r3, [r0], #4
    b 1b
3:
    ldr r0, =_sbss
    ldr r1, =_ebss
    movs r2, #0
4:  cmp r0, r1
    bcc 5f
    b 6f
5:  str r2, [r0], #4
    b 4b
6:
    bl SystemInit
    bl main
    b .

    .weak NMI_Handler
    .weak HardFault_Handler
    .weak MemManage_Handler
    .weak BusFault_Handler
    .weak UsageFault_Handler
    .weak SVC_Handler
    .weak DebugMon_Handler
    .weak PendSV_Handler
    .weak SysTick_Handler
    .weak ADC1_2_IRQHandler

NMI_Handler:
HardFault_Handler:
MemManage_Handler:
BusFault_Handler:
UsageFault_Handler:
SVC_Handler:
DebugMon_Handler:
PendSV_Handler:
SysTick_Handler:
ADC1_2_IRQHandler:
    b .

    .section .text, "ax"
    .global SystemInit
SystemInit:
    bx lr