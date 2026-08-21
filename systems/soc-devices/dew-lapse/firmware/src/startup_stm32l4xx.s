/* startup_stm32l4xx.s — minimal ARM Cortex-M4 startup for STM32L476RG.
 * Vector table + Reset_Handler that copies .data and zeroes .bss.
 */
    .syntax unified
    .cpu cortex-m4
    .thumb

    .section .isr_vector, "a", %progbits
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
    /* 16 IRQs follow; for brevity we pad up to ~64 entries */
    .rept 48
    .word Default_Handler
    .endr

    .section .text.Reset_Handler, "ax", %progbits
    .align 2
    .global Reset_Handler
    .thumb
Reset_Handler:
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
    ldr r1, =_sbss
    ldr r2, =_ebss
    movs r3, #0
zero_loop:
    cmp r1, r2
    bcc zero_fill
    b call_main
zero_fill:
    str r3, [r1], #4
    b zero_loop
call_main:
    bl main
hang:
    b hang

    .section .text.Default_Handler, "ax", %progbits
Default_Handler:
    b Default_Handler
    .weak NMI_Handler
    .thumb_set NMI_Handler, Default_Handler
    .weak MemManage_Handler
    .thumb_set MemManage_Handler, Default_Handler
    .weak BusFault_Handler
    .thumb_set BusFault_Handler, Default_Handler
    .weak UsageFault_Handler
    .thumb_set UsageFault_Handler, Default_Handler
    .weak SVC_Handler
    .thumb_set SVC_Handler, Default_Handler
    .weak DebugMon_Handler
    .thumb_set DebugMon_Handler, Default_Handler
    .weak PendSV_Handler
    .thumb_set PendSV_Handler, Default_Handler

    .end