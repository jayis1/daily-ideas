/*
 * startup_stm32g474xx.s — startup code and vector table
 * for STM32G474RET6 (Cortex-M4F, 512 KB Flash, 128 KB SRAM)
 */

    .syntax unified
    .cpu cortex-m4
    .fpu softvfp
    .thumb

.global g_pfnVectors
.global Default_Handler
.global Reset_Handler

.extern _estack
.extern _sdata
.extern _edata
.extern _sbss
.extern _ebss

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
    /* IRQ 0..15 (DMA, ADC, USART, etc.) — all default handler */
    .rept 96
    .word Default_Handler
    .endr
    .size g_pfnVectors, .-g_pfnVectors

.section .text.Reset_Handler, "ax", %progbits
    .align 2
    .global Reset_Handler
    .type Reset_Handler, %function
Reset_Handler:
    ldr   r0, =_sdata
    ldr   r1, =_edata
    ldr   r2, =_etext
copy_data:
    cmp   r0, r1
    bcc   1f
    b     clear_bss
1:
    ldr   r3, [r2], #4
    str   r3, [r0], #4
    b     copy_data
clear_bss:
    ldr   r0, =_sbss
    ldr   r1, =_ebss
    movs  r2, #0
2:
    cmp   r0, r1
    bcc   3f
    b     call_main
3:
    str   r2, [r0], #4
    b     clear_bss
call_main:
    bl    SystemInit
    bl    main
    b     .
    .size Reset_Handler, .-Reset_Handler

.section .text.Default_Handler, "ax", %progbits
    .align 2
    .global Default_Handler
    .type Default_Handler, %function
Default_Handler:
    b     .
    .size Default_Handler, .-Default_Handler

.weak NMI_Handler
.weak HardFault_Handler
.weak MemManage_Handler
.weak BusFault_Handler
.weak UsageFault_Handler
.weak SVC_Handler
.weak DebugMon_Handler
.weak PendSV_Handler
.weak SysTick_Handler
.weak DMA1_Channel1_IRQHandler
.weak USART1_IRQHandler

.thumb_set NMI_Handler, Default_Handler
.thumb_set HardFault_Handler, Default_Handler
.thumb_set MemManage_Handler, Default_Handler
.thumb_set BusFault_Handler, Default_Handler
.thumb_set UsageFault_Handler, Default_Handler
.thumb_set SVC_Handler, Default_Handler
.thumb_set DebugMon_Handler, Default_Handler
.thumb_set PendSV_Handler, Default_Handler
.thumb_set SysTick_Handler, Default_Handler
.thumb_set DMA1_Channel1_IRQHandler, Default_Handler
.thumb_set USART1_IRQHandler, Default_Handler