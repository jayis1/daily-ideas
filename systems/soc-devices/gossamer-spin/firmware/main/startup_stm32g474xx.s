/*
 * gossamer-spin / firmware / startup_stm32g474xx.s
 * Startup code for STM32G474RET6 (Cortex-M4F, LQFP64).
 * Vector table + reset handler.
 */
.syntax unified
.cpu cortex-m4
.thumb

.section .isr_vector,"a",%progbits
.align 2
.global g_pfnVectors
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
    /* 45 IRQs for STM32G4x — abbreviated */
    .rept 45
    .word Default_Handler
    .endr
    .size g_pfnVectors, . - g_pfnVectors

.section .text.Reset_Handler
.weak Reset_Handler
.type Reset_Handler, %function
Reset_Handler:
    ldr r0, =_estack
    mov sp, r0
    ldr r0, =_sidata
    ldr r1, =_sdata
    ldr r2, =_edata
1:  cmp r1, r2
    bcc 2f
    b 3f
2:  ldr r3, [r0], #4
    str r3, [r1], #4
    b 1b
3:  ldr r0, =_sbss
    ldr r1, =_ebss
    movs r2, #0
4:  cmp r0, r1
    bcc 5f
    b 6f
5:  str r2, [r0], #4
    b 4b
6:  bl main
    b .

.section .text.Default_Handler
.weak NMI_Handler
.weak HardFault_Handler
.weak MemManage_Handler
.weak BusFault_Handler
.weak UsageFault_Handler
.weak SVC_Handler
.weak DebugMon_Handler
.weak PendSV_Handler
.weak SysTick_Handler
Default_Handler:
NMI_Handler:
HardFault_Handler:
MemManage_Handler:
BusFault_Handler:
UsageFault_Handler:
SVC_Handler:
DebugMon_Handler:
PendSV_Handler:
SysTick_Handler:
    b Default_Handler
    .size Reset_Handler, . - Reset_Handler