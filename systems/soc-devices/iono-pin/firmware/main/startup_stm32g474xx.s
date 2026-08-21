/*
 * startup_stm32g474xx.s — minimal startup for STM32G474RET6
 * Copies .data from FLASH to RAM, zeros .bss, calls SystemInit then main.
 */

    .syntax unified
    .cpu cortex-m4
    .fpu softvfp
    .thumb

.extern _sidata
.extern _sdata
.extern _edata
.extern _sbss
.extern _ebss
.extern SystemInit
.extern main
.extern _estack

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

.section .text
.global Reset_Handler
Reset_Handler:
    ldr r0, =_estack
    bl SystemInit
    ldr r0, =_sidata
    ldr r1, =_sdata
    ldr r2, =_edata
copy_data:
    cmp r1, r2
    bcc copy_loop
    b zero_bss
copy_loop:
    ldr r3, [r0], #4
    str r3, [r1], #4
    b copy_data
zero_bss:
    ldr r0, =_sbss
    ldr r1, =_ebss
    movs r2, #0
zero_loop:
    cmp r0, r1
    bcc zero_fill
    b call_main
zero_fill:
    str r2, [r0], #4
    b zero_loop
call_main:
    bl main
hang:
    b hang

.weak NMI_Handler
.weak HardFault_Handler
.weak MemManage_Handler
.weak BusFault_Handler
.weak UsageFault_Handler
.weak SVC_Handler
.weak DebugMon_Handler
.weak PendSV_Handler
.weak SysTick_Handler

NMI_Handler:        b .
HardFault_Handler:   b .
MemManage_Handler:   b .
BusFault_Handler:    b .
UsageFault_Handler:  b .
SVC_Handler:         b .
DebugMon_Handler:    b .
PendSV_Handler:      b .
SysTick_Handler:     b .