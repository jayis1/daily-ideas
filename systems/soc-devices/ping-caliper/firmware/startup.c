/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * startup.s — Cortex-M4 startup code and vector table
 *
 * Minimal vector table + Reset_Handler that copies .data, zeroes .bss,
 * and calls main(). All other vectors default to an infinite loop.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"

extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

void Reset_Handler(void);
void Default_Handler(void);
void NMI_Handler(void)         __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void)    __attribute__((weak, alias("Default_Handler")));
void MemManage_Handler(void)    __attribute__((weak, alias("Default_Handler")));
void BusFault_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void UsageFault_Handler(void)   __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void)          __attribute__((weak, alias("Default_Handler")));
void DebugMon_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void)       __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void)      __attribute__((weak, alias("Default_Handler")));

/* UART/DMA/ADC handlers (weak — full impl in uart_proto.c/receiver.c) */
void DMA1_Channel1_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void USART3_IRQHandler(void)       __attribute__((weak, alias("Default_Handler")));

__attribute__((section(".isr_vector"), used))
const void *g_pfnVectors[] = {
    &_estack,                /* Initial stack pointer */
    Reset_Handler,
    NMI_Handler,
    HardFault_Handler,
    MemManage_Handler,
    BusFault_Handler,
    UsageFault_Handler,
    0, 0, 0, 0,              /* Reserved */
    SVC_Handler,
    DebugMon_Handler,
    0,                       /* Reserved */
    PendSV_Handler,
    SysTick_Handler,
    /* External interrupts (simplified — only the ones we use) */
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, /* 0..15 */
    /* IRQ 1 = DMA1 Channel 1 (index 11 in the table) */
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, DMA1_Channel1_IRQHandler, /* 11 */
    /* USART3 = IRQ 27 (simplified placement) */
};

void Reset_Handler(void)
{
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) *dst++ = *src++;

    dst = &_sbss;
    while (dst < &_ebss) *dst++ = 0;

    /* Enable FPU (CP10/CP11 full access) */
    SCB->CPACR |= (0xF << 20);

    main();

    for (;;) { }
}

void Default_Handler(void)
{
    for (;;) { }
}