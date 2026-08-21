/*
 * startup_stm32g474xx.s — Minimal startup for STM32G474RET6
 * Vector table + reset handler. Based on ST CMSIS startup.
 */

    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb

.section .isr_vector,"a",%progbits
.global _vector_table
_vector_table:
    .word _estack            /* Initial stack pointer */
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

    /* Add more IRQ vectors as needed for STM32G474 (up to 128) */
    .rept 128 - 16
    .word Default_Handler
    .endr

.section .text
Reset_Handler:
    ldr r0, =_estack
    mov sp, r0
    bl SystemInit
    bl main
    b .

Weak_Handler:
    b .
    .size Weak_Handler, . - Weak_Handler

NMI_Handler:
HardFault_Handler:
MemManage_Handler:
BusFault_Handler:
UsageFault_Handler:
SVC_Handler:
DebugMon_Handler:
PendSV_Handler:
Default_Handler:
    b Weak_Handler