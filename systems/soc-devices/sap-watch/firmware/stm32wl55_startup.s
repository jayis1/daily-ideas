/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * stm32wl55_startup.s — Cortex-M4 startup code (simplified)
 *                       Vector table + reset handler
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb

    .section .isr_vector,"a",%progbits
    .global g_pfnVectors
g_pfnVectors:
    .word _estack            /* Initial stack pointer */
    .word Reset_Handler      /* Reset */
    .word NMI_Handler        /* NMI */
    .word HardFault_Handler  /* Hard fault */
    .word 0                   /* MemManage */
    .word 0                   /* BusFault */
    .word 0                   /* UsageFault */
    .word 0                   /* Reserved */
    .word 0                   /* Reserved */
    .word 0                   /* Reserved */
    .word 0                   /* Reserved */
    .word SVC_Handler         /* SVCall */
    .word 0                   /* DebugMon */
    .word 0                   /* Reserved */
    .word PendSV_Handler      /* PendSV */
    .word SysTick_Handler     /* SysTick */
    /* Pad to 64 entries (STM32WL has ~60 IRQs; simplified) */
    .rept 48
    .word Default_Handler
    .endr

    .section .text.Reset_Handler,"ax",%progbits
    .global Reset_Handler
    .type Reset_Handler, %function
Reset_Handler:
    /* Copy .data from flash to RAM */
    ldr r0, =_sidata
    ldr r1, =_sdata
    ldr r2, =_edata
1:
    cmp r1, r2
    bcc 2f
    b 3f
2:
    ldr r3, [r0], #4
    str r3, [r1], #4
    b 1b
3:
    /* Zero .bss */
    ldr r0, =_sbss
    ldr r1, =_ebss
    ldr r2, =0
4:
    cmp r0, r1
    bcc 5f
    b 6f
5:
    str r2, [r0], #4
    b 4b
6:
    /* Call SystemInit then main */
    bl SystemInit
    bl main
    /* If main returns, loop forever */
7:
    b 7b

    .section .text.Default_Handler,"ax",%progbits
    .global Default_Handler
    .type Default_Handler, %function
Default_Handler:
    b Default_Handler

    /* Weak aliases for all handlers → Default_Handler */
    .weak NMI_Handler
    .thumb_set NMI_Handler, Default_Handler
    .weak HardFault_Handler
    .thumb_set HardFault_Handler, Default_Handler
    .weak SVC_Handler
    .thumb_set SVC_Handler, Default_Handler
    .weak PendSV_Handler
    .thumb_set PendSV_Handler, Default_Handler
    .weak SysTick_Handler
    .thumb_set SysTick_Handler, Default_Handler

    .end