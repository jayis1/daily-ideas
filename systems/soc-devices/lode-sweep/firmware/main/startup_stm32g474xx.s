/*
 * STM32G474 startup code (minimal — vector table + Reset_Handler).
 * In a real build, use the ST CMSIS startup_stm32g474xx.s.
 */
    .syntax unified
    .cpu cortex-m4
    .thumb

.section .isr_vector,"a",%progbits
.align 2
.global g_pfnVectors
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
    /* 67 IRQ vectors follow (STM32G474) — omitted for brevity */

.section .text.Reset_Handler
.weak Reset_Handler
.type Reset_Handler, %function
Reset_Handler:
    ldr   sp, =_estack
    bl    SystemInit
    bl    main
1:  b     1b

.weak NMI_Handler
.thumb_set NMI_Handler, 1:
.weak HardFault_Handler
.thumb_set HardFault_Handler, 1:
.weak MemManage_Handler
.thumb_set MemManage_Handler, 1:
.weak BusFault_Handler
.thumb_set BusFault_Handler, 1:
.weak UsageFault_Handler
.thumb_set UsageFault_Handler, 1:
.weak SVC_Handler
.thumb_set SVC_Handler, 1:
.weak DebugMon_Handler
.thumb_set DebugMon_Handler, 1:
.weak PendSV_Handler
.thumb_set PendSV_Handler, 1:
.weak SysTick_Handler
.thumb_set SysTick_Handler, 1:

.section .text.SystemInit
.weak SystemInit
.type SystemInit, %function
SystemInit:
    bx lr