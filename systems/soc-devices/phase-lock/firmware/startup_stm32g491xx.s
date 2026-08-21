/*
 * startup_stm32g491xx.s — minimal startup + vector table for STM32G491RET6.
 * Copies .data, zeroes .bss, calls SystemInit then main. Default handlers
 * are weak so the user can override in C.
 */

    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb

    .global _estack
    .global Reset_Handler

    .section .isr_vector, "a", %progbits
    .align 2
    .type g_pfnVectors, %object
g_pfnVectors:
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

    /* STM32G491 external interrupts (subset; 99 IRQs total) */
    .word WWDG_IRQHandler            /* 0  */
    .word PVD_PVM_IRQHandler         /* 1  */
    .word RTC_TAMP_LSECSS_IRQHandler /* 2  */
    .word RTC_WKUP_IRQHandler         /* 3  */
    .word FLASH_IRQHandler            /* 4  */
    .word RCC_IRQHandler              /* 5  */
    .word EXTI0_IRQHandler            /* 6  */
    .word EXTI1_IRQHandler            /* 7  */
    .word EXTI2_IRQHandler            /* 8  */
    .word EXTI3_IRQHandler            /* 9  */
    .word EXTI4_IRQHandler            /* 10 */
    .word DMA1_Channel1_IRQHandler   /* 11 — ADC1 DMA */
    .word DMA1_Channel2_IRQHandler   /* 12 */
    .word DMA1_Channel3_IRQHandler   /* 13 */
    .word DMA1_Channel4_IRQHandler   /* 14 */
    .word DMA1_Channel5_IRQHandler   /* 15 */
    .word DMA1_Channel6_IRQHandler   /* 16 */
    .word DMA1_Channel7_IRQHandler   /* 17 */
    .word ADC1_2_IRQHandler           /* 18 */
    .word USB_HP_IRQHandler           /* 19 */
    .word USB_LP_IRQHandler           /* 20 */
    .word FDCAN1_IT0_IRQHandler       /* 21 */
    .word FDCAN1_IT1_IRQHandler       /* 22 */
    .word EXTI9_5_IRQHandler          /* 23 — encoder/buttons */
    .word TIM1_BRK_TIM15_IRQHandler    /* 24 */
    .word TIM1_UP_TIM16_IRQHandler     /* 25 */
    .word TIM1_TRG_COM_TIM17_IRQHandler /* 26 */
    .word TIM1_CC_IRQHandler           /* 27 */
    .word TIM2_IRQHandler              /* 28 */
    .word TIM3_IRQHandler              /* 29 */
    .word TIM4_IRQHandler              /* 30 */
    .word I2C1_EV_IRQHandler           /* 31 */
    .word I2C1_ER_IRQHandler           /* 32 */
    .word I2C2_EV_IRQHandler           /* 33 */
    .word I2C2_ER_IRQHandler           /* 34 */
    .word SPI1_IRQHandler              /* 35 */
    .word SPI2_IRQHandler              /* 36 */
    .word USART1_IRQHandler            /* 37 */
    .word USART2_IRQHandler            /* 38 */
    .word USART3_IRQHandler            /* 39 */
    .word UART4_IRQHandler             /* 40 */
    .word UART5_IRQHandler             /* 41 */
    .word LPUART1_IRQHandler           /* 42 */
    .word LPTIM1_IRQHandler            /* 43 */
    .word LPTIM2_IRQHandler            /* 44 */
    .word TIM6_DAC_IRQHandler          /* 45 — DAC1 underrun */
    .word TIM7_IRQHandler              /* 46 */
    .word TIM8_BRK_IRQHandler          /* 47 */
    .word TIM8_UP_IRQHandler           /* 48 */
    .word TIM8_TRG_COM_IRQHandler      /* 49 */
    .word TIM8_CC_IRQHandler           /* 50 */
    .word ADC3_IRQHandler              /* 51 */
    .word 0                            /* 52 */
    .word 0                            /* 53 */
    .word 0                            /* 54 */
    .word SPI3_IRQHandler               /* 55 */
    .word UART4_IRQHandler             /* 56 */
    .word 0                            /* 57 */
    .word TIM8_BRK_IRQHandler           /* 58 (placeholder) */
    .word TIM8_UP_IRQHandler           /* 59 */
    .word TIM8_TRG_COM_IRQHandler       /* 60 */
    .word TIM8_CC_IRQHandler           /* 61 */
    .word ADC4_IRQHandler               /* 62 */
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word CRS_IRQHandler                /* 71 */
    .word SAI1_IRQHandler              /* 72 */
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word TIM8_BRK_IRQHandler
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word FDCAN2_IT0_IRQHandler
    .word FDCAN2_IT1_IRQHandler
    .word 0
    .word 0
    .word 0
    .word RNG_IRQHandler
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word I2C4_EV_IRQHandler
    .word I2C4_ER_IRQHandler
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word UCPD1_IRQHandler
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word CORDIC_IRQHandler            /* CORDIC ready */
    .word FMAC_IRQHandler              /* FMAC IRQ */
    .word LPUART1_IRQHandler
    .word 0
    .word 0
    .word 0
    .word TIM8_BRK_IRQHandler
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .size g_pfnVectors, . - g_pfnVectors

    .section .text.Reset_Handler, "ax", %progbits
    .align 2
    .global Reset_Handler
    .type Reset_Handler, %function
Reset_Handler:
    ldr   r0, =_estack
    mov   sp, r0
    ldr   r0, =_sidata
    ldr   r1, =_sdata
    ldr   r2, =_edata
copy_data:
    cmp   r1, r2
    bcc   copy_loop
    b     zero_bss
copy_loop:
    ldr   r3, [r0], #4
    str   r3, [r1], #4
    b     copy_data
zero_bss:
    ldr   r0, =_sbss
    ldr   r1, =_ebss
    movs  r2, #0
zero_loop:
    cmp   r0, r1
    bcc   zero_str
    b     call_main
zero_str:
    str   r2, [r0], #4
    b     zero_loop
call_main:
    bl    SystemInit
    bl    main
hang:
    b     hang

    .section .text.Default_Handler, "ax", %progbits
    .align 2
    .global Default_Handler
    .type Default_Handler, %function
Default_Handler:
    b     Default_Handler

    .weak NMI_Handler
    .weak HardFault_Handler
    .weak MemManage_Handler
    .weak BusFault_Handler
    .weak UsageFault_Handler
    .weak SVC_Handler
    .weak DebugMon_Handler
    .weak PendSV_Handler
    .weak SysTick_Handler
    .weak WWDG_IRQHandler
    .weak PVD_PVM_IRQHandler
    .weak RTC_TAMP_LSECSS_IRQHandler
    .weak RTC_WKUP_IRQHandler
    .weak FLASH_IRQHandler
    .weak RCC_IRQHandler
    .weak EXTI0_IRQHandler
    .weak EXTI1_IRQHandler
    .weak EXTI2_IRQHandler
    .weak EXTI3_IRQHandler
    .weak EXTI4_IRQHandler
    .weak DMA1_Channel1_IRQHandler
    .weak DMA1_Channel2_IRQHandler
    .weak DMA1_Channel3_IRQHandler
    .weak DMA1_Channel4_IRQHandler
    .weak DMA1_Channel5_IRQHandler
    .weak DMA1_Channel6_IRQHandler
    .weak DMA1_Channel7_IRQHandler
    .weak ADC1_2_IRQHandler
    .weak USB_HP_IRQHandler
    .weak USB_LP_IRQHandler
    .weak FDCAN1_IT0_IRQHandler
    .weak FDCAN1_IT1_IRQHandler
    .weak EXTI9_5_IRQHandler
    .weak TIM1_BRK_TIM15_IRQHandler
    .weak TIM1_UP_TIM16_IRQHandler
    .weak TIM1_TRG_COM_TIM17_IRQHandler
    .weak TIM1_CC_IRQHandler
    .weak TIM2_IRQHandler
    .weak TIM3_IRQHandler
    .weak TIM4_IRQHandler
    .weak I2C1_EV_IRQHandler
    .weak I2C1_ER_IRQHandler
    .weak I2C2_EV_IRQHandler
    .weak I2C2_ER_IRQHandler
    .weak SPI1_IRQHandler
    .weak SPI2_IRQHandler
    .weak USART1_IRQHandler
    .weak USART2_IRQHandler
    .weak USART3_IRQHandler
    .weak UART4_IRQHandler
    .weak UART5_IRQHandler
    .weak LPUART1_IRQHandler
    .weak LPTIM1_IRQHandler
    .weak LPTIM2_IRQHandler
    .weak TIM6_DAC_IRQHandler
    .weak TIM7_IRQHandler
    .weak TIM8_BRK_IRQHandler
    .weak TIM8_UP_IRQHandler
    .weak TIM8_TRG_COM_IRQHandler
    .weak TIM8_CC_IRQHandler
    .weak ADC3_IRQHandler
    .weak SPI3_IRQHandler
    .weak ADC4_IRQHandler
    .weak CRS_IRQHandler
    .weak SAI1_IRQHandler
    .weak FDCAN2_IT0_IRQHandler
    .weak FDCAN2_IT1_IRQHandler
    .weak RNG_IRQHandler
    .weak I2C4_EV_IRQHandler
    .weak I2C4_ER_IRQHandler
    .weak UCPD1_IRQHandler
    .weak CORDIC_IRQHandler
    .weak FMAC_IRQHandler

    .thumb_set NMI_Handler, Default_Handler
    .thumb_set HardFault_Handler, Default_Handler
    .thumb_set MemManage_Handler, Default_Handler
    .thumb_set BusFault_Handler, Default_Handler
    .thumb_set UsageFault_Handler, Default_Handler
    .thumb_set SVC_Handler, Default_Handler
    .thumb_set DebugMon_Handler, Default_Handler
    .thumb_set PendSV_Handler, Default_Handler
    .thumb_set SysTick_Handler, Default_Handler
    .thumb_set WWDG_IRQHandler, Default_Handler
    .thumb_set PVD_PVM_IRQHandler, Default_Handler
    .thumb_set RTC_TAMP_LSECSS_IRQHandler, Default_Handler
    .thumb_set RTC_WKUP_IRQHandler, Default_Handler
    .thumb_set FLASH_IRQHandler, Default_Handler
    .thumb_set RCC_IRQHandler, Default_Handler
    .thumb_set EXTI0_IRQHandler, Default_Handler
    .thumb_set EXTI1_IRQHandler, Default_Handler
    .thumb_set EXTI2_IRQHandler, Default_Handler
    .thumb_set EXTI3_IRQHandler, Default_Handler
    .thumb_set EXTI4_IRQHandler, Default_Handler
    .thumb_set DMA1_Channel1_IRQHandler, Default_Handler
    .thumb_set DMA1_Channel2_IRQHandler, Default_Handler
    .thumb_set DMA1_Channel3_IRQHandler, Default_Handler
    .thumb_set DMA1_Channel4_IRQHandler, Default_Handler
    .thumb_set DMA1_Channel5_IRQHandler, Default_Handler
    .thumb_set DMA1_Channel6_IRQHandler, Default_Handler
    .thumb_set DMA1_Channel7_IRQHandler, Default_Handler
    .thumb_set ADC1_2_IRQHandler, Default_Handler
    .thumb_set USB_HP_IRQHandler, Default_Handler
    .thumb_set USB_LP_IRQHandler, Default_Handler
    .thumb_set FDCAN1_IT0_IRQHandler, Default_Handler
    .thumb_set FDCAN1_IT1_IRQHandler, Default_Handler
    .thumb_set EXTI9_5_IRQHandler, Default_Handler
    .thumb_set TIM1_BRK_TIM15_IRQHandler, Default_Handler
    .thumb_set TIM1_UP_TIM16_IRQHandler, Default_Handler
    .thumb_set TIM1_TRG_COM_TIM17_IRQHandler, Default_Handler
    .thumb_set TIM1_CC_IRQHandler, Default_Handler
    .thumb_set TIM2_IRQHandler, Default_Handler
    .thumb_set TIM3_IRQHandler, Default_Handler
    .thumb_set TIM4_IRQHandler, Default_Handler
    .thumb_set I2C1_EV_IRQHandler, Default_Handler
    .thumb_set I2C1_ER_IRQHandler, Default_Handler
    .thumb_set I2C2_EV_IRQHandler, Default_Handler
    .thumb_set I2C2_ER_IRQHandler, Default_Handler
    .thumb_set SPI1_IRQHandler, Default_Handler
    .thumb_set SPI2_IRQHandler, Default_Handler
    .thumb_set USART1_IRQHandler, Default_Handler
    .thumb_set USART2_IRQHandler, Default_Handler
    .thumb_set USART3_IRQHandler, Default_Handler
    .thumb_set UART4_IRQHandler, Default_Handler
    .thumb_set UART5_IRQHandler, Default_Handler
    .thumb_set LPUART1_IRQHandler, Default_Handler
    .thumb_set LPTIM1_IRQHandler, Default_Handler
    .thumb_set LPTIM2_IRQHandler, Default_Handler
    .thumb_set TIM6_DAC_IRQHandler, Default_Handler
    .thumb_set TIM7_IRQHandler, Default_Handler
    .thumb_set TIM8_BRK_IRQHandler, Default_Handler
    .thumb_set TIM8_UP_IRQHandler, Default_Handler
    .thumb_set TIM8_TRG_COM_IRQHandler, Default_Handler
    .thumb_set TIM8_CC_IRQHandler, Default_Handler
    .thumb_set ADC3_IRQHandler, Default_Handler
    .thumb_set SPI3_IRQHandler, Default_Handler
    .thumb_set ADC4_IRQHandler, Default_Handler
    .thumb_set CRS_IRQHandler, Default_Handler
    .thumb_set SAI1_IRQHandler, Default_Handler
    .thumb_set FDCAN2_IT0_IRQHandler, Default_Handler
    .thumb_set FDCAN2_IT1_IRQHandler, Default_Handler
    .thumb_set RNG_IRQHandler, Default_Handler
    .thumb_set I2C4_EV_IRQHandler, Default_Handler
    .thumb_set I2C4_ER_IRQHandler, Default_Handler
    .thumb_set UCPD1_IRQHandler, Default_Handler
    .thumb_set CORDIC_IRQHandler, Default_Handler
    .thumb_set FMAC_IRQHandler, Default_Handler

    .end